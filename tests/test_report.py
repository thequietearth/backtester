"""Tests for bt.report: the backtest window and the year-by-year table, on made-up data."""
import numpy as np
import pandas as pd
import pytest

from bt.report import backtest_window, run_strategy, year_table

CAL = pd.bdate_range("2019-12-02", "2022-01-31")


def test_backtest_window_years_run_from_purchase_to_next_purchase():
    w = backtest_window(CAL, 2020, 2021)
    assert w.rebalance == [pd.Timestamp("2019-12-31"), pd.Timestamp("2020-12-31")]  # formation dates
    assert w.boundaries == [pd.Timestamp("2020-01-01"), pd.Timestamp("2021-01-01"), pd.Timestamp("2022-01-03")]
    assert w.end == pd.Timestamp("2022-01-03")  # first trading day after the last year: the last sale


def test_year_table_lists_holdings_returns_beat_and_coverage():
    prices = pd.DataFrame({"A": 100.0, "B": 100.0, "SPY": 100.0}, index=CAL)
    prices.loc["2020-06-01":, "A"] = 150.0   # A: +50% in 2020
    prices.loc["2021-03-01":, "B"] = 90.0    # B: -10% in 2021
    prices.loc["2021-06-01":, "SPY"] = 110.0  # SPY: +10% in 2021
    prices.loc["2021-07-01":, "B"] = np.nan   # B's data ends mid-2021 while held
    win = backtest_window(CAL, 2020, 2021)
    weights = pd.DataFrame({"A": [1.0, 0.0], "B": [0.0, 1.0]}, index=win.rebalance)
    strat = run_strategy("Top 1", weights, prices, 0, CAL, win)
    spy = run_strategy("SPY", pd.DataFrame({"SPY": [1.0]}, index=win.rebalance[:1]), prices, 0, CAL, win)
    coverage = {2020: ("trusted", 98.0), 2021: ("lower coverage", 90.0)}
    t = year_table(strat, spy, {"A": "AAA", "B": "BBB"}, coverage)
    assert list(t["Year"]) == [2020, 2021]
    assert list(t["Holdings"]) == ["AAA", "BBB †"]  # † = data ended while held
    assert t["Strategy %"].tolist() == pytest.approx([50.0, -10.0])
    assert t["SPY %"].tolist() == pytest.approx([0.0, 10.0])
    assert list(t["Beat SPY"]) == ["✓", "✗"]
    assert list(t["Coverage"]) == ["✓ trusted (98.0%)", "⚠ lower coverage (90.0%)"]
