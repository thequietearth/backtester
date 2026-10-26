"""Audit what the strategies actually held: price moves on held days that can't be real.

Usage: python scripts/audit_holdings.py [--variants]   (after scripts/build_data.py)

The coverage report's checks keep broken series out of the *ranking*, but a stock bought
before its data breaks is still held (CLAUDE.md rule 10: holding-period moves are kept,
because real crashes must stay in the results). So this lists every day on which a held
position moved in a way that needs a human verdict:
  - glitch: the adjusted price moves >25% while the traded price moves <10%. Always a data
    error (a split applied twice, a split that never happened);
  - jump: the adjusted price doubles or halves in a day. Real crashes (Lehman, Enron) and
    broken series (a code turning into another instrument) look alike, so each is judged
    by hand and either kept or fixed in data/ticker_map.csv / data/price_exclusions.csv.
It runs last year's top 50 and worst 50 (whose holdings include every smaller N), momentum
and low volatility over 1999-2025 in both universes; the worst 50 uses the crash review
(data/crash_review.csv). --variants adds all 36 momentum variants of the M6 robustness grid
(point-in-time only), whose holdings differ from the published rule's. Verdicts are recorded in docs/sanity-check.md.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bt.coverage import ADJ_MOVE, JUMP, RAW_STILL, load_crash_review, rankable_by_date, rankable_universe  # noqa: E402
from bt.data import load_tbill  # noqa: E402
from bt.report import backtest_window, monthly_decisions, run_strategy  # noqa: E402
from bt.robustness import variant_grid  # noqa: E402
from bt.strategies import bottom_n, low_volatility, momentum, top_n  # noqa: E402
from bt.universe import formation_dates  # noqa: E402

CACHE = ROOT / "data" / "cache"


def held_moves(holdings: pd.DataFrame, prices: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    """Glitches and jumps on days a position was held at the previous close."""
    adj_move = np.log(prices).diff().abs()
    raw_move = np.log(raw.reindex_like(prices)).diff().abs()
    kind = pd.DataFrame("", index=prices.index, columns=prices.columns)
    kind = kind.mask(adj_move > JUMP, "jump").mask((adj_move > ADJ_MOVE) & (raw_move < RAW_STILL), "glitch")
    h = holdings.drop(columns="cash")
    exposed = (h.shift() > 0) & (kind.reindex(index=h.index, columns=h.columns) != "")
    rows = []
    for i, j in zip(*np.nonzero(exposed.to_numpy())):
        day, code = h.index[i], h.columns[j]
        before = prices[code].loc[:day].dropna().iloc[-2:]
        traded = raw[code].loc[:day].dropna().iloc[-2:]
        rows.append({"date": day.date(), "code": code, "kind": kind.at[day, code],
                     "weight %": round(100 * h.iloc[i - 1, j], 2),
                     "adjusted move %": round(100 * (before.iloc[-1] / before.iloc[0] - 1)),
                     "traded move %": round(100 * (traded.iloc[-1] / traded.iloc[0] - 1)),
                     "effect, pts": round(100 * h.iloc[i - 1, j] * (before.iloc[-1] / before.iloc[0] - 1), 2)})
    return pd.DataFrame(rows)


def main():
    prices = pd.read_parquet(CACHE / "prices.parquet")
    raw = pd.read_parquet(CACHE / "close.parquet")
    cal = prices["SPY"].dropna().index
    tbill = load_tbill(ROOT / "data" / "tbill_dtb3.csv")
    w = backtest_window(cal, 1999, 2025)
    found = []
    for mode in ("pit", "naive"):
        yearly = rankable_universe(pd.read_parquet(CACHE / f"coverage_{mode}_detail.parquet"),
                                   formation_dates(cal, w.years))
        monthly = rankable_by_date(pd.read_parquet(CACHE / f"universe_monthly_{mode}.parquet"))
        crashes = rankable_universe(pd.read_parquet(CACHE / f"coverage_{mode}_detail.parquet"),
                                    formation_dates(cal, w.years),
                                    real_crashes=load_crash_review(ROOT / "data" / "crash_review.csv"))
        strategies = {"top 50": top_n(prices, yearly, w.rebalance, n=50),
                      "worst 50": bottom_n(prices, crashes, w.rebalance, n=50),
                      "momentum": momentum(prices, monthly, monthly_decisions(cal, w)),
                      "low volatility": low_volatility(prices, monthly, monthly_decisions(cal, w, every=3))}
        if "--variants" in sys.argv and mode == "pit":
            for v in variant_grid().itertuples(index=False):
                name = f"momentum {round(100 * v.fraction)}% {v.lookback}-{v.skip} every {v.every}"
                strategies[name] = momentum(prices, monthly, monthly_decisions(cal, w, every=v.every),
                                            lookback=v.lookback, skip=v.skip, fraction=v.fraction)
        for name, weights in strategies.items():
            run = run_strategy(name, weights, prices, 10, cal, w, tbill)
            moves = held_moves(run.holdings, prices, raw)
            if len(moves):
                found.append(moves.assign(universe=mode, strategy=name))
    if not found:
        print("No glitches or jumps on held days.")
        return
    df = pd.concat(found)[["universe", "strategy", "date", "code", "kind", "weight %", "adjusted move %",
                           "traded move %", "effect, pts"]]
    pd.set_option("display.width", 200)
    print(df.to_string(index=False))
    glitches = df[df.kind == "glitch"]
    print(f"\n{len(glitches)} glitch(es): always data errors, fix them." if len(glitches) else
          "\nNo glitches. Judge each jump: real (keep) or broken data (fix).")


if __name__ == "__main__":
    main()
