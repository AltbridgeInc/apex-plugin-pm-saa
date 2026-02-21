#!/usr/bin/env python3
"""
rebalancing-monitor.py — Portfolio Rebalancing Monitor.

Compares the current live portfolio weights against the target (final-portfolio.json)
and determines whether rebalancing is needed based on:
1. Absolute drift threshold (any asset drifted > 3% from target)
2. Relative drift threshold (any asset drifted > 20% of its target weight)
3. IPS violation (any asset outside its IPS bounds)
4. Tracking error breach (TE > 8%)
5. Category bounds breach (total equity/FI/etc outside category limits)

Usage:
    python rebalancing-monitor.py [--date YYYYMMDD] [--portfolio PATH]
    
    --portfolio PATH: Path to JSON file with current live portfolio weights
    Format: {"weights": {"us-large-cap": 0.25, ...}, "date": "YYYY-MM-DD"}
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).parent
PC_SCRIPTS = SCRIPT_DIR.parent.parent / "portfolio-construction" / "scripts"
sys.path.insert(0, str(PC_SCRIPTS))
from common import (
    SLUGS, N, SLUG_TO_IDX, W_BENCH, IPS_BOUNDS, CATEGORY_BOUNDS, TE_MAX,
    load_covariance, saa_path, parse_date_arg, _check_ips_compliance
)

# ---------------------------------------------------------------------------
# Rebalancing thresholds
# ---------------------------------------------------------------------------

# Trigger rebalancing if any asset drifts more than this from target
ABS_DRIFT_THRESHOLD = 0.03   # 3 percentage points

# Trigger if relative drift > this fraction of target weight
REL_DRIFT_THRESHOLD = 0.20   # 20% of target weight

# Trigger if TE exceeds this
TE_BREACH_THRESHOLD = TE_MAX  # 8%

# Transaction cost estimate (basis points one-way per unit traded)
TRANSACTION_COST_BPS = 10  # 10 bps = 0.10%


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def load_target_portfolio(date_str=None):
    """Load target portfolio from CIO final-portfolio.json."""
    base = saa_path(date_str)
    target_file = base / "cio" / "final-portfolio.json"

    if not target_file.exists():
        raise FileNotFoundError(
            f"Target portfolio not found at {target_file}. "
            f"Run 'recommend' command first."
        )

    with open(target_file) as f:
        data = json.load(f)

    w_dict = data["weights"]
    w = np.array([w_dict.get(slug, 0.0) for slug in SLUGS])
    return w, data


def load_live_portfolio(portfolio_path):
    """Load current live portfolio from a JSON file."""
    path = Path(portfolio_path)
    if not path.exists():
        raise FileNotFoundError(f"Live portfolio file not found: {portfolio_path}")

    with open(path) as f:
        data = json.load(f)

    w_dict = data.get("weights", data)  # Support both formats
    w = np.array([w_dict.get(slug, 0.0) for slug in SLUGS])

    # Normalize if needed
    if abs(w.sum() - 1.0) > 0.01:
        w = w / w.sum()

    return w, data


def analyze_drift(w_live, w_target, Sigma):
    """
    Analyze drift between live and target portfolio.
    Returns comprehensive drift analysis.
    """
    w_live = np.asarray(w_live, dtype=float)
    w_target = np.asarray(w_target, dtype=float)

    drift = w_live - w_target
    abs_drift = np.abs(drift)

    # Relative drift (as % of target weight)
    rel_drift = np.where(
        w_target > 0.001,
        abs(drift) / w_target,
        abs_drift  # For near-zero targets, use absolute drift
    )

    # Tracking error of live vs target
    te_vs_target = float(np.sqrt(drift @ Sigma @ drift))

    # Tracking error of live vs benchmark
    diff_bench = w_live - W_BENCH
    te_vs_bench = float(np.sqrt(diff_bench @ Sigma @ diff_bench))

    # Per-asset analysis
    asset_drift = {}
    for i, slug in enumerate(SLUGS):
        lo, hi = IPS_BOUNDS[i]
        ips_ok = lo - 1e-5 <= w_live[i] <= hi + 1e-5

        asset_drift[slug] = {
            "live_weight": round(float(w_live[i]), 4),
            "target_weight": round(float(w_target[i]), 4),
            "absolute_drift": round(float(drift[i]), 4),
            "relative_drift": round(float(rel_drift[i]), 4),
            "abs_drift_exceeds_threshold": bool(abs_drift[i] > ABS_DRIFT_THRESHOLD),
            "rel_drift_exceeds_threshold": bool(rel_drift[i] > REL_DRIFT_THRESHOLD),
            "ips_ok": bool(ips_ok),
            "ips_bounds": [lo, hi],
        }

    # Category drift
    category_drift = {}
    for cat, (indices, lo, hi) in CATEGORY_BOUNDS.items():
        live_cat = sum(w_live[i] for i in indices)
        target_cat = sum(w_target[i] for i in indices)
        category_drift[cat] = {
            "live_weight": round(live_cat, 4),
            "target_weight": round(target_cat, 4),
            "drift": round(live_cat - target_cat, 4),
            "ips_bounds": [lo, hi],
            "ips_ok": bool(lo - 1e-5 <= live_cat <= hi + 1e-5),
        }

    return {
        "asset_drift": asset_drift,
        "category_drift": category_drift,
        "te_vs_target": round(te_vs_target, 6),
        "te_vs_benchmark": round(te_vs_bench, 6),
        "max_abs_drift": round(float(abs_drift.max()), 4),
        "max_rel_drift": round(float(rel_drift.max()), 4),
        "max_drift_asset": SLUGS[int(abs_drift.argmax())],
    }


def determine_rebalancing_triggers(drift_analysis, w_live, w_target):
    """
    Determine which rebalancing triggers are breached.
    Returns list of triggers and overall rebalancing recommendation.
    """
    triggers = []

    # 1. Absolute drift breach
    for slug, d in drift_analysis["asset_drift"].items():
        if d["abs_drift_exceeds_threshold"]:
            triggers.append({
                "type": "absolute_drift",
                "asset": slug,
                "severity": "HIGH" if abs(d["absolute_drift"]) > 0.05 else "MEDIUM",
                "detail": f"{slug}: live={d['live_weight']*100:.1f}%, "
                          f"target={d['target_weight']*100:.1f}%, "
                          f"drift={d['absolute_drift']*100:+.1f}%"
            })

    # 2. Relative drift breach
    for slug, d in drift_analysis["asset_drift"].items():
        if d["rel_drift_exceeds_threshold"] and not d["abs_drift_exceeds_threshold"]:
            if d["target_weight"] > 0.02:  # Only flag if meaningful position
                triggers.append({
                    "type": "relative_drift",
                    "asset": slug,
                    "severity": "LOW",
                    "detail": f"{slug}: relative drift {d['relative_drift']*100:.0f}% of target"
                })

    # 3. IPS violations
    for slug, d in drift_analysis["asset_drift"].items():
        if not d["ips_ok"]:
            triggers.append({
                "type": "ips_violation",
                "asset": slug,
                "severity": "CRITICAL",
                "detail": f"{slug}: weight {d['live_weight']*100:.1f}% outside "
                          f"IPS bounds [{d['ips_bounds'][0]*100:.0f}%, {d['ips_bounds'][1]*100:.0f}%]"
            })

    # 4. Category bounds breach
    for cat, d in drift_analysis["category_drift"].items():
        if not d["ips_ok"]:
            triggers.append({
                "type": "category_ips_violation",
                "asset": cat,
                "severity": "HIGH",
                "detail": f"{cat}: {d['live_weight']*100:.1f}% outside "
                          f"bounds [{d['ips_bounds'][0]*100:.0f}%, {d['ips_bounds'][1]*100:.0f}%]"
            })

    # 5. Tracking error breach
    if drift_analysis["te_vs_benchmark"] > TE_BREACH_THRESHOLD:
        triggers.append({
            "type": "tracking_error_breach",
            "asset": "portfolio",
            "severity": "HIGH",
            "detail": f"TE vs benchmark: {drift_analysis['te_vs_benchmark']*100:.1f}% > {TE_MAX*100:.0f}% limit"
        })

    # Determine overall recommendation
    severities = [t["severity"] for t in triggers]
    if "CRITICAL" in severities:
        recommendation = "IMMEDIATE_REBALANCE"
        urgency = "Immediate action required — IPS violation detected"
    elif "HIGH" in severities:
        recommendation = "REBALANCE_RECOMMENDED"
        urgency = "Rebalancing recommended within 5 business days"
    elif "MEDIUM" in severities:
        recommendation = "REBALANCE_CONSIDER"
        urgency = "Consider rebalancing at next scheduled review"
    elif "LOW" in severities:
        recommendation = "MONITOR"
        urgency = "Monitor at next review — no action required now"
    else:
        recommendation = "NO_ACTION"
        urgency = "Portfolio within tolerance — no rebalancing needed"

    return triggers, recommendation, urgency


def compute_trade_list(w_live, w_target):
    """
    Compute the trades needed to move from live to target portfolio.
    Returns list of trade instructions with estimated costs.
    """
    drift = w_target - w_live  # Positive = buy, negative = sell
    trades = []

    for i, slug in enumerate(SLUGS):
        d = float(drift[i])
        if abs(d) > 0.001:  # Only include meaningful trades
            direction = "BUY" if d > 0 else "SELL"
            est_cost_bps = abs(d) * TRANSACTION_COST_BPS * 100  # in basis points
            trades.append({
                "asset": slug,
                "direction": direction,
                "trade_size_pct": round(abs(d) * 100, 2),
                "from_weight": round(float(w_live[i]) * 100, 2),
                "to_weight": round(float(w_target[i]) * 100, 2),
                "estimated_cost_bps": round(est_cost_bps, 1),
            })

    # Sort by trade size descending
    trades.sort(key=lambda x: x["trade_size_pct"], reverse=True)

    total_turnover = sum(t["trade_size_pct"] for t in trades if t["direction"] == "BUY")
    total_cost_bps = sum(t["estimated_cost_bps"] for t in trades)

    return trades, round(total_turnover, 2), round(total_cost_bps, 1)


def write_rebalancing_report(
    date_str, drift_analysis, triggers, recommendation, urgency,
    trades, total_turnover, total_cost_bps, w_live, w_target, target_meta
):
    """Write rebalancing analysis to disk."""
    base = saa_path(date_str)
    out_dir = base / "rebalancing"
    out_dir.mkdir(parents=True, exist_ok=True)

    run_date = datetime.today().strftime("%Y-%m-%d")
    if date_str:
        run_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    target_date = target_meta.get("date", "unknown")

    # rebalancing-status.json
    status = {
        "date": run_date,
        "recommendation": recommendation,
        "urgency": urgency,
        "target_portfolio_date": target_date,
        "drift_summary": {
            "max_abs_drift": drift_analysis["max_abs_drift"],
            "max_drift_asset": drift_analysis["max_drift_asset"],
            "te_vs_target": drift_analysis["te_vs_target"],
            "te_vs_benchmark": drift_analysis["te_vs_benchmark"],
            "n_triggers": len(triggers),
        },
        "triggers": triggers,
        "trade_list": trades,
        "total_turnover_pct": total_turnover,
        "estimated_total_cost_bps": total_cost_bps,
    }

    with open(out_dir / "rebalancing-status.json", "w") as f:
        json.dump(status, f, indent=2)

    # rebalancing-report.md
    trigger_rows = "\n".join(
        f"| {t['severity']:<8} | {t['type']:<25} | {t['detail'][:70]} |"
        for t in triggers
    ) or "| — | No triggers | Portfolio within all thresholds |"

    trade_rows = "\n".join(
        f"| {t['asset']:<25} | {t['direction']:<4} | {t['from_weight']:>6.2f}% | "
        f"{t['to_weight']:>6.2f}% | {t['trade_size_pct']:>6.2f}% | {t['estimated_cost_bps']:>6.1f} bps |"
        for t in trades[:15]  # Show top 15 trades
    ) or "| — | — | No trades required | — |"

    # Category summary
    cat_rows = "\n".join(
        f"| {cat:<20} | {d['live_weight']*100:.1f}% | {d['target_weight']*100:.1f}% | "
        f"{d['drift']*100:+.1f}% | [{d['ips_bounds'][0]*100:.0f}%, {d['ips_bounds'][1]*100:.0f}%] | "
        f"{'OK' if d['ips_ok'] else 'BREACH'} |"
        for cat, d in drift_analysis["category_drift"].items()
    )

    report = f"""# Rebalancing Monitor Report

