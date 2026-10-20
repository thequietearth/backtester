# Data source evaluation

**Status (2026-10-20): EODHD adopted.** The Historian plan is subscribed. It passes the traps and dividend tests, and price-sanity checks keep its broken series out of the ranking. Coverage is trusted from 2010, lower coverage for 1999–2009, and unreliable for 1996–98, which is why the backtest starts in 1999. If it fails, the fallback is Yahoo for 2011–2025 only. Membership comes from a separate source; see "Membership source" below.

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

**Paid month, v1 results (2026-10-19).** Subscribed to Historian.
- **Download:** `scripts/download_eodhd.py --scope v1` made 4,524 calls with 0 errors. That's prices, dividends and splits for 1,508 codes: every candidate for every member, plus SPY and RSP.
- **Mapping:** `scripts/build_price_cache.py` mapped the 1,262 membership spells as 854 automatic, 322 flagged for review and 86 missing. Of the missing spells, 52 ended before 1999 and 34 overlap 1999 or later.

**EODHD truncates old histories.** Of the delisted codes downloaded, 362 have prices starting exactly on 1997-12-31, another 36 on 1999-01-04 and 27 on 2003-09-10. Companies that still trade go back to 1994. For example, `WEN_old` (Wendy's International) starts at 1997-12-31. So for 1996–1998, many members can't be ranked, because ranking them needs prices from before 1998.

**Pass test 1, coverage** (`bt/coverage.py`). Final figures, after hand mapping and the price checks in pass test 4:

| Years | Coverage | Band |
|---|---|---|
| 1996–1998 | 42.9–48.0% | unreliable (before the 1999 start, shown to document why) |
| 1999–2009 | 86.4–94.6% | lower coverage |
| 2010–2025 | 96.6–99.8% | trusted |

Before hand mapping and price checks, 2005–2009 measured about 96%. The stricter checks set aside 13–18 suspect members a year there, which moved those years just under 95%.

Why members are missing in 1996–98: 623 member-years without formation data (the 1997 truncation) and 158 with no EODHD security at all (companies gone before 1999, such as Amoco, Sonat and NYNEX).

**Pass test 2, traps:** all six pass.
- `WEN` 1997 → `WEN_old`, flagged partial (the truncated history).
- `EP` 2003 and 2009 → `EP_old`.
- `FDO` 2008 → `FDO`.
- `AN` 1997 → flagged for review, because the ticker left the index and came back.
- `SNT` 1996 → flagged "small", since it's Senstar.

One mapping rule changed after the first run. A candidate whose prices stop when membership ended is now preferred even with a truncated history; before, today's `WEN` won on full coverage.

**Pass test 4, price sanity** (added during M1). Reviewing each year's top-ranked stocks exposed broken EODHD series, mostly for delisted companies before 2013. Examples:
- **Two securities mixed in one series:** Cooper Industries' price alternates between about $12 (volume 16) and $35 (volume 983,000) from day to day.
- **A corrupt adjustment factor:** Ambac's adjusted price is about $0.0001 against a traded price of about $59.
- **Splits applied twice:** Time Warner, Safeway and Gateway, whose adjusted price doubles on the split date while the traded price doesn't move.
- **Raw prices off by 9× to 444×:** R. R. Donnelley.
- **Garbage prints:** Univision, Goodrich and Countrywide, with swings of +58%, −24% and +38% on consecutive days.
- **The wrong security behind the ticker, with no `_old` code:** `BBBY` holds Overstock's history, and `PBG` and `SLR` hold thinly traded instruments.

Left alone, these produce "winners" like +17,292% (Cooper, 2006) and +49,349% (Donnelley, 2001), and the top-1 strategy picks exactly those. The coverage report (`bt/coverage.py`) now applies these checks to each member's formation year:
1. **Jump:** the adjusted price doubles or halves in a day → "suspect prices". The same rule fires once in 32 years across Yahoo's 20 long-lived stocks.
2. **Hole:** more than 10 trading days without a price → "suspect prices". This caught L Brands, whose "+84% day" was a jump across a missing month.
3. **Adjustment glitch:** the adjusted price moves more than 25% in a day while the traded price moves less than 10% → "suspect prices". This catches double-counted splits (Safeway, Gateway) and corrupt factors (Ambac). It compares against the true traded price, because EODHD's traded price is sometimes already split-adjusted.
4. **Unexplained gap:** over the year, the adjusted return and the traded return (on the same split basis) differ by more than 30% → "suspect prices". Dividends rarely explain more than about 10%. This caught Williams 2003 and Deluxe 2001, probably mishandled spin-offs.
5. **Small:** trading value under $0.5m a day, and not confirmed by hand → "suspect identity". Below that line nearly every case was broken data or another company.

**Calibration:** genuine winners that split during their big year stay "ok": Qualcomm 1999, Dell 1998, Nvidia 2001, Tesla 2020, Apple 2004 and XL 2009.

Suspect members aren't ranked, and they show up in the coverage gaps instead. Jumps during a holding year are only flagged, because real crashes (Lehman −94% in a day) must stay in the results. In 1999–2025 there are 214 suspect member-years.

**Hand fixes from this review** (`data/ticker_map.csv`):
- `BBBY` → `BBBYQ`, the real Bed Bath & Beyond. EODHD's `BBBY` and `BBBY_old` are both Overstock's history.
- `PBG` is excluded from December 2003, because EODHD's series becomes a different instrument in September 2004.
- Ambac is excluded, because of its corrupt factor.
- Found in M2's sanity check: two index tickers sharing one price series would be held twice by an equal-weight portfolio.
  - fja05680 lists Times Mirror twice, as `TMC` and `TMC.A`. Only `TMC.A` is mapped.
  - EODHD's `USW` holds MediaOne's prices, not U S West's, so U S West is missing.

  `build_price_cache.py` now reports any code shared by two members at the same time.

**Top pick per year after all checks** (pass test for top-1): every one is a genuine annual winner. Dell, Qualcomm, Reebok, Nvidia, Providian, Avaya, Autodesk, Valero, Allegheny Technologies, NOV, Family Dollar, XL, Netflix, Cabot Oil & Gas, PulteGroup, Netflix, Southwest, Netflix, Nvidia, NRG, AMD, AMD, Tesla, Devon, Occidental, Nvidia and Palantir, for 1999–2025 in order.

**Not done yet:** each top-10 pick for 1999–2012 still needs checking. That's an M3 task (see PLAN.md).

**Pass test 3, dividends:** passes (`scripts/validate_prices.py`). For 20 stocks that still trade, each year's adjusted return beats the raw-price return by about the dividend yield (KO +3.1% a year, XOM +3.0%, SPY +2.0%). Against Yahoo's total-return prices, the median yearly difference is 0.0. Only 4 of 611 full years differ by more than 0.5 points: PFE 1995, JPM 1995 and 1996, and KO 2001 (by 0.6).

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

**Chosen: fja05680/sp500 (MIT licence).** It was compared on 2026-10-19 with a fresh Wikipedia rebuild at every year-end from 1995 to 2025. Script: `scripts/compare_membership_sources.py`.

| | fja05680 | Wikipedia rebuild |
|---|---|---|
| Method | One snapshot per change date from 1996-01-02. Early years come from Andreas Clenow's *Trading Evolved* dataset; recent years from Wikipedia plus searches | Today's list, walked backwards through the change table (also Robot Wealth's method) |
| Early history | Full snapshots | The change table lists only 7 changes for 1995–99 and 8 for 2000–04, while the index really changes 20–30 times a year |
| Year-end 1995 | 487 members | Shares only 222 tickers with fja05680. Most of the rebuild is today's members, i.e. survivorship bias |
| Agreement | | Within about 5% only from 2019 onwards |
| Known events | All correct | Wrong for Amoco, Sonat, Wendy's and Enron |
| Tickers | As used at the time, except that bankrupt companies appear under their bankruptcy tickers (`ENRNQ`, `LEHMQ`, `AAMRQ`) and a few 1996 entries use later tickers (`ARNC`, `BHGE`) | Today's tickers, because renames such as FB → META aren't recorded |
| Company names | None | Yes, for the changes it lists |
| Licence | MIT, so the derived file can be committed with its notice | CC BY-SA |

The known events checked were Amoco, Sonat, Wendy's International, El Paso, Family Dollar, Enron, Lehman and Tesla.

**Robot Wealth:** its published data is an R file last updated in May 2020, built with the same Wikipedia method, so a fresh rebuild supersedes it. In 2026 Wikipedia moved the change table from "List of S&P 500 companies" to "Historical components of the S&P 500", which breaks older scrapers, including Robot Wealth's.

**fja05680 known issues:**
- It lists only 487 members on 1996-01-02, and its README says the first five years may miss some symbols.
- `AAL` and `AAMRQ` both appear in 1996, probably the same airline (AMR) counted twice.
- Its first snapshot is 1996-01-02, which stands in for the end-1995 formation date.

**Wikipedia's role:** a cross-check for recent years, and company names to help review the ticker mapping.

## References

- Massive: [stocks overview](https://massive.com/docs/rest/stocks/overview), [custom bars](https://massive.com/docs/rest/stocks/aggregates/custom-bars), [pricing](https://massive.com/pricing), [market data terms](https://massive.com/legal/market-data-terms-of-service), [individuals terms](https://massive.com/legal/individuals-terms-of-service)
- Yahoo: [yfinance README](https://github.com/ranaroussi/yfinance)
- Membership: [fja05680/sp500](https://github.com/fja05680/sp500)
- EODHD: [pricing](https://eodhd.com/pricing), [terms](https://eodhd.com/financial-apis/terms-conditions), [delisted data](https://eodhd.com/financial-apis/delisted-stock-companies-data-2), [Trustpilot](https://www.trustpilot.com/review/eodhistoricaldata.com), [ABS ticker-reuse write-up](https://incoherency.co.uk/notes/20260507.html)
- Norgate: [packages](https://norgatedata.com/stockmarketpackages.php), [free trial](https://norgatedata.com/subscribe/freetrial.php)
- Sharadar: [QuantRocket overview](https://www.quantrocket.com/sharadar/)
- Family Dollar as 2008's top S&P 500 stock: [CNN Money, 31 Dec 2008](https://money.cnn.com/2008/12/31/markets/SP500_year_end/index.htm)
