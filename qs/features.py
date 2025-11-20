from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from .db import get_engine
from .indicators import (
    rsi, macd, bollinger_bands, adx, stochastic, atr, obv,
    williams_r, cci, ema, sma
)


def compute_features() -> int:
    engine = get_engine()
    with engine.begin() as conn:
        prices = pd.read_sql(
            text("SELECT symbol, date, open, high, low, close, adj_close, volume FROM prices ORDER BY symbol, date"),
            conn
        )
    if prices.empty:
        return 0

    def feats_for_symbol(df: pd.DataFrame) -> pd.DataFrame:
        df = df.sort_values('date').copy()
        
        # Basic features
        df['ret_1d'] = df['adj_close'].pct_change(1)
        df['ret_5d'] = df['adj_close'].pct_change(5)
        df['mom_20'] = df['adj_close'] / df['adj_close'].shift(20) - 1.0
        df['vol_20'] = df['ret_1d'].rolling(20).std()
        df['zscore_5'] = (df['adj_close'] - df['adj_close'].rolling(5).mean()) / df['adj_close'].rolling(5).std()
        
        # Technical indicators
        if len(df) >= 14:
            df['rsi_14'] = rsi(df['adj_close'], period=14)
        
        if len(df) >= 26:
            macd_df = macd(df['adj_close'])
            df['macd'] = macd_df['macd']
            df['macd_signal'] = macd_df['signal']
            df['macd_histogram'] = macd_df['histogram']
        
        if len(df) >= 20:
            bb_df = bollinger_bands(df['adj_close'], period=20)
            df['bb_upper'] = bb_df['upper']
            df['bb_lower'] = bb_df['lower']
            df['bb_middle'] = bb_df['middle']
            df['bb_width'] = (bb_df['upper'] - bb_df['lower']) / bb_df['middle']
            df['bb_position'] = (df['adj_close'] - bb_df['lower']) / (bb_df['upper'] - bb_df['lower'])
        
        if len(df) >= 14 and 'high' in df.columns and 'low' in df.columns:
            df['adx_14'] = adx(df['high'], df['low'], df['close'], period=14)
            stoch_df = stochastic(df['high'], df['low'], df['close'], k_period=14, d_period=3)
            df['stoch_k'] = stoch_df['k']
            df['stoch_d'] = stoch_df['d']
            df['atr_14'] = atr(df['high'], df['low'], df['close'], period=14)
            df['williams_r'] = williams_r(df['high'], df['low'], df['close'], period=14)
        
        if len(df) >= 20 and 'high' in df.columns and 'low' in df.columns:
            df['cci_20'] = cci(df['high'], df['low'], df['close'], period=20)
        
        if 'volume' in df.columns:
            df['obv'] = obv(df['close'], df['volume'])
        
        # Moving averages
        if len(df) >= 20:
            df['sma_20'] = sma(df['adj_close'], period=20)
            df['ema_12'] = ema(df['adj_close'], period=12)
            df['ema_26'] = ema(df['adj_close'], period=26)
        
        if len(df) >= 50:
            df['sma_50'] = sma(df['adj_close'], period=50)
        
        if len(df) >= 200:
            df['sma_200'] = sma(df['adj_close'], period=200)
        
        # Price position relative to MAs
        if 'sma_20' in df.columns:
            df['price_vs_sma20'] = (df['adj_close'] - df['sma_20']) / df['sma_20']
        if 'sma_50' in df.columns:
            df['price_vs_sma50'] = (df['adj_close'] - df['sma_50']) / df['sma_50']
        
        # Select feature columns
        feature_cols = [
            'ret_1d', 'ret_5d', 'mom_20', 'vol_20', 'zscore_5',
            'rsi_14', 'macd', 'macd_signal', 'macd_histogram',
            'bb_upper', 'bb_lower', 'bb_middle', 'bb_width', 'bb_position',
            'adx_14', 'stoch_k', 'stoch_d', 'atr_14', 'williams_r', 'cci_20',
            'obv', 'sma_20', 'ema_12', 'ema_26', 'sma_50', 'sma_200',
            'price_vs_sma20', 'price_vs_sma50'
        ]
        
        # Only include columns that exist
        available_cols = [col for col in feature_cols if col in df.columns]
        long = df.melt(
            id_vars=['symbol', 'date'],
            value_vars=available_cols,
            var_name='feature',
            value_name='value'
        )
        return long.dropna()

    out = prices.groupby('symbol', group_keys=False).apply(feats_for_symbol)

    engine = get_engine()
    with engine.begin() as conn:
        if not out.empty:
            min_date = out['date'].min()
            max_date = out['date'].max()
            for sym in out['symbol'].unique().tolist():
                conn.execute(text(
                    "DELETE FROM features WHERE symbol = :sym AND date BETWEEN :min_date AND :max_date"
                ), dict(sym=sym, min_date=min_date, max_date=max_date))
            out.to_sql('features', con=conn.connection, if_exists='append', index=False)
    return 0 if out.empty else len(out)