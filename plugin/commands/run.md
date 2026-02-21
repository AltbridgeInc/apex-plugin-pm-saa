---
description: "Run the full SAA strategy pipeline: construct all methods → recommend → risk"
argument-hint: "[--date YYYYMMDD]"
---

# Run Command

Execute the full SAA strategy pipeline end-to-end for a given date.

## Usage

```
/project:run [--date YYYYMMDD]
```

### Arguments

- `--date YYYYMMDD`: Date folder to process. Defaults to today.

## Pipeline Steps

```
1. construct (all 16 methods)
     ↓
2. recommend (CIO ensemble → final-portfolio.json)
     ↓
3. risk (stress tests + factor analysis on final portfolio)
```

## Prerequisites

All inputs from `apex-plugin-analysis-assetclass` must exist:
- `.analysis/saa/YYYYMMDD/asset-classes/{slug}/output/cma.json` for all 18 slugs
- `.analysis/saa/YYYYMMDD/covariance/output/covariance-matrix.json`
- `.analysis/saa/YYYYMMDD/macro/macro-view.json`

If these don't exist, run `apex-plugin-analysis-assetclass` first.

## Execution

```bash
DATE=20260220

# Step 1: Run all 16 portfolio construction methods
for method in market-cap-weight equal-weight inverse-vol inverse-variance \
              max-sharpe risk-parity global-min-variance max-diversification \
              vol-targeting minimum-correlation hierarchical-risk-parity \
              robust-mean-variance cvar mean-downside-risk resampled-frontier \
              max-drawdown-constrained; do
    python plugin/skills/portfolio-construction/scripts/pc-${method}.py --date ${DATE}
done

# Step 2: CIO ensemble analysis
python plugin/skills/ensemble-methods/scripts/cio-analysis.py --date ${DATE}

# Step 3: Risk analysis
python plugin/skills/risk-management/scripts/risk-analysis.py --date ${DATE}
```

## Complete Output Structure After `run`

```
.analysis/saa/YYYYMMDD/
├── portfolio-construction/
│   ├── pc-market-cap-weight/
│   │   ├── portfolio.json
│   │   ├── memo.md
│   │   └── output/{weights.json, diagnostics.json, backtest.json}
│   ├── pc-equal-weight/        (same structure)
│   ├── pc-inverse-vol/         (same structure)
│   ├── ... (13 more methods)
│   └── pc-max-drawdown-constrained/
├── cio/
│   ├── final-portfolio.json     ← PRIMARY OUTPUT
│   ├── method-scores.json
│   ├── ensemble-portfolios.json
│   ├── cio-recommendation.md
│   └── board-memo.md
└── risk-analysis/
    ├── risk-analysis.json
    └── risk-report.md
```

## Estimated Total Runtime

| Component              | Estimated Time  |
|------------------------|-----------------|
| Fast PC methods (5)    | 10–20 seconds   |
| Optimization PC (7)    | 60–120 seconds  |
| Monte Carlo PC (3)     | 3–6 minutes     |
| Resampled frontier (1) | 2–4 minutes     |
| CIO ensemble           | 30–60 seconds   |
| Risk analysis          | 30–60 seconds   |
| **Total**              | **~8–12 minutes** |

## Post-Run Actions

After `run` completes:
1. Review `cio/board-memo.md` for the executive summary
2. Review `cio/cio-recommendation.md` for full analysis
3. Review `risk-analysis/risk-report.md` for stress test results
4. If implementing: run `rebalance --portfolio /path/to/live-portfolio.json` to get trade list
