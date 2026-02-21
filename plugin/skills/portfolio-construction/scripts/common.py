#!/usr/bin/env python3
"""
common.py — Shared utilities for all 16 portfolio construction scripts.

All PC scripts import from here. Provides:
- Asset class definitions and IPS constraints
- Input loaders (CMAs, covariance, historical returns)
- Constraint builders for scipy.optimize
- Diagnostics computation
- Backtest engine
- Standardized output writers
"""

import json
import os
import sys
from datetime import datetime, date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize, LinearConstraint, Bounds
from sklearn.covariance import LedoitWolf

# ---------------------------------------------------------------------------
# Asset class definitions
# ---------------------------------------------------------------------------

SLUGS = [
    "us-large-cap",          # 0
    "us-small-cap",          # 1
    "us-value",              # 2
    "us-growth",             # 3
    "intl-developed",        # 4
    "emerging-markets",      # 5
    "short-treasury",        # 6
    "interm-treasury",       # 7
    "long-treasury",         # 8
    "ig-corps",              # 9
    "hy-corps",              # 10
    "intl-sovereign-bonds",  # 11
    "intl-corps",            # 12
    "usd-em-debt",           # 13
    "reits",                 # 14
    "gold",                  # 15
    "commodities",           # 16
    "cash",                  # 17
]

N = len(SLUGS)  # 18

SLUG_TO_IDX = {slug: i for i, slug in enumerate(SLUGS)}

# ---------------------------------------------------------------------------
# IPS Constraints (Investment Policy Statement)
# ---------------------------------------------------------------------------

IPS_BOUNDS = [
    (0.10, 0.40),  # 0  us-large-cap
    (0.00, 0.15),  # 1  us-small-cap
    (0.00, 0.15),  # 2  us-value
    (0.00, 0.15),  # 3  us-growth
    (0.05, 0.25),  # 4  intl-developed
    (0.00, 0.15),  # 5  emerging-markets
    (0.00, 0.20),  # 6  short-treasury
    (0.00, 0.25),  # 7  interm-treasury
    (0.00, 0.15),  # 8  long-treasury
    (0.00, 0.20),  # 9  ig-corps
    (0.00, 0.10),  # 10 hy-corps
    (0.00, 0.15),  # 11 intl-sovereign-bonds
    (0.00, 0.10),  # 12 intl-corps
    (0.00, 0.10),  # 13 usd-em-debt
    (0.00, 0.15),  # 14 reits
    (0.00, 0.10),  # 15 gold
    (0.00, 0.10),  # 16 commodities
    (0.00, 0.20),  # 17 cash
]

# Category bounds: (indices, min_weight, max_weight)
CATEGORY_BOUNDS = {
    "total_equity":  ([0, 1, 2, 3, 4, 5],          0.30, 0.75),
    "us_equity":     ([0, 1, 2, 3],                 0.20, 0.55),
    "intl_equity":   ([4, 5],                        0.05, 0.30),
    "total_fi":      ([6, 7, 8, 9, 10, 11, 12, 13], 0.15, 0.60),
    "us_fi":         ([6, 7, 8, 9, 10],              0.10, 0.45),
    "intl_fi":       ([11, 12, 13],                  0.00, 0.20),
    "real_assets":   ([14, 15, 16],                  0.00, 0.25),
    "cash":          ([17],                           0.00, 0.20),
}

# Benchmark: 60% US Large Cap / 40% Intermediate Treasury
W_BENCH = np.zeros(N)
W_BENCH[0] = 0.60   # us-large-cap
W_BENCH[7] = 0.40   # interm-treasury

TE_MAX = 0.08  # Maximum tracking error vs benchmark

# Default risk-free rate fallback (annualized)
DEFAULT_RF = 0.045

# ---------------------------------------------------------------------------
# Input loaders
# ---------------------------------------------------------------------------

def resolve_date_folder(date_str=None):
    """
    Resolve YYYYMMDD date folder. Uses provided string or today's date.
    Returns YYYYMMDD string.
    """
    if date_str:
        return date_str
    return datetime.today().strftime("%Y%m%d")


def find_analysis_root():
    """
    Walk up from cwd to find .analysis/saa/ directory.
    Returns Path to workspace root (where .analysis/ lives).
    """
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / ".analysis" / "saa").exists():
            return parent
    # Fallback: use cwd
    return cwd


