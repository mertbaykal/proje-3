# [file name]: simple_sentiment.py
# [file content begin]
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import re
from collections import Counter

class SimpleSentimentAnalyzer:
    """
    Basit keyword-based sentiment analyzer.
    Büyük kütüphanelere ihtiyaç duymaz.
    """
    
    def __init__(self):
        # Cryptocurrency-specific sentiment dictionaries
        self.positive_words = {
            'bull', 'bullish', 'moon', 'lambo', 'rocket', '🚀', 'pump',
            'buy', 'long', 'accumulate', 'hodl', 'diamond', 'hands',
            'green', 'profit', 'gain', 'win', 'success', 'breakout',
            'support', 'resistance', 'uptrend', 'rally', 'surge'
        }
        
        self.negative_words = {
            'bear', 'bearish', 'dump', 'crash', 'rekt', '🔥', 'burn',
            'sell', 'short', 'exit', 'panic', 'fud', 'scam', 'rug',
            'red', 'loss', 'drop', 'decline', 'dip', 'correction',
            'death', 'cross', 'downtrend', 'collapse', 'warning'
        }
        
        # Intensity modifiers
        self.intensifiers = {
            'very': 1.5, 'extremely': 2.0, 'highly': 1.5, 'super': 1.8,
            'mega': 2.0, 'massive': 1.8, 'huge': 1.7, 'big': 1.3,
            'slightly': 0.5, 'somewhat': 0.7, 'moderately': 0.8
        }
        
        # Negation words
        self.negations = {'not', "n't", 'no', 'never', 'none', 'nothing'}
    
    def clean_text(self, text):
        """Clean and tokenize text"""
        if not text:
            return []
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove URLs, mentions, and special characters
        text = re.sub(r'http\S+|@\S+|#\S+', '', text)
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Tokenize
        tokens = text.split()
        
        return tokens
    
    def analyze_sentiment(self, text):
        """Analyze sentiment of a text"""
        tokens = self.clean_text(text)
        
        if not tokens:
            return {'polarity': 0.0, 'label': 'NEUTRAL', 'score': 0.0}
        
        positive_score = 0
        negative_score = 0
        intensity = 1.0
        
        # Check for negations and intensifiers
        for i, token in enumerate(tokens):
            if token in self.intensifiers:
                intensity = self.intensifiers[token]
            elif token in self.negations:
                # If negation found, invert next sentiment word
                if i + 1 < len(tokens):
                    next_word = tokens[i + 1]
                    if next_word in self.positive_words:
                        negative_score += 1 * intensity
                    elif next_word in self.negative_words:
                        positive_score += 1 * intensity
        
        # Count positive and negative words
        for token in tokens:
            if token in self.positive_words:
                positive_score += 1 * intensity
            elif token in self.negative_words:
                negative_score += 1 * intensity
        
        # Calculate polarity (-1 to 1)
        total = positive_score + negative_score
        if total > 0:
            polarity = (positive_score - negative_score) / total
        else:
            polarity = 0.0
        
        # Determine label
        if polarity > 0.2:
            label = 'POSITIVE'
        elif polarity < -0.2:
            label = 'NEGATIVE'
        else:
            label = 'NEUTRAL'
        
        return {
            'polarity': polarity,
            'label': label,
            'score': abs(polarity),
            'positive_words': positive_score,
            'negative_words': negative_score
        }
    
    def analyze_batch(self, texts):
        """Analyze multiple texts"""
        if not texts:
            return {
                'avg_polarity': 0.0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'sentiment_score': 0.0,
                'total': 0
            }
        
        results = []
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        for text in texts:
            sentiment = self.analyze_sentiment(text)
            results.append(sentiment)
            
            if sentiment['label'] == 'POSITIVE':
                positive_count += 1
            elif sentiment['label'] == 'NEGATIVE':
                negative_count += 1
            else:
                neutral_count += 1
        
        # Calculate averages
        avg_polarity = sum(r['polarity'] for r in results) / len(results)
        
        # Composite sentiment score (-1 to 1)
        sentiment_score = (positive_count - negative_count) / len(texts)
        
        return {
            'avg_polarity': avg_polarity,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'sentiment_score': sentiment_score,
            'total': len(texts)
        }


def generate_sample_data(symbol, num_items=100):
    """Generate sample news and social media data"""
    import random
    
    positive_templates = [
        f"{symbol} showing strong bullish momentum",
        f"Experts predict {symbol} will reach new highs",
        f"Major partnership announced for {symbol}",
        f"{symbol} adoption increasing rapidly",
        f"Technical analysis shows {symbol} breakout imminent"
    ]
    
    negative_templates = [
        f"{symbol} facing regulatory challenges",
        f"Market correction affecting {symbol} price",
        f"Security concerns raised about {symbol}",
        f"{symbol} trading volume declining",
        f"Analysts warn about {symbol} volatility"
    ]
    
    neutral_templates = [
        f"{symbol} maintains current trading range",
        f"Development update for {symbol} released",
        f"{symbol} community discusses roadmap",
        f"Market analysis for {symbol} published",
        f"{symbol} shows mixed signals"
    ]
    
    all_templates = positive_templates + negative_templates + neutral_templates
    
    data = []
    for i in range(num_items):
        template = random.choice(all_templates)
        # Add some crypto-specific jargon
        jargon = random.choice(['🚀', 'HODL', 'to the moon', 'buy the dip', 'FUD', 'REKT', ''])
        text = f"{template} {jargon}"
        
        # Random date in last 30 days
        days_ago = random.randint(0, 30)
        date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
        
        data.append({
            'text': text,
            'date': date,
            'source': random.choice(['Twitter', 'Reddit', 'News', 'Telegram']),
            'engagement': random.randint(10, 10000)
        })
    
    return data


