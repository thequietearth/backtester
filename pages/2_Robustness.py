"""Robustness page (M6): does momentum's lead over SPY survive other reasonable settings,
both eras, higher costs, and the possibility of luck? Reads data/cache/robustness.parquet,
built by scripts/robustness.py."""
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bt.robustness import ERAS, GRID, verdict  # noqa: E402

CACHE = ROOT / "data" / "cache"
# One series: the app's validated strategy blue (light, dark); reference lines in muted grey.
BLUE, GREY = ("#2a78d6", "#3987e5"), ("#8a8984", "#6e6d69")

st.set_page_config(page_title="Robustness", layout="wide")
with st.sidebar:
    st.page_link("app.py", label="Results", icon="📈")
    st.page_link("pages/1_Coverage.py", label="Coverage report", icon="📊")
    st.page_link("pages/2_Robustness.py", label="Robustness", icon="🧪")
st.title("Robustness: is momentum real?")
st.write(
    "Momentum (the top 10% of members by return from 12 months ago to 1 month ago, re-ranked monthly) "
    "beat SPY by about a point a year in 1999–2025. A strategy that only works with one exact set of "
    "settings is probably a fluke of history, so here the rule is re-run with every combination of "
    "reasonable settings: the share held (5, 10 or 20%), the lookback (6, 9 or 12 months), whether the "
    "latest month is skipped, and monthly or quarterly rebalancing. That makes 36 variants, all on the "
    "members of the time, at 10 bps per trade, with cash earning the T-bill rate."
)
st.caption(
    "**Ground rule:** all variants are judged together, and the best one is never the headline. Trying many "
    "settings and keeping the best mostly finds the luckiest one (data snooping). The verdict criteria were "
    "fixed before any results were seen: **robust** if at least 75% of variants beat SPY over 1999–2025 and a "
    "majority beat it in each era; **fragile** if fewer than half beat it; otherwise **mixed**."
)

path = CACHE / "robustness.parquet"
if not path.exists():
    st.warning("No robustness results yet. Run `python scripts/robustness.py` (after `scripts/build_data.py`).")
    st.stop()

r = pd.read_parquet(path)
theme = 1 if getattr(st.context.theme, "type", None) == "dark" else 0
(a1, z1), (a2, z2) = ERAS
e1, e2 = f"lead_{a1}_{z1}", f"lead_{a2}_{z2}"
beat, beat1, beat2 = (r.lead > 0).mean(), (r[e1] > 0).mean(), (r[e2] > 0).mean()
v = verdict(beat, beat1, beat2)
lucky = int((r.t_stat >= 2).sum())

st.subheader(f"Verdict: {v}")
cols = st.columns(5)
cols[0].metric("Beat SPY, 1999–2025", f"{(r.lead > 0).sum()} of {len(r)}")
cols[1].metric(f"Beat SPY, {a1}–{z1}", f"{(r[e1] > 0).sum()} of {len(r)}")
cols[2].metric(f"Beat SPY, {a2}–{z2}", f"{(r[e2] > 0).sum()} of {len(r)}")
cols[3].metric("Typical lead", f"{r.lead.median():+.1f} pts/yr", help="Median over the 36 variants.")
cols[4].metric("Pass the luck test", f"{lucky} of {len(r)}",
               help="t-statistic of 2 or more: the average yearly lead is large compared with how much it swings.")
st.write(
    f"SPY returned {r.spy_cagr.iloc[0]:.1f}% a year (Sharpe {r.spy_sharpe.iloc[0]:.2f}). The typical variant "
    f"returned {r.cagr.median():.1f}% a year (Sharpe {r.sharpe.median():.2f}). The lead disappears at a trading "
    f"cost of about {r.break_even_bps.median():.0f} bps per trade for the typical variant."
)

# --- Added after the first results: the equal-weight baseline --------------------------
ew_lead = r.ew_cagr.iloc[0] - r.spy_cagr.iloc[0]
w1, w2 = f"vs_ew_{a1}_{z1}", f"vs_ew_{a2}_{z2}"
st.subheader("Added after the fact: against owning every member equally")
st.write(
    "Every variant holds its stocks in equal amounts, while SPY weights companies by size. So part of any lead "
    "over SPY can come from equal weighting alone, with no picking at all. This comparison was added after the "
    "first results (by a verification run), so it doesn't change the verdict above, which was set in advance. "
    "But it changes what the verdict means."
)
cols = st.columns(4)
cols[0].metric("Every member, equal weight", f"{r.ew_cagr.iloc[0]:.1f}% a year",
               help=f"Sharpe {r.ew_sharpe.iloc[0]:.2f}, worst fall {r.ew_worst_fall.iloc[0]:.0f}%. Same members, "
                    "rebalanced monthly, 10 bps per trade.")
cols[1].metric("Variants beating it, 1999–2025", f"{(r.lead_vs_ew > 0).sum()} of {len(r)}")
cols[2].metric(f"Beating it, {a1}–{z1}", f"{(r[w1] > 0).sum()} of {len(r)}")
cols[3].metric(f"Beating it, {a2}–{z2}", f"{(r[w2] > 0).sum()} of {len(r)}")
st.write(
    f"Owning every member equally beat SPY by {r[f'ew_lead_{a1}_{z1}'].iloc[0]:+.1f} points a year in {a1}–{z1} and "
    f"trailed it by {-r[f'ew_lead_{a2}_{z2}'].iloc[0]:.1f} in {a2}–{z2}: the same pattern as momentum. Against "
    f"that baseline the typical variant is {r.lead_vs_ew.median():+.1f} points a year, so **momentum's lead over "
    "SPY is the equal-weight effect, not momentum**: smaller companies beat the giants in the 2000s, and the giants "
    "led after 2010."
)


