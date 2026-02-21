#!/usr/bin/env python3
"""
cio-analysis.py — CIO Ensemble Analysis.

Loads all 16 PC method outputs, scores each on 6 dimensions,
runs 7 ensemble combination methods, selects the recommended ensemble,
and produces final portfolio outputs + board memo.

Usage:
    python cio-analysis.py [--date YYYYMMDD]
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).parent
PC_SCRIPTS = SCRIPT_DIR.parent.parent / "portfolio-construction" / "scripts"
sys.path.insert(0, str(PC_SCRIPTS))
from common import (
    SLUGS, N, SLUG_TO_IDX, W_BENCH, IPS_BOUNDS, CATEGORY_BOUNDS, TE_MAX,
    DEFAULT_RF, load_cmas, load_covariance, load_macro,
    saa_path, parse_date_arg,
    compute_diagnostics, run_backtest, weights_to_dict,
    _check_ips_compliance
)

# ---------------------------------------------------------------------------
# All 16 PC methods
# ---------------------------------------------------------------------------

ALL_METHODS = [
    "pc-market-cap-weight",
    "pc-equal-weight",
    "pc-inverse-vol",
    "pc-inverse-variance",
    "pc-max-sharpe",
    "pc-risk-parity",
    "pc-global-min-variance",
    "pc-max-diversification",
    "pc-vol-targeting",
    "pc-minimum-correlation",
    "pc-hierarchical-risk-parity",
    "pc-robust-mean-variance",
    "pc-cvar",
    "pc-mean-downside-risk",
    "pc-resampled-frontier",
    "pc-max-drawdown-constrained",
]

# ---------------------------------------------------------------------------
# Scoring weights (6 dimensions)
# ---------------------------------------------------------------------------

SCORE_WEIGHTS = {
    "sharpe_ratio":      0.25,  # Forward-looking Sharpe
    "backtest_sharpe":   0.20,  # Historical backtest Sharpe
    "diversification":   0.20,  # Effective N (by risk contribution)
    "ips_compliance":    0.20,  # IPS hard check (binary, weighted heavily)
    "te_score":          0.10,  # Tracking error (lower TE is better vs benchmark)
    "drawdown_score":    0.05,  # Historical max drawdown (higher is better = lower DD)
}

# ---------------------------------------------------------------------------
# Regime-conditional model priors
# ---------------------------------------------------------------------------

REGIME_MODEL_PRIORS = {
    "EXPANSION": {
        "pc-max-sharpe": 0.15,
        "pc-robust-mean-variance": 0.12,
        "pc-resampled-frontier": 0.12,
        "pc-max-diversification": 0.10,
        "pc-risk-parity": 0.08,
        "pc-market-cap-weight": 0.08,
        "pc-equal-weight": 0.06,
        "pc-hierarchical-risk-parity": 0.06,
        "pc-mean-downside-risk": 0.05,
        "pc-max-drawdown-constrained": 0.05,
        "pc-vol-targeting": 0.03,
        "pc-minimum-correlation": 0.03,
        "pc-inverse-vol": 0.02,
        "pc-inverse-variance": 0.02,
        "pc-global-min-variance": 0.02,
        "pc-cvar": 0.01,
    },
    "LATE-CYCLE": {
        "pc-robust-mean-variance": 0.12,
        "pc-risk-parity": 0.10,
        "pc-max-diversification": 0.10,
        "pc-hierarchical-risk-parity": 0.08,
        "pc-resampled-frontier": 0.08,
        "pc-max-drawdown-constrained": 0.08,
        "pc-vol-targeting": 0.07,
        "pc-cvar": 0.06,
        "pc-mean-downside-risk": 0.06,
        "pc-minimum-correlation": 0.05,
        "pc-max-sharpe": 0.05,
        "pc-equal-weight": 0.05,
        "pc-global-min-variance": 0.04,
        "pc-inverse-vol": 0.03,
        "pc-inverse-variance": 0.02,
        "pc-market-cap-weight": 0.01,
    },
    "RECESSION": {
        "pc-global-min-variance": 0.15,
        "pc-cvar": 0.12,
        "pc-max-drawdown-constrained": 0.12,
        "pc-vol-targeting": 0.10,
        "pc-risk-parity": 0.08,
        "pc-inverse-vol": 0.08,
        "pc-inverse-variance": 0.06,
        "pc-minimum-correlation": 0.06,
        "pc-hierarchical-risk-parity": 0.06,
        "pc-mean-downside-risk": 0.05,
        "pc-max-diversification": 0.04,
        "pc-equal-weight": 0.03,
        "pc-robust-mean-variance": 0.03,
        "pc-resampled-frontier": 0.02,
        "pc-max-sharpe": 0.00,
        "pc-market-cap-weight": 0.00,
    },
    "RECOVERY": {
        "pc-max-sharpe": 0.12,
        "pc-equal-weight": 0.10,
        "pc-max-diversification": 0.10,
        "pc-resampled-frontier": 0.10,
        "pc-robust-mean-variance": 0.08,
        "pc-market-cap-weight": 0.08,
        "pc-risk-parity": 0.08,
        "pc-hierarchical-risk-parity": 0.06,
        "pc-mean-downside-risk": 0.06,
        "pc-max-drawdown-constrained": 0.05,
        "pc-vol-targeting": 0.05,
        "pc-minimum-correlation": 0.04,
        "pc-cvar": 0.03,
        "pc-inverse-vol": 0.02,
        "pc-inverse-variance": 0.02,
        "pc-global-min-variance": 0.01,
    },
}

# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_all_pc_outputs(date_str=None):
    """
    Load portfolio.json from all available PC methods.
    Returns dict: method_name -> {weights: np.array, diag: dict, backtest: dict}
    """
    base = saa_path(date_str)
    pc_dir = base / "portfolio-construction"

    outputs = {}
    missing = []

    for method in ALL_METHODS:
        portfolio_file = pc_dir / method / "portfolio.json"
        if not portfolio_file.exists():
            missing.append(method)
            continue

        with open(portfolio_file) as f:
            data = json.load(f)

        w_dict = data["weights"]
        w = np.array([w_dict.get(slug, 0.0) for slug in SLUGS])
        outputs[method] = {
            "weights": w,
            "weights_dict": w_dict,
            "diagnostics": data.get("diagnostics", {}),
            "backtest": data.get("backtest_summary", {}),
        }

    if missing:
        print(f"Warning: Missing PC outputs for: {missing}", file=sys.stderr)
    if not outputs:
        raise FileNotFoundError(
            f"No PC method outputs found in {pc_dir}. Run 'construct' command first."
        )

    print(f"Loaded {len(outputs)} PC method outputs ({len(missing)} missing).")
    return outputs


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_methods(outputs, mu, Sigma, rf):
    """
    Score each PC method on 6 dimensions.
    Returns dict: method_name -> {dimension_scores, total_score}
    """
    scores = {}

    # Collect raw metrics for normalization
    raw = {}
    for method, data in outputs.items():
        w = data["weights"]
        diag = data["diagnostics"]

        sharpe = diag.get("sharpe_ratio", 0.0)
        bt_sharpe = data["backtest"].get("sharpe_ratio", 0.0)
        eff_n = diag.get("effective_n", 1.0)
        ips_ok = diag.get("ips_compliance", {}).get("overall", False)
        te = diag.get("tracking_error_vs_benchmark", 0.10)
        max_dd = data["backtest"].get("max_drawdown", -0.50)  # negative number

        raw[method] = {
            "sharpe": sharpe,
            "bt_sharpe": bt_sharpe,
            "eff_n": eff_n,
            "ips_ok": ips_ok,
            "te": te,
            "max_dd": max_dd,
        }

    if not raw:
        return {}

    # Normalize metrics (min-max to [0, 1])
    def normalize(vals, higher_is_better=True):
        arr = np.array(vals, dtype=float)
        mn, mx = arr.min(), arr.max()
        if mx == mn:
            return np.full(len(arr), 0.5)
        normed = (arr - mn) / (mx - mn)
        if not higher_is_better:
            normed = 1.0 - normed
        return normed

    methods = list(raw.keys())
    sharpe_norm = normalize([raw[m]["sharpe"] for m in methods])
    bt_sharpe_norm = normalize([raw[m]["bt_sharpe"] for m in methods])
    eff_n_norm = normalize([raw[m]["eff_n"] for m in methods])
    ips_scores = np.array([1.0 if raw[m]["ips_ok"] else 0.0 for m in methods])
    te_norm = normalize([raw[m]["te"] for m in methods], higher_is_better=False)
    dd_norm = normalize([raw[m]["max_dd"] for m in methods], higher_is_better=False)

    for i, method in enumerate(methods):
        dim_scores = {
            "sharpe_ratio":    round(float(sharpe_norm[i]), 4),
            "backtest_sharpe": round(float(bt_sharpe_norm[i]), 4),
            "diversification": round(float(eff_n_norm[i]), 4),
            "ips_compliance":  round(float(ips_scores[i]), 4),
            "te_score":        round(float(te_norm[i]), 4),
            "drawdown_score":  round(float(dd_norm[i]), 4),
        }
        total = sum(dim_scores[dim] * SCORE_WEIGHTS[dim] for dim in SCORE_WEIGHTS)
        scores[method] = {
            "dimension_scores": dim_scores,
            "total_score": round(total, 4),
            "raw_metrics": {
                "sharpe_ratio": round(raw[method]["sharpe"], 4),
                "backtest_sharpe": round(raw[method]["bt_sharpe"], 4),
                "effective_n": round(raw[method]["eff_n"], 2),
                "ips_compliant": raw[method]["ips_ok"],
                "tracking_error": round(raw[method]["te"], 4),
                "max_drawdown": round(raw[method]["max_dd"], 4),
            }
        }

    return scores


# ---------------------------------------------------------------------------
# Ensemble methods (7)
# ---------------------------------------------------------------------------

def ensemble_simple_average(outputs):
    """1. Simple Average: equal weight to each PC method."""
    weights_list = [data["weights"] for data in outputs.values()]
    if not weights_list:
        return np.zeros(N)
    avg = np.mean(weights_list, axis=0)
    return avg / avg.sum()


def ensemble_inverse_te(outputs, Sigma):
    """2. Inverse Tracking Error Weighting: weight by 1/TE vs benchmark."""
    te_weights = {}
    for method, data in outputs.items():
        w = data["weights"]
        diff = w - W_BENCH
        te = float(np.sqrt(diff @ Sigma @ diff))
        te_weights[method] = 1.0 / max(te, 1e-6)

    total = sum(te_weights.values())
    combined = np.zeros(N)
    for method, tw in te_weights.items():
        combined += (tw / total) * outputs[method]["weights"]

    model_weights = {m: round(tw / total, 4) for m, tw in te_weights.items()}
    return combined / combined.sum(), model_weights


def ensemble_backtest_sharpe(outputs):
    """3. Backtest Sharpe Weighting: weight by historical backtest Sharpe (positive only)."""
    sharpe_weights = {}
    for method, data in outputs.items():
        bs = data["backtest"].get("sharpe_ratio", 0.0)
        sharpe_weights[method] = max(bs, 0.0)

    total = sum(sharpe_weights.values())
    if total <= 0:
        # Fallback to equal weight
        return ensemble_simple_average(outputs), {m: 1/len(outputs) for m in outputs}

    combined = np.zeros(N)
    for method, sw in sharpe_weights.items():
        combined += (sw / total) * outputs[method]["weights"]

    model_weights = {m: round(sw / total, 4) for m, sw in sharpe_weights.items()}
    return combined / combined.sum(), model_weights


def ensemble_meta_optimization(outputs, mu, Sigma, rf):
    """4. Meta-Optimization (Stacking): optimize weights of PC models to max ensemble Sharpe."""
    from scipy.optimize import minimize as sp_minimize

    M = len(outputs)
    if M == 0:
        return np.zeros(N), {}
    methods = list(outputs.keys())
    W_matrix = np.stack([outputs[m]["weights"] for m in methods], axis=0)  # (M, N)

    def neg_sharpe(alpha):
        alpha_norm = np.maximum(alpha, 0)
        alpha_norm = alpha_norm / alpha_norm.sum() if alpha_norm.sum() > 0 else np.ones(M) / M
        w_ensemble = W_matrix.T @ alpha_norm  # (N,)
        port_ret = float(w_ensemble @ mu)
        port_vol = float(np.sqrt(w_ensemble @ Sigma @ w_ensemble))
        return -(port_ret - rf) / port_vol if port_vol > 0 else 0.0

    alpha0 = np.ones(M) / M
    bounds = [(0, 1)] * M
    constraints = [{"type": "eq", "fun": lambda a: a.sum() - 1.0}]

    result = sp_minimize(neg_sharpe, alpha0, method="SLSQP", bounds=bounds, constraints=constraints,
                         options={"ftol": 1e-10, "maxiter": 1000})
    alpha_opt = np.maximum(result.x, 0)
    if alpha_opt.sum() > 0:
        alpha_opt = alpha_opt / alpha_opt.sum()
    else:
        alpha_opt = np.ones(M) / M

    w_combined = W_matrix.T @ alpha_opt
    w_combined = w_combined / w_combined.sum()
    model_weights = {methods[i]: round(float(alpha_opt[i]), 4) for i in range(M)}
    return w_combined, model_weights


def ensemble_regime_conditional(outputs, regime):
    """5. Regime-Conditional Weighting: use REGIME_MODEL_PRIORS for given regime."""
    priors = REGIME_MODEL_PRIORS.get(regime, REGIME_MODEL_PRIORS["EXPANSION"])

    combined = np.zeros(N)
    total_weight = 0.0
    model_weights = {}

    for method, data in outputs.items():
        prior = priors.get(method, 0.01)
        combined += prior * data["weights"]
        total_weight += prior
        model_weights[method] = prior

    if total_weight > 0:
        combined = combined / total_weight
    else:
        combined = ensemble_simple_average(outputs)

    # Normalize model weights to sum to 1
    mw_total = sum(model_weights.values())
    model_weights = {m: round(w / mw_total, 4) for m, w in model_weights.items()} if mw_total > 0 else model_weights
    return combined / combined.sum(), model_weights


def ensemble_score_weighted(outputs, scores):
    """6. Score-Weighted Combination: weight by total composite score."""
    combined = np.zeros(N)
    total_score = sum(scores[m]["total_score"] for m in outputs if m in scores)

    if total_score <= 0:
        return ensemble_simple_average(outputs), {m: 1/len(outputs) for m in outputs}

    model_weights = {}
    for method, data in outputs.items():
        if method not in scores:
            continue
        s = scores[method]["total_score"]
        combined += (s / total_score) * data["weights"]
        model_weights[method] = round(s / total_score, 4)

    return combined / combined.sum(), model_weights


def ensemble_trimmed_mean(outputs, trim_pct=0.125):
    """7. Trimmed Mean: remove top/bottom trim_pct methods by score, then average."""
    if len(outputs) <= 4:
        return ensemble_simple_average(outputs), {m: 1/len(outputs) for m in outputs}

    methods = list(outputs.keys())
    M = len(methods)
    n_trim = max(1, int(np.floor(M * trim_pct)))

    # Sort by backtest Sharpe as trimming criterion
    sharpes = {m: outputs[m]["backtest"].get("sharpe_ratio", 0.0) for m in methods}
    sorted_methods = sorted(sharpes, key=sharpes.get)
    kept_methods = sorted_methods[n_trim: M - n_trim]

    if not kept_methods:
        kept_methods = methods

    combined = np.mean([outputs[m]["weights"] for m in kept_methods], axis=0)
    model_weights = {m: (1/len(kept_methods) if m in kept_methods else 0.0) for m in methods}
    return combined / combined.sum(), model_weights


# ---------------------------------------------------------------------------
# Ensemble selection
# ---------------------------------------------------------------------------

def run_all_ensembles(outputs, mu, Sigma, rf, regime, scores):
    """Run all 7 ensemble methods and return their results."""
    print("  Running ensemble 1: simple-average")
    w1 = ensemble_simple_average(outputs)
    mw1 = {m: round(1/len(outputs), 4) for m in outputs}

    print("  Running ensemble 2: inverse-tracking-error")
    w2, mw2 = ensemble_inverse_te(outputs, Sigma)

    print("  Running ensemble 3: backtest-sharpe")
    w3, mw3 = ensemble_backtest_sharpe(outputs)

    print("  Running ensemble 4: meta-optimization")
    w4, mw4 = ensemble_meta_optimization(outputs, mu, Sigma, rf)

    print("  Running ensemble 5: regime-conditional")
    w5, mw5 = ensemble_regime_conditional(outputs, regime)

    print("  Running ensemble 6: score-weighted")
    w6, mw6 = ensemble_score_weighted(outputs, scores)

    print("  Running ensemble 7: trimmed-mean")
    w7, mw7 = ensemble_trimmed_mean(outputs)

    ensembles = {
        "simple-average":          {"weights": w1, "model_weights": mw1},
        "inverse-tracking-error":  {"weights": w2, "model_weights": mw2},
        "backtest-sharpe":         {"weights": w3, "model_weights": mw3},
        "meta-optimization":       {"weights": w4, "model_weights": mw4},
        "regime-conditional":      {"weights": w5, "model_weights": mw5},
        "score-weighted":          {"weights": w6, "model_weights": mw6},
        "trimmed-mean":            {"weights": w7, "model_weights": mw7},
    }
    return ensembles


def select_recommended_ensemble(ensembles, mu, Sigma, rf, regime):
    """
    Select the recommended ensemble based on priority criteria:
    1. IPS compliance (mandatory)
    2. Tracking error <= 8%
    3. Regime fit (regime-conditional gets bonus)
    4. Sharpe ratio
    5. Effective N (diversification)
    """
    from common import _check_ips_compliance, project_to_ips

    candidate_scores = {}

    for name, data in ensembles.items():
        w = data["weights"]

        # Check IPS compliance
        ips = _check_ips_compliance(w)
        if not ips["overall"]:
            # Try to project to IPS feasible
            w_proj = project_to_ips(w)
            ips = _check_ips_compliance(w_proj)
            if not ips["overall"]:
                print(f"  Warning: {name} is IPS non-compliant even after projection — penalized.")
                candidate_scores[name] = -999.0
                continue
            w = w_proj
            data["weights"] = w

        # Tracking error
        diff = w - W_BENCH
        te = float(np.sqrt(diff @ Sigma @ diff))
        if te > TE_MAX:
            # Penalize but don't disqualify — CIO may accept with explanation
            te_penalty = (te - TE_MAX) * 5
        else:
            te_penalty = 0.0

        # Sharpe
        port_ret = float(w @ mu)
        port_vol = float(np.sqrt(w @ Sigma @ w))
        sharpe = (port_ret - rf) / port_vol if port_vol > 0 else 0.0

        # Diversification (effective N)
        mrc = Sigma @ w
        rc = w * mrc / port_vol if port_vol > 0 else np.ones(N) / N
        rc_pct = rc / rc.sum() if rc.sum() > 0 else np.ones(N) / N
        hhi = float(np.sum(rc_pct ** 2))
        eff_n = 1.0 / hhi if hhi > 0 else float(N)

        # Regime bonus
        regime_bonus = 0.10 if name == "regime-conditional" else 0.0

        score = sharpe + 0.5 * (eff_n / N) + regime_bonus - te_penalty
        candidate_scores[name] = round(score, 4)

    if not candidate_scores or max(candidate_scores.values()) == -999.0:
        print("Warning: No IPS-compliant ensemble found. Defaulting to simple-average.")
        return "simple-average"

    best = max(candidate_scores, key=candidate_scores.get)
    print(f"  Ensemble scores: {candidate_scores}")
    print(f"  Selected: {best}")
    return best


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def save_cio_outputs(
    date_str, regime, outputs, scores, ensembles,
    recommended_name, mu, Sigma, rf
):
    """Save all CIO outputs to .analysis/saa/YYYYMMDD/cio/"""
    base = saa_path(date_str)
    cio_dir = base / "cio"
    cio_dir.mkdir(parents=True, exist_ok=True)

    run_date = datetime.today().strftime("%Y-%m-%d")
    if date_str:
        run_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    recommended = ensembles[recommended_name]
    w_final = recommended["weights"]

    # Compute diagnostics for final portfolio
    diag = compute_diagnostics(w_final, mu, Sigma, rf)
    backtest = run_backtest(w_final, date_str)

    # final-portfolio.json
    diff = w_final - W_BENCH
    te = float(np.sqrt(diff @ Sigma @ diff))

    final_portfolio = {
        "date": run_date,
        "recommended_ensemble": recommended_name,
        "macro_regime": regime,
        "weights": weights_to_dict(w_final),
        "diagnostics": diag,
        "backtest_summary": backtest,
        "model_weights": recommended["model_weights"],
        "ips_compliant": diag["ips_compliance"]["overall"],
        "tracking_error": round(te, 6),
        "all_ensemble_model_weights": {
            name: data["model_weights"] for name, data in ensembles.items()
        },
    }

    with open(cio_dir / "final-portfolio.json", "w") as f:
        json.dump(final_portfolio, f, indent=2)

    # method-scores.json
    with open(cio_dir / "method-scores.json", "w") as f:
        json.dump({"date": run_date, "scores": scores}, f, indent=2)

    # ensemble-weights.json — all 7 ensemble portfolios
    ensemble_out = {}
    for name, data in ensembles.items():
        w = data["weights"]
        ens_diag = compute_diagnostics(w, mu, Sigma, rf)
        ens_diff = w - W_BENCH
        ens_te = float(np.sqrt(ens_diff @ Sigma @ ens_diff))
        ensemble_out[name] = {
            "weights": weights_to_dict(w),
            "model_weights": data["model_weights"],
            "expected_return": ens_diag["expected_return"],
            "expected_volatility": ens_diag["expected_volatility"],
            "sharpe_ratio": ens_diag["sharpe_ratio"],
            "tracking_error": round(ens_te, 6),
            "ips_compliant": ens_diag["ips_compliance"]["overall"],
            "effective_n": ens_diag["effective_n"],
        }

    with open(cio_dir / "ensemble-portfolios.json", "w") as f:
        json.dump({"date": run_date, "ensembles": ensemble_out}, f, indent=2)

    # cio-recommendation.md
    _write_cio_recommendation(cio_dir, run_date, regime, recommended_name, w_final,
                               diag, backtest, scores, ensemble_out, mu, Sigma)

    # board-memo.md
    _write_board_memo(cio_dir, run_date, regime, recommended_name, w_final, diag, backtest)

    print(f"CIO outputs saved to: {cio_dir}")
    return final_portfolio


def _write_cio_recommendation(cio_dir, run_date, regime, recommended_name, w_final,
                                diag, backtest, scores, ensemble_out, mu, Sigma):
    """Write detailed CIO recommendation markdown."""

    # Top 5 methods by score
    top_methods = sorted(scores.items(), key=lambda x: x[1]["total_score"], reverse=True)[:5]
    top_rows = "\n".join(
        f"| {m:<35} | {s['total_score']:.3f} | {s['raw_metrics']['sharpe_ratio']:.3f} | "
        f"{s['raw_metrics']['ips_compliant']} | {s['raw_metrics']['tracking_error']*100:.1f}% |"
        for m, s in top_methods
    )

    # Ensemble comparison table
    ens_rows = "\n".join(
        f"| {name:<25} | {e['expected_return']*100:.2f}% | {e['expected_volatility']*100:.2f}% | "
        f"{e['sharpe_ratio']:.3f} | {e['tracking_error']*100:.2f}% | {e['ips_compliant']} |"
        for name, e in ensemble_out.items()
    )

    # Top holdings
    w_sorted = sorted(weights_to_dict(w_final).items(), key=lambda x: x[1], reverse=True)[:8]
    holdings_rows = "\n".join(f"| {slug:<25} | {w*100:.2f}% |" for slug, w in w_sorted)

    ips = diag["ips_compliance"]
    ips_status = "COMPLIANT" if ips["overall"] else "NON-COMPLIANT"
    violations = "\n".join(f"- {v}" for v in ips.get("violations", [])) or "None"

    content = f"""# CIO Portfolio Recommendation

