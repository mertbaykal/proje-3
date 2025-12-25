INSERT INTO daily_data (
    symbol_id,
    date,
    open,
    high,
    low,
    close,
    volume,
    last_price_24h,
    volume_24h,
    high_24h,
    low_24h,
    liquidity
) VALUES (
    :symbol_id,
    :date,
    :open,
    :high,
    :low,
    :close,
    :volume,
    :last_price_24h,
    :volume_24h,
    :high_24h,
    :low_24h,
    :liquidity
)
ON CONFLICT(symbol_id, date) DO UPDATE SET
    open           = excluded.open,
    high           = excluded.high,
    low            = excluded.low,
    close          = excluded.close,
    volume         = excluded.volume,
    last_price_24h = excluded.last_price_24h,
    volume_24h     = excluded.volume_24h,
    high_24h       = excluded.high_24h,
    low_24h        = excluded.low_24h,
    liquidity      = excluded.liquidity;         