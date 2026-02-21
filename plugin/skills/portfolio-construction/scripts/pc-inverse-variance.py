#!/usr/bin/env python3
"""
pc-inverse-variance.py — Inverse Variance weighted portfolio construction.

Similar to inverse-vol but uses 1/σ² (variance) instead of 1/σ.
Gives stronger downweight to high-variance assets.
"""

import sys
import numpy as np
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from common import run_pc_script, N, project_to_ips

METHODOLOGY = """
## Inverse Variance

Inverse variance (IV²) weighting assigns weights proportional to 1/σ²_i.
Compared to inverse-vol, this gives a stronger downweight to volatile assets.

This method is the closed-form optimal solution for minimizing portfolio
variance when all assets have zero correlation — making it a useful
approximation when cross-asset correlations are small or uncertain.

**Strengths**: Analytically optimal for zero-correlation case; simple; defensive.
**Weaknesses**: Same as inverse-vol plus ignores correlations even more aggressively.
**Best regime**: RECESSION, LATE-CYCLE (strong defensive tilt).
"""


def optimize(mu, Sigma, rf, vols):
    """Inverse variance: w_i ∝ 1/σ²_i."""
    variance = vols ** 2
    iv2 = 1.0 / np.maximum(variance, 1e-10)
    raw = iv2 / iv2.sum()
    return project_to_ips(raw)


if __name__ == "__main__":
    run_pc_script("pc-inverse-variance", optimize, METHODOLOGY)
