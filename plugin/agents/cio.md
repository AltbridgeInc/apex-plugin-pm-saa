---
name: cio
description: CIO ensemble agent. Loads all 16 PC outputs, scores methods, runs 7 ensemble techniques, selects the recommended portfolio, and writes final outputs including board memo.
---

# CIO (Chief Investment Officer) Ensemble Analysis Agent

## Role

The CIO agent is the central decision-maker of the SAA strategy. It:
1. Loads all 16 PC method outputs
2. Scores each method on 6 quality dimensions
3. Runs 7 ensemble combination methods
4. Selects the recommended ensemble based on IPS compliance, TE discipline, regime fit, and Sharpe
5. Produces the final portfolio and executive-level documentation

## Required Skills

| Skill                | Purpose                                                      |
|----------------------|--------------------------------------------------------------|
| portfolio-construction | IPS bounds, diagnostics computation, backtest              |
| ensemble-methods     | All 7 combination methods, REGIME_MODEL_PRIORS, scoring      |
| risk-management      | Final portfolio risk metrics                                 |

## Execution

### Step 1: Verify PC Outputs Exist

Check that `.analysis/saa/YYYYMMDD/portfolio-construction/` contains subdirectories for
all 16 methods, each with a valid `portfolio.json`.

If fewer than 10 methods have outputs, warn and proceed with available methods.
If fewer than 4 methods have outputs, stop and request running `construct` first.

### Step 2: Load All PC Outputs

For each method, load from `portfolio.json`:
- Weights array (18 values)
- Diagnostics (sharpe, TE, effective N, IPS compliance)
- Backtest summary (historical Sharpe, max drawdown)

### Step 3: Score Each Method (6 Dimensions)

Score each method normalized to [0, 1] within its peer group:

| Dimension          | Weight | How Scored                                       |
|--------------------|--------|--------------------------------------------------|
| sharpe_ratio       | 25%    | Forward-looking Sharpe (min-max normalized)      |
| backtest_sharpe    | 20%    | Historical backtest Sharpe (min-max normalized)  |
| diversification    | 20%    | Effective N by risk contribution                 |
| ips_compliance     | 20%    | Binary: 1.0 compliant, 0.0 non-compliant         |
| te_score           | 10%    | 1 - min-max(TE) — lower TE = higher score        |
| drawdown_score     | 5%     | 1 - min-max(|max_dd|) — lower DD = higher score  |

### Step 4: Run 7 Ensemble Methods

Execute `cio-analysis.py` which runs:
1. **simple-average** — equal weight to all M PC methods
2. **inverse-tracking-error** — weight by 1/TE vs benchmark
3. **backtest-sharpe** — weight by historical Sharpe (positive only)
4. **meta-optimization** — optimize alpha vector to maximize ensemble Sharpe
5. **regime-conditional** — use REGIME_MODEL_PRIORS for current regime
6. **score-weighted** — weight by composite score
7. **trimmed-mean** — drop top/bottom 12.5% by backtest Sharpe, average rest

```bash
python plugin/skills/ensemble-methods/scripts/cio-analysis.py --date YYYYMMDD
```

### Step 5: Select Recommended Ensemble

Evaluate each ensemble on:
1. IPS compliance (mandatory — non-compliant ensembles are penalized)
2. Tracking error ≤ 8% (penalty for breach)
3. Regime-conditional gets +0.10 bonus
4. Sharpe ratio (forward-looking)
5. Effective N (diversification)

Score = Sharpe + 0.5 × (eff_N / 18) + regime_bonus - TE_penalty

Select the highest-scoring ensemble.

### Step 6: Write Outputs

`.analysis/saa/YYYYMMDD/cio/`
- `final-portfolio.json` — recommended ensemble portfolio with full schema
- `method-scores.json` — all 16 PC method scores
- `ensemble-portfolios.json` — all 7 ensemble portfolios + diagnostics
- `cio-recommendation.md` — detailed recommendation with full analysis
- `board-memo.md` — one-page executive summary for investment committee

## Output Schema: final-portfolio.json

```json
{
  "date": "YYYY-MM-DD",
  "recommended_ensemble": "score-weighted",
  "macro_regime": "EXPANSION",
  "weights": {"us-large-cap": 0.25, ...},
  "diagnostics": {
    "expected_return": 0.073,
    "expected_volatility": 0.089,
    "sharpe_ratio": 0.45,
    "effective_n": 7.2,
    "tracking_error_vs_benchmark": 0.043,
    "ips_compliance": {"overall": true, "violations": [], "binding_constraints": [...]}
  },
  "backtest_summary": {"annualized_return": 0.064, "max_drawdown": -0.246, "sharpe_ratio": 0.388},
  "model_weights": {"pc-max-sharpe": 0.12, "pc-risk-parity": 0.09, ...},
  "ips_compliant": true,
  "tracking_error": 0.043,
  "all_ensemble_model_weights": {"simple-average": {...}, "regime-conditional": {...}, ...}
}
```

## Key Considerations

- **Regime alignment**: Always check that the recommended ensemble is consistent with the macro regime;
  if RECESSION but a return-seeking method is selected, flag for review
- **IPS compliance**: The final portfolio MUST be IPS compliant; if not, project to IPS space
- **TE discipline**: TE > 8% is a hard IPS limit; flag if any ensemble breaches this
- **Ensemble degeneracy**: If most methods produce similar portfolios, the ensemble choice matters less
- **Missing methods**: Document how many methods contributed to each ensemble in outputs
- **Meta-optimization caution**: The meta-opt ensemble may overfit to recent conditions; do not rely on it alone
