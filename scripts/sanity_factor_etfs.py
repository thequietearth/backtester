"""M5b sanity check: do our low-volatility and momentum strategies behave like the real
funds that follow those ideas?

Usage: python scripts/sanity_factor_etfs.py   (after scripts/build_data.py)
Writes data/cache/sanity_factor_etfs.csv; the write-up is in docs/sanity-check.md.

1. SPLV replica (Invesco S&P 500 Low Volatility ETF, since May 2011), following the index
   rules: on the last trading day of Jan, Apr, Jul and Oct, take the 100 point-in-time
   members with the lowest volatility over the past year, weight each by 1 / volatility,
   and trade at the close of the third Friday of the next month. Built with our data,
   universe checks and engine, at 10 bps per side. SPLV charges 0.25% a year. If the
   replica tracks SPLV closely, our data and volatility ranking are sound.
2. Momentum: our strategy (top 10% by 12-1 month return, equal weight, monthly) is not a
   replica of any fund, so this is a rough comparison with MTUM (iShares MSCI USA
   Momentum, since 2013: about 125 stocks, risk-adjusted momentum, twice-yearly
   rebalancing) and SPMO (Invesco S&P 500 Momentum, since late 2015 but thinly traded at
   first, so compared from 2017: 100 stocks, weighted by momentum and size). Expect similar
   direction, not similar numbers. Both funds weight big companies more, while ours is
   equal weight, so RSP (the equal-weight S&P 500) is shown as our baseline.

Every fund correlates with the market, so the telling number is the correlation of
returns *beyond SPY*: does our strategy beat or trail SPY in the same months as the fund?
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bt.coverage import rankable_by_date  # noqa: E402
from bt.data import cache_file  # noqa: E402
from bt.engine import run_backtest  # noqa: E402
from bt.metrics import cagr, holding_period_returns  # noqa: E402
from bt.report import backtest_window, monthly_decisions  # noqa: E402
from bt.strategies import low_volatility, momentum  # noqa: E402
from bt.universe import month_ends  # noqa: E402

CACHE = ROOT / "data" / "cache"
EODHD = ROOT / "data" / "raw" / "eodhd"


def etf(code: str) -> pd.Series:
    return pd.read_parquet(cache_file(EODHD, "eod", code)).set_index("date")["adjusted_close"]


def monthly(equity: pd.Series) -> pd.Series:
    return equity.groupby(equity.index.to_period("M")).last().pct_change().dropna()


def compare(name: str, ours: pd.Series, fund: pd.Series, spy: pd.Series, window,
            extra: dict | None = None) -> tuple[pd.DataFrame, dict]:
    """Year-by-year returns over the same purchase-to-purchase dates, plus overall stats.
    Daily returns only count days where every series has a close on that day and the one
    before."""
    start, end = window.boundaries[0], window.end
    series = {"ours": ours, name: fund, "SPY": spy, **(extra or {})}
    clipped = {k: v.loc[start:end] for k, v in series.items()}
    years = pd.DataFrame({k: holding_period_returns(v, window.boundaries) for k, v in clipped.items()})
    years["gap_pts"] = 100 * (years["ours"] - years[name])
    m = pd.DataFrame({k: monthly(v) for k, v in clipped.items()}).dropna()
    d = pd.DataFrame(clipped).pct_change(fill_method=None).dropna()
    stats = {
        "years": f"{window.years[0]}-{window.years[-1]}",
        **{f"CAGR {'ours' if k == 'ours' else k} %": 100 * cagr(v) for k, v in clipped.items()},
        "daily correlation": d["ours"].corr(d[name]),
        "tracking error %/yr": 100 * (d["ours"] - d[name]).std() * np.sqrt(252),
        "monthly correlation beyond SPY": (m["ours"] - m["SPY"]).corr(m[name] - m["SPY"]),
    }
    return years, stats


def third_friday(year: int, month: int, cal: pd.DatetimeIndex) -> pd.Timestamp:
    fridays = pd.date_range(f"{year}-{month:02d}-01", periods=31, freq="D")
    fridays = fridays[(fridays.month == month) & (fridays.weekday == 4)]
    day = fridays[2]
    return cal[cal <= day].max()  # if that Friday was a holiday, the trading day before


def main():
    prices = pd.read_parquet(CACHE / "prices.parquet")
    cal = prices["SPY"].dropna().index
    universe = rankable_by_date(pd.read_parquet(CACHE / "universe_monthly_pit.parquet"))
    spy = prices["SPY"].dropna()
    rows = []

    # 1. SPLV replica: rank at the end of Jan/Apr/Jul/Oct, trade on the third Friday after.
    win = backtest_window(cal, 2012, 2025)
    refs = [d for d in month_ends(cal, "2011-10-01", "2025-10-31") if d.month in (1, 4, 7, 10)]
    w = low_volatility(prices, universe, refs, n=100, weighting="inverse volatility")
    # The engine trades at the close after a decision; the index trades at the third
    # Friday's close, so date each decision the trading day before. It uses data from the
    # reference date, which is older: no lookahead.
    trade_days = [third_friday(d.year, d.month + 1, cal) for d in refs]
    w.index = pd.DatetimeIndex([cal[cal < t].max() for t in trade_days])
    replica = run_backtest(w, prices, cost_bps=10, calendar=cal).equity
    years, stats = compare("SPLV", replica, etf("SPLV"), spy, win)
    print("SPLV replica: 100 calmest members, weighted by 1 / volatility, quarterly\n")
    print((100 * years.drop(columns="gap_pts")).round(1).join(years.gap_pts.round(1)).to_string())
    print(pd.Series(stats).to_string(), "\n")
    rows.append({"check": "SPLV replica", **stats})

    # The app's version (50 calmest, equal weight, quarterly at Dec/Mar/Jun/Sep) next to SPLV.
    app_dates = monthly_decisions(cal, win, every=3)
    app_lv = run_backtest(low_volatility(prices, universe, app_dates, n=50), prices, cost_bps=10, calendar=cal).equity
    _, stats = compare("SPLV", app_lv, etf("SPLV"), spy, win)
    print("App's low volatility (50 calmest, equal weight, quarterly) vs SPLV\n" + pd.Series(stats).to_string(), "\n")
    rows.append({"check": "app low volatility vs SPLV", **stats})

    # 2. Momentum vs MTUM and SPMO, each over its full years.
    for fund, first in (("MTUM", 2014), ("SPMO", 2017)):
        win = backtest_window(cal, first, 2025)
        dates = monthly_decisions(cal, win)
        mom = run_backtest(momentum(prices, universe, dates), prices, cost_bps=10, calendar=cal).equity
        years, stats = compare(fund, mom, etf(fund), spy, win, extra={"RSP": prices["RSP"].dropna()})
        print(f"Momentum (top 10% by 12-1 month return, monthly) vs {fund}\n")
        print((100 * years.drop(columns="gap_pts")).round(1).join(years.gap_pts.round(1)).to_string())
        print(pd.Series(stats).to_string(), "\n")
        rows.append({"check": f"momentum vs {fund}", **stats})
    pd.DataFrame(rows).to_csv(CACHE / "sanity_factor_etfs.csv", index=False)


if __name__ == "__main__":
    main()
