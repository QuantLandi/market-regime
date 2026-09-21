"""Sign rules and weight schemes for Map B sleeves."""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest.config import CASH_COL, MAP_COL, N_SLEEVES, SLEEVES


def signs_from_means(means: pd.Series) -> pd.Series:
    """Binary signs from mean excess: +1 / -1 / 0."""
    out = pd.Series(0, index=list(SLEEVES), dtype=int)
    for col in SLEEVES:
        mu = means.get(col, np.nan)
        if pd.isna(mu) or float(mu) == 0.0:
            out[col] = 0
        else:
            out[col] = 1 if float(mu) > 0 else -1
    return out


def vols_to_date(
    returns: pd.DataFrame,
    *,
    asof: pd.Timestamp,
    min_history: int,
) -> pd.Series:
    """Expanding daily return vol for each sleeve using dates strictly before ``asof``."""
    hist = returns.loc[returns.index < asof, list(SLEEVES)]
    if len(hist) < min_history:
        return pd.Series(np.nan, index=list(SLEEVES))
    return hist.std(ddof=1)


def full_sample_vols(returns: pd.DataFrame) -> pd.Series:
    return returns[list(SLEEVES)].std(ddof=1)


def ls_weights(
    signs: pd.Series,
    *,
    scheme: str,
    vols: pd.Series | None = None,
) -> pd.Series:
    """Long/short weights with sum(|w|)=1 when any sleeve is live.

    equal:   w_i = sign_i / 7
    inv_vol: w_i ∝ sign_i / σ_i, then rescale to sum(|w|)=1
    """
    s = signs.reindex(list(SLEEVES)).fillna(0).astype(float)
    if scheme == "equal":
        return s / N_SLEEVES
    if scheme == "inv_vol":
        if vols is None:
            raise ValueError("inv_vol requires vols")
        v = vols.reindex(list(SLEEVES)).astype(float)
        raw = pd.Series(0.0, index=list(SLEEVES))
        for col in SLEEVES:
            if s[col] == 0 or pd.isna(v[col]) or float(v[col]) <= 0:
                continue
            raw[col] = s[col] / float(v[col])
        gross = float(raw.abs().sum())
        if gross == 0.0:
            return raw
        return raw / gross
    raise ValueError(f"unknown scheme {scheme!r}")


def long_only_weights(
    *,
    scheme: str,
    vols: pd.Series | None = None,
) -> pd.Series:
    """Long-only weights summing to 1."""
    if scheme == "equal":
        return pd.Series(1.0 / N_SLEEVES, index=list(SLEEVES))
    if scheme == "inv_vol":
        if vols is None:
            raise ValueError("inv_vol requires vols")
        v = vols.reindex(list(SLEEVES)).astype(float)
        raw = pd.Series(0.0, index=list(SLEEVES))
        for col in SLEEVES:
            if pd.isna(v[col]) or float(v[col]) <= 0:
                continue
            raw[col] = 1.0 / float(v[col])
        total = float(raw.sum())
        if total == 0.0:
            return raw
        return raw / total
    raise ValueError(f"unknown scheme {scheme!r}")


def mean_excess_to_date(
    returns: pd.DataFrame,
    regimes: pd.DataFrame,
    *,
    box: str,
    asof: pd.Timestamp,
    map_col: str = MAP_COL,
) -> tuple[pd.Series, int]:
    """Mean daily excess vs cash for ``box`` using only dates strictly before ``asof``."""
    lab = regimes[map_col]
    mask = (lab == box) & (lab.index < asof)
    n = int(mask.sum())
    if n == 0:
        return pd.Series(np.nan, index=list(SLEEVES)), 0
    sub = returns.loc[mask, list(SLEEVES) + [CASH_COL]]
    excess = sub[list(SLEEVES)].sub(sub[CASH_COL], axis=0)
    return excess.mean(), n


def rebalance_dates(regimes: pd.DataFrame, *, map_col: str = MAP_COL) -> pd.DatetimeIndex:
    """Dates where the regime label is non-null and differs from the prior day."""
    lab = regimes[map_col]
    changed = lab.notna() & (lab.ne(lab.shift(1)) | lab.shift(1).isna())
    return pd.DatetimeIndex(lab.index[changed])


def _align(
    returns: pd.DataFrame, regimes: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DatetimeIndex]:
    rets = returns.copy()
    rets.index = pd.DatetimeIndex(rets.index).normalize()
    regs = regimes.copy()
    regs.index = pd.DatetimeIndex(regs.index).normalize()
    dates = rets.index.intersection(regs.index)
    return rets.reindex(dates), regs.reindex(dates), dates


