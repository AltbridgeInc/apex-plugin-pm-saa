---
name: pc-minimum-correlation
description: Constructs a minimum correlation portfolio. Use to find the most internally uncorrelated set of assets.
---

# minimum correlation Portfolio Construction Agent (title-case: Minimum Correlation)

## Role

Construct the minimum correlation portfolio using covariance and volatility inputs, then project
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
python plugin/skills/portfolio-construction/scripts/pc-minimum-correlation.py --date YYYYMMDD
```

### Step 3: Verify Outputs

Check:
- Weight sum = 100%
- All IPS bounds satisfied (individual and category)
- Tracking error vs benchmark reasonable (< 8%)

### Step 4: Outputs Written

`.analysis/saa/YYYYMMDD/portfolio-construction/pc-minimum-correlation/`
- `portfolio.json` — weights + diagnostics + backtest
- `memo.md` — methodology and weight table
- `output/weights.json`, `output/diagnostics.json`, `output/backtest.json`

## Key Considerations

- Minimizes wᵀCw where C is the correlation matrix (not covariance)
- Normalizes out individual volatility differences — focuses purely on correlation structure
- May hold high-vol assets if they are uncorrelated with everything else (e.g., commodities)
- Effective N by correlation is maximized with this method
- No return estimates required; correlation estimation only
