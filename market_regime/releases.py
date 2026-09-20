"""Load / validate first-print macro releases → data/releases_raw.csv."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from market_regime.macro import GROWTH_SERIES, INFLATION_SERIES, MACRO_SERIES

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RELEASES_RAW_CSV = DATA_DIR / "releases_raw.csv"

REQUIRED_COLS = ("release_date", "series", "actual")
OPTIONAL_COLS = ("release_type", "obs_period", "source")


def empty_releases() -> pd.DataFrame:
    cols = list(REQUIRED_COLS) + list(OPTIONAL_COLS)
    return pd.DataFrame(columns=cols)


def normalize_releases(df: pd.DataFrame) -> pd.DataFrame:
    """Canonical columns, types, sort. Drops rows with null actual."""
    out = df.copy()
    for c in REQUIRED_COLS:
        if c not in out.columns:
            raise ValueError(f"releases CSV missing column {c!r}")
    for c in OPTIONAL_COLS:
        if c not in out.columns:
            out[c] = pd.NA

    out["release_date"] = pd.to_datetime(out["release_date"]).dt.normalize()
    out["series"] = out["series"].astype(str).str.strip()
    out["actual"] = pd.to_numeric(out["actual"], errors="coerce")
    out["release_type"] = out["release_type"].astype("string")
    out["obs_period"] = out["obs_period"].astype("string")
    out["source"] = out["source"].astype("string")

    unknown = sorted(set(out["series"]) - set(MACRO_SERIES))
    if unknown:
        raise ValueError(
            f"Unknown series {unknown}; expected one of {sorted(MACRO_SERIES)}"
        )

    out = out.dropna(subset=["release_date", "series", "actual"])
    out = out.sort_values(["series", "release_date", "release_type"]).reset_index(
        drop=True
    )
    return out[list(REQUIRED_COLS) + list(OPTIONAL_COLS)]


def load_releases(path: Path = RELEASES_RAW_CSV) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return normalize_releases(pd.read_csv(path))


def save_releases(df: pd.DataFrame, path: Path = RELEASES_RAW_CSV) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalize_releases(df).to_csv(path, index=False)
    return path


def first_print_rate_path(releases: pd.DataFrame, series: str) -> pd.Series:
    """Release-date index → actual rate (%). One value per release_date (last wins)."""
    sub = releases.loc[releases["series"] == series].copy()
    if sub.empty:
        return pd.Series(dtype=float, name=series)
    # Same calendar day can have Advance then we keep chronological file order;
    # last row that day wins (e.g. if CSV lists one row per release event uniquely).
    sub = sub.drop_duplicates(subset=["release_date"], keep="last")
    s = pd.Series(
        sub["actual"].to_numpy(dtype=float),
        index=pd.DatetimeIndex(sub["release_date"]),
        name=series,
    )
    return s.sort_index()


def require_growth_inflation(releases: pd.DataFrame) -> None:
    have = set(releases["series"].unique())
    need = {GROWTH_SERIES, INFLATION_SERIES}
    missing = need - have
    if missing:
        raise ValueError(f"releases missing series {sorted(missing)}")
