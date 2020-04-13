import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style
import mini_midas
import datetime
import excalibur


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
            ys_price.append(time_prices_dict[date_string]['4. close'])
        return xs_date, ys_price

    def animate(self, i):
        data_file_path = self.get_ticker_file_path()
        json_data = excalibur.file_utility.read_gzip_file_as_json_obj(data_file_path)
        xs, ys = self.parse_json_data_to_graph_data(json_data)

        # plot the graph
        self.ax1.clear()
        self.ax1.plot(xs, ys)

    def run(self):
        ani = animation.FuncAnimation(self.fig, self.animate, interval=1000)
        plt.show()
