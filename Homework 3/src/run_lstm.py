from db import get_connection
from analysis.lstm_model import train_lstm_for_symbol

if __name__ == "__main__":
    conn = get_connection()
    try:
        train_lstm_for_symbol(conn, "AAVEBTC", lookback_days=30, epochs=15)
    finally:
        conn.close()
