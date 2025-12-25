from datetime import datetime, timedelta, timezone

from db import INSERT_DAILY_DATA_SQL
from http_client import fetch_klines_range


def normalize_klines(symbol_id, klines):
    """
    Normalize Binance klines to the structure required by insert_daily_data.sql.
    """
    rows_by_date = {}

    for k in klines:
        open_time_ms = k[0]
        open_price   = float(k[1])
        high_price   = float(k[2])
        low_price    = float(k[3])
        close_price  = float(k[4])
        volume       = float(k[5])

        dt = datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc)
        date_str = dt.date().isoformat()

        rows_by_date[date_str] = {
            "symbol_id": symbol_id,
            "date": date_str,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": volume,
            "last_price_24h": close_price,
            "volume_24h": volume,
            "high_24h": high_price,
            "low_24h": low_price,
            "liquidity": volume,
        }

    return rows_by_date


def fill_missing_dates(symbol_id, start_date, end_date, rows_by_date):
    """
    Ensure every calendar day in [start_date, end_date] has a row.
    If a date is missing create a synthetic candle from previous close.
    """
    filled_rows = []
    current = start_date
    prev_close = None

    have_dates = set(rows_by_date.keys())

    while current <= end_date:
        ds = current.isoformat()
        if ds in have_dates:
            row = rows_by_date[ds]
            prev_close = row["close"]
        else:
            if prev_close is not None:
                row = {
                    "symbol_id": symbol_id,
                    "date": ds,
                    "open": prev_close,
                    "high": prev_close,
                    "low": prev_close,
                    "close": prev_close,
                    "volume": 0.0,
                    "last_price_24h": prev_close,
                    "volume_24h": 0.0,
                    "high_24h": prev_close,
                    "low_24h": prev_close,
                    "liquidity": 0.0,
                }
            else:
                row = None

        if row is not None:
            filled_rows.append(row)

        current += timedelta(days=1)

    return filled_rows


def filter_3_fill_data(tasks_iter, conn):
    """
    Final filter:
    - For each task (symbol_id, symbol, date range):
        - fetch all missing klines (via http_client)
        - normalize them
        - fill missing dates
        - insert/merge into daily_data
    """
    cur = conn.cursor()

    for task in tasks_iter:
        symbol_id  = task["symbol_id"]
        symbol     = task["symbol"]
        start_date = task["start_date"]
        end_date   = task["end_date"]

        print(f"  [Filter 3] {symbol}: {start_date} → {end_date}")

        # Download klines from Binance
        klines = fetch_klines_range(symbol, start_date, end_date)

        # Normalize into per-date rows
        rows_by_date = normalize_klines(symbol_id, klines)

        # Fill any missing calendar dates
        rows_to_store = fill_missing_dates(
            symbol_id, start_date, end_date, rows_by_date
        )

        # Insert/update in DB
        if rows_to_store:
            cur.executemany(INSERT_DAILY_DATA_SQL, rows_to_store)
            conn.commit()
