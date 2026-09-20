"""One-picture combo for sharing: 3-year release timeline + joint Sharpe heatmap.

Top: growth/inflation signs after each GDP / CPI first print (last 3 years).
Bottom: Sharpe of daily excess vs cash by joint regime, today's row outlined.

  uv run python -m market_regime.plot_combo
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm

from market_regime.plot_findings import (
    CB_DIVERGING,
    RET_VOL_CSV,
    TODAY_JOINT,
    _label_joint,
    build_matrix,
)
from market_regime.plot_regime_timeline import (
    CMAP,
    COL_LABELS,
    _build_release_panel,
    _to_code,
)

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "figures"
OUT = FIG_DIR / "combo_timeline_sharpe.png"

TIMELINE_YEARS = 3


def _draw_timeline(ax: plt.Axes, panel: pd.DataFrame) -> None:
    mat = _to_code(panel).T
    n = len(panel)
    ax.imshow(mat, aspect="auto", cmap=CMAP, vmin=0, vmax=1, interpolation="nearest")

    ax.set_yticks(range(4))
    ax.set_yticklabels(COL_LABELS, fontsize=9)

    step = 1 if n <= 40 else max(1, n // 25)
    xticks = sorted(set(list(range(0, n, step)) + [n - 1]))
    ax.set_xticks(xticks)
    ax.set_xticklabels(
        [
            f"{panel.loc[i, 'release_date'].strftime('%Y-%m-%d')} {panel.loc[i, 'series']}"
            for i in xticks
        ],
        fontsize=7.5,
        rotation=45,
        ha="right",
        rotation_mode="anchor",
    )

    codes = _to_code(panel)
    for j in range(1, n):
        if not np.array_equal(codes[j], codes[j - 1]):
            ax.axvline(j - 0.5, color="#666666", lw=0.7, alpha=0.85, zorder=3)

    ax.add_patch(
        plt.Rectangle(
            (n - 1 - 0.5, -0.5), 1, 4,
            fill=False, edgecolor="#000000", linewidth=2.0, zorder=5,
        )
    )

    ax.set_title(
        f"How the regime evolved — GDP / CPI first prints, last {TIMELINE_YEARS} years\n"
        "Orange = up or accelerating · Blue = down or slowing · "
        "Gray line = picture changed · Black outline = latest release",
        fontsize=10.5,
    )


def _draw_sharpe(ax: plt.Axes, mat: pd.DataFrame, row_highlight: str) -> None:
    data = mat.to_numpy(dtype=float)
    vmax = float(np.nanmax(np.abs(data[np.isfinite(data)])))
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)
    ax.imshow(data, aspect="auto", cmap=CB_DIVERGING, norm=norm)

    ax.set_xticks(range(len(mat.columns)))
    ax.set_xticklabels(list(mat.columns), fontsize=9)
    ylabels = list(mat.index)
    ax.set_yticks(range(len(ylabels)))
    ax.set_yticklabels(ylabels, fontsize=9)

    if row_highlight in ylabels:
        i = ylabels.index(row_highlight)
        ax.add_patch(
            plt.Rectangle(
                (-0.5, i - 0.5), len(mat.columns), 1,
                fill=False, edgecolor="#000000", linewidth=2,
            )
        )
        ax.annotate(
            "today",
            xy=(len(mat.columns) - 0.5, i),
            xytext=(6, 0),
            textcoords="offset points",
            va="center",
            ha="left",
            fontsize=9,
            fontweight="bold",
        )

    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data[i, j]
            if not np.isfinite(v):
                continue
            light = abs(v) < 0.45 * vmax
            ax.text(
                j, i, format(v, ".2f"),
                ha="center", va="center", fontsize=8,
                color="#111111" if light else "#FFFFFF",
            )

    ax.set_title(
        "What each regime has meant — Sharpe of daily excess returns vs cash, 1994–2026\n"
        "Orange = positive Sharpe · Blue = negative · Rows sorted by days in regime · "
        "Black outline = today's regime",
        fontsize=10.5,
    )


def main() -> None:
    for p in (RET_VOL_CSV,):
        if not p.exists():
            raise SystemExit(
                f"Missing {p.relative_to(ROOT).as_posix()}. Run: uv run python -m market_regime regimes"
            )
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    panel = _build_release_panel()
    latest = panel.iloc[-1]["release_date"]
    panel = panel.loc[
        panel["release_date"] >= latest - pd.DateOffset(years=TIMELINE_YEARS)
    ].reset_index(drop=True)

    ret_vols = pd.read_csv(RET_VOL_CSV)
    mat, _ = build_matrix(ret_vols, "map_joint", _label_joint)

    fig = plt.figure(figsize=(12.0, 12.5))
    gs = fig.add_gridspec(
        2, 1, height_ratios=[1.0, 1.85],
        left=0.16, right=0.93, top=0.90, bottom=0.06, hspace=0.42,
    )
    ax_top = fig.add_subplot(gs[0])
    ax_bot = fig.add_subplot(gs[1])

    _draw_timeline(ax_top, panel)
    _draw_sharpe(ax_bot, mat, _label_joint(TODAY_JOINT))

    fig.suptitle(
        "Growth–inflation regimes: where we are, and what it has meant for assets",
        fontsize=15, fontweight="bold", y=0.978,
    )
    fig.text(
        0.5, 0.952,
        f"g = real GDP YoY · π = headline CPI YoY · first prints only · as of {latest.strftime('%d %b %Y')}",
        ha="center", fontsize=10, color="#555555",
    )
    fig.text(
        0.5, 0.015,
        "© Alexandre Landi · educational, not investment advice · "
        "Data: Bloomberg (assets), ALFRED first-print vintages (macro)",
        ha="center", fontsize=8.5, color="#666666",
    )

    fig.savefig(OUT, dpi=160)
    plt.close(fig)
    print(f"Wrote {OUT.relative_to(ROOT).as_posix()}", flush=True)


if __name__ == "__main__":
    main()
