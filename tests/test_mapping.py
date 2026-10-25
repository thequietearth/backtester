"""Tests for the ticker -> security mapping in bt.data, with tiny made-up prices."""
import numpy as np
import pandas as pd

from bt.data import apply_overrides, assess_candidate, choose_security, follow_renames

CAL = pd.bdate_range("2000-01-03", "2000-12-29")  # trading calendar
AS_OF = CAL[-1]


def prices(start, end, close=50.0, volume=1_000_000):
    """Made-up daily prices from start to end (inclusive) on the calendar."""
    d = CAL[(CAL >= start) & (CAL <= end)]
    return pd.DataFrame({"date": d, "close": close, "adjusted_close": close, "volume": float(volume)})


SPELL = {"ticker": "WEN", "start": pd.Timestamp("2000-01-03"), "end": pd.Timestamp("2000-06-01")}


def assess(p, spell=SPELL):
    return assess_candidate(spell["start"], spell["end"], p, CAL, AS_OF)


def test_assess_candidate_measures_coverage_end_match_and_size():
    a = assess(prices("2000-01-03", "2000-05-31"))
    assert a["coverage"] == 1.0
    assert a["end_match"]  # data stops when the stock left the index
    assert a["dollar_volume"] == 50_000_000  # 50 x 1,000,000 a day
    late = assess(prices("2000-03-01", "2000-12-29"))
    assert 0.3 < late["coverage"] < 0.7 and not late["end_match"]


def test_prefers_the_code_whose_data_ends_when_membership_ends():
    # WEN today (a different company, still trading) vs WEN_old (the member, delisted when it left).
    a = {"WEN": assess(prices("2000-01-03", "2000-12-29")),
         "WEN_old": assess(prices("2000-01-03", "2000-05-31"))}
    code, status, flags = choose_security(a, multi_spell=False)
    assert (code, status, flags) == ("WEN_old", "auto", [])


def test_end_match_beats_full_coverage_even_when_history_is_truncated():
    # Real case: EODHD's WEN_old (Wendy's International) only starts at end-1997, while
    # today's WEN (a different company) covers the whole spell. The end match decides.
    a = {"WEN": assess(prices("2000-01-03", "2000-12-29")),
         "WEN_old": assess(prices("2000-02-15", "2000-05-31"))}
    code, status, flags = choose_security(a, multi_spell=False)
    assert code == "WEN_old" and status == "review" and flags == ["partial"]


def test_prefers_the_bigger_company_when_end_dates_dont_decide():
    a = {"EP": assess(prices("2000-01-03", "2000-12-29", close=0.05, volume=100_000)),
         "EP_old": assess(prices("2000-01-03", "2000-12-29"))}
    code, status, flags = choose_security(a, multi_spell=False)
    assert code == "EP_old" and status == "review" and "ambiguous" in flags


def test_flags_a_candidate_too_small_to_be_an_sp500_member():
    # SNT today is Senstar, a micro-cap; Sonat itself isn't in EODHD.
    a = {"SNT": assess(prices("2000-01-03", "2000-12-29", close=3.0, volume=20_000))}
    code, status, flags = choose_security(a, multi_spell=False)
    assert code == "SNT" and status == "review" and "small" in flags


def test_partial_coverage_and_reused_tickers_go_to_review():
    code, status, flags = choose_security({"X": assess(prices("2000-03-01", "2000-05-31"))}, multi_spell=False)
    assert code == "X" and status == "review" and "partial" in flags
    code, status, flags = choose_security({"AN": assess(prices("2000-01-03", "2000-12-29"))}, multi_spell=True)
    assert status == "review" and "multi_spell" in flags


def test_no_candidates_means_missing():
    assert choose_security({}, multi_spell=False) == (None, "missing", [])
    no_data = {"X": assess(prices("2000-08-01", "2000-12-29"))}  # no data during the spell at all
    assert choose_security(no_data, multi_spell=False)[1] == "missing"


