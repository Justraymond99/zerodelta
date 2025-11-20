from __future__ import annotations

import pandas as pd
from typing import Literal


def resample_prices(
    df: pd.DataFrame,
    timeframe: Literal["1H", "4H", "1D", "1W", "1M"],
    price_col: str = "adj_close"
) -> pd.DataFrame:
    """
    Resample price data to different timeframes.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with datetime index and price columns
    timeframe : str
        Target timeframe: "1H", "4H", "1D", "1W", "1M"
    price_col : str
        Price column name
    
    Returns:
    --------
    pd.DataFrame
        Resampled data
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' in df.columns:
            df = df.set_index('date')
        else:
            raise ValueError("DataFrame must have datetime index or 'date' column")
    
    # Map timeframe to pandas frequency
    freq_map = {
        "1H": "1H",
        "4H": "4H",
        "1D": "1D",
        "1W": "W",
        "1M": "M"
    }
    
    if timeframe not in freq_map:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    
    freq = freq_map[timeframe]
    
    # Resample OHLCV data
    if all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume']):
        resampled = pd.DataFrame()
        resampled['open'] = df['open'].resample(freq).first()
        resampled['high'] = df['high'].resample(freq).max()
        resampled['low'] = df['low'].resample(freq).min()
        resampled['close'] = df['close'].resample(freq).last()
        if 'adj_close' in df.columns:
            resampled['adj_close'] = df['adj_close'].resample(freq).last()
        resampled['volume'] = df['volume'].resample(freq).sum()
        return resampled.dropna()
    else:
        # Simple resampling for single price column
        return df[price_col].resample(freq).last().to_frame().dropna()


def multi_timeframe_features(
    df: pd.DataFrame,
    timeframes: list[Literal["1H", "4H", "1D", "1W", "1M"]],
    price_col: str = "adj_close"
) -> pd.DataFrame:
    """
    Calculate features across multiple timeframes.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Price data
    timeframes : list
        List of timeframes to analyze
    price_col : str
        Price column name
    
    Returns:
    --------
    pd.DataFrame
        Features across timeframes
    """
    features_list = []
    
    for tf in timeframes:
        resampled = resample_prices(df, tf, price_col)
        
        if len(resampled) > 0:
            returns = resampled[price_col].pct_change()
            
            features_list.append({
                'timeframe': tf,
                'mean_return': returns.mean(),
                'volatility': returns.std(),
                'sharpe': returns.mean() / returns.std() if returns.std() > 0 else 0,
                'max_drawdown': (resampled[price_col] / resampled[price_col].cummax() - 1).min()
            })
    
    return pd.DataFrame(features_list)

