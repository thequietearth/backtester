# Backtester

A Streamlit app that backtests simple, rule-based stock strategies on the S&P 500 and compares them with SPY.

The first question it answers: **what if you had bought last year's best-performing S&P 500 stock every January since 1996?** The answer aims to be honest, which means using:
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

Price data is **not included** in this repo, because it is licensed for personal use only. You rebuild it locally with your own data-source API key; the build script arrives in milestone M1.

How the data source was chosen, and how the alternatives compared: [docs/data-source-evaluation.md](docs/data-source-evaluation.md).

## Licence

[MIT](LICENSE)
