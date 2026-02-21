---
name: pc-max-drawdown-constrained
description: Constructs a max-Sharpe portfolio with explicit maximum drawdown constraint (≤25%). Use in LATE-CYCLE or RECESSION when drawdown control is a mandate.
---

# pc-max-drawdown-constrained Portfolio Construction Agent

## Role

Maximize Sharpe ratio subject to a soft penalty constraint that limits simulated 5-year maximum drawdown to 25%. Uses Monte Carlo for MDD estimation.

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
python plugin/skills/portfolio-construction/scripts/pc-max-drawdown-constrained.py --date YYYYMMDD
```

### Step 3: Verify Outputs

Check:
- Weight sum = 100%
- IPS individual and category bounds satisfied
- Tracking error ≤ 8%
- Optimization converged successfully (check logs for warnings)

### Step 4: Outputs Written

`.analysis/saa/YYYYMMDD/portfolio-construction/pc-max-drawdown-constrained/`
- `portfolio.json` — weights + diagnostics + backtest
- `memo.md` — methodology and weight table
- `output/weights.json`, `output/diagnostics.json`, `output/backtest.json`

## Key Considerations

- MDD constraint is soft (penalty-based) — optimizer balances Sharpe vs drawdown
- Monte Carlo with 2,000 paths over 5-year horizon estimates expected MDD
- Computationally moderate — MDD cache prevents redundant computations
- Results in portfolios with both good risk-adjusted return AND controlled tail losses
- IPS projection applied after optimization
- Best regimes: LATE-CYCLE, RECESSION
