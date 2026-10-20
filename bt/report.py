"""Results for the app and the write-up: run strategies over a chosen window of years,
summarise them, and build the year-by-year table. Pure functions; no Streamlit here.

A "year" is a holding year: from the purchase at the close of the first trading day
after a formation date, to the next purchase. Every strategy and SPY are measured over
exactly the same dates (CLAUDE.md rule 8).
"""
from dataclasses import dataclass

import pandas as pd

from bt.engine import DATA_ENDED, run_backtest
from bt.metrics import annual_volatility, beat_rate, cagr, holding_period_returns, max_drawdown, sharpe_ratio
from bt.universe import formation_dates


@dataclass
class Window:
    years: list[int]
    rebalance: list[pd.Timestamp]   # formation dates: decisions are made at these closes
    boundaries: list[pd.Timestamp]  # purchase dates, plus the final sale
    end: pd.Timestamp               # the final sale: first trading day after the last year


def backtest_window(calendar, start_year: int, end_year: int) -> Window:
    cal = pd.DatetimeIndex(calendar)
    years = list(range(start_year, end_year + 1))
    rebalance = list(formation_dates(cal, years).values)
    after = cal[cal.year == end_year + 1]
    end = after.min() if len(after) else cal.max()
    boundaries = [cal[cal > d].min() for d in rebalance] + [end]
    return Window(years, [pd.Timestamp(d) for d in rebalance], boundaries, end)


@dataclass
class StrategyRun:
    name: str
    weights: pd.DataFrame
    equity: pd.Series
    trades: pd.DataFrame
    yearly: pd.Series  # holding-year returns, labelled by year


def run_strategy(name, weights, prices, cost_bps, calendar, window: Window) -> StrategyRun:
    r = run_backtest(weights, prices, cost_bps=cost_bps, calendar=calendar)
    equity = r.equity.loc[:window.end]
    trades = r.trades[r.trades.date <= window.end]
    return StrategyRun(name, weights, equity, trades, holding_period_returns(equity, window.boundaries))


def summary(run: StrategyRun, spy: StrategyRun) -> dict:
    dd = max_drawdown(run.equity)
    return {"Strategy": run.name, "$10k becomes": 10_000 * run.equity.iloc[-1],
            "CAGR %": 100 * cagr(run.equity), "Volatility %": 100 * annual_volatility(run.equity),
            "Sharpe": sharpe_ratio(run.equity), "Max drawdown %": 100 * dd["depth"],
            "Drawdown lasted (years)": dd["days"] / 365.25,
            "Years beating SPY %": float("nan") if run is spy else 100 * beat_rate(run.yearly, spy.yearly)}


def year_table(run: StrategyRun, spy: StrategyRun, labels: dict, coverage: dict | None) -> pd.DataFrame:
    """One row per holding year: holdings, strategy and SPY returns, beat SPY, coverage.

    `labels` maps code -> what to show (e.g. ticker); "†" marks a holding whose data
    ended during the year (sold at its last price, real outcome unknown). `coverage`
    maps year -> (band, coverage %), or is None (e.g. for the naive universe).
    """
    years = list(run.yearly.index)
    rows = []
    for y, d in zip(years, run.weights.index):
        w = run.weights.loc[d]
        held = sorted(w[w > 0].index, key=lambda c: (-w[c], labels.get(c, c)))
        start, stop = pd.Timestamp(y, 1, 1), pd.Timestamp(y + 1, 1, 15)
        ended = set(run.trades[(run.trades.action == "exit") & run.trades.note.str.startswith(DATA_ENDED)
                               & (run.trades.date >= start) & (run.trades.date <= stop)].code)
        holdings = ", ".join(labels.get(c, c) + (" †" if c in ended else "") for c in held) or "cash"
        s, b = run.yearly[y], spy.yearly.get(y)
        cov = ""
        if coverage and y in coverage:
            band, pct = coverage[y]
            cov = f"{'✓' if band == 'trusted' else '⚠'} {band} ({pct:.1f}%)"
        rows.append({"Year": y, "Holdings": holdings, "Strategy %": 100 * s, "SPY %": 100 * b,
                     "Beat SPY": "✓" if s > b else "✗", "Coverage": cov})
    return pd.DataFrame(rows)
