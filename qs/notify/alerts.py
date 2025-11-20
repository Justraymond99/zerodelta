from __future__ import annotations

import pandas as pd
from datetime import datetime, date
from typing import Dict, List, Optional

try:
    from .twilio_client import send_sms_update, get_allowed_numbers
    HAS_TWILIO = True
except ImportError:
    HAS_TWILIO = False
    def send_sms_update(*args, **kwargs):
        pass
    def get_allowed_numbers(*args, **kwargs):
        return []
from ..options import black_scholes, implied_volatility, calculate_historical_volatility
from ..db import get_engine
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError, OperationalError
from ..utils.logger import get_logger

logger = get_logger(__name__)


def check_options_anomalies(
    symbol: str,
    strike: float,
    expiry_days: int,
    market_price: float,
    option_type: str = "call",
    threshold: float = 0.20
) -> Optional[Dict]:
    """
    Check for options pricing anomalies.
    
    Parameters:
    -----------
    symbol : str
        Stock symbol
    strike : float
        Strike price
    expiry_days : int
        Days to expiration
    market_price : float
        Market option price
    option_type : str
        "call" or "put"
    threshold : float
        Price difference threshold (20% default)
    
    Returns:
    --------
    dict or None
        Anomaly details if found
    """
    try:
        # Get current stock price
        engine = get_engine()
        try:
            with engine.begin() as conn:
                result = conn.execute(
                    text("SELECT adj_close FROM prices WHERE symbol = :sym ORDER BY date DESC LIMIT 1"),
                    {"sym": symbol}
                ).fetchone()
        except (ProgrammingError, OperationalError) as e:
            error_msg = str(e).lower()
            if "table" in error_msg and "does not exist" in error_msg:
                logger.debug(f"Prices table does not exist yet for {symbol}")
                return None
            raise
        
        if not result:
            return None
        
        S = float(result[0])
        T = expiry_days / 365.0
        r = 0.05  # Default risk-free rate
        
        # Calculate historical volatility
        hist_vol = calculate_historical_volatility(symbol, days=30, engine=engine)
        if not hist_vol:
            return None
        
        # Calculate theoretical price
        theoretical_price = black_scholes(S, strike, T, r, hist_vol, option_type)
        
        # Calculate implied volatility
        iv = implied_volatility(market_price, S, strike, T, r, option_type)
        
        if not iv:
            return None
        
        # Check for anomalies
        price_diff_pct = abs(market_price - theoretical_price) / theoretical_price if theoretical_price > 0 else 0
        vol_diff_pct = abs(iv - hist_vol) / hist_vol if hist_vol > 0 else 0
        
        if price_diff_pct > threshold or vol_diff_pct > threshold:
            return {
                'symbol': symbol,
                'strike': strike,
                'expiry_days': expiry_days,
                'option_type': option_type,
                'market_price': market_price,
                'theoretical_price': theoretical_price,
                'price_diff_pct': price_diff_pct,
                'implied_vol': iv,
                'historical_vol': hist_vol,
                'vol_diff_pct': vol_diff_pct,
                'anomaly_type': 'price' if price_diff_pct > threshold else 'volatility'
            }
    
    except Exception as e:
        logger.error(f"Error checking options anomaly for {symbol}: {e}")
    
    return None


def check_buy_signals(
    signal_name: str = "xgb_alpha",
    threshold: float = 0.7,
    top_n: int = 5
) -> List[Dict]:
    """
    Check for strong buy signals.
    
    Parameters:
    -----------
    signal_name : str
        Signal name
    threshold : float
        Signal score threshold
    top_n : int
        Number of top signals to return
    
    Returns:
    --------
    list
        List of buy signals
    """
    engine = get_engine()
    
    try:
        with engine.begin() as conn:
            # Get latest signals
            signals_df = pd.read_sql(
                text("""
                    SELECT s.symbol, s.score, p.adj_close as price
                    FROM signals s
                    JOIN prices p ON s.symbol = p.symbol AND s.date = p.date
                    WHERE s.signal_name = :name
                    AND s.date = (SELECT MAX(date) FROM signals WHERE signal_name = :name)
                    AND s.score > :threshold
                    ORDER BY s.score DESC
                    LIMIT :top_n
                """),
                conn,
                params={"name": signal_name, "threshold": threshold, "top_n": top_n}
            )
        
        buy_signals = []
        for _, row in signals_df.iterrows():
            buy_signals.append({
                'symbol': row['symbol'],
                'score': float(row['score']),
                'price': float(row['price']),
                'signal_type': 'BUY'
            })
        
        return buy_signals
    
    except Exception as e:
        logger.error(f"Error checking buy signals: {e}")
        return []


