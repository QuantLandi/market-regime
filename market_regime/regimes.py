"""Growth–inflation regime labels from first-print GDP / CPI rates.

Map A: sign(g) × sign(π)                         — rate signs (1st deriv)
Map B: sign(Δg) × sign(Δπ)                       — accel / slow (2nd deriv)
Map joint: (sign g, sign Δg) × (sign π, sign Δπ) — full 1st×2nd combo

Labels update on release; apply from the *next* session on the returns calendar.
Hold until the next print. No survey / expectations.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from market_regime.macro import GROWTH_SERIES, INFLATION_SERIES
from market_regime.releases import (
    RELEASES_RAW_CSV,
    first_print_rate_path,
    load_releases,
    require_growth_inflation,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RETURNS_CSV = DATA_DIR / "returns.csv"
REGIMES_CSV = DATA_DIR / "regimes.csv"
REGIME_MEANS_CSV = DATA_DIR / "regime_means.csv"
REGIME_VOLS_CSV = DATA_DIR / "regime_vols.csv"
REGIME_RET_VOL_CSV = DATA_DIR / "regime_ret_vol.csv"

TRADING_DAYS_PER_YEAR = 252
CASH_COL = "cash"


def _box(growth: str, inflation: str) -> str:
    return f"g_{growth}__pi_{inflation}"


def _joint_box(g_sign: str, g_delta: str, pi_sign: str, pi_delta: str) -> str:
    """1st×2nd derivatives: g_{rate}_{Δ}__pi_{rate}_{Δ}."""
    return f"g_{g_sign}_{g_delta}__pi_{pi_sign}_{pi_delta}"


def rate_events(rate: pd.Series) -> pd.DataFrame:
    """One row per release: rate, delta vs prior release, signs."""
    s = rate.dropna().sort_index()
    if s.empty:
        return pd.DataFrame(
            columns=["release_date", "rate", "delta", "sign_rate", "sign_delta"]
        )
    delta = s.diff()
    out = pd.DataFrame(
        {
            "release_date": s.index,
            "rate": s.to_numpy(dtype=float),
            "delta": delta.to_numpy(dtype=float),
        }
    )
    out["sign_rate"] = np.where(out["rate"] > 0, "up", "down")
    out["sign_delta"] = np.where(
        out["delta"].isna(),
        pd.NA,
        np.where(out["delta"] > 0, "up", "down"),
    )
    return out.reset_index(drop=True)


def _hold_from_next_session(
    events: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    value_col: str,
    *,
    as_string: bool,
) -> pd.Series:
    """Map release events onto trading calendar: start next session, hold."""
    cal = pd.DatetimeIndex(calendar).sort_values().normalize()
    dtype = "string" if as_string else float
    out = pd.Series(index=cal, dtype=dtype)
    if events.empty or value_col not in events.columns:
        return out

    rows = events.dropna(subset=[value_col]).sort_values("release_date")
    for _, row in rows.iterrows():
        rel = pd.Timestamp(row["release_date"]).normalize()
        later = cal[cal > rel]
        if later.empty:
            continue
        start = later[0]
        val = row[value_col]
        out.loc[start:] = str(val) if as_string else float(val)
    return out


def build_regime_panel(
    releases: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Daily regime labels aligned to ``calendar`` (usually returns index)."""
    require_growth_inflation(releases)
    g_ev = rate_events(first_print_rate_path(releases, GROWTH_SERIES))
    pi_ev = rate_events(first_print_rate_path(releases, INFLATION_SERIES))

    g_sign = _hold_from_next_session(g_ev, calendar, "sign_rate", as_string=True)
    pi_sign = _hold_from_next_session(pi_ev, calendar, "sign_rate", as_string=True)
    g_delta = _hold_from_next_session(g_ev, calendar, "sign_delta", as_string=True)
    pi_delta = _hold_from_next_session(pi_ev, calendar, "sign_delta", as_string=True)
    g_yoy = _hold_from_next_session(g_ev, calendar, "rate", as_string=False)
    pi_yoy = _hold_from_next_session(pi_ev, calendar, "rate", as_string=False)

    panel = pd.DataFrame(
        {
            "g_yoy": g_yoy,
            "pi_yoy": pi_yoy,
            "g_sign": g_sign,
            "pi_sign": pi_sign,
            "g_delta_sign": g_delta,
            "pi_delta_sign": pi_delta,
        },
        index=pd.DatetimeIndex(calendar).normalize(),
    )
    panel.index.name = "date"

    map_a: list[object] = []
    map_b: list[object] = []
    map_joint: list[object] = []
    for gs, ps, gd, pds in zip(
        panel["g_sign"],
        panel["pi_sign"],
        panel["g_delta_sign"],
        panel["pi_delta_sign"],
        strict=True,
    ):
        if pd.isna(gs) or pd.isna(ps):
            map_a.append(pd.NA)
        else:
            map_a.append(_box(str(gs), str(ps)))
        if pd.isna(gd) or pd.isna(pds):
            map_b.append(pd.NA)
        else:
            map_b.append(_box(str(gd), str(pds)))
        if pd.isna(gs) or pd.isna(ps) or pd.isna(gd) or pd.isna(pds):
            map_joint.append(pd.NA)
        else:
            map_joint.append(_joint_box(str(gs), str(gd), str(ps), str(pds)))
    panel["map_a"] = pd.array(map_a, dtype="string")
    panel["map_b"] = pd.array(map_b, dtype="string")
    panel["map_joint"] = pd.array(map_joint, dtype="string")
    return panel


