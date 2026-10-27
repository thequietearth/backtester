# S&P 500 Strategy Backtester

I saw a strategy online: every January, buy last year's best-performing S&P 500 stock. The backtests people posted looked amazing, so I built my own to check it properly.

Short answer: most of that return was hindsight. Done honestly (the index members of the time, companies that later went bust, dividends, trading costs), it beat SPY by about a point a year, with a −98% crash along the way.

Then I kept going and tested nine more strategies. This repo is the result: a local Streamlit app, a backtest engine I wrote from scratch, and write-ups of everything I found.

## The results

1999–2025, after 10 bps per trade, with cash earning the T-bill rate:

| Strategy | What it does | Return per year | Worst fall | Sharpe |
|---|---|---|---|---|
| **Every member, equal weight** | Own every S&P 500 member in equal amounts, no picking | **9.9%** | −60% | 0.47 |
| Last year's #1 | Each January, buy last year's best stock | 9.5% | −98% | 0.41 |
| Last year's top 10 | The same with the 10 best | 9.3% | −83% | 0.38 |
| Momentum | Monthly, the top 10% by 12-month return (skipping the latest month) | 9.3% | −61% | 0.41 |
| Low volatility | Quarterly, the 50 members with the calmest prices | 8.8% | **−36%** | **0.52** |
| **SPY** | **The benchmark: the S&P 500, weighted by company size** | **8.4%** | **−55%** | **0.42** |
| Golden cross | Hold SPY while its 50-day average is above its 200-day average | 8.4% | −34% | **0.52** |
| 200-day trend | Hold SPY while it's above its 200-day average | 7.0% | −24% | 0.47 |
| Last year's worst 10 | Each January, buy last year's 10 worst stocks | 5.1% | −82% | 0.27 |
| RSI(2) dip-buying | Buy SPY after a sharp two-day dip in an uptrend | 4.2% | −15% | 0.37 |

**Sharpe** is return per unit of volatility, beyond what T-bills paid. **Worst fall** is the biggest drop from a peak. "Every member, equal weight" is a baseline I added in the robustness check; it isn't in the app yet.

## What I found
1. **Chasing last year's winner kinda works, but it's brutal.** It beat SPY by about a point a year, but at one point it was down 98% and took about 23 years to recover. Most of the result comes from a few recent winners (Nvidia, AMD, Palantir).
2. **The version you see online is mostly hindsight.** Run on *today's* S&P 500 list, the same rule appears to make 19% a year, and 28% for the top 10. Today's list only has the survivors, so that backtest never buys the companies that blew up.
3. **None of my stock-picking rules beat just owning everything.** Owning every member in equal amounts made 9.9% a year, more than any rule I tested. Turns out their lead over SPY was mostly the equal-weight effect: smaller companies beat the giants in the 2000s, and the giants won after 2010.
4. **Momentum looked promising, but it isn't an edge.** I re-ran it with 36 different settings. 31 beat SPY, but none by more than luck could explain, and as a group they don't beat equal weight ([robustness check](docs/robustness.md)).
5. **Timing rules don't make more money, but they can cut the crashes.** The golden cross matched SPY's return with a worst fall of −34% instead of −55%.

Everything in detail, with charts: **[docs/results.md](docs/results.md)**

![Growth of $10,000](docs/figures/growth.png)

## The app
I run it locally. You pick up to four strategies and compare them side by side with SPY: a comparison table, growth and drawdown charts, and a year-by-year table showing every pick. You can change N, the years, trading costs, what cash earns, and the universe (the members of the time, or today's list if you want to see survivorship bias for yourself).

![Comparing four strategies](docs/screenshots/comparison.png)

There are two more pages:
- **Coverage report:** how many members had usable prices each year.
- **Robustness:** all 36 momentum variations.

## Keeping it honest
Most of the work went here, because it's really easy to fool yourself with a backtest.
- **The members of the time.** Each year's picks come from that year's S&P 500, including companies that later went bankrupt or got taken over.
- **No peeking ahead.** Every decision uses only prices up to that day's close, and trades at the next day's close. There's a test proving it for every strategy.
- **Real returns and costs.** Prices include dividends, every trade pays 10 bps, and cash earns the T-bill rate.
- **Fixing data, not prices.** The price data has broken bits: splits counted twice, renamed tickers, spin-offs that look like crashes, junk prices. Automatic checks, plus an audit of every day a strategy held a stock, caught them. Each one is fixed by mapping the right data or excluding the dates, with a note saying why. No price was edited by hand.
- **Checked against real funds.** With the same data and engine, I rebuilt an equal-weight S&P 500 and a low-volatility portfolio, and they track the real funds (RSP and SPLV) closely. I also checked all 540 top-10 and worst-10 picks, against Yahoo or by hand.
- **142 tests,** including hand-worked engine and metric cases. No backtesting libraries.

## Documentation
| Document | What's in it |
|---|---|
| [Results](docs/results.md) | Every strategy, with charts and the story behind the numbers |
| [Robustness check](docs/robustness.md) | Is momentum real? 36 variations, a luck test, and the equal-weight baseline |
| [Sanity check](docs/sanity-check.md) | Rebuilding real funds (RSP, SPLV), and the audit of every holding |
| [Data sources](docs/data-source-evaluation.md) | Why I picked EODHD, and the traps I found in the data |
| [Top-10 pick review](docs/top10-review.md) | All 270 "last year's winners" picks, checked |
| [Worst-10 pick review](docs/worst10-review.md) | All 270 "last year's losers" picks, checked, and which crashes were real |

## Run it yourself
The price data isn't included, because it's licensed for personal use only. To rebuild it you need your own [EODHD](https://eodhd.com) API key on the Historian plan. That's about $20 for a month, and one month is enough to download everything.

Requires Python 3.11+.

```
python -m venv .venv
.venv\Scripts\activate          # Windows. On macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # then put your EODHD API key in .env
python scripts/build_data.py    # download (~4,500 calls, only what's missing), check, build the universes
streamlit run app.py            # open the app at http://localhost:8501
pytest                          # run the tests
```

<details>
<summary>Other scripts</summary>

- `scripts/make_figures.py` redraws the charts and prints the numbers in the write-ups.
- `scripts/robustness.py` runs the 36 momentum variations for the Robustness page (several minutes); `scripts/verify_robustness.py` checks that run independently.
- `scripts/sanity_rsp.py`, `scripts/sanity_factor_etfs.py` and `scripts/audit_holdings.py` (`--variants` adds the momentum variations) run the sanity checks.
- `scripts/run_v1.py`, `scripts/review_top10.py` and `scripts/review_worst10.py` print the pick reviews.
- `scripts/validate_prices.py` checks that the adjusted prices include dividends.
- `scripts/screenshots.py` retakes the screenshots. It needs `pip install -r requirements-dev.txt` and `python -m playwright install chromium`.
</details>

**Also in the repo:**
- S&P 500 membership history, derived from [fja05680/sp500](https://github.com/fja05680/sp500) (MIT licence, notice in `data/LICENSE-fja05680.txt`).
- 3-month T-bill rates from FRED series [DTB3](https://fred.stlouisfed.org/series/DTB3) (Board of Governors of the Federal Reserve System; public domain).
- My hand fixes to the data, `data/ticker_map.csv`, `data/price_exclusions.csv` and `data/crash_review.csv`, each with a note explaining why.

## Licence
[MIT](LICENSE)
