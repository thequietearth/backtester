# Robustness: is momentum real? (M6)

**Verdict: mixed.** Momentum's lead over SPY holds up across settings, but not across time.
- **Across settings:** 31 of 36 variants of the rule beat SPY over 1999–2025, typically by 1.2 points a year.
- **Across time:** all 36 beat SPY in 1999–2009 (typically by 5.0 points a year), but only 1 did in 2010–2025 (typically 1.8 points behind).
- **Luck:** no variant passes the luck test.

The criteria fixed before running call that "mixed", because it fails the condition that a majority beat SPY in each era.

**A check added afterwards explains the result.** Simply owning every member in equal amounts, with no picking at all, returned **9.9% a year**: more than the typical variant (9.7%). It shows the same pattern, ahead of SPY in 1999–2009 and behind it since. Against that baseline, only **14 of 36** variants come out ahead, typically 0.2 points a year behind. **Momentum's lead over SPY is the equal-weight effect, not momentum.**

Reproduce: `python scripts/robustness.py` (several minutes), then open the app's Robustness page or run `python scripts/make_figures.py` for the figure. `python scripts/verify_robustness.py` reruns the independent checks below.

## Why this check
The momentum rule in the results (the top 10% of members by return from 12 months ago to 1 month ago, re-ranked monthly) beat SPY by about a point a year. But that rule involves several fairly arbitrary choices. If the lead only appeared with exactly those choices, it would probably be a fluke of history: "curve fitting". If most reasonable variants show a similar lead, the idea is more likely real.

**Ground rule:** all variants are judged together, and the best one is never the headline. Trying many settings and keeping the best mostly finds the luckiest one (data snooping), whose backtest overstates what it would do next.

## The test, fixed before any results were seen

| Setting | Values |
|---|---|
| Share of members held | top 5%, 10%, 20% |
| Lookback | 6, 9, 12 months |
| Skip the latest month | yes, no |
| Rebalance | monthly, quarterly |

That gives 3 × 3 × 2 × 2 = 36 variants. Everything else is held fixed: members of the time, equal weight, 10 bps per trade, cash at the T-bill rate, 1999–2025. Every variant ranks from the same month-end universe (members with 12 clean months of prices).

**Verdict criteria:**
- **Robust:** at least 75% of variants beat SPY over 1999–2025, *and* a majority beat it in each era (1999–2009, 2010–2025).
- **Fragile:** fewer than half beat SPY.
- **Mixed:** anything in between.

**For each variant:** return and lead over SPY, the lead in each era, Sharpe ratio, worst fall, turnover, the **break-even cost** (the trading cost at which the lead disappears), and two luck measures:
- the **t-statistic**: the average yearly lead divided by its uncertainty (around 2 or more is the usual bar for "probably not luck");
- **no lead when resampled**: the 27 yearly leads redrawn at random 20,000 times, and how often the average comes out at zero or below.

## Results

![Momentum: 36 variants of the rule](figures/robustness.png)

| 36 variants | Result |
|---|---|
| Beat SPY over 1999–2025 | **31** (86%); typical lead +1.2 points a year, range −0.9 to +3.2 |
| Beat SPY in 1999–2009 | **36** (100%); typical lead +5.0 points a year |
| Beat SPY in 2010–2025 | **1** (3%); typical lead −1.8 points a year, range −4.0 to +0.3 |
| Pass the luck test (t ≥ 2) | **0**; highest t 1.81, typical 0.78 |
| No lead when resampled | typically 22% of resampled histories |
| Break-even trading cost | typically 24 bps (range 0–59) |
| Sharpe ratio | typically 0.44 (range 0.33–0.50), against SPY's 0.42 |
| Worst fall | −54% to −71%, against SPY's −55% |

- **The idea isn't a fluke of one setting.** Almost every variant beat SPY over the whole period, and the published rule (+0.9 points a year) ranks 24th of 36: a typical variant, not a lucky pick. Shorter lookbacks did somewhat better than 12 months (typical leads +1.3 and +1.5 points for 6 and 9 months, +0.6 for 12), quarterly rebalancing slightly better than monthly (+1.5 against +1.1), and skipping the latest month made no difference (+1.2 either way). These differences are themselves within the noise, so they are no reason to switch to the "best" settings.
- **But the edge belongs to one era.** Every variant was ahead of SPY in 1999–2009, by 1 to 11 points a year. In 2010–2025 all but one trailed it, by up to 4 points a year. Momentum's weak run since 2009 is widely noted. It began with the "momentum crash" of 2009 (the beaten-down stocks rebounded fastest), and in a market led by a few giant companies, an equal-weight portfolio of about 50 stocks owns too little of them.
- **Nothing passes the luck test.** The yearly lead swings by around 12 points from year to year, so a lead of one or two points a year can't be told apart from luck in 27 years. With 36 variants tested, one or two crossing t ≈ 2 by chance alone would have been no surprise; none did.
- **Costs matter.** Monthly variants replace about four times their holdings a year (median turnover 421%) and break even at about 22 bps per trade; quarterly ones (229%) at about 38 bps. Trading large US stocks costs a few bps today, but the bid-ask spread alone was often 20 bps or more before 2001.
- **The ride is rougher, not smoother.** Typical Sharpe ratios are a little above SPY's (0.44 against 0.42), but 30 of 36 variants had a deeper worst fall than SPY.

