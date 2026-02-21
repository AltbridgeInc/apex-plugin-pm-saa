---
name: pc-risk-parity
description: Constructs an equal risk contribution (risk parity) portfolio. Use when true risk diversification across asset classes is the primary goal.
---

# Risk Parity Portfolio Construction Agent

## Role

Solve for portfolio weights where each asset contributes equally to total portfolio
risk (RC_i = σ_p / N for all i). Uses log-barrier method in unconstrained space,
then projects to IPS-feasible space.

## Required Skills

| Skill                   | Purpose                                          |
|-------------------------|-------------------------------------------------|
| portfolio-construction  | Risk parity optimizer, IPS projection, backtest  |

## Execution

### Step 1: Load Inputs

- `.analysis/saa/YYYYMMDD/covariance/output/covariance-matrix.json`
- `.analysis/saa/YYYYMMDD/macro/macro-view.json`
- Expected returns loaded for diagnostics but not used in optimization

### Step 2: Run Script

```bash
python plugin/skills/portfolio-construction/scripts/pc-risk-parity.py --date YYYYMMDD
```

The script:
1. Applies Ledoit-Wolf shrinkage to Σ
2. Solves unconstrained risk parity in log-weight space (log-barrier ensures positivity)
3. Normalizes to sum to 1
4. Projects to IPS-feasible space via quadratic projection

### Step 3: Verify Risk Contributions

After optimization, the risk contributions should be approximately equal (within ~2% deviation).
The IPS projection will disturb perfect equality — some assets will have binding constraints.

### Step 4: Outputs Written

`.analysis/saa/YYYYMMDD/portfolio-construction/pc-risk-parity/`
- `portfolio.json`
- `memo.md`
- `output/weights.json`, `output/diagnostics.json`, `output/backtest.json`

## Key Considerations

- **Bond heavy before IPS projection**: unconstrained RP typically puts 50–70% in fixed income
  (bonds have much lower vol). The IPS equity minimum (30–75%) enforces equity allocation.
- **Regime robustness**: RP is one of the most regime-robust methods — good in all environments
- **Practical note**: institutional RP uses leverage to bring up equity-equivalent returns; we do not use leverage
- **Log-barrier optimization**: more numerically stable than direct RP formulation; avoids zero-weight corner solutions
- **IPS projection impact**: expect 5–15% reallocation from pure RP to IPS-projected RP
- **Historical performance**: risk parity has excellent out-of-sample Sharpe across multiple decades
