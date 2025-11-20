from __future__ import annotations

from typing import Optional, Dict
import os

try:
    from ib_insync import IB, Stock, MarketOrder, LimitOrder
except Exception:  # pragma: no cover
    IB = None  # type: ignore
    Stock = None
    MarketOrder = None
    LimitOrder = None


class IBKRAdapter:
    """
    Interactive Brokers API adapter for live trading.
    
    Requires:
    - TWS or IB Gateway running
    - API enabled in TWS/Gateway settings
    - Port 7496 (live) or 7497 (paper)
    """
    
    def __init__(self, paper: bool = True):
        self.paper = paper
        self.ib: Optional[IB] = None
        self._connected = False

    def connect(
        self,
        host: str = None,
        port: int = None,
        client_id: int = None
    ) -> bool:
        """
        Connect to IBKR TWS/Gateway.
        
        Parameters:
        -----------
        host : str, optional
            Host (default: 127.0.0.1)
        port : int, optional
            Port (default: 7497 for paper, 7496 for live)
        client_id : int, optional
            Client ID (default: 1)
        
        Returns:
        --------
        bool
            True if connected successfully
        """
        if IB is None:
            raise ImportError("ib_insync not installed. Run: pip install ib-insync")
        
        host = host or os.getenv("IBKR_HOST", "127.0.0.1")
        port = port or (7497 if self.paper else 7496)
        client_id = client_id or int(os.getenv("IBKR_CLIENT_ID", "1"))
        
        try:
            self.ib = IB()
            self.ib.connect(host, port, clientId=client_id)
            self._connected = True
            return True
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"Failed to connect to IBKR: {e}")

    def is_connected(self) -> bool:
        """Check if connected to IBKR."""
        return self._connected and self.ib is not None and self.ib.isConnected()

    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        limit_price: Optional[float] = None
    ) -> None:
        """
        Place an order.
        
        Parameters:
        -----------
        symbol : str
            Stock symbol
        side : str
            "buy" or "sell"
        quantity : float
            Number of shares
        order_type : str
            "market" or "limit"
        limit_price : float, optional
            Limit price (required for limit orders)
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to IBKR. Call connect() first.")
        
        if IB is None or Stock is None:
            raise ImportError("ib_insync not installed")
        
        contract = Stock(symbol, 'SMART', 'USD')
        action = 'BUY' if side.lower() == 'buy' else 'SELL'
        
        if order_type.lower() == "limit":
            if limit_price is None:
                raise ValueError("limit_price required for limit orders")
            order = LimitOrder(action, int(quantity), limit_price)
        else:
            order = MarketOrder(action, int(quantity))
        
        self.ib.placeOrder(contract, order)

    def get_positions(self) -> Dict[str, float]:
        """
        Get current positions.
        
        Returns:
        --------
        dict
            {symbol: quantity} mapping
        """
        if not self.is_connected():
            return {}
        
        positions = {}
        for pos in self.ib.positions():
            if pos.contract.secType == "STK":
                positions[pos.contract.symbol] = pos.position
        
        return positions

    def get_account_value(self, tag: str = "NetLiquidation") -> float:
        """
        Get account value.
        
        Parameters:
        -----------
        tag : str
            Account value tag (NetLiquidation, TotalCashValue, etc.)
        
        Returns:
        --------
        float
            Account value
        """
        if not self.is_connected():
            return 0.0
        
        account_values = self.ib.accountValues()
        for av in account_values:
            if av.tag == tag:
                return float(av.value)
        
        return 0.0

    def disconnect(self) -> None:
        """Disconnect from IBKR."""
        if self.ib is not None and self.ib.isConnected():
            self.ib.disconnect()
        self.ib = None
        self._connected = False