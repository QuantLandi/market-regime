"""Locked teaching proxies for All Weather regime tables.

Default sample: 1997-03-01 → today. Binding constraint: US TIPS from March 1997.

DXY is USD / dollar exposure — never cash.
"""

from __future__ import annotations

from typing import TypedDict

SAMPLE_START = "1997-03-01"
SAMPLE_END = "latest"
SAMPLE_CONVENTION = "indices_tr"  # TR/index where available; front futures for HG/W/CL


class Proxy(TypedDict):
    sleeve: str
    name: str
    role: str
    bloomberg: str
    note: str


# Keys and bloomberg fields match the locked objectives table.
PROXIES: dict[str, Proxy] = {
    "spx_tr": {
        "sleeve": "equities",
        "name": "S&P 500 Total Return",
        "role": "core",
        "bloomberg": "SPXT Index",
        "note": "Not the ProShares ETF also tickered SPXT",
    },
    "ust_tr": {
        "sleeve": "nominal_bonds",
        "name": "Bloomberg US Treasury TR",
        "role": "core",
        "bloomberg": "LUATTRUU Index",
        "note": "Broad UST TR — not constant-maturity 10Y",
    },
    "tips_tr": {
        "sleeve": "il_bonds",
        "name": "US TIPS TR (Series-L)",
        "role": "core",
        "bloomberg": "LBUTLTRUU Index",
        "note": "Binds SAMPLE_START (1997-03-01)",
    },
    "cash": {
        "sleeve": "cash",
        "name": "3M T-bill",
        "role": "core",
        "bloomberg": "GB3 Govt",
        "note": "Convert rate → period return; not SOFR",
    },
    "gold": {
        "sleeve": "precious_metals",
        "name": "Gold spot",
        "role": "commodity",
        "bloomberg": "XAU Curncy",
        "note": "",
    },
    "copper": {
        "sleeve": "base_metals",
        "name": "Copper",
        "role": "commodity",
        "bloomberg": "HG1 Comdty",
        "note": "COMEX continuous front future",
    },
    "wheat": {
        "sleeve": "agriculturals",
        "name": "Wheat",
        "role": "commodity",
        "bloomberg": "W 1 Comdty",
        "note": "CBOT continuous front future",
    },
    "crude": {
        "sleeve": "energy",
        "name": "WTI crude",
        "role": "commodity",
        "bloomberg": "CL1 Comdty",
        "note": "NYMEX continuous front future",
    },
    "dxy": {
        "sleeve": "usd",
        "name": "Dollar index",
        "role": "optional_fx",
        "bloomberg": "DXY Curncy",
        "note": "Never cash",
    },
}
