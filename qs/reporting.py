from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from .backtest import backtest_signal
from .attribution import performance_attribution
from .utils.logger import get_logger

logger = get_logger(__name__)

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab not available. PDF reports will not work. Install with: pip install reportlab")


def generate_performance_report(
    signal_name: str,
    output_path: str,
    format: str = "pdf",
    include_charts: bool = False
) -> None:
    """
    Generate comprehensive performance report.
    
    Parameters:
    -----------
    signal_name : str
        Signal name to analyze
    output_path : str
        Output file path
    format : str
        Report format: "pdf", "html", "markdown"
    include_charts : bool
        Whether to include charts (requires matplotlib)
    """
    if format == "pdf":
        _generate_pdf_report(signal_name, output_path, include_charts)
    elif format == "html":
        _generate_html_report(signal_name, output_path, include_charts)
    elif format == "markdown":
        _generate_markdown_report(signal_name, output_path, include_charts)
    else:
        raise ValueError(f"Unsupported format: {format}")


def _generate_pdf_report(signal_name: str, output_path: str, include_charts: bool):
    """Generate PDF performance report."""
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab is required for PDF reports. Install with: pip install reportlab")
    
    # Get backtest stats
    stats = backtest_signal(signal_name=signal_name, return_equity_curve=True)
    attribution = performance_attribution(signal_name)
    
    # Create PDF
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=30
    )
    
    # Title
    story.append(Paragraph(f"Performance Report: {signal_name}", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Executive Summary
    story.append(Paragraph("Executive Summary", styles['Heading2']))
    summary_data = [
        ['Metric', 'Value'],
        ['Total Return', f"{stats.get('total_return', 0)*100:.2f}%"],
        ['Annualized Return', f"{stats.get('annualized_return', 0)*100:.2f}%"],
        ['Sharpe Ratio', f"{stats.get('sharpe', 0):.2f}"],
        ['Sortino Ratio', f"{stats.get('sortino', 0):.2f}"],
        ['Max Drawdown', f"{stats.get('max_drawdown', 0)*100:.2f}%"],
        ['Win Rate', f"{stats.get('win_rate', 0)*100:.2f}%"],
        ['Volatility', f"{stats.get('volatility', 0)*100:.2f}%"],
    ]
    
    if 'beta' in stats:
        summary_data.append(['Beta', f"{stats.get('beta', 0):.2f}"])
        summary_data.append(['Alpha', f"{stats.get('alpha', 0)*100:.2f}%"])
    
    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Performance Attribution
    if attribution and 'symbol_contributions' in attribution:
        story.append(Paragraph("Top Contributors", styles['Heading2']))
        top_contributors = sorted(
            attribution['symbol_contributions'].items(),
            key=lambda x: x[1].get('contribution', 0),
            reverse=True
        )[:10]
        
        contrib_data = [['Symbol', 'Contribution', 'Avg Weight', 'Avg Return']]
        for symbol, data in top_contributors:
            contrib_data.append([
                symbol,
                f"{data.get('contribution', 0)*100:.2f}%",
                f"{data.get('avg_weight', 0)*100:.2f}%",
                f"{data.get('avg_return', 0)*100:.2f}%"
            ])
        
        contrib_table = Table(contrib_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        contrib_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(contrib_table)
    
    # Build PDF
    doc.build(story)
    logger.info(f"Generated PDF report: {output_path}")


def _generate_html_report(signal_name: str, output_path: str, include_charts: bool):
    """Generate HTML performance report."""
    stats = backtest_signal(signal_name=signal_name, return_equity_curve=True)
    attribution = performance_attribution(signal_name)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Performance Report: {signal_name}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1 {{ color: #1f4788; }}
            table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            th {{ background-color: #4CAF50; color: white; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
            .metric {{ font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>Performance Report: {signal_name}</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>Executive Summary</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Total Return</td><td>{stats.get('total_return', 0)*100:.2f}%</td></tr>
            <tr><td>Annualized Return</td><td>{stats.get('annualized_return', 0)*100:.2f}%</td></tr>
            <tr><td>Sharpe Ratio</td><td>{stats.get('sharpe', 0):.2f}</td></tr>
            <tr><td>Sortino Ratio</td><td>{stats.get('sortino', 0):.2f}</td></tr>
            <tr><td>Max Drawdown</td><td>{stats.get('max_drawdown', 0)*100:.2f}%</td></tr>
            <tr><td>Win Rate</td><td>{stats.get('win_rate', 0)*100:.2f}%</td></tr>
            <tr><td>Volatility</td><td>{stats.get('volatility', 0)*100:.2f}%</td></tr>
    """
    
    if 'beta' in stats:
        html += f"""
            <tr><td>Beta</td><td>{stats.get('beta', 0):.2f}</td></tr>
            <tr><td>Alpha</td><td>{stats.get('alpha', 0)*100:.2f}%</td></tr>
        """
    
    html += """
        </table>
    </body>
    </html>
    """
    
    with open(output_path, 'w') as f:
        f.write(html)
    logger.info(f"Generated HTML report: {output_path}")


def _generate_markdown_report(signal_name: str, output_path: str, include_charts: bool):
    """Generate Markdown performance report."""
    stats = backtest_signal(signal_name=signal_name, return_equity_curve=True)
    attribution = performance_attribution(signal_name)
    
    md = f"""# Performance Report: {signal_name}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Return | {stats.get('total_return', 0)*100:.2f}% |
| Annualized Return | {stats.get('annualized_return', 0)*100:.2f}% |
| Sharpe Ratio | {stats.get('sharpe', 0):.2f} |
| Sortino Ratio | {stats.get('sortino', 0):.2f} |
| Max Drawdown | {stats.get('max_drawdown', 0)*100:.2f}% |
| Win Rate | {stats.get('win_rate', 0)*100:.2f}% |
| Volatility | {stats.get('volatility', 0)*100:.2f}% |
"""
    
    if 'beta' in stats:
        md += f"| Beta | {stats.get('beta', 0):.2f} |\n"
        md += f"| Alpha | {stats.get('alpha', 0)*100:.2f}% |\n"
    
    if attribution and 'symbol_contributions' in attribution:
        md += "\n## Top Contributors\n\n"
        md += "| Symbol | Contribution | Avg Weight | Avg Return |\n"
        md += "|--------|-------------|------------|------------|\n"
        
        top_contributors = sorted(
            attribution['symbol_contributions'].items(),
            key=lambda x: x[1].get('contribution', 0),
            reverse=True
        )[:10]
        
        for symbol, data in top_contributors:
            md += f"| {symbol} | {data.get('contribution', 0)*100:.2f}% | {data.get('avg_weight', 0)*100:.2f}% | {data.get('avg_return', 0)*100:.2f}% |\n"
    
    with open(output_path, 'w') as f:
        f.write(md)
    logger.info(f"Generated Markdown report: {output_path}")

