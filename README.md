# Market regime

Locked All Weather proxies + Bloomberg pull. Data stays local (gitignored).

## Setup

```bash
uv sync
uv sync --extra bloomberg   # on a Bloomberg PC only
```

## Proxies

See `market_regime/proxies.py`. Sample from **1994-03-01**. No TIPS; copper/wheat/crude = S&P GSCI **excess return**.

**Cash (`GB3 Govt`):** US Generic 3M T-bill; `PX_LAST` is an **annualized yield in percent** (bill quote), not a total-return index. Daily teaching conversion: `simple = (y/100)/252`, then `log(1+simple)`.

## Pipeline

```bash
uv run python -m market_regime download          # -> data/closes_raw.csv
uv run python -m market_regime download --update
uv run python -m market_regime preprocess        # -> data/closes.csv (ffill)
uv run python -m market_regime returns           # -> data/returns.csv (daily log returns)
```

| File | Role |
|------|------|
| `data/closes_raw.csv` | Raw Bloomberg outer join |
| `data/closes.csv` | Prices / levels, forward-filled |
| `data/returns.csv` | Daily log returns (cash via rate→simple/252→log1p) |

## Returns

- Non-cash: `log(P_t / P_{t-1})`
- Cash: `log1p((y_pct/100)/252)`
- Panel starts at the first date where **all non-cash** returns are non-null
- Annualize means with ×252 when needed
