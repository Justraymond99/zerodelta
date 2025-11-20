from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Dict, List
from .db import get_engine
from sqlalchemy import text
from ..utils.logger import get_logger

logger = get_logger(__name__)


def validate_prices(df: pd.DataFrame) -> Dict[str, List[str]]:
    """
    Validate price data quality.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Price dataframe with columns: symbol, date, open, high, low, close, adj_close, volume
    
    Returns:
    --------
    dict
        Dictionary with validation results: {'errors': [...], 'warnings': [...]}
    """
    errors = []
    warnings = []
    
    if df.empty:
        errors.append("Dataframe is empty")
        return {'errors': errors, 'warnings': warnings}
    
    # Check required columns
    required_cols = ['symbol', 'date', 'open', 'high', 'low', 'close', 'adj_close', 'volume']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")
        return {'errors': errors, 'warnings': warnings}
    
    # Check for missing values
    for col in ['open', 'high', 'low', 'close', 'adj_close']:
        missing = df[col].isna().sum()
        if missing > 0:
            warnings.append(f"Column {col} has {missing} missing values")
    
    # Check price relationships: high >= low, high >= open, high >= close, etc.
    invalid_high_low = (df['high'] < df['low']).sum()
    if invalid_high_low > 0:
        errors.append(f"{invalid_high_low} rows where high < low")
    
    invalid_high_open = (df['high'] < df['open']).sum()
    if invalid_high_open > 0:
        warnings.append(f"{invalid_high_open} rows where high < open")
    
    invalid_high_close = (df['high'] < df['close']).sum()
    if invalid_high_close > 0:
        warnings.append(f"{invalid_high_close} rows where high < close")
    
    invalid_low_open = (df['low'] > df['open']).sum()
    if invalid_low_open > 0:
        warnings.append(f"{invalid_low_open} rows where low > open")
    
    invalid_low_close = (df['low'] > df['close']).sum()
    if invalid_low_close > 0:
        warnings.append(f"{invalid_low_close} rows where low > close")
    
    # Check for negative prices
    price_cols = ['open', 'high', 'low', 'close', 'adj_close']
    for col in price_cols:
        negative = (df[col] <= 0).sum()
        if negative > 0:
            errors.append(f"Column {col} has {negative} non-positive values")
    
    # Check for negative volume
    negative_volume = (df['volume'] < 0).sum()
    if negative_volume > 0:
        errors.append(f"Volume has {negative_volume} negative values")
    
    # Check for outliers (prices that change by more than 50% in one day)
    if 'adj_close' in df.columns:
        returns = df.groupby('symbol')['adj_close'].pct_change()
        extreme_returns = (returns.abs() > 0.5).sum()
        if extreme_returns > 0:
            warnings.append(f"{extreme_returns} days with returns > 50% (possible data errors)")
    
    # Check for duplicate dates per symbol
    duplicates = df.groupby('symbol')['date'].duplicated().sum()
    if duplicates > 0:
        errors.append(f"{duplicates} duplicate date entries per symbol")
    
    return {'errors': errors, 'warnings': warnings}


def validate_database() -> Dict[str, any]:
    """
    Validate database data quality.
    
    Returns:
    --------
    dict
        Validation results
    """
    engine = get_engine()
    results = {
        'prices': {'errors': [], 'warnings': []},
        'signals': {'errors': [], 'warnings': []},
        'features': {'errors': [], 'warnings': []}
    }
    
    try:
        with engine.begin() as conn:
            # Validate prices
            prices_df = pd.read_sql(
                text("SELECT symbol, date, open, high, low, close, adj_close, volume FROM prices LIMIT 10000"),
                conn
            )
            if not prices_df.empty:
                results['prices'] = validate_prices(prices_df)
            
            # Check signals
            signals_count = pd.read_sql(
                text("SELECT COUNT(*) as cnt FROM signals"),
                conn
            )['cnt'].iloc[0]
            
            if signals_count == 0:
                results['signals']['warnings'].append("No signals found in database")
            
            # Check features
            features_count = pd.read_sql(
                text("SELECT COUNT(*) as cnt FROM features"),
                conn
            )['cnt'].iloc[0]
            
            if features_count == 0:
                results['features']['warnings'].append("No features found in database")
            
            # Check for missing data
            missing_prices = pd.read_sql(
                text("""
                    SELECT symbol, COUNT(*) as cnt 
                    FROM prices 
                    GROUP BY symbol 
                    HAVING cnt < 20
                """),
                conn
            )
            
            if not missing_prices.empty:
                results['prices']['warnings'].append(
                    f"{len(missing_prices)} symbols with less than 20 data points"
                )
    
    except Exception as e:
        logger.error(f"Error validating database: {e}")
        results['errors'] = [str(e)]
    
    return results


def detect_outliers(series: pd.Series, method: str = "iqr", threshold: float = 3.0) -> pd.Series:
    """
    Detect outliers in a series.
    
    Parameters:
    -----------
    series : pd.Series
        Data series
    method : str
        "iqr" (interquartile range) or "zscore"
    threshold : float
        Threshold for outlier detection
    
    Returns:
    --------
    pd.Series
        Boolean series indicating outliers
    """
    if method == "iqr":
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR
        return (series < lower_bound) | (series > upper_bound)
    else:  # zscore
        z_scores = np.abs((series - series.mean()) / series.std())
        return z_scores > threshold


def fill_missing_data(df: pd.DataFrame, method: str = "forward") -> pd.DataFrame:
    """
    Fill missing data using specified method.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Dataframe with missing values
    method : str
        "forward", "backward", "interpolate", or "mean"
    
    Returns:
    --------
    pd.DataFrame
        Dataframe with filled values
    """
    df_filled = df.copy()
    
    if method == "forward":
        df_filled = df_filled.fillna(method='ffill')
    elif method == "backward":
        df_filled = df_filled.fillna(method='bfill')
    elif method == "interpolate":
        df_filled = df_filled.interpolate()
    elif method == "mean":
        df_filled = df_filled.fillna(df_filled.mean())
    
    return df_filled

