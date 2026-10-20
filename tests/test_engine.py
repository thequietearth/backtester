"""Engine tests on tiny made-up prices, each worked out by hand in the comments.

Conventions (see bt/engine.py):
- equity starts at 1.0; weights decided at the close of day t trade at the close of
  the next trading day;
- after a trade, every position is exactly its target share of the post-cost equity E',
  and the cost is c = 0.001 (10 bps) of what was actually traded:
      E' = E - c * sum(|w_i * E' - V_i|)
  For a $1 entry fully into one stock: E' = 1 - c * E'  ->  E' = 1 / 1.001.
"""
import numpy as np
import pandas as pd
import pytest

from bt.engine import run_backtest

D = pd.bdate_range("2024-01-01", periods=6)  # Mon 1 Jan .. Mon 8 Jan
C = 0.001
E1 = 1 / (1 + C)  # equity right after a full $1 entry


def frame(**cols):
    return pd.DataFrame(cols, index=D[:len(next(iter(cols.values())))], dtype=float)


def weights(rows):
    """{decision day number: {code: weight}} -> weights DataFrame."""
    return pd.DataFrame({D[i]: w for i, w in rows.items()}).T.fillna(0.0)


def test_single_stock_follows_its_price_after_the_entry_cost():
    prices = frame(A=[10, 11, 12, 9.9])
    r = run_backtest(weights({0: {"A": 1.0}}), prices, cost_bps=10)
    # Decided on day 0, bought at day 1's close (11). Then the position moves with the price.
    assert list(r.equity.index) == list(D[1:4])
    np.testing.assert_allclose(r.equity.values, [E1, E1 * 12 / 11, E1 * 9.9 / 11])
    t = r.trades.iloc[0]
    assert (t.date, t.code, t.action, t.price) == (D[1], "A", "buy", 11)
    assert t.value == pytest.approx(E1) and t.cost == pytest.approx(1 - E1)


def test_two_stocks_drift_with_their_prices_and_are_not_rebalanced():
    prices = frame(A=[10, 10, 20], B=[10, 10, 5])
    r = run_backtest(weights({0: {"A": 0.5, "B": 0.5}}), prices, cost_bps=10)
    # Day 1: E1/2 each. Day 2: A doubles -> E1, B halves -> E1/4. Total 1.25 * E1.
    assert r.equity[D[2]] == pytest.approx(1.25 * E1)
    assert r.holdings.loc[D[2], "A"] == pytest.approx(0.8)  # drifted, not reset to 50%
    assert r.holdings.loc[D[2], "B"] == pytest.approx(0.2)


def test_rebalance_costs_both_the_sale_and_the_purchase():
    prices = frame(A=[10, 10, 20, 20], B=[10, 10, 5, 5])
    r = run_backtest(weights({0: {"A": 0.5, "B": 0.5}, 2: {"B": 1.0}}), prices, cost_bps=10)
    # Day 3 trades the day-2 decision. Before: A = E1, B = E1/4, E = 1.25 * E1.
    # Sell all of A (E1); buy B up to E': E' = E - c*(E1 + E' - E1/4)
    #   -> E' = E1 * (1.25 - 0.75c) / (1 + c)
    e_after = E1 * (1.25 - 0.75 * C) / (1 + C)
    assert r.equity[D[3]] == pytest.approx(e_after)
    day3 = r.trades[r.trades.date == D[3]].set_index("code")
    assert day3.loc["A", "action"] == "sell" and day3.loc["A", "value"] == pytest.approx(E1)
    assert day3.loc["B", "action"] == "buy" and day3.loc["B", "value"] == pytest.approx(e_after - E1 / 4)
    assert day3.cost.sum() == pytest.approx(1.25 * E1 - e_after)  # cost = equity lost to trading
    assert r.holdings.loc[D[3], "B"] == pytest.approx(1.0)


def test_unused_weight_stays_in_cash_at_zero_interest():
    prices = frame(A=[10, 10, 20])
    r = run_backtest(weights({0: {"A": 0.5}}), prices, cost_bps=10)
    # Day 1: E' = 1 - c * 0.5 E'  ->  E' = 1/1.0005, half in A, half cash.
    # Day 2: A doubles -> 1.5 * E'; cash is 1/3 of that.
    e1 = 1 / (1 + 0.5 * C)
    assert r.equity[D[2]] == pytest.approx(1.5 * e1)
    assert r.holdings.loc[D[2], "cash"] == pytest.approx(1 / 3)


