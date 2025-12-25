import requests
from datetime import datetime, timedelta, timezone

import config


def fetch_spot_symbols():
    """
    Call Binance /api/v3/exchangeInfo and return the list of symbol objects
    that have SPOT permission.
    """
    resp = requests.get(
        config.EXCHANGE_INFO_URL,
        params={"permissions": "SPOT"},
        timeout=config.REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["symbols"]  


def fetch_24h_tickers():
    """
    Call Binance /api/v3/ticker/24hr and return the list of 24h ticker stats.
    """
    resp = requests.get(
        config.TICKER_24HR_URL,
        timeout=config.REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()  


def date_to_ms(d):
    """
    Convert a date object to a UTC timestamp in milliseconds
    representing the start of that day.
    """
    dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def fetch_klines_range(symbol, start_date, end_date):
    """
    Fetch ALL daily klines for [start_date, end_date] by looping over /api/v3/klines.

    Returns a list of raw kline arrays as returned by Binance.
    """
    all_klines = []
    current_start = start_date

    while current_start <= end_date:
        params = {
            "symbol": symbol,
            "interval": "1d",
            "startTime": date_to_ms(current_start),
            "endTime": date_to_ms(end_date),
            "limit": config.MAX_KLINES_PER_REQUEST,
        }
        resp = requests.get(
            config.KLINES_URL,
            params=params,
            timeout=config.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        chunk = resp.json()

        if not chunk:
            break  # no more data

        all_klines.extend(chunk)

        # Advance current_start to the next day after the last kline we got
        last_open_time_ms = chunk[-1][0]
        last_dt = datetime.fromtimestamp(
            last_open_time_ms / 1000, tz=timezone.utc
        ).date()
        current_start = last_dt + timedelta(days=1)

        # Just in case something weird happens and we don't move forward:
        if current_start <= start_date:
            break

    return all_klines