def check_sell_signals(
    signal_name: str = "xgb_alpha",
    threshold: float = -0.3,
    top_n: int = 5
) -> List[Dict]:
    """
    Check for sell signals.
    
    Parameters:
    -----------
    signal_name : str
        Signal name
    threshold : float
        Signal score threshold (negative)
    top_n : int
        Number of signals to return
    
    Returns:
    --------
    list
        List of sell signals
    """
    engine = get_engine()
    
    try:
        with engine.begin() as conn:
            signals_df = pd.read_sql(
                text("""
                    SELECT s.symbol, s.score, p.adj_close as price
                    FROM signals s
                    JOIN prices p ON s.symbol = p.symbol AND s.date = p.date
                    WHERE s.signal_name = :name
                    AND s.date = (SELECT MAX(date) FROM signals WHERE signal_name = :name)
                    AND s.score < :threshold
                    ORDER BY s.score ASC
                    LIMIT :top_n
                """),
                conn,
                params={"name": signal_name, "threshold": threshold, "top_n": top_n}
            )
        
        sell_signals = []
        for _, row in signals_df.iterrows():
            sell_signals.append({
                'symbol': row['symbol'],
                'score': float(row['score']),
                'price': float(row['price']),
                'signal_type': 'SELL'
            })
        
        return sell_signals
    
    except Exception as e:
        logger.error(f"Error checking sell signals: {e}")
        return []


def send_trading_alerts(
    check_options: bool = True,
    check_signals: bool = True,
    options_threshold: float = 0.20,
    signal_threshold: float = 0.7
) -> int:
    """
    Send trading alerts via SMS.
    
    Parameters:
    -----------
    check_options : bool
        Check for options anomalies
    check_signals : bool
        Check for buy/sell signals
    options_threshold : float
        Options anomaly threshold
    signal_threshold : float
        Signal threshold
    
    Returns:
    --------
    int
        Number of alerts sent
    """
    alerts_sent = 0
    messages = []
    
    # Check buy signals
    if check_signals:
        buy_signals = check_buy_signals(threshold=signal_threshold)
        if buy_signals:
            msg = "🔥 BUY SIGNALS:\n"
            for signal in buy_signals[:3]:  # Top 3
                msg += f"{signal['symbol']} @ ${signal['price']:.2f} (score: {signal['score']:.2f})\n"
            messages.append(msg)
            alerts_sent += 1
        
        # Check sell signals
        sell_signals = check_sell_signals(threshold=-signal_threshold)
        if sell_signals:
            msg = "📉 SELL SIGNALS:\n"
            for signal in sell_signals[:3]:  # Top 3
                msg += f"{signal['symbol']} @ ${signal['price']:.2f} (score: {signal['score']:.2f})\n"
            messages.append(msg)
            alerts_sent += 1
    
    # Check options anomalies (example - would need options data source)
    # This is a placeholder - in practice, you'd fetch options chain data
    if check_options:
        # Example: Check for anomalies in known options
        # In real implementation, you'd iterate through options chain
        pass
    
    # Send all messages
    for msg in messages:
        send_sms_update(msg)
    
    return alerts_sent


def format_options_anomaly_alert(anomaly: Dict) -> str:
    """Format options anomaly alert message."""
    msg = f"⚠️ OPTIONS ANOMALY: {anomaly['symbol']}\n"
    msg += f"{anomaly['option_type'].upper()} K={anomaly['strike']:.0f} T={anomaly['expiry_days']}d\n"
    msg += f"Market: ${anomaly['market_price']:.2f}\n"
    msg += f"Theoretical: ${anomaly['theoretical_price']:.2f}\n"
    msg += f"Diff: {anomaly['price_diff_pct']*100:.1f}%\n"
    msg += f"IV: {anomaly['implied_vol']*100:.1f}% vs Hist: {anomaly['historical_vol']*100:.1f}%"
    return msg


def format_buy_alert(signals: List[Dict]) -> str:
    """Format buy signal alert message."""
    msg = "🔥 STRONG BUY SIGNALS:\n"
    for signal in signals:
        msg += f"{signal['symbol']} @ ${signal['price']:.2f} (score: {signal['score']:.2f})\n"
    return msg


def format_sell_alert(signals: List[Dict]) -> str:
    """Format sell signal alert message."""
    msg = "📉 SELL SIGNALS:\n"
    for signal in signals:
        msg += f"{signal['symbol']} @ ${signal['price']:.2f} (score: {signal['score']:.2f})\n"
    return msg

