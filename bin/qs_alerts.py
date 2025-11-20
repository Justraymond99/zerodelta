#!/usr/bin/env python3
from __future__ import annotations

import argparse
from qs.notify.alerts import (
    send_trading_alerts,
    check_buy_signals,
    check_sell_signals,
    check_options_anomalies,
    format_buy_alert,
    format_sell_alert,
    format_options_anomaly_alert
)


def main() -> None:
    p = argparse.ArgumentParser(description="Trading alerts and notifications")
    p.add_argument('--check-signals', action='store_true', help='Check buy/sell signals')
    p.add_argument('--check-options', action='store_true', help='Check options anomalies')
    p.add_argument('--send-sms', action='store_true', help='Send alerts via SMS')
    p.add_argument('--signal-threshold', type=float, default=0.7, help='Signal threshold')
    p.add_argument('--options-threshold', type=float, default=0.20, help='Options anomaly threshold')
    
    args = p.parse_args()
    
    if args.check_signals:
        print("Checking buy/sell signals...")
        buy_signals = check_buy_signals(threshold=args.signal_threshold)
        sell_signals = check_sell_signals(threshold=-args.signal_threshold)
        
        if buy_signals:
            print("\n" + format_buy_alert(buy_signals))
        if sell_signals:
            print("\n" + format_sell_alert(sell_signals))
        if not buy_signals and not sell_signals:
            print("No strong signals found.")
    
    if args.check_options:
        print("\nChecking options anomalies...")
        # This would require options chain data - placeholder
        print("Options anomaly checking requires options chain data source.")
    
    if args.send_sms:
        print("\nSending SMS alerts...")
        alerts_sent = send_trading_alerts(
            check_options=args.check_options,
            check_signals=args.check_signals,
            options_threshold=args.options_threshold,
            signal_threshold=args.signal_threshold
        )
        print(f"Sent {alerts_sent} alert(s)")


if __name__ == "__main__":
    main()

