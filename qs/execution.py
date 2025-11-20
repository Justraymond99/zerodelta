from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Literal
from datetime import datetime, timedelta


def twap_execution(
    total_quantity: float,
    start_time: datetime,
    end_time: datetime,
    n_intervals: int = 10
) -> pd.DataFrame:
    """
    Generate TWAP (Time-Weighted Average Price) execution schedule.
    
    Parameters:
    -----------
    total_quantity : float
        Total quantity to execute
    start_time : datetime
        Start time
    end_time : datetime
        End time
    n_intervals : int
        Number of intervals
    
    Returns:
    --------
    pd.DataFrame
        Execution schedule with columns: time, quantity
    """
    time_delta = (end_time - start_time) / n_intervals
    quantity_per_interval = total_quantity / n_intervals
    
    schedule = []
    current_time = start_time
    
    for i in range(n_intervals):
        schedule.append({
            'time': current_time,
            'quantity': quantity_per_interval
        })
        current_time += time_delta
    
    return pd.DataFrame(schedule)


def vwap_execution(
    total_quantity: float,
    volume_profile: pd.Series,
    start_time: datetime | None = None,
    end_time: datetime | None = None
) -> pd.DataFrame:
    """
    Generate VWAP (Volume-Weighted Average Price) execution schedule.
    
    Parameters:
    -----------
    total_quantity : float
        Total quantity to execute
    volume_profile : pd.Series
        Expected volume profile (time-indexed)
    start_time : datetime, optional
        Start time (if None, uses volume_profile index start)
    end_time : datetime, optional
        End time (if None, uses volume_profile index end)
    
    Returns:
    --------
    pd.DataFrame
        Execution schedule
    """
    if start_time is None:
        start_time = volume_profile.index[0]
    if end_time is None:
        end_time = volume_profile.index[-1]
    
    # Filter volume profile to time range
    mask = (volume_profile.index >= start_time) & (volume_profile.index <= end_time)
    profile = volume_profile[mask]
    
    # Normalize volume profile
    total_volume = profile.sum()
    if total_volume == 0:
        # Equal distribution if no volume data
        quantity_per_period = total_quantity / len(profile)
        schedule = pd.DataFrame({
            'time': profile.index,
            'quantity': quantity_per_period
        })
    else:
        # Weight by volume
        weights = profile / total_volume
        quantities = weights * total_quantity
        
        schedule = pd.DataFrame({
            'time': profile.index,
            'quantity': quantities.values
        })
    
    return schedule


def market_impact(
    quantity: float,
    average_volume: float,
    volatility: float,
    k: float = 0.1
) -> float:
    """
    Estimate market impact cost.
    
    Parameters:
    -----------
    quantity : float
        Order quantity
    average_volume : float
        Average daily volume
    volatility : float
        Stock volatility
    k : float
        Impact coefficient (default: 0.1)
    
    Returns:
    --------
    float
        Estimated market impact (as fraction, e.g., 0.001 for 0.1%)
    """
    participation_rate = quantity / average_volume if average_volume > 0 else 0
    impact = k * np.sqrt(participation_rate) * volatility
    return float(impact)


def optimal_execution(
    total_quantity: float,
    start_time: datetime,
    end_time: datetime,
    method: Literal["twap", "vwap"] = "twap",
    volume_profile: pd.Series | None = None,
    n_intervals: int = 10
) -> pd.DataFrame:
    """
    Generate optimal execution schedule.
    
    Parameters:
    -----------
    total_quantity : float
        Total quantity to execute
    start_time : datetime
        Start time
    end_time : datetime
        End time
    method : str
        "twap" or "vwap"
    volume_profile : pd.Series, optional
        Volume profile for VWAP
    n_intervals : int
        Number of intervals for TWAP
    
    Returns:
    --------
    pd.DataFrame
        Execution schedule
    """
    if method == "twap":
        return twap_execution(total_quantity, start_time, end_time, n_intervals)
    elif method == "vwap":
        if volume_profile is None:
            raise ValueError("volume_profile required for VWAP execution")
        return vwap_execution(total_quantity, volume_profile, start_time, end_time)
    else:
        raise ValueError(f"Unknown method: {method}")


def execution_cost_analysis(
    execution_schedule: pd.DataFrame,
    market_prices: pd.Series,
    average_volume: float,
    volatility: float
) -> dict:
    """
    Analyze execution costs.
    
    Parameters:
    -----------
    execution_schedule : pd.DataFrame
        Execution schedule with 'time' and 'quantity' columns
    market_prices : pd.Series
        Market prices (time-indexed)
    average_volume : float
        Average daily volume
    volatility : float
        Stock volatility
    
    Returns:
    --------
    dict
        Cost analysis results
    """
    # Align execution times with market prices
    costs = []
    total_cost = 0
    total_quantity = 0
    
    for _, row in execution_schedule.iterrows():
        exec_time = row['time']
        quantity = row['quantity']
        
        # Find closest market price
        price_idx = market_prices.index.get_indexer([exec_time], method='nearest')[0]
        exec_price = market_prices.iloc[price_idx]
        
        # Calculate market impact
        impact = market_impact(quantity, average_volume, volatility)
        adjusted_price = exec_price * (1 + impact)
        
        cost = quantity * adjusted_price
        costs.append(cost)
        total_cost += cost
        total_quantity += quantity
    
    avg_price = total_cost / total_quantity if total_quantity > 0 else 0
    total_impact = sum([market_impact(q, average_volume, volatility) * q for q in execution_schedule['quantity']])
    
    return {
        'total_cost': float(total_cost),
        'total_quantity': float(total_quantity),
        'average_price': float(avg_price),
        'total_impact_cost': float(total_impact),
        'execution_details': pd.DataFrame({
            'time': execution_schedule['time'],
            'quantity': execution_schedule['quantity'],
            'cost': costs
        })
    }

