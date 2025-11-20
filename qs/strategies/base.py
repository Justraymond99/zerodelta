from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd
from ..utils.logger import get_logger

logger = get_logger(__name__)


class Strategy(ABC):
    """
    Base class for trading strategies.
    
    Strategies define how to generate signals and manage positions.
    """
    
    def __init__(self, name: str, params: Dict[str, Any] | None = None):
        self.name = name
        self.params = params or {}
        self.logger = get_logger(f"strategy.{name}")
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals from data.
        
        Parameters:
        -----------
        data : pd.DataFrame
            Price/feature data
        
        Returns:
        --------
        pd.DataFrame
            Signals with columns: symbol, date, score, signal (optional)
        """
        pass
    
    @abstractmethod
    def calculate_position_size(self, signal: float, account_value: float, **kwargs) -> float:
        """
        Calculate position size based on signal.
        
        Parameters:
        -----------
        signal : float
            Signal strength/score
        account_value : float
            Current account value
        
        Returns:
        --------
        float
            Position size (in dollars or shares)
        """
        pass

