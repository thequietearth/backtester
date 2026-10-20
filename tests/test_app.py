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
    labels = [m.label for m in at.metric]
    assert "Return per year (CAGR)" in labels and "Years beating SPY" in labels
    assert len(at.dataframe) == 2  # a year-by-year table for each strategy


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
])
def test_settings_render(change):
    at = app()
    change(at)
    at.run()
    assert not at.exception
