"""Free upper-bound estimate of EODHD coverage per year, before paying.

Usage: python scripts/probe_eodhd_estimate.py <yahoo_probe_out_dir> data/raw/eodhd
Run probe_yahoo_coverage.py and probe_eodhd_symbols.py first.

Members Yahoo covers count as covered. For members Yahoo misses, count them as
'probably covered' if EODHD's delisted list has the ticker or ticker_old.
Upper bound: a listed symbol may lack 1990s prices or be a different company.
"""
import json
import sys
from pathlib import Path

import pandas as pd

yahoo, eod = Path(sys.argv[1]), Path(sys.argv[2])
report = pd.read_csv(yahoo / "coverage_by_year.csv")
missing = pd.read_csv(yahoo / "missing.csv")
delisted = pd.DataFrame(json.loads((eod / "symbols_us_delisted.json").read_text(encoding="utf-8")))
codes = set(delisted["Code"].astype(str))


def in_eodhd(t):
    c = t.replace(".", "-")
    return c in codes or f"{c}_old" in codes


missing["eodhd"] = missing["ticker"].map(in_eodhd)
add = missing.groupby("year")["eodhd"].sum()
rows = []
for _, r in report.iterrows():
    gained = int(add.get(r.year, 0))
    still = int(r.members - r.both_ok - gained)
    rows.append({"year": r.year, "members": r.members, "yahoo": r.both_ok,
                 "eodhd_adds": gained, "still_missing": still,
                 "est_coverage_pct": round(100 * (r.both_ok + gained) / r.members, 1)})
out = pd.DataFrame(rows)
print(out.to_string(index=False))
for y in (1996, 1997, 1998, 1999, 2000, 2005):
    m = missing[(missing.year == y) & ~missing.eodhd].ticker
    print(f"\n{y} still missing ({len(m)}): {', '.join(m)}")