**Date**: {run_date}
**Target Portfolio Date**: {target_date}
**Recommendation**: **{recommendation}**
**Urgency**: {urgency}

---

## Drift Summary

| Metric                    | Value    |
|---------------------------|----------|
| Max Absolute Drift        | {drift_analysis['max_abs_drift']*100:.2f}% ({drift_analysis['max_drift_asset']}) |
| TE vs Target Portfolio    | {drift_analysis['te_vs_target']*100:.2f}% |
| TE vs Benchmark (60/40)   | {drift_analysis['te_vs_benchmark']*100:.2f}% |
| Rebalancing Triggers      | {len(triggers)} |

---

## Rebalancing Triggers

| Severity | Trigger Type              | Detail                                                 |
|----------|---------------------------|--------------------------------------------------------|
{trigger_rows}

---

## Category Allocation

| Category             | Live    | Target  | Drift   | IPS Range         | Status  |
|----------------------|---------|---------|---------|-------------------|---------|
{cat_rows}

---

## Required Trades (Top 15)

| Asset Class               | Dir. | From    | To      | Size    | Est. Cost |
|---------------------------|------|---------|---------|---------|-----------|
{trade_rows}

**Total Turnover**: {total_turnover:.1f}%
**Estimated Total Cost**: {total_cost_bps:.0f} bps

