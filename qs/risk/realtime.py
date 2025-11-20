from __future__ import annotations

import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from ..db import get_engine
from sqlalchemy import text
from ..oms.manager import get_order_manager
from ..risk import (
    value_at_risk, conditional_var, portfolio_volatility,
    risk_limit_check, portfolio_correlation
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


class RealTimeRiskMonitor:
    """
    Real-time risk monitoring and position limits enforcement.
    """
    
    def __init__(
        self,
        max_position_pct: float = 0.10,
        max_portfolio_risk: float = 0.20,
        max_leverage: float = 1.0,
        max_correlation: float = 0.7
    ):
        self.max_position_pct = max_position_pct
        self.max_portfolio_risk = max_portfolio_risk
        self.max_leverage = max_leverage
        self.max_correlation = max_correlation
        self.order_manager = get_order_manager()
    
    def get_current_positions(self) -> Dict[str, float]:
        """Get current positions."""
        return self.order_manager.get_positions()
    
    def get_portfolio_value(self, prices: Dict[str, float]) -> float:
        """Calculate total portfolio value."""
        positions = self.get_current_positions()
        position_value = sum(positions.get(sym, 0) * price for sym, price in prices.items())
        return position_value
    
    def check_position_limit(self, symbol: str, quantity: float, price: float, account_value: float) -> tuple[bool, str]:
        """Check if position violates limits."""
        position_value = quantity * price
        return risk_limit_check(account_value, position_value, self.max_position_pct, self.max_portfolio_risk)
    
    def check_portfolio_risk(self, account_value: float) -> Dict:
        """Check overall portfolio risk."""
        positions = self.get_current_positions()
        
        if not positions:
            return {
                "status": "ok",
                "total_exposure": 0.0,
                "leverage": 0.0,
                "warnings": []
            }
        
        # Get current prices
        engine = get_engine()
        prices = {}
        with engine.begin() as conn:
            for symbol in positions.keys():
                result = conn.execute(
                    text("SELECT adj_close FROM prices WHERE symbol = :sym ORDER BY date DESC LIMIT 1"),
                    {"sym": symbol}
                ).fetchone()
                if result:
                    prices[symbol] = float(result[0])
        
        # Calculate exposure
        total_exposure = sum(abs(qty) * prices.get(sym, 0) for sym, qty in positions.items())
        leverage = total_exposure / account_value if account_value > 0 else 0.0
        
        warnings = []
        
        # Check leverage
        if leverage > self.max_leverage:
            warnings.append(f"Leverage {leverage:.2f}x exceeds limit {self.max_leverage:.2f}x")
        
        # Check position concentration
        for symbol, qty in positions.items():
            position_value = abs(qty) * prices.get(symbol, 0)
            position_pct = position_value / account_value if account_value > 0 else 0
            if position_pct > self.max_position_pct:
                warnings.append(f"Position {symbol}: {position_pct*100:.1f}% exceeds limit {self.max_position_pct*100:.1f}%")
        
        # Check correlation
        if len(positions) > 1:
            try:
                returns_df = self._get_returns_dataframe(list(positions.keys()))
                if not returns_df.empty:
                    corr_matrix = portfolio_correlation(returns_df)
                    max_corr = corr_matrix.max().max()
                    if max_corr > self.max_correlation:
                        warnings.append(f"High correlation detected: {max_corr:.2f}")
            except Exception as e:
                logger.warning(f"Error checking correlation: {e}")
        
        status = "warning" if warnings else "ok"
        if leverage > self.max_leverage * 1.5:
            status = "critical"
        
        return {
            "status": status,
            "total_exposure": total_exposure,
            "leverage": leverage,
            "num_positions": len(positions),
            "warnings": warnings,
            "timestamp": datetime.now().isoformat()
        }
    
    def check_var(self, confidence_level: float = 0.95) -> Dict:
        """Calculate real-time VaR."""
        positions = self.get_current_positions()
        
        if not positions:
            return {"var": 0.0, "cvar": 0.0}
        
        # Get returns
        returns_df = self._get_returns_dataframe(list(positions.keys()))
        if returns_df.empty:
            return {"var": 0.0, "cvar": 0.0}
        
        # Calculate portfolio returns
        # Simplified: equal weight for now
        portfolio_returns = returns_df.mean(axis=1)
        
        var = value_at_risk(portfolio_returns, confidence_level)
        cvar = conditional_var(portfolio_returns, confidence_level)
        
        return {
            "var": var,
            "cvar": cvar,
            "confidence_level": confidence_level,
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_returns_dataframe(self, symbols: List[str], days: int = 30) -> pd.DataFrame:
        """Get returns dataframe for symbols."""
        engine = get_engine()
        with engine.begin() as conn:
            placeholders = ",".join([f":sym{i}" for i in range(len(symbols))])
            params = {f"sym{i}": sym for i, sym in enumerate(symbols)}
            
            prices_df = pd.read_sql(
                text(f"""
                    SELECT symbol, date, adj_close
                    FROM prices
                    WHERE symbol IN ({placeholders})
                    AND date >= DATE('now', '-{days} days')
                    ORDER BY symbol, date
                """),
                conn,
                params=params
            )
        
        if prices_df.empty:
            return pd.DataFrame()
        
        # Pivot and calculate returns
        prices_pivot = prices_df.pivot(index='date', columns='symbol', values='adj_close')
        returns = prices_pivot.pct_change().dropna()
        
        return returns
    
    def enforce_limits(self, symbol: str, quantity: float, price: float, account_value: float) -> tuple[bool, str]:
        """Enforce all risk limits before allowing trade."""
        # Position limit
        is_violation, reason = self.check_position_limit(symbol, quantity, price, account_value)
        if is_violation:
            return False, reason
        
        # Portfolio risk check
        risk_status = self.check_portfolio_risk(account_value)
        if risk_status["status"] == "critical":
            return False, f"Portfolio risk critical: {risk_status['warnings']}"
        
        return True, "OK"


# Global risk monitor instance
_risk_monitor: Optional[RealTimeRiskMonitor] = None


def get_risk_monitor() -> RealTimeRiskMonitor:
    """Get global risk monitor instance."""
    global _risk_monitor
    if _risk_monitor is None:
        _risk_monitor = RealTimeRiskMonitor()
    return _risk_monitor

