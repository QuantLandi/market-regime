"""Build analysis panel from raw Bloomberg download (ffill gaps)."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from market_regime.proxies import SAMPLE_START

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CLOSES_RAW_CSV = DATA_DIR / "closes_raw.csv"
CLOSES_CSV = DATA_DIR / "closes.csv"


def preprocess(
    *,
    start: str = SAMPLE_START,
    raw_path: Path = CLOSES_RAW_CSV,
    out_path: Path = CLOSES_CSV,
) -> pd.DataFrame:
    """Slice from ``start``, forward-fill, drop all-empty rows → closes.csv."""
    if not raw_path.exists():
        raise SystemExit(
            f"Missing {raw_path.relative_to(ROOT).as_posix()}. "
            "Run: uv run python -m market_regime download"
        )
    raw = pd.read_csv(raw_path, index_col=0, parse_dates=True).sort_index()
    panel = raw.loc[pd.Timestamp(start) :].ffill().dropna(how="all")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(out_path)
    n_na = int(panel.isna().sum().sum())
    print(
        f"Wrote {out_path.relative_to(ROOT).as_posix()} "
        f"({len(panel)} rows, {n_na} remaining NA after ffill — usually leading)",
        flush=True,
    )
    return panel


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Forward-fill raw closes into the analysis panel."
    )
    parser.add_argument(
        "--start",
        default=SAMPLE_START,
        help=f"Panel start (default {SAMPLE_START}).",
    )
    args = parser.parse_args(argv)
    preprocess(start=args.start)


if __name__ == "__main__":
    main()
