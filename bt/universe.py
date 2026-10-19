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
