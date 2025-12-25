import sqlite3
from datetime import datetime
from typing import List, Dict

import numpy as np
import pandas as pd

from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, ADXIndicator, CCIIndicator
from ta.volatility import BollingerBands

TECHNICAL_TIMEFRAMES = ["1D", "1W", "1M"]


def _load_ohlcv_for_symbol(conn: sqlite3.Connection, symbol: str) -> pd.DataFrame:
    """
    Load daily OHLCV data for a given symbol from daily_data table.
    """
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


def _resample_timeframe(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """
    Convert daily OHLCV into 1D/1W/1M series.
    """
    if timeframe == "1D":
        return df.copy()

    if timeframe == "1W":
        rule = "W"   
    elif timeframe == "1M":
        rule = "ME"   
    else:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    ohlcv = pd.DataFrame()
    ohlcv["open"] = df["open"].resample(rule).first()
    ohlcv["high"] = df["high"].resample(rule).max()
    ohlcv["low"] = df["low"].resample(rule).min()
    ohlcv["close"] = df["close"].resample(rule).last()
    ohlcv["volume"] = df["volume"].resample(rule).sum()

    ohlcv.dropna(inplace=True)
    return ohlcv


def _weighted_moving_average(series: pd.Series, window: int) -> pd.Series:
    """
    WMA implementation.
    """
    weights = np.arange(1, window + 1)
    return series.rolling(window).apply(
        lambda values: np.dot(values, weights) / weights.sum(),
        raw=True
    )


def _compute_indicators_for_df(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """
    Given OHLCV indexed by date, compute all required indicators.
    """
    df = ohlcv.copy()

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    window = 20  

    # --- Oscillators ---
    df["rsi"] = RSIIndicator(close=close, window=14).rsi()
    macd_ind = MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
    df["macd"] = macd_ind.macd()
    df["macd_signal"] = macd_ind.macd_signal()
    df["macd_hist"] = macd_ind.macd_diff()

    stoch = StochasticOscillator(
        high=high, low=low, close=close, window=14, smooth_window=3
    )
    df["stoch_k"] = stoch.stoch()
    df["stoch_d"] = stoch.stoch_signal()

    df["adx"] = ADXIndicator(high=high, low=low, close=close, window=14).adx()
    df["cci"] = CCIIndicator(high=high, low=low, close=close, window=20).cci()

    # --- Moving-average style ---
    df["sma"] = close.rolling(window).mean()
    df["ema"] = close.ewm(span=window, adjust=False).mean()
    df["wma"] = _weighted_moving_average(close, window)

    bb = BollingerBands(close=close, window=20, window_dev=2)
    df["bb_middle"] = bb.bollinger_mavg()
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()

    df["vol_sma"] = volume.rolling(window).mean()

    return df


def _generate_signal(row: pd.Series) -> str:
    rsi = row["rsi"]
    macd = row["macd"]
    macd_signal = row["macd_signal"]

    if pd.isna(rsi) or pd.isna(macd) or pd.isna(macd_signal):
        return "HOLD"

    # Oversold + bullish MACD -> BUY
    if rsi < 30 and macd > macd_signal:
        return "BUY"

    # Overbought + bearish MACD -> SELL
    if rsi > 70 and macd < macd_signal:
        return "SELL"

    return "HOLD"


def compute_and_store_indicators_for_symbol(
    conn: sqlite3.Connection,
    symbol: str,
    timeframes: List[str] = None,
) -> None:
    """
    Main entry point:
    - load OHLCV from daily_data
    - resample to each timeframe (1D, 1W, 1M)
    - compute indicators
    - generate signals
    - upsert into technical_indicators table
    """
    if timeframes is None:
        timeframes = TECHNICAL_TIMEFRAMES

    base_df = _load_ohlcv_for_symbol(conn, symbol)
    if base_df.empty:
        print(f"[technical] No OHLCV data for symbol {symbol}")
        return

    # get symbol_id
    cur = conn.cursor()
    cur.execute("SELECT id FROM cryptocurrencies WHERE symbol = ?", (symbol,))
    row = cur.fetchone()
    if not row:
        print(f"[technical] Symbol {symbol} not found in cryptocurrencies table")
        return
    symbol_id = row["id"] if isinstance(row, sqlite3.Row) else row[0]

    sql = """
        INSERT INTO technical_indicators (
            symbol_id, date, timeframe,
            rsi, macd, macd_signal, macd_hist,
            stoch_k, stoch_d, adx, cci,
            sma, ema, wma,
            bb_upper, bb_middle, bb_lower,
            vol_sma,
            signal
        )
        VALUES (
            :symbol_id, :date, :timeframe,
            :rsi, :macd, :macd_signal, :macd_hist,
            :stoch_k, :stoch_d, :adx, :cci,
            :sma, :ema, :wma,
            :bb_upper, :bb_middle, :bb_lower,
            :vol_sma,
            :signal
        )
        ON CONFLICT(symbol_id, date, timeframe) DO UPDATE SET
            rsi         = excluded.rsi,
            macd        = excluded.macd,
            macd_signal = excluded.macd_signal,
            macd_hist   = excluded.macd_hist,
            stoch_k     = excluded.stoch_k,
            stoch_d     = excluded.stoch_d,
            adx         = excluded.adx,
            cci         = excluded.cci,
            sma         = excluded.sma,
            ema         = excluded.ema,
            wma         = excluded.wma,
            bb_upper    = excluded.bb_upper,
            bb_middle   = excluded.bb_middle,
            bb_lower    = excluded.bb_lower,
            vol_sma     = excluded.vol_sma,
            signal      = excluded.signal
    """

    for tf in timeframes:
        ohlcv = _resample_timeframe(base_df, tf)
        if ohlcv.empty:
            continue

        df_ind = _compute_indicators_for_df(ohlcv)
        df_ind = df_ind.dropna(subset=["rsi", "macd", "macd_signal"])

        rows: List[Dict] = []
        for idx, r in df_ind.iterrows():
            rows.append({
                "symbol_id": symbol_id,
                "date": idx.date().isoformat(),
                "timeframe": tf,
                "rsi": float(r["rsi"]),
                "macd": float(r["macd"]),
                "macd_signal": float(r["macd_signal"]),
                "macd_hist": float(r["macd_hist"]),
                "stoch_k": float(r["stoch_k"]),
                "stoch_d": float(r["stoch_d"]),
                "adx": float(r["adx"]),
                "cci": float(r["cci"]),
                "sma": float(r["sma"]),
                "ema": float(r["ema"]),
                "wma": float(r["wma"]),
                "bb_upper": float(r["bb_upper"]),
                "bb_middle": float(r["bb_middle"]),
                "bb_lower": float(r["bb_lower"]),
                "vol_sma": float(r["vol_sma"]),
                "signal": _generate_signal(r),
            })

        if rows:
            cur.executemany(sql, rows)
            conn.commit()
            print(f"[technical] Stored {len(rows)} rows for {symbol} ({tf})")
