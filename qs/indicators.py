from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Optional


def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index (RSI).
    
    Parameters:
    -----------
    prices : pd.Series
        Price series
    period : int
        Period for RSI calculation (default: 14)
    
    Returns:
    --------
    pd.Series
        RSI values (0-100)
    """
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def macd(
    prices: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> pd.DataFrame:
    """
    Moving Average Convergence Divergence (MACD).
    
    Parameters:
    -----------
    prices : pd.Series
        Price series
    fast : int
        Fast EMA period (default: 12)
    slow : int
        Slow EMA period (default: 26)
    signal : int
        Signal line EMA period (default: 9)
    
    Returns:
    --------
    pd.DataFrame
        Columns: macd, signal, histogram
    """
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return pd.DataFrame({
        'macd': macd_line,
        'signal': signal_line,
        'histogram': histogram
    })


def bollinger_bands(
    prices: pd.Series,
    period: int = 20,
    std_dev: float = 2.0
) -> pd.DataFrame:
    """
    Bollinger Bands.
    
    Parameters:
    -----------
    prices : pd.Series
        Price series
    period : int
        Moving average period (default: 20)
    std_dev : float
        Number of standard deviations (default: 2.0)
    
    Returns:
    --------
    pd.DataFrame
        Columns: middle, upper, lower, bandwidth
    """
    middle = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    bandwidth = (upper - lower) / middle
    
    return pd.DataFrame({
        'middle': middle,
        'upper': upper,
        'lower': lower,
        'bandwidth': bandwidth
    })


def adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    Average Directional Index (ADX).
    
    Parameters:
    -----------
    high : pd.Series
        High prices
    low : pd.Series
        Low prices
    close : pd.Series
        Close prices
    period : int
        Period for ADX calculation (default: 14)
    
    Returns:
    --------
    pd.Series
        ADX values (0-100)
    """
    # Calculate True Range
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Calculate Directional Movement
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    # Smooth the values
    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    # Calculate ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    
    return adx


def stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3
) -> pd.DataFrame:
    """
    Stochastic Oscillator (%K and %D).
    
    Parameters:
    -----------
    high : pd.Series
        High prices
    low : pd.Series
        Low prices
    close : pd.Series
        Close prices
    k_period : int
        %K period (default: 14)
    d_period : int
        %D smoothing period (default: 3)
    
    Returns:
    --------
    pd.DataFrame
        Columns: k, d
    """
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    
    k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    d = k.rolling(window=d_period).mean()
    
    return pd.DataFrame({
        'k': k,
        'd': d
    })


def atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    Average True Range (ATR).
    
    Parameters:
    -----------
    high : pd.Series
        High prices
    low : pd.Series
        Low prices
    close : pd.Series
        Close prices
    period : int
        Period for ATR calculation (default: 14)
    
    Returns:
    --------
    pd.Series
        ATR values
    """
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    On-Balance Volume (OBV).
    
    Parameters:
    -----------
    close : pd.Series
        Close prices
    volume : pd.Series
        Volume series
    
    Returns:
    --------
    pd.Series
        OBV values
    """
    obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
    return obv


def williams_r(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    Williams %R.
    
    Parameters:
    -----------
    high : pd.Series
        High prices
    low : pd.Series
        Low prices
    close : pd.Series
        Close prices
    period : int
        Period for calculation (default: 14)
    
    Returns:
    --------
    pd.Series
        Williams %R values (-100 to 0)
    """
    highest_high = high.rolling(window=period).max()
    lowest_low = low.rolling(window=period).min()
    wr = -100 * ((highest_high - close) / (highest_high - lowest_low))
    return wr


def cci(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 20
) -> pd.Series:
    """
    Commodity Channel Index (CCI).
    
    Parameters:
    -----------
    high : pd.Series
        High prices
    low : pd.Series
        Low prices
    close : pd.Series
        Close prices
    period : int
        Period for calculation (default: 20)
    
    Returns:
    --------
    pd.Series
        CCI values
    """
    tp = (high + low + close) / 3
    sma = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
    cci = (tp - sma) / (0.015 * mad)
    return cci


def ema(prices: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return prices.ewm(span=period, adjust=False).mean()


def sma(prices: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return prices.rolling(window=period).mean()

