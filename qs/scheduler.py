from __future__ import annotations

import schedule
import time
from datetime import datetime
from .flows.daily import daily_flow
from .scanner import MarketScanner
from .notify.alerts import send_trading_alerts
from .utils.logger import get_logger

logger = get_logger(__name__)


def scheduled_daily_flow():
    """Scheduled daily flow execution."""
    logger.info("Starting scheduled daily flow")
    try:
        stats = daily_flow()
        logger.info(f"Daily flow completed: {stats}")
    except Exception as e:
        logger.error(f"Error in scheduled daily flow: {e}")


def scheduled_market_scan():
    """Scheduled market scan."""
    logger.info("Starting scheduled market scan")
    try:
        scanner = MarketScanner(
            scan_interval=60,  # Not used for single scan
            auto_send_alerts=True
        )
        results = scanner.scan_markets()
        logger.info(f"Market scan completed: {len(results.get('buy_signals', []))} buys, {len(results.get('sell_signals', []))} sells")
    except Exception as e:
        logger.error(f"Error in scheduled market scan: {e}")


def scheduled_alerts_check():
    """Scheduled alerts check."""
    logger.info("Checking for trading alerts")
    try:
        alerts_sent = send_trading_alerts(check_options=False, check_signals=True)
        logger.info(f"Sent {alerts_sent} alert(s)")
    except Exception as e:
        logger.error(f"Error in scheduled alerts check: {e}")


def setup_schedule(
    daily_flow_time: str = "09:00",  # 9 AM
    scan_interval_minutes: int = 15,
    alerts_interval_minutes: int = 30
):
    """
    Setup scheduled tasks.
    
    Parameters:
    -----------
    daily_flow_time : str
        Time to run daily flow (HH:MM format)
    scan_interval_minutes : int
        Market scan interval in minutes
    alerts_interval_minutes : int
        Alerts check interval in minutes
    """
    # Daily flow - run once per day
    schedule.every().day.at(daily_flow_time).do(scheduled_daily_flow)
    logger.info(f"Scheduled daily flow at {daily_flow_time}")
    
    # Market scans - run every N minutes during market hours
    schedule.every(scan_interval_minutes).minutes.do(scheduled_market_scan)
    logger.info(f"Scheduled market scans every {scan_interval_minutes} minutes")
    
    # Alerts check - run every N minutes
    schedule.every(alerts_interval_minutes).minutes.do(scheduled_alerts_check)
    logger.info(f"Scheduled alerts check every {alerts_interval_minutes} minutes")


def run_scheduler():
    """Run the scheduler continuously."""
    logger.info("Starting scheduler...")
    
    # Setup default schedule
    setup_schedule()
    
    logger.info("Scheduler running. Press Ctrl+C to stop.")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Error in scheduler: {e}")


if __name__ == "__main__":
    run_scheduler()

