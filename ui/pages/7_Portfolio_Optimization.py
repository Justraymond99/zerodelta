from __future__ import annotations

import os
import sys
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine, text

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from qs.config import get_settings
from qs.portfolio import (
    mean_variance_optimize, risk_parity_optimize,
    min_variance_portfolio, efficient_frontier
)
from qs.db import get_engine

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_css import SHARED_CSS, CHART_LAYOUT, CHART_CONFIG

# Inject modern CSS
st.markdown(SHARED_CSS, unsafe_allow_html=True)

st.markdown("""
<div style="padding: 20px 0 30px 0;">
    <h1 style="font-size: 36px; font-weight: 800; background: linear-gradient(135deg, #00d4ff 0%, #0096ff 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin: 0;">
        📊 Portfolio Optimization
    </h1>
    <p style="color: #94a3b8; font-size: 14px; margin: 8px 0 0 0;">
        Mean-variance optimization, risk parity, efficient frontier, and minimum variance
    </p>
</div>
""", unsafe_allow_html=True)

settings = get_settings()
engine = get_engine()

# Get available symbols
try:
    with engine.begin() as conn:
        symbols = pd.read_sql(
            text("SELECT DISTINCT symbol FROM prices ORDER BY symbol"),
            conn
        )['symbol'].tolist()
except Exception:
    symbols = []
    st.warning("Database is busy; retry in a few seconds.")

