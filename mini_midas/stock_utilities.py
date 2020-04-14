"""

save ticker info


tickers_to_save = ['dal', 'aal', 'ual', 'tsla', 'amzn',
'aapl', 'msft', 'nvda', 'intc', 'googl', 'cost', 'iau', 'gld', 'gm', 'amd']
    counter = 0
    for tick in tickers_to_save:
        alpha = AlphaVantageTickerIntraPriceRetriever(tick)
        alpha.save_price_only()
        counter += 1
        if counter % 5 == 0:
            time.sleep(61)
"""


import os
import pathlib
import datetime
import json
import time
import requests
import multiprocessing
import excalibur
import mini_midas


LOG_INSTANCE = excalibur.logger.getlogger_debug()


class AlphaVantageTickerIntraPriceRetriever:
    """
    this class only collects intraday data, since the api doesn't provide any historical price
    the api limit is 5 call per minute
    """
    TOKEN_PATH = mini_midas.common.TOKEN_PATH
    BASE_URL = mini_midas.common.BASE_URL
    DATA_STORAGE_PATH = mini_midas.common.DATA_STORAGE_PATH

    def init_dirs(self):
        """
        creates directory for today's both intraday and historical data folder
        """
        self.intraday_data_storage_path = mini_midas.common.get_intraday_data_storage_path()
        self.historical_data_storage_path = mini_midas.common.get_historical_data_storage_path()

        pathlib.Path(self.intraday_data_storage_path).mkdir(parents=True, exist_ok=True)
        pathlib.Path(self.historical_data_storage_path).mkdir(parents=True, exist_ok=True)

    def __init__(self, ticker):
        self.token = self.get_token()
        self.init_dirs()
        self.cache = []
        self.ticker = ticker

    def get_token(self):
        """
        get token from file at a fixed location stated by self.TOKEN_PATH
        """
        if not os.path.exists(self.TOKEN_PATH):
            raise FileNotFoundError(f"Token file at {self.TOKEN_PATH} not found")

        with open(self.TOKEN_PATH, 'r') as fil:
            self.token = fil.readline()

        if self.token:
            LOG_INSTANCE.info("Loaded market api token %s", self.token)
        return self.token

    def get_url(self, function_string):
        """
        URL would return base + function string which is the full url of alphaadvantage url
        https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=MSFT&apikey=demo
        """
        return self.BASE_URL + function_string

    def get_start_price(self):
        """
        when we started during the day, or we periodically disconnected,
        we need to run this to get all prices so far

        {
            "Meta Data": {
                "1. Information": "Intraday (1min) open, high, low, close prices and volume",
                "2. Symbol": "tsla", "3. Last Refreshed": "2020-04-09 16:00:00",
                "4. Interval": "1min", "5. Output Size": "Compact", "6. Time Zone": "US/Eastern"
            },
            "Time Series (1min)": {
                "2020-04-09 16:00:00": {"1. open": "571.9250", "2. high": "573.0100",
                "3. low": "571.7300", "4. close": "573.0100", "5. volume": "117287"},
                "2020-04-09 15:59:00": {"1. open": "572.0000", "2. high": "572.0000",
                "3. low": "571.4500", "4. close": "572.0000", "5. volume": "56954"},
                "2020-04-09 15:58:00": {"1. open": "571.4500", "2. high": "572.0000", "3. low": ...
                }
            }, ...
        }

        """
        function_string = f"TIME_SERIES_INTRADAY&symbol={self.ticker}&interval=1min&apikey={self.token}"
        url = self.BASE_URL + function_string
        req = requests.get(url)
        return req.json()

    def retrieve_start_price(self):
        """
        1. try to read from file
        2. if file not exist, read from endpoint
        """
        file_path = self.get_file_saved_path()

        if excalibur.file_utility.does_gzip_file_exist_and_not_empty(file_path):
            ticker_data = excalibur.file_utility.read_gzip_file_as_json_obj(file_path)
            return ticker_data

        ticker_data = self.get_start_price()
        self.save_start_price_to_file(ticker_data)
        return ticker_data

    @classmethod
    def is_market_holiday(cls):
        """
        returns if this is market holiday
        """
        # TODO: need to implement this
        return False

    # def extract_info_out_of_ticker_data(self, data_json):
    #     ticker_name = data_json['2. Symbol']
    #     last_price_datetime = data_json['3. Last Refreshed']
    #     date_str, hour = self.split_date_string()
    #     return ticker_name, last_price_datetime, date_str, hour

    def get_file_saved_path(self):
        """
        returns file save path,
        it will switch between historical data and intraday data based on the current time.
        when market is open, it will return intraday data path,
        when market is closed, it will return historical data path
        """
        date_str, hour = mini_midas.common.split_date_string()

        if mini_midas.common.is_market_closed():
            # we need to give a full name and save it to full day path
            save_path = f"{self.historical_data_storage_path}/{self.ticker}.{date_str}.json.gzip"
        else:
            # we save it to intraday
            save_path = f"{self.intraday_data_storage_path}/{self.ticker}.{date_str},{hour}.json.gzip"

        return save_path

    @classmethod
    def get_ticker_name_from_data(cls, data_json: dict) -> str:
        """
        extract name from ticker data received
        """
        meta_data = data_json['Meta Data']
        data_ticker_name = meta_data['2. Symbol']
        return data_ticker_name

    def save_start_price_to_file(self, data_json: dict) -> None:
        """
        this writes the data into file

        data has below field for formulating a storage location
        res['Meta Data']
        {'1. Information': 'Intraday (1min) open, high, low, close prices and volume',
        '2. Symbol': 'msft', '3. Last Refreshed': '2020-04-03 16:00:00', '4. Interval': '1min',
        '5. Output Size': 'Compact', '6. Time Zone': 'US/Eastern'}
        """
        data_ticker_name = self.get_ticker_name_from_data(data_json)
        if self.ticker != data_ticker_name:
            raise Exception(f"Error saving data, ticker_name to save: {self.ticker}, data_ticker_name in data:{data_ticker_name}")

        data_path = self.get_file_saved_path()
        excalibur.file_utility.remove_gzip_file_if_empty(data_path)
        excalibur.file_utility.write_to_gzip(data_path, [json.dumps(data_json)])

    def get_ticker_price(self):
        """
        {
            'Global Quote': {'01. symbol': 'TSLA', '02. open': '562.0900', '03. high': '575.1818', '04. low': '557.1100',
            '05. price': '573.0000', '06. volume': '13650000', '07. latest trading day': '2020-04-09',
            '08. previous close': '548.8400', '09. change': '24.1600', '10. change percent': '4.4020%'}
        }
        """
        # https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=MSFT&apikey=demo
        try:
            function_string = f"GLOBAL_QUOTE&symbol={self.ticker}&apikey={self.token}"
            url = self.BASE_URL + function_string
            r = requests.get(url)
            return r.json()

        except Exception as e:
            LOG_INSTANCE.critical("Unable to retrieve price, error: %sstatus:%s, %s, raw:%s", str(e), r.status_code, r.text, r.raw)

    def save_current_cached_data(self):
        if not self.cache:
            raise Exception("Cache doesn't have any data")
        data_path = self.get_file_saved_path()
        excalibur.file_utility.write_to_gzip(data_path, [json.dumps(self.cache)])

    def reset_cache(self):
        self.cache = []

    def clear_intraday_prices(self):
        """
        clears the cached price hourly since holding in memory doesn't serve any purpose and we are writing every hour data into file
        """
        self.cache['Time Series (1min)'] = {}

    def save_price_only(self):
        """
        this method is for those runner periodically saves interday prices to keep a record
        """

        if mini_midas.common.is_market_closed and not mini_midas.common.is_market_open:
            # sleeps 1 hr and hope the market is closed and we can get full historical price
            time.sleep(3600)

        LOG_INSTANCE.info(f"Retrieving {self.ticker} price")
        self.reset_cache()
        # curls and save intraday data
        intraday_price_so_far = self.retrieve_start_price()
        self.save_start_price_to_file(intraday_price_so_far)

    def cache_intraday_ticker_data(self, intraday_price_so_far):
        self.cache = intraday_price_so_far

    def get_latest_price_from_cache(self):
        """
        display the latest price from cache, which is in below format

        intraday format:
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
        if not self.cache:
            raise Exception("Empty Cache")
        time_series = self.cache["Time Series (1min)"]
        keys = sorted(time_series.keys())
        latest_date = keys[-1]
        latest_data = time_series[latest_date]
        latest_data['timestamp'] = latest_date
        return latest_data

    def cache_ticker_minute_data(self, ticker_minute_data):
        """
        this function would add daily data into intraday format
        every minute ticker data:
        {
            'Global Quote': {
                '01. symbol': 'TSLA',
                '02. open': '562.0900',
                '03. high': '575.1818',
                '04. low': '557.1100',
                '05. price': '573.0000',
                '06. volume': '13650000',
                '07. latest trading day': '2020-04-09',
                '08. previous close': '548.8400',
                '09. change': '24.1600',
                '10. change percent': '4.4020%'
            }
        },

        intraday format:
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
        try:
            global_quote = ticker_minute_data['Global Quote']
            # check symbol is the same or not
            # symbol = global_quote['01. symbol']
            open_price = global_quote['02. open']
            high_price = global_quote['03. high']
            low_price = global_quote['04. low']
            price = global_quote['05. price']
            volume = global_quote['06. volume']

            # 2020-04-09 16:00:00, we manufacture this receive time just for intraday display purpose
            date_received = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # just irresponsbily append to the end and hope the display would do a sort before display
            self.cache['Time Series (1min)'][date_received] = {
                "1. open": open_price, "2. high": high_price, "3. low": low_price, "4. close": price, "5. volume": volume,
            }

        except Exception as e:
            LOG_INSTANCE.critical(f"Invalid Quote Data: {ticker_minute_data}, Error: {str(e)}")

    def sleep_if_market_not_available(self):
        while mini_midas.common.is_market_not_available():
            LOG_INSTANCE.debug('Market Closed,sleeping....Zzzz...')
            time.sleep(60)
            continue

        LOG_INSTANCE.info("Market is Open")

    def run(self):
        """
        this main method will do below steps, but remember, this intraday data collected may be
        different from it whole day minute data, we need to have a separate process
        that specialized at collect this daily data and the end of market every day

        # 1. curl endpoint to download all minute price so far
        # 2. save them into a file, if today market is already closed, we should save it at another location
        # 3. curl the endpoint every minute to retrieve price until market ends
        # 4. every 10 minutes, save the price into a flat file, by hour
        # 5. when market ends, save all these files into one file at another location
        """

        self.sleep_if_market_not_available()

        LOG_INSTANCE.info(f"Retrieving {self.ticker} price")
        self.reset_cache()

        # curls and save intraday data
        intraday_price_so_far = self.retrieve_start_price()
        self.cache_intraday_ticker_data(intraday_price_so_far)
        latest_price = self.get_latest_price_from_cache()
        LOG_INSTANCE.info("Retrieved Latest Intraday data for %s: %s", self.ticker, latest_price)

        self.save_start_price_to_file(intraday_price_so_far)
        # we will stop here for now for saving data
        current_hour = excalibur.time_conversion.get_current_hour()

        # import ipdb
        # ipdb.set_trace()

        # TODO: intraday disconnected, then we will have one hour carries all daily data, we need to address this issue

        while True:
            # if market is closed or is weekend, or is market holidays, we will just keep sleeping
            if mini_midas.common.is_market_not_available():
                LOG_INSTANCE.debug('Market Closed,sleeping....Zzzz...')
                time.sleep(60)
                continue

            ticker_minute_data = self.get_ticker_price()
            LOG_INSTANCE.info("%s intraday: %s", self.ticker, ticker_minute_data)
            self.cache_ticker_minute_data(ticker_minute_data)

            # save current cached prices every hour
            new_hour = excalibur.time_conversion.get_current_hour()
            if current_hour != new_hour:
                self.save_current_cached_data()
                self.clear_intraday_prices()
            # sleep 1 minute before retry
            time.sleep(60)


def secure_ticker_prices(ticker_list):
    # we don't do it in weekend
    if mini_midas.common.is_weekend():
        return

    counter = 0
    for tick in ticker_list:
        alpha = AlphaVantageTickerIntraPriceRetriever(tick)
        alpha.save_price_only()
        counter += 1
        if counter % 5 == 0:
            time.sleep(61)


def monit_ticker(tic):
    while True:
        try:
            alpha = mini_midas.stock_utilities.AlphaVantageTickerIntraPriceRetriever(tic)
            alpha.run()
        except Exception as e:
            LOG_INSTANCE.critical("%s monitoring process was terminated, error: %s", tic, str(e))

        time.sleep(1)


def start_monitoring_tickers(tickers):
    # multiprocessing
    print("Number of cpu : ", multiprocessing.cpu_count())

    # Process will create a process waiting to run
    procs = []
    for tick in tickers:
        p = multiprocessing.Process(target=monit_ticker, args=(tick,))
        time.sleep(1)
        p.start()
        procs.append(p)

    # wait for process to end
    for p in procs:
        p.join()


if __name__ == '__main__':
    # secure_ticker_prices()
    alpha = AlphaVantageTickerIntraPriceRetriever("TSLA")
    alpha.run()
