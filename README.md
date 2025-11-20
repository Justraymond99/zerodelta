# ZeroDelta: Quantitative Trading Platform

ZeroDelta is a professional-grade quantitative trading and portfolio management platform with comprehensive features for strategy development, backtesting, risk management, and real-time execution.

## Setup

1. Create venv and install requirements:
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy env and edit as needed:
```bash
cp env.example .env
```

3. Initialize DB and fetch data:
```bash
PYTHONPATH=. python bin/qs_init_db.py
PYTHONPATH=. python bin/qs_fetch.py --tickers AAPL MSFT SPY --start 2018-01-01
```

### Bulk universe ingestion
```bash
# S&P 500
PYTHONPATH=. python bin/qs_fetch_universe.py --sp500 --start 2018-01-01 --chunk-size 50

# Crypto (major cryptocurrencies)
PYTHONPATH=. python bin/qs_fetch_universe.py --crypto --start 2018-01-01 --chunk-size 50

# From CSV (comma or line separated)
PYTHONPATH=. python bin/qs_fetch_universe.py --csv symbols.csv --start 2018-01-01 --chunk-size 50
```

### Fetching individual crypto symbols
You can also fetch individual crypto symbols using the standard fetch command:
```bash
PYTHONPATH=. python bin/qs_fetch.py --tickers BTC-USD ETH-USD SOL-USD --start 2018-01-01
```

4. Train and backtest:
```bash
PYTHONPATH=. python bin/qs_train.py
PYTHONPATH=. python bin/qs_backtest.py
```

5. Or run end-to-end:
```bash
PYTHONPATH=. python bin/qs_daily.py
```

### Continuous Market Analysis
Run the system continuously to constantly analyze markets:

```bash
# Continuous market scanner (runs forever, scans every 5 minutes)
PYTHONPATH=. python bin/qs_scanner.py --interval 300

# Run single scan
PYTHONPATH=. python bin/qs_scanner.py --once

# Full daemon mode (scanner + scheduled tasks)
PYTHONPATH=. python bin/qs_daemon.py --mode both

# Scheduler only (scheduled daily flow + periodic scans)
PYTHONPATH=. python bin/qs_daemon.py --mode scheduler --daily-time 09:00 --scan-schedule 15
```

The daemon will:
- Continuously scan markets for opportunities
- Run daily flow at scheduled time
- Check for buy/sell signals periodically
- Monitor price movements and volume spikes
- Send SMS alerts automatically

See `README_DAEMON.md` for detailed setup and configuration instructions.

### Options Pricing & Analysis
The system includes Black-Scholes and Monte Carlo option pricing:

```bash
# Black-Scholes pricing
PYTHONPATH=. python bin/qs_options.py bs --S 100 --K 105 --T 0.25 --symbol AAPL --type call --greeks

# Monte Carlo pricing
PYTHONPATH=. python bin/qs_options.py mc --S 100 --K 105 --T 0.25 --symbol AAPL --type call --simulations 100000

# Implied volatility
PYTHONPATH=. python bin/qs_options.py iv --price 5.50 --S 100 --K 105 --T 0.25 --type call

# Value at Risk (VaR)
PYTHONPATH=. python bin/qs_options.py var --symbol AAPL --confidence 0.95 --horizon 1
```

Via SMS API:
- `option AAPL 150 30 CALL` - Price a call option (uses current price and historical vol, detects anomalies)
- `option AAPL 150 30 PUT S=145 r=0.05` - Price with custom parameters
- `alerts` - Get buy/sell signals and options anomalies

### Trading Alerts
Check for trading opportunities and anomalies:
```bash
# Check alerts via command line
PYTHONPATH=. python bin/qs_alerts.py --check-signals --send-sms

# Or via SMS: send "alerts" to your Twilio number
```

### Performance Reports
Generate comprehensive performance reports:
```bash
# Generate PDF report
from qs.reporting import generate_performance_report
generate_performance_report("xgb_alpha", "report.pdf", format="pdf")

# Generate HTML or Markdown
generate_performance_report("xgb_alpha", "report.html", format="html")
generate_performance_report("xgb_alpha", "report.md", format="markdown")
```