def test_manual_overrides_win_and_blank_code_means_missing():
    spells = pd.DataFrame([
        {"ticker": "AN", "start": pd.Timestamp("1996-01-02"), "end": pd.Timestamp("1999-01-04"),
         "code": "AN", "status": "review", "flags": "multi_spell"},
        {"ticker": "AN", "start": pd.Timestamp("2003-02-24"), "end": pd.NaT,
         "code": "AN", "status": "review", "flags": "multi_spell"},
    ])
    overrides = pd.DataFrame([
        {"ticker": "AN", "start": "1996-01-02", "end": "1999-01-04", "code": None, "note": "Amoco: not in EODHD"},
        {"ticker": "AN", "start": "2003-02-24", "end": None, "code": "AN", "note": "AutoNation"},
    ])
    out = apply_overrides(spells, overrides)
    assert out.loc[0, "status"] == "manual" and pd.isna(out.loc[0, "code"])
    assert out.loc[1, "status"] == "manual" and out.loc[1, "code"] == "AN"


def test_override_can_split_a_spell_where_the_company_behind_the_ticker_changed():
    # Real case: IR was Ingersoll-Rand plc (now Trane, TT) until 2 March 2020, then a different company.
    spells = pd.DataFrame([{"ticker": "IR", "start": pd.Timestamp("2010-11-17"), "end": pd.NaT,
                            "code": "IR", "status": "review", "flags": "partial"}])
    overrides = pd.DataFrame([{"ticker": "IR", "start": "2010-11-17", "end": "2020-03-02",
                               "code": "TT", "note": "Ingersoll-Rand plc, renamed Trane"}])
    out = apply_overrides(spells, overrides)
    assert len(out) == 2
    assert (out.loc[0, "start"], out.loc[0, "end"], out.loc[0, "code"], out.loc[0, "status"]) == \
        (pd.Timestamp("2010-11-17"), pd.Timestamp("2020-03-02"), "TT", "manual")
    assert (out.loc[1, "start"], out.loc[1, "code"], out.loc[1, "status"]) == \
        (pd.Timestamp("2020-03-02"), "IR", "review")
    assert pd.isna(out.loc[1, "end"])


# --- Renames: the same company under a new ticker -------------------------------------

RCAL = pd.bdate_range("2008-01-01", "2016-12-30")
RENAME = pd.Timestamp("2015-07-01")  # OLD leaves the index and NEW joins on this day


def walk(seed, start="2008-01-01", end="2016-12-30", scale=1.0):
    """A made-up company's adjusted prices: a random walk on the calendar."""
    d = RCAL[(RCAL >= start) & (RCAL <= end)]
    steps = np.random.default_rng(seed).normal(0.0003, 0.015, len(RCAL))
    level = 50 * np.exp(np.cumsum(steps))[RCAL.isin(d)] * scale
    return pd.Series(level, index=d)


def frame(adjusted: pd.Series, traded: pd.Series | None = None) -> pd.DataFrame:
    traded = adjusted if traded is None else traded.reindex(adjusted.index)
    return pd.DataFrame({"date": adjusted.index, "close": traded.values, "adjusted_close": adjusted.values,
                         "volume": 1e6})


def rename_spells(old_start="2010-01-04"):
    return pd.DataFrame({"ticker": ["OLD", "NEW"], "start": [pd.Timestamp(old_start), RENAME],
                         "end": [RENAME, pd.NaT], "code": ["OLDX", "NEWX"], "status": "auto", "flags": ""})


def follow(old: pd.Series, new: pd.Series, spells=None, new_traded=None):
    eods = {"OLDX": frame(old), "NEWX": frame(new, new_traded)}
    return follow_renames(rename_spells() if spells is None else spells, eods.get)


