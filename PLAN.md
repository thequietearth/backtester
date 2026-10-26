# Backtester: build plan

## Goal
v1 is a Streamlit app, run locally with its code public, that honestly answers: "What if I had bought last year's best S&P 500 stock every January since 1999?"

It uses point-in-time index membership and compares that strategy with SPY and with a top-10 version.

## Key definitions
- **Backtest years:** 1999 to 2025, full calendar years. The start moved from 1996 after the M1 coverage report (see Decisions). The coverage report still shows 1996–98, to document the gap.
- **Formation date:** the last trading day of the previous year. The universe is the S&P 500 members on that date.
- **Formation period:** the 12 months ending on the formation date. Stocks are ranked on their total return over this period.
- **Entry:** the close of the first trading day of the year.
- **Holding period:** from entry until the close of the first trading day of the next year, when the next rebalance happens.
- **Point-in-time constituents:** the index members as of a given date.
- **Coverage:** the share of point-in-time members that have usable price data for both the formation period and the holding period.

## Milestones

### M0: Setup ✅ (done 2026-10-17)
- Repo skeleton following the CLAUDE.md layout, plus `requirements.txt`, `.gitignore` and a README stub
- `app.py` shows a placeholder page, and pytest runs one trivial test

**Done when:** `streamlit run app.py` opens a page and `pytest` passes.

### M1: Data and coverage report (decision gate) ✅ (done 2026-10-20)
- **Point-in-time membership.** Evaluate these sources, recommend one and document its limits:
  - a. Robot Wealth's free historical constituents dataset, described in their article "How To Get Historical S&P 500 Constituents Data For Free" (goes back to 1990)
  - b. Rebuilding the history from Wikipedia's "List of S&P 500 companies" page, using its current list plus changes table, or its old page revisions. Prior art: github.com/bkestelman/sp500_historical_components
  - c. github.com/fja05680/sp500: one row per change date since 1996, already used in the Yahoo probe. Known issues are in `docs/data-source-evaluation.md`.
  - Output: `data/constituents.parquet`, one row per (date, ticker), with at least one snapshot per formation date.
- **Price cache.** Daily closes adjusted for splits and dividends, from 1994-01-01 to today, for every ticker ever in the universe (including stocks that no longer trade), plus SPY and RSP, saved as parquet in `data/cache/`.
  - Start in 1994 because the 1996 ranking needs the close of 30 Dec 1994.
  - The source must have prices for delisted stocks, and must tell apart different companies that used the same ticker (e.g. `AN` was Amoco until 1998 and is AutoNation today). Yahoo fails both. The candidates and the pass tests are in `docs/data-source-evaluation.md`.
  - Price data is licensed for personal use only, so `data/raw/` and `data/cache/` are gitignored and never committed.
- **Ticker map.** `ticker_map.csv` lists renamed tickers (e.g. FB → META). Start with the renames the coverage report turns up. Because tickers get reused, entries need a date range, not just the ticker.
- **Coverage report** (`bt/coverage.py`, a Streamlit page and a CSV export). For each year it shows:
  - number of members
  - members with full formation-period data
  - members with holding-period data
  - coverage %
  - the list of missing tickers
  - members whose data ends during the holding year (counted as covered, but flagged)

**Done when:** the price source passes the tests in `docs/data-source-evaluation.md`, the report runs end to end for 1996–2025, and Raymond has decided the start year and coverage threshold (record them under Decisions below).

### M2: Engine and metrics ✅ (done 2026-10-20)
- **`engine.py`:** takes weights, prices and costs, and returns a daily equity curve, holdings and a trade log (with delisting flags).
- **`metrics.py`:**
  - CAGR
  - annualised volatility
  - Sharpe ratio (risk-free rate = 0 in v1; document this)
  - max drawdown and how long it lasted
  - best and worst year
  - % of years beating SPY
- **Tests:**
  - hand-computed cases on made-up prices: a single stock, two stocks, the effect of costs, and a stock delisted mid-period
  - the no-lookahead test from CLAUDE.md
