#!/usr/bin/env python3
"""
risk-analysis.py — Portfolio risk analysis and stress testing.

Loads the final portfolio (or a specified PC method output) and runs:
1. Five historical stress scenarios
2. Factor sensitivity analysis
3. Correlation stability analysis
4. Tail risk metrics (VaR, CVaR at multiple confidence levels)
5. Scenario attribution (which assets drive stress losses)

Usage:
    python risk-analysis.py [--date YYYYMMDD] [--portfolio PATH]
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Add portfolio-construction/scripts to path for common utilities
SCRIPT_DIR = Path(__file__).parent
PC_SCRIPTS = SCRIPT_DIR.parent.parent / "portfolio-construction" / "scripts"
sys.path.insert(0, str(PC_SCRIPTS))
from common import (
    SLUGS, N, SLUG_TO_IDX, W_BENCH, IPS_BOUNDS, DEFAULT_RF,
    load_cmas, load_covariance, load_macro, saa_path, parse_date_arg
)

# ---------------------------------------------------------------------------
# Historical stress scenarios
# ---------------------------------------------------------------------------

STRESS_SCENARIOS = {
    "gfc_2007_2009": {
        "name": "Global Financial Crisis (Oct 2007 – Feb 2009)",
        "description": "Severe credit crisis, banking system near-collapse, equity markets -50%",
        "duration_months": 17,
        "asset_shocks": {
            # Asset returns during the scenario (approximate annualized equivalents)
            "us-large-cap":          -0.50,
            "us-small-cap":          -0.58,
            "us-value":              -0.54,
            "us-growth":             -0.45,
            "intl-developed":        -0.55,
            "emerging-markets":      -0.65,
            "short-treasury":        +0.06,
            "interm-treasury":       +0.16,
            "long-treasury":         +0.25,
            "ig-corps":              -0.15,
            "hy-corps":              -0.40,
            "intl-sovereign-bonds":  +0.10,
            "intl-corps":            -0.12,
            "usd-em-debt":           -0.30,
            "reits":                 -0.70,
            "gold":                  +0.15,
            "commodities":           -0.30,
            "cash":                  +0.04,
        }
    },
    "covid_crash_2020": {
        "name": "COVID-19 Crash (Feb – Mar 2020)",
        "description": "Fastest bear market in history, global lockdowns, cross-asset selling",
        "duration_months": 2,
        "asset_shocks": {
            "us-large-cap":          -0.34,
            "us-small-cap":          -0.42,
            "us-value":              -0.40,
            "us-growth":             -0.28,
            "intl-developed":        -0.35,
            "emerging-markets":      -0.32,
            "short-treasury":        +0.02,
            "interm-treasury":       +0.07,
            "long-treasury":         +0.15,
            "ig-corps":              -0.12,
            "hy-corps":              -0.22,
            "intl-sovereign-bonds":  +0.04,
            "intl-corps":            -0.10,
            "usd-em-debt":           -0.18,
            "reits":                 -0.45,
            "gold":                  -0.02,
            "commodities":           -0.35,
            "cash":                  +0.004,
        }
    },
    "rate_shock_2022": {
        "name": "Rate Shock / Inflation Surge (Jan – Oct 2022)",
        "description": "Fed rapid hiking cycle: stocks AND bonds fell simultaneously",
        "duration_months": 10,
        "asset_shocks": {
            "us-large-cap":          -0.24,
            "us-small-cap":          -0.27,
            "us-value":              -0.12,
            "us-growth":             -0.35,
            "intl-developed":        -0.27,
            "emerging-markets":      -0.30,
            "short-treasury":        -0.03,
            "interm-treasury":       -0.15,
            "long-treasury":         -0.32,
            "ig-corps":              -0.18,
            "hy-corps":              -0.14,
            "intl-sovereign-bonds":  -0.20,
            "intl-corps":            -0.16,
            "usd-em-debt":           -0.17,
            "reits":                 -0.30,
            "gold":                  -0.10,
            "commodities":           +0.15,
            "cash":                  +0.018,
        }
    },
    "dot_com_2000_2002": {
        "name": "Dot-Com Bust (Mar 2000 – Oct 2002)",
        "description": "Tech bubble collapse, prolonged equity bear market, flight to bonds",
        "duration_months": 31,
        "asset_shocks": {
            "us-large-cap":          -0.49,
            "us-small-cap":          -0.44,
            "us-value":              -0.28,
            "us-growth":             -0.66,
            "intl-developed":        -0.47,
            "emerging-markets":      -0.35,
            "short-treasury":        +0.10,
            "interm-treasury":       +0.22,
            "long-treasury":         +0.30,
            "ig-corps":              +0.15,
            "hy-corps":              -0.05,
            "intl-sovereign-bonds":  +0.18,
            "intl-corps":            +0.12,
            "usd-em-debt":           +0.08,
            "reits":                 +0.12,
            "gold":                  +0.10,
            "commodities":           -0.05,
            "cash":                  +0.06,
        }
    },
    "taper_tantrum_2013": {
        "name": "Taper Tantrum (May – Jun 2013)",
        "description": "Fed signals QE tapering; bond selloff while equities flat",
        "duration_months": 2,
        "asset_shocks": {
            "us-large-cap":          +0.01,
            "us-small-cap":          +0.02,
            "us-value":              +0.02,
            "us-growth":             +0.01,
            "intl-developed":        -0.04,
            "emerging-markets":      -0.12,
            "short-treasury":        -0.01,
            "interm-treasury":       -0.05,
            "long-treasury":         -0.10,
            "ig-corps":              -0.05,
            "hy-corps":              -0.03,
            "intl-sovereign-bonds":  -0.07,
            "intl-corps":            -0.06,
            "usd-em-debt":           -0.08,
            "reits":                 -0.10,
            "gold":                  -0.12,
            "commodities":           -0.04,
            "cash":                  +0.001,
        }
    },
}

# ---------------------------------------------------------------------------
# Hypothetical forward-looking scenarios
# ---------------------------------------------------------------------------

HYPOTHETICAL_SCENARIOS = {
    "severe_recession": {
        "name": "Severe Recession (-35% equity shock)",
        "asset_shocks": {
            "us-large-cap": -0.35, "us-small-cap": -0.45, "us-value": -0.32,
            "us-growth": -0.40, "intl-developed": -0.35, "emerging-markets": -0.45,
            "short-treasury": +0.04, "interm-treasury": +0.12, "long-treasury": +0.22,
            "ig-corps": -0.08, "hy-corps": -0.25, "intl-sovereign-bonds": +0.08,
            "intl-corps": -0.06, "usd-em-debt": -0.20, "reits": -0.40,
            "gold": +0.12, "commodities": -0.20, "cash": +0.04,
        }
    },
    "stagflation": {
        "name": "Stagflation (high inflation + recession)",
        "asset_shocks": {
            "us-large-cap": -0.25, "us-small-cap": -0.28, "us-value": -0.18,
            "us-growth": -0.32, "intl-developed": -0.22, "emerging-markets": -0.28,
            "short-treasury": -0.02, "interm-treasury": -0.12, "long-treasury": -0.25,
            "ig-corps": -0.15, "hy-corps": -0.18, "intl-sovereign-bonds": -0.15,
            "intl-corps": -0.12, "usd-em-debt": -0.12, "reits": -0.15,
            "gold": +0.20, "commodities": +0.25, "cash": +0.02,
        }
    },
    "rates_spike_300bps": {
        "name": "Interest Rate Spike +300bps",
        "asset_shocks": {
            "us-large-cap": -0.15, "us-small-cap": -0.12, "us-value": -0.08,
            "us-growth": -0.20, "intl-developed": -0.14, "emerging-markets": -0.18,
            "short-treasury": -0.06, "interm-treasury": -0.22, "long-treasury": -0.40,
            "ig-corps": -0.20, "hy-corps": -0.10, "intl-sovereign-bonds": -0.25,
            "intl-corps": -0.18, "usd-em-debt": -0.15, "reits": -0.20,
            "gold": -0.08, "commodities": +0.05, "cash": +0.03,
        }
    },
}


# ---------------------------------------------------------------------------
# Core analysis functions
# ---------------------------------------------------------------------------

def apply_stress_scenario(w, shocks):
    """Compute portfolio return under a stress scenario."""
    w = np.asarray(w, dtype=float)
    shock_vec = np.array([shocks.get(slug, 0.0) for slug in SLUGS])
    return float(w @ shock_vec)


def compute_var_cvar(w, Sigma, mu, confidence_levels=(0.90, 0.95, 0.99), n_sims=50000):
    """Compute VaR and CVaR at multiple confidence levels via Monte Carlo."""
    rng = np.random.default_rng(42)
    monthly_mu = mu / 12
    monthly_Sigma = Sigma / 12
    scenarios = rng.multivariate_normal(monthly_mu, monthly_Sigma, size=n_sims)
    port_returns = scenarios @ w
    annual_returns = port_returns * 12  # Scale to annual

    results = {}
    for conf in confidence_levels:
        var = float(np.percentile(annual_returns, (1 - conf) * 100))
        tail = annual_returns[annual_returns <= var]
        cvar = float(np.mean(tail)) if len(tail) > 0 else var
        results[f"var_{int(conf*100)}"] = round(var, 4)
        results[f"cvar_{int(conf*100)}"] = round(cvar, 4)

    return results


def compute_factor_sensitivities(w, Sigma):
    """
    Compute factor sensitivities via proxy betas:
    - Equity factor: vs 100% US large cap
    - Duration factor: vs 100% long treasury
    - Credit factor: vs 100% HY corps
    - Inflation factor: vs 100% commodities + gold blend
    """
    w = np.asarray(w, dtype=float)

    def portfolio_corr_with_factor(factor_w):
        """Correlation of portfolio with a factor portfolio."""
        port_var = w @ Sigma @ w
        factor_var = factor_w @ Sigma @ factor_w
        cross_cov = w @ Sigma @ factor_w
        if port_var <= 0 or factor_var <= 0:
            return 0.0
        corr = cross_cov / np.sqrt(port_var * factor_var)
        return float(np.clip(corr, -1, 1))

    # Equity factor
    eq_w = np.zeros(N)
    eq_w[0] = 1.0
    equity_beta = portfolio_corr_with_factor(eq_w)

    # Duration factor
    dur_w = np.zeros(N)
    dur_w[8] = 1.0  # long-treasury
    duration_beta = portfolio_corr_with_factor(dur_w)

    # Credit factor
    credit_w = np.zeros(N)
    credit_w[10] = 1.0  # hy-corps
    credit_beta = portfolio_corr_with_factor(credit_w)

    # Inflation factor (gold + commodities blend)
    infl_w = np.zeros(N)
    infl_w[15] = 0.5  # gold
    infl_w[16] = 0.5  # commodities
    inflation_beta = portfolio_corr_with_factor(infl_w)

    return {
        "equity_factor_exposure": round(equity_beta, 4),
        "duration_factor_exposure": round(duration_beta, 4),
        "credit_factor_exposure": round(credit_beta, 4),
        "inflation_factor_exposure": round(inflation_beta, 4),
    }


def scenario_attribution(w, shocks):
    """Break down scenario return by asset class contribution."""
    w = np.asarray(w, dtype=float)
    attributions = {}
    for i, slug in enumerate(SLUGS):
        shock = shocks.get(slug, 0.0)
        contribution = float(w[i] * shock)
        attributions[slug] = {
            "weight": round(float(w[i]), 4),
            "shock": round(shock, 4),
            "contribution": round(contribution, 4),
        }
    total = sum(v["contribution"] for v in attributions.values())
    return attributions, round(total, 4)


def run_full_risk_analysis(w, mu, Sigma, rf, date_str=None):
    """
    Run complete risk analysis on portfolio weights.
    Returns dict with all risk metrics.
    """
    w = np.asarray(w, dtype=float)

    print("  Running historical stress scenarios...")
    stress_results = {}
    for scenario_id, scenario in STRESS_SCENARIOS.items():
        shocks = scenario["asset_shocks"]
        port_return = apply_stress_scenario(w, shocks)
        bench_return = apply_stress_scenario(W_BENCH, shocks)
        attributions, total = scenario_attribution(w, shocks)
        stress_results[scenario_id] = {
            "name": scenario["name"],
            "description": scenario["description"],
            "duration_months": scenario["duration_months"],
            "portfolio_return": round(port_return, 4),
            "benchmark_return": round(bench_return, 4),
            "excess_vs_benchmark": round(port_return - bench_return, 4),
            "asset_attribution": attributions,
        }

    print("  Running hypothetical scenarios...")
    hypo_results = {}
    for scenario_id, scenario in HYPOTHETICAL_SCENARIOS.items():
        shocks = scenario["asset_shocks"]
        port_return = apply_stress_scenario(w, shocks)
        bench_return = apply_stress_scenario(W_BENCH, shocks)
        hypo_results[scenario_id] = {
            "name": scenario["name"],
            "portfolio_return": round(port_return, 4),
            "benchmark_return": round(bench_return, 4),
            "excess_vs_benchmark": round(port_return - bench_return, 4),
        }

    print("  Computing VaR/CVaR...")
    var_cvar = compute_var_cvar(w, Sigma, mu)

    print("  Computing factor sensitivities...")
    factor_sens = compute_factor_sensitivities(w, Sigma)

    # Tracking error and information ratio
    diff = w - W_BENCH
    te = float(np.sqrt(diff @ Sigma @ diff))
    port_ret = float(w @ mu)
    bench_ret = float(W_BENCH @ mu)
    ir = float((port_ret - bench_ret) / te) if te > 0 else 0.0

    # Concentration metrics
    hhi_weights = float(np.sum(w ** 2))
    effective_n_weights = 1.0 / hhi_weights if hhi_weights > 0 else N

    # Risk contribution Herfindahl
    port_vol = float(np.sqrt(w @ Sigma @ w))
    mrc = Sigma @ w
    rc = w * mrc / port_vol if port_vol > 0 else np.ones(N) / N
    rc_pct = rc / rc.sum() if rc.sum() > 0 else np.ones(N) / N
    hhi_risk = float(np.sum(rc_pct ** 2))
    effective_n_risk = 1.0 / hhi_risk if hhi_risk > 0 else N

    return {
        "summary": {
            "expected_return": round(port_ret, 6),
            "expected_volatility": round(port_vol, 6),
            "tracking_error": round(te, 6),
            "information_ratio": round(ir, 4),
            "effective_n_by_weight": round(effective_n_weights, 2),
            "effective_n_by_risk": round(effective_n_risk, 2),
        },
        "tail_risk": var_cvar,
        "factor_sensitivities": factor_sens,
        "historical_stress_scenarios": stress_results,
        "hypothetical_scenarios": hypo_results,
    }


def write_risk_report(risk_results, date_str=None):
    """Write risk analysis outputs to disk."""
    base = saa_path(date_str)
    out_dir = base / "risk-analysis"
    out_dir.mkdir(parents=True, exist_ok=True)

    run_date = datetime.today().strftime("%Y-%m-%d")
    if date_str:
        run_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    # risk-analysis.json
    full_output = {"date": run_date, **risk_results}
    with open(out_dir / "risk-analysis.json", "w") as f:
        json.dump(full_output, f, indent=2)

    # Write stress scenario summary markdown
    summary = risk_results["summary"]
    tail = risk_results["tail_risk"]
    factors = risk_results["factor_sensitivities"]
    stress = risk_results["historical_stress_scenarios"]

    stress_rows = []
    for sid, s in stress.items():
        stress_rows.append(
            f"| {s['name'][:45]:<45} | {s['portfolio_return']*100:+6.1f}% | "
            f"{s['benchmark_return']*100:+6.1f}% | {s['excess_vs_benchmark']*100:+6.1f}% |"
        )
    stress_table = "\n".join(stress_rows)

    hypo = risk_results["hypothetical_scenarios"]
    hypo_rows = []
    for sid, s in hypo.items():
        hypo_rows.append(
            f"| {s['name']:<45} | {s['portfolio_return']*100:+6.1f}% | "
            f"{s['benchmark_return']*100:+6.1f}% | {s['excess_vs_benchmark']*100:+6.1f}% |"
        )
    hypo_table = "\n".join(hypo_rows)

    report = f"""# Risk Analysis Report

