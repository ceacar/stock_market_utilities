import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style
from matplotlib import ticker
import mini_midas
import datetime
import excalibur
# import pandas


LOG_INSTANCE = excalibur.logger.getlogger_debug()
style.use('fivethirtyeight')


class Plotter:
    def __init__(self, ticker):
        self.ticker = ticker
        self.fig = plt.figure()
        self.ax1 = self.fig.add_subplot(1, 1, 1)
        self.path_finder = mini_midas.stock_utilities.AlphaVantageTickerIntraPriceRetriever(self.ticker)

    def get_ticker_file_path(self):
        return self.path_finder.get_file_saved_path()

    def parse_json_data_to_graph_data(self, json_obj: dict) -> (list, list):
        """
        {
            "Meta Data": {
                "1. Information": "Intraday (1min) open, high, low, close prices and volume",
                "2. Symbol": "tsla", "3. Last Refreshed": "2020-04-09 16:00:00",
                "4. Interval": "1min", "5. Output Size": "Compact", "6. Time Zone": "US/Eastern"
            },
            "Time Series (1min)": {
                "2020-04-09 16:00:00": {"1. open": "571.9250", "2. high": "573.0100", "3. low": "571.7300", "4. close": "573.0100", "5. volume": "117287"},
                "2020-04-09 15:59:00": {"1. open": "572.0000", "2. high": "572.0000", "3. low": "571.4500", "4. close": "572.0000", "5. volume": "56954"},
                "2020-04-09 15:58:00": {"1. open": "571.4500", "2. high": "572.0000", "3. low": ...
                }
            }, ...
        }
        """
        time_prices_dict = json_obj["Time Series (1min)"]
        xs_date, ys_price = [], []
        for date_string in sorted(time_prices_dict.keys()):
            xs_date.append(datetime.datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S"))
            ys_price.append((
                float(time_prices_dict[date_string]['2. high']) + float(time_prices_dict[date_string]['3. low'])) / 2.0
            )
            # ys_price.append(time_prices_dict[date_string]['4. close'])
        return xs_date, ys_price

    def merge_historical_data(self, old_json, new_json_data):
        if not old_json:
            return new_json_data

        old_json["Time Series (1min)"].update(new_json_data["Time Series (1min)"])

        # now we want to sort this dict by dates, so we can have a nice plot
        time_series = old_json["Time Series (1min)"]
        new_time_series_dict = {}
        for dt in sorted(time_series.keys()):
            new_time_series_dict[dt] = time_series[dt]
        old_json["Time Series (1min)"] = new_time_series_dict

        return old_json

    def merge_data(self, old_json, new_json_data):
        """
        merge data currently only for historical data since we are caching all prices in memory throughout the day
        """
        return self.merge_historical_data(old_json, new_json_data)

    # TODO: now expand this to multiple
    def animate(self, interval):
        data_file_path_list = mini_midas.common.get_all_file_saved_path(self.ticker)
        ticker_data = {}
        for file_path in data_file_path_list:
            json_data = excalibur.file_utility.read_gzip_file_as_json_obj(file_path)
            LOG_INSTANCE.info("Reading from %s", file_path)
            ticker_data = self.merge_data(ticker_data, json_data)
        xs, ys = self.parse_json_data_to_graph_data(ticker_data)

        # plot the graph
        self.ax1.clear()
        self.ax1.yaxis.set_major_locator(ticker.MultipleLocator(12))
        self.ax1.plot(xs, ys)
        # self.ax1.xlabel("时间")
        # self.ax1.ylabel("价格")
        self.ax1.set_title(f"{self.ticker}")

    # def parse_json_data_to_pandas(self, json_obj: dict) -> (list, list):
    #     """
    #     {
    #         "Meta Data": {
    #             "1. Information": "Intraday (1min) open, high, low, close prices and volume",
    #             "2. Symbol": "tsla", "3. Last Refreshed": "2020-04-09 16:00:00",
    #             "4. Interval": "1min", "5. Output Size": "Compact", "6. Time Zone": "US/Eastern"
    #         },
    #         "Time Series (1min)": {
    #             "2020-04-09 16:00:00": {"1. open": "571.9250", "2. high": "573.0100", "3. low": "571.7300", "4. close": "573.0100", "5. volume": "117287"},
    #             "2020-04-09 15:59:00": {"1. open": "572.0000", "2. high": "572.0000", "3. low": "571.4500", "4. close": "572.0000", "5. volume": "56954"},
    #             "2020-04-09 15:58:00": {"1. open": "571.4500", "2. high": "572.0000", "3. low": ...
    #             }
    #         }, ...
    #     }
    #     """
    #     time_prices_dict = json_obj["Time Series (1min)"]
    #     dict_list = []
    #     for dt in time_prices_dict.keys():
    #         time_prices_dict[dt]['timestamp'] = dt
    #         dict_list.append(time_prices_dict[dt])
    #     return pandas.DataFrame.from_dict(dict_list)

    # def get_market_plot_figure(self):
    #     data_file_path = self.get_ticker_file_path()
    #     json_data = excalibur.file_utility.read_gzip_file_as_json_obj(data_file_path)

    #     fig = plt.figure(figsize=(10, 10))

    #     # ax.xaxis.set_major_locator(matplotlib.dates.YearLocator())
    #     # ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%Y'))
    #     # plt.locator_params(nbins=4)
    #     df = self.parse_json_data_to_pandas(json_data)
    #     import ipdb
    #     ipdb.set_trace()
    #     plt.plot(df['timestamp'], df['4. close'])
    #     # plt.yticks(np.arange(min(df['4. close']), max(df['4. close']) + 1, 1.0))
    #     plt.xlabel("date")
    #     plt.ylabel("price")
    #     plt.title(f"{self.ticker} Stock Price")
    #     return fig

    def run(self):
        ani = animation.FuncAnimation(self.fig, self.animate, interval=1000)
        # self.get_market_plot_figure()
        plt.show()
