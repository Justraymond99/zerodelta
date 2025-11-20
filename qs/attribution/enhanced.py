from __future__ import annotations

from typing import Dict, List
import pandas as pd
import numpy as np
from ..db import get_engine
from sqlalchemy import text
from ..utils.logger import get_logger

logger = get_logger(__name__)


class EnhancedPerformanceAttribution:
    """
    Enhanced performance attribution with symbol-level, strategy-level, and factor attribution.
    """
    
    def symbol_level_attribution(
        self,
        start_date: str,
        end_date: str,
        benchmark_symbol: str = None
    ) -> pd.DataFrame:
        """Symbol-level performance attribution."""
        engine = get_engine()
        
        with engine.begin() as conn:
            # Get trades
            trades_df = pd.read_sql(
                text("""
                    SELECT symbol, date, side, quantity, price
                    FROM trades
                    WHERE date >= :start AND date <= :end
                """),
                conn,
                params={"start": start_date, "end": end_date}
            )
            
            # Get prices
            prices_df = pd.read_sql(
                text("""
                    SELECT symbol, date, adj_close
                    FROM prices
                    WHERE date >= :start AND date <= :end
                """),
                conn,
                params={"start": start_date, "end": end_date}
            )
        
        if trades_df.empty or prices_df.empty:
            return pd.DataFrame()
        
        # Calculate P&L per symbol
        attribution = []
        for symbol in trades_df['symbol'].unique():
            symbol_trades = trades_df[trades_df['symbol'] == symbol]
            symbol_prices = prices_df[prices_df['symbol'] == symbol].set_index('date')
            
            total_pnl = 0
            total_value = 0
            
            for _, trade in symbol_trades.iterrows():
                trade_date = pd.to_datetime(trade['date'])
                price = trade['price']
                quantity = trade['quantity']
                side = trade['side']
                
                # Find exit price (next trade or end date price)
                if side.lower() == 'buy':
                    # Find corresponding sell or use end price
                    sells = symbol_trades[
                        (symbol_trades['symbol'] == symbol) &
                        (symbol_trades['side'] == 'sell') &
                        (pd.to_datetime(symbol_trades['date']) > trade_date)
                    ]
                    
                    if not sells.empty:
                        exit_price = sells.iloc[0]['price']
                    else:
                        # Use end date price
                        end_price = symbol_prices.iloc[-1]['adj_close'] if not symbol_prices.empty else price
                        exit_price = end_price
                    
                    pnl = (exit_price - price) * quantity
                    total_pnl += pnl
                    total_value += price * quantity
            
            if total_value > 0:
                attribution.append({
                    'symbol': symbol,
                    'pnl': total_pnl,
                    'value': total_value,
                    'return_pct': (total_pnl / total_value) * 100,
                    'num_trades': len(symbol_trades)
                })
        
        return pd.DataFrame(attribution)
    
    def strategy_level_attribution(
        self,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """Strategy-level performance attribution."""
        engine = get_engine()
        
        with engine.begin() as conn:
            # Get signals by strategy
            signals_df = pd.read_sql(
                text("""
                    SELECT signal_name, symbol, date, score
                    FROM signals
                    WHERE date >= :start AND date <= :end
                """),
                conn,
                params={"start": start_date, "end": end_date}
            )
            
            # Get prices
            prices_df = pd.read_sql(
                text("""
                    SELECT symbol, date, adj_close
                    FROM prices
                    WHERE date >= :start AND date <= :end
                """),
                conn,
                params={"start": start_date, "end": end_date}
            )
        
        if signals_df.empty or prices_df.empty:
            return pd.DataFrame()
        
        # Calculate performance per strategy
        attribution = []
        for strategy in signals_df['signal_name'].unique():
            strategy_signals = signals_df[signals_df['signal_name'] == strategy]
            
            # Calculate returns for top signals
            total_return = 0
            signal_count = 0
            
            for _, signal in strategy_signals.iterrows():
                symbol = signal['symbol']
                date = pd.to_datetime(signal['date'])
                
                # Get price change
                symbol_prices = prices_df[
                    (prices_df['symbol'] == symbol) &
                    (pd.to_datetime(prices_df['date']) >= date)
                ].sort_values('date')
                
                if len(symbol_prices) > 1:
                    entry_price = symbol_prices.iloc[0]['adj_close']
                    exit_price = symbol_prices.iloc[-1]['adj_close']
                    ret = (exit_price - entry_price) / entry_price
                    total_return += ret * signal['score']  # Weight by signal strength
                    signal_count += 1
            
            if signal_count > 0:
                attribution.append({
                    'strategy': strategy,
                    'avg_return': (total_return / signal_count) * 100,
                    'signal_count': signal_count,
                    'total_return': total_return * 100
                })
        
        return pd.DataFrame(attribution)
    
    def factor_attribution(
        self,
        start_date: str,
        end_date: str
    ) -> Dict:
        """Factor-based attribution (momentum, mean reversion, etc.)."""
        engine = get_engine()
        
        with engine.begin() as conn:
            # Get features
            features_df = pd.read_sql(
                text("""
                    SELECT symbol, date, feature, value
                    FROM features
                    WHERE date >= :start AND date <= :end
                """),
                conn,
                params={"start": start_date, "end": end_date}
            )
            
            # Get returns
            prices_df = pd.read_sql(
                text("""
                    SELECT symbol, date, adj_close
                    FROM prices
                    WHERE date >= :start AND date <= :end
                    ORDER BY symbol, date
                """),
                conn,
                params={"start": start_date, "end": end_date}
            )
        
        if features_df.empty or prices_df.empty:
            return {}
        
        # Calculate returns
        prices_pivot = prices_df.pivot(index='date', columns='symbol', values='adj_close')
        returns = prices_pivot.pct_change().dropna()
        
        # Factor attribution
        factors = {
            'momentum': ['rsi', 'macd', 'momentum'],
            'mean_reversion': ['bollinger_bands', 'z_score'],
            'volatility': ['atr', 'volatility'],
            'volume': ['volume', 'obv']
        }
        
        attribution = {}
        for factor_name, feature_names in factors.items():
            factor_features = features_df[features_df['feature'].isin(feature_names)]
            
            if not factor_features.empty:
                # Calculate correlation with returns
                # Simplified - would need proper factor model
                attribution[factor_name] = {
                    'contribution': 0.0,  # Placeholder
                    'feature_count': len(feature_names)
                }
        
        return attribution
    
    def time_period_attribution(
        self,
        start_date: str,
        end_date: str,
        period: str = "monthly"
    ) -> pd.DataFrame:
        """Time-period based attribution."""
        engine = get_engine()
        
        with engine.begin() as conn:
            trades_df = pd.read_sql(
                text("""
                    SELECT date, side, quantity, price, symbol
                    FROM trades
                    WHERE date >= :start AND date <= :end
                """),
                conn,
                params={"start": start_date, "end": end_date}
            )
        
        if trades_df.empty:
            return pd.DataFrame()
        
        trades_df['date'] = pd.to_datetime(trades_df['date'])
        
        # Group by period
        if period == "monthly":
            trades_df['period'] = trades_df['date'].dt.to_period('M')
        elif period == "weekly":
            trades_df['period'] = trades_df['date'].dt.to_period('W')
        else:
            trades_df['period'] = trades_df['date'].dt.date
        
        # Calculate P&L per period
        period_pnl = []
        for period_val, group in trades_df.groupby('period'):
            # Simplified P&L calculation
            buys = group[group['side'] == 'buy']
            sells = group[group['side'] == 'sell']
            
            buy_value = (buys['quantity'] * buys['price']).sum()
            sell_value = (sells['quantity'] * sells['price']).sum()
            pnl = sell_value - buy_value
            
            period_pnl.append({
                'period': str(period_val),
                'pnl': pnl,
                'num_trades': len(group),
                'buy_value': buy_value,
                'sell_value': sell_value
            })
        
        return pd.DataFrame(period_pnl)


# Global attribution analyzer
_attribution_analyzer: Optional[EnhancedPerformanceAttribution] = None


def get_attribution_analyzer() -> EnhancedPerformanceAttribution:
    """Get global attribution analyzer."""
    global _attribution_analyzer
    if _attribution_analyzer is None:
        _attribution_analyzer = EnhancedPerformanceAttribution()
    return _attribution_analyzer

