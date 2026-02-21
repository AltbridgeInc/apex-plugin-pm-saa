---
name: pc-inverse-variance
description: Constructs a inverse variance weighting (1/σ²). Gives stronger downweight to volatile assets than inverse-vol.
---

# Inverse Variance Portfolio Construction Agent

## Role

Weight each asset class proportionally to 1/σ²_i, the inverse of individual variance, then project to IPS space.

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
python plugin/skills/portfolio-construction/scripts/pc-inverse-variance.py --date YYYYMMDD
```

### Step 3: Verify Outputs

Check:
- Weight sum = 100%
- IPS individual bounds satisfied
- IPS category bounds satisfied (especially equity 30–75%)

### Step 4: Outputs Written

`.analysis/saa/YYYYMMDD/portfolio-construction/pc-inverse-variance/`
- `portfolio.json` — weights + diagnostics + backtest
- `memo.md` — methodology and weight table
- `output/weights.json`, `output/diagnostics.json`, `output/backtest.json`

## Key Considerations

- Stronger defensive tilt than inverse-vol; even lower effective equity weight before IPS projection
- Analytically optimal when all assets have zero pairwise correlation
- Very robust to correlation estimation error precisely because it ignores correlations
- IPS equity minimum (us-large-cap ≥ 10%) is typically binding with this method
- Recommended for RECESSION regime as a defensive anchor
