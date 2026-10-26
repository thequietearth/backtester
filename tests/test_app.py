"""The app renders without errors for several settings (Streamlit's test runner).

Needs the local data cache (scripts/build_data.py), so it is skipped on a fresh clone
without data.
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "cache" / "coverage_pit_detail.parquet").exists(),
                                reason="needs the local data cache (scripts/build_data.py)")


def app():
    return AppTest.from_file(str(ROOT / "app.py"), default_timeout=300).run()


def test_default_view():
    at = app()
    assert not at.exception
    comparison = at.dataframe[0].value
    assert list(comparison["Strategy"]) == ["Last year's #1", "Last year's top 10", "SPY (benchmark)"]
    assert "Invested" in comparison.columns and "Trades/yr" in comparison.columns
    assert len(at.dataframe) == 3  # the comparison, plus a year-by-year table for each strategy


def test_comparison_of_four_strategies_including_timing_rules():
    at = app()
    at.multiselect(key="strategies").set_value(
        ["Last year's top N", "SPY 200-day trend", "SPY golden cross (50/200 days)", "SPY RSI(2) dip-buying"])
    at.run()
    assert not at.exception
    comparison = at.dataframe[0].value
    assert len(comparison) == 5  # four strategies and SPY
    trend = comparison[comparison.Strategy == "SPY 200-day trend"].iloc[0]
    assert trend["Invested"] != "100%"  # it does sit in cash sometimes


def test_momentum_and_low_volatility_show_portfolio_holdings():
    at = app()
    at.multiselect(key="strategies").set_value(["Momentum (top 10%, monthly)", "Low volatility (50 calmest, quarterly)"])
    at.run()
    assert not at.exception
    comparison = at.dataframe[0].value
    assert list(comparison["Strategy"]) == ["Momentum (top 10%, monthly)", "Low volatility (50 calmest, quarterly)",
                                            "SPY (benchmark)"]
    for table in at.dataframe[1:]:
        holdings = table.value["Holdings"]
        assert holdings.str.contains(r"^\d+ stocks · \d+% turnover · biggest: ").all()


def test_worst_n_shows_its_floor_and_marks_picks_that_could_not_be_bought():
    at = app()
    at.multiselect(key="strategies").set_value(["Last year's worst N"])
    at.run()
    assert not at.exception
    assert list(at.dataframe[0].value["Strategy"]) == ["Last year's worst 10", "SPY (benchmark)"]
    assert any(c.value.startswith("**Floor for last year's worst 10:**") for c in at.caption)
    year_2009 = at.dataframe[1].value.set_index("Year").loc[2009, "Holdings"]
    assert "NCC (not bought)" in year_2009 and "WB (not bought)" in year_2009  # taken over on 2008-12-31


def test_coverage_page_lists_only_members_with_issues():
    # Regression: `d.flags` is a pandas attribute, not the column, and once made every
    # member look flagged ("503 of 503").
    import re
    at = app()  # start from the entry point, then switch pages as a user would
    at.switch_page("pages/1_Coverage.py").run()
    assert not at.exception
    text = next(c.value for c in at.caption if "members in" in c.value)
    shown, members = map(int, re.match(r"(\d+) of (\d+)", text).groups())
    assert 0 < shown < members


@pytest.mark.parametrize("change", [
    lambda at: at.slider(key="n").set_value(1),
    lambda at: at.slider(key="cost").set_value(0),
    lambda at: at.select_slider(key="years").set_value((2010, 2015)),
    lambda at: at.radio(key="universe").set_value(at.radio(key="universe").options[1]),
    lambda at: at.multiselect(key="strategies").set_value([]),
    lambda at: at.radio(key="cash").set_value("0%"),
    lambda at: at.multiselect(key="strategies").set_value(["SPY RSI(2) dip-buying"]),
    lambda at: (at.multiselect(key="strategies").set_value(["Momentum (top 10%, monthly)"]),
                at.radio(key="universe").set_value(at.radio(key="universe").options[1])),
    lambda at: (at.multiselect(key="strategies").set_value(["Low volatility (50 calmest, quarterly)"]),
                at.select_slider(key="years").set_value((2008, 2009))),
])
def test_settings_render(change):
    at = app()
    change(at)
    at.run()
    assert not at.exception


@pytest.mark.skipif(not (ROOT / "data" / "cache" / "robustness.parquet").exists(),
                    reason="needs scripts/robustness.py to have run")
def test_robustness_page_shows_every_variant_and_a_verdict():
    at = app()
    at.switch_page("pages/2_Robustness.py").run()
    assert not at.exception
    assert any(h.value.startswith("Verdict: ") for h in at.subheader)
    table = at.dataframe[0].value
    assert len(table) == 36 and table.Variant.str.endswith("(published)").sum() == 1

