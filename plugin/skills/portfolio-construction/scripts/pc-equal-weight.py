#!/usr/bin/env python3
"""
pc-equal-weight.py — Equal Weight (1/N) portfolio construction.

Each asset receives weight 1/N before applying IPS bounds projection.
Robust to estimation error; acts as a strong diversification baseline.
"""

import sys
import numpy as np
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from common import run_pc_script, N, project_to_ips

METHODOLOGY = """
## Equal Weight (1/N)

Equal weighting assigns 1/N to each of the N asset classes before projecting
to the IPS-feasible space. This method makes no assumptions about returns or
covariances and is known to be surprisingly competitive with optimized portfolios
due to its immunity to estimation error.

**Strengths**: Maximum simplicity, high robustness, strong diversification baseline.
**Weaknesses**: Ignores return and risk information; over-weights small/illiquid classes.
**Best regime**: All regimes (especially useful as ensemble anchor).
"""


def optimize(mu, Sigma, rf, vols):
    """Equal weight: 1/N for all assets, then project to IPS."""
    raw = np.full(N, 1.0 / N)
    return project_to_ips(raw)


if __name__ == "__main__":
    run_pc_script("pc-equal-weight", optimize, METHODOLOGY)
