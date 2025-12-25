INSERT INTO cryptocurrencies (symbol, base_asset, quote_asset)
VALUES (?, ?, ?)
ON CONFLICT(symbol) DO UPDATE
SET
    base_asset = excluded.base_asset,
    quote_asset = excluded.quote_asset,
    is_active = 1;
