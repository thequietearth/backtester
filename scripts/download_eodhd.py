"""Download EODHD prices, dividends and splits into the local cache.

Usage:
  python scripts/download_eodhd.py --codes SPY AAPL   specific EODHD codes
  python scripts/download_eodhd.py --scope v1         every candidate code for every S&P 500 member
                                                      since 1996, plus SPY, RSP and data/ticker_map.csv
  python scripts/download_eodhd.py --scope broad      all US common stocks and ETFs, active and delisted
Options:
  --kinds eod div splits   what to download (default: all three)
  --max-calls N            stop after N API calls (default: whatever is left of today's limit)

Resumable: anything already cached is skipped, so nothing is downloaded twice. Files are
written under a temporary name and renamed when complete, so an interrupted run can't
leave a half-written file behind. Requests run in parallel under one shared rate limit.
On the free plan, files go to data/raw/eodhd_free_test/ instead of data/raw/eodhd/, so
one-year free-tier data can never be mistaken for full history in the paid month.
Every request is logged to <cache>/download_log.csv.
"""
import argparse
import csv
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bt.data import (EODHDError, account_status, cache_file, call_budget, candidate_codes, get_json,  # noqa: E402
                     index_codes, load_api_key, parse_dividends, parse_eod, parse_splits,
                     split_payload)
from bt.universe import load_constituents  # noqa: E402

SYMBOLS = ROOT / "data" / "raw" / "eodhd"  # symbol lists are complete on every plan, so they live here
START = "1994-01-01"
BENCHMARKS = ["SPY", "RSP"]
ENDPOINTS = {"eod": parse_eod, "div": parse_dividends, "splits": parse_splits}
MIN_INTERVAL = 0.06  # seconds between calls, across all threads: ~1,000 a minute, under EODHD's 1,200 limit
WORKERS = 8  # parallel requests; each call waits ~0.5 s for EODHD, so one at a time manages only ~2 a second


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def symbol_list(key, kind, session) -> pd.DataFrame:
    """US symbol list ('active' or 'delisted'), cached. Fetching one costs a call."""
    path = SYMBOLS / f"symbols_us_{kind}.json"
    if not path.exists():
        data = get_json("exchange-symbol-list/US", key, {"delisted": 1} if kind == "delisted" else {},
                        session=session)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
    return pd.DataFrame(json.loads(path.read_text(encoding="utf-8")))


def manual_codes() -> list[str]:
    """EODHD codes added by hand in data/ticker_map.csv, once that file exists."""
    path = ROOT / "data" / "ticker_map.csv"
    return pd.read_csv(path, comment="#")["code"].dropna().astype(str).tolist() if path.exists() else []


