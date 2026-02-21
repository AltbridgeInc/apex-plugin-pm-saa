---
name: pc-max-diversification
description: Constructs a maximum diversification ratio portfolio. Use to maximize the diversification benefit captured from combining assets.
---

# max diversification Portfolio Construction Agent (title-case: Max Diversification)

## Role

Construct the max diversification portfolio using covariance and volatility inputs, then project
to the IPS-feasible space. No expected return inputs are required for this method.

## Required Skills

| Skill                   | Purpose                                            |
|-------------------------|----------------------------------------------------|
| portfolio-construction  | Optimization, IPS constraints, backtest, outputs   |

## Execution

### Step 1: Load Inputs

- `.analysis/saa/YYYYMMDD/asset-classes/{slug}/output/cma.json` — for rf and diagnostics
- `.analysis/saa/YYYYMMDD/covariance/output/covariance-matrix.json`
- `.analysis/saa/YYYYMMDD/macro/macro-view.json`

### Step 2: Run Script

```bash
python plugin/skills/portfolio-construction/scripts/pc-max-diversification.py --date YYYYMMDD
```

### Step 3: Verify Outputs

Check:
- Weight sum = 100%
- All IPS bounds satisfied (individual and category)
- Tracking error vs benchmark reasonable (< 8%)

### Step 4: Outputs Written

`.analysis/saa/YYYYMMDD/portfolio-construction/pc-max-diversification/`
- `portfolio.json` — weights + diagnostics + backtest
- `memo.md` — methodology and weight table
- `output/weights.json`, `output/diagnostics.json`, `output/backtest.json`

## Key Considerations

- Diversification Ratio = weighted-avg-vol / portfolio-vol; higher is better
- Uses multiple restarts; non-convex objective
- Results in well-diversified portfolios without requiring return estimates
- Correlation-aware: rewards assets that are uncorrelated with the portfolio
- Good across all regimes; especially useful when correlation structure is well-estimated
