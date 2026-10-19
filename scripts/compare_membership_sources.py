"""M1 step 1: compare point-in-time S&P 500 membership sources at every year-end.

Sources:
  - fja05680/sp500 (MIT): one row per change date, tickers as used at the time.
  - Wikipedia rebuild: today's list ("List of S&P 500 companies"), walked backwards
    through the changes table, which moved in 2026 to "Historical components of the
    S&P 500" (undo each addition, re-add each removal). This is also Robot Wealth's method.

Usage: python scripts/compare_membership_sources.py <fja05680_components.csv>
Wikipedia pages are cached in data/raw/wikipedia/ (one fetch per page per day at most).
"""
import io
import json
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
WIKI_CACHE = ROOT / "data" / "raw" / "wikipedia"
UA = "backtester-research/0.1 (https://github.com/thequietearth/backtester)"
YEARS = range(1995, 2026)


def wikipedia_html(page, stem):
    path = WIKI_CACHE / f"{stem}_{date.today()}.html"
    if not path.exists():
        r = requests.get("https://en.wikipedia.org/w/api.php", headers={"User-Agent": UA}, timeout=60,
                         params={"action": "parse", "page": page,
                                 "prop": "text", "format": "json", "formatversion": 2})
        r.raise_for_status()
        WIKI_CACHE.mkdir(parents=True, exist_ok=True)
        path.write_text(r.json()["parse"]["text"], encoding="utf-8")
    return path.read_text(encoding="utf-8")


def clean(x):
    """Strip footnote markers like [12] and whitespace; empty -> None."""
    if pd.isna(x):
        return None
    s = re.sub(r"\[.*?\]", "", str(x)).strip()
    return s or None


def wikipedia_tables():
    current_html = wikipedia_html("List_of_S&P_500_companies", "sp500")
    changes_html = wikipedia_html("Historical_components_of_the_S&P_500", "sp500_historical")
    current = pd.read_html(io.StringIO(current_html), attrs={"id": "constituents"})[0]
    changes = pd.read_html(io.StringIO(changes_html), attrs={"id": "changes"})[0]
    changes.columns = ["date", "added", "added_name", "removed", "removed_name", "reason", "refs"]
    for c in changes.columns:
        changes[c] = changes[c].map(clean)
    changes["date"] = pd.to_datetime(changes["date"], format="mixed")
    return current, changes.sort_values("date", ascending=False).reset_index(drop=True)


def wikipedia_snapshots(current, changes):
    """Walk backwards from today's list. Returns {year: set} and a log of undo failures."""
    members = set(current["Symbol"].map(clean))
    snaps, failures = {}, []
    i = 0
    for y in sorted(YEARS, reverse=True):
        cutoff = pd.Timestamp(y, 12, 31)
        while i < len(changes) and changes.loc[i, "date"] > cutoff:
            row = changes.loc[i]
            if isinstance(row.added, str):
                if row.added in members:
                    members.discard(row.added)
                else:
                    failures.append((row.date.date(), "added ticker not in set", row.added, row.added_name))
            if isinstance(row.removed, str):
                if row.removed in members:
                    failures.append((row.date.date(), "removed ticker already in set", row.removed, row.removed_name))
                members.add(row.removed)
            i += 1
        snaps[y] = set(members)
    return snaps, failures


def fja_snapshots(path):
    comp = pd.read_csv(path, parse_dates=["date"]).sort_values("date")
    snaps = {}
    for y in YEARS:
        rows = comp[comp["date"] <= pd.Timestamp(y, 12, 31)]
        row = rows.iloc[-1] if len(rows) else comp.iloc[0]
        snaps[y] = set(row["tickers"].split(","))
    return snaps


current, changes = wikipedia_tables()
wiki, failures = wikipedia_snapshots(current, changes)
fja = fja_snapshots(Path(sys.argv[1]))

print(f"Wikipedia: {len(current)} current members, {len(changes)} change rows, "
      f"oldest change {changes['date'].min().date()}")
per_decade = changes.groupby((changes["date"].dt.year // 5) * 5).size()
print("change rows per 5-year block:", ", ".join(f"{k}-{k + 4}: {v}" for k, v in per_decade.items()))

rows = []
for y in YEARS:
    a, b = fja[y], wiki[y]
    rows.append({"year_end": y, "fja": len(a), "wiki": len(b), "both": len(a & b),
                 "only_fja": len(a - b), "only_wiki": len(b - a)})
print("\n" + pd.DataFrame(rows).to_string(index=False))

print(f"\nWikipedia undo failures: {len(failures)} (first 15 shown)")
for f in failures[:15]:
    print("  ", f)

# Known events: should the ticker be a member at that year-end?
checks = [("AN", 1997, True, "Amoco"), ("AN", 1999, False, "Amoco gone (BP merger)"),
          ("SNT", 1996, True, "Sonat"), ("SNT", 1999, False, "Sonat gone (El Paso)"),
          ("WEN", 1997, True, "Wendy's Intl"), ("EP", 2003, True, "El Paso"), ("EP", 2009, True, "El Paso"),
          ("FDO", 2008, True, "Family Dollar"), ("ENE", 2000, True, "Enron"), ("ENE", 2001, False, "Enron gone"),
          ("ENRNQ", 2000, True, "Enron, bankruptcy ticker"),
          ("LEH", 2007, True, "Lehman"), ("LEH", 2008, False, "Lehman gone"),
          ("LEHMQ", 2007, True, "Lehman, bankruptcy ticker"),
          ("TSLA", 2019, False, "Tesla not yet"), ("TSLA", 2020, True, "Tesla added 21 Dec 2020")]
print("\nKnown events (expected member? -> fja / wiki):")
for t, y, expect, note in checks:
    got_f, got_w = t in fja[y], t in wiki[y]
    mark = lambda g: "ok" if g == expect else "WRONG"
    print(f"  {t:5} end-{y}  expect {'in ' if expect else 'out'}  fja:{mark(got_f):5}  wiki:{mark(got_w):5}  ({note})")

# Names for the tickers each source disagrees on, from Wikipedia's change table (useful for review)
names = pd.concat([changes[["added", "added_name"]].set_axis(["t", "n"], axis=1),
                   changes[["removed", "removed_name"]].set_axis(["t", "n"], axis=1)]).dropna().drop_duplicates("t")
name_of = dict(zip(names.t, names.n))
for y in (2020, 2025):
    of, ow = sorted(fja[y] - wiki[y]), sorted(wiki[y] - fja[y])
    print(f"\nend-{y}: only in fja ({len(of)}): {', '.join(of[:25])}{' ...' if len(of) > 25 else ''}")
    print(f"end-{y}: only in wiki ({len(ow)}): {', '.join(f'{t} ({name_of.get(t, "?")})' for t in ow[:15])}{' ...' if len(ow) > 15 else ''}")
