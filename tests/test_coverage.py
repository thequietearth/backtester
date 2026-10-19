"""Tests for bt.coverage: one made-up backtest year (2001), worked out by hand.

Formation period: close of 1999-12-31 to close of 2000-12-29. Entry: 2001-01-02.
Holding period ends at the first trading day of 2002.
"""
import numpy as np
import pandas as pd

from bt.coverage import band, coverage_by_year

CAL = pd.bdate_range("1999-12-01", "2002-01-31")
CONS = pd.DataFrame({"date": pd.Timestamp("2000-01-03"),
                     "ticker": ["AAA", "BBB", "CCC", "DDD", "EEE"]})
SMAP = pd.DataFrame({
    "ticker": ["AAA", "BBB", "CCC", "DDD", "EEE"],
    "start": pd.Timestamp("2000-01-03"), "end": pd.NaT,
    "code": ["AAA", "BBB", "CCC", "DDD", None],
    "status": ["auto", "auto", "auto", "review", "missing"],
    "flags": ["", "", "", "partial", ""],
})


def series(start=None, end=None):
    s = pd.Series(100.0, index=CAL)
    if start:
        s[s.index < start] = np.nan
    if end:
        s[s.index > end] = np.nan
    return s


PRICES = pd.DataFrame({
    "AAA": series(),                     # full data: covered
    "BBB": series(start="2000-03-01"),   # no price at formation start: can't be ranked
    "CCC": series(end="2000-12-29"),     # no price at entry: can't be held
    "DDD": series(end="2001-06-29"),     # covered, but data ends mid-year: flagged
})                                       # EEE: no security mapped at all


def test_coverage_by_year_worked_example():
    summary, detail = coverage_by_year(CONS, SMAP, PRICES, CAL, [2001])
    row = summary.iloc[0]
    assert row.formation_date == pd.Timestamp("2000-12-29")
    assert (row.members, row.formation_ok, row.holding_ok, row.covered) == (5, 3, 3, 2)
    assert row.coverage_pct == 40.0
    assert row.ended_mid_year == 1 and row.flagged == 1
    assert row.band == "unreliable"
    status = detail.set_index("ticker")["status"].to_dict()
    assert status == {"AAA": "ok", "BBB": "no formation data", "CCC": "no holding data",
                      "DDD": "ok", "EEE": "no security"}
    assert detail.set_index("ticker").loc["DDD", "ended_mid_year"]


def test_a_price_jump_in_the_formation_year_makes_a_member_suspect():
    # A one-day spike to 3x and back (a bad print) would make a fake "best stock of the year".
    spike = series()
    spike[pd.Timestamp("2000-06-15")] = 300.0
    cons = CONS[CONS.ticker == "AAA"].assign(ticker="FFF")
    smap = SMAP[SMAP.ticker == "AAA"].assign(ticker="FFF", code="FFF")
    summary, detail = coverage_by_year(cons, smap, pd.DataFrame({"FFF": spike}), CAL, [2001])
    assert detail.status.tolist() == ["suspect prices"]
    assert summary.covered[0] == 0 and summary.suspect[0] == 1


def test_a_jump_in_the_holding_year_is_flagged_but_still_covered():
    # A real crash while held (e.g. Lehman, -94% in a day) must stay in the results.
    crash = series()
    crash[crash.index >= pd.Timestamp("2001-09-17")] = 6.0
    cons = CONS[CONS.ticker == "AAA"]
    summary, detail = coverage_by_year(cons, SMAP[SMAP.ticker == "AAA"], pd.DataFrame({"AAA": crash}), CAL, [2001])
    assert detail.status.tolist() == ["ok"] and bool(detail.holding_jump[0])
    assert summary.covered[0] == 1


def test_adjusted_price_moving_while_traded_price_doesnt_is_suspect():
    # Real case: Safeway's 1998 split was applied twice - the adjusted price doubled on the
    # split date while the traded price didn't move.
    adj = series()
    adj[adj.index >= pd.Timestamp("2000-02-28")] = 200.0
    raw = series()
    cons = CONS[CONS.ticker == "AAA"]
    smap = SMAP[SMAP.ticker == "AAA"]
    summary, detail = coverage_by_year(cons, smap, pd.DataFrame({"AAA": adj}), CAL, [2001],
                                       raw_prices=pd.DataFrame({"AAA": raw}))
    assert detail.status.tolist() == ["suspect prices"]


