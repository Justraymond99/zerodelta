from __future__ import annotations

import os
import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import text
from datetime import datetime, timedelta
import time

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from qs.config import get_settings
from qs.backtest import backtest_signal
from qs.risk import value_at_risk, conditional_var
from qs.data.validation import validate_database
import numpy as np
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_css import SHARED_CSS, CHART_LAYOUT, CHART_CONFIG

# Inject modern CSS
st.markdown(SHARED_CSS, unsafe_allow_html=True)

st.markdown("""
<div style="padding: 20px 0 30px 0;">
    <h1 style="font-size: 36px; font-weight: 800; background: linear-gradient(135deg, #00d4ff 0%, #0096ff 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin: 0;">
        🔍 Real-Time Monitoring
    </h1>
    <p style="color: #94a3b8; font-size: 14px; margin: 8px 0 0 0;">
        Live portfolio status, risk metrics, and system health
    </p>
</div>
""", unsafe_allow_html=True)

from qs.db import get_engine
engine = get_engine()

# Auto-refresh
with st.sidebar:
    st.markdown("### ⚙️ Controls")
    auto_refresh = st.checkbox("Auto-refresh", value=False)
    refresh_interval = st.slider("Refresh interval (seconds)", 5, 60, 30, 5)

if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()

# Portfolio Status
st.markdown('<div class="section-header">💼 Portfolio Status</div>', unsafe_allow_html=True)
try:
    with engine.begin() as conn:
        latest_signals = pd.read_sql(
            text("""
                SELECT s.symbol, s.score, p.adj_close as price
                FROM signals s
                JOIN prices p ON s.symbol = p.symbol AND s.date = p.date
                WHERE s.signal_name = 'xgb_alpha'
                AND s.date = (SELECT MAX(date) FROM signals WHERE signal_name = 'xgb_alpha')
                ORDER BY s.score DESC
                LIMIT 10
            """),
            conn
        )
    
    if not latest_signals.empty:
        st.dataframe(latest_signals, use_container_width=True, hide_index=True)
        
        st.markdown('<div class="section-header">📊 Top 5 Positions</div>', unsafe_allow_html=True)
        fig = go.Figure()
        top5 = latest_signals.head(5)
        colors = ['#10b981' if x > 0 else '#ef4444' for x in top5['score']]
        fig.add_trace(go.Bar(
            x=top5['symbol'],
            y=top5['score'],
            marker=dict(color=colors),
            hovertemplate='<b>%{x}</b><br>Score: %{y:,.4f}<br>Price: $%{text}<extra></extra>',
            text=top5['price'].apply(lambda x: f'{x:.2f}')
        ))
        
        layout = CHART_LAYOUT.copy()
        layout.update({
            'height': 400,
            'xaxis': dict(showgrid=False, showline=True, linecolor='rgba(255, 255, 255, 0.2)'),
            'yaxis': dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', showline=True, linecolor='rgba(255, 255, 255, 0.2)', title='Signal Score'),
            'hovermode': 'closest'
        })
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
    else:
        st.info("No current positions found.")
except Exception as e:
    st.error(f"Error loading positions: {e}")

# Risk Metrics
st.markdown('<div class="section-header">⚠️ Risk Metrics</div>', unsafe_allow_html=True)
try:
    with engine.begin() as conn:
        recent_prices = pd.read_sql(
            text("""
                SELECT symbol, date, adj_close
                FROM prices
                WHERE date >= CURRENT_DATE - INTERVAL '30 days'
                ORDER BY date DESC
            """),
            conn
        )
    
    if not recent_prices.empty:
        prices_pivot = recent_prices.pivot(index='date', columns='symbol', values='adj_close')
        returns = prices_pivot.pct_change().dropna()
        
        if len(returns.columns) > 0:
            port_returns = returns.mean(axis=1)
            
            var_95 = value_at_risk(port_returns, confidence_level=0.95)
            cvar_95 = conditional_var(port_returns, confidence_level=0.95)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("95% VaR (1-day)", f"{var_95*100:.2f}%", help="Value at Risk at 95% confidence")
            with col2:
                st.metric("95% CVaR (1-day)", f"{cvar_95*100:.2f}%", help="Conditional Value at Risk")
            with col3:
                st.metric("Current Volatility", f"{port_returns.std()*np.sqrt(252)*100:.2f}%", help="Annualized volatility")
            
            st.markdown('<div class="section-header">📈 Recent Portfolio Returns</div>', unsafe_allow_html=True)
            returns_df = pd.DataFrame({
                'date': returns.index,
                'return': port_returns.values * 100
            })
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=returns_df['date'],
                y=returns_df['return'],
                mode='lines',
                name='Portfolio Returns',
                line=dict(color='#00d4ff', width=2),
                fill='tozeroy',
                fillcolor='rgba(0, 212, 255, 0.1)'
            ))
            
            layout = CHART_LAYOUT.copy()
            layout.update({
                'height': 350,
                'yaxis': dict(
                    showgrid=True,
                    gridcolor='rgba(255, 255, 255, 0.1)',
                    showline=True,
                    linecolor='rgba(255, 255, 255, 0.2)',
                    title='Return (%)'
                )
            })
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
except Exception as e:
    st.warning(f"Could not calculate risk metrics: {e}")

# Data Quality
st.markdown('<div class="section-header">🔍 Data Quality Check</div>', unsafe_allow_html=True)
if st.button("Run Validation", type="primary"):
    with st.spinner("Validating database..."):
        validation_results = validate_database()
    
    for category, results in validation_results.items():
        if isinstance(results, dict):
            with st.expander(f"✅ {category.title()} Validation"):
                if results.get('errors'):
                    st.error("❌ Errors:")
                    for error in results['errors']:
                        st.write(f"- {error}")
                if results.get('warnings'):
                    st.warning("⚠️ Warnings:")
                    for warning in results['warnings']:
                        st.write(f"- {warning}")
                if not results.get('errors') and not results.get('warnings'):
                    st.success("✅ No issues found!")

# System Health
st.markdown('<div class="section-header">💚 System Health</div>', unsafe_allow_html=True)
try:
    with engine.begin() as conn:
        latest_date = pd.read_sql(text("SELECT MAX(date) as latest FROM prices"), conn)['latest'].iloc[0]
        num_symbols = pd.read_sql(text("SELECT COUNT(DISTINCT symbol) as cnt FROM prices"), conn)['cnt'].iloc[0]
        num_signals = pd.read_sql(text("SELECT COUNT(*) as cnt FROM signals"), conn)['cnt'].iloc[0]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Latest Data Date", str(latest_date))
    with col2:
        st.metric("Symbols Tracked", num_symbols)
    with col3:
        st.metric("Total Signals", num_signals)
except Exception as e:
    st.error(f"Error checking system health: {e}")
