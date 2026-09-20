"""CLI: download | preprocess | returns | download-releases | regimes."""

from __future__ import annotations

import argparse

from market_regime.download import main as download_main
from market_regime.download_releases import main as download_releases_main
from market_regime.preprocess import main as preprocess_main
from market_regime.regimes import main as regimes_main
from market_regime.returns import main as returns_main


def main() -> None:
    parser = argparse.ArgumentParser(
        description="All Weather proxy panel + first-print growth/inflation regimes."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("download", help="Bloomberg asset pull -> data/closes_raw.csv")
    sub.add_parser("preprocess", help="ffill raw -> data/closes.csv")
    sub.add_parser("returns", help="log returns -> data/returns.csv")
    sub.add_parser(
        "download-releases",
        help="First-print GDP/CPI YoY -> data/releases_raw.csv",
    )
    sub.add_parser(
        "regimes",
        help="Map A/B labels + mean returns by box -> data/regimes.csv",
    )

    args, rest = parser.parse_known_args()
    if args.cmd == "download":
        download_main(rest)
    elif args.cmd == "preprocess":
        preprocess_main(rest)
    elif args.cmd == "returns":
        returns_main(rest)
    elif args.cmd == "download-releases":
        download_releases_main(rest)
    else:
        regimes_main(rest)


if __name__ == "__main__":
    main()
