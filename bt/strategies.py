"""One function per strategy. Each returns target weights per rebalance date:

    strategy(prices, universe, rebalance_dates, **params) -> DataFrame[date x ticker]

Built in M3.
"""