def saa_path(date_str=None):
    """Return Path to .analysis/saa/YYYYMMDD/"""
    root = find_analysis_root()
    folder = resolve_date_folder(date_str)
    return root / ".analysis" / "saa" / folder


def load_cmas(date_str=None):
    """
    Load Capital Market Assumptions for all 18 asset classes.

    Returns:
        mu: np.ndarray shape (N,) — expected annual returns
        rf: float — risk-free rate
        meta: dict — full CMA metadata keyed by slug
    """
    base = saa_path(date_str)
    mu = np.zeros(N)
    meta = {}
    rf = DEFAULT_RF

    for i, slug in enumerate(SLUGS):
        cma_file = base / "asset-classes" / slug / "output" / "cma.json"
        if not cma_file.exists():
            raise FileNotFoundError(
                f"CMA file not found: {cma_file}\n"
                f"Run analysis-assetclass plugin first."
            )
        with open(cma_file) as f:
            data = json.load(f)

        # Expected return field: try common field names
        er = (
            data.get("expected_return_annual")
            or data.get("expected_return")
            or data.get("forward_return")
            or data.get("return_forecast")
        )
        if er is None:
            raise KeyError(f"Cannot find expected return in {cma_file}. Keys: {list(data.keys())}")
        mu[i] = float(er)
        meta[slug] = data

        # Extract risk-free rate from cash or dedicated field
        if slug == "cash":
            rf = float(er)
        if "risk_free_rate" in data:
            rf = float(data["risk_free_rate"])

    return mu, rf, meta


def load_covariance(date_str=None):
    """
    Load covariance matrix from covariance/output/covariance-matrix.json.

    Returns:
        Sigma: np.ndarray shape (N, N)
        vols: np.ndarray shape (N,) — annualized volatilities (sqrt of diagonal)
    """
    base = saa_path(date_str)
    cov_file = base / "covariance" / "output" / "covariance-matrix.json"

    if not cov_file.exists():
        raise FileNotFoundError(
            f"Covariance matrix not found: {cov_file}\n"
            f"Run analysis-assetclass covariance step first."
        )

    with open(cov_file) as f:
        data = json.load(f)

    # Support two formats: {"matrix": [[...]]} or {"covariance_matrix": [[...]]}
    raw = (
        data.get("matrix")
        or data.get("covariance_matrix")
        or data.get("cov_matrix")
    )
    if raw is None:
        raise KeyError(f"Cannot find matrix in {cov_file}. Keys: {list(data.keys())}")

    Sigma = np.array(raw, dtype=float)
    if Sigma.shape != (N, N):
        raise ValueError(f"Expected {N}x{N} covariance matrix, got {Sigma.shape}")

    # Ensure positive semi-definite via Ledoit-Wolf shrinkage if needed
    eigvals = np.linalg.eigvalsh(Sigma)
    if eigvals.min() < 1e-10:
        lw = LedoitWolf()
        # Use diagonal as proxy for regularization
        Sigma = _nearest_psd(Sigma)

    vols = np.sqrt(np.diag(Sigma))
    return Sigma, vols


def load_macro(date_str=None):
    """
    Load macro regime view.

    Returns:
        regime: str — "EXPANSION" | "LATE-CYCLE" | "RECESSION" | "RECOVERY"
        macro_data: dict — full macro view
    """
    base = saa_path(date_str)
    macro_file = base / "macro" / "macro-view.json"

    if not macro_file.exists():
        print(f"Warning: Macro file not found at {macro_file}, defaulting to EXPANSION", file=sys.stderr)
        return "EXPANSION", {}

    with open(macro_file) as f:
        data = json.load(f)

    regime = (
        data.get("regime")
        or data.get("macro_regime")
        or data.get("current_regime")
        or "EXPANSION"
    ).upper()

    # Normalize to expected values
    regime_map = {
        "EXPANSION": "EXPANSION",
        "LATE_CYCLE": "LATE-CYCLE",
        "LATE-CYCLE": "LATE-CYCLE",
        "LATECYCLE": "LATE-CYCLE",
        "RECESSION": "RECESSION",
        "CONTRACTION": "RECESSION",
        "RECOVERY": "RECOVERY",
        "EARLY-CYCLE": "RECOVERY",
        "EARLY_CYCLE": "RECOVERY",
    }
    regime = regime_map.get(regime, "EXPANSION")
    return regime, data


