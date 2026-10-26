"""Streamlit entry point. Run with: streamlit run app.py

Backtests simple rules on the S&P 500 and shows them next to SPY over exactly the same
dates: v1's "buy last year's winners", and v2's timing rules on SPY, momentum, low
volatility and the contrarian "buy last year's losers". Reads only the local data cache built by scripts/build_data.py, plus the
committed T-bill rates; it never calls a data API.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from bt.coverage import load_crash_review, rankable_by_date, rankable_universe  # noqa: E402
from bt.data import load_tbill  # noqa: E402
from bt.metrics import drawdown_series  # noqa: E402
from bt.report import (backtest_window, daily_decisions, monthly_decisions, run_strategy, summary,  # noqa: E402
                       year_table)
from bt.strategies import (bottom_n, low_volatility, momentum, spy_buy_and_hold, spy_golden_cross,  # noqa: E402
                           spy_rsi2, spy_trend, top_n)
from bt.universe import formation_dates  # noqa: E402

CACHE = ROOT / "data" / "cache"
FIRST_YEAR, LAST_YEAR = 1999, 2025
TOP1, TOPN, BOTTOMN = "Last year's #1", "Last year's top N", "Last year's worst N"
TREND, CROSS, RSI2 = "SPY 200-day trend", "SPY golden cross (50/200 days)", "SPY RSI(2) dip-buying"
MOM, LOWVOL = "Momentum (top 10%, monthly)", "Low volatility (50 calmest, quarterly)"
SPY = "SPY (benchmark)"
TIMING = {TREND: spy_trend, CROSS: spy_golden_cross, RSI2: spy_rsi2}
PORTFOLIOS = {MOM, LOWVOL}  # dozens of stocks, rebalanced within the year
PICKERS = {TOP1, TOPN, BOTTOMN} | PORTFOLIOS  # stock-picking: these use the universe setting
PIT = "Point-in-time: the index members at the time"
NAIVE = "Naive: today's members only (shows survivorship bias)"
TBILL, ZERO = "3-month T-bill rate", "0%"
# Each small chart shows one strategy (blue) against SPY (aqua, dashed): two colours
# validated for colour-blind separation. More lines in one chart can't be told apart.
STRATEGY_COLOUR, SPY_COLOUR = ("#2a78d6", "#3987e5"), ("#1baf7a", "#199e70")

st.set_page_config(page_title="Backtester", layout="wide")
st.title("Backtester")
st.write("Simple, honest backtests on the S&P 500, next to SPY over exactly the same dates. Results include "
         "dividends and trading costs; stock-picking strategies use the index members of the time, not today's.")

if not (CACHE / "coverage_pit_detail.parquet").exists():
    st.warning("No data yet: run `python scripts/build_data.py` first (see the README).")
    st.stop()


@st.cache_resource
def load():
    prices = pd.read_parquet(CACHE / "prices.parquet")
    pit = pd.read_parquet(CACHE / "coverage_pit_detail.parquet")
    naive = pd.read_parquet(CACHE / "coverage_naive_detail.parquet")
    cov = pd.read_parquet(CACHE / "coverage_pit_summary.parquet")
    tbill = load_tbill(ROOT / "data" / "tbill_dtb3.csv")
    monthly = {mode: pd.read_parquet(CACHE / f"universe_monthly_{mode}.parquet") for mode in ("pit", "naive")}
    # Crashes a hand review found real: only the contrarian ranking uses them (see bt.coverage).
    crashes = load_crash_review(ROOT / "data" / "crash_review.csv")
    return prices, pit, naive, cov, tbill, monthly, crashes


prices, pit_detail, naive_detail, cov_summary, tbill, monthly_detail, real_crashes = load()
cal = prices["SPY"].dropna().index

with st.sidebar:
    st.page_link("app.py", label="Results", icon="📈")
    st.page_link("pages/1_Coverage.py", label="Coverage report", icon="📊")
    st.divider()
    st.header("Settings")
    chosen = st.multiselect("Strategies (up to 4)", [TOP1, TOPN, BOTTOMN, MOM, LOWVOL, TREND, CROSS, RSI2],
                            default=[TOP1, TOPN], max_selections=4, key="strategies")
    n = st.slider("N, for top N and worst N", 1, 50, 10, key="n")
    start, end = st.select_slider("Years", options=list(range(FIRST_YEAR, LAST_YEAR + 1)),
                                  value=(FIRST_YEAR, LAST_YEAR), key="years")
    cost = st.slider("Trading cost (basis points per side)", 0, 100, 10, key="cost",
                     help="1 basis point = 0.01%. Charged on every purchase and sale.")
    cash = st.radio("Cash earns", [TBILL, ZERO], key="cash",
                    help="Uninvested money earns the 3-month US Treasury bill rate (FRED series DTB3), "
                         "and the Sharpe ratio is measured beyond it. Matters most for timing rules, "
                         "which sit in cash for long stretches.")
    mode = st.radio("Universe, for stock-picking strategies", [PIT, NAIVE], key="universe")
    st.caption("Every strategy decides at a close and trades at the next day's close. Last year's #1 / top N: "
               "ranked on the last trading day of each year. Last year's worst N: the mirror image, a bet that big losers bounce back. Momentum: the top 10% by return from 12 months "
               "ago to 1 month ago, re-ranked every month-end. Low volatility: the 50 members with the "
               "calmest daily prices over the past year, re-ranked every quarter. SPY timing rules: decided "
               "every day. SPY buy-and-hold is always shown.")


@st.cache_data(show_spinner="Running the backtest...")
def compute(chosen: tuple, n: int, start: int, end: int, cost: int, mode: str, cash: str):
    window = backtest_window(cal, start, end)
    rate = tbill if cash == TBILL else None
    detail = pit_detail if mode == PIT else naive_detail
    monthly = monthly_detail["pit" if mode == PIT else "naive"]
    universe = rankable_universe(detail, formation_dates(cal, window.years))
    with_crashes = rankable_universe(detail, formation_dates(cal, window.years), real_crashes=real_crashes)
    by_month = rankable_by_date(monthly)
    worst_case = None
    runs = {SPY: run_strategy(SPY, spy_buy_and_hold(prices, universe, window.rebalance), prices, cost, cal, window, rate)}
    for name in chosen:
        if name in TIMING:
            w, label = TIMING[name](prices, {}, daily_decisions(cal, window)), name
        elif name == MOM:
            w, label = momentum(prices, by_month, monthly_decisions(cal, window)), name
        elif name == LOWVOL:
            w, label = low_volatility(prices, by_month, monthly_decisions(cal, window, every=3), n=50), name
        elif name == BOTTOMN:
            w, label = bottom_n(prices, with_crashes, window.rebalance, n=n), f"Last year's worst {n}"
            # Lower bound: every holding whose data ended counted as worthless (bankruptcies).
            low = run_strategy(label, w, prices, cost, cal, window, rate, ended_recovery=0.0)
            exits = low.trades.note.str.contains("counted as worth", na=False).sum()
            worst_case = (label, summary(low, low)["CAGR %"], int(exits))
        elif name == TOP1:
            w, label = top_n(prices, universe, window.rebalance, n=1), TOP1
        else:
            w, label = top_n(prices, universe, window.rebalance, n=n), f"Last year's top {n}"
        runs[name] = run_strategy(label, w, prices, cost, cal, window, rate)
    named = pd.concat([monthly[["code", "ticker"]], detail[["code", "ticker"]]]).dropna(subset=["code"])
    labels = named.drop_duplicates("code", keep="last").set_index("code")["ticker"].to_dict()
    coverage = ({r.year: (r.band, r.coverage_pct) for r in cov_summary.itertuples()} if mode == PIT else None)
    return runs, labels, coverage, worst_case


runs, labels, coverage, worst_case = compute(tuple(chosen), n, start, end, cost, mode, cash)
theme = 1 if getattr(st.context.theme, "type", None) == "dark" else 0
spy = runs[SPY]
strategies = [(k, r) for k, r in runs.items() if k != SPY]

if PICKERS & set(chosen):
    if mode == NAIVE:
        st.warning("**Naive universe.** The stock-picking strategies rank only companies in the S&P 500 *today*, so "
                   "they never pick a company that later collapsed or was taken over, and they rank some that "
                   "weren't in the index yet. That flatters the results. It's here to show how big survivorship "
                   "bias is, not as a real result.")
    elif coverage:
        weak = [y for y in range(start, end + 1) if coverage.get(y, ("trusted",))[0] != "trusted"]
        if weak:
            lo = min(coverage[y][1] for y in weak)
            st.info(f"⚠ **Lower coverage in {weak[0]}–{weak[-1]}** ({len(weak)} of {end - start + 1} years) for the "
                    f"stock-picking strategies: as few as {lo:.0f}% of that year's members had usable price data, "
                    "so a missing stock could have ranked differently. Every top-10 pick of last year's winners "
                    "was checked by hand (docs/top10-review.md). Years are labelled in the tables below.")
if not chosen:
    st.info("Choose at least one strategy in the sidebar.")

# --- Comparison table -------------------------------------------------------------
st.subheader("Comparison")
rows = [summary(r, spy) for _, r in strategies] + [summary(spy, spy)]
spy_cagr = rows[-1]["CAGR %"]
fmt_pct = lambda v, d=1: "—" if pd.isna(v) else f"{v:.{d}f}%"  # noqa: E731
table = pd.DataFrame([{
    "Strategy": s["Strategy"], "$10k becomes": f"${s['$10k becomes']:,.0f}",
    "Return/yr": fmt_pct(s["CAGR %"]),
    "vs SPY": "—" if s is rows[-1] else f"{round(s['CAGR %'] - spy_cagr, 1) + 0.0:+.1f} pts",  # + 0.0: no "-0.0"
    "Volatility": fmt_pct(s["Volatility %"], 0),
    "Sharpe": "—" if pd.isna(s["Sharpe"]) else f"{s['Sharpe']:.2f}",
    "Worst fall": fmt_pct(s["Max drawdown %"], 0),
    "Recovery": f"{s['Drawdown lasted (years)']:.1f} yrs",
    "Beat SPY": "—" if s is rows[-1] else fmt_pct(s["Years beating SPY %"], 0),
    "Trades/yr": f"{s['Trades per year']:.1f}",
    "Invested": fmt_pct(s["Time invested %"], 0)} for s in rows])
st.dataframe(table, hide_index=True, width="stretch",  # wide enough for the longest strategy name
             column_config={"Strategy": st.column_config.TextColumn(width=275)})
st.caption("**Return/yr**: compound annual growth rate. **Sharpe**: return per unit of volatility, "
           f"{'beyond what T-bills paid' if cash == TBILL else 'with cash at 0%'}. **Worst fall**: the biggest drop "
           "from a peak; **recovery**: how long until that peak was regained (or until the end, if never). "
           "**Beat SPY**: share of years with a higher return. **Trades/yr**: purchases and sales, including the small "
           "top-ups and trims that keep a monthly portfolio equally weighted. **Invested**: average share of money "
           "in stocks rather than cash.")
if worst_case and worst_case[2]:
    label, low_cagr, exits = worst_case
    normal = next(r["CAGR %"] for r in rows if r["Strategy"] == label)
    st.caption(f"**Floor for {label.lower()}:** if all {exits} holdings whose data ended had been worthless, it would "
               f"return {low_cagr:.1f}% a year instead of {normal:.1f}%. That floor is far too pessimistic: most of those "
               "companies were bought out, which paid holders about the last price. The exceptions are bankruptcies "
               "and failures such as SVB's (docs/worst10-review.md).")


# --- Charts: one small chart per strategy, each against SPY --------------------------
def small_multiples(title, series_of, hover, log=False, height_per_row=300):
    cols = 1 if len(strategies) == 1 else 2
    nrows = math.ceil(len(strategies) / cols)
    fig = make_subplots(rows=nrows, cols=cols, shared_xaxes=True, shared_yaxes=True,
                        subplot_titles=[r.name for _, r in strategies], vertical_spacing=0.12 / nrows,
                        horizontal_spacing=0.04)
    for i, (key, run) in enumerate(strategies):
        row, col = i // cols + 1, i % cols + 1
        for r, colour, dash, name in ((run, STRATEGY_COLOUR, "solid", "Strategy"), (spy, SPY_COLOUR, "dash", SPY)):
            y = series_of(r)
            fig.add_scatter(x=y.index, y=y.values, name=name, legendgroup=name, showlegend=i == 0, mode="lines",
                            line=dict(color=colour[theme], width=2, dash=dash),
                            hovertemplate=f"{r.name}: {hover}<extra></extra>", row=row, col=col)
    if log:
        values = pd.concat([series_of(r) for _, r in strategies] + [series_of(spy)])
        ticks = [m * 10 ** e for e in range(2, 9) for m in (1, 2, 5)
                 if values.min() * 0.8 <= m * 10 ** e <= values.max() * 1.25]
        fig.update_yaxes(type="log", tickvals=ticks, ticktext=[f"${v / 1e6:g}M" if v >= 1e6 else f"${v / 1e3:g}k"
                                                                if v >= 1e3 else f"${v:g}" for v in ticks])
    else:
        fig.update_yaxes(ticksuffix="%")
    fig.update_yaxes(matches="y")  # one scale for every panel, so they can be compared at a glance
    # The legend sits on the title's line, above the panel titles, so it never covers them.
    fig.update_layout(title=dict(text=title, y=0.99, yanchor="top"), hovermode="x unified",
                      height=110 + height_per_row * nrows, margin=dict(t=110),
                      legend=dict(orientation="h", yref="container", y=0.99, yanchor="top", x=1, xanchor="right"))
    return fig


if strategies:
    st.plotly_chart(small_multiples("Growth of $10,000 (log scale)", lambda r: 10_000 * r.equity, "$%{y:,.0f}",
                                    log=True), width="stretch")
    st.plotly_chart(small_multiples("Drawdown: how far below its previous peak",
                                    lambda r: 100 * drawdown_series(r.equity), "%{y:.0f}%", height_per_row=220),
                    width="stretch")

# --- Year by year -------------------------------------------------------------------
if strategies:
    st.subheader("Year by year")
    st.caption("Each year runs from the January purchase to the next January's purchase. For momentum and low "
               "volatility, holdings show the average number of stocks held, turnover (the share of the "
               "portfolio sold during the year: 100% = all of it replaced once) and the three holdings that moved "
               "the year's return most, in percentage points. † = the stock's data ended during the year: it was "
               "sold at its last price, and the real outcome (often a takeover or bankruptcy) is unknown. "
               "(not bought) = no price on the purchase day, e.g. a company taken over on the formation date; "
               "its share stayed in cash.")
    pct = st.column_config.NumberColumn(format="%.1f%%")
    tabs = st.tabs([r.name for _, r in strategies])
    for tab, (key, run) in zip(tabs, strategies):
        with tab:
            timing = key in TIMING
            kind = "timing" if timing else "portfolio" if key in PORTFOLIOS else "picks"
            t = year_table(run, spy, labels, None if timing else coverage, kind=kind, prices=prices)
            if timing:
                t = t.drop(columns=["Coverage"])
            st.dataframe(t, hide_index=True, width="stretch", height=35 * (len(t) + 1) + 3,
                         column_config={"Strategy %": pct, "SPY %": pct,
                                        "Year": st.column_config.NumberColumn(format="%d")})

st.page_link("pages/1_Coverage.py", label="Coverage report: which members had usable data each year", icon="📊")
st.caption("Data: S&P 500 membership from fja05680/sp500 (MIT); prices from EODHD, adjusted for splits and "
           "dividends, checked as described in docs/data-source-evaluation.md; 3-month T-bill rates from FRED "
           "(series DTB3, Board of Governors of the Federal Reserve System). Past results don't predict future ones.")
