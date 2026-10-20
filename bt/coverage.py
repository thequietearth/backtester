"""Coverage report: for each year, how many index members have usable price data,
and which ones are missing or flagged.

A member is covered when it has a price at both ends of the formation period (so it
can be ranked) and at entry (so it can be held). Coverage = covered / members on the
formation date. Bands, from the PLAN.md decisions: >= 95% "trusted", 85-95% "lower
coverage", below that "unreliable". Years are never dropped, only labelled.

Price sanity: an S&P 500 stock almost never doubles or halves in a single day, but
broken data does it all the time (two securities mixed in one series, splits applied
twice). A member is "suspect prices" and is not ranked if its formation year shows
  - a jump: the adjusted price doubles or halves in a day;
  - a hole: more than 10 trading days with no price;
  - a glitch: the adjusted price moves >25% in a day while the traded price moves <10%;
  - an unexplained gap: adjusted and traded (split-basis) returns differ by >30%.
So a fake +17,000% can't become a pick. A jump in the holding year is only flagged:
real crashes (Lehman, -94% in a day) must stay in the results.
"""
import numpy as np
import pandas as pd

from bt.universe import formation_dates, members_on, snapshot_on

TRUSTED_PCT, LOWER_PCT = 95.0, 85.0


JUMP = np.log(2)  # a one-day move of x2 or more, or a halving or worse


ADJ_MOVE, RAW_STILL = np.log(1.25), np.log(1.10)


def has_jump(prices: pd.Series, start, end) -> bool:
    """True if the price doubles or halves (or worse) from one trading day to the next
    within [start, end]. Zero or negative prices count too: they are always bad data."""
    x = prices.loc[start:end].dropna()
    if (x <= 0).any():
        return True
    return bool((np.log(x).diff().abs() > JUMP).any())


def has_adjustment_glitch(adjusted: pd.Series, raw: pd.Series, start, end) -> bool:
    """True if, on some day in [start, end], the adjusted price moves more than 25% while
    the traded price moves less than 10%. A real split or special dividend does the
    opposite (the traded price drops, the adjusted one stays smooth), so this pattern means
    the adjustment itself is broken: a split applied twice, or a corrupt factor."""
    both = pd.concat([adjusted.loc[start:end], raw.loc[start:end]], axis=1).dropna()
    if len(both) < 2 or (both <= 0).any().any():
        return False
    moves = np.log(both).diff().abs()
    return bool(((moves.iloc[:, 0] > ADJ_MOVE) & (moves.iloc[:, 1] < RAW_STILL)).any())


MAX_HOLE_DAYS = 10


def has_hole(prices: pd.Series, calendar: pd.DatetimeIndex, start, end) -> bool:
    """True if more than MAX_HOLE_DAYS trading days in a row have no price within
    [start, end]. A listed S&P 500 stock trades every day; a long hole means missing
    data, and any 'return' across it can't be trusted."""
    days = calendar[(calendar >= start) & (calendar <= end)]
    missing = prices.reindex(days).isna().to_numpy()
    run = longest = 0
    for m in missing:
        run = run + 1 if m else 0
        longest = max(longest, run)
    return longest > MAX_HOLE_DAYS


GAP_TOLERANCE = np.log(1.3)


def has_unexplained_adjustment(adjusted: pd.Series, raw_split_adjusted: pd.Series, start, end) -> bool:
    """True if, over [start, end], the adjusted return and the traded return (put on the
    same basis for splits) differ by more than 30%.

    The only legitimate difference is dividends, rarely more than ~10% a year. A bigger
    gap means the adjustment drifted (e.g. a mishandled spin-off) - or, rarely, a genuine
    giant spin-off. Either way the year's return can't be trusted for ranking.
    """
    vals = [adjusted.get(start), adjusted.get(end), raw_split_adjusted.get(start), raw_split_adjusted.get(end)]
    if any(pd.isna(v) or v <= 0 for v in vals):
        return False
    a0, a1, r0, r1 = vals
    return bool(abs(np.log(a1 / a0) - np.log(r1 / r0)) > GAP_TOLERANCE)


# Statuses that may be ranked. "no holding data" is included on purpose: whether a stock
# has a price at entry is only known the day after the decision, so requiring it would
# use tomorrow's information. If a pick can't be bought, the engine keeps that money in cash.
RANKABLE = {"ok", "no holding data"}


def rankable_universe(detail: pd.DataFrame, formation_dates: pd.Series) -> dict:
    """{formation date: sorted codes that may be ranked that year}, from coverage detail."""
    return {formation_dates[y]: sorted(detail[(detail.year == y) & detail.status.isin(RANKABLE)].code)
            for y in formation_dates.index}


