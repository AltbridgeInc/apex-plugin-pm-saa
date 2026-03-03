---
description: "Run CIO ensemble analysis and produce the final portfolio recommendation"
argument-hint: "[--date YYYYMMDD]"
---

# Recommend Command

Run the CIO ensemble analysis to combine 16 PC methods, score them, and produce the
final portfolio recommendation with board memo.

## Usage

```
/project:recommend [--date YYYYMMDD]
```

### Arguments

- `--date YYYYMMDD`: Date folder to process. Defaults to today.

## Prerequisites

At least 4 PC method outputs must exist at:
`.db/pm/saa/YYYYMMDD/portfolio-construction/{method}/portfolio.json`

Run `construct` command first.

Also requires:
- `.db/analysis/assetclass/YYYYMMDD/covariance/output/covariance-matrix.json`
- `.db/analysis/assetclass/YYYYMMDD/asset-classes/{slug}/output/cma.json`
- `.db/analysis/assetclass/YYYYMMDD/macro/macro-view.json`

## Execution

```bash
python plugin/skills/ensemble-methods/scripts/cio-analysis.py --date YYYYMMDD
```

## What It Does

1. **Loads** all available PC method outputs
2. **Scores** each method on 6 dimensions (Sharpe, backtest Sharpe, diversification, IPS, TE, drawdown)
3. **Runs 7 ensemble methods**: simple-average, inverse-TE, backtest-Sharpe, meta-optimization,
   regime-conditional, score-weighted, trimmed-mean
4. **Selects** recommended ensemble based on IPS compliance, TE, regime fit, and Sharpe
5. **Writes** final-portfolio.json, method-scores.json, ensemble-portfolios.json,
   cio-recommendation.md, and board-memo.md

## Outputs

`.db/pm/saa/YYYYMMDD/cio/`
```
final-portfolio.json          ← Machine-readable final recommendation
method-scores.json            ← All 16 PC method scores
ensemble-portfolios.json      ← All 7 ensemble portfolios
cio-recommendation.md         ← Detailed analytical recommendation
board-memo.md                 ← Executive summary for investment committee
```

## Notes

- The regime (from macro-view.json) influences ensemble #5 (regime-conditional) and the selection bonus
- If an ensemble is IPS non-compliant, it is projected to IPS-feasible space before scoring
- The recommended ensemble is not necessarily the one with the highest Sharpe — IPS compliance is mandatory
- After running `recommend`, run `risk` for stress testing the final portfolio
