# Top-10 pick review

**Result:** all 270 point-in-time top-10 picks for 1999–2025 were checked, 27 years × 10.
- **196 confirmed automatically:** formation-year and holding-year returns match Yahoo's dividend-adjusted prices within about 5%.
- **74 checked by hand:** Yahoo has no prices for them (mostly delisted companies). Each formation-year return was compared with the company's reported history.

The review found **five broken price histories and one wrong label**. All are now fixed or excluded, and none was fixed by editing a price.

**Updated in M5b (2026-10-26):** Ball Corp's own clean history replaced EODHD's broken `BLL` series, which puts Ball into 2003's top 10 at #6 (it matches Yahoo) and moves Sigma-Aldrich out. Renamed companies now use the code that carries on, so PerkinElmer (`RVTY`), Jacobs (`J`) and Facebook (`META`) are checked against Yahoo instead of by hand. Last year's top 10 returns 9.31% a year instead of 9.33%.

PLAN.md requires 1999–2012. Later years were cheap to check automatically, so they're included.

Reproduce: `python scripts/run_v1.py`, then `python scripts/review_top10.py` (writes `data/cache/top10_review.csv`).

## Method
1. **Stocks that still trade** (196 picks): EODHD's returns are compared with Yahoo's for the same years. A difference above 5% (in log terms) goes to review.
2. **Delisted stocks** (74 picks):
   - EODHD's adjusted return is shown next to the traded-price return (on the same split basis) and the data range.
   - Each formation-year return was compared with the company's reported price history.
   - The holding-year return was checked against what happened to the company (takeover, bankruptcy and so on).

## What the review found

| Pick | Problem | Fix |
|---|---|---|
| Williams (WMB), 2005 #5 | EODHD's dividend adjustments in 2003–05 are far too large: +105% adjusted against +66% traded (Yahoo also +66%). The real dividend was about $0.01 a quarter | Prices for 2003–05 excluded (`data/price_exclusions.csv`) |
| L Brands (LB), 2005 #4 | `LB_old2` before 2007 is a different, thinly traded instrument, giving +133% where the real figure was about +28% | Remapped: `LTD` for Sep 2003–Nov 2013 (checked against Yahoo's BBWI), `LB_old2` afterwards (matches Yahoo exactly), missing before Sep 2003 |
| Coastal (CGP), 2001 #7 | Coastal was bought by El Paso on 29 Jan 2001, but EODHD's `CGP` prices restart later as another instrument, running to 2022. The engine "held" the impostor | Prices after 29 Jan 2001 excluded. The engine also changed (below) |
| Hercules (HPC), 2007 | Bought by Ashland on 13 Nov 2008. After that the price is frozen at $30.02 with no volume, then becomes another instrument | Prices after the takeover excluded |
| Johnson Controls (JCI), 2017 #9 | 2016 was the Tyco merger and the Adient spin-off. EODHD's adjusted return (+64%) disagrees with its traded price (+38%) and Yahoo (+42%) | Prices for Sep–Dec 2016 excluded, so it isn't ranked for 2017 |
| Ball (`BLL`), 2003 | EODHD's `BLL` series applies Ball's 2002 split twice: the adjusted price doubles on the split day while the traded price doesn't move. The price checks set Ball aside, so it was never ranked for 2003, though its real 2002 return (+46%) made the top 10. Found in M5b, when momentum held Ball across the split | Remapped to `BALL`, the same company's history with clean adjustments (`data/ticker_map.csv`) |
| Mallinckrodt (`MNK_old`), 2015 #5 | EODHD's symbol list labels the code as a municipal bond fund | None needed: the prices start at Mallinckrodt's June 2013 spin-off and match its returns (+89% in 2014, −25% in 2015) |

**Engine change prompted by Coastal:** a held stock with no price for more than 10 trading days in a row is now sold at its last price, flagged "data ended, real outcome unknown". Before, the engine checked whether prices existed *later* to tell a gap from an ending. That was a small lookahead, and it let a series that restarts as another instrument be followed. The no-lookahead test now also covers prices vanishing.

