from __future__ import annotations

from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
from ..db import get_engine
from sqlalchemy import text
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ExecutionQualityAnalyzer:
    """
    Analyzes execution quality including slippage, market impact, and fill quality.
    """
    
    def __init__(self):
        self.executions: List[Dict] = []
    
    def record_execution(
        self,
        order_id: str,
        symbol: str,
        side: str,
        quantity: float,
        expected_price: float,
        actual_price: float,
        timestamp: datetime
    ):
        """Record an execution for analysis."""
        slippage = actual_price - expected_price if side.lower() == "buy" else expected_price - actual_price
        slippage_bps = (slippage / expected_price) * 10000  # Basis points
        
        execution = {
            'order_id': order_id,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'expected_price': expected_price,
            'actual_price': actual_price,
            'slippage': slippage,
            'slippage_bps': slippage_bps,
            'timestamp': timestamp
        }
        
        self.executions.append(execution)
        self._save_execution(execution)
    
    def calculate_slippage_stats(self, symbol: Optional[str] = None) -> Dict:
        """Calculate slippage statistics."""
        execs = self.executions
        if symbol:
            execs = [e for e in execs if e['symbol'] == symbol]
        
        if not execs:
            return {}
        
        slippages = [e['slippage_bps'] for e in execs]
        
        return {
            'count': len(execs),
            'avg_slippage_bps': sum(slippages) / len(slippages),
            'median_slippage_bps': sorted(slippages)[len(slippages) // 2],
            'max_slippage_bps': max(slippages),
            'min_slippage_bps': min(slippages),
            'std_slippage_bps': pd.Series(slippages).std()
        }
    
    def calculate_market_impact(self, symbol: str, quantity: float, price: float) -> float:
        """Calculate estimated market impact."""
        # Simple model: impact = k * sqrt(quantity / average_volume) * volatility
        try:
            engine = get_engine()
            with engine.begin() as conn:
                # Get average volume
                result = conn.execute(
                    text("""
                        SELECT AVG(volume) as avg_vol, 
                               STDDEV(adj_close) / AVG(adj_close) as vol
                        FROM prices
                        WHERE symbol = :sym
                        AND date >= DATE('now', '-30 days')
                    """),
                    {"sym": symbol}
                ).fetchone()
            
            if result and result[0]:
                avg_volume = float(result[0])
                volatility = float(result[1]) if result[1] else 0.02
                
                # Market impact model
                participation_rate = quantity / avg_volume if avg_volume > 0 else 0
                impact = 0.1 * (participation_rate ** 0.5) * volatility * price
                return impact
        except Exception as e:
            logger.error(f"Error calculating market impact: {e}")
        
        return 0.0
    
    def get_execution_quality_report(self) -> pd.DataFrame:
        """Get execution quality report."""
        if not self.executions:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.executions)
        return df
    
    def _save_execution(self, execution: Dict):
        """Save execution to database."""
        try:
            engine = get_engine()
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO execution_quality (
                            order_id, symbol, side, quantity,
                            expected_price, actual_price, slippage, slippage_bps, timestamp
                        ) VALUES (
                            :order_id, :symbol, :side, :quantity,
                            :expected_price, :actual_price, :slippage, :slippage_bps, :timestamp
                        )
                    """),
                    {
                        'order_id': execution['order_id'],
                        'symbol': execution['symbol'],
                        'side': execution['side'],
                        'quantity': execution['quantity'],
                        'expected_price': execution['expected_price'],
                        'actual_price': execution['actual_price'],
                        'slippage': execution['slippage'],
                        'slippage_bps': execution['slippage_bps'],
                        'timestamp': execution['timestamp']
                    }
                )
        except Exception as e:
            logger.error(f"Error saving execution: {e}")


# Global analyzer
_execution_analyzer: Optional[ExecutionQualityAnalyzer] = None


def get_execution_analyzer() -> ExecutionQualityAnalyzer:
    """Get global execution quality analyzer."""
    global _execution_analyzer
    if _execution_analyzer is None:
        _execution_analyzer = ExecutionQualityAnalyzer()
    return _execution_analyzer

