from __future__ import annotations

import asyncio
import json
from typing import Dict, Set, List
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from ..db import get_engine
from sqlalchemy import text
import pandas as pd
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[WebSocket, Set[str]] = {}  # websocket -> set of symbols
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.subscriptions[websocket] = set()
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connections."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting: {e}")
                disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_to_subscribers(self, symbol: str, message: dict):
        """Broadcast message to subscribers of a symbol."""
        disconnected = []
        for connection, subscribed_symbols in self.subscriptions.items():
            if symbol in subscribed_symbols:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to subscriber: {e}")
                    disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)
    
    def subscribe(self, websocket: WebSocket, symbol: str):
        """Subscribe to symbol updates."""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].add(symbol)
            logger.info(f"Subscribed to {symbol}")
    
    def unsubscribe(self, websocket: WebSocket, symbol: str):
        """Unsubscribe from symbol updates."""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].discard(symbol)
            logger.info(f"Unsubscribed from {symbol}")


# Global connection manager
manager = ConnectionManager()


async def stream_prices(symbols: List[str], interval: int = 1):
    """
    Stream price updates for symbols.
    
    Parameters:
    -----------
    symbols : list
        List of symbols to stream
    interval : int
        Update interval in seconds
    """
    engine = get_engine()
    
    while True:
        try:
            with engine.begin() as conn:
                # Get latest prices
                placeholders = ",".join([f":sym{i}" for i in range(len(symbols))])
                params = {f"sym{i}": sym for i, sym in enumerate(symbols)}
                
                prices_df = pd.read_sql(
                    text(f"""
                        SELECT symbol, date, adj_close, volume
                        FROM prices
                        WHERE symbol IN ({placeholders})
                        AND date = (SELECT MAX(date) FROM prices WHERE symbol IN ({placeholders}))
                    """),
                    conn,
                    params={**params, **{f"sym{i}_2": sym for i, sym in enumerate(symbols)}}
                )
            
            # Send updates to subscribers
            for _, row in prices_df.iterrows():
                message = {
                    "type": "price_update",
                    "symbol": row['symbol'],
                    "price": float(row['adj_close']),
                    "volume": int(row['volume']),
                    "timestamp": datetime.now().isoformat()
                }
                await manager.broadcast_to_subscribers(row['symbol'], message)
            
            await asyncio.sleep(interval)
        
        except Exception as e:
            logger.error(f"Error in price streaming: {e}")
            await asyncio.sleep(interval)


async def stream_signals(signal_name: str = "xgb_alpha", interval: int = 60):
    """Stream signal updates."""
    engine = get_engine()
    
    while True:
        try:
            with engine.begin() as conn:
                signals_df = pd.read_sql(
                    text("""
                        SELECT s.symbol, s.score, p.adj_close as price
                        FROM signals s
                        JOIN prices p ON s.symbol = p.symbol AND s.date = p.date
                        WHERE s.signal_name = :name
                        AND s.date = (SELECT MAX(date) FROM signals WHERE signal_name = :name)
                        ORDER BY s.score DESC
                        LIMIT 10
                    """),
                    conn,
                    params={"name": signal_name}
                )
            
            message = {
                "type": "signal_update",
                "signal_name": signal_name,
                "signals": signals_df.to_dict(orient="records"),
                "timestamp": datetime.now().isoformat()
            }
            
            await manager.broadcast(message)
            await asyncio.sleep(interval)
        
        except Exception as e:
            logger.error(f"Error in signal streaming: {e}")
            await asyncio.sleep(interval)

