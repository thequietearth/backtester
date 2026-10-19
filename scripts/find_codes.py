"""Find EODHD codes by company name, for hand mappings in data/ticker_map.csv.

Usage: python scripts/find_codes.py "lehman" "general motors" "^3com"
Each argument is a case-insensitive regular expression matched against company names
(and codes). Shows common stocks only, with the cached price range if downloaded.
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bt.data import cache_file  # noqa: E402

EODHD = ROOT / "data" / "raw" / "eodhd"


def main():
    lists = pd.concat([pd.DataFrame(json.loads((EODHD / f"symbols_us_{k}.json").read_text(encoding="utf-8")))
                       .assign(list=k) for k in ("active", "delisted")])
    lists = lists[lists["Type"] == "Common Stock"]
    for pattern in sys.argv[1:]:
        hits = lists[lists["Name"].fillna("").str.contains(pattern, case=False, regex=True)
                     | lists["Code"].astype(str).str.fullmatch(pattern, case=False)]
        print(f"--- {pattern}: {len(hits)} match(es)")
        for r in hits.head(8).itertuples():
            path = cache_file(EODHD, "eod", str(r.Code))
            if path.exists():
                d = pd.read_parquet(path)["date"]
                span = f"{d.min().date()} -> {d.max().date()}" if len(d) else "no prices"
            else:
                span = "not downloaded yet"
            print(f"    {r.Code:10} {r.Name[:42]:42} {r.list:8} {r.Exchange:8} {span}")


if __name__ == "__main__":
    main()
