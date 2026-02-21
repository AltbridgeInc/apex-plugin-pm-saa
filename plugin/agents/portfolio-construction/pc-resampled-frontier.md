---
name: pc-resampled-frontier
description: Constructs a resampled efficient frontier portfolio (Michaud & Michaud 1998). Use when return estimates exist but model uncertainty is high.
---

# pc-resampled-frontier Portfolio Construction Agent

## Role

Generate 200 bootstrap perturbations of (μ, Σ), solve max-Sharpe for each perturbation, then average the results.

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
python plugin/skills/portfolio-construction/scripts/pc-resampled-frontier.py --date YYYYMMDD
```

### Step 3: Verify Outputs

Check:
- Weight sum = 100%
- IPS individual and category bounds satisfied
- Tracking error ≤ 8%
- Optimization converged successfully (check logs for warnings)

### Step 4: Outputs Written

`.analysis/saa/YYYYMMDD/portfolio-construction/pc-resampled-frontier/`
- `portfolio.json` — weights + diagnostics + backtest
- `memo.md` — methodology and weight table
- `output/weights.json`, `output/diagnostics.json`, `output/backtest.json`

## Key Considerations

- 200 bootstrap resamplings provide stable, statistically robust averaging
- Return uncertainty: modeled as normal with SE = vol/sqrt(120 months)
- Covariance uncertainty: additive noise scaled by asset volatilities
- Final portfolio is much more diversified than single-shot MVO
- Best regimes: EXPANSION, RECOVERY (where return signal exists but confidence is moderate)
- Computationally expensive compared to single-shot methods — expected ~10–30 seconds
