# Worst-10 pick review (M5c)

**Result:** all 270 point-in-time worst-10 picks for 1999–2025 were checked, 27 years × 10.
- **145 confirmed automatically:** formation-year and holding-year returns match Yahoo's dividend-adjusted prices within about 5%.
- **125 checked by hand:** mostly delisted companies Yahoo has no prices for. Each formation-year loss was compared with the company's history, and EODHD's adjusted return with its own traded-price return.

The contrarian strategy needed one more step first. The price checks set aside real crashes along with broken data, and last year's losers are exactly those stocks. **26 members set aside as "suspect prices" would rank among a year's 15 worst.** Each got a hand verdict in `data/crash_review.csv`: 11 real crashes, which the contrarian ranking may use, and 15 broken series, which stay out. The winner strategies don't read the file.

The review found more broken data that the automatic checks miss: two **spin-offs missing from the adjusted prices** (a spin-off looks exactly like a crash), **dividends that were never paid**, and a **change of split basis**. All are fixed by excluding dates, never by editing a price. None affects the winner strategies' published results.

Reproduce: `python scripts/review_worst10.py --crashes` (evidence for the verdicts), then `python scripts/review_worst10.py` (writes `data/cache/worst10_review.csv`).

## Real crash or broken data?

| Bought | Stock | Loss the year before | Rank among losers | Verdict | Evidence |
|---|---|---|---|---|---|
| 1999 | Marathon Oil Corporation (`MRO`) | −53% | 10 | **broken** | Traded price halves overnight on 1998-12-21 (16.92 -> 8.33) on normal volume; no event explains it |
| 2001 | Apple Inc. (`AAPL`) | −71% | 10 | **real** | Apple fell 52% on 2000-09-29 after a profit warning; the year's -71% matches Yahoo |
| 2001 | Sapient Corp (`SAPE`) | −66% | 12 | **broken** | Adjustment glitch: +87% adjusted on 2000-08-29 while the traded price barely moved |
| 2001 | Fluor Corporation (`FLR`) | −64% | 14 | **broken** | On 2000-12-01 the series switches to the new Fluor spun off from Massey (73 -> 27, volume down tenfold): not a crash |
| 2002 | Raytheon Company (`RTN`) | −95% | 1 | **broken** | Adjusted price 372 -> 18.7 on 2001-05-14 while the traded price stayed at about $29.5 |
| 2002 | Providian Financial Corp (`PVN`) | −94% | 2 | **real** | Providian collapsed in 2001 (credit-card losses): about $58 -> $3.55 |
| 2003 | Electronic Data Systems (`EDS`) | −73% | 12 | **real** | Electronic Data Systems fell 53% on 2002-09-19 after an earnings warning |
| 2004 | Electronic Arts Inc (`EA`) | −76% | 1 | **broken** | EODHD's traded price is $775 before the November 2003 split and $46 after; Electronic Arts really rose in 2003 |
| 2004 | Time Warner Inc (`TWX`) | −54% | 2 | **broken** | Not a crash: price 47 -> 15.9 on 2003-10-16, the day AOL Time Warner became Time Warner (TWX), because the earlier prices are on a x3 split basis. Dates excluded in data/price_exclusions.csv |
| 2005 | Tektronix Inc (`TEK_old`) | −49% | 1 | **broken** | Frozen prices: the same close for 28 days in a row |
| 2006 | MBNA Corp (`KRB`) | −99% | 1 | **broken** | $25.3 -> $0.12 on 2005-07-29 with zero volume; MBNA traded normally until Bank of America bought it at the end of 2005 |
| 2006 | Tektronix Inc (`TEK_old`) | −39% | 9 | **broken** | Frozen prices: the same close for 37 days in a row |
| 2007 | First Data Corp (`FDC_old`) | −41% | 1 | **broken** | Not a crash: the Western Union spin-off (2006-09-29) is missing from the adjusted prices, a fake -44% day. Dates excluded in data/price_exclusions.csv |
| 2008 | E*TRADE Financial LLC (`ETFC`) | −84% | 1 | **real** | E*Trade fell 59% on 2007-11-12 on mortgage-related losses; -84% for the year |
| 2009 | American International Group Inc (`AIG`) | −97% | 1 | **real** | AIG's 2008 collapse and government rescue; -97% matches Yahoo |
| 2009 | XL Group Ltd (`XL_old`) | −93% | 2 | **real** | XL Capital fell about 93% in the 2008 financial crisis |
| 2009 | National City Corp (`NCC_old`) | −89% | 4 | **real** | National City collapsed in 2008 and was sold to PNC for about $2.23 a share |
| 2009 | Genworth Financial Inc (`GNW`) | −88% | 5 | **real** | Genworth's 2008 collapse; -88% matches Yahoo |
| 2009 | Wachovia Corp (`WB_old1`) | −85% | 9 | **real** | Wachovia fell 82% on 2008-09-29, when its sale to Citigroup was announced |
| 2009 | Schering Plough Corp (`SGP_old1`) | −81% | 12 | **broken** | $25.8 -> $2.50 on 2008-01-08 with near-zero volume, then frozen for 62 days |
| 2010 | Time Warner Cable Inc (`TWC`) | −74% | 1 | **broken** | The traded price is steady around $25 while the adjusted price falls 63% on 2009-03-13: Time Warner Cable's special dividend and reverse split are mishandled |
| 2011 | R. R. Donnelley & Sons Company (`RRD`) | −72% | 1 | **broken** | Traded price 17.5 -> 5.7 overnight on 2010-12-20 with no event; EODHD's RRD prices are known to be off by large factors |
| 2012 | Cablevision Systems Corp (`CVC`) | −57% | 6 | **broken** | Not a crash: the AMC Networks spin-off (2011-06-30) is missing from the adjusted prices, a fake -28% day. Dates excluded in data/price_exclusions.csv |
| 2014 | Noble Energy Inc (`NBL`) | −33% | 2 | **broken** | Price 236 -> 59 on 2013-05-29, a 2-for-1 split mishandled; Noble Energy rose in 2013 |
| 2021 | Occidental Petroleum Corporation (`OXY`) | −57% | 2 | **real** | Occidental fell 52% on 2020-03-09 in the oil price crash; -57% for the year matches Yahoo |
| 2021 | APA Corporation (`APA`) | −44% | 12 | **real** | Apache fell 54% on 2020-03-09 in the oil price crash; -44% for the year matches Yahoo |

