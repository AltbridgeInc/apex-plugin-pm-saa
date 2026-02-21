#!/usr/bin/env python3
"""
pc-minimum-correlation.py — Minimum Correlation portfolio.

Minimizes the weighted-average pairwise correlation of the portfolio.
Finds the most internally diversified set of assets.
"""

import sys
import numpy as np
from scipy.optimize import minimize
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from common import (
    run_pc_script, N, build_constraints, get_bounds,
    make_initial_weights, shrink_covariance
)

METHODOLOGY = """
## Minimum Correlation Portfolio

Minimizes the average pairwise correlation of portfolio holdings:

    minimize  wᵀCw  (where C is the correlation matrix)
    subject to  Σwᵢ = 1, IPS bounds, category bounds

By using the correlation matrix (rather than covariance), this method
normalizes out vol differences and focuses purely on reducing correlation
between holdings. The result is the most internally uncorrelated portfolio.

**Strengths**: Pure diversification metric; correlation-aware; robust to vol estimation.
**Weaknesses**: Does not account for vol levels; can hold high-vol uncorrelated assets.
**Best regime**: EXPANSION, RECOVERY (when finding uncorrelated return sources matters most).
"""


def optimize(mu, Sigma, rf, vols):
    """Minimize weighted-average pairwise correlation."""
    Sigma_shrunk = shrink_covariance(Sigma, "ledoit-wolf")

    # Compute correlation matrix
    vol_outer = np.outer(vols, vols)
    C = Sigma_shrunk / np.maximum(vol_outer, 1e-10)
    np.fill_diagonal(C, 1.0)

    bounds = get_bounds()
    constraints = build_constraints(Sigma_shrunk, include_category=True)
    w0 = make_initial_weights()

    def objective(w):
        return w @ C @ w

    def grad(w):
        return 2 * C @ w

    result = minimize(
        objective,
        w0,
        jac=grad,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"ftol": 1e-12, "maxiter": 2000},
    )

    w = np.clip(result.x, 0, 1)
    return w / w.sum()


if __name__ == "__main__":
    run_pc_script("pc-minimum-correlation", optimize, METHODOLOGY)
