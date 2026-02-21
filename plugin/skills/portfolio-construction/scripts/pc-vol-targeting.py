#!/usr/bin/env python3
"""
pc-vol-targeting.py — Volatility-Targeted portfolio construction.

Starts from an equal-weight baseline, then scales each asset's weight
to target a fixed portfolio volatility (10% annualized). Ensures the
portfolio stays within a risk budget regardless of market conditions.
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
## Volatility Targeting

Targets a specific portfolio volatility level (10% annualized):

    Step 1: Start from inverse-vol weights as baseline
    Step 2: Scale weights so portfolio vol = target vol (10%)
    Step 3: Project to IPS-feasible space

The target volatility is chosen to align with a typical institutional
moderate-risk mandate. In high-vol environments this reduces risk; in
low-vol environments it increases allocation to riskier assets.

Uses Ledoit-Wolf covariance shrinkage for stability.

**Strengths**: Explicit vol control; regime-adaptive exposure; simple concept.
**Weaknesses**: Ignores returns; may underperform in low-vol bull markets.
**Best regime**: LATE-CYCLE, RECESSION (risk reduction when vol spikes).
"""

TARGET_VOL = 0.10  # 10% annualized target volatility


def optimize(mu, Sigma, rf, vols):
    """Vol-targeted: inverse-vol baseline scaled to TARGET_VOL, then IPS projection."""
    Sigma_shrunk = shrink_covariance(Sigma, "ledoit-wolf")

    # Step 1: Inverse-vol baseline
    iv = 1.0 / np.maximum(vols, 1e-8)
    w_base = iv / iv.sum()

    # Step 2: Compute current portfolio vol
    current_vol = np.sqrt(w_base @ Sigma_shrunk @ w_base)

    # Step 3: Scale proportionally (but keep sum to 1 and add cash for excess)
    if current_vol > 1e-10:
        scale = TARGET_VOL / current_vol
        if scale < 1.0:
            # Reduce risky asset weights, add excess to cash (index 17)
            w_scaled = w_base * scale
            cash_add = 1.0 - w_scaled.sum()
            w_scaled[17] += cash_add
        else:
            # Can't leverage — keep as-is and optimize within bounds
            w_scaled = w_base.copy()
    else:
        w_scaled = w_base.copy()

    # Step 4: Project to IPS-feasible space
    return project_to_ips(w_scaled)


if __name__ == "__main__":
    run_pc_script("pc-vol-targeting", optimize, METHODOLOGY)
