---
name: pc-cvar
description: Constructs a CVaR (Conditional Value at Risk / Expected Shortfall) minimizing portfolio. Use in RECESSION when tail risk management is paramount.
---

# pc-cvar Portfolio Construction Agent

## Role

Minimize the 95% Expected Shortfall of the portfolio using Monte Carlo simulation (10,000 scenarios from multivariate normal). Uses Rockafellar-Uryasev framework.

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
python plugin/skills/portfolio-construction/scripts/pc-cvar.py --date YYYYMMDD
```

### Step 3: Verify Outputs

Check:
- Weight sum = 100%
- IPS individual and category bounds satisfied
- Tracking error ≤ 8%
- Optimization converged successfully (check logs for warnings)

### Step 4: Outputs Written

`.analysis/saa/YYYYMMDD/portfolio-construction/pc-cvar/`
- `portfolio.json` — weights + diagnostics + backtest
- `memo.md` — methodology and weight table
- `output/weights.json`, `output/diagnostics.json`, `output/backtest.json`

## Key Considerations

- CVaR is a coherent risk measure (unlike VaR); CVaR minimization produces risk-efficient portfolios
- Computationally intensive — Monte Carlo with 10,000 scenarios
- Result depends on distributional assumption (multivariate normal used here)
- Strongly defensive: tilts toward short-duration bonds and cash
- IPS equity minimum (30%) prevents complete flight from equities
- Best regime: RECESSION
