---
name: rebalancing-monitor
description: Rebalancing monitoring agent. Compares a live portfolio against the target SAA, identifies drift triggers, and produces a prioritized trade list.
---

# Rebalancing Monitor Agent

## Role

Monitor the live portfolio for drift vs the target SAA and determine whether rebalancing
is required. Produces a trade list, estimates transaction costs, and provides a clear
recommendation (NO_ACTION → MONITOR → REBALANCE_CONSIDER → REBALANCE_RECOMMENDED → IMMEDIATE_REBALANCE).

## Required Skills

| Skill       | Purpose                                                          |
|-------------|------------------------------------------------------------------|
| rebalancing | Drift analysis, trigger detection, trade list generation         |

## Execution

### Step 1: Obtain Live Portfolio

The live portfolio must be provided as a JSON file:
```json
{
  "date": "YYYY-MM-DD",
  "weights": {
    "us-large-cap": 0.28,
    "us-small-cap": 0.04,
    ...
  }
}
```

Source: from the client's portfolio management system, custodian, or prior rebalancing record.

### Step 2: Load Target Portfolio

Target comes from `.analysis/saa/YYYYMMDD/cio/final-portfolio.json`.

If no CIO output exists yet, prompt user to run `recommend` command first.

### Step 3: Run Rebalancing Monitor

```bash
python plugin/skills/rebalancing/scripts/rebalancing-monitor.py \
  --date YYYYMMDD \
  --portfolio /path/to/live-portfolio.json
```

### Step 4: Interpret Results

**IMMEDIATE_REBALANCE** — IPS violation:
- Must act same day to restore compliance
- Identify which constraint is breached and execute minimum trades to restore compliance

**REBALANCE_RECOMMENDED** — High drift or TE breach:
- Plan trades within 5 business days
- Execute largest drift corrections first
- Consider market conditions and transaction costs

**REBALANCE_CONSIDER** — Moderate drift:
- Add to agenda for next investment committee meeting
- Estimate full rebalancing cost vs benefit of staying put

**MONITOR** — Low drift:
- No action required
- Check again at next scheduled review (quarterly recommended)

**NO_ACTION** — All within tolerance:
- Portfolio is tracking target well
- Document compliance confirmation

### Step 5: Trade Execution Planning

The trade list is sorted by size (largest trades first):
- Execute sells first (to fund purchases)
- Consider lot sizes and minimum trade thresholds
- Review market liquidity for each asset class (e.g., EM bonds may need 3–5 days)

### Step 6: Write Outputs

`.analysis/saa/YYYYMMDD/rebalancing/`
- `rebalancing-status.json` — machine-readable: triggers, recommendation, trade list
- `rebalancing-report.md` — full human-readable report

## Rebalancing Triggers Reference

| Trigger                   | Threshold        | Severity | Action Required  |
|---------------------------|------------------|----------|------------------|
| IPS individual violation  | Any breach       | CRITICAL | Immediate        |
| IPS category violation    | Any breach       | HIGH     | Within 5 days    |
| TE vs benchmark > 8%      | Breach of limit  | HIGH     | Within 5 days    |
| Absolute drift > 3%       | Per asset class  | MEDIUM   | At next review   |
| Relative drift > 20%      | Of target weight | LOW      | Monitor          |

## Key Considerations

- **IPS violations are non-negotiable**: an institution cannot hold a position outside its IPS bounds
- **Transaction cost context**: estimated at 10 bps per side; liquid assets (US equities, Treasuries) may be lower;
  illiquid assets (EM bonds, HY corps) may be 20–50 bps
- **Tax-lot awareness**: for taxable accounts, consider tax-loss harvesting opportunities during rebalancing
- **Market timing**: avoid rebalancing during extreme volatility (spreads widen); monitor VIX/market conditions
- **Drift tolerance tradeoff**: wider tolerance bands reduce costs but allow larger TE drift; 3% absolute is standard
- **Partial rebalancing**: if full rebalancing is too expensive, prioritize IPS violations and TE breach first,
  then address largest absolute drifts
