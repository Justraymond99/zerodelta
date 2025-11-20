from __future__ import annotations

import pandas as pd
from datetime import datetime, date
from typing import Dict, List, Optional
from .db import get_engine
from sqlalchemy import text
from .utils.logger import get_logger

logger = get_logger(__name__)


class PaperTradingAccount:
    """
    Paper trading account for simulating trades.
    """
    
    def __init__(self, initial_capital: float = 100000.0, commission: float = 0.001):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission = commission
        self.positions: Dict[str, float] = {}  # symbol -> quantity
        self.trade_history: List[Dict] = []
        self.equity_history: List[Dict] = []
    
    def get_position(self, symbol: str) -> float:
        """Get current position quantity."""
        return self.positions.get(symbol, 0.0)
    
    def get_portfolio_value(self, prices: Dict[str, float]) -> float:
        """Calculate total portfolio value."""
        position_value = sum(self.positions.get(sym, 0) * price for sym, price in prices.items())
        return self.cash + position_value
    
    def place_order(
        self,
        symbol: str,
        quantity: float,
        price: float,
        side: str = "buy",
        timestamp: datetime | None = None
    ) -> bool:
        """
        Place an order.
        
        Parameters:
        -----------
        symbol : str
            Symbol to trade
        quantity : float
            Quantity to trade
        price : float
            Execution price
        side : str
            "buy" or "sell"
        timestamp : datetime, optional
            Order timestamp
        
        Returns:
        --------
        bool
            True if order executed successfully
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        cost = quantity * price
        commission_cost = cost * self.commission
        total_cost = cost + commission_cost
        
        if side.lower() == "buy":
            if total_cost > self.cash:
                logger.warning(f"Insufficient cash for {symbol} buy order")
                return False
            
            self.cash -= total_cost
            self.positions[symbol] = self.positions.get(symbol, 0.0) + quantity
            
        else:  # sell
            current_position = self.positions.get(symbol, 0.0)
            if quantity > current_position:
                logger.warning(f"Insufficient position for {symbol} sell order")
                return False
            
            self.cash += cost - commission_cost
            self.positions[symbol] = current_position - quantity
            if self.positions[symbol] == 0:
                del self.positions[symbol]
        
        # Record trade
        trade = {
            'timestamp': timestamp,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'cost': total_cost if side == "buy" else cost - commission_cost,
            'commission': commission_cost
        }
        self.trade_history.append(trade)
        
        # Calculate P&L for sells
        realized_pnl, pnl_pct = None, None
        if side.lower() == "sell":
            try:
                from qs.oms.pnl import get_pnl_calculator
                pnl_calc = get_pnl_calculator()
                realized_pnl, _, pnl_pct = pnl_calc.calculate_pnl(symbol, side, quantity, price)
            except Exception as e:
                logger.warning(f"Error calculating P&L: {e}")
        
        # Update cost basis
        try:
            from qs.oms.pnl import get_pnl_calculator
            pnl_calc = get_pnl_calculator()
            pnl_calc.update_cost_basis(symbol, side, quantity, price)
        except Exception as e:
            logger.warning(f"Error updating cost basis: {e}")
        
        # Send SMS confirmation
        try:
            from qs.notify.trade_confirmations import send_trade_confirmation
            send_trade_confirmation(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                realized_pnl=realized_pnl,
                pnl_pct=pnl_pct,
                is_paper=True
            )
        except Exception as e:
            logger.warning(f"Error sending trade confirmation: {e}")
        
        logger.info(f"Executed {side} {quantity} {symbol} @ ${price:.2f}")
        return True
    
    def update_equity(self, prices: Dict[str, float], timestamp: datetime | None = None):
        """Record current equity snapshot."""
        if timestamp is None:
            timestamp = datetime.now()
        
        portfolio_value = self.get_portfolio_value(prices)
        self.equity_history.append({
            'timestamp': timestamp,
            'cash': self.cash,
            'portfolio_value': portfolio_value,
            'equity': portfolio_value,
            'return': (portfolio_value / self.initial_capital) - 1.0
        })
    
    def get_statistics(self, prices: Dict[str, float]) -> Dict:
        """Get account statistics."""
        portfolio_value = self.get_portfolio_value(prices)
        total_return = (portfolio_value / self.initial_capital) - 1.0
        
        return {
            'initial_capital': self.initial_capital,
            'cash': self.cash,
            'portfolio_value': portfolio_value,
            'total_return': total_return,
            'num_positions': len(self.positions),
            'num_trades': len(self.trade_history),
            'positions': self.positions.copy()
        }
    
    def save_to_database(self):
        """Save trade history to database."""
        engine = get_engine()
        with engine.begin() as conn:
            for trade in self.trade_history:
                conn.execute(
                    text("""
                        INSERT INTO trades (symbol, date, side, quantity, price, notes)
                        VALUES (:symbol, :date, :side, :quantity, :price, :notes)
                    """),
                    {
                        'symbol': trade['symbol'],
                        'date': trade['timestamp'].date(),
                        'side': trade['side'],
                        'quantity': trade['quantity'],
                        'price': trade['price'],
                        'notes': f"Paper trade: commission={trade['commission']:.4f}"
                    }
                )


def run_paper_trading(
    signals: pd.DataFrame,
    prices: pd.DataFrame,
    initial_capital: float = 100000.0,
    commission: float = 0.001,
    rebalance_frequency: str = "D"
) -> PaperTradingAccount:
    """
    Run paper trading simulation.
    
    Parameters:
    -----------
    signals : pd.DataFrame
        Trading signals with columns: symbol, date, score
    prices : pd.DataFrame
        Price data with columns: symbol, date, adj_close
    initial_capital : float
        Starting capital
    commission : float
        Commission rate
    rebalance_frequency : str
        Rebalancing frequency
    
    Returns:
    --------
    PaperTradingAccount
        Account with trade history
    """
    account = PaperTradingAccount(initial_capital, commission)
    
    # Group signals by date
    signals_by_date = signals.groupby('date')
    prices_pivot = prices.pivot(index='date', columns='symbol', values='adj_close')
    
    for date, date_signals in signals_by_date:
        # Get current prices
        if date not in prices_pivot.index:
            continue
        
        current_prices = prices_pivot.loc[date].to_dict()
        
        # Close existing positions not in new signals
        current_positions = set(account.positions.keys())
        new_symbols = set(date_signals['symbol'].unique())
        symbols_to_close = current_positions - new_symbols
        
        for symbol in symbols_to_close:
            quantity = account.get_position(symbol)
            if quantity > 0 and symbol in current_prices:
                account.place_order(symbol, quantity, current_prices[symbol], "sell", datetime.combine(date, datetime.min.time()))
        
        # Open new positions
        top_signals = date_signals.nlargest(5, 'score')  # Top 5
        
        for _, signal in top_signals.iterrows():
            symbol = signal['symbol']
            if symbol not in current_prices:
                continue
            
            target_value = initial_capital / 5  # Equal weight
            price = current_prices[symbol]
            quantity = target_value / price
            
            current_position = account.get_position(symbol)
            if current_position == 0:
                # New position
                account.place_order(symbol, quantity, price, "buy", datetime.combine(date, datetime.min.time()))
            else:
                # Rebalance if needed
                current_value = current_position * price
                if abs(current_value - target_value) > target_value * 0.1:  # 10% threshold
                    diff = target_value - current_value
                    if diff > 0:
                        account.place_order(symbol, diff / price, price, "buy", datetime.combine(date, datetime.min.time()))
                    else:
                        account.place_order(symbol, abs(diff) / price, price, "sell", datetime.combine(date, datetime.min.time()))
        
        # Update equity
        account.update_equity(current_prices, datetime.combine(date, datetime.min.time()))
    
    return account

