# Ensemble Methods Skill

## Overview

Implements 7 methods for combining 16 PC model outputs into a single portfolio recommendation.
Also scores each of the 16 PC methods on 6 dimensions and uses regime-conditional priors
to align model selection with the current macroeconomic environment.

## Script

`skills/ensemble-methods/scripts/cio-analysis.py`

## Dependencies

numpy, scipy (shared with portfolio-construction skill)

## Input Requirements

All 16 PC method outputs at:
`.db/pm/saa/YYYYMMDD/portfolio-construction/{method}/portfolio.json`

Plus CMA, covariance, and macro regime (same as PC scripts).

## Outputs

`.db/pm/saa/YYYYMMDD/cio/`
```
final-portfolio.json         ← Recommended portfolio (machine-readable)
method-scores.json           ← Scores for all 16 PC methods
ensemble-portfolios.json     ← All 7 ensemble portfolios + diagnostics
cio-recommendation.md        ← Detailed CIO analysis document
board-memo.md                ← Executive summary for investment committee
```

---

## Scoring (6 Dimensions)

Each PC method is scored on 6 normalized (0–1) dimensions:

| Dimension          | Weight | Description                                           |
|--------------------|--------|-------------------------------------------------------|
| sharpe_ratio       | 25%    | Forward-looking Sharpe (normalized across 16 methods) |
| backtest_sharpe    | 20%    | Historical backtest Sharpe ratio                      |
| diversification    | 20%    | Effective N by risk contribution (normalized)         |
| ips_compliance     | 20%    | Binary: 1.0 if compliant, 0.0 if not                 |
| te_score           | 10%    | Tracking error quality (lower TE = higher score)      |
| drawdown_score     | 5%     | Historical max drawdown (lower DD = higher score)     |

Total score = weighted sum of dimension scores.

---

## The 7 Ensemble Methods

### 1. Simple Average
Equal weight (1/M) to each of the M available PC methods.
Most naive but often competitive. Serves as baseline.

### 2. Inverse Tracking Error Weighting
Weight each PC method by `1/TE_i` where TE_i is the method's tracking
error vs the 60/40 benchmark. Methods closer to benchmark get more weight.

### 3. Backtest Sharpe Weighting
Weight proportional to historical backtest Sharpe ratio (positive values only).
Methods with stronger historical performance get more influence.

### 4. Meta-Optimization (Stacking)
Optimize the mixing weights α₁...αₘ to maximize the ensemble Sharpe ratio:
- maximize (μ_ensemble - rf) / σ_ensemble
- subject to Σαᵢ = 1, αᵢ ≥ 0
Uses scipy SLSQP for the alpha vector optimization.

### 5. Regime-Conditional Weighting
Uses hardcoded `REGIME_MODEL_PRIORS` dict: for each of 4 macroeconomic
regimes (EXPANSION, LATE-CYCLE, RECESSION, RECOVERY), a prior weight
for each PC method is specified based on which methods are theoretically
suited to that environment. Current regime is read from macro-view.json.

**EXPANSION prior** (highest weight): max-sharpe (15%), robust-mean-variance (12%), resampled-frontier (12%)
**LATE-CYCLE prior**: robust-mean-variance (12%), risk-parity (10%), max-diversification (10%)
**RECESSION prior**: global-min-variance (15%), cvar (12%), max-drawdown-constrained (12%)
**RECOVERY prior**: max-sharpe (12%), equal-weight (10%), max-diversification (10%)

### 6. Score-Weighted Combination
Weight each PC method proportionally to its total composite score.
Methods with higher overall quality get more influence.

### 7. Trimmed Mean
Sort PC methods by backtest Sharpe, remove top and bottom 12.5%,
then equal-weight the remaining middle tier. Avoids outlier distortion.

---

## Ensemble Selection Criteria

The CIO selects among the 7 ensembles using:

1. **IPS compliance** (mandatory — non-compliant ensembles are projected or excluded)
2. **Tracking error ≤ 8%** (penalized if exceeded)
3. **Regime fit** (regime-conditional gets +0.10 bonus in scoring)
4. **Sharpe ratio** (forward-looking)
5. **Effective N** (risk diversification)

Score = Sharpe + 0.5 × (effective_N / 18) + regime_bonus - TE_penalty

---

## Regime Model Priors Table

Full REGIME_MODEL_PRIORS values (used in ensemble #5):

| Method                    | EXPANSION | LATE-CYCLE | RECESSION | RECOVERY |
|---------------------------|-----------|------------|-----------|----------|
| pc-max-sharpe             | 0.15      | 0.05       | 0.00      | 0.12     |
| pc-robust-mean-variance   | 0.12      | 0.12       | 0.03      | 0.08     |
| pc-resampled-frontier     | 0.12      | 0.08       | 0.02      | 0.10     |
| pc-max-diversification    | 0.10      | 0.10       | 0.04      | 0.10     |
| pc-risk-parity            | 0.08      | 0.10       | 0.08      | 0.08     |
| pc-market-cap-weight      | 0.08      | 0.01       | 0.00      | 0.08     |
| pc-equal-weight           | 0.06      | 0.05       | 0.03      | 0.10     |
| pc-hierarchical-risk-parity| 0.06     | 0.08       | 0.06      | 0.06     |
| pc-mean-downside-risk     | 0.05      | 0.06       | 0.05      | 0.06     |
| pc-max-drawdown-constrained| 0.05     | 0.08       | 0.12      | 0.05     |
| pc-vol-targeting          | 0.03      | 0.07       | 0.10      | 0.05     |
| pc-minimum-correlation    | 0.03      | 0.05       | 0.06      | 0.04     |
| pc-inverse-vol            | 0.02      | 0.03       | 0.08      | 0.02     |
| pc-inverse-variance       | 0.02      | 0.02       | 0.06      | 0.02     |
| pc-global-min-variance    | 0.02      | 0.04       | 0.15      | 0.01     |
| pc-cvar                   | 0.01      | 0.06       | 0.12      | 0.03     |

---

## Running

```bash
python plugin/skills/ensemble-methods/scripts/cio-analysis.py --date 20260220
```
