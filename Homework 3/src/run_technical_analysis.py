from db import get_connection
from analysis.technical_indicators import compute_and_store_indicators_for_symbol

if __name__ == "__main__":
    conn = get_connection()
    try:
        compute_and_store_indicators_for_symbol(conn, "AAVEBTC")
    finally:
        conn.close()
