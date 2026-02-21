#!/usr/bin/env python3
"""
pc-global-min-variance.py — Global Minimum Variance portfolio.

Minimizes portfolio variance with no return inputs required.
Most defensive optimization-based approach.
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
## Global Minimum Variance

Finds the portfolio with the lowest possible variance:

    minimize  wᵀΣw
    subject to  Σwᵢ = 1, IPS bounds, category bounds

Requires only the covariance matrix — no expected returns needed.
Uses Ledoit-Wolf shrinkage on the covariance matrix to improve stability.

The GMV portfolio sits at the leftmost point of the efficient frontier.

**Strengths**: No sensitivity to return estimates; lowest portfolio variance ex-ante;
  strong historical risk-adjusted performance (low-vol anomaly).
**Weaknesses**: Ignores returns; can concentrate in historically low-vol assets.
**Best regime**: RECESSION, LATE-CYCLE (maximum risk reduction).
"""


def optimize(mu, Sigma, rf, vols):
    """Global minimum variance: minimize wᵀΣw subject to IPS constraints."""
    Sigma_shrunk = shrink_covariance(Sigma, "ledoit-wolf")
    bounds = get_bounds()
    constraints = build_constraints(Sigma_shrunk, include_category=True)
    w0 = make_initial_weights()

    def objective(w):
        return w @ Sigma_shrunk @ w

    def grad(w):
        return 2 * Sigma_shrunk @ w

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
    run_pc_script("pc-global-min-variance", optimize, METHODOLOGY)