if symbols:
    # Symbol selection
    selected_symbols = st.multiselect(
        "Select Symbols for Portfolio",
        symbols,
        default=symbols[:5] if len(symbols) >= 5 else symbols,
        key="opt_symbols"
    )
    
    if len(selected_symbols) >= 2:
        # Get historical returns
        try:
            with engine.begin() as conn:
                # Create proper placeholders for SQL IN clause
                placeholders = ','.join([f':sym{i}' for i in range(len(selected_symbols))])
                params = {f'sym{i}': s for i, s in enumerate(selected_symbols)}
                
                prices_df = pd.read_sql(
                    text(f"""
                        SELECT symbol, date, adj_close
                        FROM prices
                        WHERE symbol IN ({placeholders})
                        AND date >= CURRENT_DATE - INTERVAL '252 days'
                        ORDER BY date
                    """),
                    conn,
                    params=params
                )
            
            if not prices_df.empty:
                # Pivot to get returns
                prices_pivot = prices_df.pivot(index='date', columns='symbol', values='adj_close')
                returns = prices_pivot.pct_change().dropna()
                
                if not returns.empty:
                    # Optimization method selection
                    method = st.selectbox(
                        "Optimization Method",
                        ["Max Sharpe Ratio", "Min Volatility", "Risk Parity", "Efficient Frontier"],
                        key="opt_method"
                    )
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        risk_free_rate = st.number_input("Risk-Free Rate (%)", value=5.0, min_value=0.0, step=0.1, format="%.2f") / 100.0
                    
                    with col2:
                        if method == "Min Volatility":
                            target_return = st.number_input("Target Return (%) (optional)", value=None, min_value=0.0, step=0.1, format="%.2f")
                            target_return = target_return / 100.0 if target_return else None
                    
                    if st.button("Optimize Portfolio", type="primary"):
                        with st.spinner("Optimizing portfolio..."):
                            if method == "Max Sharpe Ratio":
                                weights = mean_variance_optimize(
                                    returns, risk_free_rate=risk_free_rate, method="max_sharpe"
                                )
                            elif method == "Min Volatility":
                                weights = mean_variance_optimize(
                                    returns, target_return=target_return, risk_free_rate=risk_free_rate, method="min_vol"
                                )
                            elif method == "Risk Parity":
                                weights = risk_parity_optimize(returns)
                            else:  # Efficient Frontier
                                frontier_points = efficient_frontier(returns, risk_free_rate=risk_free_rate, n_points=50)
                                
                                # Plot efficient frontier
                                st.markdown('<div class="section-header">📈 Efficient Frontier</div>', unsafe_allow_html=True)
                                fig = go.Figure()
                                
                                # Efficient frontier
                                fig.add_trace(go.Scatter(
                                    x=frontier_points['volatility'],
                                    y=frontier_points['return'],
                                    mode='lines',
                                    name='Efficient Frontier',
                                    line=dict(color='#00d4ff', width=3)
                                ))
                                
                                # Markers for different portfolios
                                for method_name, color in [("Max Sharpe", "#10b981"), ("Min Vol", "#f59e0b")]:
                                    if method_name == "Max Sharpe":
                                        w = mean_variance_optimize(returns, risk_free_rate=risk_free_rate, method="max_sharpe")
                                    else:
                                        w = min_variance_portfolio(returns)
                                    
                                    port_ret = (returns * w).sum(axis=1).mean() * 252
                                    port_vol = (returns * w).sum(axis=1).std() * np.sqrt(252)
                                    
                                    fig.add_trace(go.Scatter(
                                        x=[port_vol],
                                        y=[port_ret],
                                        mode='markers',
                                        name=method_name,
                                        marker=dict(size=12, color=color, symbol='star')
                                    ))
                                
                                layout = CHART_LAYOUT.copy()
                                layout.update({
                                    'height': 500,
                                    'xaxis': dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', showline=True, linecolor='rgba(255, 255, 255, 0.2)', title='Volatility'),
                                    'yaxis': dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', showline=True, linecolor='rgba(255, 255, 255, 0.2)', title='Expected Return'),
                                    'hovermode': 'closest',
                                    'legend': dict(bgcolor='rgba(0, 0, 0, 0.3)', bordercolor='rgba(255, 255, 255, 0.1)', font=dict(color='#ffffff'))
                                })
                                fig.update_layout(**layout)
                                st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
                                
                                # Show weights for max sharpe
                                weights = mean_variance_optimize(returns, risk_free_rate=risk_free_rate, method="max_sharpe")
                            
                            if method != "Efficient Frontier":
                                # Display weights
                                weights_df = pd.DataFrame({
                                    'Symbol': weights.index,
                                    'Weight (%)': (weights * 100).round(2)
                                }).sort_values('Weight (%)', ascending=False)
                                
                                st.markdown('<div class="section-header">📊 Optimal Portfolio Weights</div>', unsafe_allow_html=True)
                                st.dataframe(weights_df, use_container_width=True, hide_index=True)
                                
                                # Portfolio metrics
                                portfolio_returns = (returns * weights).sum(axis=1)
                                portfolio_ret = portfolio_returns.mean() * 252
                                portfolio_vol = portfolio_returns.std() * np.sqrt(252)
                                sharpe = (portfolio_ret - risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0
                                
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Expected Return", f"{portfolio_ret*100:.2f}%")
                                with col2:
                                    st.metric("Volatility", f"{portfolio_vol*100:.2f}%")
                                with col3:
                                    st.metric("Sharpe Ratio", f"{sharpe:.2f}")
                                with col4:
                                    st.metric("Sum of Weights", f"{weights.sum()*100:.2f}%")
                                
                                # Visualization
                                fig = go.Figure()
                                fig.add_trace(go.Bar(
                                    x=weights_df['Symbol'],
                                    y=weights_df['Weight (%)'],
                                    marker=dict(color='#00d4ff'),
                                    hovertemplate='<b>%{x}</b><br>Weight: %{y:.2f}%<extra></extra>'
                                ))
                                layout = CHART_LAYOUT.copy()
                                layout.update({
                                    'height': 400,
                                    'xaxis': dict(showgrid=False, showline=True, linecolor='rgba(255, 255, 255, 0.2)'),
                                    'yaxis': dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', showline=True, linecolor='rgba(255, 255, 255, 0.2)', title='Weight (%)'),
                                    'hovermode': 'closest'
                                })
                                fig.update_layout(**layout)
                                st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
                else:
                    st.warning("Insufficient data to calculate returns.")
            else:
                st.warning("No price data found for selected symbols.")
        except Exception as e:
            st.error(f"Error optimizing portfolio: {e}")
    else:
        st.info("👈 Select at least 2 symbols to optimize a portfolio.")
else:
    st.info("👈 No symbols available. Load data first.")

