# Market regime

Locked All Weather proxies + Bloomberg pull. Data stays local (gitignored).

## Setup

```bash
uv sync
uv sync --extra bloomberg   # on a Bloomberg PC only
```

## Proxies

See `market_regime/proxies.py`. Sample from **1994-03-01**. No TIPS; copper/wheat/crude = S&P GSCI **excess return**.

## Pipeline

```bash
uv run python -m market_regime download          # → data/closes_raw.csv (outer join, NAs kept)
uv run python -m market_regime download --update
uv run python -m market_regime preprocess        # → data/closes.csv (ffill from SAMPLE_START)
```

| File | Role |
|------|------|
| `data/closes_raw.csv` | Raw Bloomberg outer join |
| `data/closes.csv` | Analysis panel (forward-filled) |

## Load (analysis)

```python
import pandas as pd
from market_regime import SAMPLE_START

df = pd.read_csv("data/closes.csv", index_col=0, parse_dates=True)
df = df.loc[SAMPLE_START:]
```