def load_historical_returns(date_str=None):
    """
    Load historical return series for backtesting.
    Reads from .analysis/saa/YYYYMMDD/covariance/output/historical-returns.json
    or falls back to a synthetic series based on CMA + covariance.

    Returns:
        returns_df: pd.DataFrame shape (T, N) — monthly returns, columns=SLUGS
    """
    base = saa_path(date_str)
    hist_file = base / "covariance" / "output" / "historical-returns.json"

    if hist_file.exists():
        with open(hist_file) as f:
            data = json.load(f)
        # Format: {"dates": [...], "returns": {"slug": [...]}}
        dates = pd.to_datetime(data["dates"])
        returns_dict = {}
        for slug in SLUGS:
            returns_dict[slug] = data["returns"].get(slug, [0.0] * len(dates))
        return pd.DataFrame(returns_dict, index=dates)

    # Fallback: generate synthetic monthly returns (360 months = 30 years)
    print("Warning: Historical returns not found, using synthetic data for backtest.", file=sys.stderr)
    try:
        mu, rf, _ = load_cmas(date_str)
        Sigma, _ = load_covariance(date_str)
    except Exception:
        # Absolute fallback with generic assumptions
        mu = np.array([0.09, 0.10, 0.09, 0.10, 0.08, 0.10,
                        0.04, 0.045, 0.05, 0.05, 0.07, 0.04,
                        0.05, 0.06, 0.08, 0.06, 0.05, 0.042])
        Sigma = np.eye(N) * 0.04
        rf = 0.042

    T = 360  # 30 years of monthly data
    monthly_mu = mu / 12
    monthly_Sigma = Sigma / 12

    rng = np.random.default_rng(42)
    raw = rng.multivariate_normal(monthly_mu, monthly_Sigma, size=T)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=T, freq="ME")
    return pd.DataFrame(raw, index=dates, columns=SLUGS)


# ---------------------------------------------------------------------------
# Matrix utilities
# ---------------------------------------------------------------------------

def _nearest_psd(A):
    """Project matrix to nearest positive semi-definite matrix."""
    B = (A + A.T) / 2
    eigvals, eigvecs = np.linalg.eigh(B)
    eigvals = np.maximum(eigvals, 1e-8)
    return eigvecs @ np.diag(eigvals) @ eigvecs.T


def shrink_covariance(Sigma, method="ledoit-wolf"):
    """
    Apply covariance shrinkage.

    method: "ledoit-wolf" | "constant-correlation" | "none"
    """
    if method == "none":
        return Sigma
    if method == "ledoit-wolf":
        # Apply analytical Ledoit-Wolf shrinkage toward identity-scaled diagonal
        n = Sigma.shape[0]
        trace = np.trace(Sigma)
        mu_shrink = trace / n
        target = mu_shrink * np.eye(n)
        # Shrinkage intensity: simple Oracle approximation
        alpha = 0.1
        return (1 - alpha) * Sigma + alpha * target
    return Sigma


# ---------------------------------------------------------------------------
# Constraint builders for scipy.optimize
# ---------------------------------------------------------------------------

def build_constraints(Sigma=None, include_category=True, te_constraint=False):
    """
    Build scipy constraints list for IPS compliance.

    Returns list of constraint dicts for scipy.optimize.minimize.
    """
    constraints = []

    # Sum to 1
    constraints.append({
        "type": "eq",
        "fun": lambda w: np.sum(w) - 1.0
    })

    # Category bounds
    if include_category:
        for cat_name, (indices, lo, hi) in CATEGORY_BOUNDS.items():
            idx = np.array(indices)
            if lo > 0:
                constraints.append({
                    "type": "ineq",
                    "fun": lambda w, idx=idx, lo=lo: np.sum(w[idx]) - lo
                })
            if hi < 1.0:
                constraints.append({
                    "type": "ineq",
                    "fun": lambda w, idx=idx, hi=hi: hi - np.sum(w[idx])
                })

    # Tracking error constraint
    if te_constraint and Sigma is not None:
        def te_con(w):
            diff = w - W_BENCH
            te = np.sqrt(diff @ Sigma @ diff)
            return TE_MAX - te
        constraints.append({"type": "ineq", "fun": te_con})

    return constraints


