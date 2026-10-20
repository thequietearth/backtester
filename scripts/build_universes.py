"""Build the coverage results the app reads, so it never has to recompute them.

Usage: python scripts/build_universes.py   (after scripts/build_price_cache.py)
Outputs (gitignored, data/cache/):
  coverage_pit_summary.parquet  one row per year: members, coverage %, band...
  coverage_pit_detail.parquet   one row per year and member: status, flags...
  coverage_naive_detail.parquet the same for the naive universe (today's members only)
The app builds each year's rankable universe from the detail files (bt.coverage.rankable_universe).
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bt.coverage import coverage_by_year  # noqa: E402
from bt.universe import load_constituents, naive_constituents, naive_security_map  # noqa: E402

CACHE = ROOT / "data" / "cache"
REPORT_YEARS = range(1996, 2026)  # the coverage report shows 1996-98 to document the start year
BACKTEST_YEARS = range(1999, 2026)


def main():
    cons = load_constituents(ROOT / "data" / "constituents.parquet")
    smap = pd.read_csv(CACHE / "security_map.csv", parse_dates=["start", "end"])
    prices, raw, factors = (pd.read_parquet(CACHE / f) for f in
                            ("prices.parquet", "close.parquet", "split_factors.parquet"))
    cal = prices["SPY"].dropna().index
    summary, detail = coverage_by_year(cons, smap, prices, cal, REPORT_YEARS, raw_prices=raw, split_factors=factors)
    summary.to_parquet(CACHE / "coverage_pit_summary.parquet", index=False)
    detail.to_parquet(CACHE / "coverage_pit_detail.parquet", index=False)
    ncons = naive_constituents(cons)
    _, naive = coverage_by_year(ncons, naive_security_map(smap, ncons), prices, cal, BACKTEST_YEARS,
                                raw_prices=raw, split_factors=factors)
    naive.to_parquet(CACHE / "coverage_naive_detail.parquet", index=False)
    print(f"coverage files written: {len(summary)} years, {len(detail):,} point-in-time and "
          f"{len(naive):,} naive member-years")


if __name__ == "__main__":
    main()
