# apex-plugin-strategy-saa

Strategic Asset Allocation (SAA) strategy plugin for the Apex investment research ecosystem.

## Overview

This plugin is the strategy layer of the SAA system. It consumes outputs from
`apex-plugin-analysis-assetclass` (expected returns, covariance matrix, macro regime)
and produces final portfolio recommendations using 16 portfolio construction methods,
an ensemble CIO decision, risk analysis, and rebalancing monitoring.

## Architecture

```
apex-plugin-analysis-assetclass
  ↓ produces: CMAs, covariance matrix, macro regime
apex-plugin-strategy-saa
  ↓ produces: final-portfolio.json, board-memo.md, risk-report.md
```

## Asset Universe (18 asset classes)

| Slug                  | Category      |
|-----------------------|---------------|
| us-large-cap          | US Equity     |
| us-small-cap          | US Equity     |
| us-value              | US Equity     |
| us-growth             | US Equity     |
| intl-developed        | Intl Equity   |
| emerging-markets      | Intl Equity   |
| short-treasury        | US Fixed Inc. |
| interm-treasury       | US Fixed Inc. |
| long-treasury         | US Fixed Inc. |
| ig-corps              | US Fixed Inc. |
| hy-corps              | US Fixed Inc. |
| intl-sovereign-bonds  | Intl Fixed Inc|
| intl-corps            | Intl Fixed Inc|
| usd-em-debt           | Intl Fixed Inc|
| reits                 | Real Assets   |
| gold                  | Real Assets   |
| commodities           | Real Assets   |
| cash                  | Cash          |

## Quick Start

```bash
# Full pipeline (requires analysis-assetclass outputs to exist)
/project:run --date 20260220

# Step by step
/project:construct all --date 20260220
/project:recommend --date 20260220
/project:risk --date 20260220

# Rebalancing check (requires live portfolio)
/project:rebalance --date 20260220 --portfolio /path/to/live.json
```

## Portfolio Construction Methods (16)

### Heuristic / No-Optimization
1. `pc-market-cap-weight` — Global market cap proxy weights
2. `pc-equal-weight` — 1/N equal weight
3. `pc-inverse-vol` — Weight by 1/σ
4. `pc-inverse-variance` — Weight by 1/σ²
5. `pc-vol-targeting` — Scale to 10% annual vol target

### Covariance-Based (No Returns Required)
6. `pc-global-min-variance` — Minimize wᵀΣw
7. `pc-max-diversification` — Maximize DR = (wᵀσ)/√(wᵀΣw)
8. `pc-minimum-correlation` — Minimize wᵀCw (correlation matrix)
9. `pc-risk-parity` — Equal risk contribution (ERC)
10. `pc-hierarchical-risk-parity` — HRP (Lopez de Prado 2016)

### Return-Based (MVO Family)
11. `pc-max-sharpe` — Maximize (μ-rf)/σ with 10 restarts
12. `pc-robust-mean-variance` — James-Stein return shrinkage + LW covariance
13. `pc-resampled-frontier` — 200-bootstrap average (Michaud & Michaud)

### Downside Risk Methods
14. `pc-cvar` — Minimize 95% CVaR (Monte Carlo)
15. `pc-mean-downside-risk` — Maximize Sortino ratio (Monte Carlo)
16. `pc-max-drawdown-constrained` — Max Sharpe with MDD ≤ 25% constraint

## Ensemble Methods (7)

1. Simple Average
2. Inverse Tracking Error Weighting
3. Backtest Sharpe Weighting
4. Meta-Optimization (alpha vector optimization)
5. Regime-Conditional Weighting (uses REGIME_MODEL_PRIORS)
6. Score-Weighted Combination
7. Trimmed Mean

## IPS Constraints

Individual bounds per asset class plus category-level constraints:
- Total Equity: 30–75%
- US Equity: 20–55%
- International Equity: 5–30%
- Total Fixed Income: 15–60%
- Real Assets: 0–25%
- Benchmark: 60/40 (US Large Cap / Interm Treasury)
- Max TE vs Benchmark: 8%

## Output Files

| File                                           | Description                     |
|------------------------------------------------|---------------------------------|
| `cio/final-portfolio.json`                     | Final recommended portfolio      |
| `cio/board-memo.md`                            | Executive summary                |
| `cio/cio-recommendation.md`                    | Full analytical recommendation   |
| `cio/method-scores.json`                       | 16-method scoring breakdown      |
| `cio/ensemble-portfolios.json`                 | All 7 ensemble portfolios        |
| `portfolio-construction/{method}/portfolio.json` | Per-method output              |
| `risk-analysis/risk-report.md`                 | Stress test and risk report      |
| `rebalancing/rebalancing-report.md`            | Drift analysis and trade list    |
