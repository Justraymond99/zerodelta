from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import Literal


def mean_variance_optimize(
    returns: pd.DataFrame,
    target_return: float | None = None,
    risk_free_rate: float = 0.0,
    method: Literal["max_sharpe", "min_vol", "max_return"] = "max_sharpe"
) -> pd.Series:
    """
    Mean-variance portfolio optimization.
    
    Parameters:
    -----------
    returns : pd.DataFrame
        Returns matrix (dates x assets)
    target_return : float, optional
        Target return (for min_vol with target)
    risk_free_rate : float
        Risk-free rate
    method : str
        Optimization objective: "max_sharpe", "min_vol", or "max_return"
    
    Returns:
    --------
    pd.Series
        Optimal weights
    """
    if returns.empty:
        return pd.Series(dtype=float)
    
    # Annualized returns and covariance
    mean_returns = returns.mean() * 252
    cov_matrix = returns.cov() * 252
    
    n_assets = len(mean_returns)
    
    def portfolio_return(weights: np.ndarray) -> float:
        return np.sum(mean_returns * weights)
    
    def portfolio_volatility(weights: np.ndarray) -> float:
        return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
    
    def negative_sharpe(weights: np.ndarray) -> float:
        ret = portfolio_return(weights)
        vol = portfolio_volatility(weights)
        if vol == 0:
            return 1e10
        return -(ret - risk_free_rate) / vol
    
    # Constraints: weights sum to 1
    constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
    
    # Bounds: weights between 0 and 1 (long only)
    bounds = tuple((0, 1) for _ in range(n_assets))
    
    # Initial guess: equal weights
    initial_weights = np.array([1.0 / n_assets] * n_assets)
    
    if method == "max_sharpe":
        result = minimize(
            negative_sharpe,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
    elif method == "min_vol":
        if target_return is not None:
            # Minimize volatility with target return constraint
            constraints = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
                {'type': 'eq', 'fun': lambda w: portfolio_return(w) - target_return}
            ]
        result = minimize(
            portfolio_volatility,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
    else:  # max_return
        # Maximize return with volatility constraint
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        result = minimize(
            lambda w: -portfolio_return(w),
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
    
    if result.success:
        weights = pd.Series(result.x, index=mean_returns.index)
        # Normalize to ensure they sum to 1
        weights = weights / weights.sum()
        return weights
    else:
        # Fallback to equal weights
        return pd.Series(1.0 / n_assets, index=mean_returns.index)


def risk_parity_optimize(returns: pd.DataFrame, target_vol: float = 0.15) -> pd.Series:
    """
    Risk parity optimization (equal risk contribution).
    
    Parameters:
    -----------
    returns : pd.DataFrame
        Returns matrix (dates x assets)
    target_vol : float
        Target portfolio volatility
    
    Returns:
    --------
    pd.Series
        Optimal weights
    """
    from .risk import risk_parity_weights
    return risk_parity_weights(returns, target_vol)


def min_variance_portfolio(returns: pd.DataFrame) -> pd.Series:
    """
    Minimum variance portfolio.
    
    Parameters:
    -----------
    returns : pd.DataFrame
        Returns matrix (dates x assets)
    
    Returns:
    --------
    pd.Series
        Optimal weights
    """
    return mean_variance_optimize(returns, method="min_vol")


def max_sharpe_portfolio(returns: pd.DataFrame, risk_free_rate: float = 0.0) -> pd.Series:
    """
    Maximum Sharpe ratio portfolio.
    
    Parameters:
    -----------
    returns : pd.DataFrame
        Returns matrix (dates x assets)
    risk_free_rate : float
        Risk-free rate
    
    Returns:
    --------
    pd.Series
        Optimal weights
    """
    return mean_variance_optimize(returns, risk_free_rate=risk_free_rate, method="max_sharpe")


def efficient_frontier(
    returns: pd.DataFrame,
    num_portfolios: int = 50,
    risk_free_rate: float = 0.0
) -> pd.DataFrame:
    """
    Generate efficient frontier portfolios.
    
    Parameters:
    -----------
    returns : pd.DataFrame
        Returns matrix (dates x assets)
    num_portfolios : int
        Number of portfolios to generate
    risk_free_rate : float
        Risk-free rate
    
    Returns:
    --------
    pd.DataFrame
        Columns: return, volatility, sharpe, weights (as dict)
    """
    if returns.empty:
        return pd.DataFrame()
    
    mean_returns = returns.mean() * 252
    cov_matrix = returns.cov() * 252
    
    min_ret = mean_returns.min()
    max_ret = mean_returns.max()
    target_returns = np.linspace(min_ret, max_ret, num_portfolios)
    
    portfolios = []
    for target_ret in target_returns:
        try:
            weights = mean_variance_optimize(returns, target_return=target_ret, method="min_vol")
            port_ret = (weights * mean_returns).sum()
            port_vol = np.sqrt(weights @ cov_matrix @ weights)
            sharpe = (port_ret - risk_free_rate) / port_vol if port_vol > 0 else 0
            
            portfolios.append({
                'return': port_ret,
                'volatility': port_vol,
                'sharpe': sharpe,
                'weights': weights.to_dict()
            })
        except Exception:
            continue
    
    return pd.DataFrame(portfolios)