- **Sanity check:** build an equal-weight point-in-time S&P 500, rebalanced yearly, and compare it with RSP from 2003.
  - Expect some gap, because RSP rebalances quarterly and charges fees.
  - Record the gap for each year. A year with an unusually large gap usually means a data problem, so investigate it.

**Done when:** the tests pass and the RSP comparison is written up in `docs/sanity-check.md`.

### M3: v1 strategies ✅ (done 2026-10-20)
- SPY buy and hold (the benchmark)
- Last year's #1 performer (top 1)
- Last year's top N, equal weight (N defaults to 10)
- Universe mode: point-in-time (default) or today's list, labelled "naive, shows survivorship bias"
- **Verify top-10 picks for 1999–2012** against independent facts: published annual winners, Yahoo for stocks that still trade, company histories. Fix or exclude in `data/ticker_map.csv`. M1 already checked every top-1 pick for 1999–2025, plus the top 3 for 1999–2012. EODHD's older data has broken series that the automatic checks may still miss (see `docs/data-source-evaluation.md`, pass test 4).

**Done when:** each strategy runs over the full backtest period, a manual spot check of 3 years shows sensible picks, and every top-10 pick for 1999–2012 has been checked.

### M4: GUI v1 and publish (v1 shipped) ✅ (done 2026-10-20; a fresh clone reproduced every result exactly)
- **Sidebar:** strategies (multi-select), N, start and end year, cost in bps, universe mode
- **Main view:**
  - growth of $10k vs SPY, on a log scale
  - drawdown chart
  - metric cards
  - year-by-year table: year, holdings, strategy return, SPY return, beat SPY?
  - coverage warnings on flagged years
  - a link to the coverage report page
- **Publish.** The app runs locally. The repo is public and holds code only, with no price data, because the data licence is personal-use only.
  - A script rebuilds `data/cache/` with your own data-source API key.
  - README: what the app does, how to rebuild the data and run it, and screenshots.
  - A results write-up with charts in `docs/`.

**Done when:** a fresh clone, plus the data build script, plus `streamlit run app.py` reproduces the results, and the README and write-up are published.

### M5: v2 (only after v1 is shipped)
Build in this order, each step with its own plan and done-criteria.

**M5a: SPY trend rules and the comparison view** ✅ (done 2026-10-22)
- Simple trend rules on SPY:
  - 200-day moving average: hold SPY when it's above, cash when below
  - golden cross (50-day vs 200-day average)
  - RSI(2) mean reversion
- Comparison view: pick any 2–4 strategies side by side

**M5b: price-based strategies on the point-in-time S&P 500** ✅ (done 2026-10-26)
- Academic momentum: rank on the last 12 months excluding the most recent month, hold the top 10%, rebalance monthly. The research version of v1's "last year's winners"
- Low volatility: hold the 50 least volatile stocks of the past year
- Built with them: month-end universes with the coverage report's checks (`bt.coverage.decision_universe`, which must agree with the report on every year-end), the frozen-price check, rename following (`bt.data.follow_renames`), the SPLV replica and momentum-ETF comparison (`scripts/sanity_factor_etfs.py`), and the holdings audit (`scripts/audit_holdings.py`), whose findings fixed data that also changed one v1 pick (Ball, 2003)

**M5c: contrarian** ✅ (done 2026-10-26)
- Last year's worst N. **Caution from M2's sanity check:** the price-sanity checks set aside real crashes along with broken data, which is exactly what this strategy looks for. Real crashes and data errors need telling apart (by hand, or with a second source) before its results can be trusted.
- Done with: hand verdicts on 26 set-aside crashes (`data/crash_review.csv`), a review of all 270 picks (`docs/worst10-review.md`), a spin-off screen, the contrarian strategy added to the holdings audit, and a floor for holdings whose data ended

### M6: Is momentum real? A robustness check (final milestone for now) ✅ (done 2026-10-26)
- Re-run the momentum rule with 36 variants (top 5/10/20%; 6/9/12-month lookback; skip the latest month or not; monthly or quarterly), all judged together. The best variant is never the headline
- For each: lead over SPY overall and per era (1999–2009, 2010–2025), Sharpe, worst fall, turnover, break-even cost, t-statistic and bootstrap
- Verdict criteria fixed before running: robust if ≥ 75% beat SPY and a majority beat it in each era; fragile if < 50% beat it; otherwise mixed
- Built: `bt/robustness.py`, `scripts/robustness.py`, the app's Robustness page, `docs/robustness.md`; the holdings audit extended to all variants

