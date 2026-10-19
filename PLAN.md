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

### M2: Engine and metrics
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

### M3: v1 strategies
- SPY buy and hold (the benchmark)
- Last year's #1 performer (top 1)
- Last year's top N, equal weight (N defaults to 10)
- Universe mode: point-in-time (default) or today's list, labelled "naive, shows survivorship bias"
- **Verify top-10 picks for 1999–2012** against independent facts: published annual winners, Yahoo for stocks that still trade, company histories. Fix or exclude in `data/ticker_map.csv`. M1 already checked every top-1 pick for 1999–2025, plus the top 3 for 1999–2012. EODHD's older data has broken series that the automatic checks may still miss (see `docs/data-source-evaluation.md`, pass test 4).

**Done when:** each strategy runs over the full backtest period, a manual spot check of 3 years shows sensible picks, and every top-10 pick for 1999–2012 has been checked.

### M4: GUI v1 and publish (v1 shipped)
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
- Contrarian: last year's worst N
- Simple trend rules on SPY:
  - 200-day moving average: hold SPY when it's above, cash when below
  - golden cross (50-day vs 200-day average)
  - RSI(2) mean reversion
- Comparison view: pick any 2–4 strategies side by side
- Ideas that need more data work (assess before building):
  - Dogs of the Dow: needs point-in-time Dow members and dividend history
  - Cap-weighted vs equal-weighted: needs historical shares outstanding

## Decisions
| Decision | Default | Status |
|---|---|---|
| Start year | 1999 | Decided after the M1 coverage report. EODHD's histories for delisted companies mostly start at the end of 1997, so 1996–98 coverage is only 45–49%. 1999–2004 run with a "lower coverage" label |
| Coverage threshold for a "trusted" year | 95% | Decided: ≥ 95% trusted; 85–95% labelled "lower coverage" with the missing list shown; top-1 picks in those years checked by hand against published year-end winners. The numbers may be adjusted after the M1 report |
| Membership source | fja05680/sp500 (MIT) | Decided, see `docs/data-source-evaluation.md` |
| Share classes in top-N (e.g. GOOG and GOOGL) | Not decided | Open, decide in M3 |
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
| Risk-free rate for Sharpe | 0 | Revisit in v2 |
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
- Norgate Platinum ($630/year: prices from 1990, delisted stocks, daily index membership) if EODHD's early years turn out too thin
