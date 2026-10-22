"""One function per strategy. Each returns target weights per rebalance date:

    strategy(prices, universe, rebalance_dates, **params) -> DataFrame[date x code]

`prices` is adjusted close (total return), one column per code. `universe` maps each
rebalance date to the codes that may be picked then (built in bt.coverage, from
point-in-time membership and the price checks). A decision on date d may only use
prices up to the close of d; the engine trades it at the next close.
"""
import numpy as np
import pandas as pd


def formation_returns(prices: pd.DataFrame, codes, date) -> pd.Series:
    """Each code's total return over the calendar year that ends on `date`: from the
    last close of the previous year to the close of `date`. Codes without both prices
    are left out, so a stock can only be ranked with a full formation period."""
    past = prices.index[prices.index <= date]
    start = past[past.year == pd.Timestamp(date).year - 1].max()
    codes = [c for c in codes if c in prices.columns]
    r = prices.loc[date, codes] / prices.loc[start, codes] - 1
    return r.dropna()


def ranked(prices: pd.DataFrame, codes, date) -> pd.Series:
    """Formation returns, best first; ties break alphabetically so results repeat."""
    r = formation_returns(prices, codes, date)
    order = sorted(r.index, key=lambda c: (-r[c], c))
    return r[order]


def top_n(prices: pd.DataFrame, universe: dict, rebalance_dates, n: int = 10) -> pd.DataFrame:
    """Hold last year's N best performers, equal weight, until the next rebalance.
    With fewer than N eligible, hold all of them equally. n=1 is "last year's #1"."""
    rows = {}
    for d in rebalance_dates:
        picks = list(ranked(prices, universe.get(d, []), d).index[:n])
        rows[d] = {c: 1 / len(picks) for c in picks}
    return pd.DataFrame(rows).T.fillna(0.0).reindex(list(rebalance_dates)).fillna(0.0)


def spy_buy_and_hold(prices: pd.DataFrame, universe: dict, rebalance_dates, code: str = "SPY") -> pd.DataFrame:
    """The benchmark: buy SPY once at the first rebalance date and never trade again."""
    first = min(rebalance_dates)
    return pd.DataFrame({code: [1.0]}, index=pd.DatetimeIndex([first]))


# --- Timing rules on SPY ----------------------------------------------------------------
# Each decides every day whether to hold SPY (weight 1) or cash (0), using only prices up
# to that day's close; the engine trades the next day. They run on SPY's adjusted
# (total-return) price, so dividends don't create false "drops" on ex-dividend days.

def moving_average(s: pd.Series, window: int) -> pd.Series:
    """Simple average of the last `window` closes; empty until there are that many."""
    return s.rolling(window, min_periods=window).mean()


def rsi(prices: pd.Series, period: int = 2) -> pd.Series:
    """Wilder's Relative Strength Index, 0-100: 100 - 100 / (1 + average gain / average loss).
    The averages start as the simple mean of the first `period` daily changes, then update
    as avg = (previous avg * (period - 1) + today) / period. Low values mean the price fell
    hard over the last few days (RSI(2) below 10 is a sharp two-day drop)."""
    s = prices.dropna()
    change = s.diff()
    gain, loss = change.clip(lower=0), (-change).clip(lower=0)
    out = pd.Series(np.nan, index=s.index)
    if len(s) > period:
        avg_gain, avg_loss = gain.iloc[1:period + 1].mean(), loss.iloc[1:period + 1].mean()
        for i in range(period, len(s)):
            if i > period:
                avg_gain = (avg_gain * (period - 1) + gain.iloc[i]) / period
                avg_loss = (avg_loss * (period - 1) + loss.iloc[i]) / period
            out.iloc[i] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    return out.reindex(prices.index)


def rsi2_positions(close, rsi_values, trend_ma, exit_ma, entry: float = 10) -> pd.Series:
    """Connors' RSI(2) rule as a day-by-day state: buy when the price is above its long
    trend average and RSI is below `entry` (a sharp dip in an uptrend); hold until the
    price closes above its short exit average (the bounce)."""
    holding, out = False, []
    for c, r, t, x in zip(close, rsi_values, trend_ma, exit_ma):
        if holding and c > x:
            holding = False
        elif not holding and r < entry and c > t:
            holding = True
        out.append(holding)
    return pd.Series(out, index=getattr(close, "index", None))


def _spy_weights(hold: pd.Series, rebalance_dates, code: str) -> pd.DataFrame:
    hold = hold.reindex(pd.DatetimeIndex(rebalance_dates)).fillna(False).astype(bool)
    return pd.DataFrame({code: hold.astype(float)})


def spy_trend(prices: pd.DataFrame, universe: dict, rebalance_dates, window: int = 200,
              code: str = "SPY") -> pd.DataFrame:
    """Hold SPY when it closes above its `window`-day average, else cash."""
    s = prices[code].dropna()
    return _spy_weights(s > moving_average(s, window), rebalance_dates, code)


def spy_golden_cross(prices: pd.DataFrame, universe: dict, rebalance_dates, fast: int = 50,
                     slow: int = 200, code: str = "SPY") -> pd.DataFrame:
    """Hold SPY while its `fast`-day average is above its `slow`-day average ("golden
    cross"), cash after it falls below ("death cross")."""
    s = prices[code].dropna()
    return _spy_weights(moving_average(s, fast) > moving_average(s, slow), rebalance_dates, code)


def spy_rsi2(prices: pd.DataFrame, universe: dict, rebalance_dates, period: int = 2, entry: float = 10,
             trend: int = 200, exit_ma: int = 5, code: str = "SPY") -> pd.DataFrame:
    """Larry Connors' RSI(2) mean reversion: buy a sharp dip (RSI(2) < 10) while SPY is
    above its 200-day average, sell when it closes above its 5-day average."""
    s = prices[code].dropna()
    hold = rsi2_positions(s, rsi(s, period), moving_average(s, trend), moving_average(s, exit_ma), entry)
    return _spy_weights(hold, rebalance_dates, code)
