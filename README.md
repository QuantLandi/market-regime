# Market regime

Growth–inflation **regime labeling** and **asset-class returns by regime** (All Weather four-box lens), for Global Macro teaching.

## Default sample (locked)

- **Start:** 1997-03-01 (US TIPS binds the panel)
- **End:** latest available
- **Convention:** total-return / index series where they exist; front-month futures for copper, wheat, crude
- **Series:** locked in [`market_regime/proxies.py`](market_regime/proxies.py)

| Sleeve | Series | Ticker |
| --- | --- | --- |
| Equities | S&P 500 Total Return | SPXT Index |
| Nominal bonds | Bloomberg US Treasury TR | LUATTRUU Index |
| IL bonds | US TIPS TR (Series-L) | LBUTLTRUU Index |
| Cash | 3M T-bill | GB3 Govt |
| Precious metals | Gold spot | XAU Curncy |
| Base metals | Copper | HG1 Comdty |
| Agriculturals | Wheat | W 1 Comdty |
| Energy | WTI crude | CL1 Comdty |
| USD (optional FX) | Dollar index | DXY Curncy (never cash) |

## Layout

| Path | Role |
|------|------|
| [market_regime/](market_regime/) | Python package |
| [data/](data/) | Frozen CSVs (Bloomberg / FRED exports); relative paths |
| [examples/](examples/) | Small runnable scripts |

## Setup

```bash
uv sync
```

## Run

```bash
uv run python examples/list_proxies.py
```

## Status

- Sample + series/tickers: **locked**
- Regime dating (expectations vs realized): still open
- Avg return-by-regime table: not built yet
