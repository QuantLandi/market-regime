# Market regime

Software workspace for growth–inflation **regime labeling** and **asset-class returns by regime** (All Weather four-box lens).

Tied to Session 5 candidate work: see [sessions/session05/objectives.md](../sessions/session05/objectives.md). May ship in Session 5 or move to Slot 6 — the code lives here either way.

## Layout

| Path | Role |
|------|------|
| [market_regime/](market_regime/) | Python package |
| [data/closes.csv](data/closes.csv) | Frozen **complete daily** panel from **1994-03-01** |

## Sample window

`SAMPLE_START` = `DAILY_SAMPLE_START` = **1994-03-01**  
(`LUATTRUU` is month-end only before that; sparse pre-1994 history was removed.)

```bash
uv run python -c "from market_regime import load_daily_closes; print(load_daily_closes().shape)"
```

## Run

```bash
uv run python examples/list_proxies.py
```

## Status

- Proxies: no TIPS; copper = LME `LMCADS03 Comdty`
- Panel: complete daily rows only, 1994-03-01 → present
- Regime dating: still open
- Avg return-by-regime table: not built yet

Bloomberg re-pull (keeps start at 1994-03-01):

```bash
cd market-regime
uv sync --extra bloomberg
uv run python examples/download_proxies.py --update
```