def test_stock_whose_data_ends_while_held_is_sold_at_its_last_price_and_flagged():
    days = pd.bdate_range("2024-01-01", periods=20)
    a = [10, 10, 12] + [np.nan] * 17
    prices = pd.DataFrame({"A": a, "B": 10.0}, index=days)
    w = pd.DataFrame({"A": [1.0]}, index=[days[0]])
    r = run_backtest(w, prices, cost_bps=10)
    # Day 2: 1.2 * E1. From day 3 there is no price: held at its last value while the gap
    # might be temporary. After more than 10 trading days without a price (day 13) it is
    # sold at that last price (12), paying 10 bps, and the money is cash from then on.
    # Deciding this needs only what is known on each day - no peeking at later prices.
    assert r.equity[days[12]] == pytest.approx(1.2 * E1)
    assert r.equity[days[13]] == pytest.approx(1.2 * E1 * (1 - C))
    assert r.equity[days[19]] == pytest.approx(1.2 * E1 * (1 - C))
    t = r.trades.iloc[-1]
    assert (t.date, t.code, t.action, t.price) == (days[13], "A", "exit", 12)
    assert t.note == "data ended, real outcome unknown (last price 2024-01-03)"


def test_prices_that_resume_after_a_long_hole_are_not_followed():
    # Real case: EODHD's Coastal (CGP) stops at its 2001 takeover, then restarts as a
    # different instrument. After more than 10 missing days the position is gone.
    days = pd.bdate_range("2024-01-01", periods=20)
    a = [10, 10, 12] + [np.nan] * 12 + [50.0] * 5
    prices = pd.DataFrame({"A": a, "B": 10.0}, index=days)
    r = run_backtest(pd.DataFrame({"A": [1.0]}, index=[days[0]]), prices, cost_bps=10)
    assert r.equity[days[19]] == pytest.approx(1.2 * E1 * (1 - C))  # not 5x from the impostor


def test_a_short_gap_in_prices_is_not_mistaken_for_data_ending():
    prices = frame(A=[10, 10, np.nan, 15], B=[10, 10, 10, 10])
    r = run_backtest(weights({0: {"A": 1.0}}), prices, cost_bps=10)
    # Day 2 has no price: hold at the last value. Day 3: E1 * 15/10.
    assert r.equity[D[2]] == pytest.approx(E1)
    assert r.equity[D[3]] == pytest.approx(1.5 * E1)
    assert (r.trades.action == "exit").sum() == 0


def test_no_price_on_the_trade_date_leaves_that_weight_in_cash_and_says_so():
    prices = frame(A=[10, np.nan, 10], B=[10, 10, 10])
    r = run_backtest(weights({0: {"A": 0.5, "B": 0.5}}), prices, cost_bps=10)
    # Only B can be bought: E' = 1 - c * 0.5 E'. A's half stays in cash.
    assert r.equity[D[1]] == pytest.approx(1 / (1 + 0.5 * C))
    skipped = r.trades[r.trades.code == "A"].iloc[0]
    assert skipped.action == "skipped" and skipped.note == "no price on the trade date"


def test_decision_on_the_last_day_cannot_trade_and_is_reported():
    prices = frame(A=[10, 10, 10])
    with pytest.warns(UserWarning, match="no trading day after"):
        r = run_backtest(weights({0: {"A": 1.0}, 2: {"A": 0.0}}), prices, cost_bps=10)
    assert len(r.trades) == 1  # only the day-1 purchase


def test_zero_cost_reproduces_the_price_path_exactly():
    prices = frame(A=[10, 11, 12, 9.9])
    r = run_backtest(weights({0: {"A": 1.0}}), prices, cost_bps=0)
    np.testing.assert_allclose(r.equity.values, [1.0, 12 / 11, 9.9 / 11])


def test_rejects_leverage_and_short_selling():
    prices = frame(A=[10, 10], B=[10, 10])
    with pytest.raises(ValueError, match="sum"):
        run_backtest(weights({0: {"A": 0.7, "B": 0.7}}), prices)
    with pytest.raises(ValueError, match="negative"):
        run_backtest(weights({0: {"A": -0.5}}), prices)