## Frontend (Dashboard)
Run the Streamlit app:
```bash
PYTHONPATH=. streamlit run ui/app.py --server.port 8501
```
Pages:
- Data: inspect prices and volumes
- Features: visualize engineered features
- Signals: view model scores and ranks
- Backtest: run quick simulation and view stats
- Monitoring: real-time portfolio and risk monitoring
- Options: options pricing, Greeks, and chain analysis
- Portfolio Optimization: mean-variance, risk parity, efficient frontier
- Strategy Management: multi-strategy management and comparison
- Performance Attribution: symbol/strategy/factor attribution
- Trade Analysis: execution quality, slippage, market impact
- Walk-Forward Analysis: rolling window analysis

## SMS Control (Twilio) + API
1. Set environment variables in `.env` (Twilio):
```
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM=+15551234567
TWILIO_ALLOWED_NUMBERS=+15557654321
```
2. Run API server:
```bash
PYTHONPATH=. python bin/qs_api.py
```
3. Configure Twilio Messaging Webhook:
- URL: `https://<your_public_host>/twilio/sms`
- Method: POST
- Content Type: application/x-www-form-urlencoded

Commands:
- `status` / `ping`
- `backtest` or `backtest xgb_alpha`
- `daily` (runs the daily flow)
- `buy AAPL 10` / `sell AAPL 10` (uses IBKR adapter stub)
- `option SYMBOL STRIKE EXPIRY_DAYS [CALL|PUT]` - Price options using Black-Scholes (with anomaly detection)
- `alerts` - Check for buy/sell signals and options anomalies

### Automated Trading
Execute trades automatically based on signals:

```bash
# Paper trading (safe testing)
PYTHONPATH=. python bin/qs_auto_trade.py --paper --interval 300

# Single trading cycle
PYTHONPATH=. python bin/qs_auto_trade.py --once

# Live trading (requires confirmation)
PYTHONPATH=. python bin/qs_auto_trade.py --live --auto-execute
```

### API Documentation
The API now includes auto-generated documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health checks: `http://localhost:8000/health/detailed`

## Components
- DuckDB via SQLAlchemy for storage
- yfinance (free) + FMP (optional) for data
- Feature engineering: momentum, mean reversion, quality, plus 15+ technical indicators (RSI, MACD, Bollinger Bands, ADX, Stochastic, ATR, OBV, Williams %R, CCI, etc.)
- MLflow tracking; XGBoost/RandomForest model
- Enhanced backtesting with comprehensive metrics (Sharpe, Sortino, Calmar, win rate, beta, alpha, information ratio)
- Risk management: position sizing (Kelly criterion), stop-loss, risk limits, correlation analysis, VaR/CVaR
- Portfolio optimization: mean-variance, risk parity, minimum variance, efficient frontier
- Walk-forward analysis framework
- Performance attribution analysis
- Performance reporting: PDF, HTML, and Markdown reports with detailed analytics
- Options pricing: Black-Scholes, Monte Carlo simulation, Greeks, implied volatility, options chain, volatility surface
- Options anomaly detection: automatic detection of mispriced options
- Multi-timeframe analysis support
- Market regime detection
- Execution algorithms: TWAP, VWAP, market impact modeling
- Data validation and quality checks
- Real-time monitoring dashboard
- Trading alerts: SMS notifications for buy/sell signals and options anomalies
- Strategy framework: reusable strategy patterns (momentum, mean reversion, ML-based)
- Paper trading simulation: realistic order tracking and execution
- Factor models: Fama-French factor analysis and risk decomposition
- Data export: export backtests, signals, and portfolio holdings
- Prefect orchestration (optional inline daily in API); IBKR stub via ib_insync
- FastAPI + Twilio webhook for SMS control
- Structured logging infrastructure
- **API Security**: JWT authentication, API keys, role-based access
- **Automated Trading**: Auto-execute trades based on signals
- **API Documentation**: Auto-generated OpenAPI/Swagger docs
- **Health Monitoring**: Comprehensive health checks and system metrics
- **WebSocket Streaming**: Real-time price and signal updates
- **Advanced OMS**: Full order lifecycle management with state machine
- **Real-Time Risk**: Live position limits, VaR, portfolio risk monitoring
- **Alternative Data**: News sentiment analysis, RSS feeds
- **Caching**: Redis caching for performance
- **Error Tracking**: Sentry integration
- **Rate Limiting**: API protection
- **Database Migrations**: Alembic for schema versioning

See `IMPLEMENTATION_COMPLETE.md` for details on all new features.
- Unit testing framework with pytest

## Deployment

See `DEPLOY.md` for deployment instructions to Streamlit Cloud, Railway, Render, or Docker.

Quick deploy to Streamlit Cloud:
1. Push to GitHub: `git push origin main`
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Deploy!
