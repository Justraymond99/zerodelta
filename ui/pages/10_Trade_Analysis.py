from __future__ import annotations

import os
import sys
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from qs.config import get_settings
from qs.db import get_engine
from qs.execution.quality import get_execution_analyzer

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_css import SHARED_CSS, CHART_LAYOUT, CHART_CONFIG

# Inject modern CSS
st.markdown(SHARED_CSS, unsafe_allow_html=True)

st.markdown("""
<div style="padding: 20px 0 30px 0;">
    <h1 style="font-size: 36px; font-weight: 800; background: linear-gradient(135deg, #00d4ff 0%, #0096ff 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin: 0;">
        📈 Trade Analysis
    </h1>
    <p style="color: #94a3b8; font-size: 14px; margin: 8px 0 0 0;">
        Execution quality, slippage analysis, market impact, and trade statistics
    </p>
</div>
""", unsafe_allow_html=True)

settings = get_settings()
engine = get_engine()
execution_analyzer = get_execution_analyzer()

# Get execution quality data
try:
    with engine.begin() as conn:
        execution_df = pd.read_sql(
            text("""
                SELECT order_id, symbol, side, quantity, expected_price, actual_price,
                       slippage, slippage_bps, timestamp
                FROM execution_quality
                ORDER BY timestamp DESC
                LIMIT 1000
            """),
            conn
        )
except Exception:
    execution_df = pd.DataFrame()
    # Try to get from trades table if execution_quality doesn't exist
    try:
        with engine.begin() as conn:
            execution_df = pd.read_sql(
                text("""
                    SELECT symbol, side, quantity, price, date
                    FROM trades
                    ORDER BY date DESC
                    LIMIT 1000
                """),
                conn
            )
    except Exception:
        pass

if not execution_df.empty:
    # Execution Quality Summary
    st.markdown('<div class="section-header">⚡ Execution Quality Summary</div>', unsafe_allow_html=True)
    
    if 'slippage_bps' in execution_df.columns:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Executions", len(execution_df))
        with col2:
            avg_slippage = execution_df['slippage_bps'].mean()
            st.metric("Avg Slippage", f"{avg_slippage:.2f} bps")
        with col3:
            median_slippage = execution_df['slippage_bps'].median()
            st.metric("Median Slippage", f"{median_slippage:.2f} bps")
        with col4:
            max_slippage = execution_df['slippage_bps'].abs().max()
            st.metric("Max Slippage", f"{max_slippage:.2f} bps")
        
        # Slippage by Symbol
        if 'symbol' in execution_df.columns:
            st.markdown('<div class="section-header">📊 Slippage by Symbol</div>', unsafe_allow_html=True)
            symbol_slippage = execution_df.groupby('symbol')['slippage_bps'].agg(['mean', 'std', 'count']).reset_index()
            symbol_slippage = symbol_slippage.sort_values('mean', ascending=False).head(20)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=symbol_slippage['symbol'],
                y=symbol_slippage['mean'],
                error_y=dict(type='data', array=symbol_slippage['std']),
                marker=dict(color='#00d4ff'),
                hovertemplate='<b>%{x}</b><br>Avg Slippage: %{y:.2f} bps<br>Count: %{text}<extra></extra>',
                text=symbol_slippage['count']
            ))
            
            layout = CHART_LAYOUT.copy()
            layout.update({
                'height': 400,
                'margin': dict(l=20, r=20, t=40, b=80),
                'xaxis': dict(showgrid=False, showline=True, linecolor='rgba(255, 255, 255, 0.2)', title='Symbol'),
                'yaxis': dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', showline=True, linecolor='rgba(255, 255, 255, 0.2)', title='Slippage (bps)'),
                'hovermode': 'closest'
            })
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
        
        # Slippage Distribution
        st.markdown('<div class="section-header">📈 Slippage Distribution</div>', unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=execution_df['slippage_bps'],
            nbinsx=30,
            marker=dict(color='#00d4ff'),
            hovertemplate='Slippage: %{x:.2f} bps<br>Count: %{y}<extra></extra>'
        ))
        
        layout = CHART_LAYOUT.copy()
        layout.update({
            'height': 400,
            'xaxis': dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', showline=True, linecolor='rgba(255, 255, 255, 0.2)', title='Slippage (bps)'),
            'yaxis': dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', showline=True, linecolor='rgba(255, 255, 255, 0.2)', title='Frequency'),
            'hovermode': 'closest'
        })
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
    
    # Execution Details
    st.markdown('<div class="section-header">📋 Execution Details</div>', unsafe_allow_html=True)
    st.dataframe(execution_df.tail(100), use_container_width=True, hide_index=True, height=400)
    
    # Trade Statistics
    if 'side' in execution_df.columns:
        st.markdown('<div class="section-header">📊 Trade Statistics</div>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_trades = len(execution_df)
            st.metric("Total Trades", total_trades)
        with col2:
            buys = len(execution_df[execution_df['side'].str.lower() == 'buy']) if 'side' in execution_df.columns else 0
            st.metric("Buys", buys)
        with col3:
            sells = len(execution_df[execution_df['side'].str.lower() == 'sell']) if 'side' in execution_df.columns else 0
            st.metric("Sells", sells)
        with col4:
            if 'quantity' in execution_df.columns:
                total_volume = execution_df['quantity'].sum()
                st.metric("Total Volume", f"{total_volume:,.0f}")
        
        # Market Impact Analysis
        if 'symbol' in execution_df.columns and 'quantity' in execution_df.columns:
            st.markdown('<div class="section-header">💥 Market Impact Analysis</div>', unsafe_allow_html=True)
            symbol_select = st.selectbox("Select Symbol", execution_df['symbol'].unique() if 'symbol' in execution_df.columns else [])
            
            if symbol_select and 'quantity' in execution_df.columns and 'actual_price' in execution_df.columns:
                symbol_trades = execution_df[execution_df['symbol'] == symbol_select]
                if not symbol_trades.empty:
                    # Calculate estimated market impact
                    market_impacts = []
                    for _, trade in symbol_trades.iterrows():
                        impact = execution_analyzer.calculate_market_impact(
                            symbol_select,
                            trade.get('quantity', 0),
                            trade.get('actual_price', 0)
                        )
                        market_impacts.append(impact)
                    
                    symbol_trades = symbol_trades.copy()
                    symbol_trades['market_impact'] = market_impacts
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=symbol_trades.get('timestamp', symbol_trades.index),
                        y=symbol_trades['market_impact'],
                        mode='markers',
                        marker=dict(size=8, color='#f59e0b'),
                        hovertemplate='Impact: $%{y:.2f}<br>Quantity: %{text}<extra></extra>',
                        text=symbol_trades.get('quantity', 0)
                    ))
                    
                    layout = CHART_LAYOUT.copy()
                    layout.update({
                        'height': 400,
                        'xaxis': dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', showline=True, linecolor='rgba(255, 255, 255, 0.2)', title='Time'),
                        'yaxis': dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', showline=True, linecolor='rgba(255, 255, 255, 0.2)', title='Market Impact ($)'),
                        'hovermode': 'closest'
                    })
                    fig.update_layout(**layout)
                    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
else:
    st.info("👈 No execution quality data available. Trades will appear here once executed.")

