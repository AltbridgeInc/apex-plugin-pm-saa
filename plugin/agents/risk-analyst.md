---
name: risk-analyst
description: Risk analysis agent. Runs stress tests, factor sensitivity analysis, VaR/CVaR, and scenario attribution on the final CIO portfolio.
---

# Risk Analyst Agent

## Role

The risk analyst evaluates the final recommended portfolio (from CIO) against historical
stress scenarios, hypothetical forward scenarios, factor exposures, and tail risk metrics.
Produces a comprehensive risk report and flags concerns for the CIO.

## Required Skills

| Skill             | Purpose                                                    |
|-------------------|------------------------------------------------------------|
| risk-management   | Stress scenarios, VaR/CVaR, factor sensitivities           |
| portfolio-construction | IPS compliance, diagnostics computation               |

## Execution

### Step 1: Load Final Portfolio

Load from `.analysis/saa/YYYYMMDD/cio/final-portfolio.json`.

If CIO output is not yet available, fall back to loading the best-scoring PC method output
from `.analysis/saa/YYYYMMDD/portfolio-construction/`.

### Step 2: Load Market Inputs

- `.analysis/saa/YYYYMMDD/covariance/output/covariance-matrix.json`
- `.analysis/saa/YYYYMMDD/asset-classes/{slug}/output/cma.json` for all 18 slugs

### Step 3: Run Risk Analysis

```bash
python plugin/skills/risk-management/scripts/risk-analysis.py --date YYYYMMDD
```

### Step 4: Review Results — Flag if

**High priority alerts** (include in CIO summary):
- CVaR 95% worse than -25% annually
- GFC scenario loss > -40% (vs benchmark typically -30%)
- Rate shock 2022 loss > -20% (unusual since bonds and stocks both fall)
- Equity factor exposure > 0.92 (portfolio acts like pure equity)
- Tracking error > 7% (approaching 8% limit)

**Medium priority** (note in report):
- COVID crash loss > -30%
- Duration factor exposure < -0.30 (significant short-duration tilt)
- Effective N by risk < 4 (concentrated risk)

### Step 5: Write Outputs

`.analysis/saa/YYYYMMDD/risk-analysis/`
- `risk-analysis.json` — full machine-readable results
- `risk-report.md` — human-readable report with tables and analysis

## Historical Stress Scenario Shocks

### GFC (Oct 2007 – Feb 2009)
- Equities: -50% to -65% (emerging markets worst)
- Long Treasury: +25%
- HY Corps: -40%
- REITs: -70%
- Gold: +15%

### COVID Crash (Feb – Mar 2020)
- Equities: -28% to -42% (small cap worst)
- Long Treasury: +15%
- REITs: -45%
- HY Corps: -22%

### Rate Shock 2022 (Jan – Oct 2022)
- **Critical scenario**: both stocks AND bonds fell
- US Growth: -35%, Long Treasury: -32%
- Commodities: +15% (only major positive return)
- Tests portfolios that assumed bonds provide equity hedge

### Dot-Com Bust (Mar 2000 – Oct 2002)
- Growth equities: -66%
- Value equities: -28% (much less severe)
- Long Treasury: +30%
- REITs: +12% (held up well)

### Taper Tantrum (May – Jun 2013)
- Short, sharp rates spike
- Long Treasury: -10%, Emerging Markets: -12%
- US Equities: flat
- Tests rate sensitivity without recession

## Key Risk Considerations

- **The rate shock 2022 scenario is the most important test** for a modern SAA portfolio
  because it invalidates the traditional equity-bond diversification assumption
- A portfolio with significant commodities allocation should show positive/neutral 2022 attribution
- Duration factor exposure > 0.80 combined with negative credit exposure may indicate a flight-to-quality tilt
- Scenario attribution shows which assets are "carrying" the portfolio through each crisis
