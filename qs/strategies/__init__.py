# Strategy package
# Expose strategy classes from qs/strategies.py file
# We need to load the file module with proper package context for relative imports

import sys
import importlib.util
from pathlib import Path

# Check if classes are already available
MomentumStrategy = None
MeanReversionStrategy = None
MLStrategy = None

# Try to load from the strategies.py file with proper package context
try:
    # Ensure qs package is loaded first
    if 'qs' not in sys.modules:
        import qs
    
    # Get the qs package path
    qs_module = sys.modules.get('qs')
    if qs_module and hasattr(qs_module, '__file__'):
        qs_path = Path(qs_module.__file__).parent
    else:
        # Fallback: construct path
        qs_path = Path(__file__).parent.parent
    
    strategies_file = qs_path / "strategies.py"
    
    if strategies_file.exists():
        # Ensure parent modules are in sys.modules for relative imports
        # This is critical for relative imports like "from ..utils.logger"
        if 'qs' not in sys.modules:
            import qs
        if 'qs.utils' not in sys.modules:
            try:
                import qs.utils
            except ImportError:
                pass
        if 'qs.utils.logger' not in sys.modules:
            try:
                import qs.utils.logger
            except ImportError:
                pass
        
        # Load the strategies.py file module with proper package context
        # Use a unique name to avoid conflicts with the package
        spec = importlib.util.spec_from_file_location("qs.strategies_file", strategies_file)
        strategies_module = importlib.util.module_from_spec(spec)
        
        # CRITICAL: Set package context BEFORE executing
        strategies_module.__package__ = 'qs'
        strategies_module.__name__ = 'qs.strategies_file'
        
        # Store in sys.modules BEFORE executing to allow relative imports
        sys.modules['qs.strategies_file'] = strategies_module
        
        # Execute the module (this will resolve relative imports)
        spec.loader.exec_module(strategies_module)
        
        # Extract the classes
        MomentumStrategy = getattr(strategies_module, 'MomentumStrategy', None)
        MeanReversionStrategy = getattr(strategies_module, 'MeanReversionStrategy', None)
        MLStrategy = getattr(strategies_module, 'MLStrategy', None)
        
        # Verify they're actually classes (not None)
        if MomentumStrategy and not (callable(MomentumStrategy) and hasattr(MomentumStrategy, '__init__')):
            MomentumStrategy = None
        if MeanReversionStrategy and not (callable(MeanReversionStrategy) and hasattr(MeanReversionStrategy, '__init__')):
            MeanReversionStrategy = None
        if MLStrategy and not (callable(MLStrategy) and hasattr(MLStrategy, '__init__')):
            MLStrategy = None
            
except Exception as e:
    # If loading fails, classes remain None
    # Log error but don't break the import
    import logging
    logging.getLogger(__name__).debug(f"Could not load strategies from file: {e}")
    pass

# Export classes for easy importing
__all__ = ['MomentumStrategy', 'MeanReversionStrategy', 'MLStrategy']
