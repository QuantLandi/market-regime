"""Print locked proxies and default sample."""

from __future__ import annotations

from market_regime.proxies import PROXIES, SAMPLE_CONVENTION, SAMPLE_START


def main() -> None:
    print(f"sample_start={SAMPLE_START}  convention={SAMPLE_CONVENTION}")
    print()
    for key, p in PROXIES.items():
        print(f"{key:8}  {p['bloomberg']:18}  {p['name']}")


if __name__ == "__main__":
    main()
