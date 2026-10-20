"""Strategy and universe tests on tiny made-up prices.

Formation period for the 2021 decision: close of 2019-12-31 to close of 2020-12-31.
Made-up returns over it: A +50%, B +20%, C +80%, D +80% (a tie with C), E +200% (E is
not in the universe, so it must never be picked).
"""
import numpy as np
import pandas as pd
import pytest

from bt.coverage import RANKABLE, coverage_by_year, rankable_universe
from bt.strategies import spy_buy_and_hold, top_n
from bt.universe import members_on, naive_constituents, naive_security_map

DAYS = pd.bdate_range("2019-12-02", "2021-01-29")
F_START, F_DATE = pd.Timestamp("2019-12-31"), pd.Timestamp("2020-12-31")
GAIN = {"A": 1.5, "B": 1.2, "C": 1.8, "D": 1.8, "E": 3.0, "SPY": 1.1}


def make_prices():
    p = pd.DataFrame(100.0, index=DAYS, columns=list(GAIN))
    for c, g in GAIN.items():
        p.loc[p.index > F_START, c] = 100.0 * g  # jump right after the formation start, then flat
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
