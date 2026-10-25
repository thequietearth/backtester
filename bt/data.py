"""Price download, parquet caching and ticker mapping.

A ticker is not a company: the map turns (ticker, date range) into the one
security to download. Network code is kept thin; parsing and candidate rules are
pure functions so they can be tested without the network.

Prices come from EODHD (eodhd.com); see docs/data-source-evaluation.md. The API key
lives in .env and is never printed: errors carry the HTTP status and response text,
never the request URL, because the URL contains the key.
"""
import os
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

EODHD_API = "https://eodhd.com/api"
RETRY_STATUSES = {429, 500, 502, 503, 504}  # EODHD refusing (rate limit) or failing: wait and retry

EOD_COLUMNS = ["date", "open", "high", "low", "close", "adjusted_close", "volume"]
DIV_COLUMNS = ["date", "value", "unadjusted_value", "currency"]
SPLIT_COLUMNS = ["date", "split", "ratio"]


class EODHDError(Exception):
    """An EODHD request failed. `status` is the HTTP status, or 0 for a network error."""

    def __init__(self, status: int, message: str):
        super().__init__(f"EODHD HTTP {status}: {message}")
        self.status = status


def load_api_key(env_file: str | Path) -> str:
    load_dotenv(env_file)
    key = os.environ.get("EODHD_API_KEY", "").strip()
    if not key or key == "your-key-here":
        raise RuntimeError(f"EODHD_API_KEY is missing or still the placeholder in {env_file}")
    return key


def get_json(path: str, key: str, params: dict | None = None, session=None,
             retries: int = 5, sleep=time.sleep):
    """GET {EODHD_API}/{path} and return the parsed JSON.

    Retries with exponential back-off (5 s, 10 s, 20 s, ...) on 429 and 5xx responses
    and on network errors; any other failure raises EODHDError straight away.
    """
    session = session or requests
    query = {"api_token": key, "fmt": "json", **(params or {})}
    for attempt in range(retries + 1):
        try:
            r = session.get(f"{EODHD_API}/{path}", params=query, timeout=60)
        except requests.RequestException as e:
            err = EODHDError(0, type(e).__name__)  # not str(e): it can contain the URL
        else:
            if r.status_code == 200:
                try:
                    return r.json()
                except ValueError:
                    raise EODHDError(200, f"not JSON: {r.text[:200]}") from None
            err = EODHDError(r.status_code, r.text[:200])
            if r.status_code not in RETRY_STATUSES:
                raise err
        if attempt < retries:
            sleep(min(5 * 2 ** attempt, 300))
    raise err


def call_budget(daily_limit: int, used_today: int, max_calls: int | None) -> int:
    """How many calls a download run may make: what's left today, capped by max_calls.
    max_calls=None means no cap; max_calls=0 means a dry run."""
    left = max(0, daily_limit - used_today)
    return left if max_calls is None else max(0, min(left, max_calls))


def account_status(key: str, session=None) -> dict:
    """Plan and today's usage. The endpoint also returns name and email; those are dropped."""
    d = get_json("user", key, session=session)
    return {"plan": d.get("subscriptionType"), "used": d.get("apiRequests"),
            "usage_date": d.get("apiRequestsDate"), "daily_limit": d.get("dailyRateLimit")}


def split_payload(payload) -> tuple[list[dict], list[str]]:
    """Split an EODHD list response into data records and warning messages.

    EODHD can put a warning object inside the list (e.g. "Data is limited by one year
    as you have free subscription"). Those must never be parsed as data rows. Anything
    that isn't a list is unexpected and raises.
    """
    if not isinstance(payload, list):
        raise ValueError(f"expected a list, got {type(payload).__name__}: {str(payload)[:200]}")
    records = [r for r in payload if isinstance(r, dict) and "date" in r]
    warnings = [str(r.get("warning", r)) if isinstance(r, dict) else str(r)
                for r in payload if not (isinstance(r, dict) and "date" in r)]
    return records, warnings


def _frame(records, columns) -> pd.DataFrame:
    return pd.DataFrame(list(records)).reindex(columns=columns)