def test_adjusted_return_far_from_traded_return_is_suspect_but_splits_are_explained():
    # Real case: Deluxe's adjusted price rose +189% over 2001 while its traded price rose ~70%,
    # with no split: the adjustment drifted (a mishandled spin-off). A gap over 30% is suspect.
    days = PRICES.index
    adj = pd.Series(np.linspace(100, 290, len(days)), index=days)
    raw = pd.Series(np.linspace(100, 170, len(days)), index=days)
    cons, smap = CONS[CONS.ticker == "AAA"], SMAP[SMAP.ticker == "AAA"]
    _, detail = coverage_by_year(cons, smap, pd.DataFrame({"AAA": adj}), CAL, [2001],
                                 raw_prices=pd.DataFrame({"AAA": raw}))
    assert detail.status.tolist() == ["suspect prices"]
    # A 2-for-1 split: the traded price halves, the split factor doubles, nothing is suspect.
    flat = pd.Series(100.0, index=days)
    raw_split = flat.where(days < pd.Timestamp("2000-06-01"), 50.0)
    factor = pd.Series(1.0, index=days).where(days < pd.Timestamp("2000-06-01"), 2.0)
    _, detail = coverage_by_year(cons, smap, pd.DataFrame({"AAA": flat}), CAL, [2001],
                                 raw_prices=pd.DataFrame({"AAA": raw_split}),
                                 split_factors=pd.DataFrame({"AAA": factor}))
    assert detail.status.tolist() == ["ok"]


def test_split_counted_twice_is_caught_even_when_split_factors_are_supplied():
    # Real case: Safeway's "traded" price from EODHD was already split-adjusted, and the split
    # was applied again to the adjusted price. Split factors must not hide that.
    adj = series()
    adj[adj.index >= pd.Timestamp("2000-02-28")] = 200.0
    factor = pd.Series(1.0, index=CAL).where(CAL < pd.Timestamp("2000-02-28"), 2.0)
    cons, smap = CONS[CONS.ticker == "AAA"], SMAP[SMAP.ticker == "AAA"]
    _, detail = coverage_by_year(cons, smap, pd.DataFrame({"AAA": adj}), CAL, [2001],
                                 raw_prices=pd.DataFrame({"AAA": series()}),
                                 split_factors=pd.DataFrame({"AAA": factor}))
    assert detail.status.tolist() == ["suspect prices"]


def test_a_long_hole_in_the_formation_year_is_suspect():
    # Real case: EODHD's L Brands series has no prices from mid-November to 19 Dec 2011,
    # and a +84% jump across the hole.
    holed = series()
    holed[(holed.index > pd.Timestamp("2000-10-02")) & (holed.index < pd.Timestamp("2000-11-01"))] = np.nan
    cons, smap = CONS[CONS.ticker == "AAA"], SMAP[SMAP.ticker == "AAA"]
    _, detail = coverage_by_year(cons, smap, pd.DataFrame({"AAA": holed}), CAL, [2001])
    assert detail.status.tolist() == ["suspect prices"]


def test_small_flag_means_suspect_identity_unless_confirmed_by_hand():
    smap = SMAP.copy()
    smap.loc[smap.ticker == "AAA", ["status", "flags"]] = ["review", "small"]
    _, detail = coverage_by_year(CONS, smap, PRICES, CAL, [2001])
    assert detail.set_index("ticker").loc["AAA", "status"] == "suspect identity"
    smap.loc[smap.ticker == "AAA", "status"] = "manual"  # checked by hand: keep it
    _, detail = coverage_by_year(CONS, smap, PRICES, CAL, [2001])
    assert detail.set_index("ticker").loc["AAA", "status"] == "ok"


def test_bands():
    assert band(96.2) == "trusted"
    assert band(95.0) == "trusted"
    assert band(88.0) == "lower coverage"
    assert band(84.9) == "unreliable"
