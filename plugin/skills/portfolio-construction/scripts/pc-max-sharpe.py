#!/usr/bin/env python3
"""
pc-max-sharpe.py — Maximum Sharpe Ratio (Tangency Portfolio) optimization.

Maximizes (mu - rf) / sigma subject to IPS constraints.
Requires trusted return forecasts; highly sensitive to estimation error.
Uses Ledoit-Wolf shrinkage on covariance for stability.
"""

import sys
import numpy as np
from scipy.optimize import minimize
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from common import (
    run_pc_script, N, shrink_covariance,
    build_constraints, get_bounds, make_initial_weights
)

METHODOLOGY = """
## Maximum Sharpe Ratio (Tangency Portfolio)

Finds the portfolio on the efficient frontier with the highest Sharpe ratio:

    maximize  (μᵀw - rf) / √(wᵀΣw)
    subject to  Σwᵢ = 1, IPS bounds, category bounds

Equivalent to maximizing the Sharpe ratio directly, or equivalently
finding the tangency point between the Capital Market Line and the frontier.

Uses Ledoit-Wolf covariance shrinkage to improve numerical stability.
Multiple random restarts are used to avoid local optima.

**Strengths**: Theoretically optimal under mean-variance framework; highest expected Sharpe ex-ante.
**Weaknesses**: Highly sensitive to return estimates ("garbage in, garbage out"); concentrated portfolios.
**Best regime**: EXPANSION, RECOVERY (when return forecasts are most reliable).
"""


def optimize(mu, Sigma, rf, vols):
    """Maximize Sharpe ratio with IPS constraints and multiple restarts."""
    Sigma_shrunk = shrink_covariance(Sigma, "ledoit-wolf")
    bounds = get_bounds()
    constraints = build_constraints(Sigma_shrunk, include_category=True)

    def neg_sharpe(w):
        port_ret = w @ mu
        port_vol = np.sqrt(w @ Sigma_shrunk @ w)
        if port_vol < 1e-10:
            return 0.0
        return -(port_ret - rf) / port_vol

    def neg_sharpe_grad(w):
        port_ret = w @ mu
        port_var = w @ Sigma_shrunk @ w
        port_vol = np.sqrt(port_var)
        if port_vol < 1e-10:
            return np.zeros(N)
        excess = port_ret - rf
        grad_ret = mu
        grad_vol = (Sigma_shrunk @ w) / port_vol
        return -(port_vol * grad_ret - excess * grad_vol) / port_var

    best_w = None
    best_sharpe = -np.inf

    # Multiple restarts with different starting points
    rng = np.random.default_rng(42)
    starting_points = [make_initial_weights()]
    for _ in range(9):
        raw = rng.dirichlet(np.ones(N))
        from common import project_to_ips
        starting_points.append(project_to_ips(raw))

    for w0 in starting_points:
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
            if result.success or result.fun < -0.001:
                w_candidate = np.clip(result.x, 0, 1)
                w_candidate = w_candidate / w_candidate.sum()
                sharpe = -neg_sharpe(w_candidate)
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_w = w_candidate
        except Exception:
            continue

    if best_w is None:
        best_w = make_initial_weights()

    return best_w


if __name__ == "__main__":
    run_pc_script("pc-max-sharpe", optimize, METHODOLOGY)
