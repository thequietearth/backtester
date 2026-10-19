"""Tests for the ticker -> security mapping in bt.data, with tiny made-up prices."""
import pandas as pd

from bt.data import apply_overrides, assess_candidate, choose_security

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
