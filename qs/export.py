from __future__ import annotations

import pandas as pd
import json
from pathlib import Path
from typing import Dict, Any
from .db import get_engine
from sqlalchemy import text
from .utils.logger import get_logger

logger = get_logger(__name__)


def export_backtest_results(
    signal_name: str,
    output_path: str,
    format: str = "json"
) -> None:
    """
    Export backtest results to file.
    
    Parameters:
    -----------
    signal_name : str
        Signal name
    output_path : str
        Output file path
    format : str
        Export format: "json", "csv", "excel"
    """
    from .backtest import backtest_signal
    
    stats = backtest_signal(signal_name=signal_name, return_equity_curve=True)
    
    if format == "json":
        # Convert numpy types to native Python types
        export_data = {}
        for k, v in stats.items():
            if k in ['equity_curve', 'drawdown_series', 'returns', 'weights']:
                # Convert dict of dates to list of dicts
                export_data[k] = [{'date': str(date), 'value': float(val)} for date, val in v.items()]
            else:
                export_data[k] = float(v) if isinstance(v, (int, float)) else v
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
    
    elif format == "csv":
        # Export as CSV (flattened)
        df = pd.DataFrame([stats])
        df.to_csv(output_path, index=False)
    
    elif format == "excel":
        # Export to Excel with multiple sheets
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Summary sheet
            pd.DataFrame([stats]).to_excel(writer, sheet_name='Summary', index=False)
            
            # Equity curve
            if 'equity_curve' in stats:
                equity_df = pd.DataFrame(list(stats['equity_curve'].items()), columns=['date', 'equity'])
                equity_df.to_excel(writer, sheet_name='Equity Curve', index=False)
            
            # Drawdown
            if 'drawdown_series' in stats:
                dd_df = pd.DataFrame(list(stats['drawdown_series'].items()), columns=['date', 'drawdown'])
                dd_df.to_excel(writer, sheet_name='Drawdown', index=False)
    
    logger.info(f"Exported backtest results to {output_path}")


def export_signals(
    signal_name: str,
    output_path: str,
    start_date: str | None = None,
    end_date: str | None = None
) -> None:
    """
    Export signals to CSV.
    
    Parameters:
    -----------
    signal_name : str
        Signal name
    output_path : str
        Output file path
    start_date : str, optional
        Start date filter
    end_date : str, optional
        End date filter
    """
    engine = get_engine()
    
    query = "SELECT symbol, date, score FROM signals WHERE signal_name = :name"
    params = {"name": signal_name}
    
    if start_date:
        query += " AND date >= :start_date"
        params['start_date'] = start_date
    if end_date:
        query += " AND date <= :end_date"
        params['end_date'] = end_date
    
    with engine.begin() as conn:
        df = pd.read_sql(text(query), conn, params=params)
    
    df.to_csv(output_path, index=False)
    logger.info(f"Exported {len(df)} signals to {output_path}")


def export_portfolio_holdings(
    signal_name: str,
    date: str,
    output_path: str
) -> None:
    """
    Export current portfolio holdings.
    
    Parameters:
    -----------
    signal_name : str
        Signal name
    date : str
        Date to export
    output_path : str
        Output file path
    """
    engine = get_engine()
    
    with engine.begin() as conn:
        holdings = pd.read_sql(
            text("""
                SELECT s.symbol, s.score, p.adj_close as price
                FROM signals s
                JOIN prices p ON s.symbol = p.symbol AND s.date = p.date
                WHERE s.signal_name = :name AND s.date = :date
                ORDER BY s.score DESC
            """),
            conn,
            params={"name": signal_name, "date": date}
        )
    
    holdings.to_csv(output_path, index=False)
    logger.info(f"Exported portfolio holdings to {output_path}")

