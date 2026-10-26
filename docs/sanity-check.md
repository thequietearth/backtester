# Sanity check: our equal-weight S&P 500 vs RSP

**Result:** built from our data and engine, an equal-weight S&P 500 tracks RSP (the Invesco S&P 500 Equal Weight ETF) closely.
- **Rebalanced quarterly like RSP:** a correlation of 0.9996 across 2004–2025, with a typical yearly gap of 0.39 points.
- **The one large gap left, 2008 (+2.2 points),** comes from a known data limit: the crisis's worst casualties are missing or set aside. It isn't an engine error.

v2 (M5b) adds two more checks: a **low-volatility replica tracks SPLV**, a real low-volatility ETF, almost exactly, and an **audit of every day a strategy held a stock** found and fixed the price errors that could still reach results ([below](#v2-low-volatility-vs-splv)).

*Updated in M5b (2026-10-26):* the tables use the data after M3's and M5b's fixes (see `docs/data-source-evaluation.md`). Yearly gaps moved by up to 0.8 points and tracking improved slightly; the findings are unchanged.

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
| 2003* | 33.9 | 34.2 | 33.5 | +0.5 | +0.8 | 28.2 |
| 2004 | 16.6 | 16.9 | 16.5 | +0.2 | +0.4 | 10.7 |
| 2005 | 8.2 | 7.8 | 7.4 | +0.8 | +0.4 | 4.8 |
| 2006 | 15.5 | 15.6 | 15.5 | +0.1 | +0.1 | 15.8 |
| 2007 | 3.5 | 1.6 | 0.9 | **+2.6** | +0.7 | 5.1 |
| 2008 | −37.4 | −37.9 | −40.1 | **+2.7** | **+2.2** | −36.8 |
| 2009 | 42.2 | 45.5 | 44.6 | **−2.4** | +0.9 | 26.4 |
| 2010 | 20.7 | 21.5 | 21.4 | −0.7 | +0.1 | 15.1 |
| 2011 | 0.6 | 0.6 | −0.7 | +1.2 | +1.2 | 1.9 |
| 2012 | 16.5 | 17.7 | 17.2 | −0.6 | +0.5 | 16.0 |
| 2013 | 36.6 | 36.3 | 35.5 | +1.1 | +0.7 | 32.3 |
| 2014 | 13.5 | 13.9 | 14.1 | −0.5 | −0.2 | 13.5 |
| 2015 | −1.8 | −2.4 | −2.7 | +0.8 | +0.2 | 1.2 |
| 2016 | 13.4 | 14.6 | 14.5 | −1.1 | +0.1 | 12.0 |
| 2017 | 18.8 | 18.3 | 18.5 | +0.3 | −0.2 | 21.7 |
| 2018 | −7.2 | −7.6 | −7.8 | +0.7 | +0.2 | −4.6 |
| 2019 | 28.4 | 29.3 | 28.9 | −0.5 | +0.4 | 31.2 |
| 2020 | 9.5 | 13.6 | 12.7 | **−3.2** | +0.9 | 18.3 |
| 2021 | 29.0 | 29.0 | 29.4 | −0.4 | −0.4 | 28.7 |
| 2022 | −10.6 | −11.5 | −11.6 | +1.0 | +0.2 | −18.2 |
| 2023 | 14.6 | 14.2 | 13.7 | +0.9 | +0.5 | 26.2 |
| 2024 | 12.9 | 13.2 | 12.8 | +0.1 | +0.4 | 24.9 |
| 2025 | 11.5 | 11.4 | 11.2 | +0.3 | +0.2 | 17.7 |

\* Partial year for RSP (from 30 April).

| 2004–2025 | Annual | Quarterly |
|---|---|---|
| Correlation with RSP | 0.9981 | **0.9996** |
| Typical gap (median of \|gap\|) | 0.76 pts | **0.39 pts** |
| Average gap | +0.15 pts | +0.43 pts |

## Findings
1. **The big annual gaps come from rebalancing frequency, not data.** Rebalancing quarterly like RSP shrinks 2007 from +2.6 to +0.7, 2009 from −2.4 to +0.9, and 2020 from −3.2 to +0.9.
   - In 2008, quarterly rebalancing kept buying stocks that went on falling.
   - In 2009 and 2020, it bought the crash just before the rebound.

   An annual strategy doesn't get that "rebalancing bonus" or penalty. That's a real feature of the strategy, not an error.
2. **The average gap of about +0.4 points a year is RSP's fee plus its trading costs.** Ours should beat RSP by roughly that much, and it does.
3. **2008 is the one unexplained year (+2.2 points), and the cause is missing losers:**
   - **Set aside by the price checks**, though they were real crashes: AIG, Genworth, Hartford, XL, National City, Wachovia, Weatherford and Coventry. Most fell 60–97% that year.
   - **No usable data:** Countrywide, Ambac, Sovereign and Marshall & Ilsley.

   About 15 of the year's worst stocks, roughly 3% of the portfolio, are missing, which flatters 2008 by around 2 points.
4. **Even so, the price checks do more good than harm.** Holding everything (`--keep-suspect`) makes 2006 +1.2 points instead of +0.1, because broken series inflate returns, and the typical gap widens from 0.76 to 0.84 points. (Before M5b's data fixes the difference was bigger: Ball's splits counted twice alone added about 2.5 points to 2004.)

## What this means for the strategies
- **Top-1 and top-10 winners (v1):** setting suspect members aside from the *ranking* is safe, because a crashing stock never ranks as a winner. Holdings are never removed. A held stock that crashes stays in the results, and if its data ends it is sold at its last price and flagged.
- **"Last year's worst N" (v2):** these checks would bias it, because they set aside exactly the stocks it looks for. Real crashes and broken data would need telling apart by hand before that strategy can be trusted. This is noted in PLAN.md.
- **2008 and other crisis years are slightly flattered** in any strategy that holds the whole index. The coverage report's per-year lists show which members are missing.

## v2: low volatility vs SPLV
The Invesco S&P 500 Low Volatility ETF (SPLV, since May 2011) follows published rules, so it can be rebuilt: on the last trading day of January, April, July and October, take the 100 index members with the lowest volatility over the past year, weight each by 1 / its volatility, and trade at the close of the third Friday of the following month. The replica uses our data, universe checks and engine, at 10 bps per side. SPLV charges 0.25% a year.

| 2012–2025 | Replica | SPLV | SPY |
|---|---|---|---|
| Return per year | 10.17% | 9.98% | 14.75% |
| Daily correlation with SPLV | 0.9965 | | |
| Tracking error | 1.2% a year | | |
| Correlation of monthly returns beyond SPY | **0.9986** | | |

Yearly gaps stay within ±1.0 point (largest: +1.0 in 2024, +0.9 in 2025). The replica beats SPLV by about its fee. The last row is the telling one: every fund moves with the market, but the replica beats or trails SPY in the same months as SPLV, so the volatility ranking, the universe and the data behind it work.

The app's simpler version (the 50 calmest members, equal weight, re-picked at the end of each quarter) returned 10.52% a year over the same years, with a correlation beyond SPY of 0.966.

Reproduce: `python scripts/sanity_factor_etfs.py`.

## v2: momentum vs momentum ETFs (rough)
No fund runs our momentum rule (top 10% by 12-1 month return, equal weight, monthly), so this is a rough comparison with two that follow the same idea differently:
- **MTUM** (iShares MSCI USA Momentum, since 2013): about 125 stocks, risk-adjusted momentum, rebalanced twice a year, weighted towards big companies.
- **SPMO** (Invesco S&P 500 Momentum, since late 2015, compared from 2017 because it barely traded at first): 100 stocks, weighted by momentum and size.

| | Ours | Fund | SPY | RSP (equal weight) | Correlation beyond SPY |
|---|---|---|---|---|---|
| vs MTUM, 2014–2025 | 11.1% | 14.2% | 13.5% | 10.6% | 0.62 |
| vs SPMO, 2017–2025 | 12.5% | 19.4% | 15.0% | 11.1% | 0.45 |

- **The direction agrees, the numbers don't, and the main reason is weighting.** Both funds put more money in big companies; ours is equal weight. In these years the giants led: equal-weight RSP trailed SPY by about 3 points a year. Measured against its own baseline, our momentum beat RSP by 0.5 points a year (2014–2025), much as MTUM beat SPY by 0.6.
- **The big yearly gaps are mega-cap years:** 2017, 2020 and 2024, when a few giants such as Nvidia carried the funds. In 2022 ours was far ahead (−5.5% against MTUM's −19.7%), because monthly re-ranking moved into energy stocks faster.
- **The picks look like momentum:** for example Nvidia (+182%) and Freeport-McMoRan at the end of 2016, AMD (+112%) and Lam Research at the end of 2019, Nvidia and Meta at the end of 2023.

## v2: holdings audit
The coverage report's price checks keep broken series out of the *ranking*. But a stock bought before its data breaks is still held, and holding-period moves are kept on purpose, because real crashes must stay in the results. v1 holds ten stocks a year; momentum and low volatility hold about 50 and trade every month or quarter, so they meet far more corporate events. `scripts/audit_holdings.py` lists every day a strategy held a stock while its price moved in a way that needs a verdict:
- **Glitch:** the adjusted price moves more than 25% while the traded price moves less than 10%. Always a data error.
- **Jump:** the adjusted price doubles or halves in a day. Either a real crash or broken data, judged by hand.

It runs last year's top 50 (which contains every smaller top N), momentum and low volatility over 1999–2025 in both universes. The first run found these, all fixed in `data/ticker_map.csv` or `data/price_exclusions.csv`:

| Stock, date | Found | Effect | Fix |
|---|---|---|---|
| Ball, Feb 2002 and Aug 2004 | Glitch: EODHD's `BLL` applies both splits twice (adjusted +210% in 2002, +1,174% in 2004; really +46% and +49%) | +2.5 points to momentum each time | Remapped to `BALL`, the same company with clean adjustments |
| St. Jude Medical, Jul 2002 | Glitch: the split is counted twice (+86%) | +1.8 points to momentum | Three weeks around the split excluded |
| US Steel, May 2005 | Glitch: EODHD records a 2-for-1 split that never happened (+94%) | +1.9 points to momentum | Three weeks excluded |
| Golden West, Mar 2003 | Jump: the code turns into a different instrument ($71 → $2.20, then penny prices) | −2 points to momentum and low volatility | Prices from 5 Mar 2003 excluded |
| Wendy's, Sep 2003 | Jump: EODHD's `WEN_old` is Triarc's history, like today's `WEN` (−68% is Triarc's share distribution) | −1.4 points to low volatility | Wendy's International marked as having no usable prices |
| Transocean, Nov 2007 | Merger day: adjusted +30%, though holders got shares and cash worth less than the old share | +0.6 points to momentum | Three weeks excluded |

The Transocean move was neither a glitch nor a jump (the traded price moved too, by +41%), so the audit didn't flag it. It was caught by a separate one-off check comparing adjusted and traded returns over each held stint. The remaining flagged days are real and stay in the results:

| Stock, date | Move | Verdict |
|---|---|---|
| Apple, 29 Sep 2000 | −52% | Real: profit warning |
| Enron, Nov–Dec 2001 | −85%, +117% | Real: collapse and bankruptcy trading |
| Globe Life, 11 Apr 2024 | −53% | Real: short-seller report |

The audit also checked positions held when a stock left the index (rule 6: keep holding until the next rebalance), because some codes carry on as junk after a takeover, or with a spin-off left unadjusted. Momentum held 86 positions across a removal, low volatility 32 and top 10 13. None moved badly afterwards.

**M5c added the contrarian strategy (last year's worst 50) to the audit.** Losers meet far more extreme days: the worst 50 had 41 flagged days in the first run, 14 of them Signature Bank's shares trading for pennies after the bank failed. Two needed fixes:
- **Time Warner, October 2003:** a fake −66% from a change of split basis;
- **Williams, October 2002:** a glitch from bogus dividends, which moved the start of Williams' exclusion back to July 2002.

A third, American Capital's bogus June 2009 dividend, was found by comparing adjusted and traded returns over each holding year. Details are in `docs/worst10-review.md`. The rest are real and stay:
- bankruptcies and failures: Harnischfeger, Owens Corning, HealthSouth, Calpine, Dana, Freddie Mac, Washington Mutual, Circuit City, old GM, CIT, PG&E, SVB and Signature Bank;
- crisis crashes: National City, Qwest, Quanta Services and Williams' July 2002 liquidity crisis;
- the March 2020 oil crash.

Reproduce: `python scripts/audit_holdings.py`.
