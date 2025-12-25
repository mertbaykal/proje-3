CREATE TABLE IF NOT EXISTS cryptocurrencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,      -- 'BTCUSDT'
    base_asset TEXT NOT NULL,         -- 'BTC'
    quote_asset TEXT NOT NULL,        -- 'USDT'
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS daily_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol_id INTEGER NOT NULL,       
    date TEXT NOT NULL,              
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume REAL,
    last_price_24h REAL,
    volume_24h REAL,
    high_24h REAL,
    low_24h REAL,
    liquidity REAL,
    UNIQUE(symbol_id, date),
    FOREIGN KEY (symbol_id) REFERENCES cryptocurrencies(id)
);


CREATE TABLE IF NOT EXISTS technical_indicators (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol_id     INTEGER NOT NULL,
    date          TEXT    NOT NULL, 
    timeframe     TEXT    NOT NULL, -- '1D', '1W', '1M'

    -- 5 oscillators
    rsi           REAL,
    macd          REAL,
    macd_signal   REAL,
    macd_hist     REAL,
    stoch_k       REAL,
    stoch_d       REAL,
    adx           REAL,
    cci           REAL,

    -- 5 moving-average style indicators
    sma           REAL,
    ema           REAL,
    wma           REAL,
    bb_upper      REAL,
    bb_middle     REAL,
    bb_lower      REAL,
    vol_sma       REAL,

  
    signal        TEXT,   -- 'BUY', 'SELL', 'HOLD'

    UNIQUE (symbol_id, date, timeframe),
    FOREIGN KEY (symbol_id) REFERENCES cryptocurrencies(id)
);


CREATE TABLE IF NOT EXISTS lstm_predictions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol_id        INTEGER NOT NULL,
    prediction_date  TEXT    NOT NULL, 
    timeframe        TEXT    NOT NULL DEFAULT '1D',
    horizon_days     INTEGER NOT NULL, -- for next day
    lookback_days    INTEGER NOT NULL, 
    predicted_close  REAL    NOT NULL,

 
    rmse             REAL,
    mape             REAL,
    r2               REAL,

    model_name       TEXT,
    created_at       TEXT    NOT NULL, -- date when model was trained

    UNIQUE (symbol_id, prediction_date, timeframe, horizon_days, lookback_days),
    FOREIGN KEY (symbol_id) REFERENCES cryptocurrencies(id)
);