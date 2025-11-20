from __future__ import annotations

import os
import asyncio
from typing import Dict, Optional, Callable
from datetime import datetime
import pandas as pd
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Try to import real-time data providers
POLYGON_AVAILABLE = False
ALPACA_AVAILABLE = False

try:
    from polygon import RESTClient as PolygonClient
    POLYGON_AVAILABLE = True
except ImportError:
    logger.warning("polygon package not installed. Install with: pip install polygon-api-client")

try:
    import alpaca_trade_api as alpaca
    ALPACA_AVAILABLE = True
except ImportError:
    logger.warning("alpaca-trade-api not installed. Install with: pip install alpaca-trade-api")


class RealTimeDataProvider:
    """Real-time market data provider interface."""
    
    def __init__(self, provider: str = "polygon"):
        self.provider = provider.lower()
        self.client = None
        self._setup_client()
    
    def _setup_client(self):
        """Setup the data provider client."""
        if self.provider == "polygon" and POLYGON_AVAILABLE:
            api_key = os.getenv("POLYGON_API_KEY")
            if api_key:
                self.client = PolygonClient(api_key)
                logger.info("Polygon client initialized")
            else:
                logger.warning("POLYGON_API_KEY not set")
        elif self.provider == "alpaca" and ALPACA_AVAILABLE:
            api_key = os.getenv("ALPACA_API_KEY")
            api_secret = os.getenv("ALPACA_API_SECRET")
            base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
            if api_key and api_secret:
                self.client = alpaca.REST(api_key, api_secret, base_url, api_version='v2')
                logger.info("Alpaca client initialized")
            else:
                logger.warning("ALPACA_API_KEY or ALPACA_API_SECRET not set")
        else:
            logger.warning(f"Provider {self.provider} not available or not configured")
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price for a symbol."""
        if not self.client:
            return None
        
        try:
            if self.provider == "polygon":
                # Polygon API
                ticker = self.client.get_ticker_details(symbol)
                if ticker:
                    return float(ticker.last_quote.get('p', 0))
            elif self.provider == "alpaca":
                # Alpaca API
                quote = self.client.get_latest_quote(symbol)
                if quote:
                    return float((quote.bp + quote.ap) / 2)  # Mid price
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
        
        return None
    
    def get_latest_bar(self, symbol: str) -> Optional[Dict]:
        """Get latest bar (OHLCV) for a symbol."""
        if not self.client:
            return None
        
        try:
            if self.provider == "polygon":
                bars = self.client.get_aggs(
                    symbol,
                    1,
                    "minute",
                    limit=1
                )
                if bars and len(bars) > 0:
                    bar = bars[0]
                    return {
                        'open': float(bar.open),
                        'high': float(bar.high),
                        'low': float(bar.low),
                        'close': float(bar.close),
                        'volume': int(bar.volume),
                        'timestamp': datetime.fromtimestamp(bar.timestamp / 1000)
                    }
            elif self.provider == "alpaca":
                bars = self.client.get_bars(symbol, "1Min", limit=1).df
                if not bars.empty:
                    bar = bars.iloc[-1]
                    return {
                        'open': float(bar['open']),
                        'high': float(bar['high']),
                        'low': float(bar['low']),
                        'close': float(bar['close']),
                        'volume': int(bar['volume']),
                        'timestamp': bar.name
                    }
        except Exception as e:
            logger.error(f"Error getting bar for {symbol}: {e}")
        
        return None
    
    def stream_prices(self, symbols: list[str], callback: Callable):
        """Stream real-time prices (WebSocket)."""
        if not self.client:
            logger.warning("Client not initialized for streaming")
            return
        
        # This would require WebSocket implementation
        # Placeholder for now
        logger.info(f"Streaming prices for {len(symbols)} symbols")


class RealTimeDataManager:
    """Manages real-time data feeds."""
    
    def __init__(self, provider: str = "polygon"):
        self.provider = RealTimeDataProvider(provider)
        self.cache: Dict[str, Dict] = {}
        self.last_update: Dict[str, datetime] = {}
    
    def get_price(self, symbol: str, use_cache: bool = True, cache_ttl: int = 1) -> Optional[float]:
        """Get latest price with optional caching."""
        now = datetime.now()
        
        if use_cache and symbol in self.cache:
            last_update = self.last_update.get(symbol)
            if last_update and (now - last_update).seconds < cache_ttl:
                return self.cache[symbol].get('price')
        
        price = self.provider.get_latest_price(symbol)
        if price:
            self.cache[symbol] = {'price': price, 'timestamp': now}
            self.last_update[symbol] = now
        
        return price
    
    def get_bar(self, symbol: str) -> Optional[Dict]:
        """Get latest bar data."""
        return self.provider.get_latest_bar(symbol)
    
    def update_cache(self, symbol: str, price: float):
        """Manually update cache (e.g., from WebSocket)."""
        self.cache[symbol] = {'price': price, 'timestamp': datetime.now()}
        self.last_update[symbol] = datetime.now()


# Global instance
_realtime_manager: Optional[RealTimeDataManager] = None


def get_realtime_manager() -> RealTimeDataManager:
    """Get global real-time data manager."""
    global _realtime_manager
    if _realtime_manager is None:
        provider = os.getenv("REALTIME_DATA_PROVIDER", "polygon")
        _realtime_manager = RealTimeDataManager(provider)
    return _realtime_manager

