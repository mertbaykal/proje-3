import config
from db import UPSERT_SYMBOL_SQL, SELECT_BY_ID_CRYPTO_SQL
from http_client import fetch_spot_symbols, fetch_24h_tickers


def build_liquidity_map(tickers):
    """
    Build {symbol: liquidity_metric} using 24h quoteVolume.
    """
    liq = {}
    for t in tickers:
        symbol = t["symbol"]
        try:
            qv = float(t.get("quoteVolume", "0"))
        except ValueError:
            qv = 0.0
        liq[symbol] = qv
    return liq


def is_delisted(symbol_info):
    """
    Exclude delisted / non-trading symbols.
    """
    if symbol_info.get("status") != "TRADING":
        return True
    if symbol_info.get("isSpotTradingAllowed") is False:
        return True
    return False


def has_unstable_quote(symbol_info):
    """
    Exclude pairs with unstable / weird quote currencies.
    """
    quote = symbol_info["quoteAsset"]
    return quote not in config.STABLE_QUOTES


def normalize_symbol(symbol_info, liquidity_map):
    """
    Convert raw Binance symbol info into a uniform dict we work with.
    """
    symbol = symbol_info["symbol"]
    return {
        "symbol": symbol,
        "base_asset": symbol_info["baseAsset"],
        "quote_asset": symbol_info["quoteAsset"],
        "liquidity_metric": liquidity_map.get(symbol, 0.0),
    }


def filter_1_get_symbols(conn, max_symbols=None):
    """
    Filter 1:
    - Fetch metadata and 24h stats from Binance.
    - Exclude invalid symbols (delisted, unstable quote, zero liquidity).
    - Rank by liquidity and keep top N trading pairs.
    - Mark only those N as active in the DB.
    - Upsert into DB and yield for Filter 2.
    """
    if max_symbols is None:
        max_symbols = config.TOP_N_SYMBOLS

    # Raw data from Binance
    symbol_infos = fetch_spot_symbols()
    tickers = fetch_24h_tickers()
    liquidity_map = build_liquidity_map(tickers)

    # Build candidate list
    candidates = []
    for info in symbol_infos:
        if is_delisted(info):
            continue
        if has_unstable_quote(info):
            continue

        sym = normalize_symbol(info, liquidity_map)

        # treat zero-liquidity pairs as invalid / low-liquidity
        if sym["liquidity_metric"] <= 0:
            continue

        candidates.append(sym)

    # Rank by liquidity and keep top N trading pairs
    candidates.sort(key=lambda x: x["liquidity_metric"], reverse=True)
    top_active = candidates[:max_symbols]

    if not top_active:
        return

    cur = conn.cursor()


    cur.execute("UPDATE cryptocurrencies SET is_active = 0")

    # Upsert top N symbols
    for sym in top_active:
        # UPSERT sets is_active=1 for the symbol
        cur.execute(
            UPSERT_SYMBOL_SQL,
            (sym["symbol"], sym["base_asset"], sym["quote_asset"]),
        )

    
        cur.execute(SELECT_BY_ID_CRYPTO_SQL, (sym["symbol"],))
        row = cur.fetchone()
        sym["symbol_id"] = row["id"]

    conn.commit()

    for sym in top_active:
        yield sym