**Done when:** all 36 variants run on audited data, the page and write-up show every variant, and the verdict is stated against the fixed criteria. Result: **mixed**. 31 of 36 beat SPY over 1999–2025, all 36 in 1999–2009 but only 1 in 2010–2025, and none passes the luck test.

**Status: the project is complete for now.** The ideas below and under "Later" stay parked.

**Ideas that need more data work (assess before building):**
  - Dogs of the Dow: needs point-in-time Dow members and dividend history
  - Cap-weighted vs equal-weighted: needs historical shares outstanding

## Decisions
| Decision | Default | Status |
|---|---|---|
| Start year | 1999 | Decided after the M1 coverage report. EODHD's histories for delisted companies mostly start at the end of 1997, so 1996–98 coverage is only 45–49%. 1999–2004 run with a "lower coverage" label |
| Coverage threshold for a "trusted" year | 95% | Decided: ≥ 95% trusted; 85–95% labelled "lower coverage" with the missing list shown; top-1 picks in those years checked by hand against published year-end winners. The numbers may be adjusted after the M1 report |
| Membership source | fja05680/sp500 (MIT) | Decided, see `docs/data-source-evaluation.md` |
| Share classes in top-N (e.g. GOOG and GOOGL) | Allowed: each class is its own index member | Decided (M3). It never happened among the 270 checked picks |
| Ranking universe | Members on the formation date whose formation-year prices pass the checks. **No** price-at-entry requirement: entry is the day after the decision, so requiring it would use tomorrow's information. A pick that can't be bought stays as cash and is logged | Decided (M3) |
| What "a year" means in results | A holding year: from one January purchase to the next. The same dates apply to SPY | Decided (M3) |
| Known-bad prices | Listed by code and date range in `data/price_exclusions.csv` (blanked, never edited); remappings stay in `data/ticker_map.csv` | Decided (M3) |
| Top-10 pick review | All 270 picks for 1999–2025 checked: 192 against Yahoo, 78 by hand. See `docs/top10-review.md` | Done (M3) |
| Price history start | 1994-01-01 (the 1996 ranking needs the close of 30 Dec 1994) | Decided |
| Data ends during the holding year | Counts as covered, flagged in the coverage report | Decided |
| Price data source | EODHD Historian ($19.99/month) | Decided: adopted after M1. It passes the traps and dividend tests; coverage is trusted from 2010 and lower for 1999–2009. See `docs/data-source-evaluation.md` |
| Price sanity | A member whose formation year shows a one-day doubling or halving, a hole of 10+ trading days, an adjustment glitch or an unexplained adjusted-vs-traded gap, or which trades too little to be a member, is not ranked and counts as a gap. Holding-year jumps are flagged, never removed | Decided (M1) |
| Data budget | Up to about $30/month | Decided |
| Paid month | One month of EODHD Historian ($19.99). Subscribe only once the download scripts are ready; cancel before renewal | Decided |
| Download scope | Day 1: v1 needs (every S&P 500 member since 1996 in all code variants, plus SPY and RSP). Then all US common stocks and ETFs, active and delisted. Prices, dividends and splits throughout | Decided |
| Keeping data after cancelling | Kept, for private non-commercial use only. EODHD's personal terms allow private storage and analysis and don't require deletion | Decided |
| Entry timing | Close of the first trading day of the year | Default |
| Removed from the index mid-year | Keep holding until the next rebalance | Default |
| Delisted while held | Exit at the last price, flag the outcome as unknown | Default |
| Transaction cost | 10 bps per side | Default |
| Risk-free rate and cash | 3-month T-bill rate (FRED DTB3, committed), accrued daily at the previous day's rate. Cash earns it, and Sharpe is measured beyond it. The app can switch to 0% | Decided (M5a). At 0%, timing rules lose 0.5–1.8 points a year |
| Charts with several strategies | Small multiples: one chart per strategy against SPY, all on one scale. More than three lines in one chart can't be told apart reliably (palette validator) | Decided (M5a) |
| Timing-rule execution | Decide at the close, trade at the next close (no lookahead). Published RSI(2) results trade at the signal day's close, which flatters them | Decided (M5a) |
| Momentum (M5b) | Each month-end, rank members by return from the month-end 12 months back to the one 1 month back; hold the top 10% (rounded up), equal weight; trade at the next close | Decided (M5b) |
| Low volatility (M5b) | Each quarter-end (Dec, Mar, Jun, Sep), hold the 50 members with the lowest standard deviation of daily log returns over the past 12 months, equal weight. Inverse-volatility weighting only in the SPLV replica | Decided (M5b) |
| Universe for monthly and quarterly decisions | Members on the decision date whose prices pass the coverage report's checks over the 12 months ending on it (the same checks as the yearly report) | Decided (M5b) |
| Frozen prices | The same close more than 10 days in a row in the formation window → "suspect prices". Genuine members never exceeded 5 in 1998–2024 | Decided (M5b) |
| Renames | A renamed member keeps the code that carries on only for a plain rename the prices prove (`bt.data.follow_renames`); with a corporate action on the rename day, or disagreeing series, the old code is sold at its last price and flagged | Decided (M5b) |
| Held positions | `scripts/audit_holdings.py` lists every held day with an adjustment glitch or a one-day doubling/halving; each gets a verdict in `docs/sanity-check.md`. Data errors are fixed by mapping or excluding dates; real crashes stay | Decided (M5b) |
| Contrarian (M5c) | Last year's worst N, default 10, yearly, equal weight. Ranks the point-in-time members plus crashes a hand review found real (`data/crash_review.csv`); winner strategies don't read that file | Decided (M5c) |
| Data ended while held, contrarian | Sold at the last price (rule 5). The app also shows a floor counting every such holding as worthless; the review classifies each ending (most were takeovers) | Decided (M5c) |
| Robustness check (M6) | 36 momentum variants; verdict criteria fixed before running; all variants reported, never just the best | Decided (M6) |
| Publishing | Local app; public code and a write-up | Decided |
| Repo visibility | Public code, never any price data | Decided |
| Code licence | MIT | Decided |

