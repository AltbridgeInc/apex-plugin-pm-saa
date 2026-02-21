---
name: pc-market-cap-weight
description: Constructs a market-capitalization-weighted portfolio. Use for a passive baseline that reflects global investable market structure.
---

# Market-Cap Weight Portfolio Construction Agent

## Role

Construct a portfolio using approximate global market-capitalization weights for all 18 asset
classes, projected to the IPS-feasible space. This serves as the passive "what the world owns"
benchmark.

## Required Skills

| Skill                   | Purpose                                            |
|-------------------------|----------------------------------------------------|
| portfolio-construction  | IPS bounds, common utilities, output writers       |

## Execution

### Step 1: Load Inputs

Read expected returns and covariance for context (not used in optimization):
- `.analysis/saa/YYYYMMDD/asset-classes/{slug}/output/cma.json` for all 18 slugs
- `.analysis/saa/YYYYMMDD/covariance/output/covariance-matrix.json`
- `.analysis/saa/YYYYMMDD/macro/macro-view.json`

### Step 2: Run Script

```bash
python plugin/skills/portfolio-construction/scripts/pc-market-cap-weight.py --date YYYYMMDD
```

Uses hardcoded proxy market-cap weights, normalizes, then projects to IPS bounds.

### Step 3: Review Outputs

Verify:
- Sum of weights = 100%
- us-large-cap between 10–40%
- intl-developed between 5–25%
- IPS compliance = true

### Step 4: Outputs Written

`.analysis/saa/YYYYMMDD/portfolio-construction/pc-market-cap-weight/`
- `portfolio.json` — weights + diagnostics + backtest
- `memo.md` — methodology and weight table
- `output/weights.json`, `output/diagnostics.json`, `output/backtest.json`

## Key Considerations

- This method requires no return or covariance estimation — immune to estimation error
- IPS projection will shift weights: us-large-cap minimum (10%) forces some weight away from global market cap
- Best used as: ensemble anchor, diversification reference, and performance attribution baseline
- In EXPANSION regimes, market-cap weight tends to have momentum exposure (recent winners overweighted)
- Expected Tracking Error vs 60/40 benchmark: low-to-moderate (both are passive-tilted)
