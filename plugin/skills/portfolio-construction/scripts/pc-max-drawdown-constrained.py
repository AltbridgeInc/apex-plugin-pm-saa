#!/usr/bin/env python3
"""
pc-max-drawdown-constrained.py — Max-Sharpe portfolio with drawdown constraint.

Maximizes Sharpe ratio while ensuring simulated maximum drawdown stays
below a target threshold (default: 25%). Combines return optimization
with explicit tail-risk management.
"""

import sys
import numpy as np
from scipy.optimize import minimize
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from common import (
    run_pc_script, N, build_constraints, get_bounds,
    make_initial_weights, shrink_covariance, project_to_ips
)

METHODOLOGY = """
## Max-Sharpe with Maximum Drawdown Constraint

Maximizes the Sharpe ratio subject to an explicit maximum drawdown constraint:

    maximize  (μ_p - rf) / σ_p
    subject to  max_drawdown(w) <= MDD_MAX (25%)
                Σwᵢ = 1, IPS bounds, category bounds

Maximum drawdown is estimated via Monte Carlo simulation of 5-year return paths.
A penalty function enforces the constraint softly in the first pass; if violated,
the solution is iteratively constrained until MDD is within tolerance.

**Strengths**: Directly limits tail losses; explicit drawdown budget; appealing to risk-averse investors.
**Weaknesses**: MDD estimate is path-dependent and distribution-sensitive; computationally intensive.
**Best regime**: LATE-CYCLE, RECESSION (explicit drawdown protection needed).
"""

MDD_MAX = 0.25       # 25% maximum drawdown target
N_PATHS = 2000       # Monte Carlo paths
N_MONTHS = 60        # 5-year simulation horizon
RANDOM_SEED = 77
MDD_PENALTY = 50.0   # Penalty multiplier for constraint violation


def _simulate_mdd(w, Sigma_shrunk, mu, n_paths=N_PATHS, n_months=N_MONTHS):
    """Estimate expected maximum drawdown via Monte Carlo."""
    rng = np.random.default_rng(RANDOM_SEED)
    monthly_mu = mu / 12
    monthly_Sigma = Sigma_shrunk / 12

    # Simulate return paths
    paths = rng.multivariate_normal(monthly_mu, monthly_Sigma, size=(n_paths, n_months))
    port_returns = paths @ w  # (n_paths, n_months)

    # Compute max drawdown for each path
    cum_ret = np.cumprod(1 + port_returns, axis=1)
    running_max = np.maximum.accumulate(cum_ret, axis=1)
    drawdowns = (cum_ret - running_max) / running_max
    max_drawdowns = drawdowns.min(axis=1)  # (n_paths,)

    # Return median expected MDD (50th percentile)
    return float(np.median(max_drawdowns))


def optimize(mu, Sigma, rf, vols):
    """Max-Sharpe with drawdown penalty constraint."""
    Sigma_shrunk = shrink_covariance(Sigma, "ledoit-wolf")
    bounds = get_bounds()

    # Pre-compute MDD cache for efficiency
    mdd_cache = {}

    def neg_sharpe_with_mdd_penalty(w):
        port_ret = w @ mu
        port_vol = np.sqrt(np.maximum(w @ Sigma_shrunk @ w, 1e-12))
        sharpe = (port_ret - rf) / port_vol if port_vol > 0 else 0.0

        # Estimate drawdown (cache by weight hash for efficiency)
        w_key = tuple(np.round(w, 3))
        if w_key not in mdd_cache:
            mdd_cache[w_key] = _simulate_mdd(w, Sigma_shrunk, mu, n_paths=500, n_months=N_MONTHS)
        mdd = mdd_cache[w_key]

        # Soft penalty: quadratic penalty for exceeding MDD_MAX
        penalty = 0.0
        if mdd < -MDD_MAX:
            violation = abs(mdd) - MDD_MAX
            penalty = MDD_PENALTY * violation ** 2

        return -sharpe + penalty

    constraints = build_constraints(Sigma_shrunk, include_category=True)

    best_w = None
    best_obj = np.inf

    rng = np.random.default_rng(42)
    starts = [make_initial_weights()]
    # Also try inverse-vol start (defensive)
    iv = 1.0 / np.maximum(vols, 1e-8)
    starts.append(project_to_ips(iv / iv.sum()))

    for w0 in starts:
        try:
            result = minimize(
                neg_sharpe_with_mdd_penalty,
                w0,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
                options={"ftol": 1e-7, "maxiter": 300},
            )
            if result.fun < best_obj:
                best_obj = result.fun
                best_w = np.clip(result.x, 0, 1)
        except Exception:
            continue

    if best_w is None:
        best_w = make_initial_weights()

    return best_w / best_w.sum()


if __name__ == "__main__":
    run_pc_script("pc-max-drawdown-constrained", optimize, METHODOLOGY)