## Later (parking lot, don't build yet)
- Classifier experiment, e.g. gradient boosting predicting "will this stock beat SPY next year?"
  - test it walk-forward (train only on the past, test on the next period, repeat)
  - judge it against the simple rule, after costs
- Text signals from SEC filings using an LLM classifier. Caveat: the model already knows what happened afterwards, so any backtest before its training cutoff leaks future information.
- Parameter sensitivity view (e.g. N from 1 to 50)
- Bootstrap or Monte Carlo resampling of yearly returns, to show how much of the result is luck
- Multi-asset ETF strategies
- Fundamental strategies: low P/E, high free-cash-flow yield, quality (return on capital), Greenblatt's "Magic Formula". Needs point-in-time fundamentals: SEC EDGAR XBRL data is free, carries each figure's filing date and covers delisted companies, from about 2009. Use a figure only after its filing date, as originally reported. A data project on the scale of M1; fits the trusted 2010–2025 years
- Dividend-yield strategy (trailing 12-month dividends ÷ price); the dividend data is already downloaded
- Settings for momentum and low volatility (share held, N, rebalancing frequency, inverse-volatility weighting)
- Record how each holding whose data ended really ended (takeover price, bankruptcy) and use it instead of the last price
- Screen every strategy's holdings for unadjusted spin-offs (big one-day drops on ordinary volume), not just the worst-10 picks
- Contrarian over three to five years, the horizon where research finds losers bounce back
- Add the adjusted-vs-traded drift check over each held stint to `scripts/audit_holdings.py`. It caught Transocean's merger day as a one-off, but needs a per-year threshold, because years of dividends legitimately open big gaps
- Norgate Platinum ($630/year: prices from 1990, delisted stocks, daily index membership) if EODHD's early years turn out too thin
