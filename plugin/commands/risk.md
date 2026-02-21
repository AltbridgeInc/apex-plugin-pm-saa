---
description: "Run risk analysis and stress tests on the final or specified portfolio"
argument-hint: "[--date YYYYMMDD] [--portfolio PATH]"
---

# Risk Command

Run comprehensive risk analysis on the final CIO portfolio (or a specified portfolio).

## Usage

```
/project:risk [--date YYYYMMDD] [--portfolio PATH]
```

### Arguments

- `--date YYYYMMDD`: Date folder to analyze. Defaults to today.
- `--portfolio PATH`: Optional path to a specific portfolio JSON. Defaults to CIO final-portfolio.json.

## Prerequisites

- `.analysis/saa/YYYYMMDD/cio/final-portfolio.json` — from `recommend` command (preferred)
- OR `.analysis/saa/YYYYMMDD/portfolio-construction/{method}/portfolio.json` — fallback to first available PC output
- `.analysis/saa/YYYYMMDD/covariance/output/covariance-matrix.json`
- `.analysis/saa/YYYYMMDD/asset-classes/{slug}/output/cma.json`

## Execution

```bash
python plugin/skills/risk-management/scripts/risk-analysis.py --date YYYYMMDD
```

## What It Does

1. **Historical stress scenarios** (5): GFC, COVID crash, Rate shock 2022, Dot-com bust, Taper tantrum
2. **Hypothetical scenarios** (3): Severe recession, Stagflation, Rates spike +300bps
3. **VaR and CVaR** at 90%, 95%, 99% confidence (50,000 Monte Carlo scenarios, annual scale)
4. **Factor sensitivities**: equity, duration, credit, inflation factor correlations
5. **Portfolio statistics**: effective N, TE vs benchmark, information ratio

## Outputs

`.analysis/saa/YYYYMMDD/risk-analysis/`
```
risk-analysis.json    ← Full structured results
risk-report.md        ← Human-readable report with tables
```

## Key Metrics to Review

| Metric            | Watch Level   | Action Level    |
|-------------------|---------------|-----------------|
| CVaR 95% (annual) | < -20%        | < -30%          |
| GFC scenario      | < -25%        | < -40%          |
| Rate shock 2022   | < -15%        | < -25%          |
| Equity factor exp | > 0.85        | > 0.92          |
| Tracking error    | > 6%          | > 8% (IPS limit)|
