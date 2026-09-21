# Map B backtest recap

*Generated 2026-09-21. Research diagnostic — not investment advice.*

## Setup

- **Regime lens:** Map B (growth / inflation accelerating vs slowing)
- **Signals:** long sleeves with positive past mean excess in the current box; short negative
- **Timing:** weights update next session after a GDP/CPI first print; hold until the next print
- **Expanding window:** signs (and vols) use only history with `date < t`
- **Min history:** 60 past in-box days before the book goes live
- **PnL:** total portfolio return `sum(w * r)` (cash not traded)
- **Universe:** SPX, UST, gold, copper, wheat, crude, DXY

### Weight schemes

| Scheme | Long/short | Long-only bench |
|--------|------------|-----------------|
| `equal` | `w_i = sign_i / 7` | `1/7` each |
| `inv_vol` | `w_i ~ sign_i / vol_i`, then `sum(abs(w))=1` | `w_i ~ 1/vol_i`, then `sum(w)=1` |

- **Oracle:** full-sample mean excess signs (and vols) applied as if known at inception — a look-ahead ceiling, not tradable.
- **Aligned stats:** expanding LS live days only (`map_b` labeled and gross > 0).

## Sample

- Rebalances: **208** Map B changes (1994-08-01 → 2026-09-14)
- Live after min-history: **197**
- Latest box: `g_down__pi_up`

## Performance (aligned window unless noted)

| Strategy | Ann. return | Ann. vol | Sharpe | Max DD |
| --- | ---: | ---: | ---: | ---: |
| Oracle LS equal-weight | 6.9% | 8.3% | 0.83 | -13.5% |
| Oracle LS inv-vol | 5.0% | 4.6% | 1.09 | -8.8% |
| Expanding LS equal-weight | 1.4% | 9.6% | 0.15 | -41.6% |
| Expanding LS inv-vol | 1.8% | 5.4% | 0.33 | -23.2% |
| Long-only equal-weight (aligned) | 2.4% | 10.5% | 0.22 | -47.3% |
| Long-only inv-vol (aligned) | 3.0% | 5.1% | 0.59 | -18.6% |

### Full-sample long-only (all calendar days)

| Strategy | Ann. return | Ann. vol | Sharpe | Max DD |
| --- | ---: | ---: | ---: | ---: |
| Long-only equal-weight (full) | 2.8% | 10.3% | 0.27 | -47.3% |
| Long-only inv-vol (full) | 3.4% | 5.0% | 0.66 | -18.6% |

### Book shape (expanding LS, live days)

| Scheme | Avg gross | Avg net |
| --- | ---: | ---: |
| equal | 1.000 | -0.005 |
| inv_vol | 1.000 | 0.072 |

## Takeaways

1. **Oracle >> expanding:** most of the Map B LS edge in the oracle run is look-ahead; expanding-window signs are much weaker.
2. **Inv-vol helps the LS book** vs equal-weight (higher Sharpe, milder drawdowns) but still trails its matched long-only bench.
3. **Long-only inv-vol** is the strongest *expanding* rule in this cut (best Sharpe among non-oracle strategies on the aligned window).
4. **Equal-weight LS** is the weakest expanding variant here — lower return, higher vol, deeper drawdowns than its long-only bench.

## Figures

Equity and drawdown charts are **plot-only** scaled to a **10% compound annualized** target so series on the same chart end at the same point (path / risk comparison). Summary stats above are unscaled.

Signals (expanding signs + regime-change markers): [signals.png](../figures/signals.png) — filled points = live, open = flat (`n_history` below min).

### Per scheme

| Scheme | Equity | Drawdown |
| --- | --- | --- |
| equal | [equity_curve.png](../figures/equal/equity_curve.png) | [drawdown.png](../figures/equal/drawdown.png) |
| inv_vol | [equity_curve.png](../figures/inv_vol/equity_curve.png) | [drawdown.png](../figures/inv_vol/drawdown.png) |

### Pairwise compares

| Comparison | Figure |
| --- | --- |
| Oracle equal vs oracle inv-vol | [oracle_equal_vs_oracle_inv_vol.png](../figures/compare/oracle_equal_vs_oracle_inv_vol.png) |
| Expanding LO inv-vol vs equal | [expanding_lo_inv_vol_vs_lo_equal.png](../figures/compare/expanding_lo_inv_vol_vs_lo_equal.png) |
| Expanding LS inv-vol vs equal | [expanding_ls_inv_vol_vs_ls_equal.png](../figures/compare/expanding_ls_inv_vol_vs_ls_equal.png) |
| Expanding inv-vol LO vs LS | [expanding_inv_vol_lo_vs_ls.png](../figures/compare/expanding_inv_vol_lo_vs_ls.png) |
| Expanding equal LO vs LS | [expanding_equal_lo_vs_ls.png](../figures/compare/expanding_equal_lo_vs_ls.png) |

## Data files

| Path | Contents |
| --- | --- |
| `summary_compare.csv` | All schemes, stacked metrics |
| `equal/` · `inv_vol/` | `daily.csv`, `rebalances.csv`, `summary.csv` |

Regenerate with `uv run python -m backtest`.
