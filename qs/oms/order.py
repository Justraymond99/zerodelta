from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4
from ..utils.logger import get_logger

logger = get_logger(__name__)


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    """
    Order representation with full lifecycle tracking.
    """
    order_id: str = field(default_factory=lambda: str(uuid4()))
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    quantity: float = 0.0
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    average_fill_price: Optional[float] = None
    fills: list[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None
    
    def submit(self):
        """Submit order."""
        if self.status != OrderStatus.PENDING:
            raise ValueError(f"Cannot submit order in status: {self.status}")
        self.status = OrderStatus.SUBMITTED
        self.submitted_at = datetime.now()
        logger.info(f"Order {self.order_id} submitted: {self.side.value} {self.quantity} {self.symbol}")
    
    def fill(self, quantity: float, price: float, fill_id: Optional[str] = None):
        """Record a fill."""
        if self.status not in [OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]:
            raise ValueError(f"Cannot fill order in status: {self.status}")
        
        self.filled_quantity += quantity
        self.fills.append({
            "fill_id": fill_id or str(uuid4()),
            "quantity": quantity,
            "price": price,
            "timestamp": datetime.now().isoformat()
        })
        
        # Update average fill price
        total_value = sum(f["quantity"] * f["price"] for f in self.fills)
        self.average_fill_price = total_value / self.filled_quantity if self.filled_quantity > 0 else None
        
        # Update status
        if self.filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
            self.filled_at = datetime.now()
            logger.info(f"Order {self.order_id} filled: {self.filled_quantity} @ ${self.average_fill_price:.2f}")
        else:
            self.status = OrderStatus.PARTIALLY_FILLED
            logger.info(f"Order {self.order_id} partially filled: {self.filled_quantity}/{self.quantity}")
    
    def cancel(self, reason: Optional[str] = None):
        """Cancel order."""
        if self.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            raise ValueError(f"Cannot cancel order in status: {self.status}")
        
        self.status = OrderStatus.CANCELLED
        self.cancelled_at = datetime.now()
        self.notes = reason or self.notes
        logger.info(f"Order {self.order_id} cancelled: {reason}")
    
    def reject(self, reason: str):
        """Reject order."""
        if self.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            raise ValueError(f"Cannot reject order in status: {self.status}")
        
        self.status = OrderStatus.REJECTED
        self.rejected_at = datetime.now()
        self.rejection_reason = reason
        logger.warning(f"Order {self.order_id} rejected: {reason}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert order to dictionary."""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "order_type": self.order_type.value,
            "limit_price": self.limit_price,
            "stop_price": self.stop_price,
            "status": self.status.value,
            "filled_quantity": self.filled_quantity,
            "average_fill_price": self.average_fill_price,
            "fills": self.fills,
            "created_at": self.created_at.isoformat(),
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
            "rejection_reason": self.rejection_reason,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Order":
        """Create order from dictionary."""
        order = cls(
            order_id=data.get("order_id", str(uuid4())),
            symbol=data["symbol"],
            side=OrderSide(data["side"]),
            quantity=data["quantity"],
            order_type=OrderType(data.get("order_type", "market")),
            limit_price=data.get("limit_price"),
            stop_price=data.get("stop_price"),
            status=OrderStatus(data.get("status", "pending")),
            filled_quantity=data.get("filled_quantity", 0.0),
            average_fill_price=data.get("average_fill_price"),
            fills=data.get("fills", []),
            notes=data.get("notes")
        )
        
        # Parse timestamps
        if data.get("created_at"):
            order.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("submitted_at"):
            order.submitted_at = datetime.fromisoformat(data["submitted_at"])
        if data.get("filled_at"):
            order.filled_at = datetime.fromisoformat(data["filled_at"])
        if data.get("cancelled_at"):
            order.cancelled_at = datetime.fromisoformat(data["cancelled_at"])
        if data.get("rejected_at"):
            order.rejected_at = datetime.fromisoformat(data["rejected_at"])
        
        return order

