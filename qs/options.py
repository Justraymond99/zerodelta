from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.optimize import brentq
from typing import Literal


def black_scholes(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: Literal["call", "put"] = "call"
) -> float:
    """
    Black-Scholes option pricing formula for European options.
    
    Parameters:
    -----------
    S : float
        Current stock price
    K : float
        Strike price
    T : float
        Time to expiration (in years)
    r : float
        Risk-free interest rate (annualized)
    sigma : float
        Volatility (annualized)
    option_type : str
        "call" or "put"
    
    Returns:
    --------
    float
        Option price
    """
    if T <= 0:
        # Option expired
        if option_type == "call":
            return max(S - K, 0)
        else:
            return max(K - S, 0)
    
    if sigma <= 0:
        # No volatility
        if option_type == "call":
            return max(S * np.exp(-r * T) - K * np.exp(-r * T), 0)
        else:
            return max(K * np.exp(-r * T) - S * np.exp(-r * T), 0)
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type == "call":
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:  # put
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    
    return float(price)


def black_scholes_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: Literal["call", "put"] = "call"
) -> dict[str, float]:
    """
    Calculate all option Greeks using Black-Scholes model.
    
    Returns:
    --------
    dict with keys: delta, gamma, theta, vega, rho
    """
    if T <= 0 or sigma <= 0:
        return {
            "delta": 0.0,
            "gamma": 0.0,
            "theta": 0.0,
            "vega": 0.0,
            "rho": 0.0
        }
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    # Common terms
    N_d1 = norm.cdf(d1)
    N_d2 = norm.cdf(d2)
    n_d1 = norm.pdf(d1)  # PDF of standard normal
    
    # Delta
    if option_type == "call":
        delta = N_d1
    else:  # put
        delta = N_d1 - 1
    
    # Gamma (same for call and put)
    gamma = n_d1 / (S * sigma * np.sqrt(T))
    
    # Theta (per day, negative for time decay)
    if option_type == "call":
        theta = (
            -S * n_d1 * sigma / (2 * np.sqrt(T))
            - r * K * np.exp(-r * T) * N_d2
        ) / 365.0
    else:  # put
        theta = (
            -S * n_d1 * sigma / (2 * np.sqrt(T))
            + r * K * np.exp(-r * T) * norm.cdf(-d2)
        ) / 365.0
    
    # Vega (same for call and put)
    vega = S * n_d1 * np.sqrt(T) / 100.0  # per 1% change in volatility
    
    # Rho
    if option_type == "call":
        rho = K * T * np.exp(-r * T) * N_d2 / 100.0  # per 1% change in rate
    else:  # put
        rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100.0
    
    return {
        "delta": float(delta),
        "gamma": float(gamma),
        "theta": float(theta),
        "vega": float(vega),
        "rho": float(rho)
    }


def monte_carlo_option_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: Literal["call", "put"] = "call",
    n_simulations: int = 100000,
    n_steps: int = 252,
    random_seed: int | None = None
) -> dict[str, float]:
    """
    Price European option using Monte Carlo simulation.
    
    Parameters:
    -----------
    S : float
        Current stock price
    K : float
        Strike price
    T : float
        Time to expiration (in years)
    r : float
        Risk-free interest rate (annualized)
    sigma : float
        Volatility (annualized)
    option_type : str
        "call" or "put"
    n_simulations : int
        Number of Monte Carlo simulations
    n_steps : int
        Number of time steps (default 252 for daily steps)
    random_seed : int, optional
        Random seed for reproducibility
    
    Returns:
    --------
    dict with keys: price, std_error, confidence_interval_95
    """
    if random_seed is not None:
        np.random.seed(random_seed)
    
    dt = T / n_steps
    discount_factor = np.exp(-r * T)
    
    # Generate random paths
    # Using geometric Brownian motion: dS = r*S*dt + sigma*S*dW
    # For efficiency, we can use the closed-form solution for the final price
    # S_T = S_0 * exp((r - 0.5*sigma^2)*T + sigma*sqrt(T)*Z)
    # where Z ~ N(0,1)
    
    Z = np.random.standard_normal(n_simulations)
    S_T = S * np.exp((r - 0.5 * sigma ** 2) * T + sigma * np.sqrt(T) * Z)
    
    # Calculate payoffs
    if option_type == "call":
        payoffs = np.maximum(S_T - K, 0)
    else:  # put
        payoffs = np.maximum(K - S_T, 0)
    
    # Discount to present value
    option_values = payoffs * discount_factor
    
    # Calculate statistics
    price = float(np.mean(option_values))
    std_error = float(np.std(option_values) / np.sqrt(n_simulations))
    
    # 95% confidence interval
    confidence_interval_95 = (
        float(price - 1.96 * std_error),
        float(price + 1.96 * std_error)
    )
    
    return {
        "price": price,
        "std_error": std_error,
        "confidence_interval_95": confidence_interval_95,
        "min_payoff": float(np.min(option_values)),
        "max_payoff": float(np.max(option_values))
    }


