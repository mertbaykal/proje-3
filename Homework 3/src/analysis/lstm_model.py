import sqlite3
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error, r2_score

from keras.models import Sequential
from keras.layers import LSTM, Dense, Dropout


def _load_ohlcv_for_symbol(conn: sqlite3.Connection, symbol: str) -> pd.DataFrame:
    query = """
        SELECT d.date, d.open, d.high, d.low, d.close, d.volume
        FROM daily_data d
        JOIN cryptocurrencies c ON c.id = d.symbol_id
        WHERE c.symbol = ?
        ORDER BY d.date
    """
    df = pd.read_sql_query(query, conn, params=(symbol,))
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    return df


def _create_sequences(data: np.ndarray, lookback: int):
    """
    Turn [T, features] into sequences of shape [num_samples, lookback, features]
    and targets [num_samples].
    """
    X, y = [], []
    for i in range(lookback, len(data)):
        X.append(data[i - lookback:i])
        # predict next day close price
        y.append(data[i, 3])
    return np.array(X), np.array(y)


def train_lstm_for_symbol(
    conn: sqlite3.Connection,
    symbol: str,
    lookback_days: int = 30,
    horizon_days: int = 1,
    epochs: int = 20,
    batch_size: int = 32,
):
    """
    Train an LSTM on OHLCV for a given symbol and store predictions + metrics
    into lstm_predictions table.
    """
    df = _load_ohlcv_for_symbol(conn, symbol)
    if df.empty:
        print(f"[lstm] No OHLCV data for {symbol}")
        return

    
    df = df[["open", "high", "low", "close", "volume"]].astype(float)

    values = df.values
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(values)

    X, y = _create_sequences(scaled, lookback_days)
    if len(X) < 10:
        print(f"[lstm] Not enough data for {symbol} with lookback={lookback_days}")
        return

    # split 70% train / 30% test
    split_index = int(len(X) * 0.7)
    X_train, X_test = X[:split_index], X[split_index:]
    y_train, y_test = y[:split_index], y[split_index:]

    # Build LSTM model
    model = Sequential()
    model.add(LSTM(64, return_sequences=True, input_shape=(lookback_days, X.shape[2])))
    model.add(Dropout(0.2))
    model.add(LSTM(32))
    model.add(Dropout(0.2))
    model.add(Dense(1))

    model.compile(optimizer="adam", loss="mse")
    model.fit(X_train, y_train, epochs=epochs, batch_size=batch_size, verbose=1)

    # Evaluate
    y_pred_test = model.predict(X_test)

    # Inverse scale only the close price
    # Build a helper array so we can invert using the same scaler
    def _invert_scaled_close(scaled_close_vals):
        helper = np.zeros((len(scaled_close_vals), scaled.shape[1]))
        helper[:, 3] = scaled_close_vals.reshape(-1)  
        inv = scaler.inverse_transform(helper)
        return inv[:, 3]

    y_test_inv = _invert_scaled_close(y_test)
    y_pred_inv = _invert_scaled_close(y_pred_test)

    rmse = float(np.sqrt(mean_squared_error(y_test_inv, y_pred_inv)))
    mape = float(mean_absolute_percentage_error(y_test_inv, y_pred_inv))
    r2 = float(r2_score(y_test_inv, y_pred_inv))

    print(f"[lstm] {symbol} RMSE={rmse:.4f}, MAPE={mape:.4f}, R2={r2:.4f}")

    # Get symbol_id
    cur = conn.cursor()
    cur.execute("SELECT id FROM cryptocurrencies WHERE symbol = ?", (symbol,))
    row = cur.fetchone()
    if not row:
        print(f"[lstm] Symbol {symbol} not found in cryptocurrencies table")
        return
    symbol_id = row["id"] if isinstance(row, sqlite3.Row) else row[0]

    # Store predictions for the test period
    dates = df.index[lookback_days + split_index : lookback_days + split_index + len(y_test_inv)]
    created_at = datetime.utcnow().isoformat()
    model_name = "LSTM_close_v1"

    insert_sql = """
        INSERT INTO lstm_predictions (
            symbol_id, prediction_date, timeframe,
            horizon_days, lookback_days,
            predicted_close,
            rmse, mape, r2,
            model_name, created_at
        )
        VALUES (?, ?, '1D', ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol_id, prediction_date, timeframe, horizon_days, lookback_days)
        DO UPDATE SET
            predicted_close = excluded.predicted_close,
            rmse            = excluded.rmse,
            mape            = excluded.mape,
            r2              = excluded.r2,
            model_name      = excluded.model_name,
            created_at      = excluded.created_at
    """

    rows = []
    for d, pred_close in zip(dates, y_pred_inv):
        rows.append(
            (
                symbol_id,
                d.date().isoformat(),
                horizon_days,
                lookback_days,
                float(pred_close),
                rmse,
                mape,
                r2,
                model_name,
                created_at,
            )
        )

    if rows:
        cur.executemany(insert_sql, rows)
        conn.commit()
        print(f"[lstm] Stored {len(rows)} prediction rows for {symbol}")

    # Predict one step into the future - the next day
    last_window = scaled[-lookback_days:]
    last_window = np.expand_dims(last_window, axis=0)
    next_scaled = model.predict(last_window)
    next_close = _invert_scaled_close(next_scaled)[0]

    future_date = df.index[-1].date() + timedelta(days=horizon_days)

    cur.execute(
        insert_sql,
        (
            symbol_id,
            future_date.isoformat(),
            horizon_days,
            lookback_days,
            float(next_close),
            rmse,
            mape,
            r2,
            model_name + "_future",
            created_at,
        ),
    )
    conn.commit()
    print(f"[lstm] Stored future prediction for {symbol} on {future_date}")
