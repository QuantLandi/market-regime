# Market regime

Locked All Weather **asset** proxies + first-print **growth/inflation** regime
labels. Data stays local (gitignored).

## Setup

```bash
uv sync
uv sync --extra bloomberg   # on a Bloomberg PC only
cp .env.example .env        # then set FRED_API_KEY (gitignored)
```

`download-releases` reads `FRED_API_KEY` from the environment or from `.env`.

## Asset proxies

See `market_regime/proxies.py`. Sample from **1994-03-01**. No TIPS;
copper/wheat/crude = S&P GSCI **excess return**.

**Cash (`GB3 Govt`):** US Generic 3M T-bill; `PX_LAST` is an **annualized yield in
percent** (bill quote), not a total-return index. Daily teaching conversion:
`simple = (y/100)/252`, then `log(1+simple)`.

## Growth / inflation regimes (first print only)

Four-box **geometry** inspired by *The All Weather Story*; **dating is not**
Bridgewater’s surprises-vs-expectations. We use **realized first prints** of
GDP YoY and CPI YoY — never today’s revised path, never ECO survey medians.

| Series | Meaning | ALFRED (default) | Bloomberg ECO (optional) |
|--------|---------|------------------|--------------------------|
| `gdp_yoy` | Real GDP YoY % as first released | `GDPC1` → YoY in vintage | `GDP CYOY Index` |
| `cpi_yoy` | CPI headline YoY % as first released | `CPIAUCSL` → YoY in vintage | `CPI YOY Index` |

**Two maps**

| Map | Axes | Calculus on the *level* |
|-----|------|-------------------------|
| **A** `map_a` | `sign(g) × sign(π)` | 1st derivatives (rate up/down) |
| **B** `map_b` | `sign(Δg) × sign(Δπ)` | 2nd derivatives (accel/slow) |

Sign rule: `> 0` → `up`, else `down`. Box ids look like `g_up__pi_down`.

**Timing:** new label from the **next** session after `release_date`; hold until
the next print. Asset returns can start 1994-03-01; Map A is non-null only once
**both** series have a first print; Map B needs a prior print for each Δ.

## Pipeline

```bash
uv run python -m market_regime download          # -> data/closes_raw.csv
uv run python -m market_regime download --update
uv run python -m market_regime preprocess        # -> data/closes.csv (ffill)
uv run python -m market_regime returns           # -> data/returns.csv

# First-print macro (default: ALFRED; needs FRED_API_KEY)
uv run python -m market_regime download-releases
uv run python -m market_regime download-releases --source bloomberg  # Terminal; shorter history
uv run python -m market_regime download-releases --source csv --csv data/releases.example.csv
# example CSV is schema-only (1994 stub) — replace with a full history before teaching

uv run python -m market_regime regimes           # -> data/regimes.csv + regime_means.csv
```

| File | Role |
|------|------|
| `data/closes_raw.csv` | Raw Bloomberg outer join (assets) |
| `data/closes.csv` | Prices / levels, forward-filled |
| `data/returns.csv` | Daily log returns |
| `data/releases_raw.csv` | First-print GDP/CPI YoY events |
| `data/releases.example.csv` | Tiny schema example (tracked) |
| `data/regimes.csv` | Daily Map A/B labels on the returns calendar |
| `data/regime_means.csv` | Annualized mean log returns (×252) by box |

### `releases_raw.csv` schema

`release_date,series,actual,release_type,obs_period,source`

- `series`: `gdp_yoy` or `cpi_yoy`
- `actual`: YoY percent as printed that morning
- GDP may list Advance / Second / Third as separate rows (each updates `g`)

## Returns

- Non-cash: `log(P_t / P_{t-1})`
- Cash: `log1p((y_pct/100)/252)`
- Panel starts at the first date where **all non-cash** returns are non-null
- Annualize means with ×252 when needed
