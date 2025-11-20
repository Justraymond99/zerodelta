from __future__ import annotations

from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
from ..db import get_engine
from sqlalchemy import text
from ..utils.logger import get_logger
from .base import Strategy

logger = get_logger(__name__)


class StrategyManager:
    """
    Manages multiple trading strategies.
    """
    
    def __init__(self):
        self.strategies: Dict[str, Strategy] = {}
        self.strategy_configs: Dict[str, Dict] = {}
        self.strategy_performance: Dict[str, Dict] = {}
    
    def register_strategy(self, strategy: Strategy, config: Optional[Dict] = None):
        """Register a strategy."""
        self.strategies[strategy.name] = strategy
        self.strategy_configs[strategy.name] = config or {
            'enabled': True,
            'allocation': 1.0,  # Fraction of capital
            'min_signal_threshold': 0.5,
            'max_positions': 5
        }
        logger.info(f"Registered strategy: {strategy.name}")
    
    def enable_strategy(self, strategy_name: str):
        """Enable a strategy."""
        if strategy_name in self.strategy_configs:
            self.strategy_configs[strategy_name]['enabled'] = True
            logger.info(f"Enabled strategy: {strategy_name}")
    
    def disable_strategy(self, strategy_name: str):
        """Disable a strategy."""
        if strategy_name in self.strategy_configs:
            self.strategy_configs[strategy_name]['enabled'] = False
            logger.info(f"Disabled strategy: {strategy_name}")
    
    def set_allocation(self, strategy_name: str, allocation: float):
        """Set capital allocation for a strategy."""
        if strategy_name in self.strategy_configs:
            self.strategy_configs[strategy_name]['allocation'] = allocation
            logger.info(f"Set allocation for {strategy_name}: {allocation*100:.1f}%")
    
    def get_enabled_strategies(self) -> List[str]:
        """Get list of enabled strategies."""
        return [
            name for name, config in self.strategy_configs.items()
            if config.get('enabled', False)
        ]
    
    def generate_signals(self, strategy_name: str, data: pd.DataFrame) -> pd.DataFrame:
        """Generate signals for a strategy."""
        if strategy_name not in self.strategies:
            logger.error(f"Strategy not found: {strategy_name}")
            return pd.DataFrame()
        
        strategy = self.strategies[strategy_name]
        return strategy.generate_signals(data)
    
    def get_strategy_performance(self, strategy_name: str) -> Dict:
        """Get performance metrics for a strategy."""
        if strategy_name not in self.strategy_performance:
            return {}
        return self.strategy_performance[strategy_name]
    
    def update_performance(self, strategy_name: str, metrics: Dict):
        """Update performance metrics for a strategy."""
        self.strategy_performance[strategy_name] = metrics
    
    def compare_strategies(self) -> pd.DataFrame:
        """Compare performance of all strategies."""
        if not self.strategy_performance:
            return pd.DataFrame()
        
        rows = []
        for name, perf in self.strategy_performance.items():
            row = {'strategy': name, **perf}
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    def get_strategy_config(self, strategy_name: str) -> Dict:
        """Get configuration for a strategy."""
        return self.strategy_configs.get(strategy_name, {})
    
    def list_strategies(self) -> List[Dict]:
        """List all registered strategies with their status."""
        return [
            {
                'name': name,
                'enabled': config.get('enabled', False),
                'allocation': config.get('allocation', 0.0),
                'performance': self.strategy_performance.get(name, {})
            }
            for name, config in self.strategy_configs.items()
        ]


# Global strategy manager
_strategy_manager: Optional[StrategyManager] = None


def get_strategy_manager() -> StrategyManager:
    """Get global strategy manager."""
    global _strategy_manager
    if _strategy_manager is None:
        _strategy_manager = StrategyManager()
    return _strategy_manager

