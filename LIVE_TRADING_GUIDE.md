# Live Trading Guide - Trading with Real Funds

## ⚠️ IMPORTANT WARNINGS

**Before trading with real money:**
- ✅ Test thoroughly in paper trading mode first
- ✅ Start with small position sizes
- ✅ Understand all risks involved
- ✅ Monitor your account closely
- ✅ Have proper risk management in place
- ✅ Ensure you have sufficient capital
- ✅ Be aware of market hours and trading restrictions

**This system can execute trades automatically. Use at your own risk.**

## Prerequisites

### 1. Interactive Brokers Account
- Open an account at [Interactive Brokers](https://www.interactivebrokers.com)
- Fund your account
- Complete account verification
- Enable API access in account settings

### 2. Install Interactive Brokers Software

You need **one** of these running:

**Option A: Trader Workstation (TWS)**
- Download from [IBKR TWS](https://www.interactivebrokers.com/en/index.php?f=16042)
- Install and log in
- Enable API connections: **Configure → API → Settings**
  - Enable "Enable ActiveX and Socket Clients"
  - Set "Socket port" to `7497` (paper) or `7496` (live)
  - Add trusted IPs if needed

**Option B: IB Gateway (Lightweight)**
- Download from [IB Gateway](https://www.interactivebrokers.com/en/index.php?f=16457)
- Install and log in
- Enable API: **Configure → API → Settings**
  - Enable "Enable ActiveX and Socket Clients"
  - Set port to `7497` (paper) or `7496` (live)

### 3. Install Python Package
```bash
pip install ib-insync
```

## Configuration

### Step 1: Update Environment Variables

Edit your `.env` file:

```bash
# Set to 0 for live trading (1 = paper trading)
IBKR_PAPER=0

# IBKR Connection Settings (optional, defaults shown)
IBKR_HOST=127.0.0.1
IBKR_PORT=7496  # 7496 = live, 7497 = paper
IBKR_CLIENT_ID=1
```

### Step 2: Start IBKR Software

**Before running the trading system:**
1. Start TWS or IB Gateway
2. Log in to your account
3. Ensure API is enabled and port is correct
4. Keep it running while trading

### Step 3: Test Connection

Test the connection first:

```python
from qs.exec.ibkr_adapter import IBKRAdapter

# Test connection
adapter = IBKRAdapter(paper=False)  # False = live trading
adapter.connect(host='127.0.0.1', port=7496, client_id=1)
print("Connected!")

# Test getting account info (if implemented)
adapter.disconnect()
```

## Trading Methods

### Method 1: Automated Trading (Recommended for Testing)

**Single Cycle (Safe - Review Before Executing):**
```bash
# Run once, review trades, then execute manually
PYTHONPATH=. python bin/qs_auto_trade.py \
  --live \
  --once \
  --account-value 100000 \
  --max-position-pct 0.05
```

**Continuous Automated Trading (⚠️ DANGEROUS):**
```bash
# This will automatically execute trades!
PYTHONPATH=. python bin/qs_auto_trade.py \
  --live \
  --auto-execute \
  --account-value 100000 \
  --max-position-pct 0.05 \
  --interval 300
```

**You will be prompted to type 'YES' to confirm live trading with auto-execute.**

### Method 2: API Trading

**Start the API server:**
```bash
PYTHONPATH=. python bin/qs_api.py
```

**Create an order via API:**
```bash
# Create a market buy order
curl -X POST "http://localhost:8000/api/v1/orders/" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "side": "buy",
    "quantity": 10,
    "order_type": "market",
    "account_value": 100000
  }'
```

**Note:** The API currently simulates fills. For real execution, you'd need to integrate with IBKR's order management.

### Method 3: SMS Trading (via Twilio)

Send SMS commands to your configured number:
```
buy AAPL 10
sell MSFT 5
```

**Note:** Currently defaults to paper trading. Update `qs/api/commands.py` to enable live trading.

### Method 4: Direct Python Script

```python
from qs.exec.ibkr_adapter import IBKRAdapter

# Connect to live account
adapter = IBKRAdapter(paper=False)
adapter.connect(host='127.0.0.1', port=7496, client_id=1)

# Place a market order
adapter.place_order(symbol="AAPL", side="buy", quantity=10)

# Disconnect
adapter.disconnect()
```

## Enhanced IBKR Adapter

The current adapter is basic. For production use, you should enhance it:

### Recommended Enhancements:

1. **Position Tracking:**
```python
def get_positions(self):
    """Get current positions from IBKR."""
    if self.ib is None:
        return {}
    positions = {}
    for pos in self.ib.positions():
        positions[pos.contract.symbol] = pos.position
    return positions
```

2. **Account Info:**
```python
def get_account_value(self):
    """Get account value."""
    if self.ib is None:
        return 0.0
    account_values = self.ib.accountValues()
    for av in account_values:
        if av.tag == 'NetLiquidation':
            return float(av.value)
    return 0.0
```

3. **Order Status:**
```python
def get_order_status(self, order_id):
    """Get order status."""
    # Track orders and their status
    pass
```

4. **Limit Orders:**
```python
def place_limit_order(self, symbol, side, quantity, limit_price):
    """Place limit order."""
    from ib_insync import LimitOrder
    contract = Stock(symbol, 'SMART', 'USD')
    action = 'BUY' if side.lower() == 'buy' else 'SELL'
    order = LimitOrder(action, int(quantity), limit_price)
    self.ib.placeOrder(contract, order)
```

## Safety Features

### 1. Risk Limits
The system enforces:
- Maximum position size (% of account)
- Portfolio risk limits
- Position concentration limits

Configure in automated trader:
```python
trader = AutomatedTrader(
    account_value=100000.0,
    max_position_pct=0.10,  # Max 10% per position
    min_signal_threshold=0.7  # Only trade strong signals
)
```

### 2. Manual Review Mode
Run without `--auto-execute` to review trades first:
```bash
PYTHONPATH=. python bin/qs_auto_trade.py --live --once
```

### 3. Position Limits
Set conservative limits:
```bash
--max-position-pct 0.05  # Only 5% per position
--min-signal-threshold 0.8  # Only very strong signals
```

### 4. SMS Confirmations
All trades send SMS confirmations with P&L (if configured).

## Step-by-Step: First Live Trade

### 1. Preparation
```bash
# Ensure TWS/Gateway is running and logged in
# Check API is enabled on port 7496
```

### 2. Test Connection
```python
from qs.exec.ibkr_adapter import IBKRAdapter

adapter = IBKRAdapter(paper=False)
adapter.connect()
print("Connected successfully!")
adapter.disconnect()
```

### 3. Small Test Trade
```python
# Start with a very small position
adapter = IBKRAdapter(paper=False)
adapter.connect()
adapter.place_order("AAPL", "buy", 1)  # Just 1 share
adapter.disconnect()
```

### 4. Verify in TWS
- Check order appears in TWS
- Verify execution
- Check account balance

### 5. Enable Automated Trading
Once comfortable:
```bash
PYTHONPATH=. python bin/qs_auto_trade.py \
  --live \
  --auto-execute \
  --account-value 100000 \
  --max-position-pct 0.02 \
  --min-signal-threshold 0.8 \
  --interval 600
```

## Monitoring

### 1. Check Positions
```python
from qs.oms.manager import get_order_manager

manager = get_order_manager()
positions = manager.get_positions()
print(positions)
```

### 2. View Orders
```bash
curl "http://localhost:8000/api/v1/orders/"
```

### 3. Check Risk
```bash
curl "http://localhost:8000/api/v1/risk/portfolio?account_value=100000"
```

### 4. SMS Alerts
Configure Twilio to receive:
- Trade confirmations
- Daily summaries
- Risk alerts

## Troubleshooting

### Connection Issues
- **Error: Connection refused**
  - Ensure TWS/Gateway is running
  - Check port number (7496 for live)
  - Verify API is enabled in settings

### Order Rejected
- Check account has sufficient buying power
- Verify symbol is tradeable
- Check market hours
- Review account permissions

### No Positions Showing
- The current adapter doesn't query positions
- Enhance `get_current_positions()` in `AutomatedTrader`
- Or manually track in database

## Best Practices

1. **Start Small**: Begin with minimal position sizes
2. **Monitor Closely**: Watch first few trades manually
3. **Set Limits**: Use conservative risk parameters
4. **Test First**: Paper trade extensively before going live
5. **Keep Logs**: Review trading logs regularly
6. **Have Exit Plan**: Know when to stop/disable auto-trading
7. **Backup Plan**: Keep TWS open to manually intervene if needed

## Current Limitations

The current implementation is **basic** and should be enhanced for production:

- ❌ No position querying from IBKR
- ❌ No account value retrieval
- ❌ No order status tracking
- ❌ Only market orders supported
- ❌ No error handling for connection issues
- ❌ No retry logic

**Recommendation:** Enhance the `IBKRAdapter` class before serious live trading.

## Next Steps

1. ✅ Test connection to IBKR
2. ✅ Place a small manual test trade
3. ✅ Verify SMS confirmations work
4. ✅ Run automated trader in review mode (no auto-execute)
5. ✅ Enable auto-execute with very small positions
6. ✅ Monitor closely and adjust parameters
7. ✅ Scale up gradually

## Support

- IBKR API Documentation: https://interactivebrokers.github.io/tws-api/
- ib_insync Documentation: https://ib-insync.readthedocs.io/
- System Logs: Check `./logs/auto_trade.log`

**Remember: Trading involves risk. Only trade with money you can afford to lose.**

