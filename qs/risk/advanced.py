from __future__ import annotations

from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from ..db import get_engine
from sqlalchemy import text
from ..oms.manager import get_order_manager
from ..oms.pnl import get_pnl_calculator
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AdvancedRiskController:
    """
    Advanced risk controls including drawdown limits, circuit breakers, and sector limits.
    """
    
    def __init__(
        self,
        max_drawdown_pct: float = 0.10,  # 10% max drawdown
        daily_loss_limit_pct: float = 0.05,  # 5% daily loss limit
        max_sector_concentration: float = 0.30,  # 30% max per sector
        max_correlation: float = 0.70,  # 70% max correlation
        circuit_breaker_enabled: bool = True
    ):
        self.max_drawdown_pct = max_drawdown_pct
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.max_sector_concentration = max_sector_concentration
        self.max_correlation = max_correlation
        self.circuit_breaker_enabled = circuit_breaker_enabled
        
        self.peak_equity: float = 0.0
        self.daily_start_equity: float = 0.0
        self.daily_pnl: float = 0.0
        self.circuit_breaker_triggered: bool = False
        self.circuit_breaker_time: Optional[datetime] = None
    
    def initialize(self, account_value: float):
        """Initialize risk controller with account value."""
        self.peak_equity = account_value
        self.daily_start_equity = account_value
        self.daily_pnl = 0.0
        logger.info(f"Risk controller initialized with account value: ${account_value:,.2f}")
    
    def check_drawdown(self, current_equity: float) -> Tuple[bool, str]:
        """Check if drawdown limit is exceeded."""
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        
        drawdown = (self.peak_equity - current_equity) / self.peak_equity if self.peak_equity > 0 else 0
        
        if drawdown > self.max_drawdown_pct:
            return True, f"Max drawdown exceeded: {drawdown*100:.2f}% > {self.max_drawdown_pct*100:.2f}%"
        
        return False, "OK"
    
    def check_daily_loss(self, current_equity: float) -> Tuple[bool, str]:
        """Check if daily loss limit is exceeded."""
        # Reset daily tracking if new day
        now = datetime.now()
        if not hasattr(self, '_last_check_date') or self._last_check_date.date() != now.date():
            self.daily_start_equity = current_equity
            self.daily_pnl = 0.0
            self._last_check_date = now
        
        daily_pnl = current_equity - self.daily_start_equity
        daily_loss_pct = abs(daily_pnl) / self.daily_start_equity if self.daily_start_equity > 0 and daily_pnl < 0 else 0
        
        if daily_loss_pct > self.daily_loss_limit_pct:
            return True, f"Daily loss limit exceeded: {daily_loss_pct*100:.2f}% > {self.daily_loss_limit_pct*100:.2f}%"
        
        self.daily_pnl = daily_pnl
        return False, "OK"
    
    def check_sector_concentration(self, positions: Dict[str, float], prices: Dict[str, float]) -> Tuple[bool, str]:
        """Check sector concentration limits."""
        # This is a placeholder - would need sector mapping
        # For now, just check if any single position is too large
        total_value = sum(abs(qty) * prices.get(sym, 0) for sym, qty in positions.items())
        
        if total_value == 0:
            return False, "OK"
        
        for symbol, quantity in positions.items():
            position_value = abs(quantity) * prices.get(symbol, 0)
            concentration = position_value / total_value if total_value > 0 else 0
            
            if concentration > self.max_sector_concentration:
                return True, f"Sector concentration exceeded for {symbol}: {concentration*100:.1f}%"
        
        return False, "OK"
    
    def check_circuit_breaker(self) -> Tuple[bool, str]:
        """Check if circuit breaker should be triggered."""
        if not self.circuit_breaker_enabled:
            return False, "OK"
        
        if self.circuit_breaker_triggered:
            # Check if we can reset (e.g., after 1 hour)
            if self.circuit_breaker_time:
                elapsed = (datetime.now() - self.circuit_breaker_time).total_seconds() / 3600
                if elapsed >= 1.0:  # 1 hour cooldown
                    self.circuit_breaker_triggered = False
                    self.circuit_breaker_time = None
                    logger.info("Circuit breaker reset")
                    return False, "OK"
            
            return True, "Circuit breaker active"
        
        return False, "OK"
    
    def trigger_circuit_breaker(self, reason: str):
        """Trigger circuit breaker."""
        self.circuit_breaker_triggered = True
        self.circuit_breaker_time = datetime.now()
        logger.warning(f"Circuit breaker triggered: {reason}")
    
    def enforce_all_limits(
        self,
        symbol: str,
        quantity: float,
        price: float,
        account_value: float,
        positions: Dict[str, float]
    ) -> Tuple[bool, str]:
        """Enforce all risk limits."""
        # Check circuit breaker
        is_breach, reason = self.check_circuit_breaker()
        if is_breach:
            return False, reason
        
        # Check drawdown
        current_equity = account_value
        is_breach, reason = self.check_drawdown(current_equity)
        if is_breach:
            self.trigger_circuit_breaker(reason)
            return False, reason
        
        # Check daily loss
        is_breach, reason = self.check_daily_loss(current_equity)
        if is_breach:
            self.trigger_circuit_breaker(reason)
            return False, reason
        
        # Check sector concentration
        prices = {symbol: price}
        is_breach, reason = self.check_sector_concentration(positions, prices)
        if is_breach:
            return False, reason
        
        return True, "OK"
    
    def get_risk_status(self, current_equity: float) -> Dict:
        """Get current risk status."""
        drawdown = (self.peak_equity - current_equity) / self.peak_equity if self.peak_equity > 0 else 0
        daily_loss_pct = abs(self.daily_pnl) / self.daily_start_equity if self.daily_start_equity > 0 and self.daily_pnl < 0 else 0
        
        return {
            'peak_equity': self.peak_equity,
            'current_equity': current_equity,
            'drawdown_pct': drawdown * 100,
            'daily_pnl': self.daily_pnl,
            'daily_loss_pct': daily_loss_pct * 100,
            'circuit_breaker_active': self.circuit_breaker_triggered,
            'max_drawdown_limit': self.max_drawdown_pct * 100,
            'daily_loss_limit': self.daily_loss_limit_pct * 100
        }


# Global risk controller
_risk_controller: Optional[AdvancedRiskController] = None


def get_risk_controller() -> AdvancedRiskController:
    """Get global advanced risk controller."""
    global _risk_controller
    if _risk_controller is None:
        _risk_controller = AdvancedRiskController()
    return _risk_controller

