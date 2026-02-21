---
description: "Run portfolio construction methods to generate SAA portfolio proposals"
argument-hint: "[METHOD|all] [--date YYYYMMDD]"
---

# Construct Command

Run one or all 16 portfolio construction methods on the analysis-assetclass outputs.

## Usage

```
/project:construct [METHOD] [--date YYYYMMDD]
```

### Arguments

- `METHOD` (optional): Name of a specific PC method (e.g., `pc-max-sharpe`, `pc-risk-parity`)
  Use `all` or omit to run all 16 methods.
- `--date YYYYMMDD`: Override the date folder. Defaults to today.

## Prerequisites

The following must exist before running:
- `.analysis/saa/YYYYMMDD/asset-classes/{slug}/output/cma.json` for all 18 slugs
- `.analysis/saa/YYYYMMDD/covariance/output/covariance-matrix.json`

These are produced by `apex-plugin-analysis-assetclass`. If they don't exist, run that plugin first.

## Execution

### Single Method

```bash
python plugin/skills/portfolio-construction/scripts/pc-max-sharpe.py --date YYYYMMDD
```

### All 16 Methods

Run each script sequentially (or in parallel if compute allows):

```bash
for method in market-cap-weight equal-weight inverse-vol inverse-variance \
              max-sharpe risk-parity global-min-variance max-diversification \
              vol-targeting minimum-correlation hierarchical-risk-parity \
              robust-mean-variance cvar mean-downside-risk resampled-frontier \
              max-drawdown-constrained; do
    python plugin/skills/portfolio-construction/scripts/pc-${method}.py --date YYYYMMDD
done
```

**Estimated runtime**: 
- Fast methods (no optimization): ~1–3 seconds each (equal-weight, market-cap, inverse-vol/var)
- Optimization methods: ~5–30 seconds each (max-sharpe, GMV, risk-parity, HRP)
- Monte Carlo methods: ~30–120 seconds each (cvar, mean-downside-risk, max-drawdown-constrained)
- Resampled frontier: ~60–180 seconds (200 bootstraps)

## Outputs

For each method, written to:
`.analysis/saa/YYYYMMDD/portfolio-construction/{method}/`
```
portfolio.json        ← Primary output (weights + diagnostics + backtest)
memo.md               ← Human-readable methodology and results
output/
  weights.json
  diagnostics.json
  backtest.json
```

## Notes

- All 16 methods apply IPS constraints before saving outputs
- Methods that fail to converge will project to the IPS feasible starting point with a warning
- Historical backtest uses synthetic data if `covariance/output/historical-returns.json` is not present
- After running `construct`, proceed with `risk`, `recommend`, or `run` commands
