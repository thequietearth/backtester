"""Map every index-membership spell to an EODHD code, then build the price cache.

Usage: python scripts/build_price_cache.py
Run scripts/download_eodhd.py --scope v1 first.

Outputs (gitignored, data/cache/):
  security_map.csv   one row per (ticker, spell): chosen code, status, flags, evidence
  prices.parquet     adjusted close, one column per chosen code, plus SPY and RSP
  close.parquet      the traded (raw) close, same layout, for adjustment checks
  split_factors.parquet  cumulative split ratio for codes that ever split
Hand fixes go in data/ticker_map.csv (ticker, start, end, code, note) and always win.
Known-bad price dates go in data/price_exclusions.csv and are blanked before anything else.
Ends with the pass test on the known traps from docs/data-source-evaluation.md.
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bt.data import (apply_overrides, apply_price_exclusions, assess_candidate, cache_file,  # noqa: E402
                     candidate_codes, choose_security, index_codes)
from bt.universe import load_constituents, membership_spells  # noqa: E402

EODHD = ROOT / "data" / "raw" / "eodhd"
OUT = ROOT / "data" / "cache"
BENCHMARKS = ["SPY", "RSP"]


def price_exclusions() -> dict:
    """{code: [(start, end or None)]} from data/price_exclusions.csv."""
    path = ROOT / "data" / "price_exclusions.csv"
    if not path.exists():
        return {}
    out = {}
    for r in pd.read_csv(path, dtype=str, comment="#").itertuples():
        end = pd.Timestamp(r.end) if isinstance(r.end, str) and r.end.strip() else None
        out.setdefault(r.code, []).append((pd.Timestamp(r.start), end))
    return out


EXCLUSIONS = price_exclusions()


def load_eod(code, memo={}):
    """A code's cached prices, with known-bad dates blanked (data/price_exclusions.csv)."""
    if code not in memo:
        path = cache_file(EODHD, "eod", code)
        eod = pd.read_parquet(path) if path.exists() else None
        if eod is not None and code in EXCLUSIONS:
            eod = apply_price_exclusions(eod, EXCLUSIONS[code])
        memo[code] = eod
    return memo[code]


def symbol_names() -> dict[str, str]:
    names = {}
    for kind in ("active", "delisted"):
        for r in json.loads((EODHD / f"symbols_us_{kind}.json").read_text(encoding="utf-8")):
            names.setdefault(str(r["Code"]), r.get("Name") or "")
    return names


