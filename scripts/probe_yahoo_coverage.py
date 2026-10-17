"""Data-source probe: how much of the point-in-time S&P 500 does Yahoo have prices for?

Results and context: docs/data-source-evaluation.md

Usage: python scripts/probe_yahoo_coverage.py <components.csv> <out_dir>
  components.csv: "S&P 500 Historical Components & Changes (Updated).csv" from
                  github.com/fja05680/sp500, saved under data/raw/
  out_dir:        e.g. data/raw/probe_yahoo (gitignored; caches the download)

For each backtest year Y (1996-2025), take the members on the formation date
(last trading day of Y-1) and check for a Yahoo adjusted close on:
  - formation start (last trading day of Y-2)
  - formation date  (last trading day of Y-1)
  - entry           (first trading day of Y)
Also count members whose data stops before the next rebalance.
"""
import logging
import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf
import yfinance.shared as yf_shared

logging.getLogger("yfinance").setLevel(logging.CRITICAL)

comp_path, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)
cache = out_dir / "closes.parquet"
errors_path = out_dir / "download_errors.csv"

comp = pd.read_csv(comp_path, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
comp["tickers"] = comp["tickers"].str.split(",")


def members_on(d):
    rows = comp[comp["date"] <= d]
    row = rows.iloc[-1] if len(rows) else comp.iloc[0]  # 1996: no 1995 row, use first row
    return row["date"], sorted(set(row["tickers"]))


def ysym(t):
    return t.replace(".", "-")  # BRK.B -> BRK-B


def is_rate_limit(msg):
    m = str(msg).lower()
    return "rate limit" in m or "too many requests" in m or "429" in m


def download(symbols):
    closes, errors = [], {}
    todo = list(symbols)
    for i in range(0, len(todo), 100):
        batch = todo[i:i + 100]
        for attempt in range(6):
            yf_shared._ERRORS.clear()
            df = yf.download(batch, start="1994-01-01", auto_adjust=True,
                             progress=False, threads=True)
            errs = dict(yf_shared._ERRORS)
            limited = [s for s, m in errs.items() if is_rate_limit(m)]
            if not limited:
                break
            wait = 30 * 2 ** attempt
            print(f"  rate limited on {len(limited)} symbols, waiting {wait}s", flush=True)
            time.sleep(wait)
        else:
            raise RuntimeError("still rate limited after retries; results would be wrong")
        close = df["Close"] if "Close" in df.columns.get_level_values(0) else pd.DataFrame()
        closes.append(close)
        errors.update(errs)
        print(f"  downloaded {min(i + 100, len(todo))}/{len(todo)}", flush=True)
        time.sleep(3)
    return pd.concat(closes, axis=1), errors


years = range(1996, 2026)

# Union of every formation-date membership list.
spy_probe = yf.download("SPY", start="1994-01-01", auto_adjust=True, progress=False)["Close"]
cal = spy_probe.dropna().index
snapshots = {}
for Y in years:
    fdate = cal[cal.year == Y - 1].max()
    snapshots[Y] = members_on(fdate)
symbols = sorted({ysym(t) for _, tl in snapshots.values() for t in tl} | {"SPY"})
print(f"{len(symbols)} unique symbols across {len(snapshots)} formation dates", flush=True)

if cache.exists():
    closes = pd.read_parquet(cache)
    errors = pd.read_csv(errors_path).set_index("symbol")["error"].to_dict() if errors_path.exists() else {}
    print("using cached closes", flush=True)
else:
    closes, errors = download(symbols)
    closes = closes.loc[:, ~closes.columns.duplicated()]
    closes.to_parquet(cache)
    pd.Series(errors, name="error").rename_axis("symbol").reset_index().to_csv(errors_path, index=False)

cal = closes["SPY"].dropna().index
rows, missing_rows = [], []
for Y in years:
    fstart = cal[cal.year == Y - 2].max()
    fdate = cal[cal.year == Y - 1].max()
    entry = cal[cal.year == Y].min()
    nxt = cal[cal.year == Y + 1]
    hold_end = nxt.min() if len(nxt) else cal.max()
    snap_date, members = snapshots[Y]
    n_form = n_hold = n_both = n_ended = 0
    for t in members:
        s = closes[ysym(t)] if ysym(t) in closes.columns else None
        has_f = s is not None and pd.notna(s.get(fstart)) and pd.notna(s.get(fdate))
        has_h = s is not None and pd.notna(s.get(entry))
        n_form += has_f
        n_hold += has_h
        if has_f and has_h:
            n_both += 1
            last = s.loc[entry:hold_end].last_valid_index()
            n_ended += last < hold_end
        else:
            first = s.first_valid_index() if s is not None else None
            missing_rows.append({"year": Y, "ticker": t,
                                 "yahoo_first_date": first.date() if first is not None else None})
    rows.append({"year": Y, "snapshot": snap_date.date(), "members": len(members),
                 "formation_ok": n_form, "holding_ok": n_hold, "both_ok": n_both,
                 "coverage_pct": round(100 * n_both / len(members), 1),
                 "ended_mid_year": n_ended})

report = pd.DataFrame(rows)
missing = pd.DataFrame(missing_rows)
report.to_csv(out_dir / "coverage_by_year.csv", index=False)
missing.to_csv(out_dir / "missing.csv", index=False)
pd.set_option("display.width", 200)
print(report.to_string(index=False))
n_any = int(closes.drop(columns="SPY").notna().any().sum())
print(f"\nsymbols with any Yahoo data at all: {n_any}/{len(symbols) - 1}")
print(f"download errors recorded: {len(errors)}")
