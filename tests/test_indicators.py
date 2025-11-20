import pytest
import pandas as pd
import numpy as np
from qs.indicators import rsi, macd, bollinger_bands, adx, stochastic, atr


def test_rsi():
    """Test RSI calculation."""
    prices = pd.Series([100, 102, 101, 103, 105, 104, 106] * 10)
    rsi_values = rsi(prices, period=14)
    assert len(rsi_values) == len(prices)
    assert all(0 <= val <= 100 or pd.isna(val) for val in rsi_values)


def test_macd():
    """Test MACD calculation."""
    prices = pd.Series([100, 102, 101, 103, 105, 104, 106] * 20)
    macd_df = macd(prices)
    assert 'macd' in macd_df.columns
    assert 'signal' in macd_df.columns
    assert 'histogram' in macd_df.columns
    assert len(macd_df) == len(prices)


def test_bollinger_bands():
    """Test Bollinger Bands calculation."""
    prices = pd.Series([100, 102, 101, 103, 105, 104, 106] * 10)
    bb_df = bollinger_bands(prices, period=20)
    assert 'upper' in bb_df.columns
    assert 'lower' in bb_df.columns
    assert 'middle' in bb_df.columns
    # Upper should be >= middle >= lower
    assert all(bb_df['upper'] >= bb_df['middle'])
    assert all(bb_df['middle'] >= bb_df['lower'])


def test_atr():
    """Test ATR calculation."""
    high = pd.Series([102, 103, 104, 105, 106])
    low = pd.Series([100, 101, 102, 103, 104])
    close = pd.Series([101, 102, 103, 104, 105])
    atr_values = atr(high, low, close, period=14)
    assert len(atr_values) == len(high)
    assert all(val >= 0 or pd.isna(val) for val in atr_values)