## Added after the fact: against owning every member equally
A verification run (below) suggested a fairer baseline than SPY. Every variant holds its stocks in equal amounts, while SPY weights companies by size, so part of any lead over SPY can come from equal weighting alone. This comparison wasn't in the plan: it doesn't change the verdict above, which was set in advance, but it changes what the verdict means.

| | Return per year | vs SPY, 1999–2009 | vs SPY, 2010–2025 | Sharpe | Worst fall |
|---|---|---|---|---|---|
| **Every member, equal weight** (no picking, rebalanced monthly) | **9.9%** | **+5.3 pts** | **−1.5 pts** | **0.47** | −60% |
| Momentum, typical variant | 9.7% | +5.0 pts | −1.8 pts | 0.44 | −60% |
| Momentum, published rule | 9.3% | +4.5 pts | −1.8 pts | 0.41 | −61% |
| SPY | 8.4% | — | — | 0.42 | −55% |

- **Momentum has no edge over equal weight.** Only 14 of 36 variants beat it over 1999–2025 (typically 0.2 points a year behind; the published rule 0.6 behind), and 15 of 36 in each era.
- **The era pattern is equal weight's, not momentum's.** In 1999–2009 smaller companies beat the giants, so any equal-weight portfolio of S&P 500 members beat SPY. After 2010 the giants led, and every equal-weight portfolio trailed. The 36 variants simply rode that wave.
- **Random picks agree.** Portfolios of 48 members picked at random each month returned 8.2–12.2% a year before costs (typically 9.6%, close to equal weight's 10.0%). The typical momentum variant returned 10.5% before costs, but its higher trading uses up most of that difference. Only 2 of 36 variants beat every random portfolio.

## How the run was checked
`scripts/verify_robustness.py` checks the run independently:
- **Returns without the engine:** buy and hold between trades, no costs. 298 of 324 monthly periods of the published rule match the engine exactly. The other 26 are months where a held stock had already stopped trading by the rebalance day, almost always a takeover that had just closed. The engine can't sell it and holds it until its "data ended" exit (−0.08 points a year, the realistic direction).
- In two other variants, a few periods also differ because the engine sold a holding after more than 10 days without a price, while the simple calculation followed the price when it came back. The cases are Gateway and Transocean after their excluded fake days, and May Department Stores, whose code comes back as junk after its 2005 takeover. In each case the engine's result is the right one.
- **Rankings recomputed from the price table:** the stocks held match exactly on all sample dates.
- **Structure:** holding counts stay within 5, 10 or 20% of the universe; quarterly variants only trade in January, April, July and October; reruns are identical.
- **Stored results:** every lead, era lead, t-statistic and break-even cost matches a fresh calculation.
- **No hidden bias:** random portfolios land near the equal-weight baseline, as they should. A pipeline with survivorship bias or lookahead would make random picks look too good.

## Data fixes found on the way
Running 36 variants means holding many more stocks at many more moments. The holdings audit (`scripts/audit_holdings.py --variants`) now covers all of them, and it found broken data that none of the published strategies had held on the bad days:
- **R.R. Donnelley** sits at about $0.02 a share until December 2001, then jumps 44,281% in a day (the company really traded around $30). Before the fix, one variant (top 20%, 12-0 months, monthly) held it across the jump and showed a fake +469% year: 16.7% a year instead of 9.2%.
- **Splits applied twice:** Gateway (1999), Liz Claiborne (2002), St. Jude Medical (2004, a second case after 2002). Raytheon's corrupt adjustment (2001).
- **Spin-offs missing from the adjusted prices:** Kansas City Southern (Stilwell Financial, 2000), E.W. Scripps (Scripps Networks, 2008), Questar (QEP Resources, 2010).
- **Wrong scale or junk:** Electronic Arts before its 2003 split, Noble Energy's 2013 split and its post-takeover prices in 2020, and Schering-Plough from January 2008.

All are excluded by date in `data/price_exclusions.csv`, never edited. Two published results moved slightly:
- **momentum:** 9.2% → 9.3% a year, because a few members dropped out of its ranking at some month-ends;
- **low volatility:** 8.7% → 8.8% a year, because it had held R.R. Donnelley's junk prices for two quarters.

## What this means
Nearly every reasonable version of momentum beat SPY over 27 years, and the result doesn't hang on one lucky setting. But the reason isn't momentum. Simply owning every S&P 500 member in equal amounts did at least as well, with the same good decade and the same bad one. Over the whole period, no variant beats SPY by more than luck could explain, and as a group they don't beat equal weight at all.

Among large US stocks in 1999–2025, then, picking last year's winners each month added nothing beyond holding everything in equal amounts. Holding an index fund would have done about as well, with far less work, trading and tax.
