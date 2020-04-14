"""
common module
"""
import datetime
import os
import excalibur


LOG_INSTANCE = excalibur.logger.getlogger_debug()


def is_market_closed():
    """
    check if market closed
    """
    dt_obj = datetime.datetime.now()
    return dt_obj.hour >= 16


def is_market_open():
    """
    check if market is open
    """
    dt_obj = datetime.datetime.now()
    time_only_str = dt_obj.strftime('%H%M')
    LOG_INSTANCE.info(time_only_str)
    return time_only_str > '0930' and time_only_str < '1600'


def is_weekend():
    """
    check if now is weekend
    """
    dt_obj = datetime.datetime.now()
    if dt_obj.isoweekday() > 5:
        return True
    return False


def split_date_string() -> (str, str):
    """
    splits date, returns date and hour
    """
    dat = datetime.datetime.now()
    date_str = dat.strftime("%Y%m%d")
    hour_str = dat.strftime("%H")
    return date_str, hour_str


TOKEN_PATH = os.path.expanduser("~/.config/api_tokens/alphavantage.co.token")
BASE_URL = "https://www.alphavantage.co/query?function="
DATA_STORAGE_PATH = os.path.expanduser("~/data/stock_historical_data")


def get_intraday_data_storage_path():
    today = excalibur.time_conversion.get_current_date(date_format="%Y%m%d")
    return f"{DATA_STORAGE_PATH}/intraday/{today}"


def get_historical_data_storage_path():
    today = excalibur.time_conversion.get_current_date(date_format="%Y%m%d")
    return f"{DATA_STORAGE_PATH}/historical/{today}"


def get_file_saved_path(ticker):
    """
    returns file save path,
    it will switch between historical data and intraday data based on the current time.
    when market is open, it will return intraday data path,
    when market is closed, it will return historical data path
    """
    date_str, hour = split_date_string()

    if is_market_closed():
        # we need to give a full name and save it to full day path
        save_path = f"{get_historical_data_storage_path()}/{ticker}.{date_str}.json.gzip"
    else:
        # we save it to intraday
        save_path = f"{get_intraday_data_storage_path()}/{ticker}.{date_str},{hour}.json.gzip"

    return save_path


def get_all_file_saved_path(ticker):
    """
    returns file save path list, this is for plot to load all files that have in a directory,
    """
    date_str, _ = split_date_string()

    if is_market_closed():
        # we need to give a full name and save it to full day path
        save_path = [f"{get_historical_data_storage_path()}/{ticker}.{date_str}.json.gzip"]
    else:
        # we save it to intraday
        save_path = []
        for hour in range(9, 17):
            temp = f"{get_intraday_data_storage_path()}/{ticker}.{date_str}.{hour}.json.gzip"
            if os.path.exists(temp):
                save_path.append(temp)

    return save_path


def is_market_holiday():
    """
    returns if this is market holiday
    """
    # TODO: need to implement this
    return False


def is_market_not_available():
    return (is_market_closed() and not is_market_open()) or is_weekend() or is_market_holiday()