**Why not tighten the automatic checks instead?** Lowering the "adjusted vs traded" threshold from 30% to 15% would have caught Williams. But it would also flag about 25 genuine spin-offs and special dividends (Hewlett-Packard/Agilent, Morgan Stanley/Discover, KLA's 2014 special dividend and others). For those, the adjusted return is correct and the traded-price return is the misleading one. Reviewing the picks themselves is more precise.

## Spot check: three years

Formation-year returns are the ranking (last year's return). Holding returns run from the January purchase to the next January's purchase.

- **2000:** last year's winners were the dot-com boom (Qualcomm, Nextel, Nortel, Oracle, Yahoo, Sun), and nearly all crashed in 2000. Momentum works until it doesn't.
- **2009:** after 2008, the "winners" were the few stocks that rose at all: defensive businesses like discount retail, tax preparation, drugs and Walmart. UST and Rohm & Haas were bought during 2009, so their holdings end with the takeover.
- **2021:** the pandemic winners, from Tesla's +743% down. Unlike 2000, most kept rising in 2021.

#### Bought January 2000 (ranked on 1999)

| Rank | Ticker | Company | Return in 1999 | Return while held | Check |
|---|---|---|---|---|---|
| 1 | QCOM | Qualcomm Incorporated | +2619% | -60% | matches Yahoo |
| 2 | NXTL | Nextel Communications Inc | +336% | -55% | hand-checked: consistent with company history |
| 3 | LSI | Lsi Corp | +319% | -48% | hand-checked: consistent with company history |
| 4 | NRTLQ | Nortel Networks Corporation (USA) | +304% | -40% | hand-checked: consistent with company history |
| 5 | ORCL | Oracle Corporation | +290% | -11% | matches Yahoo |
| 6 | NTAP | NetApp Inc | +270% | +21% | matches Yahoo |
| 7 | AABA | Altaba Inc | +265% | -88% | hand-checked: consistent with company history |
| 8 | JAVA | Sun Microsystems Inc | +262% | -33% | hand-checked: consistent with company history |
| 9 | NSM | National Semiconductor Corp | +217% | -55% | hand-checked: consistent with company history |
| 10 | TER | Teradyne Inc | +212% | -39% | matches Yahoo |

#### Bought January 2009 (ranked on 2008)

| Rank | Ticker | Company | Return in 2008 | Return while held | Check |
|---|---|---|---|---|---|
| 1 | FDO | Family Dollar Stores Inc | +36% | +5% | hand-checked: consistent with company history |
| 2 | UST | Ust Inc | +27% | +0% | hand-checked: consistent with company history |
| 3 | HRB | H&R Block Inc | +26% | +4% | matches Yahoo |
| 4 | AMGN | Amgen Inc | +24% | -2% | matches Yahoo |
| 5 | WMT | Walmart Inc. | +20% | -3% | matches Yahoo |
| 6 | CELG | Celgene Corporation | +20% | -1% | hand-checked: consistent with company history |
| 7 | ROH | ROHM & HAAS CO | +19% | +23% | hand-checked: consistent with company history |
| 8 | HAS | Hasbro Inc | +17% | +13% | matches Yahoo |
| 9 | AZO | AutoZone Inc | +16% | +12% | matches Yahoo |
| 10 | PSA | Public Storage | +12% | +10% | matches Yahoo |

#### Bought January 2021 (ranked on 2020)

| Rank | Ticker | Company | Return in 2020 | Return while held | Check |
|---|---|---|---|---|---|
| 1 | TSLA | Tesla Inc | +743% | +64% | matches Yahoo |
| 2 | ETSY | Etsy, Inc. | +302% | +22% | matches Yahoo |
| 3 | NVDA | NVIDIA Corporation | +122% | +130% | matches Yahoo |
| 4 | PYPL | PayPal Holdings Inc | +117% | -16% | matches Yahoo |
| 5 | LB | L Brands Inc. | +108% | +102% | hand-checked: consistent with company history |
| 6 | ALB | Albemarle Corp | +105% | +56% | matches Yahoo |
| 7 | AMD | Advanced Micro Devices Inc | +100% | +63% | matches Yahoo |
| 8 | FCX | Freeport-McMoran Copper & Gold Inc | +99% | +54% | matches Yahoo |
| 9 | CDNS | Cadence Design Systems Inc | +97% | +35% | matches Yahoo |
| 10 | NOW | ServiceNow Inc | +95% | +20% | matches Yahoo |

## Every pick, 1999–2025

| Year bought | Rank | Ticker | EODHD code | Company | Return the year before | Return while held | Check |
|---|---|---|---|---|---|---|---|
| 1999 | 1 | DELL | `DELL_old` | Dell Inc | +249% | +37% | hand-checked: consistent with company history |
| 1999 | 2 | AAPL | `AAPL` | Apple Inc. | +212% | +171% | matches Yahoo |
| 1999 | 3 | ASND | `ASND_old` | Ascend Communications Inc | +168% | +56% | hand-checked: consistent with company history |
| 1999 | 4 | CSCO | `CSCO` | Cisco Systems Inc | +150% | +127% | matches Yahoo |
| 1999 | 5 | UIS | `UIS` | Unisys Corporation | +148% | -8% | matches Yahoo |
| 1999 | 6 | NOVL | `NOVL` | Novell Inc | +144% | +109% | hand-checked: consistent with company history |
| 1999 | 7 | GPS | `GPS` | Gap Inc | +138% | +14% | hand-checked: consistent with company history |
| 1999 | 8 | LOW | `LOW` | Lowe's Companies Inc | +115% | +10% | matches Yahoo |
| 1999 | 9 | JAVA | `JAVA_old` | Sun Microsystems Inc | +115% | +240% | hand-checked: consistent with company history |
| 1999 | 10 | MSFT | `MSFT` | Microsoft Corporation | +115% | +65% | matches Yahoo |
| 2000 | 1 | QCOM | `QCOM` | Qualcomm Incorporated | +2619% | -60% | matches Yahoo |
| 2000 | 2 | NXTL | `NXTL` | Nextel Communications Inc | +336% | -55% | hand-checked: consistent with company history |
| 2000 | 3 | LSI | `LSI1` | Lsi Corp | +319% | -48% | hand-checked: consistent with company history |
| 2000 | 4 | NRTLQ | `NRTLQ` | Nortel Networks Corporation (USA) | +304% | -40% | hand-checked: consistent with company history |
| 2000 | 5 | ORCL | `ORCL` | Oracle Corporation | +290% | -11% | matches Yahoo |
| 2000 | 6 | NTAP | `NTAP` | NetApp Inc | +270% | +21% | matches Yahoo |
| 2000 | 7 | AABA | `AABA` | Altaba Inc | +265% | -88% | hand-checked: consistent with company history |
| 2000 | 8 | JAVA | `JAVA_old` | Sun Microsystems Inc | +262% | -33% | hand-checked: consistent with company history |
| 2000 | 9 | NSM | `NSM_old` | National Semiconductor Corp | +217% | -55% | hand-checked: consistent with company history |
| 2000 | 10 | TER | `TER` | Teradyne Inc | +212% | -39% | matches Yahoo |
| 2001 | 1 | RBK | `RBK` | Reebok International Ltd | +234% | +4% | hand-checked: consistent with company history |
| 2001 | 2 | EOG | `EOG` | EOG Resources Inc | +213% | -29% | matches Yahoo |
| 2001 | 3 | EHC | `EHC` | Encompass Health Corp | +203% | -3% | matches Yahoo |
| 2001 | 4 | CB | `CB` | Chubb Ltd | +159% | -3% | matches Yahoo |
| 2001 | 5 | KMI | `KMI1` | Kinder Morgan Inc | +159% | +14% | hand-checked: consistent with company history |
| 2001 | 6 | PKI | `RVTY` | PerkinElmer Inc | +154% | -27% | matches Yahoo |
| 2001 | 7 | CGP | `CGP` | Coastal Corp | +150% | -8% | hand-checked; prices after the 29 Jan 2001 takeover by El Paso are excluded (a different instrument), so the holding exits then |
| 2001 | 8 | UNH | `UNH` | UnitedHealth Group Incorporated | +131% | +20% | matches Yahoo |
| 2001 | 9 | FRX | `FRX_old` | Forest Laboratories Inc | +116% | +25% | hand-checked: consistent with company history |
| 2001 | 10 | APC | `APC_old` | Anadarko Petroleum Corp | +110% | -20% | hand-checked: consistent with company history |
| 2002 | 1 | NVDA | `NVDA` | NVIDIA Corporation | +308% | -82% | matches Yahoo |
| 2002 | 2 | ODP | `ODP` | ODP Corp | +160% | -14% | hand-checked: consistent with company history |
| 2002 | 3 | JCP | `JCP` | J. C. Penney Company Inc | +155% | -8% | hand-checked: consistent with company history |
| 2002 | 4 | BBY | `BBY` | Best Buy Co. Inc | +152% | -48% | matches Yahoo |
| 2002 | 5 | AZO | `AZO` | AutoZone Inc | +152% | +5% | matches Yahoo |
| 2002 | 6 | XRX | `XRX` | Xerox Corp | +130% | -22% | matches Yahoo |
| 2002 | 7 | CCTYQ | `CCTYQ` | Circuit City Stores Inc | +126% | -71% | hand-checked: consistent with company history |
| 2002 | 8 | HRB | `HRB` | H&R Block Inc | +120% | -4% | matches Yahoo |
| 2002 | 9 | LOW | `LOW` | Lowe's Companies Inc | +109% | -13% | matches Yahoo |
| 2002 | 10 | CAR | `CAR` | Avis Budget Group Inc | +104% | -44% | matches Yahoo |
| 2003 | 1 | PVN | `PVN` | Providian Financial Corp | +83% | +73% | hand-checked: consistent with company history |
| 2003 | 2 | BSX | `BSX` | Boston Scientific Corp | +76% | +69% | matches Yahoo |
| 2003 | 3 | NEM | `NEM` | Newmont Goldcorp Corp | +53% | +65% | matches Yahoo |
| 2003 | 4 | HAL | `HAL` | Halliburton Company | +47% | +39% | matches Yahoo |
| 2003 | 5 | APOL | `APOL` | Apollo Education Group Inc | +47% | +53% | hand-checked: consistent with company history |
| 2003 | 6 | BLL | `BALL` | Ball Corp | +46% | +12% | matches Yahoo |
| 2003 | 7 | ZBH | `ZBH` | Zimmer Biomet Holdings Inc | +36% | +74% | matches Yahoo |
| 2003 | 8 | BIG | `BIG` | Big Lots Inc | +27% | +2% | hand-checked: consistent with company history |
| 2003 | 9 | ANTM | `ANTM` | Anthem Inc | +27% | +20% | hand-checked: consistent with company history |
| 2003 | 10 | PFG | `PFG` | Principal Financial Group Inc | +27% | +9% | matches Yahoo |
| 2004 | 1 | AV | `AV_old1` | Avaya Inc | +428% | +32% | hand-checked: consistent with company history |
| 2004 | 2 | PMCS | `PMCS` | PMC-Sierra Inc | +262% | -45% | hand-checked: consistent with company history |
| 2004 | 3 | NOVL | `NOVL` | Novell Inc | +215% | -38% | hand-checked: consistent with company history |
| 2004 | 4 | GLW | `GLW` | Corning Incorporated | +215% | +14% | matches Yahoo |
| 2004 | 5 | AES | `AES` | The AES Corporation | +213% | +43% | matches Yahoo |
| 2004 | 6 | SANM | `SANM` | Sanmina Corporation | +181% | -35% | matches Yahoo |
| 2004 | 7 | AABA | `AABA` | Altaba Inc | +175% | +68% | hand-checked: consistent with company history |
| 2004 | 8 | NSM | `NSM_old` | National Semiconductor Corp | +163% | -10% | hand-checked: consistent with company history |
| 2004 | 9 | FCX | `FCX` | Freeport-McMoran Copper & Gold Inc | +154% | -9% | matches Yahoo |
| 2004 | 10 | NXTL | `NXTL` | Nextel Communications Inc | +143% | +8% | hand-checked: consistent with company history |
| 2005 | 1 | ADSK | `ADSK` | Autodesk Inc | +209% | +14% | matches Yahoo |
| 2005 | 2 | AAPL | `AAPL` | Apple Inc. | +201% | +136% | matches Yahoo |
| 2005 | 3 | TXU | `TXU` | Txu Corp | +172% | +63% | hand-checked: consistent with company history |
| 2005 | 4 | VLO | `VLO` | Valero Energy Corporation | +98% | +154% | matches Yahoo |
| 2005 | 5 | MON | `MON_old` | Monsanto | +93% | +46% | hand-checked: consistent with company history |
| 2005 | 6 | NUE | `NUE` | Nucor Corp | +89% | +41% | matches Yahoo |
| 2005 | 7 | SBUX | `SBUX` | Starbucks Corporation | +88% | +1% | matches Yahoo |
| 2005 | 8 | GT | `GT` | Goodyear Tire & Rubber Co | +87% | +20% | matches Yahoo |
| 2005 | 9 | AET | `AET` | Aetna Inc | +85% | +53% | hand-checked: consistent with company history |
| 2005 | 10 | BIIB | `BIIB` | Biogen Inc | +81% | -29% | matches Yahoo |
| 2006 | 1 | VLO | `VLO` | Valero Energy Corporation | +128% | -7% | matches Yahoo |
| 2006 | 2 | AAPL | `AAPL` | Apple Inc. | +123% | +12% | matches Yahoo |
| 2006 | 3 | ESRX | `ESRX` | Express Scripts Holding Co | +119% | -19% | hand-checked: consistent with company history |
| 2006 | 4 | EOG | `EOG` | EOG Resources Inc | +106% | -23% | matches Yahoo |
| 2006 | 5 | BR | `BR_old` | Burlington Resources Inc | +98% | +5% | hand-checked: consistent with company history |
| 2006 | 6 | SUN | `SUN1` | Sunoco Inc | +92% | -28% | hand-checked: consistent with company history |
| 2006 | 7 | HUM | `HUM` | Humana Inc | +83% | +0% | matches Yahoo |
| 2006 | 8 | ODP | `ODP` | ODP Corp | +81% | +19% | hand-checked: consistent with company history |
| 2006 | 9 | NOV | `NOV` | NOV Inc. | +78% | -14% | matches Yahoo |
| 2006 | 10 | MRO | `MRO` | Marathon Oil Corporation | +69% | +38% | hand-checked: consistent with company history |
| 2007 | 1 | ATI | `ATI` | Allegheny Technologies Incorporated | +153% | -4% | matches Yahoo |
| 2007 | 2 | TEX | `TEX` | Terex Corporation | +117% | +6% | matches Yahoo |
| 2007 | 3 | NVDA | `NVDA` | NVIDIA Corporation | +102% | +37% | matches Yahoo |
| 2007 | 4 | OMX | `OMX` | OFFICEMAX INC | +98% | -59% | hand-checked: consistent with company history |
| 2007 | 5 | BIG | `BIG` | Big Lots Inc | +91% | -32% | hand-checked: consistent with company history |
| 2007 | 6 | CELG | `CELG` | Celgene Corporation | +78% | -19% | hand-checked: consistent with company history |
| 2007 | 7 | DTV | `DTV_old` | DirecTV | +77% | -10% | hand-checked: consistent with company history |
| 2007 | 8 | PD | `PD_old` | Phelps Dodge Corp | +75% | +11% | hand-checked: consistent with company history |
| 2007 | 9 | BLS | `BLS` | Bellsouth Corp | +74% |  | hand-checked; BellSouth was taken over by AT&T on 29 Dec 2006, so there is no price at entry and that tenth stays cash |
| 2007 | 10 | HPC | `HPC` | HERCULES INC | +71% | -1% | hand-checked: consistent with company history |
| 2008 | 1 | NOV | `NOV` | NOV Inc. | +140% | -64% | matches Yahoo |
| 2008 | 2 | AMZN | `AMZN` | Amazon.com Inc | +135% | -44% | matches Yahoo |
| 2008 | 3 | JEC | `J` | Jacobs Engineering Group Inc | +135% | -48% | matches Yahoo |
| 2008 | 4 | AAPL | `AAPL` | Apple Inc. | +133% | -53% | matches Yahoo |
| 2008 | 5 | SUNEQ | `WFR_old` | Sunedison Inc | +126% | -82% | hand-checked: consistent with company history |
| 2008 | 6 | GME | `GME` | GameStop Corp. | +125% | -62% | matches Yahoo |
| 2008 | 7 | CNX | `CNX` | CNX Resources Corp | +124% | -55% | matches Yahoo |
| 2008 | 8 | CMI | `CMI` | Cummins Inc | +117% | -52% | matches Yahoo |
| 2008 | 9 | MON | `MON_old` | Monsanto | +113% | -34% | hand-checked: consistent with company history |
| 2008 | 10 | HES | `HES` | Hess Corporation | +105% | -42% | hand-checked: consistent with company history |
| 2009 | 1 | FDO | `FDO` | Family Dollar Stores Inc | +36% | +5% | hand-checked: consistent with company history |
| 2009 | 2 | UST | `UST_old` | Ust Inc | +27% | +0% | hand-checked: consistent with company history |
| 2009 | 3 | HRB | `HRB` | H&R Block Inc | +26% | +4% | matches Yahoo |
| 2009 | 4 | AMGN | `AMGN` | Amgen Inc | +24% | -2% | matches Yahoo |
| 2009 | 5 | WMT | `WMT` | Walmart Inc. | +20% | -3% | matches Yahoo |
| 2009 | 6 | CELG | `CELG` | Celgene Corporation | +20% | -1% | hand-checked: consistent with company history |
| 2009 | 7 | ROH | `ROH` | ROHM & HAAS CO | +19% | +23% | hand-checked: consistent with company history |
| 2009 | 8 | HAS | `HAS` | Hasbro Inc | +17% | +13% | matches Yahoo |
| 2009 | 9 | AZO | `AZO` | AutoZone Inc | +16% | +12% | matches Yahoo |
| 2009 | 10 | PSA | `PSA` | Public Storage | +12% | +10% | matches Yahoo |
| 2010 | 1 | XL | `XL_old` | XL Group Ltd | +395% | +18% | hand-checked: consistent with company history |
| 2010 | 2 | THC | `THC` | Tenet Healthcare Corporation | +369% | +25% | matches Yahoo |
| 2010 | 3 | AMD | `AMD` | Advanced Micro Devices Inc | +348% | -13% | matches Yahoo |
| 2010 | 4 | F | `F` | Ford Motor Company | +337% | +68% | matches Yahoo |
| 2010 | 5 | GNW | `GNW` | Genworth Financial Inc | +301% | +12% | matches Yahoo |
| 2010 | 6 | MU | `MU` | Micron Technology Inc | +300% | -24% | matches Yahoo |
| 2010 | 7 | WDC | `WDC` | Western Digital Corporation | +286% | -25% | matches Yahoo |
| 2010 | 8 | FCX | `FCX` | Freeport-McMoran Copper & Gold Inc | +229% | +46% | matches Yahoo |
| 2010 | 9 | WYND | `TNL` | Travel + Leisure Co | +214% | +54% | matches Yahoo |
| 2010 | 10 | CBRE | `CBRE` | CBRE Group Inc Class A | +214% | +52% | matches Yahoo |
| 2011 | 1 | NFLX | `NFLX` | Netflix Inc | +219% | -60% | matches Yahoo |
| 2011 | 2 | FFIV | `FFIV` | F5 Networks Inc | +146% | -21% | matches Yahoo |
| 2011 | 3 | CMI | `CMI` | Cummins Inc | +143% | -17% | matches Yahoo |
| 2011 | 4 | WYNN | `WYNN` | Wynn Resorts Limited | +94% | +10% | matches Yahoo |
| 2011 | 5 | AIG | `AIG` | American International Group Inc | +92% | -50% | matches Yahoo |
| 2011 | 6 | HBAN | `HBAN` | Huntington Bancshares Incorporated | +89% | -19% | matches Yahoo |
| 2011 | 7 | ZION | `ZION` | Zions Bancorporation | +89% | -33% | matches Yahoo |
| 2011 | 8 | AKAM | `AKAM` | Akamai Technologies Inc | +86% | -32% | matches Yahoo |
| 2011 | 9 | WFM | `WFM` | Whole Foods Market Inc | +84% | +39% | hand-checked: consistent with company history |
| 2011 | 10 | BKNG | `BKNG` | Booking Holdings Inc | +83% | +17% | matches Yahoo |
| 2012 | 1 | COG | `COG` | Cabot Oil & Gas Corporation | +101% | +28% | hand-checked: consistent with company history |
| 2012 | 2 | EP | `EP_old` | El Paso Corp. | +93% | +8% | hand-checked: consistent with company history |
| 2012 | 3 | ISRG | `ISRG` | Intuitive Surgical Inc | +80% | +5% | matches Yahoo |
| 2012 | 4 | MA | `MA` | Mastercard Inc | +67% | +39% | matches Yahoo |
| 2012 | 5 | BIIB | `BIIB` | Biogen Inc | +64% | +32% | matches Yahoo |
| 2012 | 6 | HUM | `HUM` | Humana Inc | +62% | -21% | matches Yahoo |
| 2012 | 7 | OKE | `OKE` | ONEOK Inc | +61% | +4% | matches Yahoo |
| 2012 | 8 | CMG | `CMG` | Chipotle Mexican Grill Inc | +59% | -12% | matches Yahoo |
| 2012 | 9 | PRGO | `PRGO` | Perrigo Company PLC | +54% | +9% | matches Yahoo |
| 2012 | 10 | ROST | `ROST` | Ross Stores Inc | +52% | +16% | matches Yahoo |
| 2013 | 1 | PHM | `PHM` | PulteGroup Inc | +188% | +9% | matches Yahoo |
| 2013 | 2 | S | `S_old` | SPRINT Corp | +142% | +80% | hand-checked: consistent with company history |
| 2013 | 3 | WHR | `WHR` | Whirlpool Corporation | +120% | +48% | matches Yahoo |
| 2013 | 4 | EXPE | `EXPE` | Expedia Group Inc. | +116% | +10% | matches Yahoo |
| 2013 | 5 | BAC | `BAC` | Bank of America Corp | +110% | +34% | matches Yahoo |
| 2013 | 6 | LEN | `LEN` | Lennar Corporation | +98% | -1% | matches Yahoo |
| 2013 | 7 | STX | `STX` | Seagate Technology PLC | +95% | +78% | matches Yahoo |
| 2013 | 8 | LYB | `LYB` | LyondellBasell Industries NV | +94% | +37% | matches Yahoo |
| 2013 | 9 | MPC | `MPC` | Marathon Petroleum Corp | +94% | +43% | matches Yahoo |
| 2013 | 10 | ANDV | `ANDV` | Andeavor | +90% | +30% | hand-checked: consistent with company history |
| 2014 | 1 | NFLX | `NFLX` | Netflix Inc | +298% | -4% | matches Yahoo |
| 2014 | 2 | BBY | `BBY` | Best Buy Co. Inc | +244% | -2% | matches Yahoo |
| 2014 | 3 | MU | `MU` | Micron Technology Inc | +243% | +60% | matches Yahoo |
| 2014 | 4 | DAL | `DAL` | Delta Air Lines Inc | +133% | +79% | matches Yahoo |
| 2014 | 5 | PBI | `PBI` | Pitney Bowes Inc | +132% | +7% | matches Yahoo |
| 2014 | 6 | ETFC | `ETFC` | E*TRADE Financial LLC | +119% | +21% | hand-checked: consistent with company history |
| 2014 | 7 | CELG | `CELG` | Celgene Corporation | +115% | +32% | hand-checked: consistent with company history |
| 2014 | 8 | BSX | `BSX` | Boston Scientific Corp | +110% | +11% | matches Yahoo |
| 2014 | 9 | GNW | `GNW` | Genworth Financial Inc | +107% | -46% | matches Yahoo |
| 2014 | 10 | FB | `META` | Facebook Inc | +105% | +43% | matches Yahoo |
| 2015 | 1 | LUV | `LUV` | Southwest Airlines Company | +126% | -1% | matches Yahoo |
| 2015 | 2 | EA | `EA` | Electronic Arts Inc | +105% | +41% | hand-checked: consistent with company history |
| 2015 | 3 | EW | `EW` | Edwards Lifesciences Corp | +94% | +23% | matches Yahoo |
| 2015 | 4 | AVGO | `AVGO` | Broadcom Inc | +93% | +44% | matches Yahoo |
| 2015 | 5 | MNK | `MNK_old` | Muniholdings New York Insured Fund III Inc | +89% | -25% | hand-checked; EODHD's list labels this code as a bond fund, but its prices start at Mallinckrodt's June 2013 spin-off and match Mallinckrodt's returns |
| 2015 | 6 | DAL | `DAL` | Delta Air Lines Inc | +81% | -0% | matches Yahoo |
| 2015 | 7 | RCL | `RCL` | Royal Caribbean Cruises Ltd | +77% | +20% | matches Yahoo |
| 2015 | 8 | GMCR | `GMCR` | Green Mountain Coffee Roasters Inc | +77% | -31% | hand-checked: consistent with company history |
| 2015 | 9 | KR | `KR` | Kroger Company | +65% | +31% | matches Yahoo |
| 2015 | 10 | MU | `MU` | Micron Technology Inc | +61% | -59% | matches Yahoo |
| 2016 | 1 | NFLX | `NFLX` | Netflix Inc | +134% | +16% | matches Yahoo |
| 2016 | 2 | AMZN | `AMZN` | Amazon.com Inc | +118% | +18% | matches Yahoo |
| 2016 | 3 | ATVI | `ATVI` | Activision Blizzard Inc | +94% | -2% | hand-checked: consistent with company history |
| 2016 | 4 | NVDA | `NVDA` | NVIDIA Corporation | +67% | +218% | matches Yahoo |
| 2016 | 5 | CVC | `CVC` | Cablevision Systems Corp | +58% | +10% | hand-checked: consistent with company history |
| 2016 | 6 | HRL | `HRL` | Hormel Foods Corporation | +54% | -8% | matches Yahoo |
| 2016 | 7 | VRSN | `VRSN` | VeriSign Inc | +53% | -8% | matches Yahoo |
| 2016 | 8 | RAI | `RAI` | Reynolds American Inc | +49% | +29% | hand-checked: consistent with company history |
| 2016 | 9 | SBUX | `SBUX` | Starbucks Corporation | +48% | -4% | matches Yahoo |
| 2016 | 10 | FSLR | `FSLR` | First Solar Inc | +48% | -50% | matches Yahoo |
| 2017 | 1 | NVDA | `NVDA` | NVIDIA Corporation | +227% | +96% | matches Yahoo |
| 2017 | 2 | OKE | `OKE` | ONEOK Inc | +150% | -2% | matches Yahoo |
| 2017 | 3 | FCX | `FCX` | Freeport-McMoran Copper & Gold Inc | +95% | +43% | matches Yahoo |
| 2017 | 4 | NEM | `NEM` | Newmont Goldcorp Corp | +90% | +11% | matches Yahoo |
| 2017 | 5 | AMAT | `AMAT` | Applied Materials Inc | +76% | +68% | matches Yahoo |
| 2017 | 6 | PWR | `PWR` | Quanta Services Inc | +72% | +12% | matches Yahoo |
| 2017 | 7 | SE | `SE1` | Spectra Energy Corp | +72% | -2% | hand-checked: consistent with company history |
| 2017 | 8 | CMA | `CMA` | Comerica Incorporated | +66% | +27% | hand-checked: consistent with company history |
| 2017 | 9 | MLM | `MLM` | Martin Marietta Materials Inc | +64% | +2% | matches Yahoo |
| 2017 | 10 | HAL | `HAL` | Halliburton Company | +62% | -9% | matches Yahoo |
| 2018 | 1 | NRG | `NRG` | NRG Energy Inc. | +134% | +32% | matches Yahoo |
| 2018 | 2 | ALGN | `ALGN` | Align Technology Inc | +131% | -10% | matches Yahoo |
| 2018 | 3 | VRTX | `VRTX` | Vertex Pharmaceuticals Inc | +103% | +7% | matches Yahoo |
| 2018 | 4 | WYNN | `WYNN` | Wynn Resorts Limited | +98% | -35% | matches Yahoo |
| 2018 | 5 | BA | `BA` | The Boeing Company | +95% | +11% | matches Yahoo |
| 2018 | 6 | DHI | `DHI` | DR Horton Inc | +89% | -30% | matches Yahoo |
| 2018 | 7 | MU | `MU` | Micron Technology Inc | +88% | -25% | matches Yahoo |
| 2018 | 8 | PYPL | `PYPL` | PayPal Holdings Inc | +87% | +16% | matches Yahoo |
| 2018 | 9 | PHM | `PHM` | PulteGroup Inc | +83% | -20% | matches Yahoo |
| 2018 | 10 | NVDA | `NVDA` | NVIDIA Corporation | +82% | -31% | matches Yahoo |
| 2019 | 1 | AMD | `AMD` | Advanced Micro Devices Inc | +80% | +161% | matches Yahoo |
| 2019 | 2 | ABMD | `ABMD` | ABIOMED Inc | +73% | -46% | hand-checked: consistent with company history |
| 2019 | 3 | FTNT | `FTNT` | Fortinet Inc | +61% | +57% | matches Yahoo |
| 2019 | 4 | AAP | `AAP` | Advance Auto Parts Inc | +58% | +1% | matches Yahoo |
| 2019 | 5 | TRIP | `TRIP` | TripAdvisor Inc | +57% | -37% | matches Yahoo |
| 2019 | 6 | CMG | `CMG` | Chipotle Mexican Grill Inc | +49% | +94% | matches Yahoo |
| 2019 | 7 | KEYS | `KEYS` | Keysight Technologies Inc | +49% | +70% | matches Yahoo |
| 2019 | 8 | RHT | `RHT` | Red Hat Inc | +46% | +8% | hand-checked: consistent with company history |
| 2019 | 9 | HCA | `HCA` | HCA Healthcare, Inc. | +43% | +23% | matches Yahoo |
| 2019 | 10 | ORLY | `ORLY` | O'Reilly Automotive Inc | +43% | +28% | matches Yahoo |
| 2020 | 1 | AMD | `AMD` | Advanced Micro Devices Inc | +148% | +88% | matches Yahoo |
| 2020 | 2 | LRCX | `LRCX` | Lam Research Corp | +119% | +63% | matches Yahoo |
| 2020 | 3 | KLAC | `KLAC` | KLA Corporation | +104% | +45% | matches Yahoo |
| 2020 | 4 | TGT | `TGT` | Target Corporation | +100% | +44% | matches Yahoo |
| 2020 | 5 | CMG | `CMG` | Chipotle Mexican Grill Inc | +94% | +54% | matches Yahoo |
| 2020 | 6 | XRX | `XRX` | Xerox Corp | +92% | -36% | matches Yahoo |
| 2020 | 7 | QRVO | `QRVO` | Qorvo Inc | +91% | +42% | hand-checked: consistent with company history |
| 2020 | 8 | CPRT | `CPRT` | Copart Inc | +90% | +29% | matches Yahoo |
| 2020 | 9 | AMAT | `AMAT` | Applied Materials Inc | +90% | +42% | matches Yahoo |
| 2020 | 10 | AAPL | `AAPL` | Apple Inc. | +89% | +74% | matches Yahoo |
| 2021 | 1 | TSLA | `TSLA` | Tesla Inc | +743% | +64% | matches Yahoo |
| 2021 | 2 | ETSY | `ETSY` | Etsy, Inc. | +302% | +22% | matches Yahoo |
| 2021 | 3 | NVDA | `NVDA` | NVIDIA Corporation | +122% | +130% | matches Yahoo |
| 2021 | 4 | PYPL | `PYPL` | PayPal Holdings Inc | +117% | -16% | matches Yahoo |
| 2021 | 5 | LB | `LB_old2` | L Brands Inc. | +108% | +102% | hand-checked: consistent with company history |
| 2021 | 6 | ALB | `ALB` | Albemarle Corp | +105% | +56% | matches Yahoo |
| 2021 | 7 | AMD | `AMD` | Advanced Micro Devices Inc | +100% | +63% | matches Yahoo |
| 2021 | 8 | FCX | `FCX` | Freeport-McMoran Copper & Gold Inc | +99% | +54% | matches Yahoo |
| 2021 | 9 | CDNS | `CDNS` | Cadence Design Systems Inc | +97% | +35% | matches Yahoo |
| 2021 | 10 | NOW | `NOW` | ServiceNow Inc | +95% | +20% | matches Yahoo |
| 2022 | 1 | DVN | `DVN` | Devon Energy Corporation | +196% | +38% | matches Yahoo |
| 2022 | 2 | MRO | `MRO` | Marathon Oil Corporation | +150% | +54% | hand-checked: consistent with company history |
| 2022 | 3 | MRNA | `MRNA` | Moderna Inc | +143% | -24% | matches Yahoo |
| 2022 | 4 | FTNT | `FTNT` | Fortinet Inc | +142% | -27% | matches Yahoo |
| 2022 | 5 | SBNY | `SBNY` | Signature Bank | +141% | -65% | hand-checked (Yahoo has no prices); Signature Bank failed in March 2023 |
| 2022 | 6 | F | `F` | Ford Motor Company | +137% | -45% | matches Yahoo |
| 2022 | 7 | BBWI | `BBWI` | Bath & Body Works Inc. | +134% | -37% | matches Yahoo |
| 2022 | 8 | FANG | `FANG` | Diamondback Energy Inc | +128% | +25% | matches Yahoo |
| 2022 | 9 | NVDA | `NVDA` | NVIDIA Corporation | +125% | -52% | matches Yahoo |
| 2022 | 10 | NUE | `NUE` | Nucor Corp | +118% | +18% | matches Yahoo |
| 2023 | 1 | OXY | `OXY` | Occidental Petroleum Corporation | +119% | -0% | matches Yahoo |
| 2023 | 2 | HES | `HES` | Hess Corporation | +94% | +9% | hand-checked: consistent with company history |
| 2023 | 3 | XOM | `XOM` | Exxon Mobil Corp | +87% | -1% | matches Yahoo |
| 2023 | 4 | MPC | `MPC` | Marathon Petroleum Corp | +87% | +41% | matches Yahoo |
| 2023 | 5 | SLB | `SLB` | Schlumberger NV | +81% | +3% | matches Yahoo |
| 2023 | 6 | APA | `APA` | APA Corporation | +76% | -15% | matches Yahoo |
| 2023 | 7 | VLO | `VLO` | Valero Energy Corporation | +75% | +12% | matches Yahoo |
| 2023 | 8 | HAL | `HAL` | Halliburton Company | +74% | -2% | matches Yahoo |
| 2023 | 9 | FSLR | `FSLR` | First Solar Inc | +72% | +18% | matches Yahoo |
| 2023 | 10 | COP | `COP` | ConocoPhillips | +72% | +8% | matches Yahoo |
| 2024 | 1 | NVDA | `NVDA` | NVIDIA Corporation | +239% | +187% | matches Yahoo |
| 2024 | 2 | META | `META` | Meta Platforms Inc. | +194% | +74% | matches Yahoo |
| 2024 | 3 | RCL | `RCL` | Royal Caribbean Cruises Ltd | +162% | +92% | matches Yahoo |
| 2024 | 4 | BLDR | `BLDR` | Builders FirstSource Inc | +157% | -14% | matches Yahoo |
| 2024 | 5 | UBER | `UBER` | Uber Technologies Inc | +149% | +8% | matches Yahoo |
| 2024 | 6 | CCL | `CCL` | Carnival Corporation | +130% | +45% | matches Yahoo |
| 2024 | 7 | PHM | `PHM` | PulteGroup Inc | +129% | +7% | matches Yahoo |
| 2024 | 8 | AMD | `AMD` | Advanced Micro Devices Inc | +128% | -13% | matches Yahoo |
| 2024 | 9 | PANW | `PANW` | Palo Alto Networks Inc | +111% | +25% | matches Yahoo |
| 2024 | 10 | AVGO | `AVGO` | Broadcom Inc | +104% | +117% | matches Yahoo |
| 2025 | 1 | PLTR | `PLTR` | Palantir Technologies Inc. | +340% | +123% | matches Yahoo |
| 2025 | 2 | VST | `VST` | Vistra Corp. | +262% | +11% | matches Yahoo |
| 2025 | 3 | NVDA | `NVDA` | NVIDIA Corporation | +171% | +37% | matches Yahoo |
| 2025 | 4 | UAL | `UAL` | United Airlines Holdings Inc | +135% | +18% | matches Yahoo |
| 2025 | 5 | AXON | `AXON` | Axon Enterprise Inc. | +130% | -6% | matches Yahoo |
| 2025 | 6 | TPL | `TPL` | Texas Pacific Land Corporation | +115% | -24% | matches Yahoo |
| 2025 | 7 | AVGO | `AVGO` | Broadcom Inc | +110% | +51% | matches Yahoo |
| 2025 | 8 | TRGP | `TRGP` | Targa Resources Inc | +110% | +4% | matches Yahoo |
| 2025 | 9 | HWM | `HWM` | Howmet Aerospace Inc | +103% | +92% | matches Yahoo |
| 2025 | 10 | CEG | `CEG` | Constellation Energy Corp | +93% | +52% | matches Yahoo |
