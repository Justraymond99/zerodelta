# Initialize Default Data for ZeroDelta

## Quick Start - Fetch Popular Tickers

To get started with ZeroDelta, fetch some popular tickers first:

```bash
# Fetch popular tech stocks, ETFs, and major indices
PYTHONPATH=. python bin/qs_fetch.py --tickers AAPL MSFT GOOGL AMZN NVDA META TSLA SPY QQQ JPM BAC --start 2018-01-01
```

Or use the UI:
1. Go to the **Data** page
2. Click "🚀 Fetch Popular Tickers" button
3. Wait for data to load

## Popular Ticker Categories

### Tech Giants
- `AAPL` - Apple
- `MSFT` - Microsoft  
- `GOOGL` - Google
- `AMZN` - Amazon
- `NVDA` - NVIDIA
- `META` - Meta (Facebook)
- `TSLA` - Tesla

### ETFs & Indices
- `SPY` - S&P 500 ETF
- `QQQ` - Nasdaq 100 ETF
- `DIA` - Dow Jones ETF
- `IWM` - Russell 2000 ETF
- `VTI` - Total Stock Market ETF
- `VOO` - S&P 500 Index Fund

### Financials
- `JPM` - JPMorgan Chase
- `BAC` - Bank of America
- `WFC` - Wells Fargo
- `GS` - Goldman Sachs

### Consumer & Retail
- `WMT` - Walmart
- `HD` - Home Depot
- `MCD` - McDonald's
- `NKE` - Nike

## Bulk Fetch Options

### Fetch S&P 500
```bash
PYTHONPATH=. python bin/qs_fetch_universe.py --sp500 --start 2018-01-01
```

### Fetch Major Crypto
```bash
PYTHONPATH=. python bin/qs_fetch_universe.py --crypto --start 2018-01-01
```

## After Fetching Data

1. **Compute Features:**
   ```bash
   PYTHONPATH=. python -c "from qs.features import compute_features; compute_features()"
   ```

2. **Train Model:**
   ```bash
   PYTHONPATH=. python bin/qs_train.py
   ```

3. **Generate Signals:**
   ```bash
   PYTHONPATH=. python -c "from qs.signal import generate_signals; generate_signals()"
   ```

4. **Run Backtest:**
   ```bash
   PYTHONPATH=. python bin/qs_backtest.py
   ```

Or use the UI - all these steps can be done through the dashboard pages!

