import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tempfile
import os
from pathlib import Path

# Set test environment variables before importing qs modules
os.environ['QS_DUCKDB_PATH'] = ':memory:'  # Use in-memory database for tests
os.environ['MLFLOW_TRACKING_URI'] = tempfile.mkdtemp()


@pytest.fixture
def sample_prices():
    """Generate sample price data for testing."""
    dates = pd.date_range(start='2020-01-01', end='2020-12-31', freq='D')
    np.random.seed(42)
    
    prices = []
    for symbol in ['AAPL', 'MSFT', 'GOOGL']:
        base_price = 100.0
        returns = np.random.normal(0.001, 0.02, len(dates))
        price_series = base_price * (1 + returns).cumprod()
        
        for i, date in enumerate(dates):
            prices.append({
                'symbol': symbol,
                'date': date.date(),
                'open': price_series[i] * 0.99,
                'high': price_series[i] * 1.01,
                'low': price_series[i] * 0.98,
                'close': price_series[i],
                'adj_close': price_series[i],
                'volume': np.random.randint(1000000, 10000000)
            })
    
    return pd.DataFrame(prices)


@pytest.fixture
def sample_returns():
    """Generate sample returns for testing."""
    dates = pd.date_range(start='2020-01-01', end='2020-12-31', freq='D')
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, len(dates))
    return pd.Series(returns, index=dates)

