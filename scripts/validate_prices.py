"""Pass test 3: do EODHD's adjusted prices include dividends?

Usage: python scripts/validate_prices.py
Run scripts/download_eodhd.py --scope v1 first.

Two checks on long-lived stocks that still trade (so Yahoo has them too):
  1. Internal: each year's return on adjusted close minus the return on raw close should
     be about the dividend yield (around 3% for a payer like KO; 0 for a non-payer).
     A split also moves the raw close, so years with a split are left out.
  2. External: yearly total returns should match Yahoo's dividend-adjusted closes.
Yahoo closes are cached in data/raw/yahoo/ so they're downloaded once.
"""
import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bt.data import cache_file  # noqa: E402

EODHD = ROOT / "data" / "raw" / "eodhd"
YAHOO = ROOT / "data" / "raw" / "yahoo" / "validation_closes.parquet"
TICKERS = ["AAPL", "MSFT", "JNJ", "XOM", "KO", "PG", "IBM", "MMM", "PFE", "MRK",
           "WMT", "GE", "CVX", "PEP", "MCD", "JPM", "INTC", "DIS", "SPY", "RSP"]
TOLERANCE = 0.005  # 0.5 percentage points of yearly return


LAST_FULL_YEAR = pd.Timestamp.today().year - 1  # the current year is unfinished: sources stop on different days


def yearly(series: pd.Series) -> pd.Series:
    """Calendar-year returns from year-end closes, full years only."""
    ye = series.dropna().groupby(series.dropna().index.year).last()
    return ye.pct_change().dropna().loc[:LAST_FULL_YEAR]


def main():
    eod = {t: pd.read_parquet(cache_file(EODHD, "eod", t)).set_index("date") for t in TICKERS}
    splits = {t: pd.read_parquet(p) for t in TICKERS if (p := cache_file(EODHD, "splits", t)).exists()}
    if YAHOO.exists():
        yahoo = pd.read_parquet(YAHOO)
    else:
        yahoo = yf.download(TICKERS, start="1994-01-01", auto_adjust=True, progress=False)["Close"]
        YAHOO.parent.mkdir(parents=True, exist_ok=True)
        yahoo.to_parquet(YAHOO)

    rows = []
    for t in TICKERS:
        adj, raw = yearly(eod[t]["adjusted_close"]), yearly(eod[t]["close"])
        split_years = set(splits[t]["date"].dt.year) if t in splits else set()
        gap = (adj - raw).drop(labels=[y for y in split_years if y in adj.index])
        ext = (adj - yearly(yahoo[t])).dropna()
        rows.append({"ticker": t, "years": len(adj),
                     "adj_minus_raw_median_pct": round(100 * gap.median(), 2),
                     "vs_yahoo_median_abs_pct": round(100 * ext.abs().median(), 3),
                     "vs_yahoo_max_abs_pct": round(100 * ext.abs().max(), 2),
                     "years_off_by_over_0.5pct": int((ext.abs() > TOLERANCE).sum())})
        for y, diff in ext[ext.abs() > TOLERANCE].items():
            rows[-1].setdefault("off", []).append(f"{y}: EODHD {100 * adj[y]:+.1f}% vs Yahoo "
                                                  f"{100 * (adj[y] - diff):+.1f}%")
    report = pd.DataFrame(rows)
    print(report.drop(columns=["off"], errors="ignore").to_string(index=False))
    off = report["years_off_by_over_0.5pct"].sum()
    print(f"\nyears compared with Yahoo: {report['years'].sum()}; off by more than 0.5 pct points: {off}")
    for r in rows:
        for line in r.get("off", []):
            print(f"  {r['ticker']} {line}")


if __name__ == "__main__":
    main()
