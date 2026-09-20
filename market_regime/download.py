"""Daily PX_LAST for locked All Weather proxies via Bloomberg Desktop API.

Writes gitignored data/closes_raw.csv only (no ffill). Then:

  uv run python -m market_regime preprocess
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path

import blpapi
import pandas as pd

from market_regime.proxies import PROXIES, SAMPLE_START

HOST = "127.0.0.1"
PORT = 8194
FIELD = "PX_LAST"
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CLOSES_RAW_CSV = DATA_DIR / "closes_raw.csv"


def _as_date(el: blpapi.Element) -> date:
    v = el.getValue()
    if hasattr(v, "year"):
        return date(int(v.year), int(v.month), int(v.day))
    return date.fromisoformat(str(v)[:10])


def _ymd(ts: pd.Timestamp | date | str) -> str:
    if isinstance(ts, str):
        return pd.Timestamp(ts).strftime("%Y%m%d")
    if isinstance(ts, date) and not isinstance(ts, datetime):
        return ts.strftime("%Y%m%d")
    return pd.Timestamp(ts).strftime("%Y%m%d")


def connect() -> blpapi.Session:
    opts = blpapi.SessionOptions()
    opts.setServerHost(HOST)
    opts.setServerPort(PORT)
    session = blpapi.Session(opts)
    if not session.start():
        raise SystemExit("Could not start Bloomberg session. Is the Terminal logged in?")
    if not session.openService("//blp/refdata"):
        session.stop()
        raise SystemExit("Could not open //blp/refdata")
    return session


def pull_one(session: blpapi.Session, ticker: str, *, start: str) -> pd.Series:
    """One HistoricalDataRequest per ticker (do not batch / tight-loop)."""
    svc = session.getService("//blp/refdata")
    req = svc.createRequest("HistoricalDataRequest")
    req.append("securities", ticker)
    req.append("fields", FIELD)
    req.set("startDate", start)
    req.set("endDate", date.today().strftime("%Y%m%d"))
    req.set("periodicitySelection", "DAILY")
    session.sendRequest(req)

    rows: list[tuple[date, float]] = []
    while True:
        ev = session.nextEvent(60_000)
        for msg in ev:
            if msg.hasElement("responseError"):
                raise RuntimeError(str(msg.getElement("responseError")))
            if not msg.hasElement("securityData"):
                continue
            sec = msg.getElement("securityData")
            if sec.hasElement("securityError"):
                raise RuntimeError(str(sec.getElement("securityError")))
            field_data = sec.getElement("fieldData")
            for i in range(field_data.numValues()):
                pt = field_data.getValueAsElement(i)
                if not pt.hasElement(FIELD) or pt.getElement(FIELD).isNull():
                    continue
                rows.append((_as_date(pt.getElement("date")), pt.getElementAsFloat(FIELD)))
        if ev.eventType() == blpapi.Event.RESPONSE:
            break

    if not rows:
        return pd.Series(dtype=float)
    s = pd.Series({pd.Timestamp(d): float(v) for d, v in rows}).sort_index()
    s.index.name = "date"
    return s


def load_raw(path: Path = CLOSES_RAW_CSV) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path, index_col=0, parse_dates=True)


def merge_series(existing: pd.Series, new: pd.Series) -> pd.Series:
    name = existing.name or new.name
    if existing.empty and new.empty:
        return pd.Series(dtype=float, name=name)
    if existing.empty:
        return new.rename(name)
    if new.empty:
        return existing.rename(name)
    out = existing.copy()
    out = out.reindex(out.index.union(new.index)).sort_index()
    out.update(new)
    return out.rename(name)


def download(*, update: bool = False, start: str = SAMPLE_START) -> pd.DataFrame:
    """Pull Bloomberg and write closes_raw.csv (outer join, no ffill)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    existing = load_raw() if update else None
    if update and existing is None:
        print("No existing data/closes_raw.csv; doing a full download.", flush=True)

    start_ts = pd.Timestamp(start)
    start_ymd = _ymd(start)
    panel_cols: dict[str, pd.Series] = {}
    failed: dict[str, str] = {}

    session = connect()
    try:
        for key, proxy in PROXIES.items():
            ticker = proxy["bloomberg"]
            old = (
                existing[key].rename(key)
                if existing is not None and key in existing.columns
                else pd.Series(dtype=float, name=key)
            )
            valid = old.dropna()
            first = None if valid.empty else pd.Timestamp(valid.index.min())
            last = None if valid.empty else pd.Timestamp(valid.index.max())

            if update and last is not None and first is not None and first <= start_ts:
                req_start = _ymd(last)
                mode = "forward"
            else:
                req_start = start_ymd
                mode = "full" if valid.empty or not update else "backfill"

            print(f"{key:8}  {ticker:18}  {mode} from {req_start}", flush=True)
            try:
                new = pull_one(session, ticker, start=req_start).rename(key)
            except Exception as exc:
                failed[key] = str(exc)
                print(f"  FAIL: {exc}", flush=True)
                if update and not old.empty:
                    panel_cols[key] = old
                    print("  kept existing series", flush=True)
                continue

            if new.empty:
                failed[key] = "empty fieldData"
                print("  FAIL: empty", flush=True)
                if update and not old.empty:
                    panel_cols[key] = old
                    print("  kept existing series", flush=True)
                continue

            if update and not valid.empty:
                merged = merge_series(old, new)
                added = int(new.dropna().index.difference(valid.index).size)
                panel_cols[key] = merged
                print(
                    f"  +{added} new dates "
                    f"(panel {merged.dropna().shape[0]} non-null; "
                    f"{merged.dropna().index.min().date()} -> "
                    f"{merged.dropna().index.max().date()})",
                    flush=True,
                )
            else:
                panel_cols[key] = new
                print(
                    f"  {new.dropna().shape[0]} rows  "
                    f"{new.index.min().date()} -> {new.index.max().date()}",
                    flush=True,
                )
    finally:
        session.stop()

    if not panel_cols:
        raise SystemExit(f"No series downloaded. Failed: {failed}")

    keys = [k for k in PROXIES if k in panel_cols]
    panel = pd.concat({k: panel_cols[k] for k in keys}, axis=1, sort=True)
    panel.index.name = "date"
    panel = panel.loc[start_ts:].dropna(how="all")
    panel.to_csv(CLOSES_RAW_CSV)
    n_na = int(panel.isna().sum().sum())
    print(
        f"Wrote {CLOSES_RAW_CSV.relative_to(ROOT).as_posix()} "
        f"({len(panel)} rows, {n_na} NA — raw outer join, no ffill)",
        flush=True,
    )
    if failed:
        print("Failed:", "; ".join(f"{k} ({v})" for k, v in failed.items()), flush=True)
    return panel


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Download locked All Weather proxies via Bloomberg DAPI (raw)."
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Extend forward from last date; backfill if history starts after --start.",
    )
    parser.add_argument(
        "--start",
        default=SAMPLE_START,
        help=f"Panel start (default {SAMPLE_START}).",
    )
    args = parser.parse_args(argv)
    download(update=args.update, start=args.start)


if __name__ == "__main__":
    main()
