from __future__ import annotations

from typing import Tuple


def _run_daily_inline() -> dict:
    # Inline daily pipeline without Prefect to avoid heavy imports in API
    from qs.data.ingest_prices import ingest_prices
    from qs.data.ingest_fundamentals import ingest_fundamentals
    from qs.features import compute_features
    from qs.ml.train import train_model
    from qs.signal import generate_signals
    from qs.backtest import backtest_signal
    from qs.config import get_settings

    settings = get_settings()
    tickers = [t.strip() for t in settings.default_tickers.split(',') if t.strip()]

    ingest_prices(tickers=tickers, start=settings.default_start)
    ingest_fundamentals(tickers)
    compute_features()
    run_id = train_model(model_name="xgb_alpha")
    _ = generate_signals(model_name="xgb_alpha")
    stats = backtest_signal(signal_name="xgb_alpha")
    
    # Send SMS update if configured
    try:
        from qs.notify.twilio_client import send_sms_update
        from qs.notify.alerts import send_trading_alerts
        
        if stats:
            msg = f"📊 Daily flow complete\n"
            msg += f"Return: {stats.get('total_return', 0)*100:.2f}%\n"
            msg += f"Sharpe: {stats.get('sharpe', 0):.2f}\n"
            msg += f"Max DD: {stats.get('max_drawdown', 0)*100:.2f}%\n"
            msg += f"Win Rate: {stats.get('win_rate', 0)*100:.1f}%"
            send_sms_update(msg)
        
        # Send trading alerts
        send_trading_alerts(check_options=False, check_signals=True)
    except Exception as e:
        pass  # Silently fail if SMS not configured
    
    return {"run_id": run_id, "stats": stats}


def handle_command(text: str) -> Tuple[str, str]:
    cmd = text.strip().lower()
    reply = "unknown command"
    kind = "unknown"

    if cmd in {"ping", "status"}:
        kind = "status"
        reply = "QS OK"
    elif cmd.startswith("backtest"):
        kind = "backtest"
        parts = cmd.split()
        signal = parts[1] if len(parts) > 1 else "xgb_alpha"
        from qs.backtest import backtest_signal
        stats = backtest_signal(signal_name=signal)
        reply = f"Backtest {signal}: {stats}"
    elif cmd in {"daily", "run daily"}:
        kind = "daily"
        res = _run_daily_inline()
        reply = f"Daily done: {res}"
    elif cmd.startswith("buy ") or cmd.startswith("sell "):
        kind = "order"
        side, rest = cmd.split(" ", 1)
        sym, qty = rest.split()
        from qs.exec.ibkr_adapter import IBKRAdapter
        adapter = IBKRAdapter(paper=True)
        adapter.connect()
        adapter.place_order(symbol=sym.upper(), side=side, quantity=float(qty))
        adapter.disconnect()
        reply = f"{side.upper()} {qty} {sym.upper()} sent"
    elif cmd.startswith("alerts") or cmd.startswith("check alerts"):
        kind = "alerts"
        try:
            from qs.notify.alerts import send_trading_alerts, check_buy_signals, check_sell_signals, format_buy_alert, format_sell_alert
            buy_signals = check_buy_signals()
            sell_signals = check_sell_signals()
            
            if buy_signals or sell_signals:
                msg = ""
                if buy_signals:
                    msg += format_buy_alert(buy_signals[:3])
                if sell_signals:
                    msg += "\n" + format_sell_alert(sell_signals[:3])
                reply = msg
            else:
                reply = "No strong signals at this time."
        except Exception as e:
            reply = f"Error checking alerts: {str(e)}"
    elif cmd.startswith("option ") or cmd.startswith("opt "):
        kind = "option"
        try:
            # Format: option SYMBOL STRIKE EXPIRY [CALL|PUT] [S=price] [r=rate] [sigma=vol]
            parts = cmd.split()
            if len(parts) < 4:
                reply = "Usage: option SYMBOL STRIKE EXPIRY_DAYS [CALL|PUT] [S=price] [r=rate] [sigma=vol]"
            else:
                symbol = parts[1].upper()
                strike = float(parts[2])
                expiry_days = float(parts[3])
                option_type = parts[4].lower() if len(parts) > 4 and parts[4].upper() in ["CALL", "PUT"] else "call"
                
                # Parse optional parameters
                S = None
                r = 0.05
                sigma = None
                for part in parts[4:]:
                    if part.startswith("S="):
                        S = float(part.split("=")[1])
                    elif part.startswith("r="):
                        r = float(part.split("=")[1])
                    elif part.startswith("sigma="):
                        sigma = float(part.split("=")[1])
                
                # Get current price from database if not provided
                if S is None:
                    from sqlalchemy import text
                    from qs.db import get_engine
                    engine = get_engine()
                    with engine.begin() as conn:
                        result = conn.execute(
                            text("SELECT adj_close FROM prices WHERE symbol = :sym ORDER BY date DESC LIMIT 1"),
                            {"sym": symbol}
                        ).fetchone()
                        if result:
                            S = float(result[0])
                        else:
                            reply = f"Error: No price data for {symbol} and S not provided"
                            return kind, reply
                
                # Calculate volatility if not provided
                if sigma is None:
                    from qs.options import calculate_historical_volatility
                    from qs.db import get_engine
                    engine = get_engine()
                    sigma = calculate_historical_volatility(symbol, engine=engine)
                    if sigma is None:
                        reply = f"Error: Could not calculate volatility for {symbol}"
                        return kind, reply
                
                T = expiry_days / 365.0
                from qs.options import black_scholes, black_scholes_greeks
                price = black_scholes(S, strike, T, r, sigma, option_type)
                greeks = black_scholes_greeks(S, strike, T, r, sigma, option_type)
                
                # Check for anomaly
                from qs.notify.alerts import check_options_anomalies, format_options_anomaly_alert
                anomaly = check_options_anomalies(symbol, strike, expiry_days, price, option_type)
                
                reply = f"{symbol} {option_type.upper()} K={strike:.0f} T={expiry_days:.0f}d: ${price:.2f} | Δ={greeks['delta']:.3f} Γ={greeks['gamma']:.4f} Θ={greeks['theta']:.2f} ν={greeks['vega']:.2f}"
                
                if anomaly:
                    reply += f"\n⚠️ ANOMALY DETECTED!\n{format_options_anomaly_alert(anomaly)}"
        except Exception as e:
            reply = f"Error: {str(e)}"
    else:
        reply = "commands: status | backtest [signal] | daily | buy TICKER QTY | sell TICKER QTY | option SYMBOL STRIKE EXPIRY [CALL|PUT] | alerts"
    return kind, reply