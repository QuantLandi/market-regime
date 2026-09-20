"""Daily log returns from ffilled closes → data/returns.csv.

Non-cash: log(P_t / P_{t-1}).
Cash (GB3): annualized yield in percent → simple daily y/100/252 → log(1+simple).

GB3 Govt is the US Generic 3M T-bill; PX_LAST is an annualized bill yield in
percent (Bloomberg bill quote). We do *not* rebuild ACT/360 discount prices —
teaching convention is 1/252 scaling into a comparable daily log return.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from market_regime.proxies import PROXIES, SAMPLE_START

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CLOSES_CSV = DATA_DIR / "closes.csv"
RETURNS_CSV = DATA_DIR / "returns.csv"

TRADING_DAYS_PER_YEAR = 252
CASH_COL = "cash"


def cash_log_return(yield_pct: pd.Series) -> pd.Series:
    """Annualized yield (%) → daily log return via simple/252."""
    simple = (yield_pct / 100.0) / TRADING_DAYS_PER_YEAR
    return np.log1p(simple)


def compute_returns(
    closes: pd.DataFrame,
    *,
    start: str = SAMPLE_START,
) -> pd.DataFrame:
    """Log-return panel; common start = first date with all non-cash returns."""
    cols = [c for c in PROXIES if c in closes.columns]
    px = closes.loc[pd.Timestamp(start) :, cols].sort_index()

    out = pd.DataFrame(index=px.index)
    non_cash = [c for c in cols if c != CASH_COL]
    for c in non_cash:
        out[c] = np.log(px[c] / px[c].shift(1))

    if CASH_COL in cols:
        out[CASH_COL] = cash_log_return(px[CASH_COL])

    # Common start: all non-cash log returns present (drop leading NA from diff).
    if non_cash:
        out = out.loc[out[non_cash].dropna(how="any").index.min() :]
    out = out.dropna(how="all")
    return out


def build_returns(
    *,
    start: str = SAMPLE_START,
    closes_path: Path = CLOSES_CSV,
    out_path: Path = RETURNS_CSV,
) -> pd.DataFrame:
    if not closes_path.exists():
        raise SystemExit(
            f"Missing {closes_path.relative_to(ROOT).as_posix()}. "
            "Run: uv run python -m market_regime preprocess"
        )
    closes = pd.read_csv(closes_path, index_col=0, parse_dates=True)
    rets = compute_returns(closes, start=start)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rets.to_csv(out_path)
    print(
        f"Wrote {out_path.relative_to(ROOT).as_posix()} "
        f"({len(rets)} rows, {rets.index.min().date()} -> {rets.index.max().date()})",
        flush=True,
    )
    return rets


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Daily log returns from data/closes.csv → data/returns.csv"
    )
    parser.add_argument(
        "--start",
        default=SAMPLE_START,
        help=f"Price sample start (default {SAMPLE_START}).",
    )
    args = parser.parse_args(argv)
    build_returns(start=args.start)


if __name__ == "__main__":
    main()
