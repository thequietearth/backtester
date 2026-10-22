"""Tests for bt.data: parsing, candidate rules and request safety. No network."""
import pandas as pd
import pytest

from bt.data import (EODHDError, apply_price_exclusions, call_budget, candidate_codes, cash_returns, get_json,
                     index_codes, load_tbill, parse_dividends, parse_eod, parse_splits, split_payload)

KEY = "SECRET-KEY-123"


def test_parse_eod_sorts_and_types():
    df = parse_eod([
        {"date": "2024-01-03", "open": 2, "high": 3, "low": 1, "close": 2.5, "adjusted_close": 2.4, "volume": 100},
        {"date": "2024-01-02", "open": 1, "high": 2, "low": 1, "close": 1.5, "adjusted_close": 1.4, "volume": None},
    ])
    assert list(df.date) == [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03")]
    assert df.adjusted_close.tolist() == [1.4, 2.4]
    assert pd.isna(df.volume[0])


def test_parse_eod_empty_keeps_columns():
    df = parse_eod([])
    assert df.empty and list(df.columns) == ["date", "open", "high", "low", "close", "adjusted_close", "volume"]


def test_parse_dividends():
    df = parse_dividends([{"date": "2024-02-09", "declarationDate": "2024-02-01", "value": 0.24,
                           "unadjustedValue": 0.48, "currency": "USD"}])
    assert list(df.columns) == ["date", "value", "unadjusted_value", "currency"]
    assert df.value[0] == 0.24 and df.unadjusted_value[0] == 0.48


def test_parse_splits_ratio():
    df = parse_splits([{"date": "2020-08-31", "split": "4.000000/1.000000"},
                       {"date": "2010-05-03", "split": "1.000000/10.000000"}])  # reverse split
    assert df.ratio.tolist() == [0.1, 4.0]  # sorted by date


def test_call_budget():
    assert call_budget(100_000, 4_000, None) == 96_000  # no cap: whatever is left today
    assert call_budget(100_000, 4_000, 500) == 500
    assert call_budget(100_000, 4_000, 0) == 0  # dry run must make no calls
    assert call_budget(20, 25, None) == 0  # never negative


def test_price_exclusions_blank_known_bad_dates_only():
    eod = parse_eod([{"date": d, "close": 10.0, "adjusted_close": 9.0, "volume": 1}
                     for d in ["2001-01-26", "2001-01-29", "2001-01-30", "2002-06-03"]])
    # Real case: Coastal (CGP) was bought on 2001-01-29; later prices are another instrument.
    out = apply_price_exclusions(eod, [(pd.Timestamp("2001-01-30"), None)])
    assert out.adjusted_close.notna().tolist() == [True, True, False, False]
    assert out.close.notna().tolist() == [True, True, False, False]
    assert out.volume.notna().all()  # only prices are blanked
    bounded = apply_price_exclusions(eod, [(pd.Timestamp("2001-01-29"), pd.Timestamp("2001-01-30"))])
    assert bounded.adjusted_close.notna().tolist() == [True, False, False, True]


def test_load_tbill_reads_fred_csv_as_yearly_decimal_rates(tmp_path):
    p = tmp_path / "dtb3.csv"
    p.write_text("observation_date,DTB3\n2024-01-02,5.25\n2024-01-03,\n2024-01-04,5.10\n")
    rate = load_tbill(p)
    assert rate.tolist()[0] == pytest.approx(0.0525) and rate.tolist()[2] == pytest.approx(0.051)
    assert pd.isna(rate.iloc[1])  # a holiday: left empty, filled with the day before when used


def test_cash_returns_accrue_calendar_days_at_the_previous_days_rate():
    cal = pd.to_datetime(["2024-01-04", "2024-01-05", "2024-01-08"])  # Thu, Fri, Mon
    rate = pd.Series([0.0365, 0.0730], index=pd.to_datetime(["2024-01-04", "2024-01-05"]))
    r = cash_returns(cal, rate)
    assert r.iloc[0] == 0.0
    assert r.iloc[1] == pytest.approx(1.0365 ** (1 / 365) - 1)  # Thu's rate, 1 day
    assert r.iloc[2] == pytest.approx(1.0730 ** (3 / 365) - 1)  # Fri's rate, 3 days (weekend)


def test_split_payload_separates_warnings_from_data():
    # EODHD answers a free-plan request for old data with a warning inside the list.
    records, warnings = split_payload([{"date": "2024-01-02", "close": 1.0},
                                       {"warning": "Data is limited by one year"}])
    assert records == [{"date": "2024-01-02", "close": 1.0}]
    assert warnings == ["Data is limited by one year"]
    assert parse_eod(split_payload([{"warning": "x"}])[0]).empty  # warning alone is not a price row


def test_split_payload_rejects_non_list():
    with pytest.raises(ValueError):
        split_payload({"message": "something unexpected"})


def test_candidate_codes_include_reused_ticker_variants():
    index = index_codes(["WEN", "WEN_old", "WENX", "EP", "EP_old", "SGP_old1", "HLT1", "BRK-B", "AN"])
    assert candidate_codes("WEN", index) == ["WEN", "WEN_old"]
    assert candidate_codes("EP", index) == ["EP", "EP_old"]
    assert candidate_codes("SGP", index) == ["SGP_old1"]
    assert candidate_codes("HLT", index) == ["HLT1"]
    assert candidate_codes("BRK.B", index) == ["BRK-B"]
    assert candidate_codes("LEHMQ", index) == []


class FakeResponse:
    def __init__(self, status, payload=None, text=""):
        self.status_code, self._payload, self.text = status, payload, text

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), 0

    def get(self, url, params=None, timeout=None):
        self.calls += 1
        return self.responses.pop(0)


def test_get_json_retries_on_rate_limit_then_succeeds():
    session = FakeSession([FakeResponse(429, text="Too many"), FakeResponse(200, [{"x": 1}])])
    waits = []
    assert get_json("eod/AAPL.US", KEY, session=session, sleep=waits.append) == [{"x": 1}]
    assert session.calls == 2 and waits == [5]


def test_get_json_error_never_contains_the_key():
    session = FakeSession([FakeResponse(401, text="Unauthenticated")])
    with pytest.raises(EODHDError) as exc:
        get_json("eod/AAPL.US", KEY, session=session, sleep=lambda s: None)
    assert exc.value.status == 401
    assert KEY not in str(exc.value)
