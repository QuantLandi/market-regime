"""Release-date heatmap: 4 sign columns (g/π × level/Δ).

One row per GDP or CPI first-print release; cell color = up/accel (orange)
vs down/slow (blue). Today's row outlined.

  uv run python -m market_regime.plot_regime_timeline
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
FIG_DIR = ROOT / "figures"
REGIMES_CSV = DATA_DIR / "regimes.csv"
RELEASES_CSV = DATA_DIR / "releases_raw.csv"

# 0 = down/slow (blue), 1 = up/accel (orange)
CMAP = ListedColormap(["#0072B2", "#E69F00"])
COL_LABELS = [
    "g level (↑/↓)",
    "g change (accel/slow)",
    "π level (↑/↓)",
    "π change (accel/slow)",
]
SIGN_COLS = ["g_sign", "g_delta_sign", "pi_sign", "pi_delta_sign"]


def _state_after_release(
    regimes: pd.DataFrame, release_date: pd.Timestamp
) -> pd.Series | None:
    """First labeled session strictly after the release (print applies next day)."""
    idx = regimes.index[regimes.index > release_date.normalize()]
    if len(idx) == 0:
        return None
    row = regimes.loc[idx[0], SIGN_COLS]
    if row.isna().any():
        return None
    return row


def _build_release_panel() -> pd.DataFrame:
    regimes = pd.read_csv(REGIMES_CSV, index_col=0, parse_dates=True)
    regimes.index = pd.DatetimeIndex(regimes.index).normalize()
    releases = pd.read_csv(RELEASES_CSV, parse_dates=["release_date"])
    releases = releases.sort_values(["release_date", "series"])

    rows: list[dict] = []
    for _, rel in releases.iterrows():
        st = _state_after_release(regimes, rel["release_date"])
        if st is None:
            continue
        rows.append(
            {
                "release_date": pd.Timestamp(rel["release_date"]).normalize(),
                "series": "GDP" if rel["series"] == "gdp_yoy" else "CPI",
                "g_sign": str(st["g_sign"]),
                "g_delta_sign": str(st["g_delta_sign"]),
                "pi_sign": str(st["pi_sign"]),
                "pi_delta_sign": str(st["pi_delta_sign"]),
            }
        )
    out = pd.DataFrame(rows)
    # Chronological: oldest → newest (left → right on the chart)
    return out.sort_values(["release_date", "series"], ascending=True).reset_index(
        drop=True
    )


def _to_code(panel: pd.DataFrame) -> np.ndarray:
    """Shape (n_releases, 4); 1 = up/accel, 0 = down/slow."""
    mat = np.zeros((len(panel), 4), dtype=float)
    mat[:, 0] = (panel["g_sign"] == "up").astype(float)
    mat[:, 1] = (panel["g_delta_sign"] == "up").astype(float)
    mat[:, 2] = (panel["pi_sign"] == "up").astype(float)
    mat[:, 3] = (panel["pi_delta_sign"] == "up").astype(float)
    return mat


def plot_release_sign_heatmap(
    panel: pd.DataFrame,
    out: Path,
    *,
    title: str,
) -> None:
    # Display as 4 rows × n releases (time on x)
    mat = _to_code(panel).T
    n = len(panel)
    fig_w = min(28.0, max(12.0, 0.22 * n + 4.0))
    # Row pitch ~1.5× the previous compact height
    fig_h = 5.2 * 1.5
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    # Fixed ~1.85" for y labels so wide figures don't get a huge left void
    left = min(0.22, 1.85 / fig_w)
    fig.subplots_adjust(left=left, right=0.96, top=0.88, bottom=0.30)
    ax.imshow(mat, aspect="auto", cmap=CMAP, vmin=0, vmax=1, interpolation="nearest")

    ax.set_yticks(range(4))
    ax.set_yticklabels(COL_LABELS, fontsize=9)
    ax.tick_params(axis="y", pad=4)

    step = 1 if n <= 40 else max(1, n // 25)
    xticks = list(range(0, n, step))
    if n - 1 not in xticks:
        xticks.append(n - 1)
    xticks = sorted(set(xticks))
    ax.set_xticks(xticks)
    ax.set_xticklabels(
        [
            f"{panel.loc[i, 'release_date'].strftime('%Y-%m-%d')} {panel.loc[i, 'series']}"
            for i in xticks
        ],
        fontsize=8,
        rotation=45,
        ha="right",
        rotation_mode="anchor",
    )

    # Soft vertical lines where the four-way state flips vs previous release
    codes = _to_code(panel)
    for j in range(1, n):
        if not np.array_equal(codes[j], codes[j - 1]):
            ax.axvline(
                j - 0.5,
                color="#666666",
                lw=0.7,
                alpha=0.85,
                zorder=3,
            )

    # Outline latest release (rightmost column)
    ax.add_patch(
        plt.Rectangle(
            (n - 1 - 0.5, -0.5),
            1,
            4,
            fill=False,
            edgecolor="#000000",
            linewidth=2.0,
            zorder=5,
        )
    )

    ax.set_title(title, fontsize=11, pad=10)
    ax.set_xlabel("")

    legend = [
        mpatches.Patch(facecolor="#E69F00", edgecolor="#333333", label="up / accel"),
        mpatches.Patch(facecolor="#0072B2", edgecolor="#333333", label="down / slow"),
    ]
    # Figure-level legend in the reserved bottom margin (below tick labels)
    fig.legend(
        handles=legend,
        loc="lower center",
        bbox_to_anchor=(0.55, 0.07),
        ncol=2,
        fontsize=10,
        frameon=False,
    )
    ax.text(
        0.01,
        0.97,
        "© Alexandre Landi, 2026",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8,
        color="#333333",
        bbox={
            "boxstyle": "round,pad=0.25",
            "facecolor": "white",
            "edgecolor": "none",
            "alpha": 0.85,
        },
        zorder=6,
    )

    fig.savefig(out, dpi=160)
    plt.close(fig)


def main() -> None:
    for p in (REGIMES_CSV, RELEASES_CSV):
        if not p.exists():
            raise SystemExit(
                f"Missing {p.relative_to(ROOT).as_posix()}. "
                "Run regimes / download-releases first."
            )
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    panel = _build_release_panel()
    if panel.empty:
        raise SystemExit("No release rows with joint labels.")

    latest = panel.iloc[-1]["release_date"]
    windows = (
        (None, "heatmap_release_signs.png", "full sample"),
        (10, "heatmap_release_signs_10y.png", "last 10 years"),
        (5, "heatmap_release_signs_5y.png", "last 5 years"),
        (3, "heatmap_release_signs_3y.png", "last 3 years"),
    )
    for years, fname, label in windows:
        if years is None:
            sub = panel
        else:
            sub = panel.loc[
                panel["release_date"] >= latest - pd.DateOffset(years=years)
            ].reset_index(drop=True)
        out = FIG_DIR / fname
        title = (
            f"Growth and inflation after each GDP / CPI release — {label}\n"
            "Orange = up or accelerating · Blue = down or slowing · "
            "Gray line = the picture changed · Black outline = latest release"
        )
        plot_release_sign_heatmap(sub, out, title=title)
        start = sub.iloc[0]["release_date"].date()
        end = sub.iloc[-1]["release_date"].date()
        print(
            f"Wrote {out.relative_to(ROOT).as_posix()} "
            f"({len(sub)} cols; {start} -> {end})",
            flush=True,
        )


if __name__ == "__main__":
    main()
