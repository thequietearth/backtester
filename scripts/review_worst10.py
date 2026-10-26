"""M5c review: last year's worst performers, for the contrarian strategy.

Usage:
  python scripts/review_worst10.py --crashes   evidence for the hand verdicts in data/crash_review.csv
  python scripts/review_worst10.py             check every point-in-time worst-10 pick for 1999-2025

The price checks set aside real crashes along with broken data, and last year's worst
stocks are exactly those. So:
1. `--crashes` lists every member set aside as "suspect prices" that would rank among its
   year's 15 worst, with evidence: which check fired and when, the adjusted return next to
   the traded-price return, trading volume, and Yahoo's return where the stock still trades.
   Each gets a verdict in data/crash_review.csv: "real" (rank it) or "broken" (keep it out).
2. Without it, every worst-10 pick (after the verdicts) is checked like v1's top 10: against
   Yahoo's dividend-adjusted prices where the stock still trades, otherwise listed with the
   evidence for a hand check. Writes data/cache/worst10_review.csv; the write-up is
   docs/worst10-review.md.
Yahoo prices are downloaded once and cached in data/raw/yahoo/.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bt.coverage import (ADJ_MOVE, MAX_FROZEN_DAYS, MAX_HOLE_DAYS, RAW_STILL, _longest_run,  # noqa: E402
                         load_crash_review, rankable_universe)
from bt.universe import formation_dates  # noqa: E402

CACHE = ROOT / "data" / "cache"
YAHOO = ROOT / "data" / "raw" / "yahoo" / "worst10_review_closes.parquet"
YEARS = range(1999, 2026)
TOLERANCE = 0.05  # log-return difference, about 5% of the stock's value


def evidence(code, f_start, f_date, prices, raw_split, raw, volume_of, cal) -> dict:
    """What the price checks saw over one formation year."""
    adj = prices[code].loc[f_start:f_date]
    x = adj.dropna()
    moves = np.log(x).diff()
    big = moves.abs().idxmax() if len(moves.dropna()) else None
    traded = raw[code].reindex(x.index)
    glitch = (moves.abs() > ADJ_MOVE) & (np.log(traded).diff().abs() < RAW_STILL)
    days = cal[(cal >= f_start) & (cal <= f_date)]
    sp = raw_split[code]
    vol = volume_of(code)
    return {"adjusted_return": x.iloc[-1] / x.iloc[0] - 1,
            "traded_return": sp.get(f_date) / sp.get(f_start) - 1,
            "biggest_day": np.exp(moves[big]) - 1 if big is not None else np.nan,
            "biggest_day_on": big.date() if big is not None else None,
            "glitch_days": int(glitch.sum()),
            "longest_hole": _longest_run(prices[code].reindex(days).isna().to_numpy()),
            "longest_frozen": _longest_run(np.diff(x.to_numpy()) == 0),
            "median_volume": float(vol.loc[f_start:f_date].median()) if vol is not None else np.nan,
            "price_at_end": raw[code].get(f_date)}


def yahoo_closes(symbols):
    if YAHOO.exists() and set(symbols) <= set(pd.read_parquet(YAHOO).columns):
        return pd.read_parquet(YAHOO)
    closes = yf.download(sorted(symbols), start="1997-12-01", auto_adjust=True, progress=False)["Close"]
    YAHOO.parent.mkdir(parents=True, exist_ok=True)
    closes.to_parquet(YAHOO)
    return closes


def main():
    prices, raw, factors = (pd.read_parquet(CACHE / f) for f in
                            ("prices.parquet", "close.parquet", "split_factors.parquet"))
    raw = raw.reindex_like(prices)
    raw_split = raw * factors.reindex(index=prices.index, columns=prices.columns).ffill().fillna(1.0)
    cal = prices["SPY"].dropna().index
    detail = pd.read_parquet(CACHE / "coverage_pit_detail.parquet")
    fdates = formation_dates(cal, [YEARS[0] - 1, *YEARS])
    active = {r["Code"] for r in json.loads((ROOT / "data/raw/eodhd/symbols_us_active.json").read_text(encoding="utf-8"))}
    names = {}
    for kind in ("active", "delisted"):
        for r in json.loads((ROOT / f"data/raw/eodhd/symbols_us_{kind}.json").read_text(encoding="utf-8")):
            names.setdefault(str(r["Code"]), r.get("Name") or "")

    def volume_of(code):
        path = ROOT / "data" / "raw" / "eodhd" / "eod" / f"{code.replace('/', '_')}.parquet"
        return pd.read_parquet(path).set_index("date")["volume"] if path.exists() else None

    # Every member with prices at both ends of its formation year, worst first, including
    # the ones the price checks set aside.
    ranked_all = {}
    for y in YEARS:
        g = detail[(detail.year == y) & detail.code.notna() & detail.formation_ok
                   & detail.status.isin(["ok", "no holding data", "suspect prices"])]
        r = (prices.loc[fdates[y], g.code] / prices.loc[fdates[y - 1], g.code] - 1).dropna()
        order = sorted(r.index, key=lambda c: (r[c], c))
        ranked_all[y] = (r[order], g.set_index("code"))
    symbols = {c for y in YEARS for c in ranked_all[y][0].index[:20] if c in active}
    yahoo = yahoo_closes(symbols)

    def yahoo_return(code, start, end):
        if code not in yahoo.columns:
            return np.nan
        y = yahoo[code]
        return y.get(end) / y.get(start) - 1 if pd.notna(y.get(start)) and pd.notna(y.get(end)) else np.nan

    if "--crashes" in sys.argv:
        rows = []
        for y in YEARS:
            r, g = ranked_all[y]
            for rank, code in enumerate(r.index[:15], 1):
                if g.at[code, "status"] != "suspect prices":
                    continue
                rows.append({"year": y, "worst_rank": rank, "ticker": g.at[code, "ticker"], "code": code,
                             "name": names.get(code, ""),
                             **evidence(code, fdates[y - 1], fdates[y], prices, raw_split, raw, volume_of, cal),
                             "yahoo_return": yahoo_return(code, fdates[y - 1], fdates[y])})
        out = pd.DataFrame(rows)
        out.to_csv(CACHE / "crash_candidates.csv", index=False)
        show = out.copy()
        for c in ("adjusted_return", "traded_return", "biggest_day", "yahoo_return"):
            show[c] = (100 * show[c]).round(0)
        show["median_volume"] = (show.median_volume / 1e3).round(0)
        pd.set_option("display.width", 260)
        pd.set_option("display.max_colwidth", 26)
        print(show.to_string(index=False))
        print(f"\n{len(out)} candidates; checks: hole > {MAX_HOLE_DAYS} days, frozen > {MAX_FROZEN_DAYS} days")
        return

    real = load_crash_review(ROOT / "data" / "crash_review.csv")
    universe = rankable_universe(detail, fdates.loc[list(YEARS)], real_crashes=real)
    rows = []
    for y in YEARS:
        f_start, f_date = fdates[y - 1], fdates[y]
        entry = cal[cal > f_date].min()
        nxt = cal[cal.year == y + 1]
        exit_ = nxt.min() if len(nxt) else cal.max()
        g = ranked_all[y][1]
        r = (prices.loc[f_date, universe[f_date]] / prices.loc[f_start, universe[f_date]] - 1).dropna()
        worst = sorted(r.index, key=lambda c: (r[c], c))[:10]
        for rank, code in enumerate(worst, 1):
            px = prices[code]
            held = px.loc[entry:exit_].dropna()
            bought = pd.notna(px.get(entry))
            hold = held.iloc[-1] / px[entry] - 1 if bought and len(held) else np.nan
            ended = bought and len(held) and held.index[-1] < exit_
            row = {"year": y, "rank": rank, "ticker": g.at[code, "ticker"], "code": code, "name": names.get(code, ""),
                   "status": g.at[code, "status"], "formation_return": r[code],
                   "traded_price_return": raw_split[code].get(f_date) / raw_split[code].get(f_start) - 1,
                   "holding_return": hold, "data_ended": held.index[-1].date() if ended else None,
                   "still_trades": code in active,
                   "data_from": px.first_valid_index().date(), "data_to": px.last_valid_index().date()}
            if code in active and code in yahoo.columns:
                yf_form = yahoo_return(code, f_start, f_date)
                y_held = yahoo[code].loc[entry:exit_].dropna()
                yf_hold = y_held.iloc[-1] / yahoo[code].get(entry) - 1 if len(y_held) and pd.notna(
                    yahoo[code].get(entry)) else np.nan
                row.update(yahoo_formation_return=yf_form, yahoo_holding_return=yf_hold)
                diffs = [abs(np.log1p(a) - np.log1p(b)) for a, b in ((r[code], yf_form), (hold, yf_hold))
                         if pd.notna(a) and pd.notna(b)]
                if not diffs:
                    row["check"] = "Yahoo has no prices for these dates: review by hand"
                else:
                    row["check"] = "matches Yahoo" if max(diffs) <= TOLERANCE else "differs from Yahoo: review"
            else:
                row["check"] = "delisted: review by hand"
            rows.append(row)
    review = pd.DataFrame(rows)
    review.to_csv(CACHE / "worst10_review.csv", index=False)
    print(review.check.value_counts().to_string())
    show = review[review.check != "matches Yahoo"].copy()
    for c in ("formation_return", "traded_price_return", "holding_return", "yahoo_formation_return",
              "yahoo_holding_return"):
        if c in show:
            show[c] = (100 * show[c]).round(0)
    pd.set_option("display.width", 260)
    pd.set_option("display.max_colwidth", 26)
    cols = ["year", "rank", "ticker", "code", "name", "status", "formation_return", "traded_price_return",
            "yahoo_formation_return", "holding_return", "yahoo_holding_return", "data_ended", "data_from",
            "data_to", "check"]
    print(show[[c for c in cols if c in show]].to_string(index=False))


if __name__ == "__main__":
    main()
