"""M2 sanity check: an equal-weight point-in-time S&P 500, built with our data and engine,
compared with RSP (the Invesco S&P 500 Equal Weight ETF) year by year.

Usage: python scripts/sanity_rsp.py
Run scripts/build_price_cache.py first. Writes data/cache/sanity_rsp.csv; the write-up
is docs/sanity-check.md.

Our version: on each formation date (last trading day of the year before) take every
member that can be held - it has a price at entry, its identity isn't suspect, and its
holding-year prices pass the price checks - and weight them equally. Trades at the next
close, 10 bps per side, buy and hold for the year. RSP differs on purpose: it rebalances
quarterly, charges a fee (0.40% a year until 2013, 0.20% since), and has no data gaps.
Some gap is expected; a year with an unusually large gap usually means a data problem.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bt.coverage import coverage_by_year  # noqa: E402
from bt.engine import run_backtest  # noqa: E402
from bt.metrics import yearly_returns  # noqa: E402
from bt.universe import formation_dates, load_constituents, members_on  # noqa: E402

CACHE = ROOT / "data" / "cache"
YEARS = range(2003, 2026)  # RSP started trading on 2003-04-30


def main():
    # --keep-suspect: hold members even if their holding-year prices fail the price checks.
    # Those checks also catch real crashes (AIG, -60% in a day in 2008), and dropping real
    # losers flatters the result, so comparing both versions shows what each costs.
    keep_suspect = "--keep-suspect" in sys.argv
    # --quarterly: rebalance at every quarter end like RSP (members as of that date), to test
    # whether the biggest yearly gaps come from rebalancing frequency rather than data.
    quarterly = "--quarterly" in sys.argv
    cons = load_constituents(ROOT / "data" / "constituents.parquet")
    smap = pd.read_csv(CACHE / "security_map.csv", parse_dates=["start", "end"])
    prices, raw, factors = (pd.read_parquet(CACHE / f) for f in
                            ("prices.parquet", "close.parquet", "split_factors.parquet"))
    cal = prices["SPY"].dropna().index
    # Coverage for year Y+1 checks the prices of year Y (its formation year) - exactly the
    # year we'd hold in year Y. So it tells us which holdings have broken prices.
    _, detail = coverage_by_year(cons, smap, prices, cal, range(YEARS[0], YEARS[-1] + 2),
                                 raw_prices=raw, split_factors=factors)
    fdates = formation_dates(cal, YEARS)

    rows, excluded = {}, []
    for y in YEARS:
        now = detail[detail.year == y]
        nxt = detail[(detail.year == y + 1) & detail.code.notna()].set_index("code")["status"]
        ok = now[now.holding_ok & ~now.status.isin(["no security", "suspect identity"])]
        bad = ok.code.map(nxt).eq("suspect prices") & (not keep_suspect)
        excluded.append({"year": y, "members": len(now), "held": int((~bad).sum()),
                         "not holdable": len(now) - len(ok), "broken holding prices": int(bad.sum())})
        held = ok.code[~bad]
        rows[fdates[y]] = {c: 1 / len(held) for c in held}
        if quarterly:  # also rebalance at the end of Mar, Jun and Sep, among that day's members
            broken = set(ok.code[bad])
            for m in (3, 6, 9):
                q = cal[(cal.year == y) & (cal.month == m)].max()
                spells = smap[(smap.start <= q) & (smap.end.isna() | (smap.end > q)) & smap.code.notna()
                              & ~((smap["flags"].fillna("").str.contains("small")) & (smap.status != "manual"))]
                members = set(members_on(cons, q))
                codes = [c for c, t in zip(spells.code, spells.ticker) if t in members and c not in broken
                         and c in prices.columns and pd.notna(prices.at[q, c])]
                rows[q] = {c: 1 / len(codes) for c in codes}
    weights = pd.DataFrame(rows).T.fillna(0.0).sort_index()

    result = run_backtest(weights, prices, cost_bps=10, calendar=cal)
    ours = yearly_returns(result.equity)
    rsp = yearly_returns(prices["RSP"].dropna())
    spy = yearly_returns(prices["SPY"].dropna().loc[fdates[YEARS[0]]:])
    table = pd.DataFrame({"equal_weight_ours": ours, "rsp": rsp, "spy": spy}).loc[YEARS[0]:YEARS[-1]]
    table["gap_pts"] = 100 * (table.equal_weight_ours - table.rsp)
    table = table.join(pd.DataFrame(excluded).set_index("year"))
    variant = ("_keep_suspect" if keep_suspect else "") + ("_quarterly" if quarterly else "")
    table.to_csv(CACHE / f"sanity_rsp{variant}.csv")

    pd.set_option("display.width", 200)
    show = table.copy()
    for col in ("equal_weight_ours", "rsp", "spy"):
        show[col] = (100 * show[col]).round(1)
    print(show.round(2).to_string())
    full = table.loc[2004:]  # 2003 is a partial year for RSP
    print(f"\nfull years 2004-{YEARS[-1]}: mean gap {full.gap_pts.mean():+.2f} pts, "
          f"median {full.gap_pts.median():+.2f}, typical size (median |gap|) {full.gap_pts.abs().median():.2f}, "
          f"correlation {full.equal_weight_ours.corr(full.rsp):.4f}")
    big = full[full.gap_pts.abs() > 3 * full.gap_pts.abs().median()]
    print("years with an unusually large gap (> 3x the typical size):",
          ", ".join(f"{y} ({g:+.1f})" for y, g in big.gap_pts.items()) or "none")
    exits = result.trades[result.trades.action == "exit"]
    print(f"positions exited because data ended: {len(exits)}")


if __name__ == "__main__":
    main()
