"""Static charts and numbers for docs/results.md, at the app's default settings
(1999-2025, last year's #1 and top 10, 10 bps per side).

Usage: python scripts/make_figures.py   (after scripts/build_data.py)
Writes docs/figures/growth.png, drawdown.png, survivorship.png and prints the numbers
the write-up quotes. Colours are the app's validated palette (light surface).
"""
import sys
from pathlib import Path

import matplotlib
import matplotlib.patches  # noqa: F401  (legend swatches)

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mticker  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bt.coverage import rankable_universe  # noqa: E402
from bt.metrics import drawdown_series  # noqa: E402
from bt.report import backtest_window, run_strategy, summary  # noqa: E402
from bt.strategies import spy_buy_and_hold, top_n  # noqa: E402
from bt.universe import formation_dates  # noqa: E402

CACHE = ROOT / "data" / "cache"
OUT = ROOT / "docs" / "figures"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"  # Top 1, Top 10, SPY - same as the app
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"


def style(ax, title):
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", fontsize=13, color=INK, fontweight="bold")
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=10)


def dollars(v, _):
    return f"${v / 1e6:g}M" if v >= 1e6 else f"${v / 1e3:g}k" if v >= 1e3 else f"${v:g}"


def main():
    prices = pd.read_parquet(CACHE / "prices.parquet")
    cal = prices["SPY"].dropna().index
    w = backtest_window(cal, 1999, 2025)
    runs = {}
    for label, file in (("pit", "coverage_pit_detail.parquet"), ("naive", "coverage_naive_detail.parquet")):
        universe = rankable_universe(pd.read_parquet(CACHE / file), formation_dates(cal, w.years))
        runs[label, "top1"] = run_strategy("Last year's #1", top_n(prices, universe, w.rebalance, n=1), prices, 10, cal, w)
        runs[label, "top10"] = run_strategy("Last year's top 10", top_n(prices, universe, w.rebalance, n=10), prices, 10, cal, w)
    spy = run_strategy("SPY (benchmark)", spy_buy_and_hold(prices, {}, w.rebalance), prices, 10, cal, w)
    series = [(runs["pit", "top1"], BLUE, "-"), (runs["pit", "top10"], ORANGE, "-"), (spy, AQUA, "--")]
    OUT.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 5.2), facecolor=SURFACE)
    for run, colour, ls in series:
        ax.plot(10_000 * run.equity, color=colour, linestyle=ls, linewidth=2, label=run.name)
    ax.set_yscale("log")
    ax.yaxis.set_major_locator(mticker.LogLocator(base=10, subs=(1, 2, 5)))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(dollars))
    ax.yaxis.set_minor_locator(mticker.NullLocator())
    style(ax, "Growth of $10,000, 1999–2025 (log scale, after 10 bps costs)")
    ax.legend(frameon=False, loc="upper left", labelcolor=INK)
    fig.tight_layout()
    fig.savefig(OUT / "growth.png", dpi=150)

    fig, ax = plt.subplots(figsize=(10, 3.6), facecolor=SURFACE)
    for run, colour, ls in series:
        ax.plot(100 * drawdown_series(run.equity), color=colour, linestyle=ls, linewidth=1.6, label=run.name)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    style(ax, "Drawdown: how far below its previous peak")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3, labelcolor=INK)
    fig.tight_layout()
    fig.savefig(OUT / "drawdown.png", dpi=150)

    # Survivorship bias: the same strategies ranked among today's members only.
    cagr = {k: summary(r, spy)["CAGR %"] for k, r in runs.items()}
    spy_cagr = summary(spy, spy)["CAGR %"]
    fig, ax = plt.subplots(figsize=(10, 4.2), facecolor=SURFACE)
    groups = [("Last year's #1", "top1", BLUE), ("Last year's top 10", "top10", ORANGE)]
    for i, (name, key, colour) in enumerate(groups):
        for j, uni in enumerate(("pit", "naive")):
            x = i * 3 + j
            v = cagr[uni, key]
            ax.bar(x, v, width=0.9, color=colour, alpha=1 if uni == "pit" else 0.35,
                   hatch="" if uni == "pit" else "//", edgecolor=colour, linewidth=1.2)
            ax.text(x, v + 0.5, f"{v:.1f}%", ha="center", va="bottom", color=INK, fontsize=11)
    ax.axhline(spy_cagr, color=AQUA, linestyle="--", linewidth=1.6)
    ax.text(2.0, spy_cagr + 0.5, f"SPY {spy_cagr:.1f}%", color=INK, fontsize=10, ha="center")  # in the gap
    ax.set_xticks([0.5, 3.5], [g[0] for g in groups], fontsize=11, color=INK)
    ax.set_xlim(-0.8, 4.8)
    ax.set_ylim(0, max(cagr.values()) * 1.18)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    style(ax, "Return per year: point-in-time vs naive universe (survivorship bias)")
    ax.tick_params(axis="x", length=0, colors=INK)
    ax.legend(handles=[matplotlib.patches.Patch(facecolor=MUTED, edgecolor=MUTED, label="members at the time (point-in-time)"),
                       matplotlib.patches.Patch(facecolor=MUTED, alpha=0.35, hatch="//", edgecolor=MUTED,
                                                label="today's members only (naive)")],
              frameon=False, loc="upper left", labelcolor=INK)
    fig.tight_layout()
    fig.savefig(OUT / "survivorship.png", dpi=150)
    print("wrote docs/figures/growth.png, drawdown.png, survivorship.png\n")

    table = pd.DataFrame([summary(runs["pit", "top1"], spy), summary(runs["pit", "top10"], spy), summary(spy, spy),
                          {**summary(runs["naive", "top1"], spy), "Strategy": "Last year's #1 (naive)"},
                          {**summary(runs["naive", "top10"], spy), "Strategy": "Last year's top 10 (naive)"}])
    print(table.round(2).to_string(index=False))
    for cost in (0, 50):
        u = rankable_universe(pd.read_parquet(CACHE / "coverage_pit_detail.parquet"), formation_dates(cal, w.years))
        r = run_strategy("top1", top_n(prices, u, w.rebalance, n=1), prices, cost, cal, w)
        print(f"last year's #1 at {cost} bps: CAGR {summary(r, spy)['CAGR %']:.2f}%")


if __name__ == "__main__":
    main()
