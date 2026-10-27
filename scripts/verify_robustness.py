"""Independent checks that the M6 robustness run (scripts/robustness.py) is correct.

Usage: python scripts/verify_robustness.py   (after scripts/robustness.py; about 10 minutes)

1. Returns recomputed without the engine: buy and hold between trades, no costs, cash at
   0%. Periods may differ only where one of the engine's two deliberate rules applied: it
   kept a stock that had stopped trading by the trade day (it can't be sold without a
   price), or it sold a holding after more than 10 days without a price, where the simple
   calculation follows the price if it comes back (after an excluded fake day, or as junk
   after a takeover).
2. Rankings recomputed from the price table on sample dates: the same stocks must be held.
3. Structure: holding counts, quarterly trade months, identical reruns.
4. Stored results against fresh calculations: leads, era leads, t-statistic, break-even cost.
5. Placebo at zero cost: random 48-stock portfolios from the same universe, against the
   variants and against owning every member in equal amounts. If the pipeline had a hidden
   bias (survivorship, lookahead), random picks would show it.
Each check prints PASS or FAIL.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bt.coverage import rankable_by_date  # noqa: E402
from bt.data import load_tbill  # noqa: E402
from bt.engine import run_backtest  # noqa: E402
from bt.report import backtest_window, monthly_decisions, run_strategy, summary  # noqa: E402
from bt.robustness import break_even_cost, era_lead, lead_stats  # noqa: E402
from bt.strategies import _weights, equal_weight_all, momentum, spy_buy_and_hold  # noqa: E402

CACHE = ROOT / "data" / "cache"


def verdict(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def main():
    p = pd.read_parquet(CACHE / "prices.parquet")
    cal = p["SPY"].dropna().index
    tb = load_tbill(ROOT / "data" / "tbill_dtb3.csv")
    u = rankable_by_date(pd.read_parquet(CACHE / "universe_monthly_pit.parquet"))
    w = backtest_window(cal, 1999, 2025)
    stored = pd.read_parquet(CACHE / "robustness.parquet")
    spy = run_strategy("SPY", spy_buy_and_hold(p, {}, w.rebalance), p, 10, cal, w, tb)
    px = p.reindex(cal).ffill()

    print("1. Returns recomputed without the engine (0 bps, cash at 0%)")
    for f, lb, sk, ev in ((0.10, 12, 1, 1), (0.05, 6, 0, 3), (0.20, 9, 1, 1)):
        wts = momentum(p, u, monthly_decisions(cal, w, every=ev), lookback=lb, skip=sk, fraction=f)
        res = run_backtest(wts, p, cost_bps=0, calendar=cal)
        eq = res.equity.loc[:w.end]
        trade_days = [cal[cal > d][0] for d in wts.index]
        kept = set(res.trades[res.trades.action == "kept"].date)
        exits = res.trades[res.trades.action == "exit"].date
        differ = unexplained = 0
        for (d, row), start, end in zip(wts.iterrows(), trade_days, trade_days[1:] + [w.end]):
            row = row[row > 0]
            simple = sum(row[c] * (px.at[end, c] / p.at[start, c] - 1) for c in row.index if pd.notna(p.at[start, c]))
            if abs((eq[end] / eq[start] - 1) - simple) > 1e-4:
                differ += 1
                unexplained += start not in kept and not ((exits > start) & (exits <= end)).any()
        print(f"   top {f:.0%} {lb}-{sk} every {ev}: {len(trade_days)} periods, {differ} differ, all where the engine "
              f"kept a stock that had stopped trading or sold one whose data ended: {verdict(unexplained == 0)}")

    print("2. Rankings recomputed from the price table")
    months = cal.to_series().groupby(cal.to_period("M")).max()
    matches = total = 0
    for f, lb, sk, ev in ((0.10, 12, 1, 1), (0.05, 6, 0, 1), (0.20, 9, 1, 3)):
        dates = monthly_decisions(cal, w, every=ev)
        wts = momentum(p, u, dates, lookback=lb, skip=sk, fraction=f)
        for d in (dates[5], dates[len(dates) // 2], dates[-3]):
            start, end = months[d.to_period("M") - lb], months[d.to_period("M") - sk]
            codes = [c for c in u[d] if c in p.columns]
            ret = (p.loc[:end, codes].ffill().iloc[-1] / p.loc[start, codes] - 1).dropna()
            expected = set(sorted(ret.index, key=lambda c: (-ret[c], c))[:math.ceil(round(f * len(ret), 9))])
            matches += expected == set(wts.loc[d][wts.loc[d] > 0].index)
            total += 1
    print(f"   {matches} of {total} sample dates hold exactly the recomputed stocks: {verdict(matches == total)}")

    print("3. Structure")
    for f in (0.05, 0.10, 0.20):
        wts = momentum(p, u, monthly_decisions(cal, w), fraction=f)
        held = (wts > 0).sum(axis=1)
        cap = pd.Series({d: math.ceil(round(f * len(u[d]), 9)) for d in wts.index})
        print(f"   top {f:.0%}: {held.min()}-{held.max()} stocks, never more than {f:.0%} of the universe rounded up: "
              f"{verdict((held <= cap).all())}")
    trade_months = sorted({cal[cal > d][0].month for d in monthly_decisions(cal, w, every=3)})
    print(f"   quarterly variants trade in months {trade_months}: {verdict(trade_months == [1, 4, 7, 10])}")
    default = momentum(p, u, monthly_decisions(cal, w))
    a, b = run_strategy("a", default, p, 10, cal, w, tb), run_strategy("b", default, p, 10, cal, w, tb)
    print(f"   a rerun gives identical equity: {verdict(a.equity.equals(b.equity))}")

    print("4. Stored results against fresh calculations")
    spy_cagr = summary(spy, spy)["CAGR %"]
    row = stored[stored.is_default].iloc[0]
    ew = run_strategy("ew", equal_weight_all(p, u, monthly_decisions(cal, w)), p, 10, cal, w, tb)
    fresh = summary(a, spy)["CAGR %"]
    checks = {
        "lead = return - SPY's, every row": np.allclose(stored.lead, stored.cagr - spy_cagr),
        "published rule's return": abs(row.cagr - fresh) < 1e-9,
        "its t-statistic": abs(row.t_stat - lead_stats(a.yearly, spy.yearly)["t_stat"]) < 1e-9,
        "its 2010-2025 lead": abs(row.lead_2010_2025 - 100 * era_lead(a.yearly, spy.yearly, 2010, 2025)) < 1e-9,
        "its lead over equal weight": abs(row.lead_vs_ew - (fresh - summary(ew, spy)["CAGR %"])) < 1e-9,
        "break-even costs, every row": np.allclose(stored.break_even_bps, [
            break_even_cost([0, 10, 30], [r.cagr_0bps, r.cagr, r.cagr_30bps], r.spy_cagr) for r in stored.itertuples()]),
        "costs only ever lower returns": ((stored.cagr_0bps >= stored.cagr) & (stored.cagr >= stored.cagr_30bps)).all(),
    }
    for name, ok in checks.items():
        print(f"   {name}: {verdict(ok)}")

    print("5. Placebo at zero cost: 20 portfolios of 48 random members, re-drawn monthly")
    rng = np.random.default_rng(7)
    decisions = monthly_decisions(cal, w)
    placebo = []
    for _ in range(20):
        rows = {}
        for d in decisions:
            codes = [c for c in u[d] if c in p.columns and pd.notna(p.at[d, c])]
            picks = rng.choice(codes, size=min(48, len(codes)), replace=False)
            rows[d] = {c: 1 / len(picks) for c in picks}
        placebo.append(summary(run_strategy("random", _weights(rows, decisions), p, 0, cal, w, tb), spy)["CAGR %"])
    placebo = pd.Series(placebo)
    ew0 = summary(run_strategy("ew", equal_weight_all(p, u, decisions), p, 0, cal, w, tb), spy)["CAGR %"]
    print(f"   random portfolios: median {placebo.median():.2f}% a year (range {placebo.min():.2f}-{placebo.max():.2f}); "
          f"every member, equal weight {ew0:.2f}%; momentum variants median {stored.cagr_0bps.median():.2f}% "
          f"(range {stored.cagr_0bps.min():.2f}-{stored.cagr_0bps.max():.2f}); SPY {spy_cagr:.2f}% at 10 bps")
    print(f"   random picks land near equal weight, as they should with no hidden bias: "
          f"{verdict(abs(placebo.median() - ew0) < 1.0)}; variants above every random portfolio: "
          f"{(stored.cagr_0bps > placebo.max()).sum()} of {len(stored)}")


if __name__ == "__main__":
    main()
