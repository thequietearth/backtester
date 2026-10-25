"""Build the coverage results the app reads, so it never has to recompute them.

Usage: python scripts/build_universes.py   (after scripts/build_price_cache.py)
Outputs (gitignored, data/cache/):
  coverage_pit_summary.parquet  one row per year: members, coverage %, band...
  coverage_pit_detail.parquet   one row per year and member: status, flags...
  coverage_naive_detail.parquet the same for the naive universe (today's members only)
  universe_monthly_pit.parquet  one row per month-end and member: may it be ranked, or why not
  universe_monthly_naive.parquet the same for the naive universe
The app builds each year's rankable universe from the detail files (bt.coverage.rankable_universe),
and each month's from the monthly files (bt.coverage.rankable_by_date). The monthly universes
must agree with the coverage report on every year-end, or nothing is written.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bt.coverage import coverage_by_year, decision_universe  # noqa: E402
from bt.universe import formation_dates, load_constituents, month_ends, naive_constituents, naive_security_map  # noqa: E402

CACHE = ROOT / "data" / "cache"
REPORT_YEARS = range(1996, 2026)  # the coverage report shows 1996-98 to document the start year
BACKTEST_YEARS = range(1999, 2026)


def check_agreement(monthly: pd.DataFrame, detail: pd.DataFrame, cal, label: str):
    """On year-ends, the monthly universe must give every member the same status as the
    coverage report (whose "no holding data" may be ranked, so counts as "ok")."""
    fd = formation_dates(cal, sorted(detail.year.unique()))
    report = detail.assign(date=detail.year.map(fd), status=detail.status.replace({"no holding data": "ok"}))
    both = monthly.merge(report[["date", "ticker", "status"]], on=["date", "ticker"], how="inner",
                         suffixes=("", "_report"))
    if len(both) != len(report):
        raise SystemExit(f"{label}: monthly universe is missing {len(report) - len(both)} member-years")
    bad = both[both.status != both.status_report]
    if len(bad):
        raise SystemExit(f"{label}: monthly universe disagrees with the coverage report:\n{bad.head(20)}")
    print(f"{label}: monthly universe agrees with the coverage report on all {len(fd)} year-ends")


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

    # Month-end universes for the monthly and quarterly strategies, from the first formation
    # date (end of 1998) to the end of the last backtest year.
    dates = month_ends(cal, formation_dates(cal, [BACKTEST_YEARS[0]]).iloc[0], f"{BACKTEST_YEARS[-1]}-12-31")
    for label, c, m, report in (("pit", cons, smap, detail),
                                ("naive", ncons, naive_security_map(smap, ncons), naive)):
        monthly = decision_universe(c, m, prices, cal, dates, raw_prices=raw, split_factors=factors)
        check_agreement(monthly, report[report.year.isin(BACKTEST_YEARS)], cal, label)
        monthly.to_parquet(CACHE / f"universe_monthly_{label}.parquet", index=False)
        ok = monthly[monthly.status == "ok"].groupby("date").size()
        print(f"universe_monthly_{label}.parquet: {len(dates)} month-ends, {ok.min()}-{ok.max()} rankable members")


if __name__ == "__main__":
    main()