**Date**: {run_date}

---

## Portfolio Summary

| Metric                    | Value    |
|---------------------------|----------|
| Expected Return           | {summary['expected_return']*100:.2f}% |
| Expected Volatility       | {summary['expected_volatility']*100:.2f}% |
| Tracking Error            | {summary['tracking_error']*100:.2f}% |
| Information Ratio         | {summary['information_ratio']:.3f} |
| Effective N (by weight)   | {summary['effective_n_by_weight']:.1f} |
| Effective N (by risk)     | {summary['effective_n_by_risk']:.1f} |

---

## Tail Risk (Annual, Monte Carlo)

| Metric  | 90% CI  | 95% CI  | 99% CI  |
|---------|---------|---------|---------|
| VaR     | {tail['var_90']*100:.1f}%  | {tail['var_95']*100:.1f}%  | {tail['var_99']*100:.1f}%  |
| CVaR    | {tail['cvar_90']*100:.1f}%  | {tail['cvar_95']*100:.1f}%  | {tail['cvar_99']*100:.1f}%  |

---

## Factor Sensitivities

| Factor                    | Correlation |
|---------------------------|-------------|
| Equity                    | {factors['equity_factor_exposure']:.3f} |
| Duration (rates)          | {factors['duration_factor_exposure']:.3f} |
| Credit                    | {factors['credit_factor_exposure']:.3f} |
| Inflation (gold+commod.)  | {factors['inflation_factor_exposure']:.3f} |

