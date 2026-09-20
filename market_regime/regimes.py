"""Growth–inflation regime labels from first-print GDP / CPI rates.

Map A: sign(g) × sign(π)     — rate signs (1st derivative of levels)
Map B: sign(Δg) × sign(Δπ)   — accel / slow (2nd derivative of levels)

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


def _box(growth: str, inflation: str) -> str:
    return f"g_{growth}__pi_{inflation}"


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
    panel["map_a"] = pd.array(map_a, dtype="string")
    panel["map_b"] = pd.array(map_b, dtype="string")
    return panel


def mean_returns_by_regime(
    returns: pd.DataFrame,
    regimes: pd.DataFrame,
    *,
    map_col: str = "map_a",
    annualize: bool = True,
) -> pd.DataFrame:
    """Average daily log return by regime box; optional ×252."""
    cols = list(returns.columns)
    aligned = returns.copy()
    aligned.index = pd.DatetimeIndex(aligned.index).normalize()
    lab = regimes[map_col].reindex(aligned.index)
    rows: list[dict] = []
    for box, idx in lab.groupby(lab, dropna=True).groups.items():
        sub = aligned.loc[idx, cols]
        means = sub.mean()
        if annualize:
            means = means * 252.0
        row: dict = {"map": map_col, "box": box, "n_days": int(len(sub))}
        row.update({c: float(means[c]) for c in cols})
        rows.append(row)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["map", "box"]).reset_index(drop=True)


def build_regimes(
    *,
    releases_path: Path = RELEASES_RAW_CSV,
    returns_path: Path = RETURNS_CSV,
    regimes_path: Path = REGIMES_CSV,
    means_path: Path = REGIME_MEANS_CSV,
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

    means_a = mean_returns_by_regime(rets, regimes, map_col="map_a")
    means_b = mean_returns_by_regime(rets, regimes, map_col="map_b")
    means = pd.concat([means_a, means_b], ignore_index=True)
    means.to_csv(means_path, index=False)

    n_a = int(regimes["map_a"].notna().sum())
    n_b = int(regimes["map_b"].notna().sum())
    start_a = regimes.loc[regimes["map_a"].notna()].index.min()
    print(
        f"Wrote {regimes_path.relative_to(ROOT).as_posix()} "
        f"(map_a {n_a} days from {start_a.date()}; map_b {n_b} days)",
        flush=True,
    )
    print(
        f"Wrote {means_path.relative_to(ROOT).as_posix()} "
        f"({len(means)} box rows, annualized mean log returns ×252)",
        flush=True,
    )
    return regimes, means


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build daily Map A / Map B regime labels from first-print releases "
            "and mean asset returns by box."
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