def implied_volatility(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: Literal["call", "put"] = "call",
    initial_guess: float = 0.2,
    tolerance: float = 1e-6
) -> float | None:
    """
    Calculate implied volatility from market option price using Black-Scholes.
    
    Uses Brent's method to solve for volatility that matches market price.
    
    Returns:
    --------
    float or None if convergence fails
    """
    def price_error(sigma: float) -> float:
        return black_scholes(S, K, T, r, sigma, option_type) - market_price
    
    # Bounds for volatility search (0.1% to 500%)
    vol_min = 0.001
    vol_max = 5.0
    
    try:
        # Check bounds
        price_at_min = price_error(vol_min)
        price_at_max = price_error(vol_max)
        
        # If same sign, no root exists
        if price_at_min * price_at_max > 0:
            return None
        
        # Use Brent's method to find root
        implied_vol = brentq(price_error, vol_min, vol_max, xtol=tolerance)
        return float(implied_vol)
    except (ValueError, RuntimeError):
        return None


def calculate_historical_volatility_from_returns(returns: np.ndarray | pd.Series) -> float:
    """
    Calculate annualized volatility from returns array.
    
    Parameters:
    -----------
    returns : np.ndarray or pd.Series
        Daily returns
    
    Returns:
    --------
    float
        Annualized volatility (assuming 252 trading days)
    """
    if isinstance(returns, pd.Series):
        returns = returns.values
    if len(returns) == 0:
        return 0.0
    return float(np.std(returns, ddof=1) * (252 ** 0.5))


def volatility_surface(
    S: float,
    strikes: list[float],
    expiries: list[float],
    r: float,
    market_prices: dict[tuple[float, float], float] | None = None,
    option_type: Literal["call", "put"] = "call"
) -> pd.DataFrame:
    """
    Generate volatility surface from market prices or implied volatilities.
    
    Parameters:
    -----------
    S : float
        Current stock price
    strikes : list[float]
        List of strike prices
    expiries : list[float]
        List of time to expiration (in years)
    r : float
        Risk-free rate
    market_prices : dict, optional
        Dictionary mapping (strike, expiry) to market price
    option_type : str
        "call" or "put"
    
    Returns:
    --------
    pd.DataFrame
        Volatility surface with columns: strike, expiry, iv, price
    """
    surface_data = []
    
    for strike in strikes:
        for expiry in expiries:
            if market_prices and (strike, expiry) in market_prices:
                market_price = market_prices[(strike, expiry)]
                iv = implied_volatility(market_price, S, strike, expiry, r, option_type)
                price = market_price
            else:
                # Use historical volatility estimate
                iv = 0.20  # Default
                price = black_scholes(S, strike, expiry, r, iv, option_type)
            
            surface_data.append({
                'strike': strike,
                'expiry': expiry,
                'moneyness': strike / S,
                'iv': iv if iv else 0.0,
                'price': price
            })
    
    return pd.DataFrame(surface_data)


