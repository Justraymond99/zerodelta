#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time
import signal
import sys
from qs.trading.automated import AutomatedTrader
from qs.utils.logger import setup_logger, get_logger


def signal_handler(sig, frame):
    """Handle interrupt signal."""
    logger = get_logger(__name__)
    logger.info("Stopping automated trader...")
    sys.exit(0)


def main() -> None:
    p = argparse.ArgumentParser(description="Automated Trading System")
    p.add_argument('--signal-name', type=str, default='xgb_alpha', help='Signal name to trade')
    p.add_argument('--account-value', type=float, default=100000.0, help='Account value')
    p.add_argument('--max-position-pct', type=float, default=0.10, help='Max position % of account')
    p.add_argument('--min-signal-threshold', type=float, default=0.7, help='Minimum signal score')
    p.add_argument('--paper', action='store_true', default=True, help='Paper trading mode')
    p.add_argument('--live', action='store_true', help='Live trading mode (requires --auto-execute)')
    p.add_argument('--auto-execute', action='store_true', help='Auto-execute trades (DANGEROUS)')
    p.add_argument('--interval', type=int, default=300, help='Trading cycle interval in seconds')
    p.add_argument('--once', action='store_true', help='Run single cycle and exit')
    p.add_argument('--log-file', type=str, default='./logs/auto_trade.log', help='Log file')
    
    args = p.parse_args()
    
    # Safety check
    if args.live and args.auto_execute:
        response = input("⚠️  WARNING: Live trading with auto-execute enabled! Type 'YES' to continue: ")
        if response != 'YES':
            print("Aborted.")
            sys.exit(1)
    
    # Setup logging
    setup_logger("qs", log_file=args.log_file)
    logger = get_logger(__name__)
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create trader
    trader = AutomatedTrader(
        signal_name=args.signal_name,
        account_value=args.account_value,
        max_position_pct=args.max_position_pct,
        min_signal_threshold=args.min_signal_threshold,
        paper_trading=not args.live,
        auto_execute=args.auto_execute
    )
    
    logger.info("=" * 60)
    logger.info("Automated Trading System Starting")
    logger.info("=" * 60)
    logger.info(f"Mode: {'PAPER' if args.paper else 'LIVE'}")
    logger.info(f"Signal: {args.signal_name}")
    logger.info(f"Account Value: ${args.account_value:,.2f}")
    logger.info(f"Max Position: {args.max_position_pct*100:.1f}%")
    logger.info(f"Signal Threshold: {args.min_signal_threshold}")
    logger.info(f"Auto Execute: {args.auto_execute}")
    logger.info("=" * 60)
    
    if args.once:
        # Single cycle
        logger.info("Running single trading cycle...")
        result = trader.run_cycle()
        print(f"\nTrading Cycle Results:")
        print(f"  Trades Generated: {result['trades_generated']}")
        print(f"  Trades Executed: {result['trades_executed']}")
        print(f"  Trades Rejected: {result['trades_rejected']}")
    else:
        # Continuous trading
        logger.info(f"Starting continuous trading (interval: {args.interval}s)")
        logger.info("Press Ctrl+C to stop\n")
        
        try:
            while True:
                result = trader.run_cycle()
                logger.info(
                    f"Cycle complete: {result['trades_executed']} executed, "
                    f"{result['trades_rejected']} rejected"
                )
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("Stopped by user")


if __name__ == "__main__":
    main()

