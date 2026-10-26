"""Tests for bt.report: the backtest window and the year-by-year table, on made-up data."""
import numpy as np
import pandas as pd
import pytest

from bt.report import (backtest_window, contributions, daily_decisions, monthly_decisions, run_strategy, summary,
                       year_table)

CAL = pd.bdate_range("2019-12-02", "2022-01-31")


def test_backtest_window_years_run_from_purchase_to_next_purchase():
    w = backtest_window(CAL, 2020, 2021)
    assert w.rebalance == [pd.Timestamp("2019-12-31"), pd.Timestamp("2020-12-31")]  # formation dates
    assert w.boundaries == [pd.Timestamp("2020-01-01"), pd.Timestamp("2021-01-01"), pd.Timestamp("2022-01-03")]
    assert w.end == pd.Timestamp("2022-01-03")  # first trading day after the last year: the last sale


def test_daily_decisions_run_from_the_first_formation_date_to_before_the_final_sale():
    w = backtest_window(CAL, 2020, 2021)
    d = daily_decisions(CAL, w)
    assert d[0] == pd.Timestamp("2019-12-31") and d[-1] == pd.Timestamp("2021-12-31")


def test_timing_rule_year_table_and_summary_show_time_invested_and_trades():
    prices = pd.DataFrame({"SPY": 100.0}, index=CAL)
    w = backtest_window(CAL, 2020, 2021)
    days = daily_decisions(CAL, w)
    hold = (days >= pd.Timestamp("2020-03-02")) & (days < pd.Timestamp("2020-09-01"))
    weights = pd.DataFrame({"SPY": hold.astype(float)}, index=days)
    run = run_strategy("200-day trend", weights, prices, 0, CAL, w)
    spy = run_strategy("SPY", pd.DataFrame({"SPY": [1.0]}, index=w.rebalance[:1]), prices, 0, CAL, w)
    # Bought at the close of 3 Mar (day after the first "hold"), sold at the close of 2 Sep.
    year = pd.bdate_range("2020-01-01", "2020-12-31")
    invested = pd.bdate_range("2020-03-03", "2020-09-01")
    t = year_table(run, spy, {}, None, kind="timing")
    assert list(t["Holdings"]) == [f"invested {100 * len(invested) / len(year):.0f}% of the time, 2 trades",
                                   "invested 0% of the time, 0 trades"]
    s = summary(run, spy)
    assert s["Trades per year"] == pytest.approx(1.0)  # 2 trades over 2 years
    assert s["Time invested %"] == pytest.approx(100 * len(invested) / len(run.equity))


def test_cash_rate_flows_into_returns_and_sharpe():
    prices = pd.DataFrame({"SPY": 100.0}, index=CAL)
    w = backtest_window(CAL, 2020, 2021)
    cash_only = pd.DataFrame({"SPY": [0.0]}, index=w.rebalance[:1])
    rate = pd.Series(0.05, index=CAL)
    run = run_strategy("cash", cash_only, prices, 0, CAL, w, cash_rate=rate)
    assert run.yearly[2020] == pytest.approx(1.05 ** (366 / 365) - 1, rel=1e-3)  # 2020 had 366 days
    spy = run_strategy("SPY", pd.DataFrame({"SPY": [1.0]}, index=w.rebalance[:1]), prices, 0, CAL, w, cash_rate=rate)
    assert np.isnan(summary(run, spy)["Sharpe"])  # earning exactly the T-bill rate: no excess, no risk


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


def test_monthly_and_quarterly_decisions_end_with_the_last_month_traded_before_the_final_sale():
    w = backtest_window(CAL, 2020, 2021)
    m = monthly_decisions(CAL, w)
    assert m[0] == pd.Timestamp("2019-12-31") and m[-1] == pd.Timestamp("2021-11-30") and len(m) == 24
    # Quarterly: the ends of Dec, Mar, Jun and Sep. End-Dec 2021 would trade on the final-sale day.
    assert monthly_decisions(CAL, w, every=3) == [pd.Timestamp(d) for d in (
        "2019-12-31", "2020-03-31", "2020-06-30", "2020-09-30", "2020-12-31", "2021-03-31", "2021-06-30",
        "2021-09-30")]


