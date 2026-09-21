"""Portfolio construction and summary stats."""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest.config import CASH_COL, MAP_COL, SLEEVES, TRADING_DAYS_PER_YEAR


def portfolio_log_returns(returns: pd.DataFrame, weights: pd.DataFrame) -> pd.Series:
    """Daily port log return = sum_i w_i * r_i."""
    rets = returns.reindex(columns=list(SLEEVES))
    rets.index = pd.DatetimeIndex(rets.index).normalize()
    w = weights.reindex(rets.index).fillna(0.0)
    return (w * rets).sum(axis=1)


def build_daily(
    returns: pd.DataFrame,
    regimes: pd.DataFrame,
    weights_ls: pd.DataFrame,
    weights_bench: pd.DataFrame,
    *,
    map_col: str = MAP_COL,
    include_oracle: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Daily LS book, matched long-only bench, optional oracle overlay."""
    rets = returns.copy()
    rets.index = pd.DatetimeIndex(rets.index).normalize()
    regs = regimes.copy()
    regs.index = pd.DatetimeIndex(regs.index).normalize()
    dates = rets.index.intersection(regs.index)
    rets = rets.reindex(dates)
    regs = regs.reindex(dates)
    w = weights_ls.reindex(dates).fillna(0.0)
    bw = weights_bench.reindex(dates).fillna(0.0)

    port = portfolio_log_returns(rets, w)
    bench = portfolio_log_returns(rets, bw)

    out = w.add_prefix("w_")
    out["regime"] = regs[map_col]
    out["map_col"] = map_col
    out["port"] = port
    out["bench"] = bench
    out["cash"] = rets[CASH_COL]
    out["gross"] = w.abs().sum(axis=1)
    out["net"] = w.sum(axis=1)
    out["equity"] = np.exp(port.fillna(0.0).cumsum())
    out["bench_equity"] = np.exp(bench.fillna(0.0).cumsum())

    if include_oracle is not None:
        ow = include_oracle.reindex(dates).fillna(0.0)
        oport = portfolio_log_returns(rets, ow)
        out["oracle"] = oport
        out["oracle_equity"] = np.exp(oport.fillna(0.0).cumsum())

    return out


def _stats_block(r: pd.Series, *, prefix: str) -> list[dict]:
    r = r.dropna()
    if r.empty:
        return [
            {"strategy": prefix, "metric": "n_days", "value": 0.0, "note": "empty"},
        ]
    mu = float(r.mean() * TRADING_DAYS_PER_YEAR)
    vol = float(r.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR))
    sharpe = float("nan") if vol == 0 or np.isnan(vol) else mu / vol
    total = float(np.expm1(r.sum()))
    eq = np.exp(r.cumsum())
    dd = float((eq / eq.cummax() - 1.0).min())
    return [
        {"strategy": prefix, "metric": "n_days", "value": float(len(r)), "note": "sample days"},
        {
            "strategy": prefix,
            "metric": "ann_total_mean",
            "value": mu,
            "note": "mean(sum w r) x252",
        },
        {
            "strategy": prefix,
            "metric": "ann_total_vol",
            "value": vol,
            "note": "sd(sum w r) x sqrt(252)",
        },
        {
            "strategy": prefix,
            "metric": "sharpe_total",
            "value": sharpe,
            "note": "ann mean / ann vol of total returns",
        },
        {
            "strategy": prefix,
            "metric": "total_simple_return",
            "value": total,
            "note": "expm1(sum log rets)",
        },
        {
            "strategy": prefix,
            "metric": "max_drawdown",
            "value": dd,
            "note": "min(equity/peak - 1)",
        },
        {
            "strategy": prefix,
            "metric": "hit_rate",
            "value": float((r > 0).mean()),
            "note": "P(daily port > 0)",
        },
    ]


def summarize(
    daily: pd.DataFrame,
    *,
    scheme: str,
    map_col: str | None = None,
) -> pd.DataFrame:
    """Primary stats on total returns sum(w·r); LS restricted to live days."""
    live = daily["regime"].notna() & (daily["gross"] > 0)
    tag = f"{scheme}"
    rows: list[dict] = []
    rows.extend(_stats_block(daily.loc[live, "port"], prefix=f"expanding_ls_{tag}"))
    rows.extend(_stats_block(daily.loc[live, "bench"], prefix=f"long_only_{tag}_aligned"))
    rows.extend(_stats_block(daily["bench"], prefix=f"long_only_{tag}_full"))
    if "oracle" in daily.columns:
        rows.extend(_stats_block(daily.loc[live, "oracle"], prefix=f"oracle_ls_{tag}"))

    if live.any():
        sub = daily.loc[live]
        rows.append(
            {
                "strategy": f"expanding_ls_{tag}",
                "metric": "avg_gross",
                "value": float(sub["gross"].mean()),
                "note": "mean sum(|w|)",
            }
        )
        rows.append(
            {
                "strategy": f"expanding_ls_{tag}",
                "metric": "avg_net",
                "value": float(sub["net"].mean()),
                "note": "mean sum(w)",
            }
        )
    out = pd.DataFrame(rows)
    out.insert(0, "scheme", scheme)
    resolved_map = map_col
    if resolved_map is None and "map_col" in daily.columns and len(daily):
        resolved_map = str(daily["map_col"].iloc[0])
    out.insert(0, "map_col", resolved_map or "?")
    return out
