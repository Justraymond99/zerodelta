from __future__ import annotations

from typing import Dict, Optional
from enum import Enum
from datetime import datetime
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AssetType(Enum):
    """Asset type enumeration."""
    STOCK = "stock"
    OPTION = "option"
    FUTURE = "future"
    FOREX = "forex"
    CRYPTO = "crypto"
    BOND = "bond"


class MultiAssetManager:
    """
    Manages multiple asset types (stocks, options, futures, forex, crypto).
    """
    
    def __init__(self):
        self.asset_handlers: Dict[AssetType, callable] = {}
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup handlers for different asset types."""
        # Stock handler (default)
        self.asset_handlers[AssetType.STOCK] = self._handle_stock
        
        # Option handler
        self.asset_handlers[AssetType.OPTION] = self._handle_option
        
        # Future handler
        self.asset_handlers[AssetType.FUTURE] = self._handle_future
        
        # Forex handler
        self.asset_handlers[AssetType.FOREX] = self._handle_forex
        
        # Crypto handler
        self.asset_handlers[AssetType.CRYPTO] = self._handle_crypto
    
    def _handle_stock(self, symbol: str, **kwargs) -> Dict:
        """Handle stock asset."""
        from ..data.realtime import get_realtime_manager
        
        manager = get_realtime_manager()
        price = manager.get_price(symbol)
        
        return {
            'symbol': symbol,
            'type': AssetType.STOCK.value,
            'price': price,
            'timestamp': datetime.now().isoformat()
        }
    
    def _handle_option(self, symbol: str, strike: float, expiry: str, option_type: str, **kwargs) -> Dict:
        """Handle option asset."""
        from ..options import black_scholes, black_scholes_greeks
        
        # Get underlying price
        underlying = symbol.split()[0] if ' ' in symbol else symbol
        from ..data.realtime import get_realtime_manager
        manager = get_realtime_manager()
        underlying_price = manager.get_price(underlying) or 100.0
        
        # Calculate option price
        expiry_date = datetime.fromisoformat(expiry)
        time_to_expiry = (expiry_date - datetime.now()).days / 365.0
        
        price = black_scholes(
            S=underlying_price,
            K=strike,
            T=time_to_expiry,
            r=kwargs.get('r', 0.05),
            sigma=kwargs.get('sigma', 0.20),
            option_type=option_type.lower()
        )
        
        greeks = black_scholes_greeks(
            S=underlying_price,
            K=strike,
            T=time_to_expiry,
            r=kwargs.get('r', 0.05),
            sigma=kwargs.get('sigma', 0.20),
            option_type=option_type.lower()
        )
        
        return {
            'symbol': symbol,
            'type': AssetType.OPTION.value,
            'underlying': underlying,
            'strike': strike,
            'expiry': expiry,
            'option_type': option_type,
            'price': price,
            'greeks': greeks,
            'timestamp': datetime.now().isoformat()
        }
    
    def _handle_future(self, symbol: str, **kwargs) -> Dict:
        """Handle future contract."""
        # Placeholder - would integrate with futures data provider
        return {
            'symbol': symbol,
            'type': AssetType.FUTURE.value,
            'price': None,
            'timestamp': datetime.now().isoformat()
        }
    
    def _handle_forex(self, pair: str, **kwargs) -> Dict:
        """Handle forex pair."""
        from ..data.realtime import get_realtime_manager
        
        manager = get_realtime_manager()
        price = manager.get_price(pair)
        
        return {
            'symbol': pair,
            'type': AssetType.FOREX.value,
            'price': price,
            'timestamp': datetime.now().isoformat()
        }
    
    def _handle_crypto(self, symbol: str, **kwargs) -> Dict:
        """Handle cryptocurrency."""
        from ..data.realtime import get_realtime_manager
        
        manager = get_realtime_manager()
        price = manager.get_price(symbol)
        
        return {
            'symbol': symbol,
            'type': AssetType.CRYPTO.value,
            'price': price,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_asset_info(self, asset_type: AssetType, symbol: str, **kwargs) -> Dict:
        """Get information for an asset."""
        handler = self.asset_handlers.get(asset_type)
        if not handler:
            logger.error(f"No handler for asset type: {asset_type}")
            return {}
        
        return handler(symbol, **kwargs)
    
    def place_order(
        self,
        asset_type: AssetType,
        symbol: str,
        side: str,
        quantity: float,
        **kwargs
    ) -> bool:
        """Place order for any asset type."""
        # Route to appropriate handler
        if asset_type == AssetType.STOCK:
            from ..oms.manager import get_order_manager
            from ..oms.order import OrderSide, OrderType
            
            manager = get_order_manager()
            order = manager.create_order(
                symbol=symbol,
                side=OrderSide(side.lower()),
                quantity=quantity,
                order_type=OrderType.MARKET
            )
            manager.submit_order(order.order_id)
            return True
        
        elif asset_type == AssetType.OPTION:
            # Options require additional parameters
            logger.info(f"Option order: {side} {quantity} {symbol}")
            return True
        
        else:
            logger.warning(f"Order placement not yet implemented for {asset_type}")
            return False


# Global multi-asset manager
_multi_asset_manager: Optional[MultiAssetManager] = None


def get_multi_asset_manager() -> MultiAssetManager:
    """Get global multi-asset manager."""
    global _multi_asset_manager
    if _multi_asset_manager is None:
        _multi_asset_manager = MultiAssetManager()
    return _multi_asset_manager

