"""Results for the app and the write-up: run strategies over a chosen window of years,
summarise them, and build the year-by-year table. Pure functions; no Streamlit here.

A "year" is a holding year: from the purchase at the close of the first trading day
after a formation date, to the next purchase. Every strategy and SPY are measured over
exactly the same dates (CLAUDE.md rule 8). Timing rules decide every day, and monthly
or quarterly strategies at month-ends, within the same window.
"""
from dataclasses import dataclass

import pandas as pd

from bt.data import cash_returns
from bt.engine import DATA_ENDED, run_backtest
from bt.metrics import annual_volatility, beat_rate, cagr, holding_period_returns, max_drawdown, sharpe_ratio
from bt.universe import formation_dates, month_ends

TRADE_ACTIONS = {"buy", "sell", "exit"}


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


def daily_decisions(calendar, window: Window) -> pd.DatetimeIndex:
    """Decision dates for daily timing rules: every trading day from the first formation
    date up to (not including) the final sale, so the first trade matches the yearly
    strategies' first purchase."""
    cal = pd.DatetimeIndex(calendar)
    return cal[(cal >= window.rebalance[0]) & (cal < window.end)]


def monthly_decisions(calendar, window: Window, every: int = 1) -> list[pd.Timestamp]:
    """Decision dates for strategies that rebalance every `every` months: month-ends from
    the first formation date (the end of December), so the first trade matches the yearly
    strategies' first purchase. every=3 gives the ends of Dec, Mar, Jun and Sep. The last
    is the final month-end whose trade comes before the final sale."""
    cal = pd.DatetimeIndex(calendar)
    out = []
    for d in month_ends(cal, window.rebalance[0], window.end):
        nxt = cal[cal > d]
        if d.month % every == 0 and len(nxt) and nxt[0] < window.end:
            out.append(d)
    return out


@dataclass
class StrategyRun:
    name: str
    weights: pd.DataFrame
    equity: pd.Series
    holdings: pd.DataFrame
    trades: pd.DataFrame
    yearly: pd.Series  # holding-year returns, labelled by year
    window: Window
    risk_free: pd.Series | None  # daily return on cash, for Sharpe; None = 0%


def run_strategy(name, weights, prices, cost_bps, calendar, window: Window, cash_rate=None,
                 ended_recovery: float = 1.0) -> StrategyRun:
    r = run_backtest(weights, prices, cost_bps=cost_bps, calendar=calendar, cash_rate=cash_rate,
                     ended_recovery=ended_recovery)
    equity = r.equity.loc[:window.end]
    risk_free = cash_returns(equity.index, cash_rate) if cash_rate is not None else None
    return StrategyRun(name, weights, equity, r.holdings.loc[:window.end], r.trades[r.trades.date <= window.end],
                       holding_period_returns(equity, window.boundaries), window, risk_free)


def summary(run: StrategyRun, spy: StrategyRun) -> dict:
    dd = max_drawdown(run.equity)
    trades = run.trades.action.isin(TRADE_ACTIONS).sum()
    return {"Strategy": run.name, "$10k becomes": 10_000 * run.equity.iloc[-1],
            "CAGR %": 100 * cagr(run.equity), "Volatility %": 100 * annual_volatility(run.equity),
            "Sharpe": sharpe_ratio(run.equity, run.risk_free), "Max drawdown %": 100 * dd["depth"],
            "Drawdown lasted (years)": dd["days"] / 365.25,
            "Years beating SPY %": float("nan") if run is spy else 100 * beat_rate(run.yearly, spy.yearly),
            "Trades per year": trades / len(run.window.years),
            "Time invested %": 100 * (1 - run.holdings["cash"]).mean()}


def contributions(run: StrategyRun, prices: pd.DataFrame) -> pd.DataFrame:
    """Each holding's gain or loss in each holding year, as a share of the portfolio's
    value at the start of the year: 0.05 means it added 5 percentage points to the year's
    return. DataFrame[year x code].

    Each day a position gains (its value the evening before) x (its price change). A stock
    without a price keeps its last value, as in the engine. Together with cash interest
    and minus costs, the contributions add up exactly to the year's return.
    """
    codes = [c for c in run.holdings.columns if c != "cash"]
    px = prices[codes].reindex(run.equity.index).ffill()
    value = run.holdings[codes].mul(run.equity, axis=0)
    gain = value.shift() * (px / px.shift() - 1)
    bounds, rows = run.window.boundaries, {}
    for i, y in enumerate(run.yearly.index):
        start, stop = bounds[i], bounds[i + 1]
        rows[y] = gain.loc[(gain.index > start) & (gain.index <= stop)].sum() / run.equity[start]
    return pd.DataFrame(rows).T


