#!/usr/bin/env python3
"""
pc-hierarchical-risk-parity.py — Hierarchical Risk Parity (HRP).

Uses hierarchical clustering on the correlation matrix to allocate risk.
Avoids the instability of covariance matrix inversion.
"""

import sys
import numpy as np
from scipy.cluster.hierarchy import linkage, to_tree
from scipy.spatial.distance import squareform
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from common import (
    run_pc_script, N, SLUGS, project_to_ips, shrink_covariance
)

METHODOLOGY = """
## Hierarchical Risk Parity (HRP)

HRP (Lopez de Prado, 2016) constructs a diversified portfolio without
inverting the covariance matrix, making it robust to estimation error.

**Three-step process**:
1. **Tree clustering**: Build a hierarchical cluster tree from the correlation matrix
   using single-linkage and a distance metric d = sqrt((1 - rho) / 2)
2. **Quasi-diagonalization**: Reorder the covariance matrix so similar
   assets are grouped together
3. **Recursive bisection**: Allocate risk top-down: at each node, split the
   allocation between two sub-clusters proportionally to their inverse variance

The result uses full covariance information without matrix inversion.
Weights are then projected to the IPS-feasible space.

**Strengths**: Robust; no matrix inversion; captures cluster structure; outperforms
  out-of-sample; used by many sophisticated institutions.
**Weaknesses**: Ignores expected returns; result depends on linkage method chosen.
**Best regime**: All regimes; particularly robust in RECESSION and LATE-CYCLE.
"""


def _corr_to_distance(corr):
    """Convert correlation matrix to distance matrix for clustering."""
    dist = np.sqrt(np.maximum((1.0 - corr) / 2.0, 0.0))
    np.fill_diagonal(dist, 0.0)
    return dist


def _get_quasi_diag(link):
    """Reorder assets from hierarchical clustering (quasi-diagonalization)."""
    root, node_list = to_tree(link, rd=True)
    n_leaves = len([n for n in node_list if n.is_leaf()])

    def get_leaves(node):
        if node.is_leaf():
            return [node.id]
        return get_leaves(node.left) + get_leaves(node.right)

    return get_leaves(root)


def _cluster_var(cov_sub, weights):
    """Compute cluster variance."""
    w = weights / weights.sum()
    return float(w @ cov_sub @ w)


def _recursive_bisection(cov, sort_ix):
    """
    Recursively bisect the sorted asset list, allocating weights by inverse variance.
    """
    n = len(sort_ix)
    w = np.ones(n)
    clusters = [list(range(n))]

    while clusters:
        cluster = clusters.pop()
        if len(cluster) <= 1:
            continue

        # Split cluster in half
        mid = len(cluster) // 2
        left_ix = cluster[:mid]
        right_ix = cluster[mid:]

        # Compute sub-cluster variances
        left_assets = [sort_ix[i] for i in left_ix]
        right_assets = [sort_ix[i] for i in right_ix]

        left_cov = cov[np.ix_(left_assets, left_assets)]
        right_cov = cov[np.ix_(right_assets, right_assets)]

        # Inverse variance weighting for each sub-cluster
        left_w = np.ones(len(left_assets)) / len(left_assets)
        right_w = np.ones(len(right_assets)) / len(right_assets)

        left_var = _cluster_var(left_cov, left_w)
        right_var = _cluster_var(right_cov, right_w)

        # Allocate proportional to inverse variance
        alpha = right_var / (left_var + right_var) if (left_var + right_var) > 0 else 0.5

        for i in left_ix:
            w[i] *= alpha
        for i in right_ix:
            w[i] *= (1 - alpha)

        if len(left_ix) > 1:
            clusters.append(left_ix)
        if len(right_ix) > 1:
            clusters.append(right_ix)

    return w


def optimize(mu, Sigma, rf, vols):
    """HRP: cluster → quasi-diagonalize → recursive bisect → project to IPS."""
    Sigma_shrunk = shrink_covariance(Sigma, "ledoit-wolf")

    # Correlation matrix
    vol_outer = np.outer(vols, vols)
    corr = Sigma_shrunk / np.maximum(vol_outer, 1e-10)
    np.fill_diagonal(corr, 1.0)
    corr = np.clip(corr, -1.0, 1.0)

    # Distance matrix for clustering
    dist = _corr_to_distance(corr)

    # Condensed distance matrix for scipy linkage
    condensed = squareform(dist, checks=False)
    link = linkage(condensed, method="single")

    # Quasi-diagonalization: reorder assets
    sort_ix = _get_quasi_diag(link)

    # Reordered covariance
    sort_ix_arr = np.array(sort_ix)
    cov_sorted = Sigma_shrunk[np.ix_(sort_ix_arr, sort_ix_arr)]

    # Recursive bisection
    w_sorted = _recursive_bisection(cov_sorted, sort_ix_arr)

    # Map back to original asset order
    w = np.zeros(N)
    for i, orig_idx in enumerate(sort_ix):
        w[orig_idx] = w_sorted[i]

    w = w / w.sum()
    return project_to_ips(w)


if __name__ == "__main__":
    run_pc_script("pc-hierarchical-risk-parity", optimize, METHODOLOGY)
