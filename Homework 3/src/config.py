from datetime import timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "crypto.db" 
SQL_DIR = BASE_DIR / "src" / "sql"  


BINANCE_BASE_URL  = "https://api.binance.com"
EXCHANGE_INFO_URL = f"{BINANCE_BASE_URL}/api/v3/exchangeInfo"
TICKER_24HR_URL   = f"{BINANCE_BASE_URL}/api/v3/ticker/24hr"
KLINES_URL        = f"{BINANCE_BASE_URL}/api/v3/klines"


STABLE_QUOTES = {
    "USDT", "USDC", "FDUSD", "BUSD", "EUR",  # stablecoins / fiat
    "BTC", "ETH", "BNB"                      # major quote assets
}


TOP_N_SYMBOLS    = 1000        
YEARS_OF_HISTORY = 10          
TEN_YEARS_DAYS   = 365 * YEARS_OF_HISTORY


REQUEST_TIMEOUT        = 30  
MAX_KLINES_PER_REQUEST = 1000  


ONE_DAY = timedelta(days=1)
