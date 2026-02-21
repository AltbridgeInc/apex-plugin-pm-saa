---
name: pc-mean-downside-risk
description: Constructs a mean-downside risk (Sortino-optimal) portfolio. Use when upside variance should not be penalized.
---

# pc-mean-downside-risk Portfolio Construction Agent

## Role

Maximize the Sortino ratio using Monte Carlo scenarios (8,000 paths). Penalizes only returns below the risk-free rate (MAR), not upside variance.

## Required Skills

| Skill                   | Purpose                                            |
|-------------------------|----------------------------------------------------|
| portfolio-construction  | Optimization, IPS constraints, backtest, outputs   |

## Execution

### Step 1: Load Inputs

- `.analysis/saa/YYYYMMDD/asset-classes/{slug}/output/cma.json` for all 18 slugs
- `.analysis/saa/YYYYMMDD/covariance/output/covariance-matrix.json`
- `.analysis/saa/YYYYMMDD/macro/macro-view.json`

### Step 2: Run Script

```bash
python plugin/skills/portfolio-construction/scripts/pc-mean-downside-risk.py --date YYYYMMDD
```

### Step 3: Verify Outputs

Check:
- Weight sum = 100%
- IPS individual and category bounds satisfied
- Tracking error ≤ 8%
- Optimization converged successfully (check logs for warnings)

### Step 4: Outputs Written

`.analysis/saa/YYYYMMDD/portfolio-construction/pc-mean-downside-risk/`
- `portfolio.json` — weights + diagnostics + backtest
- `memo.md` — methodology and weight table
- `output/weights.json`, `output/diagnostics.json`, `output/backtest.json`

## Key Considerations

- Sortino = (E[r_p] - MAR) / σ_downside where σ_downside captures semi-deviation only
- Does not penalize upside volatility — appropriate for asymmetric-return investors
- Monte Carlo (8,000 paths) provides a reasonable estimate of semi-deviation
- Less conservative than CVaR — maintains more equity exposure
- Best regimes: EXPANSION, RECOVERY (when capturing upside matters)