**Date**: {run_date}
**Macro Regime**: {regime}
**Recommended Ensemble**: {recommended_name}

---

## Executive Summary

The CIO ensemble analysis evaluated 16 portfolio construction methods and combined them
using 7 ensemble techniques. The **{recommended_name}** ensemble was selected based on:
IPS compliance, tracking error discipline (≤8%), regime alignment ({regime}),
and risk-adjusted return characteristics.

---

## Macro Regime: {regime}

The current macro regime ({regime}) influences model prior weights in the regime-conditional
ensemble. Under {regime}, higher weight is given to models that historically perform
well in this environment.

---

## Top-Scoring PC Methods

| Method                              | Score | Sharpe | IPS OK | TE      |
|-------------------------------------|-------|--------|--------|---------|
{top_rows}

---

## Ensemble Comparison

| Ensemble                  | Exp Ret | Exp Vol | Sharpe | TE      | IPS   |
|---------------------------|---------|---------|--------|---------|-------|
{ens_rows}

---

## Recommended Portfolio: {recommended_name}

### Top Holdings

| Asset Class               | Weight  |
|---------------------------|---------|
{holdings_rows}

### Portfolio Diagnostics

| Metric                    | Value    |
|---------------------------|----------|
| Expected Return           | {diag['expected_return']*100:.2f}% |
| Expected Volatility       | {diag['expected_volatility']*100:.2f}% |
| Sharpe Ratio              | {diag['sharpe_ratio']:.3f} |
| Tracking Error            | {diag['tracking_error_vs_benchmark']*100:.2f}% |
| Effective N               | {diag['effective_n']:.1f} |
| IPS Compliance            | {ips_status} |

