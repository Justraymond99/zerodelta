from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Dict
from .db import get_engine
from sqlalchemy import text


def performance_attribution(
    signal_name: str,
    benchmark_symbol: str | None = None
) -> Dict[str, any]:
    """
    Performance attribution analysis.
    
    Parameters:
    -----------
    signal_name : str
        Signal name to analyze
    benchmark_symbol : str, optional
        Benchmark symbol for comparison
    
    Returns:
    --------
    dict
        Attribution results
    """
    engine = get_engine()
    
    with engine.begin() as conn:
        # Get portfolio returns
        px = pd.read_sql(text("SELECT symbol, date, adj_close FROM prices"), conn)
        sig = pd.read_sql(
            text("SELECT symbol, date, score FROM signals WHERE signal_name = :name"),
            conn,
            params={"name": signal_name}
        )
    
    if px.empty or sig.empty:
        return {}
    
    prices = px.pivot(index='date', columns='symbol', values='adj_close').sort_index()
    scores = sig.pivot(index='date', columns='symbol', values='score').reindex(index=prices.index).fillna(0.0)
    
    # Calculate returns
    rets = prices.pct_change().fillna(0.0)
    
    # Portfolio weights (top 5)
    ranks = scores.rank(axis=1, ascending=False, method='first')
    weights = (ranks <= 5).astype(float)
    weights = weights.div(weights.sum(axis=1), axis=0).fillna(0.0)
    
    # Portfolio returns
    port_rets = (weights.shift(1).fillna(0.0) * rets).sum(axis=1)
    
    # Attribution by symbol
    symbol_contributions = {}
    for symbol in weights.columns:
        symbol_ret = (weights[symbol].shift(1).fillna(0.0) * rets[symbol]).sum()
        symbol_contributions[symbol] = {
            'total_return': float(symbol_ret),
            'avg_weight': float(weights[symbol].mean()),
            'avg_return': float(rets[symbol].mean()),
            'contribution': float(symbol_ret / port_rets.sum() if port_rets.sum() != 0 else 0)
        }
    
    # Attribution by factor (if features available)
    factor_attribution = {}
    try:
        with engine.begin() as conn:
            features_df = pd.read_sql(
                text("SELECT symbol, date, feature, value FROM features"),
                conn
            )
        
        if not features_df.empty:
            features_pivot = features_df.pivot_table(
                index=['symbol', 'date'],
                columns='feature',
                values='value'
            ).reset_index()
            
            # Calculate correlation between features and returns
            for feature in features_pivot.columns:
                if feature not in ['symbol', 'date']:
                    try:
                        feature_series = features_pivot.set_index(['symbol', 'date'])[feature]
                        # Align with returns
                        aligned = pd.DataFrame({
                            'feature': feature_series,
                            'return': rets.stack()
                        }).dropna()
                        
                        if len(aligned) > 10:
                            correlation = aligned['feature'].corr(aligned['return'])
                            factor_attribution[feature] = {
                                'correlation': float(correlation) if not np.isnan(correlation) else 0.0
                            }
                    except Exception:
                        continue
    except Exception:
        pass
    
    # Benchmark comparison
    benchmark_attribution = {}
    if benchmark_symbol and benchmark_symbol in prices.columns:
        benchmark_rets = prices[benchmark_symbol].pct_change().fillna(0.0)
        benchmark_rets = benchmark_rets.reindex(port_rets.index).fillna(0.0)
        
        excess_returns = port_rets - benchmark_rets
        benchmark_attribution = {
            'excess_return': float(excess_returns.sum()),
            'tracking_error': float(excess_returns.std()),
            'information_ratio': float(excess_returns.mean() / excess_returns.std() if excess_returns.std() > 0 else 0)
        }
    
    return {
        'symbol_contributions': symbol_contributions,
        'factor_attribution': factor_attribution,
        'benchmark_attribution': benchmark_attribution,
        'total_portfolio_return': float(port_rets.sum())
    }

