"""CLI: download | preprocess | returns."""

from __future__ import annotations

import argparse

from market_regime.download import main as download_main
from market_regime.preprocess import main as preprocess_main
from market_regime.returns import main as returns_main


def main() -> None:
    parser = argparse.ArgumentParser(
        description="All Weather proxy panel: download, preprocess, returns."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("download", help="Bloomberg pull -> data/closes_raw.csv")
    sub.add_parser("preprocess", help="ffill raw -> data/closes.csv")
    sub.add_parser("returns", help="log returns -> data/returns.csv")

    args, rest = parser.parse_known_args()
    if args.cmd == "download":
        download_main(rest)
    elif args.cmd == "preprocess":
        preprocess_main(rest)
    else:
        returns_main(rest)


if __name__ == "__main__":
    main()
