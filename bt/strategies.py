"""One function per strategy. Each returns target weights per rebalance date:

    strategy(prices, universe, rebalance_dates, **params) -> DataFrame[date x code]

`prices` is adjusted close (total return), one column per code. `universe` maps each
rebalance date to the codes that may be picked then (built in bt.coverage, from
point-in-time membership and the price checks). A decision on date d may only use
prices up to the close of d; the engine trades it at the next close.
"""
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
