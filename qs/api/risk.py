from __future__ import annotations

from fastapi import APIRouter, HTTPException
from qs.risk.realtime import get_risk_monitor
from qs.oms.manager import get_order_manager

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])


@router.get("/portfolio")
def get_portfolio_risk(account_value: float = 100000.0):
    """Get real-time portfolio risk metrics."""
    risk_monitor = get_risk_monitor()
    return risk_monitor.check_portfolio_risk(account_value)


@router.get("/var")
def get_var(confidence_level: float = 0.95):
    """Get Value at Risk."""
    risk_monitor = get_risk_monitor()
    return risk_monitor.check_var(confidence_level)


@router.get("/positions")
def get_positions():
    """Get current positions with risk metrics."""
    order_manager = get_order_manager()
    positions = order_manager.get_positions()
    
    from qs.db import get_engine
    from sqlalchemy import text
    
    position_data = []
    engine = get_engine()
    
    for symbol, quantity in positions.items():
        with engine.begin() as conn:
            result = conn.execute(
                text("SELECT adj_close FROM prices WHERE symbol = :sym ORDER BY date DESC LIMIT 1"),
                {"sym": symbol}
            ).fetchone()
        
        if result:
            price = float(result[0])
            position_value = quantity * price
            position_data.append({
                "symbol": symbol,
                "quantity": quantity,
                "price": price,
                "value": position_value
            })
    
    return position_data

