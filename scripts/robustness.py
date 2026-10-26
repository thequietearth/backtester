"""M6: run every momentum variant in the robustness grid and judge them together.

Usage: python scripts/robustness.py   (after scripts/build_data.py; takes several minutes)
Writes data/cache/robustness.parquet (gitignored), which the app's Robustness page reads,
and prints the table and the verdict. The grid and the verdict criteria were fixed before
any results were seen (bt/robustness.py, PLAN.md M6).

Every variant: point-in-time members, equal weight, cash at the T-bill rate, 1999-2025,
ranked from the same month-end universe (members with 12 clean months of prices). Each is
run at 10 bps per side (the headline), and at 0 and 30 bps to find its break-even cost.
"""
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bt.coverage import rankable_by_date  # noqa: E402
from bt.data import load_tbill  # noqa: E402
from bt.report import backtest_window, monthly_decisions, run_strategy, summary, turnover  # noqa: E402
from bt.robustness import DEFAULT, ERAS, break_even_cost, era_lead, lead_stats, variant_grid, verdict  # noqa: E402
from bt.strategies import momentum, spy_buy_and_hold  # noqa: E402

CACHE = ROOT / "data" / "cache"
COSTS = (0, 10, 30)


def label(v) -> str:
    """'top 10% · 12-1 months · monthly': lookback-skip in months, as in the research."""
    return (f"top {round(100 * v.fraction)}% · {v.lookback}-{v.skip} months · "
            f"{'monthly' if v.every == 1 else 'quarterly'}")


def main():
    prices = pd.read_parquet(CACHE / "prices.parquet")
    cal = prices["SPY"].dropna().index
    tbill = load_tbill(ROOT / "data" / "tbill_dtb3.csv")
    universe = rankable_by_date(pd.read_parquet(CACHE / "universe_monthly_pit.parquet"))
    w = backtest_window(cal, 1999, 2025)
    spy = run_strategy("SPY", spy_buy_and_hold(prices, {}, w.rebalance), prices, 10, cal, w, tbill)
    spy_sum = summary(spy, spy)
    rows, started = [], time.time()
    grid = variant_grid()
    for i, v in enumerate(grid.itertuples(index=False), 1):
        weights = momentum(prices, universe, monthly_decisions(cal, w, every=v.every),
                           lookback=v.lookback, skip=v.skip, fraction=v.fraction)
        runs = {c: run_strategy(label(v), weights, prices, c, cal, w, tbill) for c in COSTS}
        main_run = runs[10]
        s = summary(main_run, spy)
        sold = turnover(main_run)
        b = w.boundaries
        per_year = [sold[(sold.index >= b[j]) & (sold.index < b[j + 1])].sum() for j in range(1, len(w.years))]
        cagrs = [summary(runs[c], spy)["CAGR %"] for c in COSTS]
        rows.append({**v._asdict(), "label": label(v), "is_default": v._asdict() == DEFAULT,
                     "cagr": s["CAGR %"], "lead": s["CAGR %"] - spy_sum["CAGR %"], "sharpe": s["Sharpe"],
                     "worst_fall": s["Max drawdown %"], "beat_rate": s["Years beating SPY %"],
                     "turnover": 100 * pd.Series(per_year).mean(),
                     **{f"lead_{a}_{z}": 100 * era_lead(main_run.yearly, spy.yearly, a, z) for a, z in ERAS},
                     **lead_stats(main_run.yearly, spy.yearly),
                     "cagr_0bps": cagrs[0], "cagr_30bps": cagrs[2],
                     "break_even_bps": break_even_cost(COSTS, cagrs, spy_sum["CAGR %"]),
                     "spy_cagr": spy_sum["CAGR %"], "spy_sharpe": spy_sum["Sharpe"]})
        print(f"{i:2}/{len(grid)} {label(v):40} {s['CAGR %']:5.2f}% a year, lead {rows[-1]['lead']:+.2f} pts "
              f"({time.time() - started:.0f}s)", flush=True)
    out = pd.DataFrame(rows)
    out.to_parquet(CACHE / "robustness.parquet", index=False)

    (a1, z1), (a2, z2) = ERAS
    beat = (out.lead > 0).mean()
    beat1, beat2 = (out[f"lead_{a1}_{z1}"] > 0).mean(), (out[f"lead_{a2}_{z2}"] > 0).mean()
    print(f"\nSPY: {spy_sum['CAGR %']:.2f}% a year, Sharpe {spy_sum['Sharpe']:.2f}")
    print(f"variants beating SPY: {beat:.0%} over 1999-2025, {beat1:.0%} in {a1}-{z1}, {beat2:.0%} in {a2}-{z2}")
    print(f"median lead {out.lead.median():+.2f} pts a year (range {out.lead.min():+.2f} to {out.lead.max():+.2f}); "
          f"median break-even cost {out.break_even_bps.median():.0f} bps; "
          f"variants with t >= 2: {(out.t_stat >= 2).sum()} of {len(out)}")
    print(f"verdict: {verdict(beat, beat1, beat2)}")


if __name__ == "__main__":
    main()
