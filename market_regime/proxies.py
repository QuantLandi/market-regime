"""Locked teaching proxies for All Weather regime tables.

No TIPS: rising-inflation boxes rely on commodities (say so in class).
DXY is USD / dollar exposure — never cash. Cash is the risk-free sleeve.
"""

from __future__ import annotations

from typing import TypedDict

# Frozen panel and Bloomberg pulls: dense daily only (LUATTRUU daily from Mar 1994).
SAMPLE_START = "1994-03-01"
DAILY_SAMPLE_START = SAMPLE_START


class Proxy(TypedDict):
    sleeve: str
    name: str
    role: str
    bloomberg: str


# Keys = column names in data/closes.csv
PROXIES: dict[str, Proxy] = {
    "spx_tr": {
        "sleeve": "equities",
        "name": "S&P 500 Total Return",
        "role": "core",
        "bloomberg": "SPXT Index",
    },
    "ust_tr": {
        "sleeve": "nominal_bonds",
        "name": "Bloomberg US Treasury TR",
        "role": "core",
        "bloomberg": "LUATTRUU Index",
    },
    "cash": {
        "sleeve": "cash",
        "name": "3M T-bill",
        "role": "core",
        "bloomberg": "GB3 Govt",
    },
    "gold": {
        "sleeve": "precious_metals",
        "name": "Gold spot",
        "role": "commodity",
        "bloomberg": "XAU Curncy",
    },
    "copper": {
        "sleeve": "base_metals",
        "name": "LME Copper 3M",
        "role": "commodity",
        "bloomberg": "LMCADS03 Comdty",
    },
    "wheat": {
        "sleeve": "agriculturals",
        "name": "Wheat",
        "role": "commodity",
        "bloomberg": "W 1 Comdty",
    },
    "crude": {
        "sleeve": "energy",
        "name": "WTI crude",
        "role": "commodity",
        "bloomberg": "CL1 Comdty",
    },
    "dxy": {
        "sleeve": "usd",
        "name": "Dollar index",
        "role": "optional_fx",
        "bloomberg": "DXY Curncy",
    },
}
