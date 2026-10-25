"""Static charts and numbers for docs/results.md, at the app's default settings
(1999-2025, 10 bps per side, cash earning the 3-month T-bill rate).

Usage: python scripts/make_figures.py   (after scripts/build_data.py)
Writes docs/figures/growth.png, drawdown.png, survivorship.png, timing.png, factors.png
and prints the numbers the write-up quotes. Colours are the app's validated palette (light
surface).
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
from bt.coverage import rankable_by_date, rankable_universe  # noqa: E402
from bt.data import load_tbill  # noqa: E402
from bt.metrics import drawdown_series  # noqa: E402
from bt.report import (backtest_window, contributions, daily_decisions, monthly_decisions, run_strategy,  # noqa: E402
                       summary, turnover)
from bt.strategies import (low_volatility, momentum, spy_buy_and_hold, spy_golden_cross, spy_rsi2,  # noqa: E402
                           spy_trend, top_n)
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
    tbill = load_tbill(ROOT / "data" / "tbill_dtb3.csv")
    w = backtest_window(cal, 1999, 2025)
    runs = {}
    for label, file in (("pit", "coverage_pit_detail.parquet"), ("naive", "coverage_naive_detail.parquet")):
        universe = rankable_universe(pd.read_parquet(CACHE / file), formation_dates(cal, w.years))
        runs[label, "top1"] = run_strategy("Last year's #1", top_n(prices, universe, w.rebalance, n=1),
                                           prices, 10, cal, w, tbill)
        runs[label, "top10"] = run_strategy("Last year's top 10", top_n(prices, universe, w.rebalance, n=10),
                                            prices, 10, cal, w, tbill)
    spy = run_strategy("SPY (benchmark)", spy_buy_and_hold(prices, {}, w.rebalance), prices, 10, cal, w, tbill)
    days = daily_decisions(cal, w)
    months, quarters = monthly_decisions(cal, w), monthly_decisions(cal, w, every=3)
    factor = {}
    for label in ("pit", "naive"):
        by_month = rankable_by_date(pd.read_parquet(CACHE / f"universe_monthly_{label}.parquet"))
        factor[label, "mom"] = run_strategy("Momentum (top 10%, monthly)", momentum(prices, by_month, months),
                                            prices, 10, cal, w, tbill)
        factor[label, "lowvol"] = run_strategy("Low volatility (50 calmest, quarterly)",
                                               low_volatility(prices, by_month, quarters), prices, 10, cal, w, tbill)
    timing = [run_strategy(name, rule(prices, {}, days), prices, 10, cal, w, tbill)
              for name, rule in (("SPY 200-day trend", spy_trend), ("SPY golden cross (50/200 days)", spy_golden_cross),
                                 ("SPY RSI(2) dip-buying", spy_rsi2))]
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
    # Timing rules: one small panel per rule against SPY, all on the same scale.
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True, facecolor=SURFACE)
    for ax, run in zip(axes, timing):
        ax.plot(10_000 * run.equity, color=BLUE, linewidth=1.8, label="Strategy")
        ax.plot(10_000 * spy.equity, color=AQUA, linestyle="--", linewidth=1.6, label="SPY (benchmark)")
        ax.set_yscale("log")
        ax.yaxis.set_major_locator(mticker.LogLocator(base=10, subs=(1, 2, 5)))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(dollars))
        ax.yaxis.set_minor_locator(mticker.NullLocator())
        style(ax, "")
        ax.set_title(run.name, loc="left", fontsize=11, color=INK)
    axes[0].legend(frameon=False, loc="upper left", labelcolor=INK, fontsize=9)
    fig.suptitle("Timing rules on SPY: growth of $10,000, 1999–2025 (log scale)", x=0.01, ha="left",
                 fontsize=13, fontweight="bold", color=INK)
    fig.tight_layout()
    fig.savefig(OUT / "timing.png", dpi=150)
    # Momentum and low volatility: one panel each against SPY, same scale.
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True, facecolor=SURFACE)
    for ax, key in zip(axes, ("mom", "lowvol")):
        run = factor["pit", key]
        ax.plot(10_000 * run.equity, color=BLUE, linewidth=1.8, label="Strategy")
        ax.plot(10_000 * spy.equity, color=AQUA, linestyle="--", linewidth=1.6, label="SPY (benchmark)")
        ax.set_yscale("log")
        ax.yaxis.set_major_locator(mticker.LogLocator(base=10, subs=(1, 2, 5)))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(dollars))
        ax.yaxis.set_minor_locator(mticker.NullLocator())
        style(ax, "")
        ax.set_title(run.name, loc="left", fontsize=11, color=INK)
    axes[0].legend(frameon=False, loc="upper left", labelcolor=INK, fontsize=9)
    fig.suptitle("Momentum and low volatility: growth of $10,000, 1999–2025 (log scale)", x=0.01, ha="left",
                 fontsize=13, fontweight="bold", color=INK)
    fig.tight_layout()
    fig.savefig(OUT / "factors.png", dpi=150)
    print("wrote docs/figures/growth.png, drawdown.png, survivorship.png, timing.png, factors.png\n")

    table = pd.DataFrame([summary(runs["pit", "top1"], spy), summary(runs["pit", "top10"], spy),
                          *[summary(r, spy) for r in timing],
                          summary(factor["pit", "mom"], spy), summary(factor["pit", "lowvol"], spy), summary(spy, spy),
                          {**summary(runs["naive", "top1"], spy), "Strategy": "Last year's #1 (naive)"},
                          {**summary(runs["naive", "top10"], spy), "Strategy": "Last year's top 10 (naive)"},
                          {**summary(factor["naive", "mom"], spy), "Strategy": "Momentum (naive)"},
                          {**summary(factor["naive", "lowvol"], spy), "Strategy": "Low volatility (naive)"}])
    print(table.round(2).to_string(index=False))
    u = rankable_universe(pd.read_parquet(CACHE / "coverage_pit_detail.parquet"), formation_dates(cal, w.years))
    for cost in (0, 50):
        r = run_strategy("top1", top_n(prices, u, w.rebalance, n=1), prices, cost, cal, w, tbill)
        print(f"last year's #1 at {cost} bps: CAGR {summary(r, spy)['CAGR %']:.2f}%")
    zero_spy = run_strategy("SPY", spy_buy_and_hold(prices, {}, w.rebalance), prices, 10, cal, w)
    for (name, rule), run in zip((("200-day", spy_trend), ("golden cross", spy_golden_cross), ("RSI(2)", spy_rsi2)), timing):
        zero = run_strategy(name, rule(prices, {}, days), prices, 10, cal, w)
        print(f"{name} with cash at 0% instead of T-bills: CAGR {summary(zero, zero_spy)['CAGR %']:.2f}% "
              f"(vs {summary(run, spy)['CAGR %']:.2f}%)")

    # Momentum and low volatility: what the write-up quotes.
    for key in ("mom", "lowvol"):
        run = factor["pit", key]
        sold = turnover(run)
        bounds = run.window.boundaries
        per_year = pd.Series({y: sold[(sold.index >= bounds[i]) & (sold.index < bounds[i + 1])].sum()
                              for i, y in enumerate(run.yearly.index)})
        held = (run.holdings.drop(columns="cash") > 0).sum(axis=1).mean()
        print(f"\n{run.name}: average {held:.0f} stocks held, turnover {100 * per_year.iloc[1:].mean():.0f}% a year "
              "(after the first)")
        for lo, hi in ((1999, 2009), (2010, 2025)):
            r, b = run.yearly.loc[lo:hi], spy.yearly.loc[lo:hi]
            print(f"  {lo}-{hi}: {100 * ((1 + r).prod() ** (1 / len(r)) - 1):.1f}% a year vs SPY "
                  f"{100 * ((1 + b).prod() ** (1 / len(b)) - 1):.1f}%")
        diff = 100 * (run.yearly - spy.yearly)
        print("  years vs SPY (pts):", ", ".join(f"{y} {d:+.0f}" for y, d in diff.items()))
        top = contributions(run, prices).sum().sort_values(ascending=False)
        print("  biggest total contributors (pts of each year's starting value, summed):",
              ", ".join(f"{c} {100 * v:+.0f}" for c, v in top.head(5).items()))
        for cost in (0, 50):
            r = run_strategy(run.name, run.weights, prices, cost, cal, w, tbill)
            print(f"  at {cost} bps: CAGR {summary(r, spy)['CAGR %']:.2f}%")


if __name__ == "__main__":
    main()
