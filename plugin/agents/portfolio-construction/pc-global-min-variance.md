---
name: pc-global-min-variance
description: Constructs a global minimum variance portfolio. Use in RECESSION or LATE-CYCLE when minimizing risk is the primary objective.
---

# global min variance Portfolio Construction Agent (title-case: Global Min Variance)

## Role

Construct the global min variance portfolio using covariance and volatility inputs, then project
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
python plugin/skills/portfolio-construction/scripts/pc-global-min-variance.py --date YYYYMMDD
```

### Step 3: Verify Outputs

Check:
- Weight sum = 100%
- All IPS bounds satisfied (individual and category)
- Tracking error vs benchmark reasonable (< 8%)

### Step 4: Outputs Written

`.analysis/saa/YYYYMMDD/portfolio-construction/pc-global-min-variance/`
- `portfolio.json` — weights + diagnostics + backtest
- `memo.md` — methodology and weight table
- `output/weights.json`, `output/diagnostics.json`, `output/backtest.json`

## Key Considerations

- Requires no return estimates — purely covariance-based
- Sits at the leftmost tip of the efficient frontier
- Low-volatility anomaly: historically superior Sharpe to market cap weight
- IPS bounds prevent extreme concentration in lowest-vol assets (bonds/cash)
- Strongly preferred in RECESSION regime
