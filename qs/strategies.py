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


class MomentumStrategy(Strategy):
    """Simple momentum strategy."""
    
    def __init__(self, lookback: int = 20, top_n: int = 5):
        super().__init__("momentum", {"lookback": lookback, "top_n": top_n})
        self.lookback = lookback
        self.top_n = top_n
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate signals based on momentum."""
        signals = []
        
        for symbol in data['symbol'].unique():
            symbol_data = data[data['symbol'] == symbol].sort_values('date')
            if len(symbol_data) < self.lookback:
                continue
            
            # Calculate momentum
            current_price = symbol_data['adj_close'].iloc[-1]
            past_price = symbol_data['adj_close'].iloc[-self.lookback]
            momentum = (current_price / past_price) - 1.0
            
            signals.append({
                'symbol': symbol,
                'date': symbol_data['date'].iloc[-1],
                'score': momentum,
                'signal': 'buy' if momentum > 0 else 'sell'
            })
        
        return pd.DataFrame(signals)
    
    def calculate_position_size(self, signal: float, account_value: float, **kwargs) -> float:
        """Equal weight for top N positions."""
        return account_value / self.top_n


class MeanReversionStrategy(Strategy):
    """Mean reversion strategy using z-score."""
    
    def __init__(self, lookback: int = 20, entry_threshold: float = -2.0, exit_threshold: float = 0.0):
        super().__init__("mean_reversion", {
            "lookback": lookback,
            "entry_threshold": entry_threshold,
            "exit_threshold": exit_threshold
        })
        self.lookback = lookback
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate signals based on mean reversion."""
        signals = []
        
        for symbol in data['symbol'].unique():
            symbol_data = data[data['symbol'] == symbol].sort_values('date')
            if len(symbol_data) < self.lookback:
                continue
            
            # Calculate z-score
            prices = symbol_data['adj_close']
            mean = prices.tail(self.lookback).mean()
            std = prices.tail(self.lookback).std()
            
            if std == 0:
                continue
            
            z_score = (prices.iloc[-1] - mean) / std
            
            signals.append({
                'symbol': symbol,
                'date': symbol_data['date'].iloc[-1],
                'score': -z_score,  # Negative z-score is good for mean reversion
                'signal': 'buy' if z_score < self.entry_threshold else 'sell' if z_score > self.exit_threshold else 'hold'
            })
        
        return pd.DataFrame(signals)
    
    def calculate_position_size(self, signal: float, account_value: float, **kwargs) -> float:
        """Position size based on signal strength."""
        max_position = account_value * 0.1  # Max 10% per position
        return min(max_position, account_value * abs(signal) * 0.1)


class MLStrategy(Strategy):
    """ML-based strategy using model predictions."""
    
    def __init__(self, model_name: str = "xgb_alpha"):
        super().__init__("ml_strategy", {"model_name": model_name})
        self.model_name = model_name
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate signals from ML model predictions."""
        from ..signal import generate_signals
        from ..db import get_engine
        from sqlalchemy import text
        
        # Generate signals using existing infrastructure
        generate_signals(model_name=self.model_name)
        
        # Load signals from database
        engine = get_engine()
        with engine.begin() as conn:
            signals_df = pd.read_sql(
                text("SELECT symbol, date, score FROM signals WHERE signal_name = :name"),
                conn,
                params={"name": self.model_name}
            )
        
        signals_df['signal'] = signals_df['score'].apply(lambda x: 'buy' if x > 0 else 'sell')
        return signals_df
    
    def calculate_position_size(self, signal: float, account_value: float, **kwargs) -> float:
        """Position size based on signal confidence."""
        # Scale by signal strength
        base_size = account_value * 0.05  # Base 5%
        scaled_size = base_size * (1 + abs(signal))
        return min(scaled_size, account_value * 0.2)  # Cap at 20%


def create_strategy(strategy_type: str, **kwargs) -> Strategy:
    """
    Factory function to create strategies.
    
    Parameters:
    -----------
    strategy_type : str
        Type of strategy: "momentum", "mean_reversion", "ml"
    **kwargs
        Strategy-specific parameters
    
    Returns:
    --------
    Strategy
        Strategy instance
    """
    if strategy_type == "momentum":
        return MomentumStrategy(**kwargs)
    elif strategy_type == "mean_reversion":
        return MeanReversionStrategy(**kwargs)
    elif strategy_type == "ml":
        return MLStrategy(**kwargs)
    else:
        raise ValueError(f"Unknown strategy type: {strategy_type}")

