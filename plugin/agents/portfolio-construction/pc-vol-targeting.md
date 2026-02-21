---
name: pc-vol-targeting
description: Constructs a volatility-targeted portfolio (10% annual vol target). Use when explicit risk budgeting is required.
---

# vol targeting Portfolio Construction Agent (title-case: Vol Targeting)

## Role

Construct the vol targeting portfolio using covariance and volatility inputs, then project
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
python plugin/skills/portfolio-construction/scripts/pc-vol-targeting.py --date YYYYMMDD
```

### Step 3: Verify Outputs

Check:
- Weight sum = 100%
- All IPS bounds satisfied (individual and category)
- Tracking error vs benchmark reasonable (< 8%)

### Step 4: Outputs Written

`.analysis/saa/YYYYMMDD/portfolio-construction/pc-vol-targeting/`
- `portfolio.json` — weights + diagnostics + backtest
- `memo.md` — methodology and weight table
- `output/weights.json`, `output/diagnostics.json`, `output/backtest.json`

## Key Considerations

- Targets 10% annualized portfolio volatility
- When current vol exceeds target, reduces risky weights and increases cash
- Cannot leverage — does not increase exposure above 1x
- Cash (index 17) acts as the buffer asset
- In high-volatility environments (RECESSION), this produces the most defensive allocation
- Vol-targeting is regime-adaptive: same algorithm produces different portfolios as vol changes
