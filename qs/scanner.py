from __future__ import annotations

import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from .db import get_engine
from sqlalchemy import text
from .notify.alerts import (
    check_buy_signals,
    check_sell_signals,
    check_options_anomalies,
    send_trading_alerts,
    format_buy_alert,
    format_sell_alert
)
from .utils.logger import get_logger

logger = get_logger(__name__)


class MarketScanner:
    """
    Continuous market scanner that analyzes markets and sends alerts.
    """
    
    def __init__(
        self,
        scan_interval: int = 300,  # 5 minutes default
        signal_threshold: float = 0.7,
        check_options: bool = True,
        check_signals: bool = True,
        auto_send_alerts: bool = True
    ):
        self.scan_interval = scan_interval
        self.signal_threshold = signal_threshold
        self.check_options = check_options
        self.check_signals = check_signals
        self.auto_send_alerts = auto_send_alerts
        self.running = False
        self.last_scan_time = None
        self.scan_count = 0
    
    def scan_markets(self) -> Dict:
        """
        Perform a single market scan.
        
        Returns:
        --------
        dict
            Scan results
        """
        results = {
            'timestamp': datetime.now(),
            'buy_signals': [],
            'sell_signals': [],
            'options_anomalies': [],
            'market_status': 'open'
        }
        
        try:
            # Check if market is open (simplified - in production, use market hours)
            current_hour = datetime.now().hour
            market_open = 9 <= current_hour < 16  # 9 AM to 4 PM EST
            
            if not market_open:
                results['market_status'] = 'closed'
                logger.info("Market is closed, skipping detailed scan")
                return results
            
            # Check buy signals
            if self.check_signals:
                buy_signals = check_buy_signals(threshold=self.signal_threshold)
                results['buy_signals'] = buy_signals
                logger.info(f"Found {len(buy_signals)} buy signals")
            
            # Check sell signals
            if self.check_signals:
                sell_signals = check_sell_signals(threshold=-self.signal_threshold)
                results['sell_signals'] = sell_signals
                logger.info(f"Found {len(sell_signals)} sell signals")
            
            # Check for price movements
            price_movements = self._check_price_movements()
            results['price_movements'] = price_movements
            
            # Check for volume spikes
            volume_spikes = self._check_volume_spikes()
            results['volume_spikes'] = volume_spikes
            
            self.last_scan_time = datetime.now()
            self.scan_count += 1
            
        except Exception as e:
            logger.error(f"Error during market scan: {e}")
            results['error'] = str(e)
        
        return results
    
    def _check_price_movements(self, threshold: float = 0.05) -> List[Dict]:
        """Check for significant price movements."""
        engine = get_engine()
        movements = []
        
        try:
            with engine.begin() as conn:
                # Get recent prices
                prices_df = pd.read_sql(
                    text("""
                        SELECT symbol, date, adj_close,
                               LAG(adj_close) OVER (PARTITION BY symbol ORDER BY date) as prev_close
                        FROM prices
                        WHERE date >= DATE('now', '-2 days')
                        ORDER BY symbol, date DESC
                    """),
                    conn
                )
            
            if prices_df.empty:
                return movements
            
            # Calculate daily returns
            prices_df['return'] = (prices_df['adj_close'] - prices_df['prev_close']) / prices_df['prev_close']
            
            # Filter significant movements
            significant = prices_df[
                (prices_df['return'].abs() > threshold) &
                (prices_df['date'] == prices_df['date'].max())
            ]
            
            for _, row in significant.iterrows():
                movements.append({
                    'symbol': row['symbol'],
                    'price': float(row['adj_close']),
                    'return': float(row['return']),
                    'date': row['date']
                })
        
        except Exception as e:
            logger.error(f"Error checking price movements: {e}")
        
        return movements
    
    def _check_volume_spikes(self, threshold: float = 2.0) -> List[Dict]:
        """Check for volume spikes."""
        engine = get_engine()
        spikes = []
        
        try:
            with engine.begin() as conn:
                # Get recent volumes
                volume_df = pd.read_sql(
                    text("""
                        SELECT symbol, date, volume,
                               AVG(volume) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) as avg_volume
                        FROM prices
                        WHERE date >= DATE('now', '-30 days')
                        ORDER BY symbol, date DESC
                    """),
                    conn
                )
            
            if volume_df.empty:
                return spikes
            
            # Calculate volume ratio
            volume_df['volume_ratio'] = volume_df['volume'] / volume_df['avg_volume']
            
            # Filter spikes
            significant = volume_df[
                (volume_df['volume_ratio'] > threshold) &
                (volume_df['date'] == volume_df['date'].max())
            ]
            
            for _, row in significant.iterrows():
                spikes.append({
                    'symbol': row['symbol'],
                    'volume': int(row['volume']),
                    'volume_ratio': float(row['volume_ratio']),
                    'date': row['date']
                })
        
        except Exception as e:
            logger.error(f"Error checking volume spikes: {e}")
        
        return spikes
    
    def run_continuous(self):
        """Run continuous market scanning."""
        self.running = True
        logger.info(f"Starting continuous market scanner (interval: {self.scan_interval}s)")
        
        try:
            while self.running:
                results = self.scan_markets()
                
                # Send alerts if enabled
                if self.auto_send_alerts:
                    self._process_alerts(results)
                
                # Log scan results
                logger.info(
                    f"Scan #{self.scan_count}: "
                    f"{len(results.get('buy_signals', []))} buys, "
                    f"{len(results.get('sell_signals', []))} sells, "
                    f"{len(results.get('price_movements', []))} price moves, "
                    f"{len(results.get('volume_spikes', []))} volume spikes"
                )
                
                # Wait for next scan
                time.sleep(self.scan_interval)
        
        except KeyboardInterrupt:
            logger.info("Market scanner stopped by user")
            self.running = False
        except Exception as e:
            logger.error(f"Error in continuous scan loop: {e}")
            self.running = False
    
    def _process_alerts(self, results: Dict):
        """Process scan results and send alerts."""
        messages = []
        
        # Price movements
        if results.get('price_movements'):
            msg = "📈 PRICE MOVEMENTS:\n"
            for move in results['price_movements'][:5]:  # Top 5
                direction = "📈" if move['return'] > 0 else "📉"
                msg += f"{direction} {move['symbol']}: {move['return']*100:+.2f}% @ ${move['price']:.2f}\n"
            messages.append(msg)
        
        # Volume spikes
        if results.get('volume_spikes'):
            msg = "📊 VOLUME SPIKES:\n"
            for spike in results['volume_spikes'][:5]:  # Top 5
                msg += f"{spike['symbol']}: {spike['volume_ratio']:.1f}x avg volume\n"
            messages.append(msg)
        
        # Buy signals
        if results.get('buy_signals'):
            messages.append(format_buy_alert(results['buy_signals'][:3]))
        
        # Sell signals
        if results.get('sell_signals'):
            messages.append(format_sell_alert(results['sell_signals'][:3]))
        
        # Send all messages
        from .notify.twilio_client import send_sms_update
        for msg in messages:
            send_sms_update(msg)
    
    def stop(self):
        """Stop the continuous scanner."""
        self.running = False
        logger.info("Market scanner stop requested")


def run_market_scanner(
    interval: int = 300,
    signal_threshold: float = 0.7,
    check_options: bool = True,
    check_signals: bool = True
):
    """
    Run market scanner continuously.
    
    Parameters:
    -----------
    interval : int
        Scan interval in seconds (default: 300 = 5 minutes)
    signal_threshold : float
        Signal threshold for alerts
    check_options : bool
        Check options anomalies
    check_signals : bool
        Check buy/sell signals
    """
    scanner = MarketScanner(
        scan_interval=interval,
        signal_threshold=signal_threshold,
        check_options=check_options,
        check_signals=check_signals,
        auto_send_alerts=True
    )
    scanner.run_continuous()

