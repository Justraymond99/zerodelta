import pytest
from qs.options import black_scholes, black_scholes_greeks, implied_volatility


def test_black_scholes_call():
    """Test Black-Scholes call option pricing."""
    price = black_scholes(S=100, K=105, T=0.25, r=0.05, sigma=0.2, option_type="call")
    assert price > 0
    assert price < 100  # Call price should be less than stock price


def test_black_scholes_put():
    """Test Black-Scholes put option pricing."""
    price = black_scholes(S=100, K=105, T=0.25, r=0.05, sigma=0.2, option_type="put")
    assert price > 0


def test_black_scholes_greeks():
    """Test option Greeks calculation."""
    greeks = black_scholes_greeks(S=100, K=105, T=0.25, r=0.05, sigma=0.2, option_type="call")
    assert 'delta' in greeks
    assert 'gamma' in greeks
    assert 'theta' in greeks
    assert 'vega' in greeks
    assert 'rho' in greeks
    assert 0 <= greeks['delta'] <= 1  # Call delta between 0 and 1


def test_implied_volatility():
    """Test implied volatility calculation."""
    market_price = 5.0
    iv = implied_volatility(market_price, S=100, K=105, T=0.25, r=0.05, option_type="call")
    assert iv is not None
    assert iv > 0
    # Verify the IV produces the market price
    calculated_price = black_scholes(S=100, K=105, T=0.25, r=0.05, sigma=iv, option_type="call")
    assert abs(calculated_price - market_price) < 0.01

