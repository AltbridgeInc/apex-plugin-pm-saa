# Portfolio Construction Skill

## Overview

This skill provides 16 portfolio construction methods, a shared utility library (`common.py`),
and standardized output schemas. All methods consume Capital Market Assumptions (CMAs) and
a covariance matrix from `apex-plugin-analysis-assetclass`, apply IPS constraints, and produce
comparable JSON and markdown outputs.

## Scripts Location

`skills/portfolio-construction/scripts/`

## Dependencies

- Python 3.9+
- numpy, scipy, pandas, sklearn (scikit-learn)

Install: `pip install numpy scipy pandas scikit-learn`

## Shared Library: common.py

The foundation for all PC scripts. Provides:

### Asset Universe

18 asset classes in fixed order (`SLUGS` list, index 0–17):
us-large-cap, us-small-cap, us-value, us-growth, intl-developed, emerging-markets,
short-treasury, interm-treasury, long-treasury, ig-corps, hy-corps, intl-sovereign-bonds,
intl-corps, usd-em-debt, reits, gold, commodities, cash

### IPS Constraints

Individual bounds per asset (`IPS_BOUNDS`) and category-level bounds (`CATEGORY_BOUNDS`):

| Category      | Min  | Max  | Assets                            |
|---------------|------|------|-----------------------------------|
| total_equity  | 30%  | 75%  | indices 0–5                       |
| us_equity     | 20%  | 55%  | indices 0–3                       |
| intl_equity   | 5%   | 30%  | indices 4–5                       |
| total_fi      | 15%  | 60%  | indices 6–13                      |
| us_fi         | 10%  | 45%  | indices 6–10                      |
| intl_fi       | 0%   | 20%  | indices 11–13                     |
| real_assets   | 0%   | 25%  | indices 14–16                     |
| cash          | 0%   | 20%  | index 17                          |

Benchmark: 60% us-large-cap / 40% interm-treasury. TE max: 8%.

### Key Functions

| Function              | Purpose                                                      |
|-----------------------|--------------------------------------------------------------|
| `load_cmas(date)`     | Load expected returns + risk-free rate for all 18 slugs      |
| `load_covariance(d)`  | Load 18×18 covariance matrix                                 |
| `load_macro(date)`    | Load macro regime string                                     |
| `load_historical_returns(d)` | Load monthly returns DataFrame for backtesting        |
| `build_constraints()` | Build scipy constraint dicts (sum=1, category bounds)       |
| `get_bounds()`        | Return scipy Bounds object from IPS_BOUNDS                   |
| `make_initial_weights()` | Generate IPS-feasible starting point for optimization    |
| `project_to_ips(w)`   | Project arbitrary weights to IPS-feasible space              |
| `compute_diagnostics()` | Compute return, vol, Sharpe, TE, effective N, IPS check   |
| `run_backtest(w)`     | Historical backtest with periodic rebalancing                |
| `save_portfolio_outputs()` | Write portfolio.json, weights.json, diagnostics.json, backtest.json |
| `write_memo()`        | Write memo.md with full methodology documentation            |
| `run_pc_script()`     | Standard CLI runner for all PC scripts                       |

### Input File Locations

| File                                                              | Contents                    |
|-------------------------------------------------------------------|-----------------------------|
| `.db/analysis/assetclass/YYYYMMDD/asset-classes/{slug}/output/cma.json`    | CMA for each asset class    |
| `.db/analysis/assetclass/YYYYMMDD/covariance/output/covariance-matrix.json`| 18×18 covariance matrix     |
| `.db/analysis/assetclass/YYYYMMDD/macro/macro-view.json`                   | Macro regime                |
| `.db/analysis/assetclass/YYYYMMDD/covariance/output/historical-returns.json`| Monthly returns (optional) |

### Output File Locations

`.db/pm/saa/YYYYMMDD/portfolio-construction/{method}/`
```
portfolio.json          ← Top-level: weights + diagnostics + backtest summary
memo.md                 ← Methodology explanation and full weight table
output/
  weights.json          ← Just the weights dict
  diagnostics.json      ← Forward-looking metrics
  backtest.json         ← Historical performance
```

## The 16 Methods

### No-Optimization (Heuristic) Methods

| Method              | Core Idea                                    | Inputs Used  | Regime  |
|---------------------|----------------------------------------------|--------------|---------|
| market-cap-weight   | Proxy global market cap shares               | None         | All     |
| equal-weight        | 1/N to each asset                            | None         | All     |
| inverse-vol         | w ∝ 1/σ                                      | Vols only    | LATE/REC |
| inverse-variance    | w ∝ 1/σ²                                     | Vols only    | RECESSION |
| vol-targeting       | Inverse-vol scaled to 10% annual vol target  | Vols + Cov   | LATE/REC |

### Covariance-Based (No Returns) Methods

| Method              | Core Idea                                    | Inputs Used  | Regime  |
|---------------------|----------------------------------------------|--------------|---------|
| global-min-variance | Minimize wᵀΣw                               | Cov only     | RECESSION |
| max-diversification | Maximize (wᵀσ)/√(wᵀΣw)                      | Cov + Vols   | All     |
| minimum-correlation | Minimize wᵀCw (correlation matrix)           | Cov only     | All     |
| risk-parity         | Equal risk contribution from each asset       | Cov only     | All     |
| hrp                 | Hierarchical cluster + recursive bisection   | Cov only     | All     |

### Return-Based (MVO Family) Methods

| Method                  | Core Idea                                         | Regime      |
|-------------------------|---------------------------------------------------|-------------|
| max-sharpe              | Maximize (μ-rf)/σ (tangency portfolio)            | EXP/RECOV   |
| robust-mean-variance    | James-Stein return shrinkage + Ledoit-Wolf Σ      | EXP/RECOV   |
| resampled-frontier      | Average 200 bootstrap MVO solutions               | EXP/RECOV   |

### Downside Risk Methods

| Method                  | Core Idea                                         | Regime      |
|-------------------------|---------------------------------------------------|-------------|
| cvar                    | Minimize 95% Expected Shortfall via Monte Carlo   | RECESSION   |
| mean-downside-risk      | Maximize Sortino ratio (no upside penalty)        | EXP/RECOV   |
| max-drawdown-constrained| Max Sharpe with MDD ≤ 25% constraint              | LATE/REC    |

## Running a Single Method

```bash
# From the workspace root
python plugin/skills/portfolio-construction/scripts/pc-max-sharpe.py --date 20260220
```

## Output Schema

### portfolio.json
```json
{
  "method": "pc-max-sharpe",
  "date": "2026-02-20",
  "weights": {"us-large-cap": 0.25, "us-small-cap": 0.05, ...},
  "diagnostics": {
    "expected_return": 0.073,
    "expected_volatility": 0.089,
    "sharpe_ratio": 0.45,
    "effective_n": 6.2,
    "tracking_error_vs_benchmark": 0.043,
    "ips_compliance": {"overall": true, "violations": [], "binding_constraints": [...]},
    "risk_contributions": {"us-large-cap": 0.032, ...},
    "risk_contributions_pct": {"us-large-cap": 0.35, ...}
  },
  "backtest_summary": {
    "annualized_return": 0.064,
    "annualized_volatility": 0.087,
    "sharpe_ratio": 0.388,
    "sortino_ratio": 0.52,
    "calmar_ratio": 0.26,
    "max_drawdown": -0.246,
    "win_rate": 0.58,
    "start_date": "1996-01-01",
    "end_date": "2026-02-28"
  }
}
```
