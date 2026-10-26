"""Strategy and universe tests on tiny made-up prices.

Formation period for the 2021 decision: close of 2019-12-31 to close of 2020-12-31.
Made-up returns over it: A +50%, B +20%, C +80%, D +80% (a tie with C), E +200% (E is
not in the universe, so it must never be picked).
"""
import numpy as np
import pandas as pd
import pytest

from bt.coverage import RANKABLE, coverage_by_year, load_crash_review, rankable_universe
from bt.engine import run_backtest
from bt.strategies import (bottom_n, low_volatility, momentum, momentum_scores, rsi, rsi2_positions, spy_buy_and_hold,
                           spy_golden_cross, spy_rsi2, spy_trend, top_n, volatility_scores)
from bt.universe import members_on, month_end, month_ends, naive_constituents, naive_security_map

DAYS = pd.bdate_range("2019-12-02", "2021-01-29")
F_START, F_DATE = pd.Timestamp("2019-12-31"), pd.Timestamp("2020-12-31")
GAIN = {"A": 1.5, "B": 1.2, "C": 1.8, "D": 1.8, "E": 3.0, "SPY": 1.1}


def make_prices():
    # A 0.1% daily wiggle: real closes change almost every day (flat lines fail the
    # frozen-price check). It cancels out over the formation period.
    wiggle = 1 + 0.001 * (-1.0) ** np.arange(len(DAYS))
    p = pd.DataFrame({c: 100.0 * wiggle for c in GAIN}, index=DAYS)
    for c, g in GAIN.items():
        p.loc[p.index > F_START, c] *= g  # jump right after the formation start
    return p


PRICES = make_prices()
UNIVERSE = {F_DATE: ["A", "B", "C", "D"]}


def test_top_n_picks_last_years_best_and_weights_them_equally():
    w = top_n(PRICES, UNIVERSE, [F_DATE], n=2)
    assert w.loc[F_DATE][w.loc[F_DATE] > 0].to_dict() == {"C": 0.5, "D": 0.5}


def test_ties_break_alphabetically_and_top_1_is_top_n_with_n_1():
    w = top_n(PRICES, UNIVERSE, [F_DATE], n=1)
    assert w.loc[F_DATE][w.loc[F_DATE] > 0].to_dict() == {"C": 1.0}


