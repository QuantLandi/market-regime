"""First-print growth / inflation series for regime dating.

Not asset sleeves. Not survey medians. Actuals as first released only —
never current-vintage revised HP paths.
"""

from __future__ import annotations

from typing import TypedDict


class MacroSeries(TypedDict):
    name: str
    role: str
    bloomberg: str
    alfred: str
    frequency: str


# Keys = series id in data/releases_raw.csv
MACRO_SERIES: dict[str, MacroSeries] = {
    "gdp_yoy": {
        "name": "Real GDP YoY % (first print)",
        "role": "growth_rate",
        "bloomberg": "GDP CYOY Index",
        "alfred": "GDPC1",
        "frequency": "quarterly",
    },
    "cpi_yoy": {
        "name": "CPI headline YoY % (first print)",
        "role": "inflation_rate",
        "bloomberg": "CPI YOY Index",
        "alfred": "CPIAUCSL",
        "frequency": "monthly",
    },
}

GROWTH_SERIES = "gdp_yoy"
INFLATION_SERIES = "cpi_yoy"
