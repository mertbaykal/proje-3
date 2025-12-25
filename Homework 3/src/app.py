from flask import Flask, render_template, request
import sqlite3
import os
from pathlib import Path
import json

app = Flask(__name__)

# DB helpers

def find_database():
    """Automatically find crypto.db in a few common locations."""
    possible_paths = [
        "./crypto.db",
        "../crypto.db",
    ]

    for path in possible_paths:
        if os.path.exists(path):
            print(f"Database found at: {path}")
            return path

    home = Path.home()
    for db_path in home.rglob("crypto.db"):
        if os.path.exists(db_path):
            print(f"Database found at: {db_path}")
            return str(db_path)

    print("Database not found!")
    return None


DB_PATH = find_database()


def get_db_connection():
    """Return a sqlite3 connection with row access by column name."""
    if DB_PATH and os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    return None


# Make DB path available in all templates as {{ db_path }}
@app.context_processor
def inject_globals():
    return {"db_path": DB_PATH}



def format_number(num):
    """Format large numbers into K / M / B with a $ sign."""
    if num is None:
        return "N/A"
    try:
        num = float(num)
        if num >= 1e9:
            return f"${num/1e9:.2f}B"
        elif num >= 1e6:
            return f"${num/1e6:.2f}M"
        elif num >= 1e3:
            return f"${num/1e3:.2f}K"
        return f"${num:.2f}"
    except Exception:
        return "N/A"


app.jinja_env.filters["format_number"] = format_number


def format_float(value, digits=4):
    """Format a float with a fixed number of decimal places."""
    if value is None:
        return ""
    try:
        return f"{float(value):.{int(digits)}f}"
    except (TypeError, ValueError):
        return ""


app.jinja_env.filters["format_float"] = format_float


@app.route("/")
def dashboard():
    conn = get_db_connection()
    if not conn:
        return render_template("db_missing.html"), 500

    try:
        cur = conn.cursor()

        # Total symbols
        cur.execute("SELECT COUNT(*) AS count FROM cryptocurrencies")
        total_symbols = cur.fetchone()["count"]

        # Total data points
        cur.execute("SELECT COUNT(*) AS count FROM daily_data")
        total_data_points = cur.fetchone()["count"]

        # Average volume for non-zero days
        cur.execute("SELECT AVG(volume) AS avg_volume FROM daily_data WHERE volume > 0")
        row = cur.fetchone()
        avg_volume = row["avg_volume"] if row and row["avg_volume"] is not None else 0

        # Last update date
        cur.execute("SELECT MAX(date) AS last_date FROM daily_data")
        row = cur.fetchone()
        last_update = row["last_date"] if row and row["last_date"] else "Never"

        # Top 10 symbols by avg volume
        cur.execute("""
            SELECT 
                c.symbol, 
                c.base_asset, 
                c.quote_asset,
                (SELECT AVG(volume) FROM daily_data WHERE symbol_id = c.id) AS avg_volume,
                (SELECT MAX(volume) FROM daily_data WHERE symbol_id = c.id) AS max_volume
            FROM cryptocurrencies c
            WHERE EXISTS (SELECT 1 FROM daily_data WHERE symbol_id = c.id)
            ORDER BY avg_volume DESC
            LIMIT 10
        """)
        top_symbols = cur.fetchall()

    finally:
        conn.close()

    return render_template(
        "dashboard.html",
        total_symbols=total_symbols,
        total_data_points=total_data_points,
        avg_volume=avg_volume,
        last_update=last_update,
        top_symbols=top_symbols,
    )


