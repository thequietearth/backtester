"""Coverage report page: how much of the point-in-time S&P 500 has usable price data, per year."""
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bt.coverage import LOWER_PCT, TRUSTED_PCT, coverage_by_year  # noqa: E402
from bt.universe import load_constituents  # noqa: E402

CACHE = ROOT / "data" / "cache"
YEARS = range(1996, 2026)
START = 1999  # first backtest year (PLAN.md decisions); 1996-98 are shown to document why
# Status colours (good / warning / critical), always shown with an icon and a label.
BANDS = {"trusted": ("#0ca30c", "✓ trusted"), "lower coverage": ("#fab219", "⚠ lower coverage"),
         "unreliable": ("#d03b3b", "✕ unreliable")}

st.set_page_config(page_title="Coverage report", layout="wide")
st.title("Coverage report")
st.write(
    "For each backtest year: of the S&P 500 members on the formation date, how many have "
    "prices for the whole formation period (so they can be ranked) and at entry (so they "
    f"can be held). Years are never dropped, only labelled: ≥ {TRUSTED_PCT:.0f}% trusted, "
    f"{LOWER_PCT:.0f}–{TRUSTED_PCT:.0f}% lower coverage, below that unreliable. The backtest "
    f"starts in {START}: before that, the price source's histories for delisted companies are "
    "too short. Members with broken prices or a doubtful identity are not ranked and count as gaps."
)

if not (CACHE / "prices.parquet").exists():
    st.warning("No price cache yet. Run `scripts/download_eodhd.py --scope v1`, then "
               "`scripts/build_price_cache.py`.")
    st.stop()


@st.cache_data
def load():
    cons = load_constituents(ROOT / "data" / "constituents.parquet")
    smap = pd.read_csv(CACHE / "security_map.csv", parse_dates=["start", "end"])
    prices = pd.read_parquet(CACHE / "prices.parquet")
    raw = pd.read_parquet(CACHE / "close.parquet")
    factors = pd.read_parquet(CACHE / "split_factors.parquet")
    return coverage_by_year(cons, smap, prices, prices["SPY"].dropna().index, YEARS,
                            raw_prices=raw, split_factors=factors)


summary, detail = load()

bt_years = summary[summary.year >= START]
c1, c2, c3 = st.columns(3)
c1.metric(f"Trusted years ({START}–{bt_years.year.max()})",
          f"{(bt_years.band == 'trusted').sum()} of {len(bt_years)}")
worst = bt_years.loc[bt_years.coverage_pct.idxmin()]
c2.metric(f"Lowest coverage since {START}", f"{worst.coverage_pct:.1f}%", f"{worst.year}", delta_color="off")
c3.metric(f"Member-years set aside as suspect since {START}", f"{int(bt_years.suspect.sum()):,}")

fig = go.Figure()
for band, (colour, label) in BANDS.items():
    d = summary[summary.band == band]
    fig.add_bar(x=d.year, y=d.coverage_pct, name=label, marker_color=colour, marker_cornerradius=4,
                customdata=d[["covered", "members"]],
                hovertemplate="%{x}: %{y:.1f}% (%{customdata[0]} of %{customdata[1]} members)<extra>"
                              + label + "</extra>")
for level in (TRUSTED_PCT, LOWER_PCT):
    fig.add_hline(y=level, line_dash="dot", line_width=1, line_color="gray",
                  annotation_text=f"{level:.0f}%", annotation_position="top left")
fig.update_layout(barmode="overlay", bargap=0.25, height=360, margin=dict(t=20, b=10),
                  yaxis=dict(title="Coverage (%)", range=[0, 100]), xaxis=dict(title=None, dtick=2),
                  legend=dict(orientation="h", y=1.08))
st.plotly_chart(fig, width="stretch")

st.dataframe(summary.assign(band=summary.band.map(lambda b: BANDS[b][1]),
                            formation_date=summary.formation_date.dt.date),
             hide_index=True, width="stretch")
dl1, dl2 = st.columns(2)
dl1.download_button("Download summary (CSV)", summary.to_csv(index=False), "coverage_summary.csv", "text/csv")
dl2.download_button("Download member detail (CSV)", detail.to_csv(index=False), "coverage_detail.csv", "text/csv")

st.subheader("Members not covered or flagged")
year = st.selectbox("Year", list(summary.year[::-1]))
d = detail[detail.year == year]
issues = d[(d.status != "ok") | d.ended_mid_year | (d.flags != "")]
st.caption(f"{len(issues)} of {len(d)} members in {year}. Statuses: suspect prices = the formation "
           "year shows a one-day doubling or halving, a hole of 10+ trading days, or an adjusted price "
           "that disagrees with the traded price; suspect identity = trades too little to be an S&P 500 "
           "member. Flags: ambiguous = several codes fit; small = see suspect identity; partial = prices "
           "cover only part of the membership; multi_spell = the ticker left the index and came back, "
           "often a different company.")
st.dataframe(issues.drop(columns=["year"]), hide_index=True, width="stretch")