def create_sentiment_tables(conn):
    """Create sentiment analysis tables if they don't exist"""
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sentiment_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol_id INTEGER NOT NULL,
            analysis_date TEXT NOT NULL,
            
            -- News/social metrics
            avg_polarity REAL,
            positive_count INTEGER,
            negative_count INTEGER,
            neutral_count INTEGER,
            sentiment_score REAL,
            total_items INTEGER,
            
            -- Signal
            sentiment_signal TEXT,
            
            created_at TEXT NOT NULL,
            
            UNIQUE(symbol_id, analysis_date),
            FOREIGN KEY (symbol_id) REFERENCES cryptocurrencies(id)
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sentiment_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sentiment_id INTEGER NOT NULL,
            text TEXT,
            polarity REAL,
            label TEXT,
            source TEXT,
            engagement INTEGER,
            
            FOREIGN KEY (sentiment_id) REFERENCES sentiment_analysis(id)
        )
    """)
    
    conn.commit()


def analyze_symbol_sentiment(conn, symbol, days=30):
    """Analyze sentiment for a specific symbol"""
    print(f"[Sentiment] Analyzing {symbol}")
    
    # Get symbol ID
    cur = conn.cursor()
    cur.execute("SELECT id FROM cryptocurrencies WHERE symbol = ?", (symbol,))
    row = cur.fetchone()
    if not row:
        print(f"[Sentiment] Symbol {symbol} not found")
        return None
    
    symbol_id = row[0]
    
    # Generate sample data (in real app, fetch from APIs)
    print(f"[Sentiment] Generating sample data for {symbol}")
    sample_data = generate_sample_data(symbol, num_items=200)
    
    # Analyze sentiment
    analyzer = SimpleSentimentAnalyzer()
    texts = [item['text'] for item in sample_data]
    analysis_result = analyzer.analyze_batch(texts)
    
    # Determine signal
    if analysis_result['sentiment_score'] > 0.2:
        signal = 'BULLISH'
    elif analysis_result['sentiment_score'] < -0.2:
        signal = 'BEARISH'
    else:
        signal = 'NEUTRAL'
    
    # Store analysis
    analysis_date = datetime.now().strftime('%Y-%m-%d')
    
    cur.execute("""
        INSERT INTO sentiment_analysis (
            symbol_id, analysis_date,
            avg_polarity, positive_count, negative_count, neutral_count,
            sentiment_score, total_items, sentiment_signal, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol_id, analysis_date) DO UPDATE SET
            avg_polarity = excluded.avg_polarity,
            positive_count = excluded.positive_count,
            negative_count = excluded.negative_count,
            neutral_count = excluded.neutral_count,
            sentiment_score = excluded.sentiment_score,
            total_items = excluded.total_items,
            sentiment_signal = excluded.sentiment_signal,
            created_at = excluded.created_at
    """, (
        symbol_id, analysis_date,
        analysis_result['avg_polarity'],
        analysis_result['positive_count'],
        analysis_result['negative_count'],
        analysis_result['neutral_count'],
        analysis_result['sentiment_score'],
        analysis_result['total'],
        signal,
        datetime.now().isoformat()
    ))
    
    # Get the inserted ID
    cur.execute("SELECT last_insert_rowid()")
    sentiment_id = cur.fetchone()[0]
    
    # Store individual items
    for item in sample_data[:50]:  # Store first 50 items
        sentiment = analyzer.analyze_sentiment(item['text'])
        
        cur.execute("""
            INSERT INTO sentiment_items (
                sentiment_id, text, polarity, label, source, engagement
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            sentiment_id,
            item['text'][:500],  # Limit text length
            sentiment['polarity'],
            sentiment['label'],
            item['source'],
            item['engagement']
        ))
    
    conn.commit()
    
    print(f"[Sentiment] Analysis complete for {symbol}")
    print(f"  Score: {analysis_result['sentiment_score']:.3f}")
    print(f"  Signal: {signal}")
    print(f"  Positive: {analysis_result['positive_count']}")
    print(f"  Negative: {analysis_result['negative_count']}")
    
    return {
        'symbol': symbol,
        'analysis': analysis_result,
        'signal': signal,
        'analysis_date': analysis_date
    }


def get_sentiment_for_symbol(conn, symbol):
    """Get sentiment analysis for a symbol"""
    cur = conn.cursor()
    
    # Get symbol ID
    cur.execute("SELECT id FROM cryptocurrencies WHERE symbol = ?", (symbol,))
    row = cur.fetchone()
    if not row:
        return None
    
    symbol_id = row[0]
    
    # Get latest sentiment analysis
    cur.execute("""
        SELECT * FROM sentiment_analysis
        WHERE symbol_id = ?
        ORDER BY analysis_date DESC
        LIMIT 1
    """, (symbol_id,))
    
    return cur.fetchone()


if __name__ == "__main__":
    # Test the sentiment analyzer
    analyzer = SimpleSentimentAnalyzer()
    
    test_texts = [
        "Bitcoin is going to the moon! 🚀",
        "Market crash incoming, sell everything!",
        "ETH showing strong support at $2000",
        "Not bullish on crypto right now",
        "Very positive developments for ADA"
    ]
    
    for text in test_texts:
        result = analyzer.analyze_sentiment(text)
        print(f"'{text}' -> {result['label']} (score: {result['polarity']:.3f})")
    
    print("\nBatch analysis:")
    batch_result = analyzer.analyze_batch(test_texts)
    print(f"Average polarity: {batch_result['avg_polarity']:.3f}")
    print(f"Sentiment score: {batch_result['sentiment_score']:.3f}")
# [file content end]