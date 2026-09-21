"""Write a markdown recap of Map B backtest results."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from backtest.config import RESULTS_DIR, SUMMARY_COMPARE_CSV

RECAP_MD = RESULTS_DIR / "recap.md"

# Display order for the main performance table.
_STRATEGY_ORDER = [
    ("equal", "oracle_ls_equal", "Oracle LS equal-weight"),
    ("inv_vol", "oracle_ls_inv_vol", "Oracle LS inv-vol"),
    ("equal", "expanding_ls_equal", "Expanding LS equal-weight"),
    ("inv_vol", "expanding_ls_inv_vol", "Expanding LS inv-vol"),
    ("equal", "long_only_equal_aligned", "Long-only equal-weight (aligned)"),
    ("inv_vol", "long_only_inv_vol_aligned", "Long-only inv-vol (aligned)"),
]

_METRICS = (
    ("ann_total_mean", "Ann. return", True),
    ("ann_total_vol", "Ann. vol", True),
    ("sharpe_total", "Sharpe", False),
    ("max_drawdown", "Max DD", True),
)


def _pct(x: float, digits: int = 1) -> str:
    return f"{100 * x:.{digits}f}%"


def _num(x: float, digits: int = 2) -> str:
    return f"{x:.{digits}f}"


def _metric_map(summary: pd.DataFrame) -> dict[tuple[str, str], dict[str, float]]:
    out: dict[tuple[str, str], dict[str, float]] = {}
    for _, row in summary.iterrows():
        key = (str(row["scheme"]), str(row["strategy"]))
        out.setdefault(key, {})[str(row["metric"])] = float(row["value"])
    return out


def _fmt_cell(metric: str, value: float, *, as_pct: bool) -> str:
    if metric == "n_days":
        return f"{int(value):,}"
    if metric == "sharpe_total":
        return _num(value, 2)
    if as_pct:
        return _pct(value, 1)
    return _num(value, 2)


def write_recap(
    summary: pd.DataFrame,
    *,
    min_history: int,
    rebalances: pd.DataFrame | None = None,
    path: Path = RECAP_MD,
) -> Path:
    """Build ``backtest/results/recap.md`` from the combined summary table."""
    path.parent.mkdir(parents=True, exist_ok=True)
    metrics = _metric_map(summary)

    lines: list[str] = [
        "# Map B backtest recap",
        "",
        f"*Generated {date.today().isoformat()}. Research diagnostic — not investment advice.*",
        "",
        "## Setup",
        "",
        "- **Regime lens:** Map B (growth / inflation accelerating vs slowing)",
        "- **Signals:** long sleeves with positive past mean excess in the current box; "
        "short negative",
        "- **Timing:** weights update next session after a GDP/CPI first print; hold until "
        "the next print",
        "- **Expanding window:** signs (and vols) use only history with `date < t`",
        f"- **Min history:** {min_history} past in-box days before the book goes live",
        "- **PnL:** total portfolio return `sum(w * r)` (cash not traded)",
        "- **Universe:** SPX, UST, gold, copper, wheat, crude, DXY",
        "",
        "### Weight schemes",
        "",
        "| Scheme | Long/short | Long-only bench |",
        "|--------|------------|-----------------|",
        "| `equal` | `w_i = sign_i / 7` | `1/7` each |",
        "| `inv_vol` | `w_i ~ sign_i / vol_i`, then `sum(abs(w))=1` | `w_i ~ 1/vol_i`, then `sum(w)=1` |",
        "",
        "- **Oracle:** full-sample mean excess signs (and vols) applied as if known at "
        "inception — a look-ahead ceiling, not tradable.",
        "- **Aligned stats:** expanding LS live days only (`map_b` labeled and gross > 0).",
        "",
    ]

    if rebalances is not None and not rebalances.empty:
        n_reb = len(rebalances)
        n_live = int(rebalances["live"].sum())
        start = pd.Timestamp(rebalances.index.min()).date()
        end = pd.Timestamp(rebalances.index.max()).date()
        last = rebalances.iloc[-1]
        lines.extend(
            [
                "## Sample",
                "",
                f"- Rebalances: **{n_reb}** Map B changes ({start} → {end})",
                f"- Live after min-history: **{n_live}**",
                f"- Latest box: `{last['box']}`",
                "",
            ]
        )

    # Performance table
    metric_labels = [label for _, label, _ in _METRICS]
    header = "| Strategy | " + " | ".join(metric_labels) + " |"
    sep = "| --- | " + " | ".join("---:" for _ in _METRICS) + " |"
    lines.extend(
        [
            "## Performance (aligned window unless noted)",
            "",
            header,
            sep,
        ]
    )
    for scheme, strategy, label in _STRATEGY_ORDER:
        vals = metrics.get((scheme, strategy), {})
        if not vals:
            continue
        cells = [
            _fmt_cell(m, vals[m], as_pct=as_pct)
            for m, _, as_pct in _METRICS
            if m in vals
        ]
        if len(cells) != len(_METRICS):
            continue
        lines.append(f"| {label} | " + " | ".join(cells) + " |")

    # Extra rows: full-sample long-only
    lines.extend(["", "### Full-sample long-only (all calendar days)", ""])
    lines.append(header)
    lines.append(sep)
    for scheme, strategy, label in (
        ("equal", "long_only_equal_full", "Long-only equal-weight (full)"),
        ("inv_vol", "long_only_inv_vol_full", "Long-only inv-vol (full)"),
    ):
        vals = metrics.get((scheme, strategy), {})
        if not vals:
            continue
        cells = [
            _fmt_cell(m, vals[m], as_pct=as_pct)
            for m, _, as_pct in _METRICS
            if m in vals
        ]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")

    # Gross / net
    lines.extend(
        [
            "",
            "### Book shape (expanding LS, live days)",
            "",
            "| Scheme | Avg gross | Avg net |",
            "| --- | ---: | ---: |",
        ]
    )
    for scheme, strategy, label in (
        ("equal", "expanding_ls_equal", "equal"),
        ("inv_vol", "expanding_ls_inv_vol", "inv_vol"),
    ):
        vals = metrics.get((scheme, strategy), {})
        if "avg_gross" in vals and "avg_net" in vals:
            lines.append(
                f"| {label} | {_num(vals['avg_gross'], 3)} | {_num(vals['avg_net'], 3)} |"
            )

    # Takeaways
    lines.extend(
        [
            "",
            "## Takeaways",
            "",
            "1. **Oracle >> expanding:** most of the Map B LS edge in the oracle run is "
            "look-ahead; expanding-window signs are much weaker.",
            "2. **Inv-vol helps the LS book** vs equal-weight (higher Sharpe, milder drawdowns) "
            "but still trails its matched long-only bench.",
            "3. **Long-only inv-vol** is the strongest *expanding* rule in this cut "
            "(best Sharpe among non-oracle strategies on the aligned window).",
            "4. **Equal-weight LS** is the weakest expanding variant here — lower return, "
            "higher vol, deeper drawdowns than its long-only bench.",
            "",
            "## Figures",
            "",
            "Equity and drawdown charts are **plot-only** scaled to a **10% compound "
            "annualized** target so series on the same chart end at the same point "
            "(path / risk comparison). Summary stats above are unscaled.",
            "",
            "### Per scheme",
            "",
            "| Scheme | Equity | Drawdown |",
            "| --- | --- | --- |",
            "| equal | [equity_curve.png](../figures/equal/equity_curve.png) | "
            "[drawdown.png](../figures/equal/drawdown.png) |",
            "| inv_vol | [equity_curve.png](../figures/inv_vol/equity_curve.png) | "
            "[drawdown.png](../figures/inv_vol/drawdown.png) |",
            "",
            "### Pairwise compares",
            "",
            "| Comparison | Figure |",
            "| --- | --- |",
            "| Oracle equal vs oracle inv-vol | "
            "[oracle_equal_vs_oracle_inv_vol.png](../figures/compare/oracle_equal_vs_oracle_inv_vol.png) |",
            "| Expanding LO inv-vol vs equal | "
            "[expanding_lo_inv_vol_vs_lo_equal.png](../figures/compare/expanding_lo_inv_vol_vs_lo_equal.png) |",
            "| Expanding LS inv-vol vs equal | "
            "[expanding_ls_inv_vol_vs_ls_equal.png](../figures/compare/expanding_ls_inv_vol_vs_ls_equal.png) |",
            "| Expanding inv-vol LO vs LS | "
            "[expanding_inv_vol_lo_vs_ls.png](../figures/compare/expanding_inv_vol_lo_vs_ls.png) |",
            "| Expanding equal LO vs LS | "
            "[expanding_equal_lo_vs_ls.png](../figures/compare/expanding_equal_lo_vs_ls.png) |",
            "",
            "## Data files",
            "",
            "| Path | Contents |",
            "| --- | --- |",
            "| `summary_compare.csv` | All schemes, stacked metrics |",
            "| `equal/` · `inv_vol/` | `daily.csv`, `rebalances.csv`, `summary.csv` |",
            "",
            "Regenerate with `uv run python -m backtest`.",
            "",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_recap_from_csv(
    *,
    summary_path: Path = SUMMARY_COMPARE_CSV,
    rebalances_path: Path | None = None,
    min_history: int,
    path: Path = RECAP_MD,
) -> Path:
    if not summary_path.exists():
        raise SystemExit(f"Missing {summary_path}")
    summary = pd.read_csv(summary_path)
    reb = None
    if rebalances_path and rebalances_path.exists():
        reb = pd.read_csv(rebalances_path, index_col=0, parse_dates=True)
    return write_recap(summary, min_history=min_history, rebalances=reb, path=path)
