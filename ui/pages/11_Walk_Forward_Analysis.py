from __future__ import annotations

import os
import sys
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine, text

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from qs.config import get_settings
from qs.db import get_engine
from qs.walkforward import walk_forward_analysis

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_css import SHARED_CSS, CHART_LAYOUT, CHART_CONFIG

# Inject modern CSS
st.markdown(SHARED_CSS, unsafe_allow_html=True)

st.markdown("""
<div style="padding: 20px 0 30px 0;">
    <h1 style="font-size: 36px; font-weight: 800; background: linear-gradient(135deg, #00d4ff 0%, #0096ff 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin: 0;">
        🔄 Walk-Forward Analysis
    </h1>
    <p style="color: #94a3b8; font-size: 14px; margin: 8px 0 0 0;">
        Rolling window analysis with training and testing periods
    </p>
</div>
""", unsafe_allow_html=True)

settings = get_settings()
engine = get_engine()

# Get available signals
try:
    with engine.begin() as conn:
        signals = pd.read_sql(
            text("SELECT DISTINCT signal_name FROM signals ORDER BY signal_name"),
            conn
        )['signal_name'].tolist()
except Exception:
    signals = []
    st.warning("Database is busy; retry in a few seconds.")

if signals:
    # Parameters
    col1, col2 = st.columns(2)
    with col1:
        signal_name = st.selectbox("Signal", signals, index=0 if signals else None)
    with col2:
        top_n = st.number_input("Top N Stocks", value=5, min_value=1, max_value=20, step=1)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        train_period = st.number_input("Training Period (days)", value=252, min_value=30, max_value=1000, step=21)
    with col2:
        test_period = st.number_input("Test Period (days)", value=63, min_value=7, max_value=252, step=7)
    with col3:
        step_size = st.number_input("Step Size (days)", value=21, min_value=1, max_value=63, step=7)
    with col4:
        fee = st.number_input("Transaction Fee (%)", value=0.05, min_value=0.0, max_value=1.0, step=0.01, format="%.3f") / 100.0
    
    if st.button("Run Walk-Forward Analysis", type="primary"):
        with st.spinner(f"Running walk-forward analysis (this may take a while)..."):
            try:
                results_df = walk_forward_analysis(
                    signal_name=signal_name,
                    train_period=train_period,
                    test_period=test_period,
                    step_size=step_size,
                    top_n=top_n,
                    fee=fee
                )
                
                if not results_df.empty:
                    st.markdown('<div class="section-header">📊 Walk-Forward Results</div>', unsafe_allow_html=True)
                    
                    # Summary metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        avg_return = results_df['return'].mean() * 100 if 'return' in results_df.columns else 0
                        st.metric("Avg Test Return", f"{avg_return:.2f}%")
                    with col2:
                        avg_sharpe = results_df['sharpe'].mean() if 'sharpe' in results_df.columns else 0
                        st.metric("Avg Sharpe Ratio", f"{avg_sharpe:.2f}")
                    with col3:
                        avg_drawdown = results_df['max_drawdown'].mean() * 100 if 'max_drawdown' in results_df.columns else 0
                        st.metric("Avg Max Drawdown", f"{avg_drawdown:.2f}%")
                    with col4:
                        win_rate = (results_df['return'] > 0).mean() * 100 if 'return' in results_df.columns else 0
                        st.metric("Win Rate", f"{win_rate:.1f}%")
                    
                    # Display results table
                    st.dataframe(results_df, use_container_width=True, hide_index=True, height=400)
                    
                    # Visualization - Returns over time
                    if 'test_end' in results_df.columns and 'return' in results_df.columns:
                        st.markdown('<div class="section-header">📈 Test Period Returns Over Time</div>', unsafe_allow_html=True)
                        fig = go.Figure()
                        colors = ['#10b981' if x >= 0 else '#ef4444' for x in results_df['return']]
                        fig.add_trace(go.Bar(
                            x=results_df['test_end'].astype(str),
                            y=results_df['return'] * 100,
                            marker=dict(color=colors),
                            hovertemplate='<b>%{x}</b><br>Return: %{y:.2f}%<br>Sharpe: %{text:.2f}<extra></extra>',
                            text=results_df.get('sharpe', 0)
                        ))
                        
                        layout = CHART_LAYOUT.copy()
                        layout.update({
                            'height': 400,
                            'margin': dict(l=20, r=20, t=60, b=80),
                            'xaxis': dict(showgrid=False, showline=True, linecolor='rgba(255, 255, 255, 0.2)', title='Test End Date'),
                            'yaxis': dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', showline=True, linecolor='rgba(255, 255, 255, 0.2)', title='Return (%)'),
                            'hovermode': 'closest'
                        })
                        fig.update_layout(**layout)
                        st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
                    
                    # Visualization - Cumulative performance
                    if 'return' in results_df.columns:
                        st.markdown('<div class="section-header">📊 Cumulative Performance</div>', unsafe_allow_html=True)
                        cumulative = (1 + results_df['return']).cumprod()
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=results_df.index,
                            y=(cumulative - 1) * 100,
                            mode='lines',
                            name='Cumulative Return',
                            line=dict(color='#00d4ff', width=3),
                            fill='tozeroy',
                            fillcolor='rgba(0, 212, 255, 0.1)'
                        ))
                        
                        layout = CHART_LAYOUT.copy()
                        layout.update({
                            'height': 400,
                            'xaxis': dict(
                                showgrid=True,
                                gridcolor='rgba(255, 255, 255, 0.1)',
                                showline=True,
                                linecolor='rgba(255, 255, 255, 0.2)',
                                title='Period'
                            ),
                            'yaxis': dict(
                                showgrid=True,
                                gridcolor='rgba(255, 255, 255, 0.1)',
                                showline=True,
                                linecolor='rgba(255, 255, 255, 0.2)',
                                title='Cumulative Return (%)'
                            )
                        })
                        fig.update_layout(**layout)
                        st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
                    
                    # Statistical summary
                    with st.expander("📋 Statistical Summary"):
                        if 'return' in results_df.columns:
                            st.write("**Return Statistics:**")
                            st.write(results_df['return'].describe())
                        if 'sharpe' in results_df.columns:
                            st.write("**Sharpe Ratio Statistics:**")
                            st.write(results_df['sharpe'].describe())
                else:
                    st.warning("No results returned. Check your parameters and data availability.")
            except Exception as e:
                st.error(f"Error running walk-forward analysis: {e}")
                st.exception(e)
else:
    st.info("👈 No signals found. Generate signals first before running walk-forward analysis.")