def band(coverage_pct: float) -> str:
    if coverage_pct >= TRUSTED_PCT:
        return "trusted"
    return "lower coverage" if coverage_pct >= LOWER_PCT else "unreliable"


def _spell_lookup(security_map: pd.DataFrame):
    by_ticker = {t: g for t, g in security_map.groupby("ticker")}

    def spell_on(ticker, date):
        g = by_ticker.get(ticker)
        if g is None:
            return None
        hit = g[(g["start"] <= date) & (g["end"].isna() | (g["end"] > date))]
        return hit.iloc[0] if len(hit) else None
    return spell_on


def coverage_by_year(constituents: pd.DataFrame, security_map: pd.DataFrame, prices: pd.DataFrame,
                     calendar, years, raw_prices: pd.DataFrame | None = None,
                     split_factors: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (summary: one row per year, detail: one row per year and member).

    `security_map` has one row per membership spell (ticker, start, end, code, status,
    flags); `prices` is adjusted close with one column per code; `raw_prices` (optional)
    is the traded close, used to catch broken adjustments; `split_factors` (optional) is
    the cumulative split ratio per code (absent = no splits). A member whose data ends
    before the holding period does still counts as covered, but `ended_mid_year` flags it:
    the backtest exits at its last price and the real outcome is unknown. A mapping
    flagged "small" (trades far too little to be an S&P 500 member) is "suspect identity"
    unless it was confirmed by hand.
    """
    cal = pd.DatetimeIndex(calendar)
    spell_on = _spell_lookup(security_map)
    summary, detail = [], []
    for y in years:
        f_start = formation_dates(cal, [y - 1])[y - 1]
        f_date = formation_dates(cal, [y])[y]
        entry = cal[cal.year == y].min()
        nxt = cal[cal.year == y + 1]
        hold_end = nxt.min() if len(nxt) else cal.max()
        snap = snapshot_on(constituents, f_date)
        for ticker in members_on(constituents, f_date):
            spell = spell_on(ticker, snap)
            code = spell["code"] if spell is not None and isinstance(spell["code"], str) else None
            flags = spell["flags"] if spell is not None and isinstance(spell["flags"], str) else ""
            confirmed = spell is not None and spell["status"] == "manual"
            s = prices[code] if code in prices.columns else None
            raw = raw_prices[code] if raw_prices is not None and code in raw_prices.columns else None
            raw_split = raw  # traded price on the adjusted price's split basis
            if raw is not None and split_factors is not None and code in split_factors.columns:
                raw_split = raw * split_factors[code].reindex(raw.index).ffill().fillna(1.0)
            form_ok = s is not None and pd.notna(s.get(f_start)) and pd.notna(s.get(f_date))
            hold_ok = s is not None and pd.notna(s.get(entry))
            last = s.loc[entry:hold_end].last_valid_index() if hold_ok else None
            if code is None:
                status = "no security"
            elif "small" in flags.split(",") and not confirmed:
                status = "suspect identity"
            elif not form_ok:
                status = "no formation data"
            # The glitch check compares with the true traded price: if the source already
            # split-adjusted it, multiplying by split factors would hide a double-counted split.
            elif has_jump(s, f_start, f_date) or has_hole(s, cal, f_start, f_date) or (raw is not None and (
                    has_adjustment_glitch(s, raw, f_start, f_date)
                    or has_unexplained_adjustment(s, raw_split, f_start, f_date))):
                status = "suspect prices"
            elif not hold_ok:
                status = "no holding data"
            else:
                status = "ok"
            detail.append({"year": y, "ticker": ticker, "code": code, "status": status,
                           "formation_ok": form_ok, "holding_ok": hold_ok,
                           "ended_mid_year": bool(hold_ok and last < hold_end),
                           "data_last": last if hold_ok and last < hold_end else pd.NaT,
                           "holding_jump": bool(hold_ok and has_jump(s, entry, hold_end)),
                           "flags": flags})
        d = pd.DataFrame([r for r in detail if r["year"] == y])
        covered = int((d["status"] == "ok").sum())
        pct = round(100 * covered / len(d), 1)
        summary.append({"year": y, "formation_date": f_date, "members": len(d),
                        "formation_ok": int(d["formation_ok"].sum()), "holding_ok": int(d["holding_ok"].sum()),
                        "covered": covered, "coverage_pct": pct,
                        "suspect": int(d["status"].isin(["suspect prices", "suspect identity"]).sum()),
                        "ended_mid_year": int(d["ended_mid_year"].sum()),
                        "holding_jump": int(d["holding_jump"].sum()),
                        "flagged": int((d["flags"] != "").sum()), "band": band(pct)})
    return pd.DataFrame(summary), pd.DataFrame(detail)
