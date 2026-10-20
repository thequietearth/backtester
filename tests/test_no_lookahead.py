"""No-lookahead proof (CLAUDE.md rule 1): changing any price after day t must not change
any decision made on or before t, nor the equity curve up to t.

Uses a small momentum strategy written here for the test ("hold whichever stock rose most
over the last 20 days"), so the engine is exercised the way real strategies will use it.
M3's strategies get the same check.
"""
import numpy as np
import pandas as pd

from bt.engine import run_backtest

DAYS = pd.bdate_range("2023-01-02", periods=200)


def momentum_strategy(prices: pd.DataFrame, rebalance_dates, lookback: int = 20) -> pd.DataFrame:
    rows = {}
    for d in rebalance_dates:
        past = prices.loc[:d]  # only data available at the close of d
        if len(past) <= lookback:
            continue
        ret = past.iloc[-1] / past.iloc[-1 - lookback] - 1
        rows[d] = (ret == ret.max()).astype(float)
    return pd.DataFrame(rows).T


def random_prices(seed):
    rng = np.random.default_rng(seed)
    steps = rng.normal(0.0005, 0.02, size=(len(DAYS), 3))
    return pd.DataFrame(100 * np.exp(np.cumsum(steps, axis=0)), index=DAYS, columns=["A", "B", "C"])


def test_changing_prices_after_t_changes_nothing_up_to_t():
    prices = random_prices(1)
    rebalance = DAYS[25::20]
    w1 = momentum_strategy(prices, rebalance)
    r1 = run_backtest(w1, prices, cost_bps=10)

    for t in DAYS[[60, 100, 150]]:
        changed = prices.copy()
        after = changed.index > t
        changed.loc[after] = random_prices(2).loc[after].values  # every price after t replaced
        w2 = momentum_strategy(changed, rebalance)
        r2 = run_backtest(w2, changed, cost_bps=10)

        pd.testing.assert_frame_equal(w1.loc[:t], w2.loc[:t])  # same decisions up to t
        pd.testing.assert_series_equal(r1.equity.loc[:t], r2.equity.loc[:t])  # same equity up to t
        assert not r1.equity.loc[t:].equals(r2.equity.loc[t:])  # the change did matter afterwards
