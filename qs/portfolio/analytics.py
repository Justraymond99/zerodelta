from __future__ import annotations

from typing import Dict, List
import pandas as pd
import numpy as np
from datetime import datetime
from ..db import get_engine
from sqlalchemy import text
from ..oms.manager import get_order_manager
from ..oms.pnl import get_pnl_calculator
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PortfolioAnalytics:
    """
    Advanced portfolio analytics including heatmaps, risk decomposition, and trade analysis.
    """
    
    def get_portfolio_heatmap(self) -> pd.DataFrame:
        """Generate portfolio heatmap data (positions by symbol)."""
        manager = get_order_manager()
        positions = manager.get_positions()
        
        if not positions:
            return pd.DataFrame()
        
        # Get current prices
        engine = get_engine()
        heatmap_data = []
        
        with engine.begin() as conn:
            for symbol, quantity in positions.items():
                result = conn.execute(
                    text("SELECT adj_close FROM prices WHERE symbol = :sym ORDER BY date DESC LIMIT 1"),
                    {"sym": symbol}
                ).fetchone()
                
                if result:
                    price = float(result[0])
                    value = quantity * price
                    pnl_calc = get_pnl_calculator()
                    cost_basis = pnl_calc.get_position_cost_basis(symbol)
                    
                    if cost_basis:
                        entry_price = cost_basis['avg_price']
                        pnl = (price - entry_price) * quantity
                        pnl_pct = ((price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
                    else:
                        pnl = 0
                        pnl_pct = 0
                    
                    heatmap_data.append({
                        'symbol': symbol,
                        'quantity': quantity,
                        'price': price,
                        'value': value,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct
                    })
        
        return pd.DataFrame(heatmap_data)
    
    def get_risk_decomposition(self, account_value: float) -> Dict:
        """Decompose portfolio risk by symbol."""
        manager = get_order_manager()
        positions = manager.get_positions()
        
        if not positions:
            return {}
        
        # Get returns data
        engine = get_engine()
        symbols = list(positions.keys())
        
        with engine.begin() as conn:
            placeholders = ",".join([f":sym{i}" for i in range(len(symbols))])
            params = {f"sym{i}": sym for i, sym in enumerate(symbols)}
            
            prices_df = pd.read_sql(
                text(f"""
                    SELECT symbol, date, adj_close
                    FROM prices
                    WHERE symbol IN ({placeholders})
                    AND date >= DATE('now', '-30 days')
                    ORDER BY symbol, date
                """),
                conn,
                params=params
            )
        
        if prices_df.empty:
            return {}
        
        # Calculate risk metrics
        prices_pivot = prices_df.pivot(index='date', columns='symbol', values='adj_close')
        returns = prices_pivot.pct_change().dropna()
        
        # Portfolio weights
        current_prices = {}
        with engine.begin() as conn:
            for symbol in symbols:
                result = conn.execute(
                    text("SELECT adj_close FROM prices WHERE symbol = :sym ORDER BY date DESC LIMIT 1"),
                    {"sym": symbol}
                ).fetchone()
                if result:
                    current_prices[symbol] = float(result[0])
        
        portfolio_weights = {}
        total_value = sum(abs(positions.get(sym, 0)) * current_prices.get(sym, 0) for sym in symbols)
        
        for symbol in symbols:
            position_value = abs(positions.get(symbol, 0)) * current_prices.get(symbol, 0)
            portfolio_weights[symbol] = position_value / total_value if total_value > 0 else 0
        
        # Risk decomposition
        portfolio_vol = returns.std().mean() * np.sqrt(252)  # Annualized
        
        risk_decomp = {}
        for symbol in symbols:
            if symbol in returns.columns:
                symbol_vol = returns[symbol].std() * np.sqrt(252)
                weight = portfolio_weights.get(symbol, 0)
                contribution = weight * symbol_vol
                
                risk_decomp[symbol] = {
                    'weight': weight * 100,
                    'volatility': symbol_vol * 100,
                    'contribution': contribution * 100
                }
        
        return {
            'portfolio_volatility': portfolio_vol * 100,
            'symbol_risk': risk_decomp
        }
    
    def get_trade_analysis(self, days: int = 30) -> Dict:
        """Analyze trade performance."""
        engine = get_engine()
        
        with engine.begin() as conn:
            trades_df = pd.read_sql(
                text("""
                    SELECT symbol, date, side, quantity, price
                    FROM trades
                    WHERE date >= DATE('now', '-' || :days || ' days')
                    ORDER BY date DESC
                """),
                conn,
                params={"days": days}
            )
        
        if trades_df.empty:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_hold_time': 0,
                'avg_win': 0,
                'avg_loss': 0
            }
        
        # Calculate win rate
        # This is simplified - would need to track entry/exit pairs
        buys = trades_df[trades_df['side'] == 'buy']
        sells = trades_df[trades_df['side'] == 'sell']
        
        # Estimate P&L (simplified)
        total_trades = len(buys) + len(sells)
        
        return {
            'total_trades': total_trades,
            'buy_trades': len(buys),
            'sell_trades': len(sells),
            'avg_trade_size': trades_df['quantity'].mean(),
            'most_traded_symbol': trades_df['symbol'].mode().iloc[0] if not trades_df['symbol'].mode().empty else None
        }
    
    def get_drawdown_analysis(self, account_value: float) -> Dict:
        """Analyze drawdown periods."""
        engine = get_engine()
        
        # Get equity curve from trades
        with engine.begin() as conn:
            trades_df = pd.read_sql(
                text("""
                    SELECT date, side, quantity, price, symbol
                    FROM trades
                    ORDER BY date
                """),
                conn
            )
        
        if trades_df.empty:
            return {}
        
        # Calculate equity curve (simplified)
        trades_df['date'] = pd.to_datetime(trades_df['date'])
        trades_df['value'] = trades_df['quantity'] * trades_df['price']
        trades_df['pnl'] = trades_df.apply(
            lambda row: row['value'] if row['side'] == 'sell' else -row['value'],
            axis=1
        )
        
        equity_curve = trades_df.groupby('date')['pnl'].sum().cumsum() + account_value
        
        # Calculate drawdowns
        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve - running_max) / running_max
        
        max_drawdown = drawdown.min()
        max_dd_date = drawdown.idxmin() if not drawdown.empty else None
        
        return {
            'max_drawdown': max_drawdown * 100 if not pd.isna(max_drawdown) else 0,
            'max_drawdown_date': max_dd_date.isoformat() if max_dd_date else None,
            'current_drawdown': drawdown.iloc[-1] * 100 if not drawdown.empty else 0
        }


# Global analytics
_portfolio_analytics: Optional[PortfolioAnalytics] = None


def get_portfolio_analytics() -> PortfolioAnalytics:
    """Get global portfolio analytics."""
    global _portfolio_analytics
    if _portfolio_analytics is None:
        _portfolio_analytics = PortfolioAnalytics()
    return _portfolio_analytics