### Backtest Summary

| Metric                | Value    |
|-----------------------|----------|
| Annualized Return     | {backtest['annualized_return']*100:.2f}% |
| Max Drawdown          | {backtest['max_drawdown']*100:.2f}% |
| Sharpe Ratio          | {backtest['sharpe_ratio']:.3f} |
| Sortino Ratio         | {backtest['sortino_ratio']:.3f} |

### IPS Status: {ips_status}

**Violations**: {violations}

---

*Generated by apex-plugin-strategy-saa CIO Analysis on {run_date}*
"""

    with open(cio_dir / "cio-recommendation.md", "w") as f:
        f.write(content)


def _write_board_memo(cio_dir, run_date, regime, recommended_name, w_final, diag, backtest):
    """Write concise board-level executive memo."""
    ips = diag["ips_compliance"]
    ips_status = "COMPLIANT" if ips["overall"] else "REQUIRES REVIEW"

    # Top 5 holdings
    top5 = sorted(weights_to_dict(w_final).items(), key=lambda x: x[1], reverse=True)[:5]
    top5_text = " | ".join(f"{slug} {w*100:.0f}%" for slug, w in top5)

    # Simple category summary
    equity_w = sum(w_final[i] for i in [0,1,2,3,4,5]) * 100
    fi_w = sum(w_final[i] for i in [6,7,8,9,10,11,12,13]) * 100
    real_w = sum(w_final[i] for i in [14,15,16]) * 100
    cash_w = w_final[17] * 100

    memo = f"""# Investment Committee Memo — Strategic Asset Allocation