def codes_for_scope(scope, key, session) -> list[str]:
    lists = pd.concat([symbol_list(key, "active", session), symbol_list(key, "delisted", session)])
    if scope == "broad":
        return sorted(set(lists.loc[lists["Type"].isin(["Common Stock", "ETF"]), "Code"].astype(str)))
    index = index_codes(lists["Code"].astype(str).unique())
    tickers = load_constituents(ROOT / "data" / "constituents.parquet")["ticker"].unique()
    codes = {c for t in tickers for c in candidate_codes(t, index)}
    return sorted(codes | set(BENCHMARKS) | set(manual_codes()))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument("--codes", nargs="+")
    what.add_argument("--scope", choices=["v1", "broad"])
    ap.add_argument("--kinds", nargs="+", choices=list(ENDPOINTS), default=list(ENDPOINTS))
    ap.add_argument("--max-calls", type=int)
    args = ap.parse_args()

    key = load_api_key(ROOT / ".env")
    session = requests.Session()
    acct = account_status(key, session)
    today = datetime.now(timezone.utc).date().isoformat()  # EODHD resets usage at midnight GMT
    used = (acct["used"] or 0) if acct["usage_date"] == today else 0
    cache = ROOT / "data" / "raw" / ("eodhd_free_test" if acct["plan"] == "free" else "eodhd")
    print(f"plan: {acct['plan']}   calls used today: {used}/{acct['daily_limit']}   "
          f"cache: {cache.relative_to(ROOT)}")

    codes = args.codes or codes_for_scope(args.scope, key, session)
    jobs = [(k, c) for c in codes for k in args.kinds if not cache_file(cache, k, c).exists()]
    budget = call_budget(acct["daily_limit"] or 0, used, args.max_calls)
    print(f"{len(codes):,} codes; {len(jobs):,} downloads to do; call budget {budget:,}")
    if len(jobs) > budget:
        print(f"only the first {budget:,} run now; rerun later to continue")

    log_path = cache / "download_log.csv"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not log_path.exists()
    counts = dict.fromkeys(["ok", "empty", "not_found", "warning", "forbidden", "error"], 0)
    limiter, stop = RateLimiter(MIN_INTERVAL), threading.Event()
    todo = jobs[:budget]
    with open(log_path, "a", newline="", encoding="utf-8") as fh, ThreadPoolExecutor(WORKERS) as pool:
        log = csv.writer(fh)  # only this (main) thread writes the log
        if is_new:
            log.writerow(["time_utc", "kind", "code", "status", "rows", "first", "last", "detail"])
        futures = {pool.submit(fetch, kind, code, key, cache, limiter, stop): (kind, code) for kind, code in todo}
        for n, fut in enumerate(as_completed(futures), 1):
            try:
                row = fut.result()
            except Exception as e:  # e.g. a file write failed: log it and carry on
                row = [*futures[fut], "error", 0, "", "", type(e).__name__]
            if row is None:  # skipped after a stop
                continue
            if row[2] == "stopped":
                print(f"stopping: {row[6]}")
                continue
            counts[row[2]] += 1
            log.writerow([utc_now(), *row])
            if n % 500 == 0:
                fh.flush()
                print(f"  {n:,}/{len(todo):,}  {counts}", flush=True)
    print(f"done: {counts}")


class RateLimiter:
    """Spaces calls at least `interval` seconds apart across all worker threads."""

    def __init__(self, interval: float):
        self.interval, self.lock, self.next_at = interval, threading.Lock(), 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            at = max(now, self.next_at)
            self.next_at = at + self.interval
        time.sleep(at - now)


_local = threading.local()


def thread_session() -> requests.Session:
    if not hasattr(_local, "session"):
        _local.session = requests.Session()
    return _local.session


def fetch(kind, code, key, cache, limiter, stop):
    """Download one (kind, code) into the cache. Returns a log row without the time,
    or None if skipped because another thread hit a reason to stop."""
    if stop.is_set():
        return None
    limiter.wait()
    parse, warnings = ENDPOINTS[kind], []
    try:
        records, warnings = split_payload(
            get_json(f"{kind}/{code}.US", key, {"from": START}, session=thread_session()))
        df, status = parse(records), "ok"
    except ValueError as e:  # the answer wasn't a list: log it, cache nothing
        return [kind, code, "error", 0, "", "", str(e)[:200]]
    except EODHDError as e:
        if e.status in (401, 402):  # bad key, or daily limit reached: stop every thread
            stop.set()
            return [kind, code, "stopped", 0, "", "", str(e)[:200]]
        if e.status != 404:  # 403 = not available on this plan; else failed after retries
            return [kind, code, "forbidden" if e.status == 403 else "error", 0, "", "", str(e)[:200]]
        df, status = parse([]), "not_found"  # the source's answer is "no such symbol": cache as empty
    detail = "; ".join(warnings)[:200]
    if warnings and df.empty:  # only a warning came back: don't cache, so a later run retries
        return [kind, code, "warning", 0, "", "", detail]
    if status == "ok" and df.empty:
        status = "empty"
    out = cache_file(cache, kind, code)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    df.to_parquet(tmp, index=False)
    os.replace(tmp, out)  # atomic rename: an interrupted run never leaves a half-written file that looks done
    first, last = (df["date"].min().date(), df["date"].max().date()) if len(df) else ("", "")
    return [kind, code, status, len(df), first, last, detail]


if __name__ == "__main__":
    main()