def portfolio_run(prices):
    win = backtest_window(CAL, 2020, 2021)
    # 2020: half A, half B. 2021: everything in C.
    weights = pd.DataFrame({"A": [0.5, 0.0], "B": [0.5, 0.0], "C": [0.0, 1.0]}, index=win.rebalance)
    run = run_strategy("Portfolio", weights, prices, 0, CAL, win)
    spy = run_strategy("SPY", pd.DataFrame({"SPY": [1.0]}, index=win.rebalance[:1]), prices, 0, CAL, win)
    return run, spy


def test_portfolio_year_table_shows_stock_count_turnover_and_biggest_contributors():
    prices = pd.DataFrame({"A": 100.0, "B": 100.0, "C": 100.0, "SPY": 100.0}, index=CAL)
    prices.loc["2020-06-01":, "A"] = 120.0   # +20% in 2020
    prices.loc["2020-06-01":, "B"] = 90.0    # -10% in 2020
    prices.loc["2021-06-01":, "C"] = 130.0   # +30% in 2021
    run, spy = portfolio_run(prices)
    t = year_table(run, spy, {"A": "AAA", "B": "BBB", "C": "CCC"}, None, kind="portfolio", prices=prices)
    # 2020: A gains 10% of the starting value (half of it, +20%), B loses 5%: +5% in all.
    # Nothing is sold in the first year. 2021: everything sold once at the start (100%).
    assert list(t["Holdings"]) == ["2 stocks · 0% turnover · biggest: AAA +10.0, BBB -5.0 pts",
                                   "1 stock · 100% turnover · biggest: CCC +30.0 pts"]
    assert t["Strategy %"].tolist() == pytest.approx([5.0, 30.0])
    contrib = contributions(run, prices)
    assert contrib.loc[2020].sum() == pytest.approx(run.yearly[2020])  # no costs or cash: they add up


def test_portfolio_year_table_marks_holdings_whose_data_ended():
    prices = pd.DataFrame({"A": 100.0, "B": 100.0, "C": 100.0, "SPY": 100.0}, index=CAL)
    prices.loc["2020-06-01":, "B"] = 90.0
    prices.loc["2020-09-01":, "B"] = np.nan  # B's data ends while held: sold at 90, flagged
    run, spy = portfolio_run(prices)
    t = year_table(run, spy, {"A": "AAA", "B": "BBB"}, None, kind="portfolio", prices=prices)
    assert t["Holdings"].iloc[0].startswith("2 stocks · ")
    assert t["Holdings"].iloc[0].endswith("biggest: BBB † -5.0, AAA +0.0 pts · data ended: 1 †")


def test_year_table_marks_picks_that_could_not_be_bought():
    # National City and Wachovia were taken over on 2008-12-31, the formation date: they could
    # be ranked, but had no price the next day, so their share of the money stayed in cash.
    prices = pd.DataFrame({"A": 100.0, "B": 100.0, "SPY": 100.0}, index=CAL)
    prices.loc["2019-12-31":, "B"] = np.nan  # B has no price from the formation date on
    win = backtest_window(CAL, 2020, 2020)
    run = run_strategy("Worst 2", pd.DataFrame({"A": [0.5], "B": [0.5]}, index=win.rebalance), prices, 0, CAL, win)
    spy = run_strategy("SPY", pd.DataFrame({"SPY": [1.0]}, index=win.rebalance), prices, 0, CAL, win)
    t = year_table(run, spy, {"A": "AAA", "B": "BBB"}, None)
    assert list(t["Holdings"]) == ["AAA, BBB (not bought)"]
