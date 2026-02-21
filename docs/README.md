# apex-plugin-strategy-saa Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Data Flow](#data-flow)
4. [Portfolio Construction Methods](#portfolio-construction-methods)
5. [Ensemble Methods](#ensemble-methods)
6. [IPS Constraints Reference](#ips-constraints-reference)
7. [Regime-Model Priors Reference](#regime-model-priors-reference)
8. [Output Schemas](#output-schemas)
9. [Python Dependencies](#python-dependencies)
10. [Troubleshooting](#troubleshooting)

---

## Overview

`apex-plugin-strategy-saa` is the strategy layer of the Apex SAA (Strategic Asset Allocation)
system. It sits downstream of `apex-plugin-analysis-assetclass` and produces actionable
portfolio recommendations.

**Input**: Capital Market Assumptions (expected returns per asset class), covariance matrix,
and macro regime — all produced by analysis-assetclass.

**Output**: Final portfolio weights (18 asset classes), diagnostics, historical backtest,
stress test results, and a board-level investment memo.

---

## Architecture

```
Layer                Plugin                     Outputs
─────────────────────────────────────────────────────────────────
ANALYSIS    apex-plugin-analysis-assetclass  →  CMAs, Sigma, Regime
                                                    ↓
STRATEGY    apex-plugin-strategy-saa         →  16 PC Portfolios
                                             →  7 Ensembles
                                             →  Final Portfolio
                                             →  Risk Report
                                             →  Board Memo
```

---

## Data Flow

```
.analysis/saa/YYYYMMDD/
  asset-classes/{slug}/output/cma.json          (input: from analysis-assetclass)
  covariance/output/covariance-matrix.json      (input: from analysis-assetclass)
  macro/macro-view.json                         (input: from analysis-assetclass)
        ↓
  portfolio-construction/{method}/portfolio.json (output: construct command)
        ↓
  cio/final-portfolio.json                       (output: recommend command)
  cio/board-memo.md
        ↓
  risk-analysis/risk-report.md                   (output: risk command)
        ↓
  rebalancing/rebalancing-report.md              (output: rebalance command)
```

---

## Portfolio Construction Methods

### Why 16 Methods?

Different methods are optimal in different market regimes and under different confidence
levels in return estimates. By running all 16, the CIO ensemble can draw on the most
appropriate approaches for the current environment.

The methods span a spectrum:
- **No estimation required**: equal-weight, market-cap-weight (immune to estimation error)
- **Vol-only**: inverse-vol, inverse-variance, vol-targeting (use only individual vols)
- **Covariance-only**: GMV, max-diversification, minimum-correlation, risk-parity, HRP (no return estimates)
- **Return + covariance**: max-sharpe, robust-MVO, resampled-frontier (full CMA utilization)
- **Downside-focused**: CVaR, mean-downside-risk, max-drawdown-constrained (tail risk priority)

### Method Selection by Regime

| Regime      | Preferred Methods                                                    |
|-------------|----------------------------------------------------------------------|
| EXPANSION   | max-sharpe, robust-MVO, resampled-frontier, max-diversification      |
| LATE-CYCLE  | robust-MVO, risk-parity, max-diversification, HRP, vol-targeting     |
| RECESSION   | GMV, CVaR, max-drawdown-constrained, inverse-vol, HRP                |
| RECOVERY    | max-sharpe, equal-weight, max-diversification, resampled-frontier    |

---

## Ensemble Methods

### Why Combine Methods?

No single optimization method dominates across all market conditions. Combining methods:
- Reduces sensitivity to any single model's assumptions
- Hedges estimation error in returns and covariance
- Produces more stable, less extreme allocations
- Allows regime-adaptive tilting without full commitment to regime forecasting

### Ensemble Selection Priority

1. IPS compliance (mandatory — non-compliant portfolios are disqualified or projected)
2. Tracking error ≤ 8% vs 60/40 benchmark (IPS mandate)
3. Regime alignment (regime-conditional ensemble gets bonus)
4. Forward-looking Sharpe ratio
5. Effective diversification (effective N)

---

## IPS Constraints Reference

### Individual Asset Bounds

| Asset Class           | Min  | Max  |
|-----------------------|------|------|
| us-large-cap          | 10%  | 40%  |
| us-small-cap          | 0%   | 15%  |
| us-value              | 0%   | 15%  |
| us-growth             | 0%   | 15%  |
| intl-developed        | 5%   | 25%  |
| emerging-markets      | 0%   | 15%  |
| short-treasury        | 0%   | 20%  |
| interm-treasury       | 0%   | 25%  |
| long-treasury         | 0%   | 15%  |
| ig-corps              | 0%   | 20%  |
| hy-corps              | 0%   | 10%  |
| intl-sovereign-bonds  | 0%   | 15%  |
| intl-corps            | 0%   | 10%  |
| usd-em-debt           | 0%   | 10%  |
| reits                 | 0%   | 15%  |
| gold                  | 0%   | 10%  |
| commodities           | 0%   | 10%  |
| cash                  | 0%   | 20%  |

### Category Bounds

| Category        | Indices | Min  | Max  |
|-----------------|---------|------|------|
| total_equity    | 0–5     | 30%  | 75%  |
| us_equity       | 0–3     | 20%  | 55%  |
| intl_equity     | 4–5     | 5%   | 30%  |
| total_fi        | 6–13    | 15%  | 60%  |
| us_fi           | 6–10    | 10%  | 45%  |
| intl_fi         | 11–13   | 0%   | 20%  |
| real_assets     | 14–16   | 0%   | 25%  |
| cash            | 17      | 0%   | 20%  |

### Benchmark and Tracking Error

- **Benchmark**: 60% US Large Cap / 40% Interm Treasury
- **Max Tracking Error**: 8% annualized

---

## Regime-Model Priors Reference

The regime-conditional ensemble (ensemble #5) uses these hardcoded priors.
Priors represent the belief about which methods are most likely to work well in each regime.

Each set sums to 1.0 (or close to it — normalized internally).

See `skills/ensemble-methods/SKILL.md` for the full table.

---

## Output Schemas

### portfolio.json (per PC method)

```json
{
  "method": "string",
  "date": "YYYY-MM-DD",
  "weights": {"slug": float, ...},
  "diagnostics": {
    "expected_return": float,
    "expected_volatility": float,
    "sharpe_ratio": float,
    "effective_n": float,
    "tracking_error_vs_benchmark": float,
    "ips_compliance": {
      "overall": bool,
      "violations": ["string"],
      "binding_constraints": ["string"]
    },
    "risk_contributions": {"slug": float},
    "risk_contributions_pct": {"slug": float}
  },
  "backtest_summary": {
    "annualized_return": float,
    "annualized_volatility": float,
    "sharpe_ratio": float,
    "sortino_ratio": float,
    "calmar_ratio": float,
    "max_drawdown": float,
    "win_rate": float,
    "rebalance_frequency": "string",
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "num_months": int
  }
}
```

### final-portfolio.json (CIO output)

```json
{
  "date": "YYYY-MM-DD",
  "recommended_ensemble": "string",
  "macro_regime": "string",
  "weights": {"slug": float},
  "diagnostics": {...},
  "backtest_summary": {...},
  "model_weights": {"method": float},
  "ips_compliant": bool,
  "tracking_error": float,
  "all_ensemble_model_weights": {"ensemble": {"method": float}}
}
```

---

## Python Dependencies

```
numpy>=1.24
scipy>=1.10
pandas>=2.0
scikit-learn>=1.3
```

Install: `pip install numpy scipy pandas scikit-learn`

All scripts use only these packages plus the standard library.

---

## Troubleshooting

### "CMA file not found"

Run `apex-plugin-analysis-assetclass` first to generate CMA files.

### "Covariance matrix not found"

Run the covariance step of `apex-plugin-analysis-assetclass`.

### "No PC method outputs found"

Run `/project:construct all` before `/project:recommend`.

### Optimization convergence warnings

Common with `pc-max-sharpe` on flat return landscapes. The optimizer tries 10 restarts;
if all fail to find a better solution than the starting point, it returns the best found.
Check that expected returns span a reasonable range (not all identical).

### Synthetic backtest warning

If `historical-returns.json` is not in the covariance output folder, the backtest uses
synthetic returns generated from the CMA and covariance matrix. Results are directionally
useful but not historically calibrated. Add real historical returns to improve accuracy.

### IPS projection warnings

When a PC method's raw weights violate IPS constraints, they are projected to the nearest
IPS-feasible point. This is expected behavior for methods that don't incorporate IPS
constraints in their objective (e.g., unconstrained risk parity). The projection preserves
as much of the original intent as possible.
