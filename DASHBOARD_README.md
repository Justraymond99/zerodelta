# Trading Dashboard

## Overview
Modern dark-themed trading dashboard matching professional trading platforms.

## Features

### Status Widgets (Top Row)
- **PnL**: Real-time profit and loss from positions
- **Market**: Market status (OPEN/CLOSED)
- **Latency**: System latency indicator
- **System**: System health status

### Market Data Widgets
- **S&P 500**: Real-time index value and change
- **NASDAQ**: Real-time index value and change
- **EUR/USD**: Real-time currency pair value and change

### Market Chart
- Interactive price chart (SPY by default)
- Dark theme styling
- Real-time data from database

### Order Entry
- Symbol input
- Buy/Sell buttons
- Order type selection (Market, Limit, Stop)
- Quantity input
- Place order functionality

### Trades Table
- Recent trade history
- Columns: Time, Symbol, Type, Price, Quantity
- Real-time updates

### Algo Control
- Start/Stop algorithm button
- Algorithm status indicator
- Real-time status updates

### Live Logs
- System event log
- Chronological order
- Auto-updates

## Running the Dashboard

```bash
streamlit run ui/app.py
```

## Configuration

### Auto-refresh
- Enable/disable in sidebar
- Adjust refresh interval (1-10 seconds)

### Theme
- Dark theme configured in `.streamlit/config.toml`
- Custom CSS for professional look

## Integration

The dashboard integrates with:
- Order Management System (OMS)
- P&L Calculator
- Database (DuckDB)
- Real-time market data (yfinance)

## Customization

### Adding New Widgets
Edit `ui/app.py` and add new columns/widgets following the existing pattern.

### Changing Colors
Modify the CSS in the `st.markdown()` section or update `.streamlit/config.toml`.

### Adding Real-time Data
Use `yfinance` or WebSocket connections for live data feeds.

