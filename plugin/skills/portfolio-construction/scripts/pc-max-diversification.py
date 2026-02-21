#!/usr/bin/env python3
"""
pc-max-diversification.py — Maximum Diversification Ratio portfolio.

Maximizes DR = (wᵀσ) / sqrt(wᵀΣw), the ratio of weighted-average vol
to portfolio vol. Higher DR means more diversification benefit captured.
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
## Maximum Diversification Ratio

Maximizes the diversification ratio (DR):

    maximize  (wᵀσ) / √(wᵀΣw)
    subject to  Σwᵢ = 1, IPS bounds, category bounds

where σ is the vector of individual asset volatilities and Σ is the
covariance matrix. DR = 1 means no diversification benefit; higher is better.

This method rewards low-correlation combinations and naturally tilts toward
assets that contribute diversification rather than just return.

**Strengths**: Maximizes diversification benefit explicitly; correlation-aware; no return inputs.
**Weaknesses**: Can overweight assets with temporary low correlation.
**Best regime**: EXPANSION, RECOVERY, LATE-CYCLE.
"""


def optimize(mu, Sigma, rf, vols):
    """Maximize diversification ratio subject to IPS constraints."""
    Sigma_shrunk = shrink_covariance(Sigma, "ledoit-wolf")
    bounds = get_bounds()
    constraints = build_constraints(Sigma_shrunk, include_category=True)

    def neg_dr(w):
        weighted_avg_vol = w @ vols
        port_vol = np.sqrt(w @ Sigma_shrunk @ w)
        if port_vol < 1e-10:
            return 0.0
        return -weighted_avg_vol / port_vol

    def neg_dr_grad(w):
        weighted_avg_vol = w @ vols
        port_var = w @ Sigma_shrunk @ w
        port_vol = np.sqrt(port_var)
        if port_vol < 1e-10:
            return np.zeros(N)
        grad_num = vols
        grad_denom = (Sigma_shrunk @ w) / port_vol
        return -(port_vol * grad_num - weighted_avg_vol * grad_denom) / port_var

    best_w = None
    best_neg_dr = np.inf

    rng = np.random.default_rng(42)
    starts = [make_initial_weights()]
    for _ in range(4):
        from common import project_to_ips
        starts.append(project_to_ips(rng.dirichlet(np.ones(N))))

    for w0 in starts:
        try:
            result = minimize(
                neg_dr,
                w0,
                jac=neg_dr_grad,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
                options={"ftol": 1e-12, "maxiter": 2000},
            )
            if result.fun < best_neg_dr:
                best_neg_dr = result.fun
                best_w = np.clip(result.x, 0, 1)
        except Exception:
            continue

    if best_w is None:
        best_w = make_initial_weights()

    best_w = best_w / best_w.sum()
    return best_w


if __name__ == "__main__":
    run_pc_script("pc-max-diversification", optimize, METHODOLOGY)
