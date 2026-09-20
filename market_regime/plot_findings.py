"""Colorblind-friendly regime heatmaps → figures/*.png.

All panels use daily excess vs cash (r − cash).
Return and Sharpe: blue (low/negative) ↔ orange (high/positive).
Volatility: sequential blue → light → orange (always ≥ 0; no red–green).

  uv run python -m market_regime.plot_findings
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, Normalize, TwoSlopeNorm

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
FIG_DIR = ROOT / "figures"
MEANS_CSV = DATA_DIR / "regime_means.csv"
VOLS_CSV = DATA_DIR / "regime_vols.csv"
RET_VOL_CSV = DATA_DIR / "regime_ret_vol.csv"

CB_DIVERGING = LinearSegmentedColormap.from_list(
    "cb_blue_orange",
    ["#0072B2", "#56B4E9", "#F0F0F0", "#E69F00", "#D55E00"],
)
# Sequential for vol (non-negative): light → orange intensity via blue→orange
CB_SEQUENTIAL = LinearSegmentedColormap.from_list(
    "cb_vol",
    ["#F7FBFF", "#9ECAE1", "#4292C6", "#E69F00", "#D55E00"],
)

SLEEVES = ["spx_tr", "ust_tr", "gold", "copper", "crude", "wheat", "dxy"]
SLEEVE_LABELS = ["SPX", "UST", "Gold", "Copper", "Crude", "Wheat", "DXY"]

ARROW = {"up": "↑", "down": "↓"}
MOTION = {"up": "accel", "down": "slow"}

TODAY_JOINT = "g_up_down__pi_up_up"
TODAY_MAP_A = "g_up__pi_up"
TODAY_MAP_B = "g_down__pi_up"


def _label_ab(box: str) -> str:
    parts = box.split("__")
    g = parts[0].removeprefix("g_")
    p = parts[1].removeprefix("pi_")
    return f"g{ARROW[g]} π{ARROW[p]}"


def _label_joint(box: str) -> str:
    m = box.split("__")
    g = m[0].removeprefix("g_").split("_")
    p = m[1].removeprefix("pi_").split("_")
    return f"g{ARROW[g[0]]}·{MOTION[g[1]]} × π{ARROW[p[0]]}·{MOTION[p[1]]}"


def _heatmap(
    mat: pd.DataFrame,
    *,
    title: str,
    out: Path,
    cbar_label: str,
    row_highlight: str | None = None,
    figsize: tuple[float, float] = (10, 4),
    diverging: bool = True,
    fmt: str = ".1f",
    value_scale: float = 1.0,
) -> None:
    fig, ax = plt.subplots(figsize=figsize, layout="constrained")
    data = mat.to_numpy(dtype=float) * value_scale
    finite = data[np.isfinite(data)]
    if finite.size == 0:
        plt.close(fig)
        return

    if diverging:
        vmax = float(np.nanmax(np.abs(finite)))
        if vmax == 0:
            vmax = 1.0
        norm: Normalize = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)
        cmap = CB_DIVERGING
        text_ref = vmax
    else:
        vmin = 0.0
        vmax = float(np.nanmax(finite))
        if vmax == 0:
            vmax = 1.0
        norm = Normalize(vmin=vmin, vmax=vmax)
        cmap = CB_SEQUENTIAL
        text_ref = vmax

    im = ax.imshow(data, aspect="auto", cmap=cmap, norm=norm)

    ax.set_xticks(range(len(mat.columns)))
    ax.set_xticklabels(list(mat.columns), fontsize=9)
    ax.set_yticks(range(len(mat.index)))
    ylabels = list(mat.index)
    ax.set_yticklabels(ylabels, fontsize=9)

    if row_highlight is not None and row_highlight in ylabels:
        i = ylabels.index(row_highlight)
        ax.add_patch(
            plt.Rectangle(
                (-0.5, i - 0.5),
                len(mat.columns),
                1,
                fill=False,
                edgecolor="#000000",
                linewidth=2,
            )
        )

    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data[i, j]
            if not np.isfinite(v):
                continue
            if diverging:
                light = abs(v) < 0.45 * text_ref
            else:
                light = v < 0.55 * text_ref
            ax.text(
                j,
                i,
                format(v, fmt),
                ha="center",
                va="center",
                fontsize=8,
                color="#111111" if light else "#FFFFFF",
            )

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(cbar_label, fontsize=9)
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("Asset")
    ax.set_ylabel("Regime")
    fig.savefig(out, dpi=160)
    plt.close(fig)


def _day_bars(counts: pd.Series, *, title: str, out: Path) -> None:
    n = len(counts)
    fig_h = max(3.2, 0.35 * n + 1.2)
    fig, ax = plt.subplots(figsize=(8.5, fig_h), layout="constrained")
    y = np.arange(n)
    vals = counts.to_numpy(dtype=float)
    ax.barh(y, vals, color="#0072B2", height=0.7)
    ax.set_yticks(y)
    ax.set_yticklabels(list(counts.index), fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Trading days")
    ax.set_title(title, fontsize=11)
    vmax = float(vals.max()) if len(vals) else 1.0
    ax.set_xlim(0, vmax * 1.25)
    for i, v in enumerate(vals):
        label = f"{int(v):,}"
        # Keep labels inside the axes: inside long bars, just outside short ones
        if v >= 0.22 * vmax:
            ax.text(
                v - 0.012 * vmax,
                i,
                label,
                va="center",
                ha="right",
                fontsize=8,
                color="#FFFFFF",
                clip_on=True,
            )
        else:
            ax.text(
                v + 0.02 * vmax,
                i,
                label,
                va="center",
                ha="left",
                fontsize=8,
                color="#111111",
                clip_on=True,
            )
    fig.savefig(out, dpi=160, pad_inches=0.15)
    plt.close(fig)


def build_matrix(
    stats: pd.DataFrame, map_name: str, label_fn
) -> tuple[pd.DataFrame, pd.Series]:
    sub = stats.loc[stats["map"] == map_name].copy()
    sub["label"] = sub["box"].map(label_fn)
    sub = sub.sort_values("n_days", ascending=False)
    mat = sub.set_index("label")[SLEEVES]
    mat.columns = SLEEVE_LABELS
    counts = sub.set_index("label")["n_days"]
    return mat, counts


def _plot_metric(
    stats: pd.DataFrame,
    *,
    stem: str,
    title_metric: str,
    cbar_label: str,
    diverging: bool,
    fmt: str,
    value_scale: float,
) -> None:
    specs = (
        ("map_joint", _label_joint, TODAY_JOINT, (11, 6.5), "joint"),
        ("map_b", _label_ab, TODAY_MAP_B, (10, 3.5), "map_b"),
        ("map_a", _label_ab, TODAY_MAP_A, (10, 3.5), "map_a"),
    )
    titles = {
        "map_joint": "Joint (level × change)",
        "map_b": "Accelerating vs slowing",
        "map_a": "Rate signs only",
    }
    for map_name, label_fn, today_box, figsize, file_tag in specs:
        mat, _ = build_matrix(stats, map_name, label_fn)
        _heatmap(
            mat,
            title=f"{titles[map_name]} — {title_metric}",
            out=FIG_DIR / f"heatmap_{file_tag}_{stem}.png",
            cbar_label=cbar_label,
            row_highlight=label_fn(today_box),
            figsize=figsize,
            diverging=diverging,
            fmt=fmt,
            value_scale=value_scale,
        )


def main() -> None:
    missing = [p for p in (MEANS_CSV, VOLS_CSV, RET_VOL_CSV) if not p.exists()]
    if missing:
        raise SystemExit(
            "Missing "
            + ", ".join(p.relative_to(ROOT).as_posix() for p in missing)
            + ". Run: uv run python -m market_regime regimes"
        )
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    means = pd.read_csv(MEANS_CSV)
    vols = pd.read_csv(VOLS_CSV)
    ret_vols = pd.read_csv(RET_VOL_CSV)

    # Day-count bars once (from means file)
    for map_name, label_fn, file_tag, title in (
        ("map_joint", _label_joint, "joint", "Joint view — days in each regime"),
        ("map_b", _label_ab, "map_b", "Accelerating vs slowing — days"),
        ("map_a", _label_ab, "map_a", "Rate signs only — days"),
    ):
        _, counts = build_matrix(means, map_name, label_fn)
        _day_bars(counts, title=title, out=FIG_DIR / f"days_{file_tag}.png")

    # Excess returns (%): keep legacy filenames heatmap_{tag}.png as return heatmaps
    _plot_metric(
        means,
        stem="return",
        title_metric="annualized mean excess vs cash (%)",
        cbar_label="Mean(r − cash) × 252 (%)",
        diverging=True,
        fmt=".1f",
        value_scale=100.0,
    )
    # Also write legacy names used in the client note
    for tag in ("joint", "map_b", "map_a"):
        src = FIG_DIR / f"heatmap_{tag}_return.png"
        dst = FIG_DIR / f"heatmap_{tag}.png"
        dst.write_bytes(src.read_bytes())

    _plot_metric(
        vols,
        stem="vol",
        title_metric="annualized vol of excess vs cash (%)",
        cbar_label="sd(r − cash) × √252 (%)",
        diverging=False,
        fmt=".1f",
        value_scale=100.0,
    )
    _plot_metric(
        ret_vols,
        stem="ret_vol",
        title_metric="Sharpe on daily excess vs cash",
        cbar_label="Mean(r − cash) / sd(r − cash) × √252",
        diverging=True,
        fmt=".2f",
        value_scale=1.0,
    )

    print(f"Wrote figures under {FIG_DIR.relative_to(ROOT).as_posix()}/", flush=True)
    for p in sorted(FIG_DIR.glob("*.png")):
        print(f"  {p.name}", flush=True)


if __name__ == "__main__":
    main()
