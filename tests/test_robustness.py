"""Tests for bt.robustness: the M6 variant grid and the statistics that judge it, on
numbers small enough to work out by hand."""
import numpy as np
import pandas as pd
import pytest

from bt.robustness import (DEFAULT, break_even_cost, era_lead, lead_stats, variant_grid, verdict)


def test_the_grid_has_36_variants_including_the_published_rule():
    grid = variant_grid()
    assert len(grid) == 36 and len(grid.drop_duplicates()) == 36
    assert set(grid.columns) == {"fraction", "lookback", "skip", "every"}
    assert set(grid.fraction) == {0.05, 0.10, 0.20} and set(grid.lookback) == {6, 9, 12}
    assert set(grid.skip) == {0, 1} and set(grid.every) == {1, 3}
    # The rule M5b published: top 10%, 12 months skipping the latest, monthly.
    assert DEFAULT == {"fraction": 0.10, "lookback": 12, "skip": 1, "every": 1}
    assert (grid == pd.Series(DEFAULT)).all(axis=1).sum() == 1


def test_lead_stats_by_hand():
    # Yearly leads over SPY of +2, +4 and +6 points: mean 4, standard deviation 2,
    # t = 4 / (2 / sqrt(3)) = 3.46. Every resampled history has a positive average lead.
    years = [2001, 2002, 2003]
    strat = pd.Series([0.12, 0.14, 0.16], index=years)
    spy = pd.Series([0.10, 0.10, 0.10], index=years)
    s = lead_stats(strat, spy, n_boot=2000, seed=0)
    assert s["mean_lead"] == pytest.approx(0.04)
    assert s["sd_lead"] == pytest.approx(0.02)
    assert s["t_stat"] == pytest.approx(0.04 / (0.02 / np.sqrt(3)))
    assert s["share_no_lead"] == 0.0


def test_lead_stats_when_the_strategy_always_trails():
    years = [2001, 2002, 2003, 2004]
    s = lead_stats(pd.Series([0.05, 0.02, 0.07, 0.01], index=years), pd.Series(0.10, index=years), n_boot=500, seed=1)
    assert s["mean_lead"] < 0 and s["t_stat"] < 0
    assert s["share_no_lead"] == 1.0  # no resampled history has a lead


def test_era_lead_compounds_each_side_over_the_era():
    # 2010-2011: strategy +21% and 0% -> (1.21 * 1.00) ** (1/2) - 1 = 10% a year;
    # SPY +10% both years -> 10% a year. Lead 0. 2012: strategy +30%, SPY +10% -> +20 points.
    years = [2010, 2011, 2012]
    strat, spy = pd.Series([0.21, 0.0, 0.30], index=years), pd.Series([0.10, 0.10, 0.10], index=years)
    assert era_lead(strat, spy, 2010, 2011) == pytest.approx(0.0, abs=1e-12)
    assert era_lead(strat, spy, 2012, 2012) == pytest.approx(0.20)


def test_break_even_cost_interpolates_between_measured_costs():
    # 10.0% a year at 0 bps, 9.2% at 10, 7.6% at 30: SPY's 8.4% is reached halfway between
    # 10 and 30 bps, at 20.
    assert break_even_cost([0, 10, 30], [10.0, 9.2, 7.6], 8.4) == pytest.approx(20.0)
    # No lead even without costs: break-even at 0.
    assert break_even_cost([0, 10, 30], [8.0, 7.2, 5.6], 8.4) == 0.0
    # Still ahead at the highest measured cost: extend the last segment's slope.
    assert break_even_cost([0, 10, 30], [12.0, 11.2, 9.6], 8.4) == pytest.approx(45.0)


def test_verdict_follows_the_criteria_fixed_before_the_results():
    # Robust: at least 75% of variants beat SPY over the whole period, and a majority in
    # each era. Fragile: fewer than half beat SPY. Anything else: mixed.
    assert verdict(0.80, 0.60, 0.55) == "robust"
    assert verdict(0.80, 0.90, 0.40) == "mixed"  # fails in one era
    assert verdict(0.60, 0.70, 0.60) == "mixed"
    assert verdict(0.40, 0.90, 0.10) == "fragile"
