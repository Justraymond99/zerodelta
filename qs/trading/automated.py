from __future__ import annotations

import pandas as pd
from datetime import datetime
from datetime import date as date_type
from typing import Dict, List, Optional
from ..risk import risk_limit_check
from ..papertrading import PaperTradingAccount
from ..db import get_engine
from sqlalchemy import text
from ..utils.logger import get_logger
from ..exec.ibkr_adapter import IBKRAdapter
from ..oms.pnl import get_pnl_calculator
from ..notify.trade_confirmations import send_trade_confirmation

logger = get_logger(__name__)


class AutomatedTrader:
    """
    Automated trading system that executes trades based on signals.
    """
    
    def __init__(
        self,
        signal_name: str = "xgb_alpha",
        account_value: float = 100000.0,
        max_position_pct: float = 0.10,
        min_signal_threshold: float = 0.7,
        paper_trading: bool = True,
        auto_execute: bool = False
    ):
        self.signal_name = signal_name
        self.account_value = account_value
        self.max_position_pct = max_position_pct
        self.min_signal_threshold = min_signal_threshold
        self.paper_trading = paper_trading
        self.auto_execute = auto_execute
        
        if paper_trading:
            self.account = PaperTradingAccount(initial_capital=account_value)
        else:
            self.account = None
            self.ibkr = IBKRAdapter(paper=False)
    
    def get_current_positions(self) -> Dict[str, float]:
        """Get current positions."""
        if self.paper_trading:
            return self.account.positions.copy()
        else:
            # Get from IBKR
            if hasattr(self, '_ibkr_connected') and self._ibkr_connected:
                try:
                    return self.ibkr.get_positions()
                except Exception as e:
                    logger.error(f"Error getting IBKR positions: {e}")
                    return {}
            return {}
    
    def get_latest_signals(self) -> pd.DataFrame:
        """Get latest trading signals."""
        engine = get_engine()
        with engine.begin() as conn:
            df = pd.read_sql(
                text("""
                    SELECT s.symbol, s.score, p.adj_close as price
                    FROM signals s
                    JOIN prices p ON s.symbol = p.symbol AND s.date = p.date
                    WHERE s.signal_name = :name
                    AND s.date = (SELECT MAX(date) FROM signals WHERE signal_name = :name)
                    ORDER BY s.score DESC
                """),
                conn,
                params={"name": self.signal_name}
            )
        return df
    
    def calculate_target_positions(self, signals: pd.DataFrame) -> Dict[str, float]:
        """Calculate target positions based on signals."""
        # Filter by threshold
        strong_signals = signals[signals['score'] >= self.min_signal_threshold]
        
        if strong_signals.empty:
            return {}
        
        # Top N positions
        top_n = min(5, len(strong_signals))
        top_signals = strong_signals.head(top_n)
        
        # Equal weight allocation
        target_positions = {}
        position_value = self.account_value * self.max_position_pct
        
        for _, signal in top_signals.iterrows():
            symbol = signal['symbol']
            price = signal['price']
            quantity = position_value / price
            target_positions[symbol] = quantity
        
        return target_positions
    
    def generate_trades(self) -> List[Dict]:
        """Generate trades to reach target positions."""
        signals = self.get_latest_signals()
        target_positions = self.calculate_target_positions(signals)
        current_positions = self.get_current_positions()
        
        trades = []
        
        # Close positions not in target
        for symbol, current_qty in current_positions.items():
            if symbol not in target_positions:
                trades.append({
                    'symbol': symbol,
                    'side': 'sell',
                    'quantity': current_qty,
                    'reason': 'signal_exit'
                })
        
        # Open/adjust positions
        for symbol, target_qty in target_positions.items():
            current_qty = current_positions.get(symbol, 0.0)
            
            if current_qty == 0:
                # New position
                trades.append({
                    'symbol': symbol,
                    'side': 'buy',
                    'quantity': target_qty,
                    'reason': 'new_signal'
                })
            elif abs(target_qty - current_qty) > current_qty * 0.1:  # 10% rebalance threshold
                # Rebalance
                diff = target_qty - current_qty
                trades.append({
                    'symbol': symbol,
                    'side': 'buy' if diff > 0 else 'sell',
                    'quantity': abs(diff),
                    'reason': 'rebalance'
                })
        
        return trades
    
    def execute_trade(self, trade: Dict) -> bool:
        """Execute a single trade."""
        symbol = trade['symbol']
        side = trade['side']
        quantity = trade['quantity']
        
        # Get current price
        engine = get_engine()
        with engine.begin() as conn:
            result = conn.execute(
                text("SELECT adj_close FROM prices WHERE symbol = :sym ORDER BY date DESC LIMIT 1"),
                {"sym": symbol}
            ).fetchone()
        
        if not result:
            logger.warning(f"No price data for {symbol}")
            return False
        
        price = float(result[0])
        
        # Risk check
        position_value = quantity * price
        is_violation, reason = risk_limit_check(
            self.account_value,
            position_value,
            max_position_pct=self.max_position_pct
        )
        
        if is_violation:
            logger.warning(f"Trade rejected: {reason}")
            return False
        
        # Execute trade
        if self.paper_trading:
            # Get P&L before executing (for sells)
            pnl_calc = get_pnl_calculator()
            realized_pnl, _, pnl_pct = None, None, None
            if side.lower() == "sell":
                realized_pnl, _, pnl_pct = pnl_calc.calculate_pnl(symbol, side, quantity, price)
            
            success = self.account.place_order(symbol, quantity, price, side)
            if success:
                logger.info(f"Paper trade executed: {side} {quantity} {symbol} @ ${price:.2f}")
                
                # Update cost basis
                pnl_calc.update_cost_basis(symbol, side, quantity, price)
                
                # Send SMS confirmation
                send_trade_confirmation(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=price,
                    realized_pnl=realized_pnl,
                    pnl_pct=pnl_pct,
                    is_paper=True
                )
        else:
            if self.auto_execute:
                try:
                    if not hasattr(self, '_ibkr_connected') or not self.ibkr.is_connected():
                        # Get connection settings from environment
                        import os
                        host = os.getenv("IBKR_HOST", "127.0.0.1")
                        port = int(os.getenv("IBKR_PORT", "7496")) if not self.paper_trading else 7497
                        client_id = int(os.getenv("IBKR_CLIENT_ID", "1"))
                        self.ibkr.connect(host=host, port=port, client_id=client_id)
                        self._ibkr_connected = True
                        logger.info(f"Connected to IBKR (live={not self.paper_trading})")
                    
                    # Get P&L before executing (for sells)
                    pnl_calc = get_pnl_calculator()
                    realized_pnl, _, pnl_pct = None, None, None
                    if side.lower() == "sell":
                        realized_pnl, _, pnl_pct = pnl_calc.calculate_pnl(symbol, side, quantity, price)
                    
                    self.ibkr.place_order(symbol, side, quantity)
                    logger.info(f"Live trade executed: {side} {quantity} {symbol}")
                    
                    # Update cost basis
                    pnl_calc.update_cost_basis(symbol, side, quantity, price)
                    
                    # Record in database
                    with engine.begin() as conn:
                        conn.execute(
                            text("""
                                INSERT INTO trades (symbol, date, side, quantity, price, notes)
                                VALUES (:sym, :date, :side, :qty, :price, :notes)
                            """),
                            {
                                'sym': symbol,
                                'date': date_type.today(),
                                'side': side,
                                'qty': quantity,
                                'price': price,
                                'notes': f"Automated: {trade.get('reason', 'signal')}"
                            }
                        )
                    
                    # Send SMS confirmation
                    send_trade_confirmation(
                        symbol=symbol,
                        side=side,
                        quantity=quantity,
                        price=price,
                        realized_pnl=realized_pnl,
                        pnl_pct=pnl_pct,
                        is_paper=False
                    )
                    
                    return True
                except Exception as e:
                    logger.error(f"Trade execution failed: {e}")
                    return False
            else:
                logger.info(f"Trade would execute (auto_execute=False): {side} {quantity} {symbol} @ ${price:.2f}")
                return True
        
        return success
    
    def run_cycle(self) -> Dict:
        """Run one trading cycle."""
        logger.info("Starting automated trading cycle")
        
        trades = self.generate_trades()
        executed = []
        rejected = []
        
        for trade in trades:
            if self.execute_trade(trade):
                executed.append(trade)
            else:
                rejected.append(trade)
        
        result = {
            'timestamp': datetime.now(),
            'trades_generated': len(trades),
            'trades_executed': len(executed),
            'trades_rejected': len(rejected),
            'executed': executed,
            'rejected': rejected
        }
        
        logger.info(f"Trading cycle complete: {len(executed)} executed, {len(rejected)} rejected")
        return result