@app.route("/symbols")
def symbols_list():
    conn = get_db_connection()
    if not conn:
        return "Database not available", 500

    # page for normal listing, query for global search
    page = request.args.get("page", default=1, type=int)
    q = request.args.get("q", default="", type=str).strip()
    page_size = 50
    offset = (page - 1) * page_size

    try:
        cur = conn.cursor()

        if q:
            # SEARCH MODE: look across ALL symbols 
            like = f"%{q.upper()}%"

            cur.execute("""
                WITH latest AS (
                    SELECT symbol_id, MAX(date) AS latest_date
                    FROM daily_data
                    GROUP BY symbol_id
                )
                SELECT
                    c.id,
                    c.symbol,
                    c.base_asset,
                    c.quote_asset,
                    c.is_active,
                    d.date,
                    d.open,
                    d.high,
                    d.low,
                    d.close,
                    d.volume,
                    d.last_price_24h,
                    d.volume_24h,
                    d.high_24h,
                    d.low_24h,
                    d.liquidity
                FROM cryptocurrencies c
                JOIN latest l ON l.symbol_id = c.id
                JOIN daily_data d
                  ON d.symbol_id = c.id AND d.date = l.latest_date
                WHERE UPPER(c.symbol)      LIKE ?
                   OR UPPER(c.base_asset)  LIKE ?
                   OR UPPER(c.quote_asset) LIKE ?
                ORDER BY c.symbol
            """, (like, like, like))

            symbols = cur.fetchall()
            total_symbols = len(symbols)

            # in search mode we show all matches on one page
            page = 1
            total_pages = 1
            has_prev = False
            has_next = False

        else:
            # NORMAL MODE: paginated list of all symbols 
            cur.execute("""
                WITH latest AS (
                    SELECT symbol_id, MAX(date) AS latest_date
                    FROM daily_data
                    GROUP BY symbol_id
                )
                SELECT
                    c.id,
                    c.symbol,
                    c.base_asset,
                    c.quote_asset,
                    c.is_active,
                    d.date,
                    d.open,
                    d.high,
                    d.low,
                    d.close,
                    d.volume,
                    d.last_price_24h,
                    d.volume_24h,
                    d.high_24h,
                    d.low_24h,
                    d.liquidity
                FROM cryptocurrencies c
                JOIN latest l ON l.symbol_id = c.id
                JOIN daily_data d
                  ON d.symbol_id = c.id AND d.date = l.latest_date
                ORDER BY c.symbol
                LIMIT ? OFFSET ?
            """, (page_size, offset))
            symbols = cur.fetchall()

            # total count for pagination
            cur.execute("""
                SELECT COUNT(DISTINCT symbol_id) AS cnt
                FROM daily_data
            """)
            row_cnt = cur.fetchone()
            total_symbols = row_cnt["cnt"] if row_cnt and row_cnt["cnt"] is not None else 0

            import math
            total_pages = max(1, math.ceil(total_symbols / page_size))
            has_prev = page > 1
            has_next = page < total_pages

        # Sidebar last_update (same for both modes)
        cur.execute("SELECT MAX(date) AS last_date FROM daily_data")
        row_last = cur.fetchone()
        last_update = row_last["last_date"] if row_last and row_last["last_date"] else "Never"

    finally:
        conn.close()

    return render_template(
        "symbols.html",
        symbols=symbols,
        last_update=last_update,
        page=page,
        total_pages=total_pages,
        has_prev=has_prev,
        has_next=has_next,
        q=q,   # pass current search term to template
    )


@app.route("/symbols/<symbol>/history")
def symbol_history(symbol):
    conn = get_db_connection()
    if not conn:
        return "Database not available", 500

    try:
        cur = conn.cursor()

        # Find symbol_id
        cur.execute("""
            SELECT id, base_asset, quote_asset, is_active
            FROM cryptocurrencies
            WHERE symbol = ?
        """, (symbol,))
        sym_row = cur.fetchone()
        if not sym_row:
            # also get last_update for sidebar
            cur.execute("SELECT MAX(date) AS last_date FROM daily_data")
            row_last = cur.fetchone()
            last_update = row_last["last_date"] if row_last and row_last["last_date"] else "Never"

            conn.close()
            return render_template(
                "symbol_history.html",
                symbol=symbol,
                history=[],
                last_update=last_update,
                not_found=True,
                meta=None,
            )

        symbol_id = sym_row["id"]
        meta = {
            "base_asset": sym_row["base_asset"],
            "quote_asset": sym_row["quote_asset"],
            "is_active": sym_row["is_active"],
        }

        # Fetch full daily history for that symbol
        cur.execute("""
            SELECT
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
            FROM daily_data
            WHERE symbol_id = ?
            ORDER BY date
        """, (symbol_id,))
        history = cur.fetchall()

        # Sidebar last_update
        cur.execute("SELECT MAX(date) AS last_date FROM daily_data")
        row_last = cur.fetchone()
        last_update = row_last["last_date"] if row_last and row_last["last_date"] else "Never"

    finally:
        conn.close()

    return render_template(
        "symbol_history.html",
        symbol=symbol,
        history=history,
        last_update=last_update,
        not_found=False,
        meta=meta,
    )


@app.route("/symbols/<symbol>/technical")
def symbol_technical(symbol):
    conn = get_db_connection()
    if not conn:
        return "Database not available", 500

    try:
        cur = conn.cursor()

        # Find symbol_id from cryptocurrencies
        cur.execute(
            "SELECT id FROM cryptocurrencies WHERE symbol = ?",
            (symbol,),
        )
        row = cur.fetchone()
        if not row:
            conn.close()
            return f"No such symbol in database: {symbol}", 404

        symbol_id = row["id"]

        # Pull technical indicators for that symbol_id
        cur.execute("""
            SELECT
                date,
                timeframe,
                rsi,
                macd,
                macd_signal,
                macd_hist,
                stoch_k,
                stoch_d,
                adx,
                cci,
                sma,
                ema,
                wma,
                bb_middle,
                bb_upper,
                bb_lower,
                vol_sma,
                signal
            FROM technical_indicators
            WHERE symbol_id = ?
              AND timeframe = '1D'
            ORDER BY date DESC
            LIMIT 200
        """, (symbol_id,))
        rows = cur.fetchall()

    finally:
        conn.close()

    if not rows:
        message = (
            "No technical indicator data found for this symbol. "
            "Run the technical analysis script to populate the table first."
        )
    else:
        message = None

    return render_template(
        "symbol_technical.html",
        symbol=symbol,
        indicators=rows,
        message=message,
    )


