# Backtester

A Streamlit app that backtests simple, rule-based stock strategies on the S&P 500 and compares them with SPY.

The first question it answers: **what if you had bought last year's best-performing S&P 500 stock every January since 1999?** The answer aims to be honest, which means using:
- the S&P 500 members as they were on each date, not today's list
- prices that include dividends
- prices for stocks that no longer trade

Leaving any of these out flatters the results; that's survivorship bias.

> **Status:** under construction. Milestones and decisions are in [PLAN.md](PLAN.md).

## Setup

Requires Python 3.11+.

```
python -m venv .venv
.venv\Scripts\activate          # Windows. On macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # then put your EODHD API key in .env
```

## Run

```
streamlit run app.py
pytest
```

## Data

Price data is **not included** in this repo, because it is licensed for personal use only. You rebuild it locally with your own [EODHD](https://eodhd.com) API key (the Historian plan) in `.env`:

```
python scripts/download_eodhd.py --scope v1     # ~4,500 calls: every S&P 500 member since 1996, plus SPY and RSP
python scripts/build_price_cache.py             # maps members to price series and runs the trap test
python scripts/validate_prices.py               # checks that adjusted prices include dividends
streamlit run app.py                            # then open the Coverage report page
```

Index membership **is included**: `data/constituents.parquet` is derived from [fja05680/sp500](https://github.com/fja05680/sp500) under the MIT licence (notice in `data/LICENSE-fja05680.txt`).

How the data source was chosen, and how the alternatives compared: [docs/data-source-evaluation.md](docs/data-source-evaluation.md).

## Licence

[MIT](LICENSE)
