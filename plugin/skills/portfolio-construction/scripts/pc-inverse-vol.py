#!/usr/bin/env python3
"""
pc-inverse-vol.py — Inverse Volatility weighted portfolio construction.

Allocates more weight to lower-volatility assets. Uses diagonal of
covariance matrix (individual vols). Projects to IPS space.
"""

import sys
import numpy as np
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from common import run_pc_script, N, project_to_ips

METHODOLOGY = """
## Inverse Volatility

Inverse volatility (IV) weighting assigns weights proportional to 1/σ_i,
where σ_i is the annualized volatility of asset class i.
This equalizes the nominal (not risk-contribution) exposure across assets.

Only uses the diagonal of the covariance matrix — correlation is ignored.
Simple and requires no optimization solver.

**Strengths**: Very simple; reduces exposure to high-vol assets; robust to estimation error.
**Weaknesses**: Ignores correlations; ignores expected returns; still concentrates in bond-heavy portfolios.
**Best regime**: LATE-CYCLE, RECESSION (defensive tilt toward lower-vol assets like bonds).
"""


def optimize(mu, Sigma, rf, vols):
    """Inverse volatility: w_i ∝ 1/σ_i."""
    iv = 1.0 / np.maximum(vols, 1e-8)
    raw = iv / iv.sum()
    return project_to_ips(raw)


if __name__ == "__main__":
    run_pc_script("pc-inverse-vol", optimize, METHODOLOGY)