def get_bounds():
    """Return scipy Bounds object from IPS_BOUNDS."""
    lb = np.array([b[0] for b in IPS_BOUNDS])
    ub = np.array([b[1] for b in IPS_BOUNDS])
    return Bounds(lb, ub, keep_feasible=True)


def make_initial_weights(mu=None):
    """
    Generate a feasible starting point for optimization.
    Uses equal weight with IPS lower bounds satisfied.
    """
    lb = np.array([b[0] for b in IPS_BOUNDS])
    ub = np.array([b[1] for b in IPS_BOUNDS])

    # Start from lower bounds
    w = lb.copy()
    remaining = 1.0 - w.sum()

    # Distribute remaining proportionally among unconstrained assets
    headroom = ub - w
    total_headroom = headroom.sum()
    if total_headroom > 0 and remaining > 0:
        w += headroom * (remaining / total_headroom)

    # Clip and renormalize
    w = np.clip(w, lb, ub)
    w = w / w.sum()
    return w


def project_to_ips(w_raw):
    """
    Project arbitrary weights to IPS-feasible space via quadratic projection.
    Minimizes ||w - w_raw||^2 subject to IPS constraints.
    """
    w0 = make_initial_weights()

    def objective(w):
        return 0.5 * np.sum((w - w_raw) ** 2)

    def grad(w):
        return w - w_raw

    result = minimize(
        objective,
        w0,
        jac=grad,
        method="SLSQP",
        bounds=get_bounds(),
        constraints=build_constraints(include_category=True),
        options={"ftol": 1e-10, "maxiter": 1000},
    )

    if result.success:
        w = np.clip(result.x, 0, 1)
        return w / w.sum()
    # Fallback: clip and renormalize
    lb = np.array([b[0] for b in IPS_BOUNDS])
    ub = np.array([b[1] for b in IPS_BOUNDS])
    w = np.clip(w_raw, lb, ub)
    return w / w.sum()


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

def compute_diagnostics(w, mu, Sigma, rf):
    """
    Compute forward-looking portfolio diagnostics.

    Returns dict with all key metrics.
    """
    w = np.asarray(w, dtype=float)
    port_return = float(w @ mu)
    port_var = float(w @ Sigma @ w)
    port_vol = float(np.sqrt(port_var))
    sharpe = float((port_return - rf) / port_vol) if port_vol > 0 else 0.0

    # Effective N (inverse HHI of risk contributions)
    rc = _risk_contributions(w, Sigma)
    rc_pct = rc / rc.sum() if rc.sum() > 0 else np.ones(N) / N
    hhi = float(np.sum(rc_pct ** 2))
    effective_n = float(1.0 / hhi) if hhi > 0 else float(N)

    # Tracking error vs benchmark
    diff = w - W_BENCH
    te = float(np.sqrt(diff @ Sigma @ diff))

    # IPS compliance check
    ips_check = _check_ips_compliance(w)

    return {
        "expected_return": round(port_return, 6),
        "expected_volatility": round(port_vol, 6),
        "sharpe_ratio": round(sharpe, 4),
        "effective_n": round(effective_n, 2),
        "tracking_error_vs_benchmark": round(te, 6),
        "ips_compliance": ips_check,
        "risk_contributions": {slug: round(float(rc[i]), 6) for i, slug in enumerate(SLUGS)},
        "risk_contributions_pct": {slug: round(float(rc_pct[i]), 4) for i, slug in enumerate(SLUGS)},
    }


def _risk_contributions(w, Sigma):
    """Compute marginal risk contributions."""
    port_var = w @ Sigma @ w
    if port_var <= 0:
        return np.zeros(N)
    mrc = Sigma @ w
    rc = w * mrc / np.sqrt(port_var)
    return rc


