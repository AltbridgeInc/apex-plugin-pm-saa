#!/usr/bin/env python3
"""
pc-resampled-frontier.py — Resampled Efficient Frontier (Michaud & Michaud).

Generates multiple perturbed return/covariance estimates, runs MVO on each,
and averages the resulting frontier portfolios. Reduces estimation error
by averaging over many plausible input scenarios.
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
## Resampled Efficient Frontier (Michaud & Michaud, 1998)

Instead of trusting a single estimate of μ and Σ, the resampled frontier:

1. **Perturbs inputs**: Generate R bootstrap samples of (μ_r, Σ_r) from the
   multivariate distribution of estimation error
2. **Optimizes each**: For each sample, solve for the max-Sharpe portfolio
   (target point on frontier) subject to IPS constraints
3. **Averages weights**: The final portfolio = mean of the R optimal portfolios

This produces a smoother, more stable allocation that hedges against estimation
uncertainty by averaging across many plausible input scenarios.

R = 200 resamplings are used (tradeoff between stability and compute time).

**Strengths**: Dramatically more stable than single-shot MVO; robust to estimation error.
**Weaknesses**: Computationally expensive; result depends on bootstrap methodology.
**Best regime**: EXPANSION, RECOVERY (when return signal exists but confidence is moderate).
"""

N_RESAMPLINGS = 200
RANDOM_SEED = 42


def _max_sharpe_simple(mu_r, Sigma_r, rf, bounds, constraints):
    """Quick max-Sharpe solve for one resampling."""
    w0 = make_initial_weights()

    def neg_sharpe(w):
        port_ret = w @ mu_r
        port_vol = np.sqrt(np.maximum(w @ Sigma_r @ w, 1e-12))
        return -(port_ret - rf) / port_vol

    try:
        result = minimize(
            neg_sharpe,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-9, "maxiter": 500},
        )
        w = np.clip(result.x, 0, 1)
        s = w.sum()
        if s > 0:
            return w / s
    except Exception:
        pass
    return w0


def optimize(mu, Sigma, rf, vols):
    """Resampled frontier: bootstrap μ and Σ, average max-Sharpe portfolios."""
    Sigma_shrunk = shrink_covariance(Sigma, "ledoit-wolf")
    rng = np.random.default_rng(RANDOM_SEED)

    bounds = get_bounds()
    constraints = build_constraints(Sigma_shrunk, include_category=True)

    # Estimate uncertainty in mu: assume standard error ~ vol / sqrt(T), T=120 months
    T_est = 120
    mu_se = vols / np.sqrt(T_est)

    # Wishart-distributed covariance uncertainty (simplified: perturb Sigma)
    all_weights = []

    for r in range(N_RESAMPLINGS):
        # Perturb return estimates
        mu_r = rng.normal(mu, mu_se)

        # Perturb covariance (simplified Wishart perturbation)
        noise_scale = 0.05
        perturb = rng.normal(0, noise_scale, size=(N, N))
        perturb = (perturb + perturb.T) / 2  # symmetric
        Sigma_r = Sigma_shrunk + perturb * np.sqrt(np.diag(Sigma_shrunk)[:, None] * np.diag(Sigma_shrunk)[None, :])

        # Ensure PSD
        eigvals = np.linalg.eigvalsh(Sigma_r)
        if eigvals.min() < 1e-8:
            Sigma_r += (abs(eigvals.min()) + 1e-8) * np.eye(N)

        w_r = _max_sharpe_simple(mu_r, Sigma_r, rf, bounds, constraints)
        all_weights.append(w_r)

    # Average across all resamplings
    W = np.array(all_weights)  # (R, N)
    w_avg = np.mean(W, axis=0)
    w_avg = np.clip(w_avg, 0, 1)
    w_avg = w_avg / w_avg.sum()

    return project_to_ips(w_avg)


if __name__ == "__main__":
    run_pc_script("pc-resampled-frontier", optimize, METHODOLOGY)
