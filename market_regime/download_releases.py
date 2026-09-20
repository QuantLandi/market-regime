"""Pull first-print GDP YoY / CPI YoY release history.

Default: ALFRED vintages via FRED API (``FRED_API_KEY``) — YoY from each
vintage's first appearance of the latest observation (covers the 1994 asset
panel). Optional: Bloomberg ECO ``ACTUAL_RELEASE`` (shorter Desktop history).

Writes gitignored ``data/releases_raw.csv``.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from market_regime.macro import MACRO_SERIES
from market_regime.proxies import SAMPLE_START
from market_regime.releases import RELEASES_RAW_CSV, normalize_releases, save_releases

ROOT = Path(__file__).resolve().parents[1]
HOST = "127.0.0.1"
PORT = 8194

# Load gitignored .env into os.environ (does not override vars already set).
load_dotenv(ROOT / ".env")


def _ymd(ts: pd.Timestamp | date | str) -> str:
    if isinstance(ts, str):
        return pd.Timestamp(ts).strftime("%Y%m%d")
    if isinstance(ts, date) and not isinstance(ts, datetime):
        return ts.strftime("%Y%m%d")
    return pd.Timestamp(ts).strftime("%Y%m%d")


def _as_date(el) -> date:
    v = el.getValue()
    if hasattr(v, "year"):
        return date(int(v.year), int(v.month), int(v.day))
    return date.fromisoformat(str(v)[:10])


def pull_bloomberg_actuals(*, start: str = SAMPLE_START) -> pd.DataFrame:
    """HistoricalDataRequest ACTUAL_RELEASE for each macro ticker."""
    import blpapi

    from market_regime.download import connect

    session = connect()
    rows: list[dict] = []
    try:
        svc = session.getService("//blp/refdata")
        start_ymd = _ymd(start)
        end_ymd = date.today().strftime("%Y%m%d")
        for key, meta in MACRO_SERIES.items():
            ticker = meta["bloomberg"]
            print(f"{key:8}  {ticker:18}  ACTUAL_RELEASE from {start_ymd}", flush=True)
            req = svc.createRequest("HistoricalDataRequest")
            req.append("securities", ticker)
            req.append("fields", "ACTUAL_RELEASE")
            req.set("startDate", start_ymd)
            req.set("endDate", end_ymd)
            req.set("periodicitySelection", "DAILY")
            session.sendRequest(req)

            n = 0
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
                        if (
                            not pt.hasElement("ACTUAL_RELEASE")
                            or pt.getElement("ACTUAL_RELEASE").isNull()
                        ):
                            continue
                        rel = _as_date(pt.getElement("date"))
                        val = pt.getElementAsFloat("ACTUAL_RELEASE")
                        rows.append(
                            {
                                "release_date": pd.Timestamp(rel),
                                "series": key,
                                "actual": float(val),
                                "release_type": pd.NA,
                                "obs_period": pd.NA,
                                "source": "bloomberg_actual_release",
                            }
                        )
                        n += 1
                if ev.eventType() == blpapi.Event.RESPONSE:
                    break
            print(f"  {n} release points", flush=True)
    finally:
        session.stop()

    if not rows:
        raise RuntimeError("Bloomberg returned no ACTUAL_RELEASE rows")
    df = normalize_releases(pd.DataFrame(rows))
    # BDH often forward-fills ACTUAL_RELEASE on non-release days; keep changes only.
    kept: list[pd.DataFrame] = []
    for series, part in df.groupby("series", sort=False):
        part = part.sort_values("release_date")
        changed = part["actual"].ne(part["actual"].shift(1))
        kept.append(part.loc[changed])
        print(
            f"  {series}: {changed.sum()} distinct prints "
            f"(from {len(part)} BDH rows)",
            flush=True,
        )
    return normalize_releases(pd.concat(kept, ignore_index=True))


def _fred_get(path: str, params: dict) -> dict:
    key = os.environ.get("FRED_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "ALFRED/FRED download needs FRED_API_KEY in the environment "
            "(free at https://fred.stlouisfed.org/docs/api/api_key.html)."
        )
    q = urllib.parse.urlencode({**params, "api_key": key, "file_type": "json"})
    url = f"https://api.stlouisfed.org/fred/{path}?{q}"
    try:
        with urllib.request.urlopen(url, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"FRED API error {exc.code} for {path}: {exc.reason}") from exc


def _alfred_observations(series_id: str, *, observation_start: str) -> pd.DataFrame:
    """All vintages: one row per (obs date, realtime_start, realtime_end, value)."""
    payload = _fred_get(
        "series/observations",
        {
            "series_id": series_id,
            "observation_start": observation_start,
            "realtime_start": "1776-07-04",
            "realtime_end": "9999-12-31",
        },
    )
    obs = payload.get("observations", [])
    if not obs:
        return pd.DataFrame(columns=["date", "realtime_start", "realtime_end", "value"])
    df = pd.DataFrame(obs)
    df["date"] = pd.to_datetime(df["date"])
    df["realtime_start"] = pd.to_datetime(df["realtime_start"])
    df["realtime_end"] = pd.to_datetime(df["realtime_end"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna(subset=["value"])


def _first_print_yoy_from_alfred(
    series_id: str,
    *,
    key: str,
    periods_per_year: int,
    observation_start: str,
) -> pd.DataFrame:
    """YoY % at each vintage where a new observation period first appears."""
    raw = _alfred_observations(series_id, observation_start=observation_start)
    if raw.empty:
        return pd.DataFrame()

    # First vintage that published each observation date.
    first = (
        raw.sort_values(["date", "realtime_start"])
        .groupby("date", as_index=False)
        .first()
    )
    # Snapshot levels as of each first-print release date = realtime_start.
    release_dates = sorted(first["realtime_start"].unique())
    rows: list[dict] = []
    prev_latest: pd.Timestamp | None = None

    levels_by_release: dict[pd.Timestamp, pd.Series] = {}
    for rel in release_dates:
        # Values known at rel: rows with realtime_start <= rel <= realtime_end
        snap = raw.loc[
            (raw["realtime_start"] <= rel) & (raw["realtime_end"] >= rel)
        ]
        # If multiple overlapping (shouldn't for a fixed rel), keep latest start
        snap = snap.sort_values("realtime_start").groupby("date", as_index=False).last()
        lvl = pd.Series(
            snap["value"].to_numpy(dtype=float),
            index=pd.DatetimeIndex(snap["date"]),
        ).sort_index()
        levels_by_release[pd.Timestamp(rel)] = lvl

    for rel, lvl in levels_by_release.items():
        if lvl.empty:
            continue
        latest = pd.Timestamp(lvl.index.max())
        # Only emit when this release introduces a new latest obs period
        # (true first print of that period).
        if prev_latest is not None and latest <= prev_latest:
            continue
        target = latest - pd.DateOffset(years=1)
        tol = pd.Timedelta(days=40 if periods_per_year == 4 else 3)
        if target in lvl.index:
            year_ago = target
        else:
            year_ago = min(lvl.index, key=lambda d: abs(d - target))
            if abs(year_ago - target) > tol:
                prev_latest = latest
                continue
        yoy = (float(lvl.loc[latest]) / float(lvl.loc[year_ago]) - 1.0) * 100.0

        rows.append(
            {
                "release_date": pd.Timestamp(rel).normalize(),
                "series": key,
                "actual": yoy,
                "release_type": "first_print",
                "obs_period": latest.strftime("%Y-%m-%d"),
                "source": f"alfred:{series_id}",
            }
        )
        prev_latest = latest

    return pd.DataFrame(rows)


def pull_alfred_first_prints(*, start: str = SAMPLE_START) -> pd.DataFrame:
    """Build first-print YoY paths for GDP (GDPC1) and CPI (CPIAUCSL)."""
    start_obs = (pd.Timestamp(start) - pd.DateOffset(years=2)).strftime("%Y-%m-%d")
    frames: list[pd.DataFrame] = []
    for key, meta in MACRO_SERIES.items():
        sid = meta["alfred"]
        freq = meta["frequency"]
        ppy = 4 if freq == "quarterly" else 12
        print(f"{key:8}  ALFRED {sid}  first-print YoY", flush=True)
        part = _first_print_yoy_from_alfred(
            sid, key=key, periods_per_year=ppy, observation_start=start_obs
        )
        if part.empty:
            print("  FAIL: empty", flush=True)
            continue
        part = part.loc[part["release_date"] >= pd.Timestamp(start)]
        print(f"  {len(part)} first prints", flush=True)
        frames.append(part)
    if not frames:
        raise SystemExit("ALFRED returned no first-print rows")
    return normalize_releases(pd.concat(frames, ignore_index=True))


def ingest_csv(path: Path) -> pd.DataFrame:
    return normalize_releases(pd.read_csv(path))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Download first-print GDP/CPI YoY releases "
            "(ALFRED vintages by default; optional Bloomberg ACTUAL_RELEASE)."
        )
    )
    parser.add_argument(
        "--source",
        choices=("alfred", "bloomberg", "csv"),
        default="alfred",
        help="alfred (default, needs FRED_API_KEY), bloomberg, or csv ingest",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="With --source csv: path to releases file to normalize/write",
    )
    parser.add_argument(
        "--start",
        default=SAMPLE_START,
        help=f"Earliest release_date to keep (default {SAMPLE_START}).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=RELEASES_RAW_CSV,
        help="Output path (default data/releases_raw.csv).",
    )
    args = parser.parse_args(argv)

    if args.source == "bloomberg":
        try:
            df = pull_bloomberg_actuals(start=args.start)
        except ImportError as exc:
            raise SystemExit(
                "blpapi not installed. On a Bloomberg PC: uv sync --extra bloomberg\n"
                "Or use: uv run python -m market_regime download-releases --source alfred"
            ) from exc
        except SystemExit:
            raise
        except Exception as exc:
            raise SystemExit(
                f"Bloomberg pull failed: {exc}\n"
                "Fallback: --source alfred (FRED_API_KEY) or --source csv"
            ) from exc
    elif args.source == "alfred":
        df = pull_alfred_first_prints(start=args.start)
    else:
        if args.csv is None:
            raise SystemExit("--source csv requires --csv PATH")
        df = ingest_csv(args.csv)
        df = df.loc[df["release_date"] >= pd.Timestamp(args.start)]

    path = save_releases(df, args.out)
    print(
        f"Wrote {path.relative_to(ROOT).as_posix()} "
        f"({len(df)} rows; series={sorted(df['series'].unique())})",
        flush=True,
    )


if __name__ == "__main__":
    main()
