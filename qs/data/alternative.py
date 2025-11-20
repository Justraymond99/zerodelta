from __future__ import annotations

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False
    logger.warning("vaderSentiment not available. Sentiment analysis disabled.")

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    logger.warning("feedparser not available. News feeds disabled.")


class NewsSentimentAnalyzer:
    """Analyze news sentiment for symbols."""
    
    def __init__(self):
        if VADER_AVAILABLE:
            self.analyzer = SentimentIntensityAnalyzer()
        else:
            self.analyzer = None
    
    def analyze_text(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of text."""
        if not self.analyzer:
            return {"compound": 0.0, "pos": 0.0, "neu": 0.0, "neg": 0.0}
        
        scores = self.analyzer.polarity_scores(text)
        return {
            "compound": scores["compound"],
            "positive": scores["pos"],
            "neutral": scores["neu"],
            "negative": scores["neg"]
        }
    
    def analyze_news(self, news_items: List[Dict]) -> Dict[str, float]:
        """Analyze sentiment of news items."""
        if not news_items:
            return {"compound": 0.0, "positive": 0.0, "neutral": 0.0, "negative": 0.0}
        
        sentiments = [self.analyze_text(item.get("title", "") + " " + item.get("summary", "")) for item in news_items]
        
        return {
            "compound": sum(s["compound"] for s in sentiments) / len(sentiments),
            "positive": sum(s["positive"] for s in sentiments) / len(sentiments),
            "neutral": sum(s["neutral"] for s in sentiments) / len(sentiments),
            "negative": sum(s["negative"] for s in sentiments) / len(sentiments),
            "count": len(news_items)
        }


def fetch_news_rss(symbol: str, feed_url: Optional[str] = None) -> List[Dict]:
    """Fetch news from RSS feed."""
    if not FEEDPARSER_AVAILABLE:
        return []
    
    # Default to Yahoo Finance RSS
    if not feed_url:
        feed_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
    
    try:
        feed = feedparser.parse(feed_url)
        news_items = []
        
        for entry in feed.entries[:10]:  # Top 10
            news_items.append({
                "title": entry.get("title", ""),
                "summary": entry.get("summary", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "symbol": symbol
            })
        
        return news_items
    except Exception as e:
        logger.error(f"Error fetching news for {symbol}: {e}")
        return []


def get_news_sentiment(symbol: str) -> Dict:
    """Get news sentiment for a symbol."""
    news_items = fetch_news_rss(symbol)
    
    if not news_items:
        return {
            "symbol": symbol,
            "sentiment": {"compound": 0.0, "positive": 0.0, "neutral": 0.0, "negative": 0.0, "count": 0},
            "news_count": 0
        }
    
    analyzer = NewsSentimentAnalyzer()
    sentiment = analyzer.analyze_news(news_items)
    
    return {
        "symbol": symbol,
        "sentiment": sentiment,
        "news_count": len(news_items),
        "timestamp": datetime.now().isoformat()
    }


def fetch_economic_indicators() -> pd.DataFrame:
    """Fetch economic indicators (placeholder - would use FRED API or similar)."""
    # This is a placeholder - in production, use FRED API or similar
    indicators = [
        {"indicator": "GDP", "value": 0.0, "date": datetime.now().date()},
        {"indicator": "Unemployment", "value": 0.0, "date": datetime.now().date()},
        {"indicator": "CPI", "value": 0.0, "date": datetime.now().date()},
    ]
    return pd.DataFrame(indicators)


def get_alternative_data_features(symbol: str) -> Dict:
    """Get all alternative data features for a symbol."""
    features = {
        "symbol": symbol,
        "timestamp": datetime.now().isoformat()
    }
    
    # News sentiment
    news_data = get_news_sentiment(symbol)
    features["news_sentiment"] = news_data["sentiment"]
    features["news_count"] = news_data["news_count"]
    
    # Economic indicators (would be symbol-agnostic)
    # features["economic_indicators"] = fetch_economic_indicators().to_dict(orient="records")
    
    return features