def parse_eod(records) -> pd.DataFrame:
    """EODHD /eod JSON -> one row per trading day, oldest first.

    `close` is the raw traded price. `adjusted_close` is EODHD's adjusted price, meant
    to include splits and dividends; pass test 3 in the evaluation doc checks that.
    """
    df = _frame(records, EOD_COLUMNS)
    df["date"] = pd.to_datetime(df["date"])
    for c in EOD_COLUMNS[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype(float)
    return df.sort_values("date").reset_index(drop=True)


def parse_dividends(records) -> pd.DataFrame:
    """EODHD /div JSON -> one row per ex-dividend date. `value` is split-adjusted."""
    df = _frame(records, ["date", "value", "unadjustedValue", "currency"])
    df = df.rename(columns={"unadjustedValue": "unadjusted_value"})
    df["date"] = pd.to_datetime(df["date"])
    for c in ("value", "unadjusted_value"):
        df[c] = pd.to_numeric(df[c], errors="coerce").astype(float)
    df["currency"] = df["currency"].astype("string")
    return df[DIV_COLUMNS].sort_values("date").reset_index(drop=True)


def parse_splits(records) -> pd.DataFrame:
    """EODHD /splits JSON -> one row per split. `ratio` = new shares per old share,
    so "2.000000/1.000000" is 2.0 and a 1-for-10 reverse split is 0.1."""
    df = _frame(records, ["date", "split"])
    df["date"] = pd.to_datetime(df["date"])
    df["split"] = df["split"].astype("string")
    parts = df["split"].str.split("/", expand=True).reindex(columns=[0, 1])
    df["ratio"] = pd.to_numeric(parts[0], errors="coerce") / pd.to_numeric(parts[1], errors="coerce")
    return df[SPLIT_COLUMNS].sort_values("date").reset_index(drop=True)


_SUFFIX = re.compile(r"(_old\d*|\d)$")


def index_codes(codes) -> dict[str, list[str]]:
    """Group EODHD codes by base ticker, so WEN, WEN_old and HLT1 file under WEN and HLT."""
    index: dict[str, list[str]] = {}
    for code in codes:
        index.setdefault(_SUFFIX.sub("", code), []).append(code)
    return index


def candidate_codes(ticker: str, index: dict[str, list[str]]) -> list[str]:
    """EODHD codes that might hold this index member's prices.

    EODHD keeps a company whose ticker was later reused under a suffixed code
    (WEN_old, EP_old, SGP_old1, HLT1), so the candidates are the ticker plus those
    variants. Share classes use a dash (BRK.B -> BRK-B). Bankruptcy tickers (LEHMQ)
    and renamed codes follow no pattern: those go in data/ticker_map.csv.
    """
    return sorted(index.get(ticker.replace(".", "-"), []))


def load_tbill(path: str | Path) -> pd.Series:
    """FRED's DTB3 series (3-month US Treasury bill rate, in percent) as yearly decimal
    rates by date. Holidays are blank in the file and stay NaN here. DTB3 is quoted on a
    discount basis; treating it as a plain yearly rate understates it by a few hundredths
    of a percent, which doesn't matter here."""
    df = pd.read_csv(path)
    rates = pd.to_numeric(df.iloc[:, 1], errors="coerce") / 100
    return pd.Series(rates.values, index=pd.to_datetime(df.iloc[:, 0]), name="tbill")


def cash_returns(calendar, annual_rate: pd.Series) -> pd.Series:
    """Daily return on cash for each trading day:
        (1 + r) ** (calendar days since the previous trading day / 365) - 1
    where r is the yearly rate known at the previous trading day's close - so nothing is
    used before it's known, and a weekend earns three days. The first day earns nothing."""
    cal = pd.DatetimeIndex(calendar)
    rate = annual_rate.sort_index()
    rate = rate.reindex(rate.index.union(cal)).ffill().reindex(cal)
    days = pd.Series(cal, index=cal).diff().dt.days
    return ((1 + rate.shift(1)) ** (days / 365) - 1).fillna(0.0)


def apply_price_exclusions(eod: pd.DataFrame, ranges) -> pd.DataFrame:
    """Blank the prices (close and adjusted close) inside known-bad date ranges, listed by
    hand in data/price_exclusions.csv. `ranges` is [(start, end or None for "onwards")].

    Used where a code is right but its prices aren't: a series that carries on as a
    different instrument after a takeover, or a stretch of broken dividend adjustments.
    Blanked prices count as missing: the stock can't be ranked on them, and the engine
    sells a held position after a long run without prices. Prices are never edited.
    """
    out = eod.copy()
    for start, end in ranges:
        bad = out["date"] >= start
        if end is not None:
            bad &= out["date"] <= end
        out.loc[bad, ["close", "adjusted_close"]] = float("nan")
    return out


def cache_file(root: str | Path, kind: str, code: str) -> Path:
    """Where one symbol's data of one kind (eod, div, splits) is cached."""
    return Path(root) / kind / f"{code.replace('/', '_')}.parquet"


# --- Mapping: which EODHD code holds an index member's prices during one membership spell ---

MIN_COVERAGE = 0.95  # share of the spell's trading days that must have a price
# A rough floor on median daily trading value (close x volume) for a real S&P 500 member.
# Even the smallest members trade millions of dollars a day; a micro-cap that later took
# a member's ticker (Senstar under SNT, Empire Petroleum under EP) trades far less.
MIN_DOLLAR_VOLUME = 500_000
END_TOLERANCE_DAYS = 10


def assess_candidate(start, end, prices: pd.DataFrame, calendar, as_of,
                     end_tolerance_days: int = END_TOLERANCE_DAYS) -> dict:
    """How well one candidate's price history fits one membership spell [start, end).

    coverage:      share of the spell's trading days on which the candidate has a price.
    end_match:     the spell ended and the candidate's data stops within a few days of
                   that end, i.e. it stopped trading when it left the index (typical after
                   a takeover). Strong evidence that this is the member.
    dollar_volume: median daily close x volume during the spell, a rough size measure.
    """
    cal = pd.DatetimeIndex(calendar)
    days = cal[(cal >= start) & (cal <= as_of)] if pd.isna(end) else cal[(cal >= start) & (cal < end)]
    p = prices.dropna(subset=["adjusted_close"]).set_index("date")
    have = p.index.intersection(days)
    last = p.index.max() if len(p) else pd.NaT
    end_match = bool(pd.notna(end) and pd.notna(last) and abs((last - end).days) <= end_tolerance_days)
    dollar_volume = float((p.loc[have, "close"] * p.loc[have, "volume"]).median()) if len(have) else 0.0
    return {"coverage": len(have) / len(days) if len(days) else 0.0, "end_match": end_match,
            "dollar_volume": dollar_volume, "first": p.index.min() if len(p) else pd.NaT, "last": last}


def choose_security(assessments: dict[str, dict], multi_spell: bool,
                    min_coverage: float = MIN_COVERAGE,
                    min_dollar_volume: float = MIN_DOLLAR_VOLUME) -> tuple[str | None, str, list[str]]:
    """Pick the code for one spell. Returns (code, status, flags).

    status is "auto" (confident), "review" (flags explain why a human should check) or
    "missing" (no candidate has any price during the spell).

    Order of evidence: a candidate whose data stops when membership ended wins, even with
    a truncated history (EODHD's delisted histories often start at end-1997); then
    candidates that cover the spell; then whatever covers most. Ties between several
    candidates go to full coverage, then the biggest by trading value, flagged "ambiguous".
    """
    usable = {c: a for c, a in assessments.items() if a["coverage"] > 0}
    if not usable:
        return None, "missing", []
    flags = []
    ends = [c for c in usable if usable[c]["end_match"]]
    fits = [c for c in usable if usable[c]["coverage"] >= min_coverage]
    pool = ends or fits or list(usable)
    if len(pool) == 1:
        code = pool[0]
    elif not (ends or fits):
        code = max(pool, key=lambda c: usable[c]["coverage"])
    else:
        code = max(pool, key=lambda c: (usable[c]["coverage"] >= min_coverage, usable[c]["dollar_volume"]))
        flags.append("ambiguous")
    if usable[code]["coverage"] < min_coverage:
        flags.append("partial")
    if usable[code]["dollar_volume"] < min_dollar_volume:
        flags.append("small")
    if multi_spell:  # the ticker left the index and came back: often a different company
        flags.append("multi_spell")
    return code, ("review" if flags else "auto"), flags


def apply_overrides(spells: pd.DataFrame, overrides: pd.DataFrame | None) -> pd.DataFrame:
    """Hand fixes from data/ticker_map.csv win over the automatic choice.

    Each override covers [start, end) for one ticker (an empty end means "to now"). Where
    it covers only part of a spell, the spell is split: the covered part takes the
    override, the rest keeps the automatic choice. That handles a ticker whose company
    changed mid-spell (IR was Ingersoll-Rand plc until March 2020, then another company).
    An empty code means "no usable data" (e.g. Amoco, which traded as AN until 1998).
    """
    rows = [dict(r) for _, r in spells.iterrows()]
    for r in rows:
        r.setdefault("note", None)
    if overrides is None or overrides.empty:
        return pd.DataFrame(rows)
    far = pd.Timestamp.max
    for ov in overrides.itertuples():
        o_start = pd.Timestamp(ov.start)
        o_end = pd.Timestamp(ov.end) if isinstance(ov.end, str) and ov.end.strip() else far
        code = ov.code if isinstance(ov.code, str) and ov.code.strip() else None
        new_rows = []
        for r in rows:
            r_end = far if pd.isna(r["end"]) else r["end"]
            if r["ticker"] != ov.ticker or not (r["start"] < o_end and o_start < r_end):
                new_rows.append(r)
                continue
            lo, hi = max(r["start"], o_start), min(r_end, o_end)
            if r["start"] < lo:
                new_rows.append({**r, "end": lo})
            new_rows.append({**r, "start": lo, "end": pd.NaT if hi == far else hi,
                             "code": code, "status": "manual", "note": ov.note})
            if hi < r_end:
                new_rows.append({**r, "start": hi})
        rows = new_rows
    return pd.DataFrame(rows).sort_values(["ticker", "start"]).reset_index(drop=True)


# --- Renames: the same company under a new ticker -------------------------------------
# When a member is renamed (FB -> META), the membership data shows one ticker leaving and
# another joining on the same day. EODHD keeps the company's whole history under the new
# ticker (META from 2012) and a stub under the old one that stops at the rename (FB_old).
# The mapper rightly picks the stub for the old spell (its data ends when the spell does),
# but anyone holding it across the rename would see "data ended" for a company that
# carried on. follow_renames maps the old spell to the new code when the evidence says
# it's the same security.

RENAME_DAYS = 7               # the new ticker joins within a week of the old one leaving
STUB_DAYS = (15, 30)          # the old code stops at most 15 days before to 30 days after that
RETURN_MATCH = 0.005          # daily returns "the same" within half a percentage point...
MATCH_SHARE = 0.98            # ...on at least 98% of the old code's days,
LASTING_GAP = np.log(1.05)    # with no lasting jump of 5% or more in the gap between the codes,
RENAME_CHECK_DAYS = 10        # and the same cumulative return (within RETURN_MATCH) over the last 10 days
SAME_TRADED = 0.01            # on the old code's last day, both traded at the same price (1%)
RENAME_JUMP = np.log(1.15)    # a bigger move across the rename: e.g. a special dividend left unadjusted


def _series(eod: pd.DataFrame | None, column: str = "adjusted_close") -> pd.Series:
    if eod is None or eod.empty:
        return pd.Series(dtype=float)
    return eod.dropna(subset=[column]).set_index("date")[column].sort_index()


def _rename_target(spell: dict, rows: list[dict], eod_of) -> tuple | None:
    """(new code, new ticker, cut, stop) if `spell` is the old side of a rename, else None.
    The old spell uses the new code over [cut, stop)."""
    code, end = spell["code"], spell["end"]
    if not isinstance(code, str) or pd.isna(end) or spell["status"] == "manual":
        return None
    old = _series(eod_of(code))
    if old.empty or not (end - pd.Timedelta(days=STUB_DAYS[0]) <= old.index.max()
                         <= end + pd.Timedelta(days=STUB_DAYS[1])):
        return None  # the old code doesn't stop at the rename: nothing breaks
    first_old, last_old = old.index.min(), old.index.max()
    lo = spell["start"] - pd.DateOffset(months=13)  # the first decision's 12-month window, and some
    successors = sorted((t for t in rows if t["ticker"] != spell["ticker"] and isinstance(t["code"], str)
                         and t["code"] != code and abs(t["start"] - end) <= pd.Timedelta(days=RENAME_DAYS)),
                        key=lambda t: abs(t["start"] - end))
    for t in successors:
        new = _series(eod_of(t["code"]))
        after = new[new.index > last_old]
        if after.empty or last_old not in new.index:
            continue
        # Same security: the same daily returns wherever the old code traded (from a year
        # before the spell), at any price level (adjustments differ by later dividends).
        o = old[old.index >= lo]
        common = o.index.intersection(new.index)
        if len(o) < 20 or len(common) < MATCH_SHARE * len(o):
            continue
        diff = (np.log(o[common]).diff() - np.log(new[common]).diff()).dropna().abs()
        if (diff < RETURN_MATCH).mean() < MATCH_SHARE:
            continue
        # A corporate action that one code handles differently makes the gap between them
        # jump and stay (DowDuPont's reverse split and Corteva spin-off, three days before it
        # became DuPont: -17% under one code, +18% under the other). A one-day glitch that
        # reverses doesn't, nor does the slow drift from slightly different dividend data.
        # So: the gap's median over the 5 days from any date may not move by 5% from the 5
        # days before; and over the last 10 days the cumulative returns must agree.
        gap = np.log(new[common]) - np.log(o[common])
        gap_before = gap.rolling(5, min_periods=1).median().shift(1)
        gap_from = gap[::-1].rolling(5, min_periods=1).median()[::-1]
        if (gap_from - gap_before).abs().max() >= LASTING_GAP:
            continue
        k = min(RENAME_CHECK_DAYS, len(gap) - 1)
        if abs(gap.iloc[-1] - gap.iloc[-1 - k]) >= RETURN_MATCH:
            continue
        # A plain rename: on the old code's last day both codes traded at the same price (a
        # spin-off or reverse split at the rename rescales the new code's history), and the
        # price carries on without a jump.
        traded_old, traded_new = _series(eod_of(code), "close"), _series(eod_of(t["code"]), "close")
        if last_old not in traded_new.index or last_old not in traded_old.index:
            continue
        if abs(traded_new[last_old] / traded_old[last_old] - 1) > SAME_TRADED:
            continue
        if abs(np.log(after.iloc[0] / new[last_old])) > RENAME_JUMP:
            continue
        # The new code may have earlier prices the old one lacks, which may be another
        # company's. Then only dates whose 12-month window lies within the old code's own
        # history (13 months after it starts) use the new code.
        early = new[(new.index >= lo) & (new.index < first_old - pd.Timedelta(days=5))]
        cut = spell["start"] if early.empty else max(spell["start"], first_old + pd.DateOffset(months=13))
        stop = min(end, t["start"])
        if cut < stop:
            return t["code"], t["ticker"], cut, stop
    return None


def follow_renames(spells: pd.DataFrame, eod_of) -> pd.DataFrame:
    """Map the old side of each rename to the code that carries on (see above).

    `spells` is the automatic security map (ticker, start, end, code, status, flags, ...);
    `eod_of(code)` returns that code's EODHD prices (date, adjusted_close, ...) or None.
    The remapped part is flagged "renamed"; where the new code's history can't be trusted
    early on, the spell is split and its first part keeps the old code. Hand-mapped spells
    (status "manual", from data/ticker_map.csv) are left alone.

    Only plain renames are followed. A corporate action on the rename day - a spin-off
    (Arconic -> Howmet), a special dividend (Kraft -> Kraft Heinz), a reverse split -
    either rescales the new code's history or shows up as a jump, and those spells keep
    the old code: sold at its last price and flagged, as before.
    """
    rows = [dict(r) for _, r in spells.iterrows()]
    out = []
    for r in rows:
        hit = _rename_target(r, rows, eod_of)
        if hit is None:
            out.append(r)
            continue
        code, ticker, cut, stop = hit
        before = r["flags"] if isinstance(r["flags"], str) else ""
        flags = ",".join(f for f in [*before.split(","), "renamed"] if f)
        if r["start"] < cut:
            out.append({**r, "end": cut})
        out.append({**r, "start": cut, "end": stop, "code": code, "flags": flags,
                    "note": f"renamed {ticker}: the same prices continue under {code}"})
        if stop < r["end"]:
            out.append({**r, "start": stop})
    return pd.DataFrame(out).sort_values(["ticker", "start"]).reset_index(drop=True)
