#!/usr/bin/env python3
from __future__ import annotations

import argparse
import signal
import sys
import time
from qs.scheduler import run_scheduler, setup_schedule
from qs.scanner import run_market_scanner
from qs.utils.logger import setup_logger, get_logger


def signal_handler(sig, frame):
    """Handle interrupt signal."""
    logger = get_logger(__name__)
    logger.info("Received stop signal, shutting down...")
    sys.exit(0)


def main() -> None:
    p = argparse.ArgumentParser(description="QS Trading System Daemon - Continuous Market Analysis")
    p.add_argument('--mode', choices=['scanner', 'scheduler', 'both'], default='both',
                   help='Operation mode: scanner (continuous), scheduler (scheduled tasks), or both')
    p.add_argument('--scan-interval', type=int, default=300,
                   help='Market scan interval in seconds (default: 300 = 5 min)')
    p.add_argument('--daily-time', type=str, default='09:00',
                   help='Daily flow execution time (HH:MM format, default: 09:00)')
    p.add_argument('--scan-schedule', type=int, default=15,
                   help='Scheduled scan interval in minutes (default: 15)')
    p.add_argument('--alerts-schedule', type=int, default=30,
                   help='Scheduled alerts check interval in minutes (default: 30)')
    p.add_argument('--log-file', type=str, default='./logs/qs_daemon.log',
                   help='Log file path')
    
    args = p.parse_args()
    
    # Setup logging
    setup_logger("qs", log_file=args.log_file)
    logger = get_logger(__name__)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=" * 60)
    logger.info("QS Trading System Daemon Starting")
    logger.info("=" * 60)
    logger.info(f"Mode: {args.mode}")
    logger.info(f"Scan interval: {args.scan_interval}s")
    logger.info(f"Daily flow time: {args.daily_time}")
    logger.info(f"Scheduled scan: every {args.scan_schedule} minutes")
    logger.info(f"Scheduled alerts: every {args.alerts_schedule} minutes")
    logger.info("=" * 60)
    
    try:
        if args.mode in ['scanner', 'both']:
            # Start continuous scanner in background thread
            import threading
            scanner_thread = threading.Thread(
                target=run_market_scanner,
                args=(args.scan_interval,),
                daemon=True
            )
            scanner_thread.start()
            logger.info("Continuous market scanner started")
        
        if args.mode in ['scheduler', 'both']:
            # Setup and run scheduler
            setup_schedule(
                daily_flow_time=args.daily_time,
                scan_interval_minutes=args.scan_schedule,
                alerts_interval_minutes=args.alerts_schedule
            )
            
            if args.mode == 'scheduler':
                # Run scheduler in main thread
                run_scheduler()
            else:
                # Run scheduler in background thread
                import threading
                scheduler_thread = threading.Thread(
                    target=run_scheduler,
                    daemon=True
                )
                scheduler_thread.start()
                logger.info("Scheduler started")
        
        # Keep main thread alive
        if args.mode == 'both':
            logger.info("Daemon running in background. Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                logger.info("Shutting down...")
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