def hover(d):
    return [f"{x.label}<br>vs SPY {x.lead:+.1f} pts/yr ({a1}–{z1}: {x[e1]:+.1f}, {a2}–{z2}: {x[e2]:+.1f})"
            f"<br>Sharpe {x.sharpe:.2f}, worst fall {x.worst_fall:.0f}%<br>break-even cost {x.break_even_bps:.0f} bps, "
            f"t-statistic {x.t_stat:.2f}, turnover {x.turnover:.0f}% a year" for _, x in d.iterrows()]


# --- Every variant's lead, sorted -----------------------------------------------------
d = r.sort_values("lead").reset_index(drop=True)
fig = go.Figure()
fig.add_vline(x=0, line=dict(color=GREY[theme], width=1.5, dash="dot"))
fig.add_vline(x=ew_lead, line=dict(color=GREY[theme], width=1.5, dash="dash"),
              annotation_text="every member, equal weight", annotation_position="top")
fig.add_scatter(x=d.lead, y=d.label, mode="markers", marker=dict(size=10, color=BLUE[theme]),
                hovertext=hover(d), hoverinfo="text", showlegend=False)
default = d[d.is_default]
fig.add_scatter(x=default.lead, y=default.label, mode="markers+text", showlegend=False, hoverinfo="skip",
                marker=dict(size=18, color="rgba(0,0,0,0)", line=dict(color=BLUE[theme], width=2)),
                text=["  the published rule"], textposition="middle right")
fig.update_layout(title="Lead over SPY, 1999–2025 (points a year, after costs): each dot is one variant",
                  height=110 + 22 * len(d), margin=dict(l=10, r=10, t=60, b=40),
                  xaxis=dict(ticksuffix=" pts", zeroline=False), yaxis=dict(title=None))
st.plotly_chart(fig, width="stretch")
st.caption("Variants are written as lookback-skip months: 12-1 ranks on the return from 12 months ago to 1 month "
           "ago; 12-0 includes the latest month. To the right of the dotted line = ahead of SPY. The dashed line is "
           "where owning every member in equal amounts lands (added after the fact).")

# --- Eras ---------------------------------------------------------------------------
fig = go.Figure()
fig.add_vline(x=0, line=dict(color=GREY[theme], width=1.5, dash="dot"))
fig.add_hline(y=0, line=dict(color=GREY[theme], width=1.5, dash="dot"))
fig.add_scatter(x=r[e1], y=r[e2], mode="markers", marker=dict(size=10, color=BLUE[theme]),
                hovertext=hover(r), hoverinfo="text", showlegend=False)
dr = r[r.is_default]
fig.add_scatter(x=dr[e1], y=dr[e2], mode="markers+text", showlegend=False, hoverinfo="skip",
                marker=dict(size=18, color="rgba(0,0,0,0)", line=dict(color=BLUE[theme], width=2)),
                text=["  the published rule"], textposition="middle right")
fig.add_scatter(x=[r[f"ew_lead_{a1}_{z1}"].iloc[0]], y=[r[f"ew_lead_{a2}_{z2}"].iloc[0]], mode="markers+text",
                showlegend=False, marker=dict(size=13, symbol="diamond", color=GREY[theme]),
                text=["every member, equal weight  "], textposition="middle left",
                hovertext=["Every member, equal weight (added after the fact)"], hoverinfo="text")
fig.update_layout(title=f"Lead over SPY in each era (points a year): top right = ahead in both",
                  height=480, margin=dict(l=10, r=10, t=60, b=40),
                  xaxis=dict(title=f"{a1}–{z1}", ticksuffix=" pts", zeroline=False),
                  yaxis=dict(title=f"{a2}–{z2}", ticksuffix=" pts", zeroline=False))
st.plotly_chart(fig, width="stretch")

# --- Table -----------------------------------------------------------------------------
st.subheader("All 36 variants")
def pts(series):
    return series.map(lambda v: f"{round(v, 1) + 0.0:+.1f} pts")  # + 0.0: no "-0.0"


table = pd.DataFrame({
    "Variant": r.label + r.is_default.map({True: " (published)", False: ""}),
    "Return/yr": r.cagr.map("{:.1f}%".format), "vs SPY": pts(r.lead),
    f"{a1}–{z1}": pts(r[e1]), f"{a2}–{z2}": pts(r[e2]), "vs equal wt": pts(r.lead_vs_ew),
    "Sharpe": r.sharpe.map("{:.2f}".format), "Worst fall": r.worst_fall.map("{:.0f}%".format),
    "Break-even": r.break_even_bps.map("{:.0f} bps".format),
    "t-stat": r.t_stat.map("{:.2f}".format), "No lead": r.share_no_lead.map("{:.0%}".format)})
st.dataframe(table, hide_index=True, width="stretch", height=35 * (len(table) + 1) + 3,
             column_config={"Variant": st.column_config.TextColumn(width=250)})
st.caption(
    "Leads are in points a year against SPY, over the whole period and in each era; **vs equal wt** is against "
    "owning every member in equal amounts (added after the fact). **Break-even:** the trading cost per side at which the variant's lead over SPY disappears. "
    "**t-stat:** the average yearly lead divided by its uncertainty (the year-to-year spread over √27); "
    "around 2 or more is the usual bar for \"probably not luck\". **No lead:** the 27 yearly "
    "leads are redrawn at random thousands of times (a bootstrap), and this is how often the average comes out "
    "at zero or below. Testing 36 variants also means one or two would pass a luck test by chance alone. "
    f"Settings tested: {', '.join(f'{k} {list(vals)}' for k, vals in GRID.items())}."
)
