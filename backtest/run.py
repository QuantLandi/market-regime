"""Run expanding-window regime LS backtest for equal and inv-vol weights."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from backtest.config import (
    DEFAULT_MIN_HISTORY,
    MAP_COL,
    MAP_COLS,
    MAP_COMPARE_DIR,
    MAP_COMPARE_FIG,
    MAP_COMPARE_SUMMARY_CSV,
    MAP_LABELS,
    REGIMES_CSV,
    RESULTS_DIR,
    RETURNS_CSV,
    ROOT,
    SUMMARY_COMPARE_CSV,
    WEIGHT_SCHEMES,
    scheme_paths,
    scheme_results_dir,
)
from backtest.engine import build_daily, summarize
from backtest.plot import plot_comparisons, plot_equity_and_drawdown, plot_map_inv_vol_ls
from backtest.recap import write_recap
from backtest.signals import expanding_weight_panel, oracle_weight_panel


def run_scheme(
    returns: pd.DataFrame,
    regimes: pd.DataFrame,
    *,
    scheme: str,
    min_history: int,
    with_oracle: bool,
    map_col: str = MAP_COL,
    write_outputs: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if write_outputs:
        paths = scheme_paths(scheme)
        scheme_results_dir(scheme).mkdir(parents=True, exist_ok=True)

    weights, bench, rebalances = expanding_weight_panel(
        returns,
        regimes,
        min_history=min_history,
        scheme=scheme,
        map_col=map_col,
    )
    oracle_w = (
        oracle_weight_panel(returns, regimes, scheme=scheme, map_col=map_col)
        if with_oracle
        else None
    )
    daily = build_daily(
        returns,
        regimes,
        weights,
        bench,
        map_col=map_col,
        include_oracle=oracle_w,
    )
    summary = summarize(daily, scheme=scheme, map_col=map_col)

    if write_outputs:
        daily.to_csv(paths["daily"])
        rebalances.to_csv(paths["rebalances"])
        summary.to_csv(paths["summary"], index=False)
        eq_path, dd_path = plot_equity_and_drawdown(
            daily,
            scheme=scheme,
            equity_path=paths["equity"],
            drawdown_path=paths["drawdown"],
        )

        n_live = int(rebalances["live"].sum()) if not rebalances.empty else 0
        print(f"\n=== scheme={scheme} map={map_col} ===", flush=True)
        print(
            f"Wrote {paths['daily'].relative_to(ROOT).as_posix()} ({len(daily)} days)",
            flush=True,
        )
        print(
            f"Wrote {paths['rebalances'].relative_to(ROOT).as_posix()} "
            f"({len(rebalances)} rebalances, {n_live} live; min_history={min_history})",
            flush=True,
        )
        print(f"Wrote {paths['summary'].relative_to(ROOT).as_posix()}", flush=True)
        print(
            f"Wrote {eq_path.relative_to(ROOT).as_posix()}, "
            f"{dd_path.relative_to(ROOT).as_posix()}",
            flush=True,
        )
        print(summary.to_string(index=False), flush=True)

    return daily, rebalances, summary


def run_map_compare(
    returns: pd.DataFrame,
    regimes: pd.DataFrame,
    *,
    min_history: int,
) -> pd.DataFrame:
    """Expanding inv-vol LS on Map A / B / joint; equity overlay + summary."""
    daily_by_map: dict[str, pd.DataFrame] = {}
    summaries: list[pd.DataFrame] = []
    MAP_COMPARE_DIR.mkdir(parents=True, exist_ok=True)

    print("\n=== map compare: expanding inv-vol LS ===", flush=True)
    for map_col in MAP_COLS:
        daily, reb, summary = run_scheme(
            returns,
            regimes,
            scheme="inv_vol",
            min_history=min_history,
            with_oracle=False,
            map_col=map_col,
            write_outputs=False,
        )
        daily_by_map[map_col] = daily
        summaries.append(summary)
        live = daily["regime"].notna() & (daily["gross"] > 0)
        n_live = int(live.sum())
        n_reb = len(reb)
        print(
            f"  {MAP_LABELS.get(map_col, map_col)}: "
            f"{n_reb} rebalances, {n_live} live days",
            flush=True,
        )
        # Persist per-map dailies under map_compare/
        sub = MAP_COMPARE_DIR / map_col
        sub.mkdir(parents=True, exist_ok=True)
        daily.to_csv(sub / "daily.csv")
        reb.to_csv(sub / "rebalances.csv")
        summary.to_csv(sub / "summary.csv", index=False)

    compare = pd.concat(summaries, ignore_index=True)
    compare.to_csv(MAP_COMPARE_SUMMARY_CSV, index=False)
    fig_path = plot_map_inv_vol_ls(daily_by_map, out_path=MAP_COMPARE_FIG)
    print(f"Wrote {MAP_COMPARE_SUMMARY_CSV.relative_to(ROOT).as_posix()}", flush=True)
    print(f"Wrote {fig_path.relative_to(ROOT).as_posix()}", flush=True)

    # Compact print: LS Sharpe / return / vol / DD by map
    rows = []
    for map_col in MAP_COLS:
        sub = compare.loc[
            (compare["map_col"] == map_col)
            & (compare["strategy"] == "expanding_ls_inv_vol")
        ]
        m = {r["metric"]: r["value"] for _, r in sub.iterrows()}
        rows.append(
            {
                "map": MAP_LABELS.get(map_col, map_col),
                "ann_return": m.get("ann_total_mean"),
                "ann_vol": m.get("ann_total_vol"),
                "sharpe": m.get("sharpe_total"),
                "max_dd": m.get("max_drawdown"),
            }
        )
    print(pd.DataFrame(rows).to_string(index=False), flush=True)
    return compare


def run(
    *,
    returns_path: Path = RETURNS_CSV,
    regimes_path: Path = REGIMES_CSV,
    min_history: int = DEFAULT_MIN_HISTORY,
    with_oracle: bool = True,
    schemes: tuple[str, ...] = WEIGHT_SCHEMES,
    map_compare: bool = True,
) -> dict[str, tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
    for path, hint in (
        (returns_path, "uv run python -m market_regime returns"),
        (regimes_path, "uv run python -m market_regime regimes"),
    ):
        if not path.exists():
            raise SystemExit(
                f"Missing {path.relative_to(ROOT).as_posix()}. Run: {hint}"
            )

    returns = pd.read_csv(returns_path, index_col=0, parse_dates=True)
    regimes = pd.read_csv(regimes_path, index_col=0, parse_dates=True)

    out: dict[str, tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]] = {}
    daily_by_scheme: dict[str, pd.DataFrame] = {}
    summaries: list[pd.DataFrame] = []
    first_rebalances: pd.DataFrame | None = None

    for scheme in schemes:
        daily, reb, summary = run_scheme(
            returns,
            regimes,
            scheme=scheme,
            min_history=min_history,
            with_oracle=with_oracle,
            map_col=MAP_COL,
        )
        out[scheme] = (daily, reb, summary)
        daily_by_scheme[scheme] = daily
        summaries.append(summary)
        if first_rebalances is None:
            first_rebalances = reb

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if summaries:
        compare = pd.concat(summaries, ignore_index=True)
        compare.to_csv(SUMMARY_COMPARE_CSV, index=False)
        print(f"\nWrote {SUMMARY_COMPARE_CSV.relative_to(ROOT).as_posix()}", flush=True)

        compare_figs = plot_comparisons(daily_by_scheme)
        for path in compare_figs:
            print(f"Wrote {path.relative_to(ROOT).as_posix()}", flush=True)

        recap_path = write_recap(
            compare, min_history=min_history, rebalances=first_rebalances
        )
        print(f"Wrote {recap_path.relative_to(ROOT).as_posix()}", flush=True)

    if map_compare:
        run_map_compare(returns, regimes, min_history=min_history)

    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Expanding-window regime long/short backtest: signs from past mean "
            "excess; equal-weight and inv-vol schemes; hold until next GDP/CPI print; "
            "matched long-only bench per scheme; Map A/B/joint inv-vol LS compare."
        )
    )
    parser.add_argument("--returns", type=Path, default=RETURNS_CSV)
    parser.add_argument("--regimes", type=Path, default=REGIMES_CSV)
    parser.add_argument(
        "--min-history",
        type=int,
        default=DEFAULT_MIN_HISTORY,
        help="Min past days in-box (and for vol) before live (default 60)",
    )
    parser.add_argument(
        "--no-oracle",
        action="store_true",
        help="Skip oracle look-ahead overlay on charts/summary",
    )
    parser.add_argument(
        "--scheme",
        choices=list(WEIGHT_SCHEMES),
        action="append",
        help="Run only this scheme (repeatable). Default: both.",
    )
    parser.add_argument(
        "--map-compare-only",
        action="store_true",
        help="Only run expanding inv-vol LS across Map A / B / joint",
    )
    parser.add_argument(
        "--no-map-compare",
        action="store_true",
        help="Skip Map A/B/joint inv-vol LS comparison",
    )
    args = parser.parse_args(argv)

    if args.map_compare_only:
        for path, hint in (
            (args.returns, "uv run python -m market_regime returns"),
            (args.regimes, "uv run python -m market_regime regimes"),
        ):
            if not path.exists():
                raise SystemExit(
                    f"Missing {path.relative_to(ROOT).as_posix()}. Run: {hint}"
                )
        returns = pd.read_csv(args.returns, index_col=0, parse_dates=True)
        regimes = pd.read_csv(args.regimes, index_col=0, parse_dates=True)
        run_map_compare(returns, regimes, min_history=args.min_history)
        return

    schemes = tuple(args.scheme) if args.scheme else WEIGHT_SCHEMES
    run(
        returns_path=args.returns,
        regimes_path=args.regimes,
        min_history=args.min_history,
        with_oracle=not args.no_oracle,
        schemes=schemes,
        map_compare=not args.no_map_compare,
    )


if __name__ == "__main__":
    main()
