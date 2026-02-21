#!/usr/bin/env python3
"""
pc-mean-downside-risk.py — Mean-Downside Risk (Sortino-optimal) portfolio.

Maximizes the Sortino ratio by penalizing only downside volatility below
a Minimum Acceptable Return (MAR). Does not penalize upside variance.
"""

import sys
import numpy as np
from scipy.optimize import minimize
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from common import (
    run_pc_script, N, build_constraints, get_bounds,
    make_initial_weights, shrink_covariance, DEFAULT_RF
)

METHODOLOGY = """
## Mean-Downside Risk (Sortino-Optimal Portfolio)

Maximizes the Sortino ratio, which uses downside deviation instead of
total volatility in the denominator:

    maximize  (μ_p - MAR) / σ_downside
    subject to  Σwᵢ = 1, IPS bounds, category bounds

where:
- MAR = Minimum Acceptable Return (= risk-free rate)
- σ_downside = √(E[max(MAR - r_p, 0)²]) — semi-deviation

Portfolio returns are simulated from multivariate normal to estimate
downside deviation numerically.

Unlike mean-variance, this method does not penalize upside variance
("good volatility"), making it preferred by asymmetric-return-seeking investors.

**Strengths**: Asymmetric risk metric; rewards upside; intuitive for drawdown-sensitive investors.
**Weaknesses**: More sensitive to tail distribution assumptions; noisier estimate with finite samples.
**Best regime**: EXPANSION, RECOVERY (when capturing upside is valued).
"""

N_SCENARIOS = 8000
RANDOM_SEED = 99


def optimize(mu, Sigma, rf, vols):
    """Maximize Sortino ratio using simulated scenarios."""
    Sigma_shrunk = shrink_covariance(Sigma, "ledoit-wolf")

    rng = np.random.default_rng(RANDOM_SEED)
    monthly_mu = mu / 12
    monthly_Sigma = Sigma_shrunk / 12
    scenarios = rng.multivariate_normal(monthly_mu, monthly_Sigma, size=N_SCENARIOS)

    mar = rf / 12  # Monthly MAR = monthly risk-free rate

    def neg_sortino(w):
        port_returns = scenarios @ w
        ann_return = np.mean(port_returns) * 12
        shortfalls = np.minimum(port_returns - mar, 0)
        downside_var = np.mean(shortfalls ** 2) * 12
        downside_std = np.sqrt(downside_var)
        if downside_std < 1e-10:
            return -10.0  # Very good — no downside
        return -(ann_return - rf) / downside_std

    bounds = get_bounds()
    constraints = build_constraints(Sigma_shrunk, include_category=True)

    best_w = None
    best_obj = np.inf

    rng2 = np.random.default_rng(42)
    starts = [make_initial_weights()]
    for _ in range(3):
        from common import project_to_ips
        starts.append(project_to_ips(rng2.dirichlet(np.ones(N))))

    for w0 in starts:
        try:
            result = minimize(
                neg_sortino,
                w0,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
                options={"ftol": 1e-8, "maxiter": 500},
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
    run_pc_script("pc-mean-downside-risk", optimize, METHODOLOGY)
