"""
common module
"""
import datetime


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
    return dt_obj.hour >= 9 and dt_obj.minute >= 30


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