def main():
    names = symbol_names()
    index = index_codes(names)
    overrides_path = ROOT / "data" / "ticker_map.csv"
    # Hand-mapped codes apply only to the dates their override covers (apply_overrides);
    # they are not automatic candidates for the ticker's other spells.
    overrides = pd.read_csv(overrides_path, dtype=str, comment="#") if overrides_path.exists() else None

    spy = load_eod("SPY")
    calendar = pd.DatetimeIndex(spy["date"])
    as_of = calendar.max()
    spells = membership_spells(load_constituents(ROOT / "data" / "constituents.parquet"))
    n_spells = spells.groupby("ticker").size()

    rows = []
    for s in spells.itertuples():
        codes = set(candidate_codes(s.ticker, index))
        assessed = {c: assess_candidate(s.start, s.end, p, calendar, as_of)
                    for c in sorted(codes) if (p := load_eod(c)) is not None and len(p)}
        code, status, flags = choose_security(assessed, multi_spell=n_spells[s.ticker] > 1)
        a = assessed.get(code, {})
        rows.append({"ticker": s.ticker, "start": s.start, "end": s.end, "code": code,
                     "status": status, "flags": ",".join(flags), "name": names.get(code, ""),
                     "coverage": round(a.get("coverage", 0.0), 3),
                     "dollar_volume_m": round(a.get("dollar_volume", 0.0) / 1e6, 2),
                     "data_first": a.get("first"), "data_last": a.get("last"),
                     "candidates": "; ".join(f"{c} ({names.get(c, '')}, cov {v['coverage']:.2f})"
                                             for c, v in assessed.items())})
    smap = apply_overrides(pd.DataFrame(rows), overrides)
    # Re-measure hand-mapped rows against their (possibly split) date range, so the
    # evidence columns describe the code actually used.
    for i, r in smap[(smap.status == "manual") & smap.code.notna()].iterrows():
        p = load_eod(r.code)
        a = assess_candidate(r.start, r.end, p, calendar, as_of) if p is not None and len(p) else {}
        smap.loc[i, ["name", "coverage", "dollar_volume_m", "data_first", "data_last"]] = [
            names.get(r.code, ""), round(a.get("coverage", 0.0), 3),
            round(a.get("dollar_volume", 0.0) / 1e6, 2), a.get("first"), a.get("last")]
    OUT.mkdir(parents=True, exist_ok=True)
    smap.to_csv(OUT / "security_map.csv", index=False)

    codes = sorted(c for c in set(smap["code"].dropna()) | set(BENCHMARKS)
                   if load_eod(c) is not None and len(load_eod(c)))
    prices = pd.concat({c: load_eod(c).set_index("date")["adjusted_close"] for c in codes}, axis=1, sort=True)
    prices.to_parquet(OUT / "prices.parquet")
    # The traded (raw) close too: comparing it with the adjusted one exposes broken adjustments.
    pd.concat({c: load_eod(c).set_index("date")["close"] for c in codes}, axis=1, sort=True) \
        .to_parquet(OUT / "close.parquet")
    # Cumulative split ratio per code (only codes that ever split): traded close x factor
    # puts the traded price on the same basis as the adjusted one, minus dividends.
    factors = {}
    for c in codes:
        path = cache_file(EODHD, "splits", c)
        sp = pd.read_parquet(path) if path.exists() else None
        if sp is None or sp.empty:
            continue
        f = pd.Series(1.0, index=prices.index)
        for r in sp.dropna(subset=["ratio"]).itertuples():
            if r.ratio > 0:
                f[f.index >= r.date] *= r.ratio
        factors[c] = f
    pd.DataFrame(factors, index=prices.index).to_parquet(OUT / "split_factors.parquet")

    print(f"spells: {len(smap):,}   as of {as_of.date()}")
    print("status:", smap["status"].value_counts().to_dict())
    flags = smap["flags"].fillna("").str.split(",").explode()
    print("flags:", flags[flags != ""].value_counts().to_dict())
    print(f"prices.parquet: {prices.shape[1]:,} securities x {prices.shape[0]:,} days "
          f"({prices.index.min().date()} to {prices.index.max().date()})")

    # One security must never stand for two index members at the same time: an
    # equal-weight portfolio would hold it twice. (fja05680 lists a few companies twice.)
    far = pd.Timestamp.max
    shared = []
    for code, g in smap.dropna(subset=["code"]).groupby("code"):
        rows = list(g.itertuples())
        for i, a in enumerate(rows):
            for b in rows[i + 1:]:
                if a.ticker != b.ticker and a.start < (b.end if pd.notna(b.end) else far) \
                        and b.start < (a.end if pd.notna(a.end) else far):
                    shared.append(f"{code} ({a.ticker} and {b.ticker})")
    print("codes shared by two members at the same time:", ", ".join(shared) or "none")

    # Pass test 2: the known traps. Each row: (ticker, a date inside the spell, acceptable codes).
    # None in the acceptable set means "missing or flagged for review" is the right outcome.
    traps = [("WEN", "1997-12-31", {"WEN_old"}), ("EP", "2003-12-31", {"EP_old"}),
             ("EP", "2009-12-31", {"EP_old"}), ("FDO", "2008-12-31", {"FDO"}),
             ("AN", "1997-12-31", {None}), ("SNT", "1996-12-31", {None})]
    print("\ntraps:")
    for t, d, ok in traps:
        d = pd.Timestamp(d)
        row = smap[(smap.ticker == t) & (smap.start <= d) & (smap.end.isna() | (smap.end > d))]
        row = row.iloc[0] if len(row) else None
        if row is None:
            got, verdict = "no spell", "FAIL"
        else:
            code, status, flags = row["code"], row["status"], row["flags"]  # row.flags is a pandas attribute
            got = f"{code} [{status}{': ' + flags if flags else ''}] {row['name']}"
            safe = code in ok or (None in ok and (status in ("review", "missing")
                                                  or (status == "manual" and pd.isna(code))))
            verdict = "pass" if safe else "FAIL"
        print(f"  {verdict:4}  {t:4} {d.year}: {got}")


if __name__ == "__main__":
    main()
