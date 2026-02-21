#!/usr/bin/env python3
"""
pc-market-cap-weight.py — Market-Cap Weighted portfolio construction.

Uses approximate market-cap proxies for each asset class, then projects
to IPS bounds. Reflects what a passive investor would hold.
"""

import sys
import numpy as np
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from common import run_pc_script, N, SLUGS, project_to_ips

METHODOLOGY = """
## Market-Cap Weight

Approximates global market-capitalization weights for each asset class.
Weights are based on approximate global investable market sizes (~2024 estimates).
This reflects what a purely passive, index-tracking investor would hold.

After computing raw market-cap proportional weights, they are projected to
the IPS-feasible space to satisfy mandate constraints.

**Strengths**: Theoretically optimal under CAPM; low turnover; broad acceptance.
**Weaknesses**: Momentum-driven (overweights recent winners); ignores valuations.
**Best regime**: EXPANSION (momentum-friendly environments).
"""

# Approximate global market-cap weights by asset class (proxy, sums to ~1 before normalization)
# Based on approx. global investable market 2024: ~$100T equities, ~$130T bonds
MARKET_CAP_PROXIES = {
    "us-large-cap":          0.200,
    "us-small-cap":          0.035,
    "us-value":              0.060,
    "us-growth":             0.060,
    "intl-developed":        0.135,
    "emerging-markets":      0.055,
    "short-treasury":        0.070,
    "interm-treasury":       0.085,
    "long-treasury":         0.040,
    "ig-corps":              0.090,
    "hy-corps":              0.025,
    "intl-sovereign-bonds":  0.055,
    "intl-corps":            0.030,
    "usd-em-debt":           0.025,
    "reits":                 0.015,
    "gold":                  0.008,
    "commodities":           0.007,
    "cash":                  0.005,
}


def optimize(mu, Sigma, rf, vols):
    """Market cap weighted: use proxy weights, normalize, project to IPS."""
    raw = np.array([MARKET_CAP_PROXIES[slug] for slug in SLUGS])
    raw = raw / raw.sum()
    return project_to_ips(raw)


if __name__ == "__main__":
    run_pc_script("pc-market-cap-weight", optimize, METHODOLOGY)