def options_chain_pricing(
    S: float,
    strikes: list[float],
    expiry: float,
    r: float,
    sigma: float
) -> pd.DataFrame:
    """
    Generate options chain with prices and Greeks.
    
    Parameters:
    -----------
    S : float
        Current stock price
    strikes : list[float]
        List of strike prices
    expiry : float
        Time to expiration (in years)
    r : float
        Risk-free rate
    sigma : float
        Volatility
    
    Returns:
    --------
    pd.DataFrame
        Options chain with prices and Greeks
    """
    chain_data = []
    
    for strike in strikes:
        for option_type in ["call", "put"]:
            price = black_scholes(S, strike, expiry, r, sigma, option_type)
            greeks = black_scholes_greeks(S, strike, expiry, r, sigma, option_type)
            
            chain_data.append({
                'strike': strike,
                'type': option_type,
                'moneyness': strike / S,
                'price': price,
                'delta': greeks['delta'],
                'gamma': greeks['gamma'],
                'theta': greeks['theta'],
                'vega': greeks['vega'],
                'rho': greeks['rho']
            })
    
    return pd.DataFrame(chain_data)


def calculate_historical_volatility(symbol: str, days: int = 30, engine=None) -> float | None:
    """
    Calculate historical volatility from price data in database.
    
    Parameters:
    -----------
    symbol : str
        Stock symbol
    days : int
        Number of days to use for volatility calculation
    engine : sqlalchemy.Engine, optional
        Database engine (if None, will create one)
    
    Returns:
    --------
    float or None if insufficient data
    """
    if engine is None:
        from .db import get_engine
        engine = get_engine()
    
    from sqlalchemy import text
    
    with engine.begin() as conn:
        df = pd.read_sql(
            text("""
                SELECT date, adj_close 
                FROM prices 
                WHERE symbol = :sym 
                ORDER BY date DESC 
                LIMIT :days
            """),
            conn,
            params={"sym": symbol, "days": days + 1}
        )
    
    if len(df) < 2:
        return None
    
    df = df.sort_values('date')
    returns = df['adj_close'].pct_change().dropna()
    
    return calculate_historical_volatility_from_returns(returns)


def monte_carlo_var(
    returns: np.ndarray,
    confidence_level: float = 0.95,
    time_horizon: int = 1,
    n_simulations: int = 10000,
    random_seed: int | None = None
) -> dict[str, float]:
    """
    Calculate Value at Risk (VaR) using Monte Carlo simulation.
    
    Parameters:
    -----------
    returns : np.ndarray
        Historical returns
    confidence_level : float
        Confidence level (e.g., 0.95 for 95% VaR)
    time_horizon : int
        Time horizon in days
    n_simulations : int
        Number of Monte Carlo simulations
    random_seed : int, optional
        Random seed for reproducibility
    
    Returns:
    --------
    dict with keys: var, cvar (Conditional VaR), mean, std
    """
    if random_seed is not None:
        np.random.seed(random_seed)
    
    if len(returns) == 0:
        return {"var": 0.0, "cvar": 0.0, "mean": 0.0, "std": 0.0}
    
    # Estimate parameters from historical returns
    mean_return = np.mean(returns)
    std_return = np.std(returns, ddof=1)
    
    # Generate simulated returns
    simulated_returns = np.random.normal(
        mean_return * time_horizon,
        std_return * np.sqrt(time_horizon),
        n_simulations
    )
    
    # Calculate VaR (negative of the percentile)
    var_percentile = (1 - confidence_level) * 100
    var = -np.percentile(simulated_returns, var_percentile)
    
    # Calculate CVaR (Conditional VaR / Expected Shortfall)
    # Average of losses beyond VaR
    losses_beyond_var = simulated_returns[simulated_returns <= -var]
    cvar = -np.mean(losses_beyond_var) if len(losses_beyond_var) > 0 else var
    
    return {
        "var": float(var),
        "cvar": float(cvar),
        "mean": float(mean_return * time_horizon),
        "std": float(std_return * np.sqrt(time_horizon))
    }

