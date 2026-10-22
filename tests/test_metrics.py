"""Metric tests on equity curves simple enough to work out by hand."""
import numpy as np
import pandas as pd
import pytest

from bt.metrics import (annual_volatility, beat_rate, best_and_worst_year, cagr, drawdown_series,
                        holding_period_returns, max_drawdown, sharpe_ratio, yearly_returns)


def curve(values, dates):
    return pd.Series(values, index=pd.to_datetime(dates), dtype=float)


def test_cagr_doubling_in_two_years_is_about_41_percent():
    eq = curve([100, 200], ["2020-01-01", "2022-01-01"])  # 731 days = 2.0014 years
    assert cagr(eq) == pytest.approx(2 ** (365.25 / 731) - 1)
    assert cagr(eq) == pytest.approx(0.4142, abs=1e-3)


def test_volatility_and_sharpe_on_alternating_returns():
    # Daily returns alternate +1%, -1%; expected values use the textbook formulas directly.
    eq = pd.Series(100 * np.cumprod([1, 1.01, 0.99, 1.01, 0.99, 1.01]), index=pd.bdate_range("2024-01-01", periods=6))
    r = eq.pct_change().dropna()
    assert annual_volatility(eq) == pytest.approx(r.std(ddof=1) * np.sqrt(252))
    assert sharpe_ratio(eq) == pytest.approx(r.mean() / r.std(ddof=1) * np.sqrt(252))


def test_sharpe_subtracts_the_risk_free_return_each_day():
    eq = pd.Series(100 * np.cumprod([1, 1.01, 0.99, 1.01, 0.99, 1.01]), index=pd.bdate_range("2024-01-01", periods=6))
    rf = pd.Series(0.0001, index=eq.index)  # about 2.5% a year
    excess = eq.pct_change().dropna() - 0.0001
    assert sharpe_ratio(eq, rf) == pytest.approx(excess.mean() / excess.std(ddof=1) * np.sqrt(252))
    assert sharpe_ratio(eq, rf) < sharpe_ratio(eq)  # a positive risk-free rate lowers Sharpe


def test_flat_curve_has_zero_volatility_and_no_sharpe():
    eq = pd.Series(1.0, index=pd.bdate_range("2024-01-01", periods=5))
    assert annual_volatility(eq) == 0.0
    assert np.isnan(sharpe_ratio(eq))  # undefined: no risk taken


def test_max_drawdown_depth_dates_and_length():
    eq = curve([100, 120, 90, 100, 130], ["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01", "2024-05-01"])
    dd = max_drawdown(eq)
    assert dd["depth"] == pytest.approx(-0.25)  # 120 -> 90
    assert (dd["peak"], dd["trough"], dd["recovery"]) == tuple(pd.to_datetime(["2024-02-01", "2024-03-01", "2024-05-01"]))
    assert dd["days"] == 90  # 1 Feb to 1 May, calendar days


def test_unrecovered_drawdown_has_no_recovery_and_runs_to_the_end():
    eq = curve([100, 80, 90], ["2024-01-01", "2024-01-11", "2024-01-21"])
    dd = max_drawdown(eq)
    assert dd["depth"] == pytest.approx(-0.2) and dd["recovery"] is None and dd["days"] == 20


def test_drawdown_series():
    eq = curve([100, 120, 90, 130], ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"])
    np.testing.assert_allclose(drawdown_series(eq).values, [0, 0, -0.25, 0])


def test_yearly_returns_use_the_previous_year_end_and_a_partial_first_year():
    eq = curve([100, 110, 121, 108.9], ["2020-06-01", "2020-12-31", "2021-12-31", "2022-12-30"])
    yr = yearly_returns(eq)
    np.testing.assert_allclose(yr.values, [0.10, 0.10, -0.10])  # 2020 is from the start (1 Jun)
    assert list(yr.index) == [2020, 2021, 2022]
    assert best_and_worst_year(eq) == ((2020, pytest.approx(0.10)), (2022, pytest.approx(-0.10)))


def test_holding_period_returns_run_from_one_rebalance_to_the_next():
    # Rebalances (trades) on 2 Jan 2020 and 4 Jan 2021; the curve ends 4 Jan 2022.
    eq = curve([100, 104, 110, 99, 132], ["2020-01-02", "2020-12-31", "2021-01-04", "2021-12-31", "2022-01-04"])
    r = holding_period_returns(eq, pd.to_datetime(["2020-01-02", "2021-01-04", "2022-01-04"]))
    assert list(r.index) == [2020, 2021]  # labelled by the year the holding started
    np.testing.assert_allclose(r.values, [110 / 100 - 1, 132 / 110 - 1])


def test_beat_rate_counts_only_years_both_have():
    strat = pd.Series({2020: 0.10, 2021: -0.05, 2022: 0.20, 2023: 0.30})
    bench = pd.Series({2021: 0.02, 2022: 0.10, 2023: 0.40})
    assert beat_rate(strat, bench) == pytest.approx(1 / 3)  # only 2022 of 2021-2023
