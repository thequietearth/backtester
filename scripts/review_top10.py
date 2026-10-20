"""M3 review: check every point-in-time top-10 pick for 1999-2025 against independent data.

Usage: python scripts/review_top10.py
Run scripts/run_v1.py first. Writes data/cache/top10_review.csv; the write-up is
docs/top10-review.md.

- Picks whose EODHD code still trades: their formation-year and holding-year returns are
  compared with Yahoo's dividend-adjusted prices (cached in data/raw/yahoo/).
- Delisted picks (Yahoo has nothing): evidence for a hand review - the return from traded
  prices on the same split basis next to the adjusted return, and the data range.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"
YAHOO = ROOT / "data" / "raw" / "yahoo" / "top10_review_closes.parquet"
YEARS = range(1999, 2026)  # PLAN.md requires 1999-2012; later years are cheap to check too
TOLERANCE = 0.05  # log-return difference, about 5% of the stock's value


def main():
    picks = pd.read_csv(CACHE / "v1_picks.csv")
    picks = picks[(picks.universe == "point-in-time") & picks.year.isin(YEARS)].copy()
    prices, raw, factors = (pd.read_parquet(CACHE / f) for f in
                            ("prices.parquet", "close.parquet", "split_factors.parquet"))
    cal = prices["SPY"].dropna().index
    active = {r["Code"] for r in json.loads((ROOT / "data/raw/eodhd/symbols_us_active.json").read_text(encoding="utf-8"))}
    picks["still_trades"] = picks.code.isin(active)

    symbols = sorted(set(picks.loc[picks.still_trades, "code"]))
    if YAHOO.exists() and set(symbols) <= set(pd.read_parquet(YAHOO).columns):
        yahoo = pd.read_parquet(YAHOO)
    else:
        yahoo = yf.download(symbols, start="1997-12-01", auto_adjust=True, progress=False)["Close"]
        YAHOO.parent.mkdir(parents=True, exist_ok=True)
        yahoo.to_parquet(YAHOO)

    rows = []
    for p in picks.itertuples():
        f_date = cal[cal.year == p.year - 1].max()
        f_start = cal[cal.year == p.year - 2].max()
        entry = cal[cal > f_date].min()
        exit_ = cal[cal.year == p.year + 1].min()
        sp = raw[p.code] * (factors[p.code].reindex(raw.index).ffill().fillna(1.0) if p.code in factors else 1.0)
        traded_ret = sp.get(f_date) / sp.get(f_start) - 1
        row = {"year": p.year, "rank": p.rank, "ticker": p.ticker, "code": p.code, "name": p.name,
               "formation_return": p.formation_return, "traded_price_return": traded_ret,
               "holding_return": p.holding_return, "still_trades": p.still_trades,
               "data_from": prices[p.code].first_valid_index().date(), "data_to": prices[p.code].last_valid_index().date()}
        if p.still_trades and p.code in yahoo.columns:
            y = yahoo[p.code]
            yf_form = y.get(f_date) / y.get(f_start) - 1
            held = y.loc[entry:exit_].dropna()
            yf_hold = held.iloc[-1] / y.get(entry) - 1 if len(held) and pd.notna(y.get(entry)) else np.nan
            row.update(yahoo_formation_return=yf_form, yahoo_holding_return=yf_hold)
            diffs = [abs(np.log1p(a) - np.log1p(b)) for a, b in
                     ((p.formation_return, yf_form), (p.holding_return, yf_hold)) if pd.notna(a) and pd.notna(b)]
            if not diffs:
                row["check"] = "Yahoo has no prices for these dates: review by hand"
            else:
                row["check"] = "matches Yahoo" if max(diffs) <= TOLERANCE else "differs from Yahoo: review"
        else:
            row["check"] = "delisted: review by hand"
        rows.append(row)
    review = pd.DataFrame(rows)
    review.to_csv(CACHE / "top10_review.csv", index=False)

    print(review.check.value_counts().to_string())
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 28)
    show = review[review.check != "matches Yahoo"].copy()
    for c in ("formation_return", "traded_price_return", "holding_return", "yahoo_formation_return", "yahoo_holding_return"):
        if c in show:
            show[c] = (100 * show[c]).round(0)
    cols = ["year", "rank", "ticker", "code", "name", "formation_return", "traded_price_return",
            "yahoo_formation_return", "holding_return", "yahoo_holding_return", "data_from", "data_to", "check"]
    print(show[[c for c in cols if c in show]].to_string(index=False))


if __name__ == "__main__":
    main()
