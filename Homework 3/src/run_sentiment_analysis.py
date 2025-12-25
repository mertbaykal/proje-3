import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from analysis.simple_sentiment import analyze_symbol_sentiment
    from db import get_connection
except ImportError as e:
    print(f"Import error: {e}")
    print("Trying alternative import...")
    # Try relative import
    from .analysis.simple_sentiment import analyze_symbol_sentiment
    from .db import get_connection

if __name__ == "__main__":
    # Test with a specific symbol
    symbol = "BTCUSDT"  # Change this to any symbol in your database
    
    print(f"Starting sentiment analysis for {symbol}")
    
    conn = get_connection()
    try:
        result = analyze_symbol_sentiment(conn, symbol)
        if result:
            print("\nAnalysis Results:")
            print(f"Symbol: {result['symbol']}")
            print(f"Sentiment Score: {result['analysis']['sentiment_score']:.3f}")
            print(f"Signal: {result['signal']}")
        else:
            print("Analysis failed.")
    except Exception as e:
        print(f"Error during sentiment analysis: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
# [file content end]