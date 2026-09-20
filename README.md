# Market regime

Locked All Weather proxies + Bloomberg pull. Data stays local (gitignored).

## Setup

```bash
uv sync
uv sync --extra bloomberg   # on a Bloomberg PC only
```

## Proxies

See `market_regime/proxies.py`. Sample: **1994-03-01 → today** (complete daily rows). No TIPS; copper = LME `LMCADS03 Comdty`.

## Pull

```bash
uv run python -m market_regime --update
```

Writes `data/closes.csv` (not committed).

## Load

```python
import pandas as pd
from market_regime import SAMPLE_START

df = pd.read_csv("data/closes.csv", index_col=0, parse_dates=True)
df = df.loc[SAMPLE_START:].dropna(how="any")
```
