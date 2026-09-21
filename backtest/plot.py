"""Equity curve and drawdown figures (per scheme + pairwise compares).

Plot-only: each series is scaled to a common target annualized return so curves
on a chart share the same endpoint (path shape / risk comparison).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from backtest.config import COMPARE_FIG_DIR, PLOT_TARGET_ANN_RETURN, TRADING_DAYS_PER_YEAR

COLOR_LS = "#0072B2"
COLOR_BENCH = "#E69F00"
COLOR_ORACLE = "#56B4E9"
COLOR_A = "#0072B2"
COLOR_B = "#E69F00"

SCHEME_LABEL = {
    "equal": "equal-weight",
    "inv_vol": "inv-vol",
}

_SCALE_NOTE = f"scaled to {100 * PLOT_TARGET_ANN_RETURN:.0f}% ann."


def _drawdown(equity: pd.Series) -> pd.Series:
    peak = equity.cummax()
    return equity / peak - 1.0


def scale_logs_to_target_ann(
    r: pd.Series,
    *,
    target_ann: float = PLOT_TARGET_ANN_RETURN,
) -> pd.Series:
    """Constant-leverage scale of daily log returns to hit ``target_ann`` compound.

    Terminal wealth becomes ``(1 + target_ann) ** (n / 252)`` for every series
    with the same length, so curves end at the same point.
    """
    x = r.fillna(0.0).astype(float)
    n = int(len(x))
    if n == 0:
        return x
    cum = float(x.sum())
    years = n / TRADING_DAYS_PER_YEAR
    target_cum = float(np.log1p(target_ann) * years)
    if abs(cum) < 1e-12:
        # Flat path: distribute target evenly (synthetic; rare).
        return pd.Series(np.full(n, target_cum / n), index=x.index)
    return x * (target_cum / cum)


def _equity_from_logs(r: pd.Series, *, scale: bool = True) -> pd.Series:
    logs = scale_logs_to_target_ann(r) if scale else r.fillna(0.0)
    return np.exp(logs.cumsum())


def _labeled_logs(daily: pd.DataFrame, col: str) -> pd.Series:
    live = daily["regime"].notna()
    if col not in daily.columns:
        raise SystemExit(f"Missing column {col!r} for comparison plot")
    return daily.loc[live, col]


def plot_equity_and_drawdown(
    daily: pd.DataFrame,
    *,
    scheme: str,
    equity_path: Path,
    drawdown_path: Path,
) -> tuple[Path, Path]:
    equity_path.parent.mkdir(parents=True, exist_ok=True)
    drawdown_path.parent.mkdir(parents=True, exist_ok=True)

    live = daily["regime"].notna()
    sub = daily.loc[live].copy()
    if sub.empty:
        raise SystemExit("No regime-labeled days to plot.")

    eq_ls = _equity_from_logs(sub["port"])
    eq_bench = _equity_from_logs(sub["bench"])
    scheme_lbl = SCHEME_LABEL.get(scheme, scheme)
    bench_lbl = (
        "EW long-only (7)" if scheme == "equal" else "Inv-vol long-only (7)"
    )

    fig, ax = plt.subplots(figsize=(10, 4.5), layout="constrained")
    ax.plot(
        eq_ls.index,
        eq_ls,
        color=COLOR_LS,
        lw=1.4,
        label=f"Expanding Map B LS ({scheme_lbl})",
    )
    ax.plot(eq_bench.index, eq_bench, color=COLOR_BENCH, lw=1.2, label=bench_lbl)
    if "oracle" in sub.columns:
        eq_or = _equity_from_logs(sub["oracle"])
        ax.plot(
            eq_or.index,
            eq_or,
            color=COLOR_ORACLE,
            lw=1.0,
            ls="--",
            alpha=0.85,
            label=f"Oracle Map B LS ({scheme_lbl})",
        )
    ax.set_yscale("log")
    ax.set_ylabel(f"Growth of $1 (log scale, {_SCALE_NOTE})")
    ax.set_title(f"Map B long/short vs long-only — {scheme_lbl} ({_SCALE_NOTE})")
    ax.legend(frameon=False, loc="upper left")
    ax.grid(True, alpha=0.25)
    fig.savefig(equity_path, dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 3.5), layout="constrained")
    ax.fill_between(
        eq_ls.index,
        _drawdown(eq_ls),
        0.0,
        color=COLOR_LS,
        alpha=0.35,
        label=f"Expanding LS ({scheme_lbl})",
    )
    ax.plot(
        eq_bench.index,
        _drawdown(eq_bench),
        color=COLOR_BENCH,
        lw=1.0,
        label=bench_lbl,
    )
    if "oracle" in sub.columns:
        eq_or = _equity_from_logs(sub["oracle"])
        ax.plot(
            eq_or.index,
            _drawdown(eq_or),
            color=COLOR_ORACLE,
            lw=1.0,
            ls="--",
            alpha=0.85,
            label=f"Oracle LS ({scheme_lbl})",
        )
    ax.set_ylabel("Drawdown")
    ax.set_title(f"Drawdowns — {scheme_lbl} ({_SCALE_NOTE})")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{100 * x:.0f}%"))
    ax.legend(frameon=False, loc="lower left")
    ax.grid(True, alpha=0.25)
    fig.savefig(drawdown_path, dpi=150)
    plt.close(fig)

    return equity_path, drawdown_path


def plot_pair_equity(
    series_a: pd.Series,
    series_b: pd.Series,
    *,
    label_a: str,
    label_b: str,
    title: str,
    out_path: Path,
    color_a: str = COLOR_A,
    color_b: str = COLOR_B,
) -> Path:
    """Two equity curves from daily log-return series (Map B window already applied)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    idx = series_a.index.intersection(series_b.index)
    if idx.empty:
        raise SystemExit(f"No overlapping dates for {title!r}")
    eq_a = _equity_from_logs(series_a.reindex(idx))
    eq_b = _equity_from_logs(series_b.reindex(idx))

    fig, ax = plt.subplots(figsize=(10, 4.5), layout="constrained")
    ax.plot(eq_a.index, eq_a, color=color_a, lw=1.4, label=label_a)
    ax.plot(eq_b.index, eq_b, color=color_b, lw=1.4, label=label_b)
    ax.set_yscale("log")
    ax.set_ylabel(f"Growth of $1 (log scale, {_SCALE_NOTE})")
    ax.set_title(f"{title} ({_SCALE_NOTE})")
    ax.legend(frameon=False, loc="upper left")
    ax.grid(True, alpha=0.25)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_comparisons(
    daily_by_scheme: dict[str, pd.DataFrame],
    *,
    out_dir: Path = COMPARE_FIG_DIR,
) -> list[Path]:
    """Five pairwise equity comparisons across equal / inv_vol panels."""
    if "equal" not in daily_by_scheme or "inv_vol" not in daily_by_scheme:
        return []

    eq = daily_by_scheme["equal"]
    iv = daily_by_scheme["inv_vol"]
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    pairs: list[tuple[pd.Series, pd.Series, str, str, str, str]] = []

    if "oracle" in eq.columns and "oracle" in iv.columns:
        pairs.append(
            (
                _labeled_logs(eq, "oracle"),
                _labeled_logs(iv, "oracle"),
                "Oracle LS equal-weight",
                "Oracle LS inv-vol",
                "Oracle equal-weight vs oracle inv-vol",
                "oracle_equal_vs_oracle_inv_vol.png",
            )
        )

    pairs.extend(
        [
            (
                _labeled_logs(iv, "bench"),
                _labeled_logs(eq, "bench"),
                "Expanding long-only inv-vol",
                "Expanding long-only equal-weight",
                "Expanding inv-vol long-only vs equal-weight long-only",
                "expanding_lo_inv_vol_vs_lo_equal.png",
            ),
            (
                _labeled_logs(iv, "port"),
                _labeled_logs(eq, "port"),
                "Expanding LS inv-vol",
                "Expanding LS equal-weight",
                "Expanding inv-vol LS vs equal-weight LS",
                "expanding_ls_inv_vol_vs_ls_equal.png",
            ),
            (
                _labeled_logs(iv, "bench"),
                _labeled_logs(iv, "port"),
                "Expanding long-only inv-vol",
                "Expanding LS inv-vol",
                "Expanding inv-vol long-only vs inv-vol LS",
                "expanding_inv_vol_lo_vs_ls.png",
            ),
            (
                _labeled_logs(eq, "bench"),
                _labeled_logs(eq, "port"),
                "Expanding long-only equal-weight",
                "Expanding LS equal-weight",
                "Expanding equal-weight long-only vs equal-weight LS",
                "expanding_equal_lo_vs_ls.png",
            ),
        ]
    )

    for series_a, series_b, label_a, label_b, title, filename in pairs:
        path = plot_pair_equity(
            series_a,
            series_b,
            label_a=label_a,
            label_b=label_b,
            title=title,
            out_path=out_dir / filename,
        )
        written.append(path)
    return written


def plot_map_inv_vol_ls(
    daily_by_map: dict[str, pd.DataFrame],
    *,
    out_path: Path,
    labels: dict[str, str] | None = None,
) -> Path:
    """Overlay expanding inv-vol LS equity for Map A / B / joint (10% scaled)."""
    from backtest.config import MAP_LABELS

    labels = labels or MAP_LABELS
    colors = {
        "map_a": "#E69F00",
        "map_b": "#0072B2",
        "map_joint": "#009E73",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 4.5), layout="constrained")
    for map_col, daily in daily_by_map.items():
        live = daily["regime"].notna() & (daily["gross"] > 0)
        if not live.any():
            continue
        eq = _equity_from_logs(daily.loc[live, "port"])
        ax.plot(
            eq.index,
            eq,
            color=colors.get(map_col, "#333333"),
            lw=1.4,
            label=labels.get(map_col, map_col),
        )
    ax.set_yscale("log")
    ax.set_ylabel(f"Growth of $1 (log scale, {_SCALE_NOTE})")
    ax.set_title(f"Expanding inv-vol LS — Map A vs B vs joint ({_SCALE_NOTE})")
    ax.legend(frameon=False, loc="upper left")
    ax.grid(True, alpha=0.25)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
