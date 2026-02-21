#!/usr/bin/env python3
"""
pc-risk-parity.py — Risk Parity (Equal Risk Contribution) portfolio.

Each asset contributes equally to total portfolio risk.
Targets equal marginal risk contribution: w_i * (Σw)_i / σ_p = 1/N for all i.
"""

import sys
import numpy as np
from scipy.optimize import minimize
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from common import (
    run_pc_script, N, build_constraints, get_bounds,
    make_initial_weights, project_to_ips, shrink_covariance
)

METHODOLOGY = """
## Risk Parity (Equal Risk Contribution)

Risk parity targets equal risk contribution from each asset class:

    RC_i = w_i * (Σw)_i / σ_p  =  σ_p / N   for all i

This is achieved by minimizing the sum of squared deviations from equal
risk contribution. The portfolio is then projected to the IPS-feasible space.

Uses a two-step approach:
1. Solve unconstrained risk parity (using log-barrier method)
2. Project to IPS-feasible space

**Strengths**: True risk diversification; excellent out-of-sample Sharpe; regime-robust.
**Weaknesses**: Over-allocates to bonds in normal environments (leveraged in practice); ignores returns.
**Best regime**: All regimes; particularly strong in LATE-CYCLE and RECESSION.
"""


def _risk_parity_unconstrained(Sigma):
    """
    Solve unconstrained risk parity via log-barrier method.
    Minimizes sum of squared deviations from equal RC.
    """
    n = Sigma.shape[0]

    def objective(w):
        port_var = w @ Sigma @ w
        port_vol = np.sqrt(port_var)
        mrc = Sigma @ w
        rc = w * mrc / port_vol
        target = port_vol / n
        return np.sum((rc - target) ** 2)

    def grad(w):
        port_var = w @ Sigma @ w
        port_vol = np.sqrt(port_var)
        mrc = Sigma @ w
        rc = w * mrc / port_vol
        target = port_vol / n

        # Gradient of RC_i w.r.t. w_j
        # d(RC_i)/d(w_j) = (Sigma[i,j]*w[i] + mrc[i]*delta_ij)*port_vol - rc[i]*(Sigma @ w)[j] / port_var
        grad = np.zeros(n)
        for i in range(n):
            dRC = np.zeros(n)
            for j in range(n):
                dRC[j] = (Sigma[i, j] * w[i] + mrc[i] * (i == j)) / port_vol - rc[i] * mrc[j] / port_var
            grad += 2 * (rc[i] - target) * dRC
        return grad

    # Use log-barrier for positivity (avoid numerical issues at zero)
    def log_barrier_obj(log_w):
        w = np.exp(log_w)
        w = w / w.sum()
        return objective(w)

    # Initialize with inverse-vol
    vols = np.sqrt(np.diag(Sigma))
    w0 = 1.0 / np.maximum(vols, 1e-8)
    w0 = w0 / w0.sum()

    # Optimize in log space (enforces positivity automatically)
    log_w0 = np.log(np.maximum(w0, 1e-6))
    result = minimize(
        log_barrier_obj,
        log_w0,
        method="L-BFGS-B",
        options={"ftol": 1e-12, "maxiter": 5000},
    )
    w = np.exp(result.x)
    return w / w.sum()


def optimize(mu, Sigma, rf, vols):
    """Risk parity: equal risk contribution, then project to IPS."""
    Sigma_shrunk = shrink_covariance(Sigma, "ledoit-wolf")

    # Solve unconstrained risk parity
    w_rp = _risk_parity_unconstrained(Sigma_shrunk)

    # Project to IPS-feasible space
    return project_to_ips(w_rp)


if __name__ == "__main__":
    run_pc_script("pc-risk-parity", optimize, METHODOLOGY)
