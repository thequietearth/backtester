"""M6: is momentum's lead over SPY real? Pure functions for the robustness check.

A strategy that only works with one exact set of settings is probably a fluke of history
("curve fitting"). So the momentum rule is re-run with every combination of reasonable
settings, and all variants are judged together: how many beat SPY, in which eras, at what
cost, and how likely each lead is to be luck. The grid and the verdict criteria were fixed
before any results were seen (PLAN.md, M6). Picking the best variant afterwards would
mostly find the luckiest one, so the best variant is never the headline.
"""
import itertools

import numpy as np
import pandas as pd

# The rule published in M5b.
DEFAULT = {"fraction": 0.10, "lookback": 12, "skip": 1, "every": 1}
GRID = {"fraction": (0.05, 0.10, 0.20),  # share of the universe held
        "lookback": (6, 9, 12),          # months of past return ranked on
        "skip": (1, 0),                  # skip the latest month (1) or not (0)
        "every": (1, 3)}                 # rebalance every month (1) or quarter (3)
ERAS = ((1999, 2009), (2010, 2025))
ROBUST_SHARE, ERA_SHARE, FRAGILE_SHARE = 0.75, 0.5, 0.5


def variant_grid() -> pd.DataFrame:
    """Every combination of the settings in GRID: 3 x 3 x 2 x 2 = 36 variants."""
    return pd.DataFrame(list(itertools.product(*GRID.values())), columns=list(GRID))


def lead_stats(strategy_yearly: pd.Series, spy_yearly: pd.Series, n_boot: int = 20_000, seed: int = 0) -> dict:
    """How the yearly lead over SPY (strategy return minus SPY's, same years) behaves.

    t_stat: mean lead / (its standard deviation / sqrt(number of years)). Around 2 or more
    is the usual bar for "probably not luck"; it asks whether the average lead is large
    compared with how much the lead swings from year to year.
    share_no_lead: resample the years with replacement many times (a bootstrap: other
    possible orderings of the same good and bad years) and count how often the average
    lead comes out zero or negative.
    """
    lead = (strategy_yearly - spy_yearly).dropna().to_numpy()
    mean, sd = lead.mean(), lead.std(ddof=1)
    t = mean / (sd / np.sqrt(len(lead))) if sd > 0 else np.nan
    boot = np.random.default_rng(seed).choice(lead, size=(n_boot, len(lead))).mean(axis=1)
    return {"mean_lead": mean, "sd_lead": sd, "t_stat": t, "share_no_lead": float((boot <= 0).mean())}


def era_lead(strategy_yearly: pd.Series, spy_yearly: pd.Series, first: int, last: int) -> float:
    """Lead in return per year over the years first..last: each side compounded over the
    era, then the difference (0.02 = 2 points a year ahead of SPY)."""
    def per_year(r):
        r = r.loc[first:last]
        return (1 + r).prod() ** (1 / len(r)) - 1
    return per_year(strategy_yearly) - per_year(spy_yearly)


def break_even_cost(costs, cagrs, target: float) -> float:
    """The trading cost (bps per side) at which the strategy's return per year falls to
    `target` (SPY's), interpolating linearly between measured costs. 0 if it doesn't beat
    the target even without costs; beyond the highest measured cost, the last segment's
    slope is extended."""
    costs, cagrs = np.asarray(costs, float), np.asarray(cagrs, float)
    if cagrs[0] <= target:
        return 0.0
    for i in range(1, len(costs)):
        if cagrs[i] <= target:
            return float(np.interp(target, [cagrs[i], cagrs[i - 1]], [costs[i], costs[i - 1]]))
    slope = (cagrs[-1] - cagrs[-2]) / (costs[-1] - costs[-2])
    return float(costs[-1] + (target - cagrs[-1]) / slope) if slope < 0 else np.inf


def verdict(share_beating: float, share_beating_first_era: float, share_beating_second_era: float) -> str:
    """The criteria fixed before running: "robust" if at least 75% of variants beat SPY
    over the whole period and a majority beat it in each era; "fragile" if fewer than half
    beat it; otherwise "mixed"."""
    if share_beating < FRAGILE_SHARE:
        return "fragile"
    if share_beating >= ROBUST_SHARE and min(share_beating_first_era, share_beating_second_era) > ERA_SHARE:
        return "robust"
    return "mixed"
