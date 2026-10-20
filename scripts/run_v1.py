"""Run the v1 strategies over 1999-2025 and print the results.

Usage: python scripts/run_v1.py
Run scripts/build_price_cache.py first. Outputs (gitignored, data/cache/):
  v1_summary.csv  one row per strategy: CAGR, volatility, Sharpe, drawdown, beat rate...
  v1_yearly.csv   calendar-year returns of every strategy
  v1_picks.csv    every pick of the point-in-time and naive top-10 (and so top-1) strategies

Strategies: SPY buy and hold (the benchmark), last year's #1, and last year's top 10, each
in the point-in-time universe and in the naive one (today's members only - survivorship
bias). Costs 10 bps per side. Each holding year runs from the close of its first trading
day to the close of the next year's first trading day, when the next picks are bought.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bt.coverage import coverage_by_year, rankable_universe  # noqa: E402
from bt.engine import run_backtest  # noqa: E402
from bt.metrics import (annual_volatility, beat_rate, best_and_worst_year, cagr, holding_period_returns,  # noqa: E402
                        max_drawdown, sharpe_ratio)
from bt.strategies import ranked, spy_buy_and_hold, top_n  # noqa: E402
from bt.universe import formation_dates, load_constituents, naive_constituents, naive_security_map  # noqa: E402

CACHE = ROOT / "data" / "cache"
YEARS = range(1999, 2026)
COST_BPS = 10


def picks_table(prices, universe, detail, fdates, cal, names, label, n=10):
    rows = []
    tickers = detail.dropna(subset=["code"]).drop_duplicates(["year", "code"]).set_index(["year", "code"])["ticker"]
    for y, d in fdates.items():
        entry = cal[cal > d].min()
        nxt = cal[cal.year == y + 1]
        exit_ = nxt.min() if len(nxt) else cal.max()
        for rank, (code, fr) in enumerate(ranked(prices, universe.get(d, []), d).head(n).items(), 1):
            px = prices[code]
            held = px.loc[entry:exit_].dropna()
            bought = pd.notna(px.get(entry))
            rows.append({"universe": label, "year": y, "rank": rank, "code": code,
                         "ticker": tickers.get((y, code), code), "name": names.get(code, ""),
                         "formation_return": fr,
                         "holding_return": held.iloc[-1] / px[entry] - 1 if bought and len(held) else float("nan"),
                         "note": "" if bought else "no price at entry: not bought"})
            if bought and held.index[-1] < exit_:
                rows[-1]["note"] = f"data ended {held.index[-1].date()}, real outcome unknown"
    return pd.DataFrame(rows)


def main():
    cons = load_constituents(ROOT / "data" / "constituents.parquet")
    smap = pd.read_csv(CACHE / "security_map.csv", parse_dates=["start", "end"])
    prices, raw, factors = (pd.read_parquet(CACHE / f) for f in
                            ("prices.parquet", "close.parquet", "split_factors.parquet"))
    cal = prices["SPY"].dropna().index
    fdates = formation_dates(cal, YEARS)
    rebalance = list(fdates.values)
    end = cal[cal.year == YEARS[-1] + 1].min()  # first trading day after the last holding year
    # Holding years run from each purchase (the close after a formation date) to the next.
    # Every strategy, SPY included, is measured over exactly these dates.
    boundaries = [cal[cal > d].min() for d in rebalance] + [end]
    names = smap.dropna(subset=["code"]).drop_duplicates("code").set_index("code")["name"].to_dict()

    print("building universes...", flush=True)
    _, pit_detail = coverage_by_year(cons, smap, prices, cal, YEARS, raw_prices=raw, split_factors=factors)
    ncons = naive_constituents(cons)
    _, naive_detail = coverage_by_year(ncons, naive_security_map(smap, ncons), prices, cal, YEARS,
                                       raw_prices=raw, split_factors=factors)
    pit, naive = rankable_universe(pit_detail, fdates), rankable_universe(naive_detail, fdates)

    strategies = {
        "SPY buy and hold": spy_buy_and_hold(prices, pit, rebalance),
        "Top 1": top_n(prices, pit, rebalance, n=1),
        "Top 10": top_n(prices, pit, rebalance, n=10),
        "Top 1 (naive)": top_n(prices, naive, rebalance, n=1),
        "Top 10 (naive)": top_n(prices, naive, rebalance, n=10),
    }
    equity, yearly, summary = {}, {}, []
    for name, w in strategies.items():
        r = run_backtest(w, prices, cost_bps=COST_BPS, calendar=cal)
        eq = r.equity.loc[:end]
        equity[name] = eq
        yearly[name] = holding_period_returns(eq, boundaries)
        dd = max_drawdown(eq)
        (by, br), (wy, wr) = best_and_worst_year(eq, yearly[name])
        trades = r.trades[r.trades.date <= end]
        summary.append({"strategy": name, "$10k becomes": 10_000 * eq.iloc[-1],  # equity starts at 1.0 before costs
                        "CAGR %": 100 * cagr(eq), "volatility %": 100 * annual_volatility(eq),
                        "Sharpe": sharpe_ratio(eq), "max drawdown %": 100 * dd["depth"],
                        "drawdown days": dd["days"], "best year": f"{by} ({100 * br:+.0f}%)",
                        "worst year": f"{wy} ({100 * wr:+.0f}%)",
                        "data-ended exits": int((trades.action == "exit").sum()),
                        "skipped buys": int((trades.action == "skipped").sum())})
    summary = pd.DataFrame(summary).set_index("strategy")
    spy_yearly = yearly["SPY buy and hold"]
    summary["years beating SPY %"] = [100 * beat_rate(yearly[s], spy_yearly) if s != "SPY buy and hold"
                                      else float("nan") for s in summary.index]
    yearly = pd.DataFrame(yearly)

    picks = pd.concat([picks_table(prices, pit, pit_detail, fdates, cal, names, "point-in-time"),
                       picks_table(prices, naive, naive_detail, fdates, cal, names, "naive")])
    summary.to_csv(CACHE / "v1_summary.csv")
    yearly.to_csv(CACHE / "v1_yearly.csv")
    picks.to_csv(CACHE / "v1_picks.csv", index=False)

    pd.set_option("display.width", 220)
    print(f"\n{YEARS[0]}-{YEARS[-1]}, costs {COST_BPS} bps per side")
    print(summary.round(2).to_string())
    print("\nholding-year returns (%), each from the purchase to the next year's purchase:")
    print((100 * yearly).round(1).to_string())
    print("\nlast year's #1, point-in-time vs naive (holding-year return):")
    top1 = picks[picks["rank"] == 1].pivot(index="year", columns="universe", values=["ticker", "holding_return"])
    for y in YEARS:
        print(f"  {y}: {top1.loc[y, ('ticker', 'point-in-time')]:8} {100 * top1.loc[y, ('holding_return', 'point-in-time')]:+7.1f}%"
              f"   naive: {top1.loc[y, ('ticker', 'naive')]:8} {100 * top1.loc[y, ('holding_return', 'naive')]:+7.1f}%")


if __name__ == "__main__":
    main()