def expanding_weight_panel(
    returns: pd.DataFrame,
    regimes: pd.DataFrame,
    *,
    min_history: int,
    scheme: str,
    map_col: str = MAP_COL,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """LS + long-only bench weights; held between regime-label changes.

    Signs: past in-box mean excess. Vols (inv_vol): past sleeve returns date < t.
    If a box is entered with fewer than ``min_history`` past days, stay flat until
    in-box history reaches the threshold mid-hold, then turn on (needed for Map A).
    """
    rets, regs, dates = _align(returns, regimes)
    weights = pd.DataFrame(0.0, index=dates, columns=list(SLEEVES))
    bench = pd.DataFrame(0.0, index=dates, columns=list(SLEEVES))
    reb_rows: list[dict] = []

    reb_idx = rebalance_dates(regs, map_col=map_col)
    for i, t in enumerate(reb_idx):
        box = regs.at[t, map_col]
        if pd.isna(box):
            continue
        end = reb_idx[i + 1] if i + 1 < len(reb_idx) else dates[-1] + pd.Timedelta(days=1)
        span = (weights.index >= t) & (weights.index < end)
        span_dates = weights.index[span]

        means, n = mean_excess_to_date(
            rets, regs, box=str(box), asof=t, map_col=map_col
        )
        vols = vols_to_date(rets, asof=t, min_history=min_history)
        signs = pd.Series(0, index=list(SLEEVES), dtype=int)
        live = False
        w = pd.Series(0.0, index=list(SLEEVES))
        live_from = t

        def _try_activate(asof: pd.Timestamp) -> bool:
            nonlocal means, n, vols, signs, live, w
            means, n = mean_excess_to_date(
                rets, regs, box=str(box), asof=asof, map_col=map_col
            )
            if n < min_history:
                return False
            vols = vols_to_date(rets, asof=asof, min_history=min_history)
            signs = signs_from_means(means)
            if scheme == "inv_vol" and vols.isna().all():
                return False
            w = ls_weights(signs, scheme=scheme, vols=vols)
            live = bool((w.abs() > 0).any())
            return live

        if not _try_activate(t) and n < min_history and len(span_dates) > 0:
            need = min_history - n
            if len(span_dates) > need:
                live_from = span_dates[need]
                _try_activate(live_from)

        if live:
            apply = (weights.index >= live_from) & (weights.index < end)
            weights.loc[apply, list(SLEEVES)] = w.to_numpy()

        bw = long_only_weights(scheme=scheme, vols=vols)
        if scheme == "inv_vol" and float(bw.sum()) == 0.0:
            bw = long_only_weights(scheme="equal")
        bench.loc[span, list(SLEEVES)] = bw.to_numpy()

        row: dict = {
            "date": t,
            "live_from": live_from if live else pd.NaT,
            "box": str(box),
            "n_history": n,
            "live": live,
            "scheme": scheme,
            "map_col": map_col,
        }
        for col in SLEEVES:
            row[f"sign_{col}"] = int(signs[col])
            row[f"w_{col}"] = float(w[col])
            row[f"bw_{col}"] = float(bw[col])
            row[f"vol_{col}"] = (
                float(vols[col]) if vols is not None and pd.notna(vols[col]) else float("nan")
            )
        reb_rows.append(row)

    first = reb_idx[0] if len(reb_idx) else None
    if first is not None:
        pre = bench.index < first
        if pre.any():
            ew = long_only_weights(scheme="equal")
            bench.loc[pre, list(SLEEVES)] = ew.to_numpy()
    else:
        bench.loc[:, list(SLEEVES)] = long_only_weights(scheme="equal").to_numpy()

    rebalances = pd.DataFrame(reb_rows)
    if not rebalances.empty:
        rebalances = rebalances.set_index("date")
    return weights, bench, rebalances


def oracle_weight_panel(
    returns: pd.DataFrame,
    regimes: pd.DataFrame,
    *,
    scheme: str,
    map_col: str = MAP_COL,
) -> pd.DataFrame:
    """Full-sample mean excess signs (and vols) as if known at inception."""
    rets, regs, dates = _align(returns, regimes)
    sign_by_box: dict[str, pd.Series] = {}
    lab = regs[map_col]
    for box, idx in lab.groupby(lab, dropna=True).groups.items():
        sub = rets.loc[idx, list(SLEEVES) + [CASH_COL]]
        excess = sub[list(SLEEVES)].sub(sub[CASH_COL], axis=0)
        sign_by_box[str(box)] = signs_from_means(excess.mean())

    vols = full_sample_vols(rets) if scheme == "inv_vol" else None
    weights = pd.DataFrame(0.0, index=dates, columns=list(SLEEVES))
    for dt, box in lab.items():
        if pd.isna(box):
            continue
        w = ls_weights(sign_by_box[str(box)], scheme=scheme, vols=vols)
        weights.loc[dt, list(SLEEVES)] = w.to_numpy()
    return weights
