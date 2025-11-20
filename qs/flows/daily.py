from __future__ import annotations

from prefect import flow, task

from ..data.ingest_prices import ingest_prices
from ..data.ingest_fundamentals import ingest_fundamentals
from ..features import compute_features
from ..ml.train import train_model
from ..signal import generate_signals
from ..backtest import backtest_signal
from ..config import get_settings


@task
def t_ingest_prices():
    settings = get_settings()
    tickers = [t.strip() for t in settings.default_tickers.split(',') if t.strip()]
    ingest_prices(tickers=tickers, start=settings.default_start)


@task
def t_ingest_fundamentals():
    settings = get_settings()
    tickers = [t.strip() for t in settings.default_tickers.split(',') if t.strip()]
    ingest_fundamentals(tickers)


@task
def t_features():
    compute_features()


@task
def t_train():
    train_model(model_name="xgb_alpha")


@task
def t_signals():
    generate_signals(model_name="xgb_alpha")


@task
def t_backtest():
    return backtest_signal(signal_name="xgb_alpha")


@flow
def daily_flow():
    t_ingest_prices()
    t_ingest_fundamentals()
    t_features()
    t_train()
    t_signals()
    stats = t_backtest()
    
    # Send SMS update if configured
    try:
        from ..notify.twilio_client import send_sms_update
        from ..notify.alerts import send_trading_alerts
        
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
        from ..utils.logger import get_logger
        logger = get_logger(__name__)
        logger.warning(f"SMS notification failed: {e}")
    
    return stats


if __name__ == "__main__":
    print(daily_flow())