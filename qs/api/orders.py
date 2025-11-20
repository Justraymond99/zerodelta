from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Optional
from qs.oms.manager import get_order_manager
from qs.oms.order import OrderSide, OrderType, OrderStatus
from qs.risk.realtime import get_risk_monitor
from qs.utils.logger import get_logger
from qs.oms.pnl import get_pnl_calculator

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.post("/")
def create_order(
    symbol: str,
    side: str,
    quantity: float,
    order_type: str = "market",
    limit_price: Optional[float] = None,
    account_value: float = 100000.0
):
    """Create a new order."""
    order_manager = get_order_manager()
    risk_monitor = get_risk_monitor()
    
    # Validate inputs
    try:
        order_side = OrderSide(side.lower())
        order_type_enum = OrderType(order_type.lower())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid order parameter: {e}")
    
    # Get current price for risk check
    from qs.db import get_engine
    from sqlalchemy import text
    
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            text("SELECT adj_close FROM prices WHERE symbol = :sym ORDER BY date DESC LIMIT 1"),
            {"sym": symbol}
        ).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail=f"No price data for {symbol}")
    
    price = float(result[0])
    
    # Risk check
    allowed, reason = risk_monitor.enforce_limits(symbol, quantity, price, account_value)
    if not allowed:
        raise HTTPException(status_code=400, detail=f"Risk limit violation: {reason}")
    
    # Create order
    order = order_manager.create_order(
        symbol=symbol,
        side=order_side,
        quantity=quantity,
        order_type=order_type_enum,
        limit_price=limit_price
    )
    
    # Auto-submit and fill market orders (simulated)
    if order_type_enum == OrderType.MARKET:
        order_manager.submit_order(order.order_id)
        # Simulate immediate fill for market orders
        order_manager.fill_order(order.order_id, quantity, price, send_sms=True)
    
    return order.to_dict()


@router.get("/{order_id}")
def get_order(order_id: str):
    """Get order by ID."""
    order_manager = get_order_manager()
    order = order_manager.get_order(order_id)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return order.to_dict()


@router.get("/")
def list_orders(status: Optional[str] = None):
    """List orders, optionally filtered by status."""
    order_manager = get_order_manager()
    
    if status:
        try:
            status_enum = OrderStatus(status.lower())
            orders = order_manager.get_orders_by_status(status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    else:
        orders = order_manager.get_open_orders()
    
    return [order.to_dict() for order in orders]


@router.post("/{order_id}/cancel")
def cancel_order(order_id: str, reason: Optional[str] = None):
    """Cancel an order."""
    order_manager = get_order_manager()
    success = order_manager.cancel_order(order_id, reason)
    
    if not success:
        raise HTTPException(status_code=404, detail="Order not found or cannot be cancelled")
    
    return {"status": "cancelled", "order_id": order_id}


@router.get("/positions/current")
def get_positions():
    """Get current positions."""
    order_manager = get_order_manager()
    positions = order_manager.get_positions()
    
    # Get current prices
    from qs.db import get_engine
    from sqlalchemy import text
    import pandas as pd
    
    engine = get_engine()
    position_data = []
    
    for symbol, quantity in positions.items():
        with engine.begin() as conn:
            result = conn.execute(
                text("SELECT adj_close FROM prices WHERE symbol = :sym ORDER BY date DESC LIMIT 1"),
                {"sym": symbol}
            ).fetchone()
        
        if result:
            price = float(result[0])
            position_data.append({
                "symbol": symbol,
                "quantity": quantity,
                "price": price,
                "value": quantity * price
            })
    
    return position_data