def test_fewer_eligible_than_n_holds_them_all_equally():
    w = top_n(PRICES, UNIVERSE, [F_DATE], n=10)
    assert w.loc[F_DATE][w.loc[F_DATE] > 0].to_dict() == {"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}
    assert w.sum(axis=1).iloc[0] == pytest.approx(1.0)


def test_a_stock_without_a_price_at_the_formation_start_is_not_ranked():
    p = PRICES.copy()
    p.loc[F_START, "C"] = np.nan
    w = top_n(p, UNIVERSE, [F_DATE], n=1)
    assert w.loc[F_DATE][w.loc[F_DATE] > 0].to_dict() == {"D": 1.0}


def test_top_n_decisions_ignore_prices_after_the_decision_date():
    changed = PRICES.copy()
    changed.loc[changed.index > F_DATE] *= np.random.default_rng(0).uniform(0.1, 10, size=(len(changed.loc[changed.index > F_DATE]), changed.shape[1]))
    pd.testing.assert_frame_equal(top_n(PRICES, UNIVERSE, [F_DATE], n=2), top_n(changed, UNIVERSE, [F_DATE], n=2))


def test_spy_buy_and_hold_is_a_single_purchase_at_the_first_date():
    dates = [F_DATE, pd.Timestamp("2021-12-31")]
    w = spy_buy_and_hold(PRICES, UNIVERSE, dates)
    assert list(w.index) == [F_DATE] and w.loc[F_DATE].to_dict() == {"SPY": 1.0}


# --- SPY timing rules (hand-worked on a 10-day path) -------------------------------

PATH_DAYS = pd.bdate_range("2024-01-01", periods=10)
PATH = pd.DataFrame({"SPY": [10, 10, 10, 11, 12, 11, 9, 8, 9, 11]}, index=PATH_DAYS, dtype=float)


def held(w):
    return w["SPY"].astype(int).tolist()


def test_trend_rule_holds_spy_only_above_its_moving_average():
    # 3-day averages from day 2: 10, 10.33, 11, 11.33, 10.67, 9.33, 8.67, 9.33.
    # Above it on days 3 (11 > 10.33), 4 (12 > 11), 8 (9 > 8.67) and 9 (11 > 9.33).
    assert held(spy_trend(PATH, {}, PATH_DAYS, window=3)) == [0, 0, 0, 1, 1, 0, 0, 0, 1, 1]


def test_golden_cross_holds_when_the_fast_average_is_above_the_slow_one():
    # 2-day vs 3-day averages: days 3 (10.5 > 10.33), 4 (11.5 > 11), 5 (11.5 > 11.33), 9 (10 > 9.33).
    assert held(spy_golden_cross(PATH, {}, PATH_DAYS, fast=2, slow=3)) == [0, 0, 0, 1, 1, 1, 0, 0, 0, 1]


def test_rsi_uses_wilders_smoothing():
    # Changes +1, +1, -1, -1, +1. First average (2 days): gain 1, loss 0 -> RSI 100.
    # Then avg = (previous * 1 + today) / 2: gains 0.5, 0.25, 0.625; losses 0.5, 0.75, 0.375.
    r = rsi(pd.Series([10, 11, 12, 11, 10, 11], dtype=float), period=2)
    assert r.isna().tolist()[:2] == [True, True]
    np.testing.assert_allclose(r.iloc[2:].values, [100, 50, 25, 62.5])


def test_rsi2_buys_a_sharp_dip_in_an_uptrend_and_sells_on_the_bounce():
    close = pd.Series([100.0] * 6)
    rsi_v = pd.Series([50, 5, 5, 8, 40, 5])
    trend = pd.Series([90, 90, 90, 90, 90, 110])  # day 5: below the long-term average
    exit_ = pd.Series([105, 105, 105, 99, 105, 105])  # day 3: closes above the short average
    # Day 1 buys (RSI 5 < 10, above trend); held until day 3 closes above its short average.
    # Day 5 has RSI 5 again but is below the trend, so no purchase.
    assert rsi2_positions(close, rsi_v, trend, exit_, entry=10).tolist() == [False, True, True, False, False, False]


def test_timing_rules_pay_costs_only_when_the_signal_flips():
    w = spy_trend(PATH, {}, PATH_DAYS, window=3)
    with pytest.warns(UserWarning, match="no trading day after"):  # the last day's decision can't trade
        trades = run_backtest(w, PATH, cost_bps=10).trades
    # Signal flips in on day 3, out on day 5, in on day 8 -> trades on days 4, 6 and 9 only.
    assert trades.action.tolist() == ["buy", "sell", "buy"]
    assert list(trades.date) == [PATH_DAYS[4], PATH_DAYS[6], PATH_DAYS[9]]


@pytest.mark.parametrize("rule", [spy_trend, spy_golden_cross, spy_rsi2])
def test_timing_rules_ignore_prices_after_the_decision_date(rule):
    rng = np.random.default_rng(3)
    days = pd.bdate_range("2020-01-01", periods=600)
    spy = pd.DataFrame({"SPY": 100 * np.exp(np.cumsum(rng.normal(0.0004, 0.012, len(days))))}, index=days)
    t = days[450]
    changed = spy.copy()
    changed.loc[changed.index > t, "SPY"] *= rng.uniform(0.5, 1.5, (changed.index > t).sum())
    pd.testing.assert_frame_equal(rule(spy, {}, days).loc[:t], rule(changed, {}, days).loc[:t])


# --- Universes ---------------------------------------------------------------------

def test_rankable_universe_needs_formation_data_but_not_an_entry_price():
    # Entry is the day after the decision, so requiring a price then would use tomorrow's data.
    detail = pd.DataFrame({"year": 2021, "code": ["A", "B", "C", "D", "E"],
                           "status": ["ok", "no holding data", "no formation data", "suspect prices", "no security"]})
    assert RANKABLE == {"ok", "no holding data"}
    assert rankable_universe(detail, pd.Series({2021: F_DATE})) == {F_DATE: ["A", "B"]}


def test_point_in_time_universe_ignores_prices_after_the_decision_date():
    cons = pd.DataFrame({"date": pd.Timestamp("2019-12-02"), "ticker": ["A", "B", "C", "D"]})
    smap = pd.DataFrame({"ticker": ["A", "B", "C", "D"], "start": pd.Timestamp("2019-12-02"), "end": pd.NaT,
                         "code": ["A", "B", "C", "D"], "status": "auto", "flags": ""})
    cal = DAYS
    _, d1 = coverage_by_year(cons, smap, PRICES, cal, [2021])
    changed = PRICES.copy()
    changed.loc[changed.index > F_DATE, ["A", "B"]] = np.nan  # e.g. A and B stop trading right after
    _, d2 = coverage_by_year(cons, smap, changed, cal, [2021])
    fd = pd.Series({2021: F_DATE})
    assert rankable_universe(d1, fd) == rankable_universe(d2, fd) == {F_DATE: ["A", "B", "C", "D"]}


def test_naive_universe_uses_todays_members_for_every_year():
    cons = pd.DataFrame({"date": [pd.Timestamp("2000-01-03")] * 2 + [pd.Timestamp("2025-01-02")] * 2,
                         "ticker": ["OLD", "KEEP", "KEEP", "NEW"]})
    naive = naive_constituents(cons)
    assert members_on(naive, "2000-12-29") == members_on(naive, "2024-12-31") == ["KEEP", "NEW"]
    smap = pd.DataFrame({"ticker": ["OLD", "KEEP", "NEW"],
                         "start": pd.to_datetime(["2000-01-03", "2000-01-03", "2025-01-02"]),
                         "end": [pd.Timestamp("2025-01-02"), pd.NaT, pd.NaT],
                         "code": ["OLD", "KEEP", "NEW"], "status": "auto", "flags": ""})
    nmap = naive_security_map(smap, naive)
    assert sorted(nmap.ticker) == ["KEEP", "NEW"]
    assert (nmap.start <= pd.Timestamp("1990-01-01")).all() and nmap.end.isna().all()


# --- Momentum and low volatility (decided at month-ends) ----------------------------

MDAYS = pd.bdate_range("2019-11-01", "2021-02-26")
D = pd.Timestamp("2020-12-31")  # window from the end of Dec 2019; momentum skips Dec 2020


def test_month_end_is_the_last_trading_day_of_an_earlier_month():
    assert month_end(MDAYS, D, 0) == D
    assert month_end(MDAYS, D, 1) == pd.Timestamp("2020-11-30")
    assert month_end(MDAYS, D, 12) == pd.Timestamp("2019-12-31")
    assert month_end(MDAYS, pd.Timestamp("2020-06-30"), 1) == pd.Timestamp("2020-05-29")  # 31 May was a Sunday
    assert month_ends(MDAYS, "2020-10-01", "2020-12-31") == [pd.Timestamp(d) for d in
                                                            ("2020-10-30", "2020-11-30", "2020-12-31")]


def momentum_prices():
    # Returns from the end of Dec 2019 to the end of Nov 2020 (the 12-1 window):
    # A +50%, B +20%, C +40%, D +45%. B then triples in December, the skipped month, so its
    # plain 12-month return is the best - but momentum must ignore it.
    p = pd.DataFrame(100.0, index=MDAYS, columns=list("ABCD"))
    for c, level in {"A": 150.0, "B": 120.0, "C": 140.0, "D": 145.0}.items():
        p.loc["2020-06-01":, c] = level
    p.loc["2020-12-01":, "B"] = 360.0
    return p


def test_momentum_ranks_on_12_months_skipping_the_last_one():
    scores = momentum_scores(momentum_prices(), list("ABCD"), D)
    assert scores.to_dict() == pytest.approx({"A": 0.5, "D": 0.45, "C": 0.4, "B": 0.2})
    assert list(scores.index) == ["A", "D", "C", "B"]  # best first


def test_momentum_holds_the_top_fraction_equally():
    w = momentum(momentum_prices(), {D: list("ABCD")}, [D], fraction=0.5)
    assert w.loc[D][w.loc[D] > 0].to_dict() == {"A": 0.5, "D": 0.5}
    # 10% of 4 stocks rounds up to 1: at least one stock is always held.
    w = momentum(momentum_prices(), {D: list("ABCD")}, [D], fraction=0.1)
    assert w.loc[D][w.loc[D] > 0].to_dict() == {"A": 1.0}


def calm_prices(swings: dict) -> pd.DataFrame:
    """Each stock alternates up and down by exactly its swing (in log terms), so its
    volatility is proportional to the swing."""
    sign = np.where(np.arange(len(MDAYS)) % 2 == 0, 1.0, -1.0)
    return pd.DataFrame({c: 100 * np.exp(np.cumsum(a * sign)) for c, a in swings.items()}, index=MDAYS)


def test_low_volatility_holds_the_calmest_members_equally():
    p = calm_prices({"A": 0.02, "B": 0.01, "C": 0.03, "D": 0.01, "E": 0.001})  # E: not a member
    vol = volatility_scores(p, list("ABCD"), D)
    assert list(vol.index) == ["B", "D", "A", "C"]  # calmest first, ties alphabetical
    assert vol["C"] / vol["B"] == pytest.approx(3.0)
    assert vol["B"] == pytest.approx(0.01 * np.sqrt(252), rel=0.01)  # annualised
    w = low_volatility(p, {D: list("ABCD")}, [D], n=3)
    assert w.loc[D][w.loc[D] > 0].to_dict() == pytest.approx({"A": 1 / 3, "B": 1 / 3, "D": 1 / 3})


def test_low_volatility_can_weight_by_inverse_volatility():
    # The S&P 500 Low Volatility Index (SPLV) weights each stock by 1 / its volatility:
    # a stock half as volatile gets twice the weight.
    p = calm_prices({"A": 0.02, "B": 0.01, "C": 0.03})
    w = low_volatility(p, {D: list("ABC")}, [D], n=2, weighting="inverse volatility")
    assert w.loc[D][w.loc[D] > 0].to_dict() == pytest.approx({"A": 1 / 3, "B": 2 / 3})


def nonzero(w):
    return w.loc[:, (w != 0).any()].sort_index(axis=1)


@pytest.mark.parametrize("strategy, params", [(momentum, {"fraction": 0.2}), (low_volatility, {"n": 5})])
def test_monthly_strategies_ignore_prices_after_the_decision_date(strategy, params):
    rng = np.random.default_rng(5)
    days = pd.bdate_range("2018-01-01", "2020-12-31")
    codes = [f"S{i:02d}" for i in range(30)]
    steps = rng.normal(0.0003, 1.0, (len(days), 30)) * rng.uniform(0.005, 0.03, 30)
    prices = pd.DataFrame(100 * np.exp(np.cumsum(steps, axis=0)), index=days, columns=codes)
    dates = month_ends(days, "2019-01-01", "2020-12-31")
    universe = {d: codes for d in dates}
    t = dates[10]
    changed = prices.copy()
    after = changed.index > t
    changed.loc[after] *= rng.uniform(0.5, 1.5, (after.sum(), 30))
    a, b = strategy(prices, universe, dates, **params), strategy(changed, universe, dates, **params)
    pd.testing.assert_frame_equal(nonzero(a.loc[:t]), nonzero(b.loc[:t]))
    assert not nonzero(a.loc[t:].iloc[1:]).equals(nonzero(b.loc[t:].iloc[1:]))  # later decisions changed


# --- Last year's worst N (contrarian) -------------------------------------------------

def test_bottom_n_picks_last_years_worst_and_breaks_ties_alphabetically():
    # Returns: B +20%, A +50%, C and D +80% (a tie), E +200% but not in the universe.
    w = bottom_n(PRICES, UNIVERSE, [F_DATE], n=3)
    assert w.loc[F_DATE][w.loc[F_DATE] > 0].to_dict() == pytest.approx({"B": 1 / 3, "A": 1 / 3, "C": 1 / 3})


def test_bottom_n_decisions_ignore_prices_after_the_decision_date():
    changed = PRICES.copy()
    after = changed.index > F_DATE
    changed.loc[after] *= np.random.default_rng(1).uniform(0.1, 10, size=(after.sum(), changed.shape[1]))
    pd.testing.assert_frame_equal(bottom_n(PRICES, UNIVERSE, [F_DATE], n=2), bottom_n(changed, UNIVERSE, [F_DATE], n=2))


def test_a_reviewed_real_crash_may_be_ranked_but_identity_problems_never():
    # The price checks set aside real crashes along with broken data. A hand review
    # (data/crash_review.csv) marks the real ones, which the contrarian ranking may use.
    detail = pd.DataFrame({"year": 2021, "code": ["A", "B", "C", "D"],
                           "status": ["ok", "suspect prices", "suspect identity", "suspect prices"]})
    fd = pd.Series({2021: F_DATE})
    assert rankable_universe(detail, fd) == {F_DATE: ["A"]}
    real = {(2021, "B"), (2021, "C")}
    assert rankable_universe(detail, fd, real_crashes=real) == {F_DATE: ["A", "B"]}


def test_crash_review_file_only_accepts_real_or_broken(tmp_path):
    path = tmp_path / "crash_review.csv"
    path.write_text("year,ticker,code,verdict,note\n2009,AIG,AIG,real,bailout\n2004,GDW,GDW,broken,another instrument\n")
    assert load_crash_review(path) == {(2009, "AIG")}
    path.write_text("year,ticker,code,verdict,note\n2009,AIG,AIG,maybe,?\n")
    with pytest.raises(ValueError, match="verdict"):
        load_crash_review(path)