def test_a_renamed_member_follows_the_code_that_carries_on():
    # EODHD keeps the whole history under the new ticker (META since 2012) and a stub under
    # the old one that stops at the rename (FB_old). Holding the stub would look like
    # "data ended" for a company that carried on. The new code's adjusted prices sit at a
    # different level (later dividends), but the daily returns are the same.
    company = walk(1)
    out = follow(company.loc[:"2015-06-30"], 0.9 * company, new_traded=company)
    old = out[out.ticker == "OLD"]
    assert len(old) == 1 and old.code.iloc[0] == "NEWX" and "renamed" in old["flags"].iloc[0]
    assert out[out.ticker == "NEW"].code.tolist() == ["NEWX"]


def test_a_rename_is_not_followed_into_history_the_old_code_lacks():
    # The old code starts in June 2010 (EODHD truncates some histories); the new code has
    # earlier prices that may be another company's. Decisions whose 12-month window would
    # reach before June 2010 keep the old code; from 13 months after its start, the new.
    company, other = walk(1), walk(2)
    new = pd.concat([other.loc[:"2010-05-31"], company.loc["2010-06-01":]])
    out = follow(company.loc["2010-06-01":"2015-06-30"], new, rename_spells("2010-09-01"))
    old = out[out.ticker == "OLD"].reset_index(drop=True)
    assert old[["start", "end", "code"]].values.tolist() == [
        [pd.Timestamp("2010-09-01"), pd.Timestamp("2011-07-01"), "OLDX"],
        [pd.Timestamp("2011-07-01"), RENAME, "NEWX"]]


def test_different_prices_mean_a_different_company():
    out = follow(walk(1).loc[:"2015-06-30"], walk(2))
    assert out.code.tolist() == ["NEWX", "OLDX"] and (out["flags"] == "").all()


def test_a_jump_at_the_rename_is_not_followed():
    # Kraft paid a $16.50 special dividend when it became Kraft Heinz, and EODHD's KHC
    # prices don't include it: a fake 19% drop at the rename. Following it would book a fake
    # loss, so the old code (sold at its last price, flagged) stays.
    company = walk(1)
    new = company.where(company.index <= "2015-06-30", company * 0.8)
    out = follow(company.loc[:"2015-06-30"], new)
    assert out[out.ticker == "OLD"].code.tolist() == ["OLDX"]


def test_codes_that_disagree_just_before_the_rename_are_not_followed():
    # DowDuPont's reverse split and Corteva spin-off came three days before it became
    # DuPont: one code shows -17% that day, the other +18%. Agreeing on 98% of days isn't
    # enough when one day leaves a lasting gap between them.
    company = walk(1)
    i = company.index.get_loc(pd.Timestamp("2015-06-25"))
    new = company.copy()
    new.iloc[i:] *= 1.18
    out = follow(company.loc[:"2015-06-30"], new)
    assert out[out.ticker == "OLD"].code.tolist() == ["OLDX"]


def test_a_one_day_glitch_that_reverses_does_not_block_a_rename():
    # Real case: on the day HCP became Healthpeak, EODHD's new code repeats the previous
    # close, then catches up the next day. The codes agree again: still a plain rename.
    company = walk(1)
    new = company.copy()
    i = new.index.get_loc(pd.Timestamp("2015-06-25"))
    new.iloc[i] = new.iloc[i - 1]
    out = follow(company.loc[:"2015-06-30"], new)
    assert out[out.ticker == "OLD"].code.tolist() == ["NEWX"]


def test_a_new_code_rescaled_at_the_rename_is_not_followed():
    # Arconic spun off Arconic Corp the day it became Howmet. EODHD rescaled Howmet's whole
    # history by its estimate of the spin-off's value, so on the old code's last day the two
    # codes show different traded prices (12.32 vs 16.06). That isn't a plain rename: the
    # old code, sold at its last (pre-spin-off) price, is closer to what holders got.
    company = walk(1)
    out = follow(company.loc[:"2015-06-30"], 0.77 * company)
    assert out[out.ticker == "OLD"].code.tolist() == ["OLDX"]


def test_only_a_code_that_stops_at_the_rename_is_replaced():
    company = walk(1)
    out = follow(company, company)  # the old code keeps trading: nothing to fix
    assert out[out.ticker == "OLD"].code.tolist() == ["OLDX"]