Williams (2002, −89% on Yahoo) is missing from this list: its prices are excluded from July 2002, so it can't be ranked for 2003 at all (below).

## What the review found

| Problem | Effect | Fix |
|---|---|---|
| **First Data, 2006:** the Western Union spin-off is missing from EODHD's adjusted prices, a fake −44% day | It ranked #1 for 2007 on a loss that didn't happen | Three weeks after the spin-off excluded, so it can't be ranked on it and a holder exits at the pre-spin-off price |
| **Cablevision, 2011:** the AMC Networks spin-off is missing, a fake −28% day | #6 for 2012; its real 2011 loss (about −32% with the AMC shares) wouldn't make the worst 10 | Same fix |
| **American Capital, 2009:** EODHD records a $1.07 dividend in June 2009, a third of the share price; the company paid none that year | +3.6 points of fake return for the worst 10 in 2009 | Three weeks excluded; the strategy sells it at the last correct price |
| **Williams, 2002:** bogus $0.56 dividends from 30 July 2002 (the real dividend was $0.01) | The known 2003–05 problem starts earlier | Exclusion moved back to July 2002. Williams can't be ranked for 2003, though it really was one of 2002's worst stocks and **rose 251% in 2003** (Yahoo): the 2003 result misses a big winner |
| **Time Warner, 2003:** prices before 16 October 2003 are on a ×3 split basis, a fake −66% day | Hit the worst 50 while held | Three weeks excluded |
| **Teradata, 2014:** EODHD's adjusted prices count two dividends Teradata never paid (+8.7 points over the year) | About +0.9 points for the worst 10 in 2014 | Left in and noted: excluding dates can't remove a level shift, and excluding its history would remove it from other strategies |
| **DDR, 2009:** adjusted +96% against traded +63% | Mostly real: 2009 dividends, partly paid in shares. One adjustment may be a few points too generous (about 0.3 points for the worst 10) | Left in |

