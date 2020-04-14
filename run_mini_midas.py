#!/usr/bin/env python3
"""
starter for mini_midas
"""

import sys
import mini_midas


ACTION_TYPE = sys.argv[1]  # either "data" or "plot", data will keep obtaining data, while plot will draw the plot
if len(sys.argv) > 2:
    TICKER_LIST = sys.argv[2].split(",")  # ticker_list: "tsla,msft", separate the ticker by comma
else:
    TICKER_LIST = [
        'dal', 'aal', 'ual', 'tsla', 'amzn', 'aapl', 'msft',
        'nvda', 'intc', 'googl', 'cost', 'iau', 'gld', 'gm', 'amd']


if ACTION_TYPE.lower() == "get_historical_data":
    mini_midas.stock_utilities.secure_ticker_prices(TICKER_LIST)
elif ACTION_TYPE.lower() == "plot":
    for tic in TICKER_LIST:
        mini_midas.plot.Plotter(tic).run()
        # TODO: try to plot all tickers
        break

elif ACTION_TYPE.lower() == "get_intraday_data":
    mini_midas.stock_utilities.start_monitoring_tickers(TICKER_LIST)
    # for tic in TICKER_LIST:
    #     alpha = mini_midas.stock_utilities.AlphaVantageTickerIntraPriceRetriever(tic)
    #     alpha.run()
    #     break
else:
    print(f"ACTION_TYPE not correct {ACTION_TYPE}, not doing anything")
