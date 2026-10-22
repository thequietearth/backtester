"""Performance metrics, all computed from a daily equity curve (a Series of portfolio
values indexed by date).

Conventions:
- CAGR uses calendar time (days / 365.25), so it's the steady yearly growth rate that
  turns the first value into the last.
- Volatility and Sharpe annualise daily figures with 252 trading days a year:
  volatility x sqrt(252), because the spread of independent daily moves grows with the
  square root of time.
- Sharpe measures the return earned beyond cash, per unit of risk. Pass the daily T-bill
  return as `risk_free` (bt.data.cash_returns); without it, cash is assumed to earn 0%,
  which flatters every Sharpe ratio a little (T-bills paid 0-5% over 1999-2025).
"""
import numpy as np
import pandas as pd

TRADING_DAYS = 252


def daily_returns(equity: pd.Series) -> pd.Series:
    return equity.pct_change().dropna()


def cagr(equity: pd.Series) -> float:
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    return float((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1)


def annual_volatility(equity: pd.Series) -> float:
    return float(daily_returns(equity).std(ddof=1) * np.sqrt(TRADING_DAYS))


def sharpe_ratio(equity: pd.Series, risk_free: pd.Series | None = None) -> float:
    """Mean daily excess return / its standard deviation, annualised; NaN if there is no
    risk. `risk_free` is the daily return on cash by date (bt.data.cash_returns), so the
    ratio measures what the strategy earned *beyond* T-bills; None means a 0% rate."""
    r = daily_returns(equity)
    if risk_free is not None:
        r = r - risk_free.reindex(r.index).fillna(0.0)
    sd = r.std(ddof=1)
    return float(r.mean() / sd * np.sqrt(TRADING_DAYS)) if sd > 0 else float("nan")


def drawdown_series(equity: pd.Series) -> pd.Series:
    """How far below its previous peak the curve is at each date (0 at a new high)."""
    return equity / equity.cummax() - 1


def max_drawdown(equity: pd.Series) -> dict:
    """The deepest peak-to-trough fall: depth (e.g. -0.25), peak, trough, recovery (first
    date back at the peak, or None) and its length in calendar days, from the peak to the
    recovery (or to the end of the curve if it never recovered)."""
    dd = drawdown_series(equity)
    trough = dd.idxmin()
    peak = equity.loc[:trough].idxmax()
    back = equity.loc[trough:][equity.loc[trough:] >= equity[peak]]
    recovery = back.index[0] if len(back) else None
    end = recovery if recovery is not None else equity.index[-1]
    return {"depth": float(dd[trough]), "peak": peak, "trough": trough,
            "recovery": recovery, "days": int((end - peak).days)}


def yearly_returns(equity: pd.Series) -> pd.Series:
    """Return for each calendar year, from the previous year's last value to this year's.
    The first year is partial: it runs from the first value of the curve."""
    year_end = equity.groupby(equity.index.year).last()
    base = year_end.shift(1)
    base.iloc[0] = equity.iloc[0]
    return year_end / base - 1


def holding_period_returns(equity: pd.Series, trade_dates) -> pd.Series:
    """Return over each holding period: from one rebalance's close to the next one's,
    labelled by the year the period starts. For a yearly strategy that's "the year of
    each pick", which a calendar year isn't quite: picks switch at the close of the first
    trading day, so a calendar year would include one day of the previous pick."""
    dates = [d for d in pd.DatetimeIndex(trade_dates) if d in equity.index]
    values = equity.loc[dates]
    return pd.Series(values.iloc[1:].values / values.iloc[:-1].values - 1,
                     index=[d.year for d in dates[:-1]], name="return")


def best_and_worst_year(equity: pd.Series, returns: pd.Series | None = None) -> tuple[tuple[int, float], tuple[int, float]]:
    """Best and worst year: calendar years by default, or any yearly series passed in."""
    yr = yearly_returns(equity) if returns is None else returns
    return (int(yr.idxmax()), float(yr.max())), (int(yr.idxmin()), float(yr.min()))


def beat_rate(strategy_yearly: pd.Series, benchmark_yearly: pd.Series) -> float:
    """Share of the years both cover in which the strategy beat the benchmark."""
    both = pd.concat([strategy_yearly, benchmark_yearly], axis=1, join="inner").dropna()
    return float((both.iloc[:, 0] > both.iloc[:, 1]).mean())
