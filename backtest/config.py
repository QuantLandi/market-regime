"""Paths and constants for the Map B long/short backtest."""

from __future__ import annotations

from pathlib import Path

from market_regime.regimes import (
    CASH_COL,
    REGIMES_CSV,
    RETURNS_CSV,
    TRADING_DAYS_PER_YEAR,
)

ROOT = Path(__file__).resolve().parents[1]
BACKTEST_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BACKTEST_DIR / "results"
FIG_DIR = BACKTEST_DIR / "figures"

SLEEVES = ("spx_tr", "ust_tr", "gold", "copper", "wheat", "crude", "dxy")
MAP_COL = "map_b"
MAP_COLS = ("map_a", "map_b", "map_joint")
MAP_LABELS = {
    "map_a": "Map A (rate signs)",
    "map_b": "Map B (accel/slow)",
    "map_joint": "Map joint",
}
N_SLEEVES = len(SLEEVES)

WEIGHT_SCHEMES = ("equal", "inv_vol")

# Min past days in a Map B box before expanding-window signs are live.
# Also min past days for sleeve vol in the inv_vol scheme.
DEFAULT_MIN_HISTORY = 60

# Plot-only: scale each equity path so compound ann. return = this target
# (all curves on a chart share the same endpoint).
PLOT_TARGET_ANN_RETURN = 0.10

SUMMARY_COMPARE_CSV = RESULTS_DIR / "summary_compare.csv"
COMPARE_FIG_DIR = FIG_DIR / "compare"
MAP_COMPARE_DIR = RESULTS_DIR / "map_compare"
MAP_COMPARE_FIG = FIG_DIR / "compare" / "expanding_inv_vol_ls_map_a_b_joint.png"
MAP_COMPARE_SUMMARY_CSV = MAP_COMPARE_DIR / "summary.csv"


def scheme_results_dir(scheme: str) -> Path:
    return RESULTS_DIR / scheme


def scheme_fig_dir(scheme: str) -> Path:
    return FIG_DIR / scheme


def scheme_paths(scheme: str) -> dict[str, Path]:
    r = scheme_results_dir(scheme)
    f = scheme_fig_dir(scheme)
    return {
        "daily": r / "daily.csv",
        "rebalances": r / "rebalances.csv",
        "summary": r / "summary.csv",
        "equity": f / "equity_curve.png",
        "drawdown": f / "drawdown.png",
    }


__all__ = [
    "BACKTEST_DIR",
    "CASH_COL",
    "COMPARE_FIG_DIR",
    "DEFAULT_MIN_HISTORY",
    "FIG_DIR",
    "MAP_COL",
    "MAP_COLS",
    "MAP_COMPARE_DIR",
    "MAP_COMPARE_FIG",
    "MAP_COMPARE_SUMMARY_CSV",
    "MAP_LABELS",
    "N_SLEEVES",
    "PLOT_TARGET_ANN_RETURN",
    "REGIMES_CSV",
    "RESULTS_DIR",
    "RETURNS_CSV",
    "ROOT",
    "SLEEVES",
    "SUMMARY_COMPARE_CSV",
    "TRADING_DAYS_PER_YEAR",
    "WEIGHT_SCHEMES",
    "scheme_fig_dir",
    "scheme_paths",
    "scheme_results_dir",
]