---

## Thresholds Used

| Threshold                 | Value    |
|---------------------------|----------|
| Absolute drift trigger    | {ABS_DRIFT_THRESHOLD*100:.0f}% |
| Relative drift trigger    | {REL_DRIFT_THRESHOLD*100:.0f}% of target |
| TE breach threshold       | {TE_BREACH_THRESHOLD*100:.0f}% |
| Transaction cost estimate | {TRANSACTION_COST_BPS} bps/unit |

---

*Generated by apex-plugin-strategy-saa rebalancing-monitor on {run_date}*
"""

    with open(out_dir / "rebalancing-report.md", "w") as f:
        f.write(report)

    print(f"Rebalancing report saved to: {out_dir}")
    return out_dir


def main():
    date_str = parse_date_arg()
    print(f"[rebalancing-monitor] Running for date: {date_str or 'today'}")

    # Find live portfolio path
    portfolio_path = None
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--portfolio" and i + 1 < len(args):
            portfolio_path = args[i + 1]
        elif arg.startswith("--portfolio="):
            portfolio_path = arg.split("=", 1)[1]

    # Load target portfolio
    try:
        w_target, target_meta = load_target_portfolio(date_str)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Load live portfolio
    if portfolio_path:
        try:
            w_live, _ = load_live_portfolio(portfolio_path)
        except FileNotFoundError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Warning: No --portfolio provided. Comparing target vs benchmark (60/40).", file=sys.stderr)
        w_live = W_BENCH.copy()

    # Load covariance for TE computation
    try:
        Sigma, _ = load_covariance(date_str)
    except FileNotFoundError as e:
        print(f"Warning: Could not load covariance matrix: {e}", file=sys.stderr)
        Sigma = np.eye(N) * 0.04  # Fallback

    print("[rebalancing-monitor] Analyzing drift...")
    drift_analysis = analyze_drift(w_live, w_target, Sigma)

    print("[rebalancing-monitor] Checking rebalancing triggers...")
    triggers, recommendation, urgency = determine_rebalancing_triggers(
        drift_analysis, w_live, w_target
    )

    print("[rebalancing-monitor] Computing trade list...")
    trades, total_turnover, total_cost_bps = compute_trade_list(w_live, w_target)

    print("[rebalancing-monitor] Writing report...")
    write_rebalancing_report(
        date_str, drift_analysis, triggers, recommendation, urgency,
        trades, total_turnover, total_cost_bps, w_live, w_target, target_meta
    )

    print(f"[rebalancing-monitor] Done.")
    print(f"  Recommendation: {recommendation}")
    print(f"  Urgency: {urgency}")
    print(f"  Triggers: {len(triggers)}")
    print(f"  Max drift: {drift_analysis['max_abs_drift']*100:.1f}% ({drift_analysis['max_drift_asset']})")
    print(f"  Total turnover needed: {total_turnover:.1f}%")
    print(f"  Estimated cost: {total_cost_bps:.0f} bps")


if __name__ == "__main__":
    main()
