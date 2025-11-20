# Risk management package
# Import from qs.risk.py file (not this package)
import importlib.util
import sys
from pathlib import Path

# Get the parent directory and load the risk.py file directly
parent_dir = Path(__file__).parent.parent
risk_file = parent_dir / "risk.py"

if risk_file.exists():
    spec = importlib.util.spec_from_file_location("qs_risk_module", risk_file)
    qs_risk_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qs_risk_module)
    
    # Import functions from the module
    value_at_risk = getattr(qs_risk_module, 'value_at_risk', None)
    conditional_var = getattr(qs_risk_module, 'conditional_var', None)
    kelly_criterion = getattr(qs_risk_module, 'kelly_criterion', None)
    volatility_targeting = getattr(qs_risk_module, 'volatility_targeting', None)
    risk_parity_weights = getattr(qs_risk_module, 'risk_parity_weights', None)
    portfolio_correlation = getattr(qs_risk_module, 'portfolio_correlation', None)
    portfolio_volatility = getattr(qs_risk_module, 'portfolio_volatility', None)
    stop_loss_check = getattr(qs_risk_module, 'stop_loss_check', None)
    take_profit_check = getattr(qs_risk_module, 'take_profit_check', None)
    position_size_kelly = getattr(qs_risk_module, 'position_size_kelly', None)
    risk_limit_check = getattr(qs_risk_module, 'risk_limit_check', None)
else:
    # Fallback: define None if file doesn't exist
    value_at_risk = None
    conditional_var = None
    kelly_criterion = None
    volatility_targeting = None
    risk_parity_weights = None
    portfolio_correlation = None
    portfolio_volatility = None
    stop_loss_check = None
    take_profit_check = None
    position_size_kelly = None
    risk_limit_check = None

__all__ = [
    'value_at_risk',
    'conditional_var',
    'kelly_criterion',
    'volatility_targeting',
    'risk_parity_weights',
    'portfolio_correlation',
    'portfolio_volatility',
    'stop_loss_check',
    'take_profit_check',
    'position_size_kelly',
    'risk_limit_check'
]