def turnover(run: StrategyRun) -> pd.Series:
    """Share of the portfolio sold, per trade date: value sold / portfolio value before
    that day's trades. Summed over a year, 100% means the whole portfolio was replaced
    once. Buying with fresh cash (the first purchase) isn't turnover."""
    t = run.trades
    sold = t[t.action.isin({"sell", "exit"})].groupby("date")["value"].sum()
    before = run.equity + t.groupby("date")["cost"].sum().reindex(run.equity.index).fillna(0.0)
    return sold / before.reindex(sold.index)


def _describe_portfolio(run: StrategyRun, year: int, start, stop, contrib: pd.DataFrame, sold: pd.Series,
                        labels: dict) -> str:
    """'48 stocks · 310% turnover · biggest: NVDA +4.1, AAPL -2.0, MSFT +1.5 pts': the
    average number held, turnover, and the three holdings that moved the year's return
    most (gain or loss). "†" marks holdings whose data ended during the year."""
    h = run.holdings.drop(columns="cash")
    h = h.loc[(h.index >= start) & (h.index < stop)]
    n = round((h > 0).sum(axis=1).mean())
    held = h.columns[(h > 0).any()]
    trades = run.trades[(run.trades.date >= start) & (run.trades.date < stop)]
    ended = set(trades[(trades.action == "exit") & trades.note.str.startswith(DATA_ENDED)].code)
    c = contrib.loc[year, held] if len(held) else pd.Series(dtype=float)
    biggest = sorted(held, key=lambda k: (-abs(c[k]), labels.get(k, k)))[:3]
    parts = [f"{labels.get(k, k)}{' †' if k in ended else ''} {round(100 * c[k], 1) + 0.0:+.1f}" for k in biggest]
    turned = 100 * sold[(sold.index >= start) & (sold.index < stop)].sum()
    text = f"{n} stock{'' if n == 1 else 's'} · {turned:.0f}% turnover · biggest: {', '.join(parts)} pts"
    return text + (f" · data ended: {len(ended)} †" if ended else "")


def year_table(run: StrategyRun, spy: StrategyRun, labels: dict, coverage: dict | None,
               kind: str = "picks", prices: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per holding year: holdings, strategy and SPY returns, beat SPY, coverage.

    `labels` maps code -> what to show (e.g. ticker); "†" marks a holding whose data
    ended during the year (sold at its last price, real outcome unknown). `coverage`
    maps year -> (band, coverage %), or is None (e.g. for the naive universe). `kind`
    says how to describe the holdings: "picks" lists them (yearly strategies); "timing"
    gives time invested and trades (SPY timing rules); "portfolio" gives the number held,
    turnover and biggest contributors (strategies holding dozens of stocks and
    rebalancing within the year; needs `prices`).
    """
    rows = []
    bounds = run.window.boundaries
    if kind == "portfolio":
        contrib, sold = contributions(run, prices), turnover(run)
    for i, y in enumerate(run.yearly.index):
        start, stop = bounds[i], bounds[i + 1]
        if kind == "portfolio":
            holdings = _describe_portfolio(run, y, start, stop, contrib, sold, labels)
        elif kind == "timing":
            h = run.holdings.loc[(run.holdings.index >= start) & (run.holdings.index < stop)]
            n = run.trades[(run.trades.date >= start) & (run.trades.date < stop)
                           & run.trades.action.isin(TRADE_ACTIONS)]
            holdings = f"invested {100 * (1 - h['cash']).mean():.0f}% of the time, {len(n)} trades"
        else:
            w = run.weights.iloc[i]
            held = sorted(w[w > 0].index, key=lambda c: (-w[c], labels.get(c, c)))
            ended = set(run.trades[(run.trades.action == "exit") & run.trades.note.str.startswith(DATA_ENDED)
                                   & (run.trades.date >= start) & (run.trades.date <= stop + pd.Timedelta(days=14))].code)
            # A pick with no price on the purchase day (e.g. taken over on the formation date)
            # can't be bought; its share stays in cash.
            skipped = set(run.trades[(run.trades.action == "skipped") & (run.trades.date == start)].code)
            holdings = ", ".join(labels.get(c, c) + (" †" if c in ended else "") + (" (not bought)" if c in skipped
                                                                                    else "") for c in held) or "cash"
        s, b = run.yearly[y], spy.yearly.get(y)
        cov = ""
        if coverage and y in coverage:
            band, pct = coverage[y]
            cov = f"{'✓' if band == 'trusted' else '⚠'} {band} ({pct:.1f}%)"
        rows.append({"Year": y, "Holdings": holdings, "Strategy %": 100 * s, "SPY %": 100 * b,
                     "Beat SPY": "✓" if s > b else "✗", "Coverage": cov})
    return pd.DataFrame(rows)
