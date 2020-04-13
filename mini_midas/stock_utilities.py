"""

save ticker info


    tickers_to_save = ['dal', 'aal', 'ual', 'tsla', 'amzn', 'aapl', 'msft', 'nvda', 'intc', 'googl', 'cost', 'iau', 'gld', 'gm', 'amd']
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
import excalibur
import requests
import datetime
import gzip
import json
import time

log = excalibur.logger.getlogger_debug()
TICKERS_TO_SAVE = ['dal', 'aal', 'ual', 'tsla', 'amzn', 'aapl', 'msft', 'nvda', 'intc', 'googl', 'cost', 'iau', 'gld', 'gm', 'amd']


class AlphaVantageTickerIntraPriceRetriever:
    """
    this class only collects intraday data, since the api doesn't provide any historical price
    the api limit is 5 call per minute
    """
    TOKEN_PATH = os.path.expanduser("~/.config/api_tokens/alphavantage.co.token")
    BASE_URL = "https://www.alphavantage.co/query?function="
    DATA_STORAGE_PATH = os.path.expanduser("~/storage/music/stock_historical_data")

    def get_today_date(self) -> str:
        """
        return today's date in string
        """
        return excalibur.time_conversion.get_current_date(date_format="%Y%m%d")

    def split_date_string(self) -> (str, str):
        dt = datetime.datetime.now()
        date_str = dt.strftime("%Y%m%d")
        hour_str = dt.strftime("%H")
        return date_str, hour_str

    def init_dirs(self):
        """
        creates directory for today's both intraday and historical data folder
        """
        today = self.get_today_date()

        self.intraday_data_storage_path = f"{self.DATA_STORAGE_PATH}/intraday/{today}"
        self.historical_data_storage_path = f"{self.DATA_STORAGE_PATH}/historical/{today}"

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

        with open(self.TOKEN_PATH, 'r') as f:
            self.token = f.readline()

        if self.token:
            log.info(f"Loaded market api token {self.token}")
        return self.token

    def get_url(self, function_string):
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
                "2020-04-09 16:00:00": {"1. open": "571.9250", "2. high": "573.0100", "3. low": "571.7300", "4. close": "573.0100", "5. volume": "117287"},
                "2020-04-09 15:59:00": {"1. open": "572.0000", "2. high": "572.0000", "3. low": "571.4500", "4. close": "572.0000", "5. volume": "56954"},
                "2020-04-09 15:58:00": {"1. open": "571.4500", "2. high": "572.0000", "3. low": ...
                }
            }, ...
        }

        """
        function_string = f"TIME_SERIES_INTRADAY&symbol={self.ticker}&interval=1min&apikey={self.token}"
        url = self.BASE_URL + function_string
        r = requests.get(url)
        return r.json()

    def retrieve_start_price(self):
        """
        1. try to read from file
        2. if file not exist, read from endpoint
        """
        file_path = self.get_file_saved_path()

        if excalibur.file_utility.does_gzip_file_exist_and_not_empty(file_path):
            ticker_data = excalibur.file_utility.read_gzip_file_as_json_obj(file_path)
            return ticker_data
        else:
            ticker_data = self.get_start_price()
            self.save_start_price_to_file(ticker_data)
            return ticker_data

    def is_dt_after_market(self, dt_str):
        dt_obj = datetime.datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%s')
        return dt_obj.hour >= 16

    def is_market_closed(self):
        dt_obj = datetime.datetime.now()
        return dt_obj.hour >= 16

    def is_market_open(self):
        dt_obj = datetime.datetime.now()
        return dt_obj.hour >= 9 and dt_obj.minute >= 30

    def is_weekend(self):
        dt_obj = datetime.datetime.now()
        if dt_obj.isoweekday() > 5:
            return True
        return False

    def is_market_holiday(self):
        #TODO: need to implement this
        return False

    # def extract_info_out_of_ticker_data(self, data_json):
    #     ticker_name = data_json['2. Symbol']
    #     last_price_datetime = data_json['3. Last Refreshed']
    #     date_str, hour = self.split_date_string()
    #     return ticker_name, last_price_datetime, date_str, hour

    def get_file_saved_path(self):
        date_str, hour = self.split_date_string()

        if self.is_market_closed():
            # we need to give a full name and save it to full day path
            save_path = f"{self.historical_data_storage_path}/{self.ticker}.{date_str}.json.gzip"
        else:
            # we save it to intraday
            save_path = f"{self.intraday_data_storage_path}/{self.ticker}.{date_str},{hour}.json.gzip"

        return save_path

    def get_ticker_name_from_data(self, data_json: dict) -> str:
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
        function_string = f"GLOBAL_QUOTE&symbol={self.ticker}&apikey={self.token}"
        url = self.BASE_URL + function_string
        r = requests.get(url)
        return r.json()

    def save_current_cached_data(self):
        if not self.cache:
            raise Exception("Cache doesn't have any data")
        data_path = self.get_file_saved_path()
        excalibur.file_utility.write_to_gzip(data_path, [json.dumps(self.cache)])

    def reset_cache(self):
        self.cache = []

    def save_price_only(self):
        """
        this method is for those runner periodically saves interday prices to keep a record
        """

        if self.is_market_closed and not self.is_market_open:
            self

        log.info(f"Retrieving {self.ticker} price")
        self.reset_cache()
        # curls and save intraday data
        intraday_price_so_far = self.retrieve_start_price()
        self.save_start_price_to_file(intraday_price_so_far)

    def cache_intraday_ticker_data(self, intraday_price_so_far):
        self.cache = intraday_price_so_far

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
            symbol = global_quote['01. symbol']
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
            log.critical(f"Invalid Quote Data: {ticker_minute_data}, Error: {str(e)}")

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

        log.info(f"Retrieving {self.ticker} price")
        self.reset_cache()

        # curls and save intraday data
        intraday_price_so_far = self.retrieve_start_price()
        self.cache_intraday_ticker_data(intraday_price_so_far)

        self.save_start_price_to_file(intraday_price_so_far)
        # we will stop here for now for saving data
        current_hour = excalibur.time_conversion.get_current_hour()

        import ipdb
        ipdb.set_trace()

        while True:
            # if market is closed or is weekend, or is market holidays, we will just keep sleeping
            if (self.is_market_closed() and not self.is_market_open()) or self.is_weekend() or self.is_market_holiday():
                log.debug('Market Closed,sleeping....Zzzz...')
                time.sleep(60)

            ticker_minute_data = self.get_ticker_price()
            self.cache_ticker_minute_data(ticker_minute_data)

            # save current cached prices every hour
            new_hour = excalibur.time_conversion.get_current_hour()
            if current_hour != new_hour:
                self.save_current_cached_data()
            # sleep 1 minute before retry
            time.sleep(60)

def secure_ticker_prices():
    # we don't do it in weekend
    if self.is_weekend():
        return

    global TICKERS_TO_SAVE
    counter = 0
    for tick in TICKERS_TO_SAVE:
        alpha = AlphaVantageTickerIntraPriceRetriever(tick)
        alpha.save_price_only()
        counter += 1
        if counter % 5 == 0:
            time.sleep(61)



if __name__ == '__main__':
    # secure_ticker_prices()
    alpha = AlphaVantageTickerIntraPriceRetriever("TSLA")
    alpha.run()

