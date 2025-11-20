from __future__ import annotations

from typing import Optional, Dict
from datetime import datetime
from .twilio_client import send_sms_update, get_allowed_numbers
from ..utils.logger import get_logger

logger = get_logger(__name__)


def format_trade_confirmation(
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    realized_pnl: Optional[float] = None,
    pnl_pct: Optional[float] = None,
    order_id: Optional[str] = None,
    is_paper: bool = False
) -> str:
    """
    Format trade confirmation message.
    
    Parameters:
    -----------
    symbol : str
        Trading symbol
    side : str
        "buy" or "sell"
    quantity : float
        Quantity traded
    price : float
        Execution price
    realized_pnl : float, optional
        Realized profit/loss
    pnl_pct : float, optional
        P&L percentage
    order_id : str, optional
        Order ID
    is_paper : bool
        Whether this is paper trading
    
    Returns:
    --------
    str
        Formatted SMS message
    """
    mode = "📝 PAPER" if is_paper else "💰 LIVE"
    action = "🟢 BUY" if side.lower() == "buy" else "🔴 SELL"
    
    lines = [
        f"{mode} TRADE EXECUTED",
        "",
        f"{action} {quantity:.2f} {symbol}",
        f"Price: ${price:.2f}",
        f"Value: ${quantity * price:,.2f}"
    ]
    
    if order_id:
        lines.append(f"Order ID: {order_id[:8]}")
    
    if realized_pnl is not None and pnl_pct is not None:
        lines.append("")
        if realized_pnl >= 0:
            lines.append(f"✅ Realized P&L: +${realized_pnl:,.2f} (+{pnl_pct:.2f}%)")
        else:
            lines.append(f"❌ Realized P&L: ${realized_pnl:,.2f} ({pnl_pct:.2f}%)")
    
    lines.append("")
    lines.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return "\n".join(lines)


def send_trade_confirmation(
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    realized_pnl: Optional[float] = None,
    pnl_pct: Optional[float] = None,
    order_id: Optional[str] = None,
    is_paper: bool = False
) -> bool:
    """
    Send trade confirmation via SMS.
    
    Returns:
    --------
    bool
        True if sent successfully
    """
    try:
        message = format_trade_confirmation(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            realized_pnl=realized_pnl,
            pnl_pct=pnl_pct,
            order_id=order_id,
            is_paper=is_paper
        )
        
        # Send to all allowed numbers
        allowed_numbers = get_allowed_numbers()
        if not allowed_numbers:
            logger.warning("No allowed numbers configured for trade confirmations")
            return False
        
        success = send_sms_update(message)
        if success:
            logger.info(f"Trade confirmation sent: {side} {quantity} {symbol} @ ${price:.2f}")
        else:
            logger.warning("Failed to send trade confirmation")
        
        return success
    
    except Exception as e:
        logger.error(f"Error sending trade confirmation: {e}")
        return False

