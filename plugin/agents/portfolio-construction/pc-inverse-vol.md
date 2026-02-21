---
name: pc-inverse-vol
description: Constructs a inverse volatility weighting. Use as a simple risk-reduction approach that weights lower-vol assets more.
---

# Inverse Volatility Portfolio Construction Agent

## Role

Weight each asset class proportionally to 1/σ_i (inverse of individual volatility), then project to IPS space.

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
python plugin/skills/portfolio-construction/scripts/pc-inverse-vol.py --date YYYYMMDD
```

### Step 3: Verify Outputs

Check:
- Weight sum = 100%
- IPS individual bounds satisfied
- IPS category bounds satisfied (especially equity 30–75%)

### Step 4: Outputs Written

`.analysis/saa/YYYYMMDD/portfolio-construction/pc-inverse-vol/`
- `portfolio.json` — weights + diagnostics + backtest
- `memo.md` — methodology and weight table
- `output/weights.json`, `output/diagnostics.json`, `output/backtest.json`

## Key Considerations

- Only uses the diagonal of the covariance matrix — cross-asset correlations are ignored
- Naturally overweights fixed income (low vol) and underweights equities (high vol)
- Requires IPS minimum equity constraint (us-large-cap ≥ 10%) to prevent equity starvation
- More defensive than equal-weight; appropriate in LATE-CYCLE and RECESSION regimes
- Does not require a covariance matrix inversion — numerically very stable
