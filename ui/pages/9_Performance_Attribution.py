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
from qs.attribution.enhanced import get_attribution_analyzer

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_css import SHARED_CSS, CHART_LAYOUT, CHART_CONFIG

# Inject modern CSS
st.markdown(SHARED_CSS, unsafe_allow_html=True)

st.markdown("""
<div style="padding: 20px 0 30px 0;">
    <h1 style="font-size: 36px; font-weight: 800; background: linear-gradient(135deg, #00d4ff 0%, #0096ff 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin: 0;">
        📊 Performance Attribution
    </h1>
    <p style="color: #94a3b8; font-size: 14px; margin: 8px 0 0 0;">
        Symbol-level, strategy-level, and factor-based performance attribution
    </p>
</div>
""", unsafe_allow_html=True)

settings = get_settings()
engine = get_engine()
attribution_analyzer = get_attribution_analyzer()

# Date range selection
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=365))
with col2:
    end_date = st.date_input("End Date", value=datetime.now())

start_str = start_date.strftime("%Y-%m-%d")
end_str = end_date.strftime("%Y-%m-%d")

# Attribution type selection
attribution_type = st.selectbox(
    "Attribution Type",
    ["Symbol-Level", "Strategy-Level", "Factor-Based", "Time Period"],
    key="attr_type"
)

if st.button("Run Attribution Analysis", type="primary"):
    with st.spinner("Calculating attribution..."):
        try:
            if attribution_type == "Symbol-Level":
                st.markdown('<div class="section-header">📈 Symbol-Level Attribution</div>', unsafe_allow_html=True)
                result_df = attribution_analyzer.symbol_level_attribution(start_str, end_str)
                
                if not result_df.empty:
                    st.dataframe(result_df, use_container_width=True, hide_index=True)
                    
                    # Visualization
                    top_symbols = result_df.nlargest(10, 'pnl')
                    fig = go.Figure()
                    colors = ['#10b981' if x >= 0 else '#ef4444' for x in top_symbols['pnl']]
                    fig.add_trace(go.Bar(
                        x=top_symbols['symbol'],
                        y=top_symbols['pnl'],
                        marker=dict(color=colors),
                        hovertemplate='<b>%{x}</b><br>P&L: $%{y:,.2f}<extra></extra>'
                    ))
                    
                    layout = CHART_LAYOUT.copy()
                    layout.update({
                        'height': 400,
                        'xaxis': dict(showgrid=False, showline=True, linecolor='rgba(255, 255, 255, 0.2)'),
                        'yaxis': dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', showline=True, linecolor='rgba(255, 255, 255, 0.2)', title='P&L ($)'),
                        'hovermode': 'closest',
                        'title': 'Top 10 Contributors by P&L',
                        'titlefont': dict(color='#ffffff', size=18)
                    })
                    fig.update_layout(**layout)
                    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
                else:
                    st.warning("No trade data found for the selected period.")
            
            elif attribution_type == "Strategy-Level":
                st.markdown('<div class="section-header">🎯 Strategy-Level Attribution</div>', unsafe_allow_html=True)
                result_df = attribution_analyzer.strategy_level_attribution(start_str, end_str)
                
                if not result_df.empty:
                    st.dataframe(result_df, use_container_width=True, hide_index=True)
                    
                    # Visualization
                    fig = go.Figure()
                    colors = ['#10b981' if x >= 0 else '#ef4444' for x in result_df['pnl']]
                    fig.add_trace(go.Bar(
                        x=result_df['strategy'],
                        y=result_df['pnl'],
                        marker=dict(color=colors),
                        hovertemplate='<b>%{x}</b><br>P&L: $%{y:,.2f}<br>Return: %{text:.2f}%<extra></extra>',
                        text=result_df['return'] * 100
                    ))
                    
                    layout = CHART_LAYOUT.copy()
                    layout.update({
                        'height': 400,
                        'xaxis': dict(showgrid=False, showline=True, linecolor='rgba(255, 255, 255, 0.2)'),
                        'yaxis': dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', showline=True, linecolor='rgba(255, 255, 255, 0.2)', title='P&L ($)'),
                        'hovermode': 'closest'
                    })
                    fig.update_layout(**layout)
                    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
                else:
                    st.warning("No strategy data found for the selected period.")
            
            elif attribution_type == "Factor-Based":
                st.markdown('<div class="section-header">🔬 Factor-Based Attribution</div>', unsafe_allow_html=True)
                result_dict = attribution_analyzer.factor_attribution(start_str, end_str)
                
                if result_dict:
                    factor_df = pd.DataFrame([
                        {
                            'factor': factor,
                            'contribution': info.get('contribution', 0),
                            'feature_count': info.get('feature_count', 0)
                        }
                        for factor, info in result_dict.items()
                    ])
                    
                    st.dataframe(factor_df, use_container_width=True, hide_index=True)
                    
                    # Visualization
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=factor_df['factor'],
                        y=factor_df['contribution'],
                        marker=dict(color='#00d4ff'),
                        hovertemplate='<b>%{x}</b><br>Contribution: %{y:.4f}<extra></extra>'
                    ))
                    
                    layout = CHART_LAYOUT.copy()
                    layout.update({
                        'height': 400,
                        'xaxis': dict(showgrid=False, showline=True, linecolor='rgba(255, 255, 255, 0.2)'),
                        'yaxis': dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', showline=True, linecolor='rgba(255, 255, 255, 0.2)', title='Contribution'),
                        'hovermode': 'closest'
                    })
                    fig.update_layout(**layout)
                    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
                else:
                    st.warning("No factor data available.")
            
            else:  # Time Period
                period_type = st.selectbox("Period", ["monthly", "weekly", "daily"], key="period_type")
                result_df = attribution_analyzer.time_period_attribution(start_str, end_str, period=period_type)
                
                if not result_df.empty:
                    st.markdown(f'<div class="section-header">📅 {period_type.title()} Attribution</div>', unsafe_allow_html=True)
                    st.dataframe(result_df, use_container_width=True, hide_index=True)
                    
                    # Visualization
                    fig = go.Figure()
                    colors = ['#10b981' if x >= 0 else '#ef4444' for x in result_df['pnl']]
                    fig.add_trace(go.Bar(
                        x=result_df['period'].astype(str),
                        y=result_df['pnl'],
                        marker=dict(color=colors),
                        hovertemplate='<b>%{x}</b><br>P&L: $%{y:,.2f}<br>Trades: %{text}<extra></extra>',
                        text=result_df['num_trades']
                    ))
                    
                    layout = CHART_LAYOUT.copy()
                    layout.update({
                        'height': 400,
                        'xaxis': dict(showgrid=False, showline=True, linecolor='rgba(255, 255, 255, 0.2)', title='Period'),
                        'yaxis': dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', showline=True, linecolor='rgba(255, 255, 255, 0.2)', title='P&L ($)'),
                        'hovermode': 'closest'
                    })
                    fig.update_layout(**layout)
                    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
                else:
                    st.warning("No time period data found.")
        except Exception as e:
            st.error(f"Error calculating attribution: {e}")

else:
    st.info("👈 Select a date range and attribution type, then click 'Run Attribution Analysis'")