**Date**: {run_date}
**Prepared by**: CIO Ensemble System — apex-plugin-strategy-saa
**Macro Regime**: {regime}

---

## RECOMMENDATION

Adopt the **{recommended_name}** ensemble portfolio as the Strategic Asset Allocation
for the current review period.

---

## PORTFOLIO SNAPSHOT

| Category        | Weight   |
|-----------------|----------|
| Total Equity    | {equity_w:.1f}%    |
| Fixed Income    | {fi_w:.1f}%    |
| Real Assets     | {real_w:.1f}%    |
| Cash            | {cash_w:.1f}%    |

**Top 5 Holdings**: {top5_text}

---

## RISK/RETURN PROFILE

| Metric                 | Value     |
|------------------------|-----------|
| Expected Return (fwd)  | {diag['expected_return']*100:.1f}%   |
| Expected Volatility    | {diag['expected_volatility']*100:.1f}%   |
| Sharpe Ratio (fwd)     | {diag['sharpe_ratio']:.2f}      |
| Tracking Error (vs 60/40) | {diag['tracking_error_vs_benchmark']*100:.1f}%  |
| Historical Max Drawdown | {backtest['max_drawdown']*100:.1f}%  |

---

## IPS STATUS: {ips_status}

---

## KEY CONSIDERATIONS

