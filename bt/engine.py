"""Backtest engine: target weights + prices + costs -> daily equity curve,
holdings and trade log.

The engine doesn't know which strategy produced the weights, or anything about the
index. Rules (CLAUDE.md):
- Timing: weights decided at the close of day t trade at the close of the next trading
  day, so a decision can only use what was known at t.
- Between trades, positions move with their own adjusted (total-return) prices and are
  never re-weighted: buy and hold. Unused weight is cash, earning 0%.
- Costs: cost_bps of the value traded, on every trade. After a rebalance each position is
  exactly its target share of the post-cost equity E', which solves
      E' = E - c * sum(|w_i * E' - V_i|)        (c = cost_bps / 10,000)
  so costs are exact and cash never goes negative.
- Data ends while held: the position is sold at its last available price (paying the
  cost), the money goes to cash, and the trade is flagged "data ended, real outcome
  unknown". A short gap in prices is not an ending: the position is held at its last value.
- No price on a trade date: a new purchase is skipped (that weight stays cash); a held
  position is kept as it is. Both are logged.
- No leverage or short selling: weights must be >= 0 and sum to at most 1.
"""
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

DATA_ENDED = "data ended, real outcome unknown"
NO_PRICE = "no price on the trade date"


@dataclass
class BacktestResult:
    equity: pd.Series      # portfolio value at each close, from the first trade
    holdings: pd.DataFrame  # each position's share of equity, plus "cash"
    trades: pd.DataFrame   # date, code, action, value, price, cost, note


def _validate(weights: pd.DataFrame) -> pd.DataFrame:
    w = weights.fillna(0.0)
    if (w < 0).to_numpy().any():
        raise ValueError("negative weights: short selling is out of scope")
    if (w.sum(axis=1) > 1 + 1e-9).any():
        raise ValueError("weights sum to more than 1: leverage is out of scope")
    return w


def _post_trade_equity(equity: float, target: dict, current: dict, c: float) -> float:
    """Solve E' = E - c * sum(|w_i E' - V_i|) by fixed-point iteration. The map shrinks
    distances by at most c * sum(w) < 1, so it converges fast (a few steps at 10 bps)."""
    e = equity
    for _ in range(100):
        nxt = equity - c * sum(abs(w * e - current.get(k, 0.0)) for k, w in target.items())
        if abs(nxt - e) <= 1e-15 * max(1.0, abs(equity)):
            return nxt
        e = nxt
    return e


def _trade_plan(weights: pd.DataFrame, calendar: pd.DatetimeIndex) -> dict:
    """Map each decision date to the next trading day: {trade date: target weights}."""
    plan = {}
    for d, row in weights.iterrows():
        later = calendar[calendar > d]
        if len(later) == 0:
            warnings.warn(f"decision on {pd.Timestamp(d).date()} has no trading day after it, so it can't trade")
            continue
        plan[later[0]] = row[row > 0].to_dict()
    return plan


def run_backtest(weights: pd.DataFrame, prices: pd.DataFrame, cost_bps: float = 10.0,
                 initial: float = 1.0, calendar=None) -> BacktestResult:
    """Run target weights (rows = decision dates, columns = codes) through prices
    (adjusted close, one column per code). `calendar` defaults to the price dates."""
    c = cost_bps / 10_000
    w = _validate(weights)
    cal = pd.DatetimeIndex(calendar if calendar is not None else prices.index)
    px = prices.reindex(cal)
    plan = _trade_plan(w, cal)
    empty = BacktestResult(pd.Series(dtype=float), pd.DataFrame(),
                           pd.DataFrame(columns=["date", "code", "action", "value", "price", "cost", "note"]))
    if not plan:
        return empty
    last_valid = {k: px[k].last_valid_index() for k in px.columns}

    positions: dict[str, float] = {}  # code -> value
    marks: dict[str, float] = {}      # code -> price the value was last marked at
    cash = initial
    dates, equity, holdings, trades = [], [], [], []
    for t in cal[cal >= min(plan)]:
        # 1. Mark to market, and exit positions whose data has ended.
        for k in list(positions):
            p = px.at[t, k]
            if pd.notna(p):
                positions[k] *= p / marks[k]
                marks[k] = p
            elif last_valid[k] is None or last_valid[k] < t:
                value = positions.pop(k)
                cost = c * value
                cash += value - cost
                trades.append({"date": t, "code": k, "action": "exit", "value": value,
                               "price": marks.pop(k), "cost": cost, "note": DATA_ENDED})
            # else: a temporary gap - keep the last value

        # 2. Rebalance on trade dates.
        if t in plan:
            target = plan[t]
            priced = {k for k in set(target) | set(positions) if k in px.columns and pd.notna(px.at[t, k])}
            kept = {k: v for k, v in positions.items() if k not in priced}
            for k in sorted(kept):
                trades.append({"date": t, "code": k, "action": "kept", "value": 0.0, "price": np.nan,
                               "cost": 0.0, "note": NO_PRICE + ": position kept"})
            for k in sorted(set(target) - priced - set(positions)):
                trades.append({"date": t, "code": k, "action": "skipped", "value": 0.0, "price": np.nan,
                               "cost": 0.0, "note": NO_PRICE})
            tradeable = {k: target.get(k, 0.0) for k in priced}
            current = {k: positions.get(k, 0.0) for k in priced}
            e_before = cash + sum(positions.values())
            e_after = _post_trade_equity(e_before, tradeable, current, c)
            new = {k: wk * e_after for k, wk in tradeable.items() if wk > 0}
            room = e_after - sum(kept.values())
            if sum(new.values()) > room:  # only possible when a held position couldn't be sold
                scale = room / sum(new.values())
                new = {k: v * scale for k, v in new.items()}
            for k in sorted(tradeable):
                delta = new.get(k, 0.0) - current[k]
                if abs(delta) > 1e-15:
                    trades.append({"date": t, "code": k, "action": "buy" if delta > 0 else "sell",
                                   "value": abs(delta), "price": px.at[t, k], "cost": c * abs(delta), "note": ""})
            positions = {**kept, **new}
            for k in new:
                marks[k] = px.at[t, k]
            for k in set(marks) - set(positions):
                marks.pop(k)
            cash = e_after - sum(positions.values())

        total = cash + sum(positions.values())
        dates.append(t)
        equity.append(total)
        holdings.append({**{k: v / total for k, v in positions.items()}, "cash": cash / total})

    return BacktestResult(
        equity=pd.Series(equity, index=pd.DatetimeIndex(dates), name="equity"),
        holdings=pd.DataFrame(holdings, index=pd.DatetimeIndex(dates)).fillna(0.0),
        trades=pd.DataFrame(trades, columns=["date", "code", "action", "value", "price", "cost", "note"]),
    )
