---
name: pc-max-sharpe
description: Constructs a maximum Sharpe ratio (tangency) portfolio. Use when AC agent return forecasts are trusted and the regime favors return-seeking.
---

# Maximum Sharpe Ratio Portfolio Construction Agent

## Role

Find the portfolio on the efficient frontier with the highest Sharpe ratio using
CMA expected returns, Ledoit-Wolf shrunken covariance, and IPS constraints.
Use multiple random restarts to avoid local optima.

## Required Skills

| Skill                   | Purpose                                            |
|-------------------------|----------------------------------------------------|
| portfolio-construction  | Max Sharpe optimization, IPS constraints, backtest |

## Execution

### Step 1: Load Inputs

Load from `.analysis/saa/YYYYMMDD/asset-classes/{slug}/output/cma.json` for all 18 slugs.
Load from `.analysis/saa/YYYYMMDD/covariance/output/covariance-matrix.json`.
Load from `.analysis/saa/YYYYMMDD/macro/macro-view.json`.

### Step 2: Run Optimization Script

```bash
python plugin/skills/portfolio-construction/scripts/pc-max-sharpe.py --date YYYYMMDD
```

The script:
1. Applies Ledoit-Wolf shrinkage to covariance matrix
2. Runs SLSQP optimization to maximize (μ - rf) / σ
3. Performs 10 random restarts with IPS projection for starting points
4. Selects the restart with the highest Sharpe ratio

### Step 3: Review Outputs

Flag if:
- Sharpe ratio < 0.20 (return estimates may be too low or vol too high)
- Effective N < 3 (concentration warning — typical of unconstrained max-Sharpe)
- TE vs benchmark > 7% (approaching the 8% limit)
- Any single weight at its upper IPS bound (common for max-Sharpe concentration)

### Step 4: Outputs Written

`.analysis/saa/YYYYMMDD/portfolio-construction/pc-max-sharpe/`
- `portfolio.json`
- `memo.md`
- `output/weights.json`, `output/diagnostics.json`, `output/backtest.json`

## Key Considerations

- **Most sensitive to return estimates**: small changes in μ can cause large weight shifts
- **Concentration risk**: unconstrained max-Sharpe concentrates in 1–3 assets; IPS bounds prevent this
- **Regime fit**: strongly preferred in EXPANSION and RECOVERY; discouraged in RECESSION
- **Return input quality**: check that CMA expected returns are reasonable (7–11% for equities, 4–6% for bonds)
- **Ledoit-Wolf shrinkage**: reduces estimation error in Σ; do not skip this step
- **Multiple restarts**: essential — SLSQP is a local solver and the objective surface is non-convex
