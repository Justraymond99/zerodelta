#!/usr/bin/env python3
from __future__ import annotations

import argparse
import signal
import sys
from qs.scanner import MarketScanner, run_market_scanner


def signal_handler(sig, frame):
    """Handle interrupt signal."""
    print("\nStopping market scanner...")
    sys.exit(0)


def main() -> None:
    p = argparse.ArgumentParser(description="Continuous market scanner")
    p.add_argument('--interval', type=int, default=300, help='Scan interval in seconds (default: 300 = 5 min)')
    p.add_argument('--signal-threshold', type=float, default=0.7, help='Signal threshold for alerts')
    p.add_argument('--no-options', action='store_true', help='Disable options anomaly checking')
    p.add_argument('--no-signals', action='store_true', help='Disable buy/sell signal checking')
    p.add_argument('--no-alerts', action='store_true', help='Disable automatic SMS alerts')
    p.add_argument('--once', action='store_true', help='Run single scan and exit')
    
    args = p.parse_args()
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    scanner = MarketScanner(
        scan_interval=args.interval,
        signal_threshold=args.signal_threshold,
        check_options=not args.no_options,
        check_signals=not args.no_signals,
        auto_send_alerts=not args.no_alerts
    )
    
    if args.once:
        # Single scan
        print("Running single market scan...")
        results = scanner.scan_markets()
        print(f"\nScan Results:")
        print(f"  Buy signals: {len(results.get('buy_signals', []))}")
        print(f"  Sell signals: {len(results.get('sell_signals', []))}")
        print(f"  Price movements: {len(results.get('price_movements', []))}")
        print(f"  Volume spikes: {len(results.get('volume_spikes', []))}")
    else:
        # Continuous scanning
        print(f"Starting continuous market scanner...")
        print(f"  Interval: {args.interval} seconds")
        print(f"  Signal threshold: {args.signal_threshold}")
        print(f"  Options checking: {not args.no_options}")
        print(f"  Signal checking: {not args.no_signals}")
        print(f"  Auto alerts: {not args.no_alerts}")
        print(f"\nPress Ctrl+C to stop\n")
        scanner.run_continuous()


if __name__ == "__main__":
    main()

