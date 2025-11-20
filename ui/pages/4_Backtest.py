from __future__ import annotations

import os
import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from sqlalchemy import create_engine, text

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from qs.config import get_settings
from qs.backtest import backtest_signal
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_css import SHARED_CSS, CHART_LAYOUT, CHART_CONFIG

# Inject modern CSS
st.markdown(SHARED_CSS, unsafe_allow_html=True)

st.markdown("""
<div style="padding: 20px 0 30px 0;">
    <h1 style="font-size: 36px; font-weight: 800; background: linear-gradient(135deg, #00d4ff 0%, #0096ff 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin: 0;">
        📉 Backtest Analysis
    </h1>
    <p style="color: #94a3b8; font-size: 14px; margin: 8px 0 0 0;">
        Comprehensive performance analysis and metrics
    </p>
</div>
""", unsafe_allow_html=True)

settings = get_settings()
engine = create_engine(f"duckdb:///{settings.duckdb_path}?read_only=TRUE")

try:
    signals = pd.read_sql(text("SELECT DISTINCT signal_name FROM signals ORDER BY signal_name"), engine)['signal_name'].tolist()
except Exception:
    st.warning("Database is busy; retry in a few seconds while data is loading.")
    signals = []

col1, col2 = st.columns(2)
with col1:
    signal_name = st.selectbox("Signal", signals, index=0 if signals else None)
with col2:
    benchmark = st.selectbox("Benchmark (optional)", [None] + signals, index=0)

if signal_name:
    with st.spinner("Running backtest analysis..."):
        stats = backtest_signal(signal_name=signal_name, benchmark_symbol=benchmark, return_equity_curve=True)
    
    if stats:
        st.markdown('<div class="section-header">📊 Key Performance Metrics</div>', unsafe_allow_html=True)
        
        metric_cols = st.columns(4)
        with metric_cols[0]:
            st.metric("Total Return", f"{stats.get('total_return', 0)*100:.2f}%")
            st.metric("Sharpe Ratio", f"{stats.get('sharpe', 0):.2f}")
        with metric_cols[1]:
            st.metric("Sortino Ratio", f"{stats.get('sortino', 0):.2f}")
            st.metric("Max Drawdown", f"{stats.get('max_drawdown', 0)*100:.2f}%")
        with metric_cols[2]:
            st.metric("Win Rate", f"{stats.get('win_rate', 0)*100:.2f}%")
            st.metric("Calmar Ratio", f"{stats.get('calmar', 0):.2f}")
        with metric_cols[3]:
            if 'beta' in stats:
                st.metric("Beta", f"{stats.get('beta', 0):.2f}")
                st.metric("Alpha", f"{stats.get('alpha', 0)*100:.2f}%")
        
        # Equity Curve
        if 'equity_curve' in stats:
            st.markdown('<div class="section-header">📈 Equity Curve</div>', unsafe_allow_html=True)
            equity_df = pd.DataFrame(list(stats['equity_curve'].items()), columns=['date', 'equity'])
            equity_df['date'] = pd.to_datetime(equity_df['date'])
            equity_df = equity_df.sort_values('date')
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=equity_df['date'],
                y=equity_df['equity'],
                mode='lines',
                name='Portfolio Equity',
                line=dict(color='#00d4ff', width=3),
                fill='tozeroy',
                fillcolor='rgba(0, 212, 255, 0.1)'
            ))
            
            layout = CHART_LAYOUT.copy()
            layout.update({'height': 450})
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
        
        # Drawdown Chart
        if 'drawdown_series' in stats:
            st.markdown('<div class="section-header">📉 Drawdown Analysis</div>', unsafe_allow_html=True)
            dd_df = pd.DataFrame(list(stats['drawdown_series'].items()), columns=['date', 'drawdown'])
            dd_df['date'] = pd.to_datetime(dd_df['date'])
            dd_df = dd_df.sort_values('date')
            dd_df['drawdown'] = dd_df['drawdown'] * 100
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dd_df['date'],
                y=dd_df['drawdown'],
                mode='lines',
                fill='tozeroy',
                fillcolor='rgba(239, 68, 68, 0.2)',
                line=dict(color='#ef4444', width=2),
                name='Drawdown'
            ))
            
            layout = CHART_LAYOUT.copy()
            layout.update({
                'height': 350,
                'yaxis': dict(
                    showgrid=True,
                    gridcolor='rgba(255, 255, 255, 0.1)',
                    showline=True,
                    linecolor='rgba(255, 255, 255, 0.2)',
                    title='Drawdown (%)'
                )
            })
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
        
        # Rolling Metrics
        if 'returns' in stats:
            st.markdown('<div class="section-header">📊 Rolling Performance Metrics</div>', unsafe_allow_html=True)
            returns_df = pd.DataFrame(list(stats['returns'].items()), columns=['date', 'return'])
            returns_df['date'] = pd.to_datetime(returns_df['date'])
            returns_df = returns_df.sort_values('date')
            returns_df['rolling_sharpe'] = returns_df['return'].rolling(63).apply(
                lambda x: (x.mean() / x.std() * (252**0.5)) if x.std() > 0 else 0
            )
            returns_df['rolling_return'] = returns_df['return'].rolling(63).mean() * 252 * 100
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(
                go.Scatter(x=returns_df['date'], y=returns_df['rolling_sharpe'], name="Rolling Sharpe (63d)", line=dict(color='#00d4ff', width=2)),
                secondary_y=False
            )
            fig.add_trace(
                go.Scatter(x=returns_df['date'], y=returns_df['rolling_return'], name="Rolling Return % (63d)", line=dict(color='#10b981', width=2)),
                secondary_y=True
            )
            fig.update_xaxes(title_text="Date", showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)')
            fig.update_yaxes(title_text="Sharpe Ratio", secondary_y=False, showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)')
            fig.update_yaxes(title_text="Annualized Return %", secondary_y=True, showgrid=False)
            layout = CHART_LAYOUT.copy()
            layout.update({
                'height': 450,
                'legend': dict(
                    bgcolor='rgba(0, 0, 0, 0.3)',
                    bordercolor='rgba(255, 255, 255, 0.1)',
                    font=dict(color='#ffffff')
                )
            })
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
        
        # Detailed Stats
        with st.expander("📋 Detailed Statistics"):
            st.json({k: v for k, v in stats.items() if k not in ['equity_curve', 'drawdown_series', 'returns', 'weights']})
else:
    st.info("👈 Select a signal from the dropdown above to run backtest analysis.")