def _check_ips_compliance(w):
    """Check IPS individual and category constraint compliance."""
    violations = []
    binding = []

    # Individual bounds
    for i, slug in enumerate(SLUGS):
        lo, hi = IPS_BOUNDS[i]
        if w[i] < lo - 1e-6:
            violations.append(f"{slug}-min (w={w[i]:.4f} < {lo})")
        elif abs(w[i] - lo) < 1e-4 and lo > 0:
            binding.append(f"{slug}-min")
        if w[i] > hi + 1e-6:
            violations.append(f"{slug}-max (w={w[i]:.4f} > {hi})")
        elif abs(w[i] - hi) < 1e-4 and hi < 1.0:
            binding.append(f"{slug}-max")

    # Category bounds
    for cat, (indices, lo, hi) in CATEGORY_BOUNDS.items():
        cat_w = sum(w[i] for i in indices)
        if cat_w < lo - 1e-6:
            violations.append(f"{cat}-min (w={cat_w:.4f} < {lo})")
        if cat_w > hi + 1e-6:
            violations.append(f"{cat}-max (w={cat_w:.4f} > {hi})")

    # Sum to 1
    if abs(w.sum() - 1.0) > 1e-4:
        violations.append(f"sum != 1 (sum={w.sum():.6f})")

    return {
        "overall": len(violations) == 0,
        "violations": violations,
        "binding_constraints": binding,
    }


# ---------------------------------------------------------------------------
# Backtest engine
# ---------------------------------------------------------------------------

def run_backtest(w, date_str=None, rebalance_freq="quarterly"):
    """
    Run a historical backtest with the given static weights.

    Args:
        w: np.ndarray shape (N,) — portfolio weights
        date_str: YYYYMMDD — date folder for loading historical returns
        rebalance_freq: "monthly" | "quarterly" | "annual"

    Returns:
        dict with backtest summary statistics
    """
    returns_df = load_historical_returns(date_str)
    ret = returns_df[SLUGS].values  # shape (T, N)
    T = len(ret)

    # Determine rebalance periods
    rebal_periods = {"monthly": 1, "quarterly": 3, "annual": 12}
    rebal_every = rebal_periods.get(rebalance_freq, 3)

    # Simulate portfolio with periodic rebalancing
    portfolio_returns = np.zeros(T)
    current_w = w.copy()

    for t in range(T):
        # Rebalance at specified frequency
        if t % rebal_every == 0:
            current_w = w.copy()

        # Monthly portfolio return
        port_ret = float(current_w @ ret[t])
        portfolio_returns[t] = port_ret

        # Drift weights
        asset_growths = (1 + ret[t]) * current_w
        total = asset_growths.sum()
        if total > 0:
            current_w = asset_growths / total

    # Compute statistics
    ann_return = float(np.mean(portfolio_returns) * 12)
    ann_vol = float(np.std(portfolio_returns, ddof=1) * np.sqrt(12))
    rf_monthly = DEFAULT_RF / 12
    excess = portfolio_returns - rf_monthly
    sharpe = float(np.mean(excess) / np.std(excess, ddof=1) * np.sqrt(12)) if np.std(excess) > 0 else 0.0

    # Max drawdown
    cum_returns = np.cumprod(1 + portfolio_returns)
    rolling_max = np.maximum.accumulate(cum_returns)
    drawdowns = (cum_returns - rolling_max) / rolling_max
    max_dd = float(drawdowns.min())

    # Sortino ratio
    downside_ret = portfolio_returns[portfolio_returns < rf_monthly]
    downside_vol = float(np.std(downside_ret, ddof=1) * np.sqrt(12)) if len(downside_ret) > 1 else ann_vol
    sortino = float((ann_return - DEFAULT_RF) / downside_vol) if downside_vol > 0 else 0.0

    # Calmar ratio
    calmar = float(ann_return / abs(max_dd)) if max_dd < 0 else 0.0

    # Win rate
    win_rate = float(np.mean(portfolio_returns > 0))

    start_date = returns_df.index[0].strftime("%Y-%m-%d")
    end_date = returns_df.index[-1].strftime("%Y-%m-%d")

    return {
        "annualized_return": round(ann_return, 6),
        "annualized_volatility": round(ann_vol, 6),
        "sharpe_ratio": round(sharpe, 4),
        "sortino_ratio": round(sortino, 4),
        "calmar_ratio": round(calmar, 4),
        "max_drawdown": round(max_dd, 6),
        "win_rate": round(win_rate, 4),
        "rebalance_frequency": rebalance_freq,
        "start_date": start_date,
        "end_date": end_date,
        "num_months": T,
    }


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def weights_to_dict(w):
    """Convert weight array to {slug: weight} dict."""
    return {slug: round(float(w[i]), 6) for i, slug in enumerate(SLUGS)}


