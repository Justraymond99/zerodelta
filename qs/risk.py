from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Literal


def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """
    Kelly Criterion for optimal position sizing.
    
    Parameters:
    -----------
    win_rate : float
        Probability of winning (0-1)
    avg_win : float
        Average win amount (as fraction, e.g., 0.05 for 5%)
    avg_loss : float
        Average loss amount (as fraction, positive value, e.g., 0.03 for 3%)
    
    Returns:
    --------
    float
        Optimal fraction of capital to bet (0-1)
    """
    if avg_loss == 0:
        return 0.0
    q = 1 - win_rate
    kelly = (win_rate * avg_win - q * avg_loss) / avg_win
    return max(0.0, min(1.0, kelly))  # Clamp between 0 and 1


def volatility_targeting(
    target_vol: float,
    current_vol: float,
    base_position: float = 1.0
) -> float:
    """
    Scale position size based on volatility targeting.
    
    Parameters:
    -----------
    target_vol : float
        Target volatility (annualized)
    current_vol : float
        Current volatility (annualized)
    base_position : float
        Base position size
    
    Returns:
    --------
    float
        Scaled position size
    """
    if current_vol == 0:
        return base_position
    return base_position * (target_vol / current_vol)


def risk_parity_weights(returns: pd.DataFrame, target_vol: float = 0.15) -> pd.Series:
    """
    Calculate risk parity weights (equal risk contribution).
    
    Parameters:
    -----------
    returns : pd.DataFrame
        Returns matrix (dates x assets)
    target_vol : float
        Target portfolio volatility
    
    Returns:
    --------
    pd.Series
        Asset weights
    """
    if returns.empty:
        return pd.Series(dtype=float)
    
    # Calculate covariance matrix
    cov = returns.cov() * 252  # Annualize
    
    # Inverse volatility weights (simplified risk parity)
    vols = np.sqrt(np.diag(cov))
    inv_vol = 1.0 / vols
    weights = inv_vol / inv_vol.sum()
    
    # Scale to target volatility
    portfolio_vol = np.sqrt(weights @ cov @ weights)
    if portfolio_vol > 0:
        scale = target_vol / portfolio_vol
        weights = weights * scale
        weights = weights / weights.sum()  # Renormalize
    
    return pd.Series(weights, index=returns.columns)


def portfolio_correlation(returns: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate correlation matrix of portfolio returns.
    
    Parameters:
    -----------
    returns : pd.DataFrame
        Returns matrix (dates x assets)
    
    Returns:
    --------
    pd.DataFrame
        Correlation matrix
    """
    return returns.corr()


def portfolio_volatility(weights: pd.Series | np.ndarray, cov_matrix: pd.DataFrame | np.ndarray) -> float:
    """
    Calculate portfolio volatility.
    
    Parameters:
    -----------
    weights : pd.Series or np.ndarray
        Portfolio weights
    cov_matrix : pd.DataFrame or np.ndarray
        Covariance matrix
    
    Returns:
    --------
    float
        Annualized portfolio volatility
    """
    if isinstance(weights, pd.Series):
        weights = weights.values
    if isinstance(cov_matrix, pd.DataFrame):
        cov_matrix = cov_matrix.values
    
    portfolio_var = weights @ cov_matrix @ weights
    return float(np.sqrt(portfolio_var * 252))  # Annualize


def value_at_risk(
    returns: pd.Series | np.ndarray,
    confidence_level: float = 0.95,
    method: Literal["historical", "parametric"] = "historical"
) -> float:
    """
    Calculate Value at Risk (VaR).
    
    Parameters:
    -----------
    returns : pd.Series or np.ndarray
        Returns series
    confidence_level : float
        Confidence level (e.g., 0.95 for 95% VaR)
    method : str
        "historical" or "parametric"
    
    Returns:
    --------
    float
        VaR (negative value, e.g., -0.05 for 5% loss)
    """
    if isinstance(returns, pd.Series):
        returns = returns.values
    
    if method == "historical":
        percentile = (1 - confidence_level) * 100
        var = np.percentile(returns, percentile)
    else:  # parametric (assumes normal distribution)
        mean = np.mean(returns)
        std = np.std(returns, ddof=1)
        from scipy.stats import norm
        z_score = norm.ppf(1 - confidence_level)
        var = mean + z_score * std
    
    return float(var)


def conditional_var(
    returns: pd.Series | np.ndarray,
    confidence_level: float = 0.95
) -> float:
    """
    Conditional Value at Risk (CVaR) / Expected Shortfall.
    
    Parameters:
    -----------
    returns : pd.Series or np.ndarray
        Returns series
    confidence_level : float
        Confidence level
    
    Returns:
    --------
    float
        CVaR (average of losses beyond VaR)
    """
    var = value_at_risk(returns, confidence_level)
    
    if isinstance(returns, pd.Series):
        returns = returns.values
    
    losses_beyond_var = returns[returns <= var]
    if len(losses_beyond_var) == 0:
        return var
    
    return float(np.mean(losses_beyond_var))


def stop_loss_check(
    entry_price: float,
    current_price: float,
    stop_loss_pct: float
) -> bool:
    """
    Check if stop loss should be triggered.
    
    Parameters:
    -----------
    entry_price : float
        Entry price
    current_price : float
        Current price
    stop_loss_pct : float
        Stop loss percentage (e.g., 0.05 for 5%)
    
    Returns:
    --------
    bool
        True if stop loss triggered
    """
    loss_pct = (current_price - entry_price) / entry_price
    return loss_pct <= -stop_loss_pct


def take_profit_check(
    entry_price: float,
    current_price: float,
    take_profit_pct: float
) -> bool:
    """
    Check if take profit should be triggered.
    
    Parameters:
    -----------
    entry_price : float
        Entry price
    current_price : float
        Current price
    take_profit_pct : float
        Take profit percentage (e.g., 0.10 for 10%)
    
    Returns:
    --------
    bool
        True if take profit triggered
    """
    profit_pct = (current_price - entry_price) / entry_price
    return profit_pct >= take_profit_pct


def position_size_kelly(
    account_value: float,
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    max_position_pct: float = 0.25
) -> float:
    """
    Calculate position size using Kelly Criterion.
    
    Parameters:
    -----------
    account_value : float
        Total account value
    win_rate : float
        Win rate (0-1)
    avg_win : float
        Average win (as fraction)
    avg_loss : float
        Average loss (as fraction, positive)
    max_position_pct : float
        Maximum position as % of account (default: 25%)
    
    Returns:
    --------
    float
        Position size in dollars
    """
    kelly_fraction = kelly_criterion(win_rate, avg_win, avg_loss)
    # Use fractional Kelly (half) for safety
    kelly_fraction = kelly_fraction * 0.5
    kelly_fraction = min(kelly_fraction, max_position_pct)
    return account_value * kelly_fraction


def risk_limit_check(
    portfolio_value: float,
    position_value: float,
    max_position_pct: float = 0.10,
    max_portfolio_risk: float = 0.20
) -> tuple[bool, str]:
    """
    Check if position violates risk limits.
    
    Parameters:
    -----------
    portfolio_value : float
        Total portfolio value
    position_value : float
        Value of new position
    max_position_pct : float
        Maximum position as % of portfolio
    max_portfolio_risk : float
        Maximum portfolio risk (not used in simple check)
    
    Returns:
    --------
    tuple[bool, str]
        (is_violation, reason)
    """
    position_pct = position_value / portfolio_value if portfolio_value > 0 else 0
    
    if position_pct > max_position_pct:
        return True, f"Position {position_pct:.2%} exceeds limit {max_position_pct:.2%}"
    
    return False, "OK"

