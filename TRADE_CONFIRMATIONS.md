# Trade Confirmation SMS Feature

## Overview
The system now automatically sends SMS confirmations when trades are executed, including profit/loss information for closed positions.

## Features

### Automatic SMS Notifications
- ✅ Sent immediately when trades execute
- ✅ Includes trade details (symbol, quantity, price, side)
- ✅ Shows realized P&L for closed positions
- ✅ Works for both paper and live trading
- ✅ Sent to all configured phone numbers

### P&L Calculation
- ✅ Tracks cost basis (average entry price) for each position
- ✅ Calculates realized P&L when positions are closed
- ✅ Shows both dollar amount and percentage gain/loss
- ✅ Persists position data in database

## Message Format

### Buy Order
```
📝 PAPER TRADE EXECUTED

🟢 BUY 100.00 AAPL
Price: $150.25
Value: $15,025.00

Time: 2024-01-15 14:30:00
```

### Sell Order (with P&L)
```
📝 PAPER TRADE EXECUTED

🔴 SELL 100.00 AAPL
Price: $155.50
Value: $15,550.00

✅ Realized P&L: +$525.00 (+3.50%)

Time: 2024-01-15 15:45:00
```

### Live Trading
```
💰 LIVE TRADE EXECUTED

🟢 BUY 50.00 MSFT
Price: $380.00
Value: $19,000.00
Order ID: abc12345

Time: 2024-01-15 16:00:00
```

## Configuration

### Environment Variables
Make sure these are set in your `.env` file:

```bash
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM=+1234567890
TWILIO_ALLOWED_NUMBERS=+1234567890,+0987654321
```

## How It Works

### 1. Position Tracking
- When you buy, the system records the entry price
- For multiple buys, it calculates a weighted average cost basis
- Position data is stored in the `positions` table

### 2. P&L Calculation
- When you sell, the system:
  1. Looks up the cost basis for that position
  2. Calculates: `(sell_price - entry_price) × quantity`
  3. Calculates percentage: `((sell_price - entry_price) / entry_price) × 100`

### 3. SMS Sending
- Automatically triggered when:
  - Orders are filled via the OMS
  - Trades execute in automated trading
  - Paper trading orders complete
- Sent to all numbers in `TWILIO_ALLOWED_NUMBERS`

## Integration Points

### Order Management System
```python
from qs.oms.manager import get_order_manager

manager = get_order_manager()
# When order fills, SMS is automatically sent
manager.fill_order(order_id, quantity, price, send_sms=True)
```

### Automated Trading
```python
from qs.trading.automated import AutomatedTrader

trader = AutomatedTrader(paper_trading=True)
# SMS sent automatically when trades execute
trader.run_cycle()
```

### Paper Trading
```python
from qs.papertrading import PaperTradingAccount

account = PaperTradingAccount()
# SMS sent automatically when orders are placed
account.place_order("AAPL", 100, 150.25, "buy")
```

## Database Schema

The `positions` table tracks cost basis:
```sql
CREATE TABLE positions (
    symbol TEXT PRIMARY KEY,
    quantity DOUBLE,
    average_price DOUBLE,
    last_updated TIMESTAMP DEFAULT now()
);
```

## Example Flow

1. **Buy 100 AAPL @ $150**
   - Position created: `{symbol: "AAPL", quantity: 100, avg_price: 150.00}`
   - SMS: "🟢 BUY 100.00 AAPL @ $150.00"

2. **Buy 50 more AAPL @ $152**
   - Position updated: `{quantity: 150, avg_price: 150.67}` (weighted average)
   - SMS: "🟢 BUY 50.00 AAPL @ $152.00"

3. **Sell 100 AAPL @ $155**
   - P&L calculated: `(155 - 150.67) × 100 = $433.00` (+2.88%)
   - Position updated: `{quantity: 50, avg_price: 150.67}`
   - SMS: "🔴 SELL 100.00 AAPL @ $155.00 ✅ Realized P&L: +$433.00 (+2.88%)"

## Testing

To test without real trades:
```python
from qs.notify.trade_confirmations import send_trade_confirmation

# Test buy
send_trade_confirmation(
    symbol="AAPL",
    side="buy",
    quantity=100,
    price=150.25,
    is_paper=True
)

# Test sell with P&L
send_trade_confirmation(
    symbol="AAPL",
    side="sell",
    quantity=100,
    price=155.50,
    realized_pnl=525.00,
    pnl_pct=3.50,
    is_paper=True
)
```

## Notes

- P&L is only calculated for **sell orders** (closing positions)
- Buy orders don't show P&L (opening positions)
- Cost basis uses **weighted average** for multiple entries
- SMS is sent to **all** numbers in `TWILIO_ALLOWED_NUMBERS`
- Works for both paper and live trading modes

