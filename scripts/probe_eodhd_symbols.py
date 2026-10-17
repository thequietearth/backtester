"""Data-source probe, step 2: does EODHD know the six trap companies, and under which codes?

Context and pass tests: docs/data-source-evaluation.md

Uses 2 API calls (active + delisted US symbol lists). Both are cached in
data/raw/eodhd/ (gitignored, licensed data), so reruns cost nothing.
The API key is loaded from .env and never printed.

Usage: python scripts/probe_eodhd_symbols.py
"""
import json
import os
import sys
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "raw" / "eodhd"

# Names to look for: the real index members behind the traps, and the
# companies that hold those tickers today.
SEARCH = ["amoco", "sonat", "wendy", "el paso", "family dollar", "albertson",
          "autonation", "senstar", "empire petroleum", "triarc"]
TRAP_CODES = ["AN", "SNT", "WEN", "EP", "FDO", "ABS"]


def api_key():
    load_dotenv(ROOT / ".env")
    key = os.environ.get("EODHD_API_KEY", "").strip()
    if not key or key == "your-key-here":
        sys.exit("EODHD_API_KEY is missing or still the placeholder in .env")
    print(f"API key loaded ({len(key)} characters)")
    return key


def symbol_list(key, delisted):
    name = "delisted" if delisted else "active"
    path = CACHE / f"symbols_us_{name}.json"
    if path.exists():
        print(f"{name}: using cache {path.relative_to(ROOT)}")
        return pd.DataFrame(json.loads(path.read_text(encoding="utf-8")))
    params = {"api_token": key, "fmt": "json"}
    if delisted:
        params["delisted"] = 1
    try:
        r = requests.get("https://eodhd.com/api/exchange-symbol-list/US",
                         params=params, timeout=120)
    except requests.RequestException as e:
        # Report only the exception type: its message can contain the URL, and the URL holds the key.
        sys.exit(f"{name}: request failed ({type(e).__name__})")
    if r.status_code != 200:
        sys.exit(f"{name}: HTTP {r.status_code}: {r.text[:300]}")
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(r.text, encoding="utf-8")
    print(f"{name}: downloaded and cached")
    return pd.DataFrame(r.json())


key = api_key()
pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 60)
for delisted in (False, True):
    df = symbol_list(key, delisted)
    label = "DELISTED" if delisted else "ACTIVE"
    print(f"\n=== {label}: {len(df)} symbols; columns: {list(df.columns)}")
    if "Type" in df.columns:
        print(df["Type"].value_counts().head(6).to_string())
    names = df["Name"].fillna("").str.lower()
    hits = df[names.str.contains("|".join(SEARCH), regex=True)]
    print(f"\n{label} rows matching trap company names:")
    print(hits.to_string(index=False) if len(hits) else "  (none)")
    codes = df[df["Code"].isin(TRAP_CODES)]
    print(f"\n{label} rows whose code is a trap ticker:")
    print(codes.to_string(index=False) if len(codes) else "  (none)")
