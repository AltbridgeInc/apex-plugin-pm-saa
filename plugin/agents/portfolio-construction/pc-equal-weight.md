---
name: pc-equal-weight
description: Constructs a equal weight (1/N) across all 18 asset classes. Use as the simplest diversification baseline.
---

# Equal Weight (1/N) Portfolio Construction Agent

## Role

Assign equal weight to each of the 18 asset classes before projecting to the IPS-feasible space.

## Required Skills

| Skill                   | Purpose                                            |
|-------------------------|----------------------------------------------------|
| portfolio-construction  | IPS bounds, common utilities, output writers       |

## Execution

### Step 1: Load Inputs

- `.analysis/saa/YYYYMMDD/asset-classes/{slug}/output/cma.json` for all 18 slugs
- `.analysis/saa/YYYYMMDD/covariance/output/covariance-matrix.json`
- `.analysis/saa/YYYYMMDD/macro/macro-view.json`

### Step 2: Run Script

```bash
python plugin/skills/portfolio-construction/scripts/pc-equal-weight.py --date YYYYMMDD
```

### Step 3: Verify Outputs

Check:
- Weight sum = 100%
- IPS individual bounds satisfied
- IPS category bounds satisfied (especially equity 30–75%)

### Step 4: Outputs Written

`.analysis/saa/YYYYMMDD/portfolio-construction/pc-equal-weight/`
- `portfolio.json` — weights + diagnostics + backtest
- `memo.md` — methodology and weight table
- `output/weights.json`, `output/diagnostics.json`, `output/backtest.json`

## Key Considerations

- Strongest possible diversification by weight count (effective N = 18 before IPS projection)
- IPS minimums (us-large-cap ≥ 10%, intl-developed ≥ 5%) will pull weight from equal distribution
- Consistently beats optimized portfolios out-of-sample due to estimation error immunity
- In ensembles, acts as a stabilizing anchor — especially useful when model confidence is low
- Best ensemble weight: should receive higher weight in RECOVERY and RECESSION when model signal is uncertain
