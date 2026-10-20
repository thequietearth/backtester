# Backtester: project instructions for Claude Code

## What this is
A Streamlit app that backtests simple, rule-based stock strategies on the S&P 500 over roughly 30 years and compares the results with SPY.

It has two goals:
1. Learn how strategies and backtesting really work.
2. Be a polished portfolio piece: public code and a write-up, with the app run locally.

Correct, honest results matter more than features.

PLAN.md holds the milestones, done-criteria and open decisions. Read it at the start of every session.

## Stack
- Python 3.11+, pandas, numpy, pyarrow (parquet), plotly, streamlit, pytest, python-dotenv
- Price data: the source chosen in M1 (see PLAN.md and `docs/data-source-evaluation.md`). yfinance is only a fallback and a cross-check.
- No backtesting libraries (backtrader, vectorbt, zipline, bt). The engine is written by hand on purpose.
- The app runs locally and reads only the local parquet cache. It never calls a data API while running.
- Price data is licensed for personal use only. It lives in `data/raw/` and `data/cache/`, which are gitignored, and is never committed. API keys live in a gitignored `.env` file (format in `.env.example`) and are loaded with python-dotenv. Never put them in code, never print them, and never read `.env` directly.

## Layout
```
backtester/
  app.py                # Streamlit entry point
  pages/                # extra Streamlit pages (e.g. coverage report)
  bt/
    universe.py         # point-in-time S&P 500 membership
    data.py             # price download, caching, ticker mapping
    coverage.py         # coverage report
    engine.py           # target weights -> daily equity curve + trade log
    strategies.py       # one function per strategy
    metrics.py          # CAGR, volatility, Sharpe, drawdown, etc.
  data/
    raw/                # downloaded source files (gitignored)
    cache/              # parquet price cache (gitignored)
    ticker_map.csv      # (ticker, date range) -> symbol to download, hand-maintained
  scripts/              # one-off build scripts (download, build cache)
  docs/                 # write-ups (e.g. sanity-check.md)
  tests/
```

## Core design
A strategy is a function that, for each rebalance date, returns target weights:

```
strategy(prices, universe, rebalance_dates, **params) -> DataFrame[date x ticker] of weights
```

Each row of weights sums to at most 1. Whatever is left over is held as cash.

The engine doesn't know or care which strategy produced the weights. It takes weights, prices and costs, and returns a daily equity curve and a trade log. Every strategy, from "buy last year's #1 stock" to a 200-day moving-average rule, runs through the same engine.

v1 only rebalances once a year, but build the engine to accept any rebalance dates, because daily rules come in v2.

## Correctness rules (non-negotiable)
1. **No lookahead.** A decision made on date t uses only data available at the close of t. Trades execute at the close of the next trading day. Include a test that proves it: changing any price after t must not change any decision made on or before t.
2. **Point-in-time universe.** Strategies may only pick from stocks that were S&P 500 members on the formation date. Today's constituent list is used only in the clearly labelled "naive universe" mode, which exists to show survivorship bias.
3. **Total-return prices.** Use prices adjusted for splits and dividends, for both stocks and the SPY benchmark. Check that the source's adjusted prices really include dividends.
4. **Never drop missing data silently.**
   - Record every member that has no usable price data: in the coverage report, and in a per-year "excluded" list the GUI can show.
   - A stock can only be ranked if it has price data for its full formation period.
5. **Delisted while held.** If a held stock's prices stop before the holding period ends:
   - exit at the last available price and move that money to cash
   - flag the trade in the trade log as "data ended, real outcome unknown"
   - detect the end without lookahead: a held stock is sold after more than 10 trading days in a row without a price (`bt/engine.py`), never by checking whether prices exist later
6. **Removed from the index mid-year.** Keep holding the stock until the next rebalance. We own the stock, not the index.
7. **Costs.** Charge transaction costs in basis points per side on every weight change. Make the rate configurable, default 10 bps.
8. **Benchmark.** Always show results next to SPY over exactly the same dates.
9. **A ticker is not a company.** The same ticker can belong to different companies at different times (`AN` was Amoco until 1998 and is AutoNation today). Match membership to prices by ticker and date. Flag any member whose price history looks like a different company, for example a name mismatch, or data that starts after the stock joined the index.
10. **Distrust extreme data.** The price source has broken series (mixed securities, splits applied twice, corrupt adjustments), and ranking strategies pick exactly those. Members failing the price-sanity checks in `bt/coverage.py` are not ranked; they count as gaps in the coverage report, never silently. Never "fix" a price by hand: map the right code in `data/ticker_map.csv` or exclude the dates. Holding-period jumps are flagged but kept, because real crashes must stay in the results.

## Scope rules
- Build milestones in PLAN.md order. Don't start the next milestone until the current one meets its done-criteria.
- Don't add features, strategies, pages or settings that aren't in the current milestone. Put new ideas under "Later" in PLAN.md and move on.
- Out of scope until PLAN.md says otherwise: ML/classifiers, LLM signals, intraday data, short selling, leverage, live trading, user accounts.
- If something in PLAN.md looks wrong or unclear, say so and propose a fix before coding around it.

## Working style
- At the start of each milestone, propose a short implementation plan (files, functions, tests) and wait for approval.
- For the engine and metrics, write the tests first. Use tiny made-up price series where the right answer can be worked out by hand.
- Keep functions small and pure: data in, data out. Streamlit code lives only in `app.py` and `pages/`.
- Cache downloads as parquet and never re-download what's already cached. Download in batches, and wait and retry if the data source starts refusing requests.
- At the end of each milestone, commit with a clear message and tick the milestone off in PLAN.md.
- The owner is learning this domain. Explain any non-obvious finance or statistics choice in a short comment or docstring.
