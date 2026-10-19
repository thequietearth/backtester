"""Tests for bt.universe with tiny made-up membership data."""
import pandas as pd
import pytest

from bt.universe import formation_dates, members_on, membership_spells


def snapshots(rows):
    """{date: [tickers]} -> long DataFrame(date, ticker), like data/constituents.parquet."""
    return pd.DataFrame([(pd.Timestamp(d), t) for d, ts in rows.items() for t in ts],
                        columns=["date", "ticker"])


CONS = snapshots({
    "2000-01-03": ["AAA", "BBB", "CCC"],
    "2000-06-15": ["AAA", "BBB", "DDD"],  # CCC out, DDD in
    "2001-03-01": ["AAA", "CCC", "DDD"],  # BBB out, CCC back in
})


def test_members_on_uses_last_snapshot_on_or_before_date():
    assert members_on(CONS, "2000-06-14") == ["AAA", "BBB", "CCC"]
    assert members_on(CONS, "2000-06-15") == ["AAA", "BBB", "DDD"]  # change counts from its own date
    assert members_on(CONS, "2000-12-29") == ["AAA", "BBB", "DDD"]


def test_members_on_before_first_snapshot_uses_first_snapshot():
    # fja05680 starts 1996-01-02, so the end-1995 formation date falls back to it.
    assert members_on(CONS, "1999-12-31") == ["AAA", "BBB", "CCC"]


def test_membership_spells_handles_leaving_and_rejoining():
    spells = membership_spells(CONS)
    ccc = spells[spells.ticker == "CCC"].reset_index(drop=True)
    assert list(ccc.start) == [pd.Timestamp("2000-01-03"), pd.Timestamp("2001-03-01")]
    assert ccc.end[0] == pd.Timestamp("2000-06-15")  # end is exclusive: first snapshot without it
    assert pd.isna(ccc.end[1])  # still a member
    bbb = spells[spells.ticker == "BBB"]
    assert list(bbb.start) == [pd.Timestamp("2000-01-03")]
    assert list(bbb.end) == [pd.Timestamp("2001-03-01")]
    assert len(spells) == 5  # AAA, BBB, CCC x2, DDD


def test_formation_dates_are_last_trading_day_of_previous_year():
    # 30-31 Dec 2000 was a weekend, so the last trading day of 2000 is Friday 29 Dec.
    cal = pd.bdate_range("1999-12-01", "2001-01-31")
    fd = formation_dates(cal, [2000, 2001])
    assert fd[2000] == pd.Timestamp("1999-12-31")
    assert fd[2001] == pd.Timestamp("2000-12-29")


def test_formation_dates_refuses_to_guess_without_calendar_data():
    cal = pd.bdate_range("2000-01-03", "2000-12-29")
    with pytest.raises(ValueError):
        formation_dates(cal, [2000])  # the calendar has no 1999 trading days
