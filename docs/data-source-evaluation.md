# Data source evaluation

**Status (2026-10-17):** EODHD's Historian plan is under test. It passed the free symbol-list check; the paid month comes next. If it fails, the fallback is Yahoo for 2011–2025 only. Membership comes from a separate source; see "Membership source" below.

## What the data has to do

The v1 strategy buys last year's best S&P 500 stock (or top N) every January. Each year that needs:

1. **Who was in the index** on the formation date (the last trading day of the previous year).
2. **Total-return prices at both year-ends for every member**, including stocks that no longer trade. This is the ranking.
3. **The right company behind each ticker on each date.** Tickers get reused, so a ticker alone is not enough.
4. **Daily prices for the stocks actually held**, plus SPY and RSP. These feed the equity curve, drawdown and volatility.

Constraints:
- Prices from 1994-01-01. The 1996 ranking needs the close of 30 Dec 1994.
- Budget up to about $30/month.
- The app runs locally and the code is public. Every source considered is licensed for personal use only, so price data is never committed.

## Pass tests for a price source

A source is adopted only if it passes all four:

1. **Coverage:** at least 95% per year from 1996, using the PLAN.md definition (data for the full formation period and the holding period).
2. **The six traps below:** each must return the right company's prices, or be clearly missing rather than silently wrong.
3. **Dividends:** for stocks that still trade, adjusted prices must match a total-return series (cross-check against Yahoo).
4. **Licence:** allows storing and analysing the data privately on your own machine.

### The six traps

The Yahoo probe found these. Each would make a Yahoo-only backtest pick the wrong stock as "last year's #1".

| Backtest year | Ticker | Real index member | What Yahoo returns |
|---|---|---|---|
| 1996 | `AN` | Amoco (merged into BP, 1998) | AutoNation: +954% in 1995, so it ranks #1 |
| 1997 | `SNT` | Sonat (bought by El Paso, 1999) | Senstar Technologies: +216% in 1996, ranks #1 |
| 1998 | `WEN` | Wendy's International | Triarc, which bought Wendy's in 2008 and took the ticker: +137% in 1997, ranks #1 |
| 2004 | `EP` | El Paso Corp (bought by Kinder Morgan, 2012) | Empire Petroleum: +639% in 2003, ranks #1 |
| 2009 | `FDO` | Family Dollar, the real #1 of 2008 (about +38%) | Nothing, so the pick becomes H&R Block |
| 2010 | `EP` | El Paso Corp | Empire Petroleum: +571% in 2009, ranks #1 |

