---
name: pc-robust-mean-variance
description: Constructs a robust mean-variance portfolio with James-Stein return shrinkage. Use when return estimates are available but uncertainty is high.
---

# pc-robust-mean-variance Portfolio Construction Agent

## Role

Apply James-Stein shrinkage to expected returns (toward grand mean, α=0.5) and Ledoit-Wolf shrinkage to Σ, then solve maximum Sharpe optimization.

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
python plugin/skills/portfolio-construction/scripts/pc-robust-mean-variance.py --date YYYYMMDD
```

### Step 3: Verify Outputs

Check:
- Weight sum = 100%
- IPS individual and category bounds satisfied
- Tracking error ≤ 8%
- Optimization converged successfully (check logs for warnings)

### Step 4: Outputs Written

`.analysis/saa/YYYYMMDD/portfolio-construction/pc-robust-mean-variance/`
- `portfolio.json` — weights + diagnostics + backtest
- `memo.md` — methodology and weight table
- `output/weights.json`, `output/diagnostics.json`, `output/backtest.json`

## Key Considerations

- James-Stein shrinkage: μ_robust = 0.5 × μ + 0.5 × μ_bar where μ_bar is cross-sectional mean
- This moderates extreme return differences between asset classes
- Ledoit-Wolf on covariance ensures numerical stability
- Produces more diversified portfolios than raw max-Sharpe
- Suitable in EXPANSION and LATE-CYCLE (moderate trust in return estimates)
