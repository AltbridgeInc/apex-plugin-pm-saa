# Risk Management Skill

## Overview

Provides comprehensive portfolio risk analysis including 5 historical stress scenarios,
3 hypothetical forward scenarios, factor sensitivity analysis, tail risk metrics (VaR/CVaR),
and scenario attribution to identify which assets drive losses in each scenario.

## Script

`skills/risk-management/scripts/risk-analysis.py`

## Dependencies

numpy, scipy, pandas, scikit-learn (shared with portfolio-construction skill)

## Input Requirements

| Required | File                                                  | Contents             |
|----------|-------------------------------------------------------|----------------------|
| Yes      | `.analysis/saa/YYYYMMDD/cio/final-portfolio.json`     | CIO final portfolio  |
| Yes      | `.analysis/saa/YYYYMMDD/covariance/output/covariance-matrix.json` | Covariance |
| Yes      | `.analysis/saa/YYYYMMDD/asset-classes/*/output/cma.json` | Expected returns |
| Fallback | Any PC method portfolio.json                          | If CIO not run yet   |

## Outputs

`.analysis/saa/YYYYMMDD/risk-analysis/`
```
risk-analysis.json    ← Full machine-readable results
risk-report.md        ← Human-readable summary report
```

## Analysis Components

### 1. Historical Stress Scenarios (5)

| Scenario                    | Period           | Key Shock                                    |
|-----------------------------|------------------|----------------------------------------------|
| GFC                         | Oct 07 – Feb 09  | Equities -50%, credit collapse               |
| COVID crash                 | Feb – Mar 2020   | Equities -34%, fastest bear market ever      |
| Rate shock 2022             | Jan – Oct 2022   | Equities -24%, long bonds -32% simultaneously|
| Dot-com bust                | Mar 00 – Oct 02  | Tech equities -66%, treasuries +30%          |
| Taper tantrum               | May – Jun 2013   | Rates spike, EM/bonds -10%, equities flat    |

Each scenario provides:
- Portfolio return during shock
- Benchmark (60/40) return during shock
- Excess vs benchmark
- Per-asset attribution (weight × shock = contribution)

### 2. Hypothetical Forward Scenarios (3)

| Scenario                    | Description                                  |
|-----------------------------|----------------------------------------------|
| Severe recession            | -35% equity shock, flight to quality         |
| Stagflation                 | High inflation + recession, bonds AND equities fall |
| Rates spike +300bps         | Sharp rate rise across the yield curve       |

### 3. Tail Risk Metrics (Monte Carlo, 50,000 scenarios)

VaR and CVaR (Expected Shortfall) at 90%, 95%, 99% confidence levels.

### 4. Factor Sensitivities

Portfolio correlation with 4 systematic factors:
- Equity factor (proxy: US large cap)
- Duration factor (proxy: long Treasury)
- Credit factor (proxy: high yield)
- Inflation factor (proxy: 50/50 gold + commodities)

### 5. Concentration Metrics

- Effective N by weight (inverse HHI of weights)
- Effective N by risk contribution (inverse HHI of risk contributions)
- Tracking error vs 60/40 benchmark
- Information ratio (expected)

## Running

```bash
python plugin/skills/risk-management/scripts/risk-analysis.py --date 20260220
```

## Key Risk Thresholds

| Metric                     | Warning Level  | Critical Level |
|----------------------------|----------------|----------------|
| CVaR 95% (annual)          | < -20%         | < -30%         |
| Tracking Error vs Benchmark| > 6%           | > 8%           |
| GFC scenario return        | < -25%         | < -40%         |
| Rate shock 2022 return     | < -15%         | < -25%         |
| Equity factor exposure     | > 0.90         | > 0.95         |