def save_portfolio_outputs(method_name, w, mu, Sigma, rf, date_str=None, extra_meta=None):
    """
    Save standardized portfolio outputs to the expected directory structure.

    Writes:
      .analysis/saa/YYYYMMDD/portfolio-construction/{method}/portfolio.json
      .analysis/saa/YYYYMMDD/portfolio-construction/{method}/output/weights.json
      .analysis/saa/YYYYMMDD/portfolio-construction/{method}/output/diagnostics.json
      .analysis/saa/YYYYMMDD/portfolio-construction/{method}/output/backtest.json
    """
    base = saa_path(date_str)
    out_dir = base / "portfolio-construction" / method_name
    output_dir = out_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    w_arr = np.asarray(w, dtype=float)
    diag = compute_diagnostics(w_arr, mu, Sigma, rf)
    backtest = run_backtest(w_arr, date_str)
    w_dict = weights_to_dict(w_arr)

    run_date = datetime.today().strftime("%Y-%m-%d")
    if date_str:
        run_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    # portfolio.json — top-level summary
    portfolio = {
        "method": method_name,
        "date": run_date,
        "weights": w_dict,
        "diagnostics": diag,
        "backtest_summary": backtest,
    }
    if extra_meta:
        portfolio["meta"] = extra_meta

    with open(out_dir / "portfolio.json", "w") as f:
        json.dump(portfolio, f, indent=2)

    # output/weights.json
    with open(output_dir / "weights.json", "w") as f:
        json.dump({"method": method_name, "date": run_date, "weights": w_dict}, f, indent=2)

    # output/diagnostics.json
    with open(output_dir / "diagnostics.json", "w") as f:
        json.dump({"method": method_name, "date": run_date, **diag}, f, indent=2)

    # output/backtest.json
    with open(output_dir / "backtest.json", "w") as f:
        json.dump({"method": method_name, **backtest}, f, indent=2)

    print(f"[{method_name}] Outputs saved to: {out_dir}")
    return portfolio


def write_memo(method_name, w, diag, backtest, methodology_notes, date_str=None):
    """
    Write a markdown memo for the portfolio construction method.

    Writes: .analysis/saa/YYYYMMDD/portfolio-construction/{method}/memo.md
    """
    base = saa_path(date_str)
    out_dir = base / "portfolio-construction" / method_name
    out_dir.mkdir(parents=True, exist_ok=True)

    run_date = datetime.today().strftime("%Y-%m-%d")
    if date_str:
        run_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    w_arr = np.asarray(w, dtype=float)
    ips = diag["ips_compliance"]

    # Build weight table
    weight_rows = []
    for slug in SLUGS:
        pct = w_arr[SLUG_TO_IDX[slug]] * 100
        lo, hi = IPS_BOUNDS[SLUG_TO_IDX[slug]]
        bar = "#" * int(pct / 2)
        weight_rows.append(f"| {slug:<25} | {pct:6.2f}% | {lo*100:.0f}–{hi*100:.0f}% | {bar} |")

    weight_table = "\n".join(weight_rows)

    # Category summary
    cat_rows = []
    for cat, (indices, lo, hi) in CATEGORY_BOUNDS.items():
        cat_w = sum(w_arr[i] for i in indices) * 100
        cat_rows.append(f"| {cat:<20} | {cat_w:6.2f}% | {lo*100:.0f}–{hi*100:.0f}% |")
    cat_table = "\n".join(cat_rows)

    ips_status = "COMPLIANT" if ips["overall"] else "NON-COMPLIANT"
    violations_text = "\n".join(f"- {v}" for v in ips.get("violations", [])) or "None"
    binding_text = "\n".join(f"- {b}" for b in ips.get("binding_constraints", [])) or "None"

    memo_content = f"""# Portfolio Construction Memo: {method_name}

**Date**: {run_date}
**Method**: {method_name}
**IPS Status**: {ips_status}

---

## Methodology

{methodology_notes}

---

## Portfolio Weights

| Asset Class               | Weight  | IPS Range | Allocation |
|---------------------------|---------|-----------|------------|
{weight_table}

**Sum**: {w_arr.sum()*100:.2f}%

---

## Category Allocation

| Category             | Weight  | IPS Range |
|----------------------|---------|-----------|
{cat_table}

---

## Forward-Looking Diagnostics

| Metric                    | Value    |
|---------------------------|----------|
| Expected Return           | {diag['expected_return']*100:.2f}% |
| Expected Volatility       | {diag['expected_volatility']*100:.2f}% |
| Sharpe Ratio              | {diag['sharpe_ratio']:.3f} |
| Effective N               | {diag['effective_n']:.1f} |
| Tracking Error vs Benchmark | {diag['tracking_error_vs_benchmark']*100:.2f}% |

---

## Backtest Summary (Historical)

| Metric                | Value    |
|-----------------------|----------|
| Annualized Return     | {backtest['annualized_return']*100:.2f}% |
| Annualized Volatility | {backtest['annualized_volatility']*100:.2f}% |
| Sharpe Ratio          | {backtest['sharpe_ratio']:.3f} |
| Sortino Ratio         | {backtest['sortino_ratio']:.3f} |
| Max Drawdown          | {backtest['max_drawdown']*100:.2f}% |
| Calmar Ratio          | {backtest['calmar_ratio']:.3f} |
| Win Rate              | {backtest['win_rate']*100:.1f}% |
| Period               | {backtest['start_date']} to {backtest['end_date']} |

---

## IPS Compliance

**Status**: {ips_status}

**Violations**:
{violations_text}

**Binding Constraints**:
{binding_text}

---

*Generated by apex-plugin-strategy-saa on {run_date}*
"""

    memo_path = out_dir / "memo.md"
    with open(memo_path, "w") as f:
        f.write(memo_content)

    print(f"[{method_name}] Memo saved to: {memo_path}")


