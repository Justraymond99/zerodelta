from __future__ import annotations

import pandas as pd
from typing import Callable
from .backtest import backtest_signal
from .utils.logger import get_logger

logger = get_logger(__name__)


def walk_forward_analysis(
    signal_name: str,
    train_period: int = 252,
    test_period: int = 63,
    step_size: int = 21,
    top_n: int = 5,
    fee: float = 0.0005,
    slip: float = 0.0005
) -> pd.DataFrame:
    """
    Perform walk-forward analysis on a signal.
    
    Parameters:
    -----------
    signal_name : str
        Signal name to test
    train_period : int
        Training period in days (default: 252 = 1 year)
    test_period : int
        Test period in days (default: 63 = 1 quarter)
    step_size : int
        Step size for rolling window (default: 21 = 1 month)
    top_n : int
        Number of top stocks to hold
    fee : float
        Transaction fee
    slip : float
        Slippage
    
    Returns:
    --------
    pd.DataFrame
        Results for each walk-forward period
    """
    from .db import get_engine
    from sqlalchemy import text
    
    engine = get_engine()
    
    # Get date range
    with engine.begin() as conn:
        dates_df = pd.read_sql(
            text("SELECT DISTINCT date FROM signals WHERE signal_name = :name ORDER BY date"),
            conn,
            params={"name": signal_name}
        )
    
    if dates_df.empty:
        logger.warning(f"No signals found for {signal_name}")
        return pd.DataFrame()
    
    dates = pd.to_datetime(dates_df['date']).sort_values()
    min_date = dates.min()
    max_date = dates.max()
    
    results = []
    current_date = min_date
    
    while current_date + pd.Timedelta(days=train_period + test_period) <= max_date:
        train_start = current_date
        train_end = current_date + pd.Timedelta(days=train_period)
        test_start = train_end
        test_end = test_start + pd.Timedelta(days=test_period)
        
        logger.info(f"Walk-forward: Train {train_start.date()} to {train_end.date()}, Test {test_start.date()} to {test_end.date()}")
        
        # Get test period stats
        # Note: This is a simplified version - in practice, you'd retrain the model
        # on the training period and generate signals for the test period
        try:
            stats = backtest_signal(
                signal_name=signal_name,
                top_n=top_n,
                fee=fee,
                slip=slip
            )
            
            if stats:
                stats['train_start'] = train_start
                stats['train_end'] = train_end
                stats['test_start'] = test_start
                stats['test_end'] = test_end
                results.append(stats)
        except Exception as e:
            logger.error(f"Error in walk-forward period {current_date}: {e}")
        
        current_date += pd.Timedelta(days=step_size)
    
    if not results:
        return pd.DataFrame()
    
    return pd.DataFrame(results)


def walk_forward_summary(results: pd.DataFrame) -> dict:
    """
    Generate summary statistics from walk-forward results.
    
    Parameters:
    -----------
    results : pd.DataFrame
        Walk-forward results from walk_forward_analysis
    
    Returns:
    --------
    dict
        Summary statistics
    """
    if results.empty:
        return {}
    
    return {
        'num_periods': len(results),
        'avg_return': float(results['total_return'].mean()),
        'std_return': float(results['total_return'].std()),
        'avg_sharpe': float(results['sharpe'].mean()),
        'avg_max_dd': float(results['max_drawdown'].mean()),
        'win_rate': float((results['total_return'] > 0).sum() / len(results)),
        'best_period': float(results['total_return'].max()),
        'worst_period': float(results['total_return'].min()),
        'consistency': float((results['total_return'] > 0).sum() / len(results))
    }

