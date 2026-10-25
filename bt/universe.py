"""Point-in-time S&P 500 membership: which stocks were in the index on a given date.

Source: fja05680/sp500 (MIT licence), one snapshot per change date from 1996-01-02,
stored by scripts/build_constituents.py as data/constituents.parquet (columns: date, ticker).

Tickers are as used at the time, with one quirk: companies that went bankrupt appear
under their later bankruptcy ticker (e.g. ENRNQ for Enron). The ticker map in bt.data
turns (ticker, dates) into the right security.
"""
from pathlib import Path

import numpy as np
import pandas as pd


def load_constituents(path: str | Path) -> pd.DataFrame:
    """Read the membership snapshots: one row per (date, ticker), sorted."""
    return pd.read_parquet(path).sort_values(["date", "ticker"]).reset_index(drop=True)


def snapshot_on(constituents: pd.DataFrame, date) -> pd.Timestamp:
    """The snapshot that describes the index at the close of `date`: the latest one on or
    before it. A snapshot dated D already includes changes effective on D. Dates before
    the first snapshot fall back to it (fja05680 starts 1996-01-02, which stands in for
    the end-1995 formation date)."""
    dates = constituents["date"]
    eligible = dates[dates <= pd.Timestamp(date)]
    return eligible.max() if len(eligible) else dates.min()


def members_on(constituents: pd.DataFrame, date) -> list[str]:
    """Members at the close of `date` (see snapshot_on)."""
    snap = snapshot_on(constituents, date)
    return sorted(constituents.loc[constituents["date"] == snap, "ticker"])


def membership_spells(constituents: pd.DataFrame) -> pd.DataFrame:
    """Continuous periods each ticker was a member: columns ticker, start, end.

    `end` is exclusive (the first snapshot date without the ticker) and NaT while it is
    still a member. A ticker that left and later rejoined has one row per spell.
    """
    snap_dates = pd.DatetimeIndex(sorted(constituents["date"].unique()))
    rows = []
    for ticker, dates in constituents.groupby("ticker")["date"]:
        idx = np.sort(snap_dates.get_indexer(dates.unique()))
        gaps = np.flatnonzero(np.diff(idx) > 1)  # a jump in snapshot position = left and rejoined
        firsts = np.r_[idx[0], idx[gaps + 1]]
        lasts = np.r_[idx[gaps], idx[-1]]
        for first, last in zip(firsts, lasts):
            end = snap_dates[last + 1] if last + 1 < len(snap_dates) else pd.NaT
            rows.append((ticker, snap_dates[first], end))
    return pd.DataFrame(rows, columns=["ticker", "start", "end"])


NAIVE_START = pd.Timestamp("1900-01-01")


def naive_constituents(constituents: pd.DataFrame) -> pd.DataFrame:
    """Today's members as the only snapshot, dated before any formation date, so
    members_on() returns today's list for every year. This is the classic mistake the
    "naive universe" mode exists to show: it ranks only companies that survived to today
    (and some that weren't in the index yet), which flatters results - survivorship bias."""
    latest = constituents["date"].max()
    return constituents[constituents["date"] == latest].assign(date=NAIVE_START).reset_index(drop=True)


def naive_security_map(security_map: pd.DataFrame, naive: pd.DataFrame) -> pd.DataFrame:
    """Today's mapping for today's members, stretched back to NAIVE_START, as a naive
    backtest on today's tickers would use their full price history."""
    current = security_map[security_map["end"].isna() & security_map["ticker"].isin(naive["ticker"])]
    return current.assign(start=NAIVE_START).reset_index(drop=True)


def formation_dates(calendar, years) -> pd.Series:
    """For each backtest year Y, the formation date: the last trading day of Y-1.

    `calendar` is the trading days (e.g. SPY's price dates). Raises rather than guessing
    when the calendar has no trading days in a year it needs.
    """
    cal = pd.DatetimeIndex(calendar)
    out = {}
    for y in years:
        prev = cal[cal.year == y - 1]
        if prev.empty:
            raise ValueError(f"calendar has no trading days in {y - 1}")
        out[y] = prev.max()
    return pd.Series(out, name="formation_date")


def month_ends(calendar, start=None, end=None) -> list[pd.Timestamp]:
    """The last trading day of each month, within [start, end] when given."""
    cal = pd.DatetimeIndex(calendar)
    ends = cal.to_series().groupby(cal.to_period("M")).max()
    if start is not None:
        ends = ends[ends >= pd.Timestamp(start)]
    if end is not None:
        ends = ends[ends <= pd.Timestamp(end)]
    return [pd.Timestamp(d) for d in ends]


def month_end(calendar, date, months_back: int = 0) -> pd.Timestamp:
    """The last trading day of the month `months_back` months before `date`'s month
    (0: `date`'s own month, up to `date`). Monthly strategies measure returns between
    month-ends: for a decision at the end of December, `months_back=12` is the end of the
    previous December."""
    cal = pd.DatetimeIndex(calendar)
    date = pd.Timestamp(date)
    days = cal[(cal.to_period("M") == date.to_period("M") - months_back) & (cal <= date)]
    if days.empty:
        raise ValueError(f"calendar has no trading days {months_back} months before {date.date()}")
    return days.max()