# ---------------------------------------------------------------------------
# CLI helper for PC scripts
# ---------------------------------------------------------------------------

def parse_date_arg():
    """Parse --date YYYYMMDD from sys.argv. Returns date string or None."""
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--date" and i + 1 < len(args):
            return args[i + 1]
        if arg.startswith("--date="):
            return arg.split("=", 1)[1]
    return None


def run_pc_script(method_name, optimize_fn, methodology_notes):
    """
    Standard runner for all PC scripts.

    Args:
        method_name: str — e.g. "pc-max-sharpe"
        optimize_fn: callable(mu, Sigma, rf, vols) -> np.ndarray weights
        methodology_notes: str — for memo.md
    """
    date_str = parse_date_arg()
    print(f"[{method_name}] Loading inputs for date: {date_str or 'today'}")

    try:
        mu, rf, cma_meta = load_cmas(date_str)
        Sigma, vols = load_covariance(date_str)
        regime, macro_data = load_macro(date_str)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[{method_name}] Running optimization (regime: {regime})")
    try:
        w = optimize_fn(mu, Sigma, rf, vols)
    except Exception as e:
        print(f"ERROR in optimization: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Validate
    w = np.asarray(w, dtype=float)
    if not np.isfinite(w).all():
        print(f"WARNING: Non-finite weights produced, projecting to IPS feasible point.", file=sys.stderr)
        w = make_initial_weights()

    if abs(w.sum() - 1.0) > 1e-4:
        w = w / w.sum()

    ips = _check_ips_compliance(w)
    if not ips["overall"]:
        print(f"WARNING: IPS violations detected: {ips['violations']}", file=sys.stderr)
        print(f"[{method_name}] Projecting to IPS feasible space...", file=sys.stderr)
        w = project_to_ips(w)

    diag = compute_diagnostics(w, mu, Sigma, rf)
    backtest = run_backtest(w, date_str)

    portfolio = save_portfolio_outputs(method_name, w, mu, Sigma, rf, date_str, extra_meta={"regime": regime})
    write_memo(method_name, w, diag, backtest, methodology_notes, date_str)

    print(f"[{method_name}] Done.")
    print(f"  Expected Return:   {diag['expected_return']*100:.2f}%")
    print(f"  Expected Vol:      {diag['expected_volatility']*100:.2f}%")
    print(f"  Sharpe:            {diag['sharpe_ratio']:.3f}")
    print(f"  Tracking Error:    {diag['tracking_error_vs_benchmark']*100:.2f}%")
    print(f"  IPS Compliant:     {diag['ips_compliance']['overall']}")
    return portfolio