**How the spin-off screen worked.** Yahoo's adjusted prices usually don't allow for spin-offs either, so "matches Yahoo" doesn't rule one out. All 270 picks were screened twice:
- by name, for large spin-offs in the year before purchase. Merck's 2003 Medco spin-off is correctly adjusted; Noble's 2014 Paragon spin-off doesn't change its rank; Sears' Orchard Supply spin-off came after the formation date;
- by data, for big one-day drops on ordinary volume. A spin-off drops on normal volume; a news crash comes with a volume surge. 13 picks had a drop of 15% or more on less than twice the usual volume: only First Data was a spin-off. The others were market sell-offs (March 2001, 10 February 2009, OPEC's November 2014 decision, March 2020) and earnings warnings.

Every pick's holding-year adjusted return was also compared with its traded return: only American Capital and DDR differ by more than 10%.

## How the data ended for picks
Data ends during the holding year for 10 picks. The engine sells them at their last price, flagged "data ended, real outcome unknown" (CLAUDE.md rule 5). For eight that is close to the truth, because they were taken over or merged: Case (1999), Mercury Interactive (2006), Dell (2013), Envision (2018), SCANA (2018), Newfield (2019), Citrix (2022) and Walgreens (2025). Harnischfeger (1999) was already nearly worthless. The exception is **SVB (2023)**: sold at its last price (−53%) while shareholders lost nearly everything, which flatters 2023 by about 4 points.

The app also shows a floor, counting every such holding as worthless: 0.3% a year instead of 5.1%. It is far too pessimistic, because most data endings were takeovers that paid holders about the last price.

## Every pick, 1999–2025

| Year bought | Rank | Ticker | EODHD code | Company | Return the year before | Return while held | Check |
|---|---|---|---|---|---|---|---|
| 1999 | 1 | HPH | `HPH_old` | Harnischfeger Industries Inc | −71% | −97% | hand-checked: Harnischfeger went bankrupt in June 1999; data ends in December |
| 1999 | 2 | IKN | `IKN` | IKON OFFICE SOLUTIONS INC | −70% | −26% | hand-checked: adjusted and traded returns agree; holding year not independently confirmed |
| 1999 | 3 | FL | `FL` | Foot Locker Inc | −68% | +3% | hand-checked: consistent with company history |
| 1999 | 4 | RDC | `RDC` | Rowan Companies plc | −68% | +92% | hand-checked: consistent with company history |
| 1999 | 5 | CSE | `CSE1` | Case Corp | −64% | +141% | hand-checked: bought by New Holland in November 1999; data ends at the takeover |
| 1999 | 6 | UPR | `UPR` | Union Pacific Resources Group Inc | −63% | +35% | hand-checked: consistent with company history |
| 1999 | 7 | PRD | `PRD` | Polaroid Corp | −62% | +1% | hand-checked: consistent with company history |
| 1999 | 8 | TMO | `TMO` | Thermo Fisher Scientific Inc | −62% | −10% | matches Yahoo |
| 1999 | 9 | BIG | `BIG` | Big Lots Inc | −54% | −27% | hand-checked: consistent with company history |
| 1999 | 10 | PSFT | `PSFT_old` | PeopleSoft Inc | −51% | +7% | hand-checked: consistent with company history |
| 2000 | 1 | SCI | `SCI` | Service Corporation International | −81% | −78% | matches Yahoo |
| 2000 | 2 | RAD | `RAD` | Rite Aid Corporation | −77% | −78% | hand-checked: consistent with company history |
| 2000 | 3 | MCK | `MCK` | McKesson Corporation | −71% | +52% | matches Yahoo |
| 2000 | 4 | EHC | `EHC` | Encompass Health Corp | −65% | +194% | matches Yahoo |
| 2000 | 5 | QTRN | `QTRN` | Quintiles Transnational Corp | −65% | +12% | hand-checked: consistent with company history |
| 2000 | 6 | WM | `WM` | Waste Management Inc | −63% | +55% | matches Yahoo |
| 2000 | 7 | AW | `AW` | Allied Waste Industries Inc | −63% | +69% | hand-checked: consistent with company history |
| 2000 | 8 | XRX | `XRX` | Xerox Corp | −61% | −78% | matches Yahoo |
| 2000 | 9 | PGR | `PGR` | Progressive Corp | −57% | +41% | matches Yahoo |
| 2000 | 10 | ODP | `ODP` | ODP Corp | −55% | −31% | hand-checked: consistent with company history |
| 2001 | 1 | NOVL | `NOVL` | Novell Inc | −87% | −4% | hand-checked: consistent with company history |
| 2001 | 2 | AABA | `AABA` | Altaba Inc | −86% | −34% | hand-checked: consistent with company history |
| 2001 | 3 | BMC | `BMC` | Bmc Software Inc | −82% | +23% | hand-checked: consistent with company history |
| 2001 | 4 | XRX | `XRX` | Xerox Corp | −79% | +108% | matches Yahoo |
| 2001 | 5 | CNXT | `CNXT1` | Conexant Systems Inc | −77% | +18% | hand-checked: adjusted and traded returns agree; holding year not independently confirmed |
| 2001 | 6 | GTW | `GTW` | Gateway Inc | −75% | −51% | hand-checked: consistent with company history |
| 2001 | 7 | CCTYQ | `CCTYQ` | Circuit City Stores Inc | −74% | +123% | hand-checked: consistent with company history |
| 2001 | 8 | CA | `CA_old` | CA Technologies | −72% | +80% | hand-checked: consistent with company history |
| 2001 | 9 | GX | `GX` | Global Crossing Cayman Ltd | −71% | −94% | hand-checked: consistent with company history |
| 2001 | 10 | AAPL | `AAPL` | Apple Inc. | −71% | +57% | matches Yahoo |
| 2002 | 1 | PVN | `PVN` | Providian Financial Corp | −94% | +86% | hand-checked: consistent with company history |
| 2002 | 2 | PALM | `PALM` | PALM INC | −86% | −80% | hand-checked: consistent with company history |
| 2002 | 3 | AMCC | `AMCC` | Applied Micro Circuits Corp | −85% | −67% | hand-checked: consistent with company history |
| 2002 | 4 | GLW | `GLW` | Corning Incorporated | −83% | −59% | matches Yahoo |
| 2002 | 5 | CIEN | `CIEN` | Ciena Corp | −82% | −64% | matches Yahoo |
| 2002 | 6 | CMVT | `CMVT` | Comverse Technology Inc | −79% | −54% | hand-checked: consistent with company history |
| 2002 | 7 | VIAV | `VIAV` | Viavi Solutions Inc | −79% | −70% | matches Yahoo |
| 2002 | 8 | VTSS | `VTSS` | Vitesse Semiconductor Corp | −78% | −83% | hand-checked: consistent with company history |
| 2002 | 9 | NRTLQ | `NRTLQ` | Nortel Networks Corporation (USA) | −77% | −76% | hand-checked: consistent with company history |
| 2002 | 10 | TLAB | `TLAB` | Tellabs Inc | −74% | −50% | hand-checked: consistent with company history |
| 2003 | 1 | EP | `EP_old` | El Paso Corp. | −84% | +14% | hand-checked: consistent with company history |
| 2003 | 2 | NVDA | `NVDA` | NVIDIA Corporation | −83% | +88% | matches Yahoo |
| 2003 | 3 | AES | `AES` | The AES Corporation | −82% | +193% | matches Yahoo |
| 2003 | 4 | CPNLQ | `CPNLQ` | Calpine Corp | −81% | +26% | hand-checked: adjusted and traded returns agree; holding year not independently confirmed |
| 2003 | 5 | AV | `AV_old1` | Avaya Inc | −80% | +402% | hand-checked: consistent with company history |
| 2003 | 6 | SANM | `SANM` | Sanmina Corporation | −77% | +178% | matches Yahoo |
| 2003 | 7 | PKI | `RVTY` | Revvity Inc. | −76% | +104% | matches Yahoo |
| 2003 | 8 | JAVA | `JAVA_old` | Sun Microsystems Inc | −75% | +39% | hand-checked: consistent with company history |
| 2003 | 9 | PMCS | `PMCS` | PMC-Sierra Inc | −74% | +222% | hand-checked: consistent with company history |
| 2003 | 10 | MWW | `MWW` | Monster Worldwide Inc | −74% | +85% | hand-checked: consistent with company history |
| 2004 | 1 | WNDXQ | `WNDXQ` | Winn Dixie Stores Inc | −35% | −51% | hand-checked: consistent with company history |
| 2004 | 2 | EKDKQ | `EKDKQ` | Eastman Kodak Co | −27% | +28% | hand-checked: consistent with company history |
| 2004 | 3 | NWL | `NWL` | Newell Brands Inc | −22% | +10% | matches Yahoo |
| 2004 | 4 | KSS | `KSS` | Kohl's Corporation | −20% | +12% | matches Yahoo |
| 2004 | 5 | SGP | `SGP_old1` | Schering Plough Corp | −19% | +20% | hand-checked: consistent with company history |
| 2004 | 6 | Q | `Q_old` | Qwest Communications International Inc | −14% | +4% | hand-checked: consistent with company history |
| 2004 | 7 | KG | `KG_old` | King Pharmaceuticals Inc | −11% | −21% | hand-checked: consistent with company history |
| 2004 | 8 | MRK | `MRK` | Merck & Company Inc | −11% | −31% | matches Yahoo |
| 2004 | 9 | DTE | `DTE` | DTE Energy Company | −10% | +14% | matches Yahoo |
| 2004 | 10 | LMT | `LMT` | Lockheed Martin Corporation | −10% | +9% | matches Yahoo |
| 2005 | 1 | CIEN | `CIEN` | Ciena Corp | −49% | −8% | matches Yahoo |
| 2005 | 2 | PMCS | `PMCS` | PMC-Sierra Inc | −44% | −26% | hand-checked: consistent with company history |
| 2005 | 3 | CHIR | `CHIR1` | Chiron Corp | −42% | +35% | hand-checked: consistent with company history |
| 2005 | 4 | LSI | `LSI1` | Lsi Corp | −38% | +55% | hand-checked: consistent with company history |
| 2005 | 5 | DALRQ | `DALRQ` | Delta Air Lines Inc | −37% | −89% | hand-checked: consistent with company history |
| 2005 | 6 | NOVL | `NOVL` | Novell Inc | −36% | +34% | hand-checked: consistent with company history |
| 2005 | 7 | NVLS | `NVLS1` | Novellus Systems Inc | −34% | −10% | hand-checked: consistent with company history |
| 2005 | 8 | AW | `AW` | Allied Waste Industries Inc | −33% | −2% | hand-checked: consistent with company history |
| 2005 | 9 | TER | `TER` | Teradyne Inc | −33% | −11% | matches Yahoo |
| 2005 | 10 | SANM | `SANM` | Sanmina Corporation | −33% | −47% | matches Yahoo |
| 2006 | 1 | DCNAQ | `DCNAQ` | Dana Corp | −59% | −80% | hand-checked: consistent with company history |
| 2006 | 2 | GTW | `GTW` | Gateway Inc | −58% | −30% | hand-checked: consistent with company history |
| 2006 | 3 | MTLQQ | `GM_old` | General Motors Corp | −52% | +56% | hand-checked: consistent with company history |
| 2006 | 4 | SANM | `SANM` | Sanmina Corporation | −50% | −21% | matches Yahoo |
| 2006 | 5 | LXK | `LXK` | Lexmark International Inc | −47% | +60% | hand-checked: consistent with company history |
| 2006 | 6 | F | `F` | Ford Motor Company | −45% | −1% | matches Yahoo |
| 2006 | 7 | UIS | `UIS` | Unisys Corporation | −43% | +36% | matches Yahoo |
| 2006 | 8 | MERQ | `MERQ` | Mercury Interactive Corp | −39% | +86% | hand-checked: bought by Hewlett-Packard in November 2006; data ends at the takeover |
| 2006 | 9 | AMCC | `AMCC` | Applied Micro Circuits Corp | −39% | +35% | hand-checked: adjusted and traded returns agree; holding year not independently confirmed |
| 2006 | 10 | AV | `AV_old1` | Avaya Inc | −38% | +29% | hand-checked: consistent with company history |
| 2007 | 1 | APOL | `APOL` | Apollo Education Group Inc | −36% | +67% | hand-checked: consistent with company history |
| 2007 | 2 | WFM | `WFM` | Whole Foods Market Inc | −35% | −10% | hand-checked: consistent with company history |
| 2007 | 3 | ADCT | `ADCT_old` | ADC Telecommunications Inc | −35% | +2% | hand-checked: consistent with company history |
| 2007 | 4 | AABA | `AABA` | Altaba Inc | −35% | −7% | hand-checked: consistent with company history |
| 2007 | 5 | AMD | `AMD` | Advanced Micro Devices Inc | −33% | −63% | matches Yahoo |
| 2007 | 6 | JBL | `JBL` | Jabil Circuit Inc | −33% | −40% | matches Yahoo |
| 2007 | 7 | SNDK | `SNDK_old` | SanDisk Corp | −32% | −20% | hand-checked: consistent with company history |
| 2007 | 8 | EBAY | `EBAY` | eBay Inc | −30% | +8% | matches Yahoo |
| 2007 | 9 | BSX | `BSX` | Boston Scientific Corp | −30% | −33% | matches Yahoo |
| 2007 | 10 | NOVL | `NOVL` | Novell Inc | −30% | +8% | hand-checked: consistent with company history |
| 2008 | 1 | ETFC | `ETFC` | E*TRADE Financial LLC | −84% | −62% | hand-checked: consistent with company history |
| 2008 | 2 | CCTYQ | `CCTYQ` | Circuit City Stores Inc | −78% | −97% | hand-checked: consistent with company history |
| 2008 | 3 | MBI | `MBI` | MBIA Inc | −74% | −76% | matches Yahoo |
| 2008 | 4 | WAMUQ | `WAMUQ` | Washington Mutual Inc | −70% | −100% | hand-checked: consistent with company history |
| 2008 | 5 | PHM | `PHM` | PulteGroup Inc | −68% | +9% | matches Yahoo |
| 2008 | 6 | LEN | `LEN` | Lennar Corporation | −65% | −45% | matches Yahoo |
| 2008 | 7 | MTG | `MTG` | MGIC Investment Corp | −64% | −82% | matches Yahoo |
| 2008 | 8 | ODP | `ODP` | ODP Corp | −64% | −74% | hand-checked: consistent with company history |
| 2008 | 9 | AMD | `AMD` | Advanced Micro Devices Inc | −63% | −67% | matches Yahoo |
| 2008 | 10 | SLM | `SLM` | SLM Corp | −58% | −53% | matches Yahoo |
| 2009 | 1 | AIG | `AIG` | American International Group Inc | −97% | −12% | matches Yahoo |
| 2009 | 2 | XL | `XL_old` | XL Group Ltd | −93% | +381% | hand-checked: consistent with company history |
| 2009 | 3 | ACAS | `ACAS` | American Capital Ltd | −89% | −0% | bogus $1.07 dividend in June 2009 excluded (below): the strategy sells it in July at the last correct price |
| 2009 | 4 | NCC | `NCC_old` | National City Corp | −89% | not bought | taken over by PNC on 2008-12-31, the formation date: not bought, its share stays in cash |
| 2009 | 5 | GNW | `GNW` | Genworth Financial Inc | −88% | +321% | matches Yahoo |
| 2009 | 6 | MTLQQ | `GM_old` | General Motors Corp | −87% | −86% | hand-checked: consistent with company history |
| 2009 | 7 | DDR | `DDR` | DDR Corp | −86% | +96% | hand-checked: 2009 dividends, partly paid in shares, explain the gap to the traded price |
| 2009 | 8 | S | `S_old` | SPRINT Corp | −86% | +100% | hand-checked: consistent with company history |
| 2009 | 9 | WB | `WB_old1` | Wachovia Corp | −85% | not bought | taken over by Wells Fargo on 2008-12-31, the formation date: not bought, its share stays in cash |
| 2009 | 10 | SUNEQ | `WFR_old` | Sunedison Inc | −84% | −12% | hand-checked: consistent with company history |
| 2010 | 1 | HBAN | `HBAN` | Huntington Bancshares Incorporated | −52% | +95% | matches Yahoo |
| 2010 | 2 | C | `C` | Citigroup Inc. | −51% | +44% | matches Yahoo |
| 2010 | 3 | TMUS | `TMUS` | T-Mobile US Inc | −49% | +64% | matches Yahoo |
| 2010 | 4 | ZION | `ZION` | Zions Bancorporation | −47% | +89% | matches Yahoo |
| 2010 | 5 | SUN | `SUN1` | Sunoco Inc | −40% | +49% | hand-checked: consistent with company history |
| 2010 | 6 | EKDKQ | `EKDKQ` | Eastman Kodak Co | −36% | +31% | hand-checked: consistent with company history |
| 2010 | 7 | KEY | `KEY` | KeyCorp | −34% | +53% | matches Yahoo |
| 2010 | 8 | RF | `RF` | Regions Financial Corporation | −31% | +31% | matches Yahoo |
| 2010 | 9 | STI | `STI_old` | SunTrust Banks Inc | −31% | +48% | hand-checked: consistent with company history |
| 2010 | 10 | GENZ | `GENZ_old` | Genzyme Corp | −26% | +45% | hand-checked: consistent with company history |
| 2011 | 1 | DF | `DF` | Dean Foods Company | −51% | +23% | hand-checked: consistent with company history |
| 2011 | 2 | HRB | `HRB` | H&R Block Inc | −45% | +36% | matches Yahoo |
| 2011 | 3 | APOL | `APOL` | Apollo Education Group Inc | −35% | +33% | hand-checked: consistent with company history |
| 2011 | 4 | DO | `DO_old` | Diamond Offshore Drilling Inc | −32% | −14% | hand-checked: consistent with company history |
| 2011 | 5 | PHM | `PHM` | PulteGroup Inc | −25% | −16% | matches Yahoo |
| 2011 | 6 | SVU | `SVU` | SUPERVALU INC | −24% | −12% | hand-checked: adjusted and traded returns agree; holding year not independently confirmed |
| 2011 | 7 | MU | `MU` | Micron Technology Inc | −24% | −18% | matches Yahoo |
| 2011 | 8 | WDC | `WDC` | Western Digital Corporation | −23% | −9% | matches Yahoo |
| 2011 | 9 | AKS | `AKS` | AK Steel Holding Corporation | −22% | −48% | hand-checked: consistent with company history |
| 2011 | 10 | SWN | `SWN` | Southwestern Energy Company | −22% | −14% | hand-checked: consistent with company history |
| 2012 | 1 | FSLR | `FSLR` | First Solar Inc | −74% | −11% | matches Yahoo |
| 2012 | 2 | ANRZQ | `ANR` | Alpha Natural Resources Inc | −66% | −57% | hand-checked: consistent with company history |
| 2012 | 3 | NFLX | `NFLX` | Netflix Inc | −61% | +27% | matches Yahoo |
| 2012 | 4 | BAC | `BAC` | Bank of America Corp | −58% | +108% | matches Yahoo |
| 2012 | 5 | SHLD | `SHLD_old` | Sears Holdings | −57% | +33% | hand-checked: consistent with company history |
| 2012 | 6 | X | `X` | United States Steel Corporation | −54% | −7% | hand-checked: consistent with company history |
| 2012 | 7 | DXC | `DXC` | DXC Technology Co | −52% | +69% | matches Yahoo |
| 2012 | 8 | AIG | `AIG` | American International Group Inc | −51% | +52% | matches Yahoo |
| 2012 | 9 | HCBK | `HCBK` | Hudson City Bancorp Inc | −51% | +30% | hand-checked: consistent with company history |
| 2012 | 10 | ETFC | `ETFC` | E*TRADE Financial LLC | −50% | +8% | hand-checked: consistent with company history |
| 2013 | 1 | APOL | `APOL` | Apollo Education Group Inc | −61% | +27% | hand-checked: consistent with company history |
| 2013 | 2 | AMD | `AMD` | Advanced Micro Devices Inc | −56% | +56% | matches Yahoo |
| 2013 | 3 | BBY | `BBY` | Best Buy Co. Inc | −47% | +251% | matches Yahoo |
| 2013 | 4 | JCP | `JCP` | J. C. Penney Company Inc | −43% | −57% | hand-checked: consistent with company history |
| 2013 | 5 | HPQ | `HPQ` | HP Inc | −43% | +89% | matches Yahoo |
| 2013 | 6 | PBI | `PBI` | Pitney Bowes Inc | −36% | +130% | matches Yahoo |
| 2013 | 7 | CLF | `CLF` | Cleveland-Cliffs Inc | −35% | −32% | matches Yahoo |
| 2013 | 8 | ATI | `ATI` | Allegheny Technologies Incorporated | −35% | +14% | matches Yahoo |
| 2013 | 9 | DELL | `DELL_old` | Dell Inc | −31% | +31% | hand-checked: taken private in October 2013; data ends at the buyout |
| 2013 | 10 | EA | `EA` | Electronic Arts Inc | −30% | +57% | hand-checked: consistent with company history |
| 2014 | 1 | NEM | `NEM` | Newmont Goldcorp Corp | −49% | −19% | matches Yahoo |
| 2014 | 2 | CLF | `CLF` | Cleveland-Cliffs Inc | −30% | −72% | matches Yahoo |
| 2014 | 3 | EW | `EW` | Edwards Lifesciences Corp | −27% | +94% | matches Yahoo |
| 2014 | 4 | BTUUQ | `BTUUQ` | PEABODY ENERGY CORP | −27% | −60% | hand-checked: consistent with company history |
| 2014 | 5 | TDC | `TDC` | Teradata Corp | −26% | +7% | differs from Yahoo by 8.7 points: EODHD counts two dividends Teradata never paid. Left in (below) |
| 2014 | 6 | ISRG | `ISRG` | Intuitive Surgical Inc | −22% | +38% | matches Yahoo |
| 2014 | 7 | FE | `FE` | FirstEnergy Corporation | −17% | +27% | matches Yahoo |
| 2014 | 8 | DO | `DO_old` | Diamond Offshore Drilling Inc | −16% | −34% | hand-checked: consistent with company history |
| 2014 | 9 | HCP | `DOC` | Healthpeak Properties Inc | −16% | +31% | matches Yahoo |
| 2014 | 10 | MOS | `MOS` | The Mosaic Company | −15% | −1% | matches Yahoo |
| 2015 | 1 | RIG | `RIG` | Transocean Ltd | −60% | −27% | matches Yahoo |
| 2015 | 2 | NE | `NE_old` | Noble Corporation plc | −53% | −30% | hand-checked: consistent with company history |
| 2015 | 3 | DNR | `DNR` | Denbury Resources Inc | −50% | −73% | hand-checked: consistent with company history |
| 2015 | 4 | GNW | `GNW` | Genworth Financial Inc | −45% | −55% | matches Yahoo |
| 2015 | 5 | AVP | `AVP` | Avon Products Inc | −44% | −54% | hand-checked: consistent with company history |
| 2015 | 6 | ESV | `ESV` | Valaris plc | −44% | −46% | hand-checked: consistent with company history |
| 2015 | 7 | RRC | `RRC` | Range Resources Corp | −36% | −53% | matches Yahoo |
| 2015 | 8 | FCX | `FCX` | Freeport-McMoran Copper & Gold Inc | −36% | −71% | matches Yahoo |
| 2015 | 9 | DO | `DO_old` | Diamond Offshore Drilling Inc | −36% | −41% | hand-checked: consistent with company history |
| 2015 | 10 | QEP | `QEP` | QEP Resources Inc | −34% | −30% | hand-checked: consistent with company history |
| 2016 | 1 | CHK | `CHK_old` | Chesapeake Energy | −77% | +40% | hand-checked: consistent with company history |
| 2016 | 2 | CNX | `CNX` | CNX Resources Corp | −76% | +103% | matches Yahoo |
| 2016 | 3 | SWN | `SWN` | Southwestern Energy Company | −74% | +29% | hand-checked: adjusted and traded returns agree; holding year not independently confirmed |
| 2016 | 4 | FCX | `FCX` | Freeport-McMoran Copper & Gold Inc | −70% | +110% | matches Yahoo |
| 2016 | 5 | FOSL | `FOSL` | Fossil Group Inc | −67% | −23% | matches Yahoo |
| 2016 | 6 | KMI | `KMI` | Kinder Morgan Inc | −63% | +46% | matches Yahoo |
| 2016 | 7 | MU | `MU` | Micron Technology Inc | −60% | +57% | matches Yahoo |
| 2016 | 8 | NRG | `NRG` | NRG Energy Inc. | −55% | +9% | matches Yahoo |
| 2016 | 9 | MRO | `MRO` | Marathon Oil Corporation | −54% | +41% | hand-checked: consistent with company history |
| 2016 | 10 | MUR | `MUR` | Murphy Oil Corporation | −54% | +45% | matches Yahoo |
| 2017 | 1 | ENDP | `ENDP` | Endo International PLC | −73% | −54% | hand-checked: consistent with company history |
| 2017 | 2 | FSLR | `FSLR` | First Solar Inc | −51% | +110% | matches Yahoo |
| 2017 | 3 | TRIP | `TRIP` | TripAdvisor Inc | −46% | −27% | matches Yahoo |
| 2017 | 4 | PRGO | `PRGO` | Perrigo Company PLC | −42% | +5% | matches Yahoo |
| 2017 | 5 | VRTX | `VRTX` | Vertex Pharmaceuticals Inc | −41% | +104% | matches Yahoo |
| 2017 | 6 | SRCL | `SRCL` | Stericycle Inc | −36% | −10% | hand-checked: consistent with company history |
| 2017 | 7 | ALXN | `ALXN` | Alexion Pharmaceuticals Inc | −36% | +1% | hand-checked: consistent with company history |
| 2017 | 8 | ILMN | `ILMN` | Illumina Inc | −33% | +71% | matches Yahoo |
| 2017 | 9 | MNK | `MNK_old` | Muniholdings New York Insured Fund III Inc | −33% | −55% | hand-checked: consistent with company history |
| 2017 | 10 | AGN | `AGN` | Allergan plc | −33% | −20% | hand-checked: consistent with company history |
| 2018 | 1 | UAA | `UAA` | Under Armour Inc A | −50% | +18% | matches Yahoo |
| 2018 | 2 | RRC | `RRC` | Range Resources Corp | −50% | −44% | matches Yahoo |
| 2018 | 3 | UA | `UA` | Under Armour Inc C | −47% | +18% | matches Yahoo |
| 2018 | 4 | EVHC | `EVHC` | Envision Healthcare Holdings | −45% | +31% | hand-checked: taken private by KKR in October 2018; data ends at the buyout |
| 2018 | 5 | CHK | `CHK_old` | Chesapeake Energy | −44% | −47% | hand-checked: consistent with company history |
| 2018 | 6 | SCG | `SCG` | SCANA Corporation | −43% | +28% | hand-checked: merged into Dominion Energy (paid in shares) at the end of 2018 |
| 2018 | 7 | GE | `GE` | GE Aerospace | −43% | −54% | matches Yahoo |
| 2018 | 8 | MAT | `MAT` | Mattel Inc | −42% | −39% | matches Yahoo |
| 2018 | 9 | AAP | `AAP` | Advance Auto Parts Inc | −41% | +49% | matches Yahoo |
| 2018 | 10 | SIG | `SIG` | Signet Jewelers Ltd | −39% | −38% | matches Yahoo |
| 2019 | 1 | COTY | `COTY` | Coty Inc | −67% | +59% | matches Yahoo |
| 2019 | 2 | MHK | `MHK` | Mohawk Industries Inc | −58% | +14% | matches Yahoo |
| 2019 | 3 | GE | `GE` | GE Aerospace | −55% | +55% | matches Yahoo |
| 2019 | 4 | PRGO | `PRGO` | Perrigo Company PLC | −55% | +29% | matches Yahoo |
| 2019 | 5 | LB | `LB_old2` | L Brands Inc. | −54% | −30% | hand-checked: consistent with company history |
| 2019 | 6 | NFX | `NFX_old` | Newfield Exploration Company | −54% | +13% | hand-checked: bought by Encana (paid in shares) in February 2019 |
| 2019 | 7 | AMG | `AMG` | Affiliated Managers Group, Inc. | −52% | −13% | matches Yahoo |
| 2019 | 8 | IVZ | `IVZ` | Invesco Plc | −52% | +14% | matches Yahoo |
| 2019 | 9 | WDC | `WDC` | Western Digital Corporation | −52% | +78% | matches Yahoo |
| 2019 | 10 | XEC | `XEC` | Cimarex Energy Co | −49% | −16% | hand-checked: consistent with company history |
| 2020 | 1 | ABMD | `ABMD` | ABIOMED Inc | −48% | +88% | hand-checked: consistent with company history |
| 2020 | 2 | M | `M` | Macy’s Inc | −38% | −29% | matches Yahoo |
| 2020 | 3 | OXY | `OXY` | Occidental Petroleum Corporation | −28% | −58% | matches Yahoo |
| 2020 | 4 | GPS | `GPS` | Gap Inc | −28% | +17% | hand-checked: consistent with company history |
| 2020 | 5 | DXC | `DXC` | DXC Technology Co | −28% | −28% | matches Yahoo |
| 2020 | 6 | MYL | `VTRS` | Viatris Inc | −27% | −10% | matches Yahoo |
| 2020 | 7 | MOS | `MOS` | The Mosaic Company | −25% | +12% | matches Yahoo |
| 2020 | 8 | LB | `LB_old2` | L Brands Inc. | −25% | +129% | hand-checked: consistent with company history |
| 2020 | 9 | ADS | `ADS` | Alliance Data Systems Corporation | −23% | −35% | hand-checked: consistent with company history |
| 2020 | 10 | KHC | `KHC` | The Kraft Heinz Company | −21% | +14% | matches Yahoo |
| 2021 | 1 | CCL | `CCL` | Carnival Corporation | −57% | +5% | matches Yahoo |
| 2021 | 2 | OXY | `OXY` | Occidental Petroleum Corporation | −57% | +78% | matches Yahoo |
| 2021 | 3 | NCLH | `NCLH` | Norwegian Cruise Line Holdings Ltd | −56% | −7% | matches Yahoo |
| 2021 | 4 | FTI | `FTI` | TechnipFMC PLC | −55% | −13% | matches Yahoo |
| 2021 | 5 | UAL | `UAL` | United Airlines Holdings Inc | −51% | +9% | matches Yahoo |
| 2021 | 6 | MRO | `MRO` | Marathon Oil Corporation | −50% | +151% | hand-checked: consistent with company history |
| 2021 | 7 | HFC | `HFC` | HollyFrontier Corporation | −46% | +35% | hand-checked: consistent with company history |
| 2021 | 8 | FANG | `FANG` | Diamondback Energy Inc | −46% | +133% | matches Yahoo |
| 2021 | 9 | NOV | `NOV` | NOV Inc. | −45% | +4% | matches Yahoo |
| 2021 | 10 | AAL | `AAL` | American Airlines Group | −45% | +24% | matches Yahoo |
| 2022 | 1 | PENN | `PENN` | Penn National Gaming Inc | −40% | −42% | matches Yahoo |
| 2022 | 2 | GPN | `GPN` | Global Payments Inc | −37% | −29% | matches Yahoo |
| 2022 | 3 | LVS | `LVS` | Las Vegas Sands Corp | −37% | +27% | matches Yahoo |
| 2022 | 4 | ATVI | `ATVI` | Activision Blizzard Inc | −28% | +15% | hand-checked: consistent with company history |
| 2022 | 5 | MKTX | `MKTX` | MarketAxess Holdings Inc | −28% | −27% | matches Yahoo |
| 2022 | 6 | CTXS | `CTXS` | Citrix Systems Inc | −26% | +6% | hand-checked: taken private in September 2022; data ends at the buyout |
| 2022 | 7 | VTRS | `VTRS` | Viatris Inc | −26% | −17% | matches Yahoo |
| 2022 | 8 | WYNN | `WYNN` | Wynn Resorts Limited | −25% | −2% | matches Yahoo |
| 2022 | 9 | IPGP | `IPGP` | IPG Photonics Corporation | −23% | −44% | matches Yahoo |
| 2022 | 10 | FIS | `FIS` | Fidelity National Information Services Inc | −22% | −38% | matches Yahoo |
| 2023 | 1 | GNRC | `GNRC` | Generac Holdings Inc | −71% | +30% | matches Yahoo |
| 2023 | 2 | MTCH | `MTCH` | Match Group Inc | −69% | −11% | matches Yahoo |
| 2023 | 3 | ALGN | `ALGN` | Align Technology Inc | −68% | +27% | matches Yahoo |
| 2023 | 4 | SIVB | `SIVB` | SVB Financial Group | −66% | −53% | hand-checked: SVB failed on 10 March 2023. Sold at its last price (−53%), though shareholders lost nearly everything |
| 2023 | 5 | TSLA | `TSLA` | Tesla Inc | −65% | +130% | matches Yahoo |
| 2023 | 6 | CTLT | `CTLT` | Catalent Inc | −65% | −1% | hand-checked: consistent with company history |
| 2023 | 7 | META | `META` | Meta Platforms Inc. | −64% | +178% | matches Yahoo |
| 2023 | 8 | SBNY | `SBNY` | Signature Bank | −64% | −98% | hand-checked: Signature Bank failed in March 2023; its shares then traded for pennies |
| 2023 | 9 | PYPL | `PYPL` | PayPal Holdings Inc | −62% | −18% | matches Yahoo |
| 2023 | 10 | VFC | `VFC` | VF Corporation | −60% | −29% | matches Yahoo |
| 2024 | 1 | ENPH | `ENPH` | Enphase Energy Inc | −50% | −46% | matches Yahoo |
| 2024 | 2 | FMC | `FMC` | FMC Corporation | −48% | −22% | matches Yahoo |
| 2024 | 3 | MRNA | `MRNA` | Moderna Inc | −45% | −63% | matches Yahoo |
| 2024 | 4 | DG | `DG` | Dollar General Corporation | −44% | −45% | matches Yahoo |
| 2024 | 5 | PFE | `PFE` | Pfizer Inc | −41% | −5% | matches Yahoo |
| 2024 | 6 | EL | `EL` | Estee Lauder Companies Inc | −40% | −48% | matches Yahoo |
| 2024 | 7 | PAYC | `PAYC` | Paycom Software, Inc. | −33% | −1% | matches Yahoo |
| 2024 | 8 | ALB | `ALB` | Albemarle Corp | −33% | −41% | matches Yahoo |
| 2024 | 9 | ETSY | `ETSY` | Etsy, Inc. | −32% | −34% | matches Yahoo |
| 2024 | 10 | ILMN | `ILMN` | Illumina Inc | −31% | −2% | matches Yahoo |
| 2025 | 1 | WBA | `WBA` | Walgreens Boots Alliance Inc | −61% | +30% | hand-checked: taken private by Sycamore Partners in August 2025; data ends at the buyout |
| 2025 | 2 | INTC | `INTC` | Intel Corporation | −60% | +95% | matches Yahoo |
| 2025 | 3 | MRNA | `MRNA` | Moderna Inc | −58% | −27% | matches Yahoo |
| 2025 | 4 | CE | `CE` | Celanese Corporation | −55% | −38% | matches Yahoo |
| 2025 | 5 | ENPH | `ENPH` | Enphase Energy Inc | −48% | −53% | matches Yahoo |
| 2025 | 6 | EL | `EL` | Estee Lauder Companies Inc | −48% | +47% | matches Yahoo |
| 2025 | 7 | DLTR | `DLTR` | Dollar Tree Inc | −47% | +67% | matches Yahoo |
| 2025 | 8 | HUM | `HUM` | Humana Inc | −44% | +6% | matches Yahoo |
| 2025 | 9 | DG | `DG` | Dollar General Corporation | −43% | +86% | matches Yahoo |
| 2025 | 10 | BIIB | `BIIB` | Biogen Inc | −41% | +19% | matches Yahoo |
