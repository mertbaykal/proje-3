from datetime import date, timedelta
import config
from db import SELECT_LAST_DATE_SQL


def filter_2_check_dates(symbols_iter, conn):
    """
    Filter 2: 
    - Compare existing data (date ranges) in the database.
    - Produce tasks that specify which symbol and date range need to be downloaded.  
    """
    cur = conn.cursor()

    for sym in symbols_iter:
        symbol_id = sym["symbol_id"]
        symbol = sym["symbol"]

        # Check last available date in the DB
        cur.execute(SELECT_LAST_DATE_SQL, (symbol_id,))
        row = cur.fetchone()
        last_date_str = row["last_date"]

        if last_date_str is None:
            # No data: we fetch at least last N years
            end = date.today()
            start = end - timedelta(days=365 * config.YEARS_OF_HISTORY)
        else:
            # Data exists: continue from next day
            last_date = date.fromisoformat(last_date_str)
            start = last_date + timedelta(days=1)
            end = date.today()

        # If there's something to fetch (start <= end)
        if start <= end:
            yield {
                "symbol_id": symbol_id,
                "symbol": symbol,
                "start_date": start,
                "end_date": end,
            }
        # else: symbol already up to date so nothing to pass to filter 3