def stats_by_regime(
    returns: pd.DataFrame,
    regimes: pd.DataFrame,
    *,
    map_col: str = "map_a",
    metric: str = "mean",
) -> pd.DataFrame:
    """Per-box stats for each sleeve on daily excess over cash.

    Every metric uses excess_t = r_t − cash_t (cash column → NaN):
      mean     — annualized mean excess (×252)
      vol      — annualized sd of excess (×√252)
      ret_vol  — Sharpe: mean(excess)/sd(excess)×√252
    """
    if metric not in {"mean", "vol", "ret_vol"}:
        raise ValueError(f"unknown metric {metric!r}")
    cols = list(returns.columns)
    aligned = returns.copy()
    aligned.index = pd.DatetimeIndex(aligned.index).normalize()
    lab = regimes[map_col].reindex(aligned.index)
    if CASH_COL not in aligned.columns:
        raise ValueError(f"need a {CASH_COL!r} column for daily excess returns")

    rows: list[dict] = []
    for box, idx in lab.groupby(lab, dropna=True).groups.items():
        sub = aligned.loc[idx, cols]
        n = int(len(sub))
        excess = sub.sub(sub[CASH_COL], axis=0)
        if metric == "mean":
            vals = excess.mean() * TRADING_DAYS_PER_YEAR
        elif metric == "vol":
            vals = excess.std(ddof=1).replace(0.0, np.nan) * np.sqrt(
                TRADING_DAYS_PER_YEAR
            )
        else:
            mu_x = excess.mean()
            sig_x = excess.std(ddof=1).replace(0.0, np.nan)
            vals = (mu_x / sig_x) * np.sqrt(TRADING_DAYS_PER_YEAR)
        vals[CASH_COL] = np.nan  # excess over itself is not a sleeve metric
        row: dict = {"map": map_col, "box": box, "n_days": n}
        row.update({c: float(vals[c]) if pd.notna(vals[c]) else float("nan") for c in cols})
        rows.append(row)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["map", "box"]).reset_index(drop=True)


def mean_returns_by_regime(
    returns: pd.DataFrame,
    regimes: pd.DataFrame,
    *,
    map_col: str = "map_a",
    annualize: bool = True,
) -> pd.DataFrame:
    """Average daily log return by regime box; optional ×252."""
    del annualize  # always annualized; kept for call-site compatibility
    return stats_by_regime(returns, regimes, map_col=map_col, metric="mean")


def build_regimes(
    *,
    releases_path: Path = RELEASES_RAW_CSV,
    returns_path: Path = RETURNS_CSV,
    regimes_path: Path = REGIMES_CSV,
    means_path: Path = REGIME_MEANS_CSV,
    vols_path: Path = REGIME_VOLS_CSV,
    ret_vol_path: Path = REGIME_RET_VOL_CSV,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not releases_path.exists():
        raise SystemExit(
            f"Missing {releases_path.relative_to(ROOT).as_posix()}. "
            "Run: uv run python -m market_regime download-releases "
            "(or place a first-print ECO/ALFRED CSV there)."
        )
    if not returns_path.exists():
        raise SystemExit(
            f"Missing {returns_path.relative_to(ROOT).as_posix()}. "
            "Run: uv run python -m market_regime returns"
        )

    releases = load_releases(releases_path)
    rets = pd.read_csv(returns_path, index_col=0, parse_dates=True)
    regimes = build_regime_panel(releases, rets.index)

    if regimes["map_a"].isna().all():
        raise SystemExit("No overlapping first-print growth+inflation labels.")

    regimes_path.parent.mkdir(parents=True, exist_ok=True)
    regimes.to_csv(regimes_path)

    frames_mean: list[pd.DataFrame] = []
    frames_vol: list[pd.DataFrame] = []
    frames_rv: list[pd.DataFrame] = []
    for map_col in ("map_a", "map_b", "map_joint"):
        frames_mean.append(stats_by_regime(rets, regimes, map_col=map_col, metric="mean"))
        frames_vol.append(stats_by_regime(rets, regimes, map_col=map_col, metric="vol"))
        frames_rv.append(stats_by_regime(rets, regimes, map_col=map_col, metric="ret_vol"))

    means = pd.concat(frames_mean, ignore_index=True)
    vols = pd.concat(frames_vol, ignore_index=True)
    ret_vols = pd.concat(frames_rv, ignore_index=True)
    means.to_csv(means_path, index=False)
    vols.to_csv(vols_path, index=False)
    ret_vols.to_csv(ret_vol_path, index=False)

    n_a = int(regimes["map_a"].notna().sum())
    n_b = int(regimes["map_b"].notna().sum())
    n_j = int(regimes["map_joint"].notna().sum())
    start_a = regimes.loc[regimes["map_a"].notna()].index.min()
    print(
        f"Wrote {regimes_path.relative_to(ROOT).as_posix()} "
        f"(map_a {n_a} days from {start_a.date()}; map_b {n_b}; "
        f"map_joint {n_j})",
        flush=True,
    )
    print(
        f"Wrote {means_path.relative_to(ROOT).as_posix()}, "
        f"{vols_path.relative_to(ROOT).as_posix()}, "
        f"{ret_vol_path.relative_to(ROOT).as_posix()} "
        f"({len(means)} box rows each)",
        flush=True,
    )
    return regimes, means


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build daily Map A / Map B / joint regime labels from first-print "
            "releases and mean asset returns by box."
        )
    )
    parser.add_argument(
        "--releases",
        type=Path,
        default=RELEASES_RAW_CSV,
        help="First-print releases CSV",
    )
    parser.add_argument(
        "--returns",
        type=Path,
        default=RETURNS_CSV,
        help="Daily log-return panel",
    )
    args = parser.parse_args(argv)
    build_regimes(releases_path=args.releases, returns_path=args.returns)


if __name__ == "__main__":
    main()