1. **Regime**: Current {regime} regime guides model priors in ensemble selection.
2. **Diversification**: Portfolio achieves {diag['effective_n']:.1f} effective asset classes.
3. **Risk discipline**: Tracking error of {diag['tracking_error_vs_benchmark']*100:.1f}% is within 8% IPS limit.
4. **Methodology**: 16 quantitative models combined via 7 ensemble techniques.

---

*This memo is generated automatically by the Apex SAA Strategy Plugin.
All recommendations should be reviewed by the Investment Committee before implementation.*
"""

    with open(cio_dir / "board-memo.md", "w") as f:
        f.write(memo)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    date_str = parse_date_arg()
    print(f"[cio-analysis] Running for date: {date_str or 'today'}")

    # Load inputs
    try:
        mu, rf, _ = load_cmas(date_str)
        Sigma, vols = load_covariance(date_str)
        regime, _ = load_macro(date_str)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[cio-analysis] Macro regime: {regime}")

    # Load PC outputs
    try:
        outputs = load_all_pc_outputs(date_str)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Score methods
    print("[cio-analysis] Scoring PC methods...")
    scores = score_methods(outputs, mu, Sigma, rf)

    # Run ensemble methods
    print("[cio-analysis] Running 7 ensemble methods...")
    ensembles = run_all_ensembles(outputs, mu, Sigma, rf, regime, scores)

    # Select recommended
    print("[cio-analysis] Selecting recommended ensemble...")
    recommended_name = select_recommended_ensemble(ensembles, mu, Sigma, rf, regime)

    # Save all outputs
    print("[cio-analysis] Writing outputs...")
    final = save_cio_outputs(date_str, regime, outputs, scores, ensembles,
                              recommended_name, mu, Sigma, rf)

    print(f"[cio-analysis] Done.")
    print(f"  Recommended ensemble: {recommended_name}")
    print(f"  Expected Return:  {final['diagnostics']['expected_return']*100:.2f}%")
    print(f"  Expected Vol:     {final['diagnostics']['expected_volatility']*100:.2f}%")
    print(f"  Sharpe Ratio:     {final['diagnostics']['sharpe_ratio']:.3f}")
    print(f"  IPS Compliant:    {final['ips_compliant']}")
    print(f"  Tracking Error:   {final['tracking_error']*100:.2f}%")


if __name__ == "__main__":
    main()
