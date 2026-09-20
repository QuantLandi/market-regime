"""Load frozen closes and slice to the locked daily sample."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from market_regime.proxies import DAILY_SAMPLE_START, PROXIES

ROOT = Path(__file__).resolve().parents[1]
CLOSES_CSV = ROOT / "data" / "closes.csv"


def load_daily_closes(
    path: Path = CLOSES_CSV,
    *,
    start: str = DAILY_SAMPLE_START,
    require_all: bool = True,
) -> pd.DataFrame:
    """Daily panel from ``start`` (default ``DAILY_SAMPLE_START``).

    If ``require_all``, drop rows with any NA among locked ``PROXIES`` columns.
    """
    df = pd.read_csv(path, index_col=0, parse_dates=True).sort_index()
    cols = [c for c in PROXIES if c in df.columns]
    out = df.loc[pd.Timestamp(start) :, cols]
    if require_all:
        out = out.dropna(how="any")
    return out
