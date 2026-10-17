"""Which stock would a Yahoo-only backtest pick as 'last year's #1' each year?

Usage: python scripts/probe_yahoo_top1.py <components.csv> <out_dir>
Run probe_yahoo_coverage.py first; this reuses its cached closes in <out_dir>.
Ranks only members with Yahoo prices on formation start and formation date.
"""
import sys
from pathlib import Path

import pandas as pd

comp_path, out = Path(sys.argv[1]), Path(sys.argv[2])
closes = pd.read_parquet(out / "closes.parquet")
comp = pd.read_csv(comp_path, parse_dates=["date"]).sort_values("date")
comp["tickers"] = comp["tickers"].str.split(",")
cal = closes["SPY"].dropna().index

rows = []
for Y in range(1996, 2026):
    fstart, fdate = cal[cal.year == Y - 2].max(), cal[cal.year == Y - 1].max()
    snap = comp[comp["date"] <= fdate]
    members = (snap.iloc[-1] if len(snap) else comp.iloc[0])["tickers"]
    syms = [t.replace(".", "-") for t in members if t.replace(".", "-") in closes.columns]
    ret = (closes.loc[fdate, syms] / closes.loc[fstart, syms] - 1).dropna().sort_values(ascending=False)
    top = ret.head(3)
    rows.append({"year": Y, "formation": Y - 1,
                 "pick": top.index[0], "form_ret": f"{top.iloc[0]:+.0%}",
                 "runners_up": ", ".join(f"{t} {r:+.0%}" for t, r in top.iloc[1:].items())})
print(pd.DataFrame(rows).to_string(index=False))
