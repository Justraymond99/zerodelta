# Strategy package
# Note: Strategy classes are defined in qs/strategies.py (the file)
# To avoid conflicts, import them here
import importlib
import sys

# Import from parent module
qs_module = sys.modules.get('qs')
if qs_module:
    strategies_module = getattr(qs_module, 'strategies', None)
    if strategies_module:
        MomentumStrategy = getattr(strategies_module, 'MomentumStrategy', None)
        MeanReversionStrategy = getattr(strategies_module, 'MeanReversionStrategy', None)
        MLStrategy = getattr(strategies_module, 'MLStrategy', None)