@app.route("/symbols/<symbol>/sentiment")
def symbol_sentiment(symbol):
    """Display sentiment analysis for a symbol"""
    conn = get_db_connection()
    if not conn:
        return "Database not available", 500
    
    try:
        cur = conn.cursor()
        
        # Get symbol info
        cur.execute("""
            SELECT id, base_asset, quote_asset
            FROM cryptocurrencies
            WHERE symbol = ?
        """, (symbol,))
        sym = cur.fetchone()
        if not sym:
            return f"Symbol {symbol} not found", 404
        
        symbol_id = sym["id"]
        
        # Get latest sentiment analysis
        cur.execute("""
            SELECT *
            FROM sentiment_analysis
            WHERE symbol_id = ?
            ORDER BY analysis_date DESC
            LIMIT 1
        """, (symbol_id,))
        sentiment = cur.fetchone()
        
        # Get sentiment history for chart
        cur.execute("""
            SELECT analysis_date, overall_sentiment_score, sentiment_signal
            FROM sentiment_analysis
            WHERE symbol_id = ?
            ORDER BY analysis_date DESC
            LIMIT 30
        """, (symbol_id,))
        sentiment_history = cur.fetchall()
        
        # Get recent sentiment summary (last 7 days)
        cur.execute("""
            SELECT analysis_date AS date,
                   news_positive_count,
                   news_negative_count,
                   news_neutral_count
            FROM sentiment_analysis
            WHERE symbol_id = ?
            ORDER BY analysis_date DESC
            LIMIT 7
        """, (symbol_id,))
        recent_sentiment = cur.fetchall()
        
    finally:
        conn.close()
    
    return render_template(
        "symbol_sentiment.html",
        symbol=symbol,
        base_asset=sym["base_asset"],
        quote_asset=sym["quote_asset"],
        sentiment=sentiment,
        sentiment_history=sentiment_history,
        recent_sentiment=recent_sentiment
    )


@app.route("/symbols/<symbol>/lstm")
def symbol_lstm(symbol):
    conn = get_db_connection()
    if not conn:
        return "Database not available", 500

    try:
        cur = conn.cursor()

        # Find the symbol_id, base and quote
        cur.execute("""
            SELECT id, base_asset, quote_asset
            FROM cryptocurrencies
            WHERE symbol = ?
        """, (symbol,))
        sym = cur.fetchone()
        if not sym:
            return f"Symbol {symbol} not found", 404

        symbol_id = sym["id"]

        # Load LSTM prediction rows for that symbol
        cur.execute("""
            SELECT
                prediction_date,
                timeframe,
                horizon_days,
                lookback_days,
                predicted_close,
                rmse,
                mape,
                r2,
                model_name,
                created_at
            FROM lstm_predictions
            WHERE symbol_id = ?
            ORDER BY prediction_date DESC
            LIMIT 300
        """, (symbol_id,))
        predictions = cur.fetchall()

    finally:
        conn.close()

    return render_template(
        "symbol_lstm.html",
        symbol=symbol,
        base_asset=sym["base_asset"],
        quote_asset=sym["quote_asset"],
        predictions=predictions,
    )




if __name__ == "__main__":

    print("LIVE CRYPTO DASHBOARD - REAL DATA FROM YOUR DATABASE")

    if DB_PATH:
        print(f"Database found at: {DB_PATH}")

        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) AS count FROM cryptocurrencies")
            symbol_count = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) AS count FROM daily_data")
            data_count = cur.fetchone()["count"]

            cur.execute("SELECT MIN(date) AS min_date, MAX(date) AS max_date FROM daily_data")
            date_range = cur.fetchone()
            conn.close()

            print("Database Stats:")
            print(f"   • Total Symbols: {symbol_count}")
            print(f"   • Total Data Points: {data_count}")
            if date_range["min_date"] and date_range["max_date"]:
                print(f"   • Date Range: {date_range['min_date']} to {date_range['max_date']}")
    else:
        print("Database not found - Dashboard will show error message")

    print("\nStarting dashboard at: http://localhost:5000")

    app.run(debug=True, port=5000, threaded=True)
