import pytest
import pandas as pd
import numpy as np
from qs.risk import (
    kelly_criterion, volatility_targeting, value_at_risk,
    stop_loss_check, take_profit_check
)


def test_kelly_criterion():
    """Test Kelly Criterion calculation."""
    kelly = kelly_criterion(win_rate=0.6, avg_win=0.1, avg_loss=0.05)
    assert 0 <= kelly <= 1
    assert kelly > 0  # Positive edge should give positive Kelly


def test_volatility_targeting():
    """Test volatility targeting."""
    scaled = volatility_targeting(target_vol=0.15, current_vol=0.30, base_position=1.0)
    assert scaled == 0.5  # Should halve position size


def test_value_at_risk():
    """Test VaR calculation."""
    returns = pd.Series(np.random.normal(0.001, 0.02, 1000))
    var = value_at_risk(returns, confidence_level=0.95)
    assert var < 0  # VaR should be negative (loss)
    assert abs(var) < 0.5  # Should be reasonable


def test_stop_loss_check():
    """Test stop loss logic."""
    assert stop_loss_check(entry_price=100, current_price=94, stop_loss_pct=0.05) == True
    assert stop_loss_check(entry_price=100, current_price=96, stop_loss_pct=0.05) == False


def test_take_profit_check():
    """Test take profit logic."""
    assert take_profit_check(entry_price=100, current_price=110, take_profit_pct=0.10) == True
    assert take_profit_check(entry_price=100, current_price=105, take_profit_pct=0.10) == False

