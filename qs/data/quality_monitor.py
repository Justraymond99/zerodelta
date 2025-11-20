from __future__ import annotations

from typing import Dict, List
from datetime import datetime, timedelta
import pandas as pd
from ..db import get_engine
from sqlalchemy import text
from ..utils.logger import get_logger
from ..notify.twilio_client import send_sms_update

logger = get_logger(__name__)


class DataQualityMonitor:
    """
    Monitors data quality and automatically backfills missing data.
    """
    
    def __init__(self):
        self.issues: List[Dict] = []
    
    def check_data_quality(self) -> Dict[str, List[Dict]]:
        """Check data quality across all symbols."""
        engine = get_engine()
        issues = {
            'missing_data': [],
            'stale_data': [],
            'outliers': [],
            'gaps': []
        }
        
        try:
            with engine.begin() as conn:
                # Get all symbols
                symbols_df = pd.read_sql(
                    text("SELECT DISTINCT symbol FROM prices"),
                    conn
                )
                
                if symbols_df.empty:
                    return issues
                
                # Get latest date
                latest_date_df = pd.read_sql(
                    text("SELECT MAX(date) as latest FROM prices"),
                    conn
                )
                latest_date = pd.to_datetime(latest_date_df['latest'].iloc[0]).date() if not latest_date_df.empty else None
                
                if not latest_date:
                    return issues
                
                # Check each symbol
                for symbol in symbols_df['symbol']:
                    # Check for missing recent data
                    symbol_data = pd.read_sql(
                        text("""
                            SELECT date, adj_close, volume
                            FROM prices
                            WHERE symbol = :sym
                            ORDER BY date DESC
                            LIMIT 10
                        """),
                        conn,
                        params={"sym": symbol}
                    )
                    
                    if symbol_data.empty:
                        issues['missing_data'].append({
                            'symbol': symbol,
                            'issue': 'No data found',
                            'severity': 'high'
                        })
                        continue
                    
                    # Check for stale data
                    last_date = pd.to_datetime(symbol_data['date'].iloc[0]).date()
                    days_old = (datetime.now().date() - last_date).days
                    
                    if days_old > 1:
                        issues['stale_data'].append({
                            'symbol': symbol,
                            'issue': f'Data is {days_old} days old',
                            'last_date': str(last_date),
                            'severity': 'medium' if days_old <= 3 else 'high'
                        })
                    
                    # Check for outliers
                    if len(symbol_data) > 1:
                        returns = symbol_data['adj_close'].pct_change().dropna()
                        extreme_returns = returns[returns.abs() > 0.20]  # >20% move
                        
                        if not extreme_returns.empty:
                            issues['outliers'].append({
                                'symbol': symbol,
                                'issue': f'{len(extreme_returns)} extreme returns (>20%)',
                                'dates': [str(d) for d in symbol_data.loc[extreme_returns.index, 'date']],
                                'severity': 'low'
                            })
                    
                    # Check for gaps
                    if len(symbol_data) > 1:
                        dates = pd.to_datetime(symbol_data['date']).sort_values()
                        gaps = []
                        for i in range(len(dates) - 1):
                            gap = (dates.iloc[i+1] - dates.iloc[i]).days
                            if gap > 1:
                                gaps.append(gap)
                        
                        if gaps:
                            issues['gaps'].append({
                                'symbol': symbol,
                                'issue': f'Data gaps found: {gaps}',
                                'severity': 'medium'
                            })
        
        except Exception as e:
            logger.error(f"Error checking data quality: {e}")
        
        return issues
    
    def auto_backfill(self, symbol: str, start_date: datetime, end_date: datetime) -> bool:
        """Automatically backfill missing data for a symbol."""
        try:
            from ..data.ingest_prices import fetch_prices, write_prices
            
            logger.info(f"Backfilling {symbol} from {start_date.date()} to {end_date.date()}")
            
            # Fetch missing data
            df = fetch_prices([symbol], start_date.strftime("%Y-%m-%d"))
            
            if not df.empty:
                # Filter to date range
                df['date'] = pd.to_datetime(df['date'])
                df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
                
                if not df.empty:
                    write_prices(df)
                    logger.info(f"Backfilled {len(df)} rows for {symbol}")
                    return True
        
        except Exception as e:
            logger.error(f"Error backfilling {symbol}: {e}")
        
        return False
    
    def monitor_and_alert(self, send_alerts: bool = True):
        """Monitor data quality and send alerts if issues found."""
        issues = self.check_data_quality()
        
        total_issues = sum(len(v) for v in issues.values())
        
        if total_issues > 0:
            logger.warning(f"Data quality issues found: {total_issues} total")
            
            if send_alerts:
                # Format alert message
                msg_parts = ["⚠️ Data Quality Alert\n"]
                
                if issues['missing_data']:
                    msg_parts.append(f"Missing Data: {len(issues['missing_data'])} symbols")
                
                if issues['stale_data']:
                    msg_parts.append(f"Stale Data: {len(issues['stale_data'])} symbols")
                
                if issues['gaps']:
                    msg_parts.append(f"Data Gaps: {len(issues['gaps'])} symbols")
                
                message = "\n".join(msg_parts)
                send_sms_update(message)
        
        # Log issues to database
        self._log_issues(issues)
        
        return issues
    
    def _log_issues(self, issues: Dict[str, List[Dict]]):
        """Log issues to database."""
        try:
            engine = get_engine()
            with engine.begin() as conn:
                for issue_type, issue_list in issues.items():
                    for issue in issue_list:
                        conn.execute(
                            text("""
                                INSERT INTO data_quality_log (symbol, date, issue_type, description)
                                VALUES (:sym, :date, :type, :desc)
                            """),
                            {
                                'sym': issue.get('symbol', ''),
                                'date': datetime.now().date(),
                                'type': issue_type,
                                'desc': issue.get('issue', '')
                            }
                        )
        except Exception as e:
            logger.error(f"Error logging issues: {e}")


# Global monitor
_quality_monitor: Optional[DataQualityMonitor] = None


def get_quality_monitor() -> DataQualityMonitor:
    """Get global data quality monitor."""
    global _quality_monitor
    if _quality_monitor is None:
        _quality_monitor = DataQualityMonitor()
    return _quality_monitor