---

## Historical Stress Scenarios

| Scenario                                      | Portfolio | Benchmark | Excess  |
|-----------------------------------------------|-----------|-----------|---------|
{stress_table}

---

## Hypothetical Scenarios

| Scenario                                      | Portfolio | Benchmark | Excess  |
|-----------------------------------------------|-----------|-----------|---------|
{hypo_table}

---

*Generated by apex-plugin-strategy-saa risk-analysis on {run_date}*
"""

    with open(out_dir / "risk-report.md", "w") as f:
        f.write(report)

    print(f"Risk analysis saved to: {out_dir}")
    return out_dir


def main():
    date_str = parse_date_arg()
    print(f"[risk-analysis] Loading portfolio for date: {date_str or 'today'}")

    # Load inputs
    try:
        mu, rf, _ = load_cmas(date_str)
        Sigma, vols = load_covariance(date_str)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Load final portfolio if it exists; otherwise load first available PC method
    base = saa_path(date_str)
    final_portfolio_path = base / "cio" / "final-portfolio.json"

    if final_portfolio_path.exists():
        with open(final_portfolio_path) as f:
            final_data = json.load(f)
        weights_dict = final_data["weights"]
        source = "final-portfolio (CIO)"
    else:
        # Try to load first available PC output
        pc_dir = base / "portfolio-construction"
        w_source = None
        for slug in pc_dir.iterdir() if pc_dir.exists() else []:
            portfolio_file = pc_dir / slug.name / "portfolio.json"
            if portfolio_file.exists():
                with open(portfolio_file) as f:
                    data = json.load(f)
                weights_dict = data["weights"]
                w_source = slug.name
                break

        if w_source is None:
            print("ERROR: No portfolio outputs found. Run 'construct' command first.", file=sys.stderr)
            sys.exit(1)
        source = f"PC method: {w_source}"

    print(f"[risk-analysis] Analyzing portfolio from: {source}")
    w = np.array([weights_dict.get(slug, 0.0) for slug in SLUGS])

    risk_results = run_full_risk_analysis(w, mu, Sigma, rf, date_str)
    write_risk_report(risk_results, date_str)

    summary = risk_results["summary"]
    print(f"[risk-analysis] Done.")
    print(f"  Expected Return: {summary['expected_return']*100:.2f}%")
    print(f"  Expected Vol:    {summary['expected_volatility']*100:.2f}%")
    print(f"  Tracking Error:  {summary['tracking_error']*100:.2f}%")
    print(f"  CVaR (95%):      {risk_results['tail_risk']['cvar_95']*100:.1f}%")

    worst = min(
        risk_results["historical_stress_scenarios"].values(),
        key=lambda s: s["portfolio_return"]
    )
    print(f"  Worst stress:    {worst['name']}: {worst['portfolio_return']*100:.1f}%")


if __name__ == "__main__":
    main()