Other reused tickers seen: `T` (AT&T Corp until 2005; Yahoo has SBC's history), `AMP` (AMP Inc; now Ameriprise), `CCI` (Citicorp; now Crown Castle).

A top-1 strategy is especially exposed. A reused ticker usually belongs to a small, volatile company, and its wild returns beat every real member, so the ranking picks the error *because* it is extreme.

## Sources

### Yahoo Finance (yfinance): fallback only, 2011–2025

**Probe.** Membership came from fja05680/sp500. Yahoo adjusted closes were downloaded for all 1,171 tickers that were members on any formation date from 1996 to 2025. Scripts: `scripts/probe_yahoo_coverage.py` and `scripts/probe_yahoo_top1.py`.

| Year | Members | With data | Coverage | | Year | Members | With data | Coverage |
|---|---|---|---|---|---|---|---|---|
| 1996 | 487 | 178 | 36.6% | | 2011 | 497 | 327 | 65.8% |
| 1997 | 488 | 186 | 38.1% | | 2012 | 497 | 334 | 67.2% |
| 1998 | 488 | 203 | 41.6% | | 2013 | 497 | 346 | 69.6% |
| 1999 | 493 | 216 | 43.8% | | 2014 | 497 | 349 | 70.2% |
| 2000 | 492 | 227 | 46.1% | | 2015 | 499 | 359 | 71.9% |
| 2001 | 492 | 236 | 48.0% | | 2016 | 502 | 372 | 74.1% |
| 2002 | 496 | 243 | 49.0% | | 2017 | 506 | 392 | 77.5% |
| 2003 | 494 | 253 | 51.2% | | 2018 | 505 | 405 | 80.2% |
| 2004 | 494 | 257 | 52.0% | | 2019 | 505 | 418 | 82.8% |
| 2005 | 495 | 260 | 52.5% | | 2020 | 505 | 430 | 85.1% |
| 2006 | 497 | 271 | 54.5% | | 2021 | 505 | 442 | 87.5% |
| 2007 | 497 | 281 | 56.5% | | 2022 | 505 | 453 | 89.7% |
| 2008 | 497 | 298 | 60.0% | | 2023 | 503 | 469 | 93.2% |
| 2009 | 498 | 303 | 60.8% | | 2024 | 503 | 476 | 94.6% |
| 2010 | 499 | 321 | 64.3% | | 2025 | 503 | 484 | 96.2% |

**Findings:**
- **Yahoo keeps no history for stocks that no longer trade.** In 30 years, no member's data ended during a holding year. Stocks delisted in mid-2026 already had only one row left. So the missing members are not random: they are the ones that were later acquired, merged or went bust. Survivorship bias comes back through the prices even with a point-in-time membership list.
- **Reused tickers return the current owner's history**; see the traps above.
- **Spot checks:** 15 randomly chosen no-data tickers, re-downloaded one at a time, really are absent ("possibly delisted"), so this is not rate limiting.
- **2011–2025 picks look right.** They match the annual winners known from memory: Netflix, PulteGroup, Southwest, Nvidia, AMD, Tesla, Palantir.
- **Licence:** the yfinance README says Yahoo's API is "intended for personal use only".

**Verdict:** not usable for 1996–2010. Usable as a fallback for 2011–2025 if identity checks are added and each year's pick is checked against published year-end winners. Fine for SPY and RSP, which still trade.

<details>
<summary>Yahoo-only #1 pick by year (for later spot checks)</summary>

| Year bought | Pick | Formation return | | Year bought | Pick | Formation return |
|---|---|---|---|---|---|---|
| 1996 | AN ❌ | +954% | | 2011 | NFLX | +219% |
| 1997 | SNT ❌ | +216% | | 2012 | ISRG | +80% |
| 1998 | WEN ❌ | +137% | | 2013 | PHM | +188% |
| 1999 | AAPL | +212% | | 2014 | NFLX | +298% |
| 2000 | QCOM | +2619% | | 2015 | LUV | +126% |
| 2001 | EOG | +213% | | 2016 | NFLX | +134% |
| 2002 | NVDA | +308% | | 2017 | NVDA | +227% |
| 2003 | BSX | +76% | | 2018 | NRG | +134% |
| 2004 | EP ❌ | +639% | | 2019 | AMD | +80% |
| 2005 | ADSK | +210% | | 2020 | AMD | +148% |
| 2006 | VLO | +128% | | 2021 | TSLA | +743% |
| 2007 | ATI | +153% | | 2022 | DVN | +196% |
| 2008 | NOV | +140% | | 2023 | OXY | +119% |
| 2009 | HRB ❌ | +26% | | 2024 | NVDA | +239% |
| 2010 | EP ❌ | +571% | | 2025 | PLTR | +340% |

❌ = confirmed wrong. Picks for 1996–2010 without a mark are unverified: the real #1 may be a stock Yahoo no longer has.
</details>

### EODHD: under test

- **Company:** Unicorn Data Services, Lyon, France (835 149 998 R.C.S. Lyon), founded 2017. Trustpilot rates it 4.5/5 from about 139 reviews.
- **Plan:** Historian, $19.99/month ($199/year). 30+ years of daily data and 100,000 API calls a day. The free tier has 20 calls a day and only one year of history.
- **Terms (personal plans):**
  - You may "store, manipulate, and analyze the data for private, non-commercial purposes".
  - Redistributing or displaying it, "in its original or repackaged form", is not allowed.
  - Payments are non-refundable. You can cancel any time, with a one-month minimum.
  - The terms don't say whether you may keep data after cancelling.
- **Delisted stocks:**
  - Listed per exchange with `delisted=1`.
  - Stocks delisted before 2018 have end-of-day prices only, which is all we need.
  - An older EODHD blog post says its delisted coverage starts with companies delisted from January 2000 onwards. Members that disappeared in 1996–99 (e.g. Amoco) may be missing.
- **Reused tickers:** still a risk. A May 2026 write-up found that `ABS` returns the new company, not Albertsons.
- **Adjusted close:** the adjustment method isn't documented, so pass test 3 matters here.

**Free check (2026-10-17):** done with `scripts/probe_eodhd_symbols.py`, using 2 API calls. The symbol lists are cached in `data/raw/eodhd/`.

EODHD lists 50,964 active and 60,433 delisted US symbols (33,186 of the delisted ones are common stock). The six traps:

| Trap | Real company | EODHD |
|---|---|---|
| 1998 `WEN` | Wendy's International | ✅ `WEN_old`, kept separate from today's `WEN` |
| 2004, 2010 `EP` | El Paso Corp | ✅ `EP_old`, kept separate from Empire Petroleum's `EP` |
| 2009 `FDO` | Family Dollar | ✅ `FDO` in the delisted list |
| 1996 `AN` | Amoco (gone 1998) | ❌ not listed |
| 1997 `SNT` | Sonat (gone 1999) | ❌ not listed |

**Estimated coverage.** This is an upper bound: members Yahoo covers, plus members Yahoo misses whose ticker or `ticker_old` is in EODHD's delisted list. It doesn't yet prove those symbols have 1990s prices. Script: `scripts/probe_eodhd_estimate.py`.

| Year | 1996 | 1997 | 1998 | 1999 | 2000 | 2003 | 2010 | 2025 |
|---|---|---|---|---|---|---|---|---|
| Yahoo | 36.6% | 38.1% | 41.6% | 43.8% | 46.1% | 51.2% | 64.3% | 96.2% |
| EODHD (est.) | 85.4% | 87.7% | 91.0% | 92.1% | 93.5% | 95.3% | 98.4% | 99.6% |

**Many of the remaining gaps are naming mismatches, not missing companies.** Searching by company name finds them under other codes. EODHD's suffixes are inconsistent (`1`, `_old`, `_old1`, `_old2`, `-A`), so the ticker map has to map each fja05680 ticker and date range to an EODHD code:
- Wachovia `WB_old2`, GTE `GTE1`, Lehman `LEH`, AMR `AMR_old`, Hilton `HLT1`
- HCA `HCA1`, Texaco `TX1`, Union Carbide `UK1`, Seagram `VO1`, WorldCom `MCWEQ`
- Schering-Plough `SGP_old1`, Times Mirror `TMC-A`, Sunoco `SUN1`, Dollar General `DG1`

**Not in EODHD at all:**
- Companies gone before 2000: Amoco, Sonat, NYNEX.
- A few later ones: 3Com, Georgia-Pacific, and Lucent (only the merged Alcatel-Lucent `ALU` is listed).

1996–1999 will probably stay below 95% even after mapping, because companies that disappeared before 2000 are missing.

**Next: one paid month of Historian ($19.99).**
1. For every member ticker, download every matching EODHD code, including the `1`, `_old` and `_old1` variants. That's a few thousand calls, well under the 100,000 daily limit. Cache them all locally.
2. Map each member to the code whose price history covers its membership dates, and review the mapping by company name.
3. Run pass tests 1–3: real coverage per year, the traps, and dividends included.
4. Decide: adopt EODHD, accept and label lower coverage for 1996–99, move the start year, or escalate to Norgate.

### Norgate Data (Platinum): strongest on paper, over budget

- **Price:** $630/year, or $346.50 for 6 months.
- **Data:** prices from 1990, delisted stocks included, and S&P 500 membership as an in/out flag per stock per day.
- **Free trial:** only 2 years of history, so it can't test the 1990s.
- **Use it if:** EODHD fails the early years and the full 1996 start is still a must.

### Sharadar (Nasdaq Data Link): not tested

- **Data:** delisted stocks included, with prices from about 1998 (so the first backtest year would be 2000). It has S&P 500 changes since 1957, possibly only bundled with fundamentals.
- **Price:** about $9–69/month per dataset, but this is a third-party figure, not verified.

### Massive (formerly Polygon.io): rejected

- **History:** prices only from 10 Sep 2003, so the first backtest year would be 2005. Full history needs Advanced ($199/month).
- **Adjustment:** prices are split-adjusted only; dividends would have to be applied by hand. It has no index membership data.
- **Licence:** individual plans ban apps for other users and public display, including derived charts and analytics. All data must be deleted on cancelling.
- **Strengths:** delisted tickers, CIK/FIGI identifiers, ticker-change events.

## Membership source

fja05680/sp500 was used for the probe. It has one row per change date from 1996-01-02, with tickers as used at the time per its README.

**Known issues:**
- It lists only 487 members on 1996-01-02, and its README says the first five years may miss some symbols.
- `AAL` and `AAMRQ` both appear in 1996, probably the same airline (AMR) counted twice.
- Some later tickers are used for 1996, e.g. `ARNC` and `BHGE`.

Robot Wealth and Wikipedia are still to be compared in M1.

## References

- Massive: [stocks overview](https://massive.com/docs/rest/stocks/overview), [custom bars](https://massive.com/docs/rest/stocks/aggregates/custom-bars), [pricing](https://massive.com/pricing), [market data terms](https://massive.com/legal/market-data-terms-of-service), [individuals terms](https://massive.com/legal/individuals-terms-of-service)
- Yahoo: [yfinance README](https://github.com/ranaroussi/yfinance)
- Membership: [fja05680/sp500](https://github.com/fja05680/sp500)
- EODHD: [pricing](https://eodhd.com/pricing), [terms](https://eodhd.com/financial-apis/terms-conditions), [delisted data](https://eodhd.com/financial-apis/delisted-stock-companies-data-2), [Trustpilot](https://www.trustpilot.com/review/eodhistoricaldata.com), [ABS ticker-reuse write-up](https://incoherency.co.uk/notes/20260507.html)
- Norgate: [packages](https://norgatedata.com/stockmarketpackages.php), [free trial](https://norgatedata.com/subscribe/freetrial.php)
- Sharadar: [QuantRocket overview](https://www.quantrocket.com/sharadar/)
- Family Dollar as 2008's top S&P 500 stock: [CNN Money, 31 Dec 2008](https://money.cnn.com/2008/12/31/markets/SP500_year_end/index.htm)
