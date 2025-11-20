from __future__ import annotations

from typing import Dict, Optional, Tuple
from ..db import get_engine
from sqlalchemy import text
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PnLCalculator:
    """Calculate profit and loss for trades."""
    
    def __init__(self):
        self.position_cost_basis: Dict[str, Dict] = {}  # symbol -> {quantity, avg_price}
    
    def get_position_cost_basis(self, symbol: str) -> Optional[Dict]:
        """Get cost basis for a position."""
        # Try in-memory first
        if symbol in self.position_cost_basis:
            return self.position_cost_basis[symbol]
        
        # Load from database
        engine = get_engine()
        with engine.begin() as conn:
            result = conn.execute(
                text("SELECT quantity, average_price FROM positions WHERE symbol = :sym"),
                {"sym": symbol}
            ).fetchone()
        
        if result:
            cost_basis = {
                "quantity": float(result[0]),
                "avg_price": float(result[1]) if result[1] else 0.0
            }
            self.position_cost_basis[symbol] = cost_basis
            return cost_basis
        
        return None
    
    def calculate_pnl(
        self,
        symbol: str,
        side: str,
        quantity: float,
        execution_price: float
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Calculate P&L for a trade.
        
        Returns:
        --------
        (realized_pnl, unrealized_pnl, pnl_pct) or (None, None, None) if no position
        """
        if side.lower() == "buy":
            # Opening or adding to position - no realized P&L yet
            return None, None, None
        
        # Selling - calculate realized P&L
        cost_basis = self.get_position_cost_basis(symbol)
        
        if not cost_basis or cost_basis["quantity"] <= 0:
            logger.warning(f"No cost basis found for {symbol}")
            return None, None, None
        
        avg_entry_price = cost_basis["avg_price"]
        if avg_entry_price == 0:
            return None, None, None
        
        # Calculate realized P&L
        realized_pnl = (execution_price - avg_entry_price) * quantity
        pnl_pct = ((execution_price - avg_entry_price) / avg_entry_price) * 100
        
        return realized_pnl, None, pnl_pct
    
    def update_cost_basis(self, symbol: str, side: str, quantity: float, price: float):
        """Update cost basis after a trade."""
        if side.lower() == "buy":
            # Adding to position
            cost_basis = self.get_position_cost_basis(symbol)
            
            if cost_basis:
                # Weighted average
                total_quantity = cost_basis["quantity"] + quantity
                total_cost = (cost_basis["quantity"] * cost_basis["avg_price"]) + (quantity * price)
                new_avg_price = total_cost / total_quantity if total_quantity > 0 else price
                
                self.position_cost_basis[symbol] = {
                    "quantity": total_quantity,
                    "avg_price": new_avg_price
                }
            else:
                # New position
                self.position_cost_basis[symbol] = {
                    "quantity": quantity,
                    "avg_price": price
                }
        else:
            # Selling - reduce position
            cost_basis = self.get_position_cost_basis(symbol)
            if cost_basis:
                remaining_quantity = cost_basis["quantity"] - quantity
                if remaining_quantity <= 0:
                    # Position closed
                    del self.position_cost_basis[symbol]
                else:
                    # Keep same average price, just reduce quantity
                    self.position_cost_basis[symbol] = {
                        "quantity": remaining_quantity,
                        "avg_price": cost_basis["avg_price"]
                    }
        
        # Update database
        self._save_position_to_db(symbol)
    
    def _save_position_to_db(self, symbol: str):
        """Save position to database."""
        if symbol not in self.position_cost_basis:
            # Delete position
            engine = get_engine()
            with engine.begin() as conn:
                conn.execute(
                    text("DELETE FROM positions WHERE symbol = :sym"),
                    {"sym": symbol}
                )
            return
        
        cost_basis = self.position_cost_basis[symbol]
        engine = get_engine()
        with engine.begin() as conn:
            # Check if exists
            result = conn.execute(
                text("SELECT COUNT(*) FROM positions WHERE symbol = :sym"),
                {"sym": symbol}
            ).fetchone()
            
            if result[0] == 0:
                # Insert
                conn.execute(
                    text("""
                        INSERT INTO positions (symbol, quantity, average_price)
                        VALUES (:sym, :qty, :avg_price)
                    """),
                    {
                        "sym": symbol,
                        "qty": cost_basis["quantity"],
                        "avg_price": cost_basis["avg_price"]
                    }
                )
            else:
                # Update
                conn.execute(
                    text("""
                        UPDATE positions
                        SET quantity = :qty, average_price = :avg_price, last_updated = now()
                        WHERE symbol = :sym
                    """),
                    {
                        "sym": symbol,
                        "qty": cost_basis["quantity"],
                        "avg_price": cost_basis["avg_price"]
                    }
                )


# Global PnL calculator instance
_pnl_calculator: Optional[PnLCalculator] = None


def get_pnl_calculator() -> PnLCalculator:
    """Get global PnL calculator instance."""
    global _pnl_calculator
    if _pnl_calculator is None:
        _pnl_calculator = PnLCalculator()
    return _pnl_calculator

