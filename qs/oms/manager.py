from __future__ import annotations

from typing import Dict, List, Optional
from datetime import datetime
from .order import Order, OrderStatus, OrderSide, OrderType
from .pnl import get_pnl_calculator
from ..db import get_engine
from sqlalchemy import text
from ..utils.logger import get_logger

logger = get_logger(__name__)


class OrderManager:
    """
    Advanced Order Management System with full lifecycle tracking.
    """
    
    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, float] = {}  # symbol -> quantity
    
    def create_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        notes: Optional[str] = None
    ) -> Order:
        """Create a new order."""
        order = Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price,
            notes=notes
        )
        
        self.orders[order.order_id] = order
        logger.info(f"Order created: {order.order_id} - {side.value} {quantity} {symbol}")
        return order
    
    def submit_order(self, order_id: str) -> bool:
        """Submit an order for execution."""
        order = self.orders.get(order_id)
        if not order:
            logger.error(f"Order not found: {order_id}")
            return False
        
        try:
            order.submit()
            self._save_order_to_db(order)
            return True
        except Exception as e:
            logger.error(f"Error submitting order {order_id}: {e}")
            return False
    
    def fill_order(self, order_id: str, quantity: float, price: float, fill_id: Optional[str] = None, send_sms: bool = True) -> bool:
        """Record a fill for an order."""
        order = self.orders.get(order_id)
        if not order:
            logger.error(f"Order not found: {order_id}")
            return False
        
        try:
            # Calculate P&L before updating position
            pnl_calc = get_pnl_calculator()
            realized_pnl, _, pnl_pct = pnl_calc.calculate_pnl(
                order.symbol,
                order.side.value,
                quantity,
                price
            )
            
            order.fill(quantity, price, fill_id)
            self._update_position(order.symbol, order.side, quantity)
            
            # Update cost basis
            pnl_calc.update_cost_basis(
                order.symbol,
                order.side.value,
                quantity,
                price
            )
            
            self._save_order_to_db(order)
            
            # Send SMS confirmation if order is fully filled
            if send_sms and order.status == OrderStatus.FILLED:
                from ..notify.trade_confirmations import send_trade_confirmation
                send_trade_confirmation(
                    symbol=order.symbol,
                    side=order.side.value,
                    quantity=order.filled_quantity,
                    price=order.average_fill_price or price,
                    realized_pnl=realized_pnl,
                    pnl_pct=pnl_pct,
                    order_id=order.order_id,
                    is_paper=False  # Could be configurable
                )
            
            return True
        except Exception as e:
            logger.error(f"Error filling order {order_id}: {e}")
            return False
    
    def cancel_order(self, order_id: str, reason: Optional[str] = None) -> bool:
        """Cancel an order."""
        order = self.orders.get(order_id)
        if not order:
            logger.error(f"Order not found: {order_id}")
            return False
        
        try:
            order.cancel(reason)
            self._save_order_to_db(order)
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def reject_order(self, order_id: str, reason: str) -> bool:
        """Reject an order."""
        order = self.orders.get(order_id)
        if not order:
            logger.error(f"Order not found: {order_id}")
            return False
        
        try:
            order.reject(reason)
            self._save_order_to_db(order)
            return True
        except Exception as e:
            logger.error(f"Error rejecting order {order_id}: {e}")
            return False
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self.orders.get(order_id)
    
    def get_orders_by_status(self, status: OrderStatus) -> List[Order]:
        """Get all orders with specific status."""
        return [order for order in self.orders.values() if order.status == status]
    
    def get_open_orders(self) -> List[Order]:
        """Get all open orders (pending, submitted, partially filled)."""
        open_statuses = [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]
        return [order for order in self.orders.values() if order.status in open_statuses]
    
    def get_positions(self) -> Dict[str, float]:
        """Get current positions."""
        return self.positions.copy()
    
    def get_position(self, symbol: str) -> float:
        """Get position for a symbol."""
        return self.positions.get(symbol, 0.0)
    
    def _update_position(self, symbol: str, side: OrderSide, quantity: float):
        """Update position after fill."""
        if symbol not in self.positions:
            self.positions[symbol] = 0.0
        
        if side == OrderSide.BUY:
            self.positions[symbol] += quantity
        else:  # SELL
            self.positions[symbol] -= quantity
        
        # Remove if zero
        if abs(self.positions[symbol]) < 0.0001:
            del self.positions[symbol]
    
    def _save_order_to_db(self, order: Order):
        """Save order to database."""
        try:
            engine = get_engine()
            with engine.begin() as conn:
                # Check if order exists
                result = conn.execute(
                    text("SELECT COUNT(*) FROM orders WHERE order_id = :id"),
                    {"id": order.order_id}
                ).fetchone()
                
                if result[0] == 0:
                    # Insert
                    conn.execute(
                        text("""
                            INSERT INTO orders (
                                order_id, symbol, side, quantity, order_type,
                                limit_price, stop_price, status, filled_quantity,
                                average_fill_price, created_at, notes
                            ) VALUES (
                                :order_id, :symbol, :side, :quantity, :order_type,
                                :limit_price, :stop_price, :status, :filled_quantity,
                                :avg_price, :created_at, :notes
                            )
                        """),
                        {
                            "order_id": order.order_id,
                            "symbol": order.symbol,
                            "side": order.side.value,
                            "quantity": order.quantity,
                            "order_type": order.order_type.value,
                            "limit_price": order.limit_price,
                            "stop_price": order.stop_price,
                            "status": order.status.value,
                            "filled_quantity": order.filled_quantity,
                            "avg_price": order.average_fill_price,
                            "created_at": order.created_at,
                            "notes": order.notes
                        }
                    )
                else:
                    # Update
                    conn.execute(
                        text("""
                            UPDATE orders SET
                                status = :status,
                                filled_quantity = :filled_quantity,
                                average_fill_price = :avg_price,
                                submitted_at = :submitted_at,
                                filled_at = :filled_at,
                                cancelled_at = :cancelled_at,
                                rejected_at = :rejected_at,
                                rejection_reason = :rejection_reason
                            WHERE order_id = :order_id
                        """),
                        {
                            "order_id": order.order_id,
                            "status": order.status.value,
                            "filled_quantity": order.filled_quantity,
                            "avg_price": order.average_fill_price,
                            "submitted_at": order.submitted_at,
                            "filled_at": order.filled_at,
                            "cancelled_at": order.cancelled_at,
                            "rejected_at": order.rejected_at,
                            "rejection_reason": order.rejection_reason
                        }
                    )
        except Exception as e:
            logger.error(f"Error saving order to database: {e}")


# Global order manager instance
_order_manager: Optional[OrderManager] = None


def get_order_manager() -> OrderManager:
    """Get global order manager instance."""
    global _order_manager
    if _order_manager is None:
        _order_manager = OrderManager()
    return _order_manager

