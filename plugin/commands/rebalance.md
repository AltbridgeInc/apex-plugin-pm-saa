---
description: "Monitor rebalancing needs by comparing live portfolio against target SAA"
argument-hint: "[--date YYYYMMDD] [--portfolio PATH]"
---

# Rebalance Command

Compare a live portfolio against the target SAA and produce rebalancing recommendations.

## Usage

```
/project:rebalance [--date YYYYMMDD] [--portfolio PATH]
```

### Arguments

- `--date YYYYMMDD`: Date folder for target portfolio lookup. Defaults to today.
- `--portfolio PATH`: Path to JSON file containing current live portfolio weights.

## Prerequisites

- `.analysis/saa/YYYYMMDD/cio/final-portfolio.json` — target portfolio (run `recommend` first)
- `--portfolio PATH` — live portfolio JSON (see format below)

## Live Portfolio Format

```json
{
  "date": "2026-02-20",
  "weights": {
    "us-large-cap": 0.28,
    "us-small-cap": 0.04,
    "us-value": 0.03,
    "us-growth": 0.04,
    "intl-developed": 0.09,
    "emerging-markets": 0.05,
    "short-treasury": 0.02,
    "interm-treasury": 0.12,
    "long-treasury": 0.04,
    "ig-corps": 0.08,
    "hy-corps": 0.03,
    "intl-sovereign-bonds": 0.04,
    "intl-corps": 0.02,
    "usd-em-debt": 0.02,
    "reits": 0.04,
    "gold": 0.03,
    "commodities": 0.02,
    "cash": 0.05
  }
}
```

## Execution

```bash
python plugin/skills/rebalancing/scripts/rebalancing-monitor.py \
  --date YYYYMMDD \
  --portfolio /path/to/live-portfolio.json
```

If no `--portfolio` is provided, the monitor compares the target vs the 60/40 benchmark
(useful for understanding total drift since SAA inception).

## Outputs

`.analysis/saa/YYYYMMDD/rebalancing/`
```
rebalancing-status.json    ← Structured: triggers, trades, recommendation
rebalancing-report.md      ← Human-readable drift report and trade list
```

## Recommendation Levels

| Level                   | Condition                            | Action                 |
|-------------------------|--------------------------------------|------------------------|
| IMMEDIATE_REBALANCE     | IPS violation (any asset)            | Same day               |
| REBALANCE_RECOMMENDED   | TE > 8% or large absolute drift      | Within 5 business days |
| REBALANCE_CONSIDER      | Moderate drift (> 3%)                | At next review         |
| MONITOR                 | Small drift only                     | Watch closely          |
| NO_ACTION               | All within tolerance                 | Next scheduled review  |
