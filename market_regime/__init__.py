"""Growth–inflation regime analytics for Global Macro (All Weather four-box lens)."""

from market_regime.panel import load_daily_closes
from market_regime.proxies import DAILY_SAMPLE_START, PROXIES, SAMPLE_START

__all__ = [
    "DAILY_SAMPLE_START",
    "PROXIES",
    "SAMPLE_START",
    "load_daily_closes",
]
