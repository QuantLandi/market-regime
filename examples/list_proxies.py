"""Print locked proxies and sample windows."""

from __future__ import annotations

from market_regime.proxies import DAILY_SAMPLE_START, PROXIES, SAMPLE_START


def main() -> None:
    print(f"SAMPLE_START (pull)     = {SAMPLE_START}")
    print(f"DAILY_SAMPLE_START      = {DAILY_SAMPLE_START}")
    for key, p in PROXIES.items():
        print(f"{key:8}  {p['sleeve']:18}  {p['bloomberg']:18}  {p['name']}  [{p['role']}]")


if __name__ == "__main__":
    main()
