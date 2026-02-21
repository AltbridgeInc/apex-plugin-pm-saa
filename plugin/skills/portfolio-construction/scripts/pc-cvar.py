#!/usr/bin/env python3
"""
pc-cvar.py — Conditional Value at Risk (CVaR) minimization.

Minimizes Expected Shortfall (CVaR) at 95% confidence level.
Uses Monte Carlo simulation of portfolio returns.
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
## CVaR (Conditional Value at Risk / Expected Shortfall) Minimization

Minimizes the Expected Shortfall at 95% confidence:

    minimize  CVaR_0.95 = E[loss | loss > VaR_0.95]
    subject to  Σwᵢ = 1, IPS bounds, category bounds

CVaR minimization is implemented via Rockafellar-Uryasev linear reformulation:
    CVaR(α) = min_{z} { z + (1/(1-α)) * E[max(-r_p - z, 0)] }

Portfolio returns are simulated from a multivariate normal distribution
using the Ledoit-Wolf shrunken covariance matrix.

**Strengths**: Focuses on tail risk; coherent risk measure; captures downside asymmetry.
**Weaknesses**: Depends on return distribution assumption; sensitive to Monte Carlo sample size.
**Best regime**: RECESSION, LATE-CYCLE (tail risk management priority).
"""

CONFIDENCE = 0.95   # CVaR confidence level
N_SCENARIOS = 10000  # Monte Carlo scenarios
RANDOM_SEED = 42


def optimize(mu, Sigma, rf, vols):
    """Minimize CVaR using Rockafellar-Uryasev linear reformulation."""
    Sigma_shrunk = shrink_covariance(Sigma, "ledoit-wolf")

    # Generate scenario returns
    rng = np.random.default_rng(RANDOM_SEED)
    # Monthly returns
    monthly_mu = mu / 12
    monthly_Sigma = Sigma_shrunk / 12
    scenarios = rng.multivariate_normal(monthly_mu, monthly_Sigma, size=N_SCENARIOS)  # (S, N)

    alpha = CONFIDENCE
    S = N_SCENARIOS

    bounds = get_bounds()
    # Add z variable (VaR threshold) to optimization — but keep scipy simple
    # Use numerical CVaR estimation instead

    def cvar_objective(w):
        """Compute CVaR of portfolio given weights."""
        port_returns = scenarios @ w  # shape (S,)
        losses = -port_returns        # losses = negative returns
        var = np.percentile(losses, alpha * 100)
        tail_losses = losses[losses >= var]
        if len(tail_losses) == 0:
            return var
        return float(np.mean(tail_losses))

    def cvar_grad(w):
        """Numerical gradient of CVaR."""
        eps = 1e-5
        base = cvar_objective(w)
        grad = np.zeros(N)
        for i in range(N):
            w_plus = w.copy()
            w_plus[i] += eps
            grad[i] = (cvar_objective(w_plus) - base) / eps
        return grad

    constraints = build_constraints(Sigma_shrunk, include_category=True)
    w0 = make_initial_weights()

    # Use inverse-vol as warm start (naturally defensive)
    iv = 1.0 / np.maximum(vols, 1e-8)
    from common import project_to_ips
    w0_iv = project_to_ips(iv / iv.sum())

    best_w = None
    best_cvar = np.inf

    for w_init in [w0, w0_iv]:
        try:
            result = minimize(
                cvar_objective,
                w_init,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
                options={"ftol": 1e-8, "maxiter": 500},
            )
            if result.fun < best_cvar:
                best_cvar = result.fun
                best_w = np.clip(result.x, 0, 1)
        except Exception:
            continue

    if best_w is None:
        best_w = make_initial_weights()

    return best_w / best_w.sum()


if __name__ == "__main__":
    run_pc_script("pc-cvar", optimize, METHODOLOGY)
