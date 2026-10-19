"""Build data/constituents.parquet from the fja05680/sp500 membership file.

Usage: python scripts/build_constituents.py data/raw/fja05680_components.csv

Input: "S&P 500 Historical Components & Changes (Updated).csv" from
github.com/fja05680/sp500 (MIT licence; notice in data/LICENSE-fja05680.txt).
Output: one row per (date, ticker) for every change date. Small enough to commit.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bt.universe import membership_spells  # noqa: E402

OUT = ROOT / "data" / "constituents.parquet"

src = pd.read_csv(sys.argv[1], parse_dates=["date"])
cons = src.assign(ticker=src["tickers"].str.split(",")).explode("ticker")[["date", "ticker"]]
cons["ticker"] = cons["ticker"].str.strip()
cons = (cons[cons["ticker"] != ""].drop_duplicates()
        .sort_values(["date", "ticker"]).reset_index(drop=True))
cons.to_parquet(OUT, index=False)

counts = cons.groupby("date").size()
spells = membership_spells(cons)
print(f"wrote {OUT.relative_to(ROOT)}: {len(cons):,} rows, {OUT.stat().st_size / 1e6:.1f} MB")
print(f"snapshots: {counts.size:,} from {counts.index.min().date()} to {counts.index.max().date()}; "
      f"members per snapshot {counts.min()}-{counts.max()}")
print(f"tickers: {spells.ticker.nunique():,}; membership spells: {len(spells):,} "
      f"({(spells.groupby('ticker').size() > 1).sum()} tickers left and rejoined)")
