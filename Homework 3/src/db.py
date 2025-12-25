import sqlite3
import config

def load_sql(filename: str) -> str:
    path = config.SQL_DIR / filename
    return path.read_text(encoding="utf-8")

def get_connection():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    tables_sql = load_sql("create_tables.sql")
    conn.executescript(tables_sql)
    conn.commit()
    conn.close()


UPSERT_SYMBOL_SQL     = load_sql("upsert_symbol.sql")
SELECT_LAST_DATE_SQL  = load_sql("select_last_date_symbol.sql")
INSERT_DAILY_DATA_SQL = load_sql("insert_daily_data.sql")
SELECT_BY_ID_CRYPTO_SQL = load_sql("select_by_id_cryptocurrencies.sql")