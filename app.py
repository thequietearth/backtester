"""Streamlit entry point. Run with: streamlit run app.py

What if you had bought last year's best-performing S&P 500 stock every January? The app
runs the v1 strategies through the backtest engine and shows them next to SPY over exactly
the same dates. It reads only the local data cache built by scripts/build_data.py and
never calls a data API.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from bt.coverage import rankable_universe  # noqa: E402
from bt.metrics import drawdown_series  # noqa: E402
from bt.report import backtest_window, run_strategy, summary, year_table  # noqa: E402
from bt.strategies import spy_buy_and_hold, top_n  # noqa: E402
from bt.universe import formation_dates  # noqa: E402

CACHE = ROOT / "data" / "cache"
FIRST_YEAR, LAST_YEAR = 1999, 2025
TOP1, TOPN, SPY = "Last year's #1", "Last year's top N", "SPY (benchmark)"
PIT = "Point-in-time: the index members at the time"
NAIVE = "Naive: today's members only (shows survivorship bias)"
# Fixed colour per series (light, dark), validated for colour-blind separation. SPY also
# gets a dashed line, so it never relies on colour alone.
COLOURS = {TOP1: ("#2a78d6", "#3987e5"), TOPN: ("#eb6834", "#d95926"), SPY: ("#1baf7a", "#199e70")}

st.set_page_config(page_title="Backtester", layout="wide")
st.title("Backtester")
st.write("What if you had bought **last year's best-performing S&P 500 stocks** every January "
         "and held them for a year? Results include dividends and trading costs, use the index "
         "members of the time (not today's), and are shown next to SPY over exactly the same dates.")

if not (CACHE / "coverage_pit_detail.parquet").exists():
    st.warning("No data yet: run `python scripts/build_data.py` first (see the README).")
    st.stop()


@st.cache_resource
def load():
    prices = pd.read_parquet(CACHE / "prices.parquet")
    pit = pd.read_parquet(CACHE / "coverage_pit_detail.parquet")
    naive = pd.read_parquet(CACHE / "coverage_naive_detail.parquet")
    cov = pd.read_parquet(CACHE / "coverage_pit_summary.parquet")
    return prices, pit, naive, cov


prices, pit_detail, naive_detail, cov_summary = load()
cal = prices["SPY"].dropna().index

with st.sidebar:
    st.page_link("app.py", label="Results", icon="📈")
    st.page_link("pages/1_Coverage.py", label="Coverage report", icon="📊")
    st.divider()
    st.header("Settings")
    chosen = st.multiselect("Strategies", [TOP1, TOPN], default=[TOP1, TOPN], key="strategies")
    n = st.slider("N, for top N", 1, 50, 10, key="n")
    start, end = st.select_slider("Years", options=list(range(FIRST_YEAR, LAST_YEAR + 1)),
                                  value=(FIRST_YEAR, LAST_YEAR), key="years")
    cost = st.slider("Trading cost (basis points per side)", 0, 100, 10, key="cost",
                     help="1 basis point = 0.01%. Charged on every purchase and sale.")
    mode = st.radio("Universe", [PIT, NAIVE], key="universe")
    st.caption("Each year, picks are ranked on the last trading day of the year before and "
               "bought at the next day's close. SPY is always shown.")


@st.cache_data(show_spinner="Running the backtest...")
def compute(chosen: tuple, n: int, start: int, end: int, cost: int, mode: str):
    window = backtest_window(cal, start, end)
    detail = pit_detail if mode == PIT else naive_detail
    universe = rankable_universe(detail, formation_dates(cal, window.years))
    runs = {SPY: run_strategy(SPY, spy_buy_and_hold(prices, universe, window.rebalance), prices, cost, cal, window)}
    if TOP1 in chosen:
        runs[TOP1] = run_strategy(TOP1, top_n(prices, universe, window.rebalance, n=1), prices, cost, cal, window)
    if TOPN in chosen:
        runs[TOPN] = run_strategy(f"Last year's top {n}", top_n(prices, universe, window.rebalance, n=n),
                                  prices, cost, cal, window)
    labels = detail.dropna(subset=["code"]).drop_duplicates("code", keep="last").set_index("code")["ticker"].to_dict()
    coverage = ({r.year: (r.band, r.coverage_pct) for r in cov_summary.itertuples()} if mode == PIT else None)
    return runs, labels, coverage


runs, labels, coverage = compute(tuple(chosen), n, start, end, cost, mode)
theme = 1 if getattr(st.context.theme, "type", None) == "dark" else 0
colour = {k: COLOURS[k][theme] for k in COLOURS}

if mode == NAIVE:
    st.warning("**Naive universe.** Each year ranks only companies that are in the S&P 500 *today*, "
               "so it never picks a company that later collapsed or was taken over, and it ranks some "
               "that weren't in the index yet. That flatters the results. It's here to show how big "
               "survivorship bias is, not as a real result.")
elif coverage:
    weak = [y for y in range(start, end + 1) if coverage.get(y, ("trusted",))[0] != "trusted"]
    if weak:
        lo = min(coverage[y][1] for y in weak)
        st.info(f"⚠ **Lower coverage in {weak[0]}–{weak[-1]}** ({len(weak)} of {end - start + 1} years): "
                f"as few as {lo:.0f}% of that year's members had usable price data, so a missing stock "
                "could have ranked higher. Every top-10 pick was checked by hand "
                "(docs/top10-review.md). Years are labelled in the table below.")

if not chosen:
    st.info("Choose at least one strategy in the sidebar.")

# --- Metric cards -----------------------------------------------------------------
spy = runs[SPY]
for key, run in [(k, v) for k, v in runs.items() if k != SPY] + [(SPY, spy)]:
    s = summary(run, spy)
    st.markdown(f"**{run.name}**")
    c = st.columns(6)
    c[0].metric("$10k becomes", f"${s['$10k becomes']:,.0f}")
    c[1].metric("Return per year (CAGR)", f"{s['CAGR %']:.1f}%",
                None if run is spy else f"{s['CAGR %'] - summary(spy, spy)['CAGR %']:+.1f} pts vs SPY")
    c[2].metric("Volatility", f"{s['Volatility %']:.0f}%", help="How bumpy the ride is: yearly standard deviation.")
    c[3].metric("Sharpe ratio", f"{s['Sharpe']:.2f}",
                help="Return per unit of volatility, against cash at 0%. Higher is better.")
    c[4].metric("Worst fall", f"{s['Max drawdown %']:.0f}%",
                help=f"Largest drop from a peak; it took {s['Drawdown lasted (years)']:.1f} years to recover "
                     "(or hasn't yet).")
    c[5].metric("Years beating SPY", "—" if run is spy else f"{s['Years beating SPY %']:.0f}%")


# --- Charts -------------------------------------------------------------------------
def line(fig, key, run, y, hover):
    fig.add_scatter(x=y.index, y=y.values, name=run.name, mode="lines",
                    line=dict(color=colour[key], width=2, dash="dash" if key == SPY else "solid"),
                    hovertemplate=f"{run.name}: {hover}<extra></extra>")


order = [(k, v) for k, v in runs.items() if k != SPY] + [(SPY, spy)]
growth = go.Figure()
for key, run in order:
    line(growth, key, run, 10_000 * run.equity, "$%{y:,.0f}")
finals = sorted(np.log10(10_000 * r.equity.iloc[-1]) for _, r in order)
if all(b - a > 0.06 for a, b in zip(finals, finals[1:])):  # direct end labels only if they don't collide
    for key, run in order:
        v = 10_000 * run.equity.iloc[-1]
        growth.add_annotation(x=run.equity.index[-1], y=np.log10(v), text=f"${v:,.0f}", showarrow=False,
                              xanchor="left", xshift=6, font=dict(color=colour[key]))
values = pd.concat([10_000 * r.equity for _, r in order])
ticks = [m * 10 ** e for e in range(2, 9) for m in (1, 2, 5) if values.min() * 0.8 <= m * 10 ** e <= values.max() * 1.25]
growth.update_layout(title="Growth of $10,000 (log scale)", hovermode="x unified", height=430,
                     yaxis=dict(type="log", tickvals=ticks,
                                ticktext=[f"${v / 1e6:g}M" if v >= 1e6 else f"${v / 1e3:g}k" if v >= 1e3
                                          else f"${v:g}" for v in ticks]),
                     margin=dict(t=50, r=80), legend=dict(orientation="h", y=-0.12))
st.plotly_chart(growth, width="stretch")

dd = go.Figure()
for key, run in order:
    line(dd, key, run, 100 * drawdown_series(run.equity), "%{y:.0f}%")
dd.update_layout(title="Drawdown: how far below its previous peak", hovermode="x unified", height=300,
                 yaxis=dict(ticksuffix="%"), margin=dict(t=50), legend=dict(orientation="h", y=-0.2))
st.plotly_chart(dd, width="stretch")

# --- Year by year -------------------------------------------------------------------
st.subheader("Year by year")
st.caption("Each year runs from the January purchase to the next January's purchase. "
           "† = the stock's data ended during the year: it was sold at its last price, and the real "
           "outcome (often a takeover or bankruptcy) is unknown.")
pct = st.column_config.NumberColumn(format="%.1f%%")
strategy_runs = [(k, v) for k, v in runs.items() if k != SPY]
tabs = st.tabs([r.name for _, r in strategy_runs]) if strategy_runs else []
for tab, (key, run) in zip(tabs, strategy_runs):
    with tab:
        table = year_table(run, spy, labels, coverage)
        st.dataframe(table, hide_index=True, width="stretch", height=35 * (len(table) + 1) + 3,  # every year, no scrolling
                     column_config={"Strategy %": pct, "SPY %": pct, "Year": st.column_config.NumberColumn(format="%d")})

st.page_link("pages/1_Coverage.py", label="Coverage report: which members had usable data each year", icon="📊")
st.caption("Data: S&P 500 membership from fja05680/sp500 (MIT); prices from EODHD, adjusted for splits "
           "and dividends, checked as described in docs/data-source-evaluation.md. Past results don't "
           "predict future ones.")
