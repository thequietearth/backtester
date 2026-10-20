# Sanity check: our equal-weight S&P 500 vs RSP

**Result:** built from our data and engine, an equal-weight S&P 500 tracks RSP (the Invesco S&P 500 Equal Weight ETF) closely.
- **Rebalanced quarterly like RSP:** a correlation of 0.9995 across 2004–2025, with a typical yearly gap of 0.46 points.
- **The one large gap left, 2008 (+2.3 points),** comes from a known data limit: the crisis's worst casualties are missing or set aside. It isn't an engine error.

Reproduce: `python scripts/sanity_rsp.py`, adding `--quarterly` and/or `--keep-suspect` for the variants.

## Why this check
- **A backtest can be wrong in ways unit tests don't catch:** bad prices, wrong companies behind tickers, survivorship. Rebuilding a real, published index and comparing year by year exercises the membership, the price mapping, the price checks and the engine all at once.
- **Expected differences:** RSP rebalances quarterly, charges a fee (0.40% a year until 2013, 0.20% since), and has no data gaps. So some gap is expected.
- **What we're looking for:** a year with an unusually large gap, which usually means a data problem.

## Method
1. **Pick the holdings.** On each formation date (the last trading day of a year), take every index member that can be held: it has a price at entry, and its identity isn't suspect ("small").
2. **Main version:** members whose holding-year prices fail the price checks are also set aside (see `docs/data-source-evaluation.md`, pass test 4).
3. **Weight and trade:** weight them equally and trade at the next close, paying 10 bps per side. Members that disappear mid-year are sold at their last price, per the delisting rule.
4. **Three variants:**
   - **Annual:** buy and hold for the year.
   - **Quarterly:** also rebalance at the end of March, June and September, among that day's members, as RSP does.
   - **Keep suspect:** annual, but holding members whose holding-year prices fail the checks.

RSP started trading on 30 April 2003, so 2003 is a partial year for RSP and is left out of the summary statistics.

## Results (yearly total return, %)

| Year | Ours, annual | Ours, quarterly | RSP | Gap, annual | Gap, quarterly | SPY |
|---|---|---|---|---|---|---|
| 2003* | 34.1 | 34.4 | 33.5 | +0.6 | +1.0 | 28.2 |
| 2004 | 16.9 | 17.1 | 16.5 | +0.4 | +0.6 | 10.7 |
| 2005 | 7.9 | 7.7 | 7.4 | +0.5 | +0.3 | 4.8 |
| 2006 | 15.6 | 15.8 | 15.5 | +0.2 | +0.4 | 15.8 |
| 2007 | 3.3 | 1.4 | 0.9 | **+2.4** | +0.5 | 5.1 |
| 2008 | −37.4 | −37.8 | −40.1 | **+2.7** | **+2.3** | −36.8 |
| 2009 | 42.5 | 45.7 | 44.6 | **−2.1** | +1.1 | 26.4 |
| 2010 | 19.9 | 20.9 | 21.4 | −1.5 | −0.5 | 15.1 |
| 2011 | 0.3 | 0.4 | −0.7 | +1.0 | +1.1 | 1.9 |
| 2012 | 16.5 | 17.6 | 17.2 | −0.7 | +0.5 | 16.0 |
| 2013 | 36.5 | 36.2 | 35.5 | +1.0 | +0.6 | 32.3 |
| 2014 | 13.4 | 13.8 | 14.1 | −0.7 | −0.3 | 13.5 |
| 2015 | −1.9 | −2.5 | −2.7 | +0.8 | +0.2 | 1.2 |
| 2016 | 13.5 | 14.6 | 14.5 | −1.0 | +0.1 | 12.0 |
| 2017 | 18.8 | 18.3 | 18.5 | +0.3 | −0.2 | 21.7 |
| 2018 | −6.5 | −6.9 | −7.8 | +1.3 | +0.9 | −4.6 |
| 2019 | 28.3 | 29.2 | 28.9 | −0.6 | +0.3 | 31.2 |
| 2020 | 9.3 | 13.4 | 12.7 | **−3.3** | +0.7 | 18.3 |
| 2021 | 29.0 | 29.0 | 29.4 | −0.4 | −0.4 | 28.7 |
| 2022 | −10.4 | −11.4 | −11.6 | +1.2 | +0.3 | −18.2 |
| 2023 | 14.5 | 14.2 | 13.7 | +0.8 | +0.5 | 26.2 |
| 2024 | 12.9 | 13.3 | 12.8 | +0.1 | +0.5 | 24.9 |
| 2025 | 11.5 | 11.2 | 11.2 | +0.3 | +0.0 | 17.7 |

\* Partial year for RSP (from 30 April).

| 2004–2025 | Annual | Quarterly |
|---|---|---|
| Correlation with RSP | 0.9980 | **0.9995** |
| Typical gap (median of \|gap\|) | 0.82 pts | **0.46 pts** |
| Average gap | +0.12 pts | +0.42 pts |

## Findings
1. **The big annual gaps come from rebalancing frequency, not data.** Rebalancing quarterly like RSP shrinks 2007 from +2.4 to +0.5, 2009 from −2.1 to +1.1, and 2020 from −3.3 to +0.7.
   - In 2008, quarterly rebalancing kept buying stocks that went on falling.
   - In 2009 and 2020, it bought the crash just before the rebound.

   An annual strategy doesn't get that "rebalancing bonus" or penalty. That's a real feature of the strategy, not an error.
2. **The average gap of about +0.4 points a year is RSP's fee plus its trading costs.** Ours should beat RSP by roughly that much, and it does.
3. **2008 is the one unexplained year (+2.3 points), and the cause is missing losers:**
   - **Set aside by the price checks**, though they were real crashes: AIG, Genworth, Hartford, XL, National City, Wachovia, Weatherford and Coventry. Most fell 60–97% that year.
   - **No usable data:** Countrywide, Ambac, Sovereign and Marshall & Ilsley.

   About 15 of the year's worst stocks, roughly 3% of the portfolio, are missing, which flatters 2008 by around 2 points.
4. **Even so, the price checks do more good than harm.** Holding everything (`--keep-suspect`) makes 2004 +3.3 points and 2006 +1.4, because broken series inflate returns. The typical gap also widens, from 0.82 to 0.96 points.

## What this means for the strategies
- **Top-1 and top-10 winners (v1):** setting suspect members aside from the *ranking* is safe, because a crashing stock never ranks as a winner. Holdings are never removed. A held stock that crashes stays in the results, and if its data ends it is sold at its last price and flagged.
- **"Last year's worst N" (v2):** these checks would bias it, because they set aside exactly the stocks it looks for. Real crashes and broken data would need telling apart by hand before that strategy can be trusted. This is noted in PLAN.md.
- **2008 and other crisis years are slightly flattered** in any strategy that holds the whole index. The coverage report's per-year lists show which members are missing.
