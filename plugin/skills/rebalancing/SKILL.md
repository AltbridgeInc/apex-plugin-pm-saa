# Rebalancing Skill

## Overview

Monitors drift between a live portfolio and the target SAA (from CIO final-portfolio.json).
Triggers rebalancing alerts based on absolute drift, relative drift, IPS violations,
tracking error breaches, and category bounds breaches. Produces a trade list with
estimated transaction costs.

## Script

`skills/rebalancing/scripts/rebalancing-monitor.py`

## Dependencies

numpy, scipy, pandas (shared with portfolio-construction skill)

## Input Requirements

| Required | Source                                              | Contents                |
|----------|-----------------------------------------------------|-------------------------|
| Yes      | `.analysis/saa/YYYYMMDD/cio/final-portfolio.json`   | Target portfolio weights |
| Yes      | `--portfolio PATH` (CLI arg)                        | Current live portfolio  |
| Yes      | `.analysis/saa/YYYYMMDD/covariance/output/covariance-matrix.json` | TE calc |

## Live Portfolio Format

The `--portfolio` argument should point to a JSON file:
```json
{
  "date": "2026-02-20",
  "weights": {
    "us-large-cap": 0.28,
    "us-small-cap": 0.04,
    "intl-developed": 0.08,
    ...
  }
}
```

## Outputs

`.analysis/saa/YYYYMMDD/rebalancing/`
```
rebalancing-status.json    ← Machine-readable: triggers, trades, recommendation
rebalancing-report.md      ← Human-readable report with tables
```

---

## Rebalancing Triggers

| Trigger                   | Threshold        | Severity |
|---------------------------|------------------|----------|
| IPS individual violation  | Any breach       | CRITICAL |
| IPS category violation    | Any breach       | HIGH     |
| Tracking error breach     | > 8% vs benchmark| HIGH     |
| Absolute drift            | > 3% from target | MEDIUM   |
| Relative drift            | > 20% of target  | LOW      |

## Recommendations

| Recommendation        | Condition                                      | Timing          |
|-----------------------|------------------------------------------------|-----------------|
| IMMEDIATE_REBALANCE   | IPS violation (individual or category)         | Same day        |
| REBALANCE_RECOMMENDED | High severity trigger (TE breach, large drift) | Within 5 days   |
| REBALANCE_CONSIDER    | Medium severity trigger                        | Next review     |
| MONITOR               | Low severity trigger only                      | Watch closely   |
| NO_ACTION             | No triggers breached                           | Next scheduled  |

## Trade List

The monitor produces an ordered trade list showing:
- Asset class name
- Direction: BUY or SELL
- From weight (live) and to weight (target)
- Trade size as a percentage of portfolio
- Estimated transaction cost (10 bps one-way per unit traded)
- Total turnover and total estimated cost

## Running

```bash
# Compare target vs current live portfolio
python plugin/skills/rebalancing/scripts/rebalancing-monitor.py \
  --date 20260220 \
  --portfolio /path/to/live-portfolio.json

# Without live portfolio (compares target vs benchmark — useful for initial setup)
python plugin/skills/rebalancing/scripts/rebalancing-monitor.py --date 20260220
```

## Rebalancing Philosophy

The monitor uses a "tolerance band" approach:
- Small drift (< 3% absolute, < 20% relative) → monitor only
- Meaningful drift (> 3% absolute) → flag for consideration
- IPS violation → require immediate correction

Transaction costs (~10 bps per side) are estimated but the decision to rebalance
should weigh the cost of drift against the cost of trading. For institutional mandates,
IPS violations are always corrected regardless of cost.
