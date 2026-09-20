"""CLI: download (Bloomberg raw) | preprocess (ffill)."""

from __future__ import annotations

import argparse
import sys

from market_regime.download import main as download_main
from market_regime.preprocess import main as preprocess_main


def main() -> None:
    parser = argparse.ArgumentParser(
        description="All Weather proxy panel: download raw, then preprocess."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("download", help="Bloomberg pull -> data/closes_raw.csv")
    sub.add_parser("preprocess", help="ffill raw -> data/closes.csv")

    args, rest = parser.parse_known_args()
    if args.cmd == "download":
        download_main(rest)
    else:
        preprocess_main(rest)


if __name__ == "__main__":
    main()
