#!/usr/bin/env python3
"""
pc-robust-mean-variance.py — Robust Mean-Variance Optimization.

Uses James-Stein shrinkage of returns toward the grand mean and
Ledoit-Wolf covariance shrinkage to reduce estimation error.
Adds Black-Litterman-style uncertainty dampening.
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
## Robust Mean-Variance Optimization

Addresses the "garbage in, garbage out" problem of classical MVO by applying
two layers of shrinkage before optimization:

1. **James-Stein return shrinkage**: Shrinks individual asset return estimates
   toward the grand mean:
   μ_robust = (1 - α) * μ + α * μ_bar
   where α is the shrinkage intensity (default: 0.5) and μ_bar is the
   cross-sectional mean of all expected returns.

2. **Ledoit-Wolf covariance shrinkage**: Shrinks the sample covariance toward
   a diagonal target to reduce estimation noise.

Then solves standard MVO (maximize Sharpe) with robustified inputs.

**Strengths**: Balances return information with robustness; more stable than raw MVO.
**Weaknesses**: Shrinkage intensity is arbitrary; still sensitive to direction of return estimates.
**Best regime**: EXPANSION, RECOVERY (when some return signal is trusted but not fully).
"""

JS_SHRINKAGE = 0.5  # James-Stein shrinkage intensity toward grand mean


def james_stein_shrink(mu, shrinkage=JS_SHRINKAGE):
    """Apply James-Stein shrinkage of return estimates toward grand mean."""
    grand_mean = np.mean(mu)
    return (1 - shrinkage) * mu + shrinkage * grand_mean


def optimize(mu, Sigma, rf, vols):
    """Robust MVO: shrink returns + covariance, then maximize Sharpe."""
    # Apply shrinkage
    mu_robust = james_stein_shrink(mu, JS_SHRINKAGE)
    Sigma_robust = shrink_covariance(Sigma, "ledoit-wolf")

    bounds = get_bounds()
    constraints = build_constraints(Sigma_robust, include_category=True)

    def neg_sharpe(w):
        port_ret = w @ mu_robust
        port_vol = np.sqrt(w @ Sigma_robust @ w)
        if port_vol < 1e-10:
            return 0.0
        return -(port_ret - rf) / port_vol

    def neg_sharpe_grad(w):
        port_ret = w @ mu_robust
        port_var = w @ Sigma_robust @ w
        port_vol = np.sqrt(port_var)
        if port_vol < 1e-10:
            return np.zeros(N)
        excess = port_ret - rf
        grad_ret = mu_robust
        grad_vol = (Sigma_robust @ w) / port_vol
        return -(port_vol * grad_ret - excess * grad_vol) / port_var

    best_w = None
    best_obj = np.inf

    rng = np.random.default_rng(42)
    starts = [make_initial_weights()]
    for _ in range(4):
        from common import project_to_ips
        starts.append(project_to_ips(rng.dirichlet(np.ones(N))))

    for w0 in starts:
        try:
            result = minimize(
                neg_sharpe,
                w0,
                jac=neg_sharpe_grad,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
                options={"ftol": 1e-12, "maxiter": 2000},
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
    run_pc_script("pc-robust-mean-variance", optimize, METHODOLOGY)
