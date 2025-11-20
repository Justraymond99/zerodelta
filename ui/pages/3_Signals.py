from __future__ import annotations

import os
import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import text

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from qs.config import get_settings
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_css import SHARED_CSS, CHART_LAYOUT, CHART_CONFIG

# Inject modern CSS
st.markdown(SHARED_CSS, unsafe_allow_html=True)

st.markdown("""
<div style="padding: 20px 0 30px 0;">
    <h1 style="font-size: 36px; font-weight: 800; background: linear-gradient(135deg, #00d4ff 0%, #0096ff 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin: 0;">
        📡 Trading Signals
    </h1>
    <p style="color: #94a3b8; font-size: 14px; margin: 8px 0 0 0;">
        View model scores and signal rankings
    </p>
</div>
""", unsafe_allow_html=True)

from qs.db import get_engine
settings = get_settings()
engine = get_engine()

try:
    signals = pd.read_sql(text("SELECT DISTINCT signal_name FROM signals ORDER BY signal_name"), engine)['signal_name'].tolist()
except Exception:
    st.warning("Database is busy; retry in a few seconds while data is loading.")
    signals = []

signal_name = st.selectbox("Select Signal", signals, index=0 if signals else None)

if signal_name:
    dates = pd.read_sql(text("SELECT DISTINCT date FROM signals WHERE signal_name = :n ORDER BY date"), engine, params={"n": signal_name})
    if not dates.empty:
        asof = st.select_slider("As of Date", options=dates['date'].tolist(), value=dates['date'].iloc[-1])
        q = text("SELECT symbol, score FROM signals WHERE signal_name = :n AND date = :d")
        df = pd.read_sql(q, engine, params={"n": signal_name, "d": asof})
        df = df.sort_values('score', ascending=False).reset_index(drop=True)
        
        # Top metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Symbols", len(df))
        with col2:
            st.metric("Top Score", f"{df['score'].max():.4f}")
        with col3:
            st.metric("Avg Score", f"{df['score'].mean():.4f}")
        
        st.markdown('<div class="section-header">📊 Top 30 Signal Scores</div>', unsafe_allow_html=True)
        top30 = df.head(30)
        
        fig = go.Figure()
        colors = ['#10b981' if x > 0 else '#ef4444' for x in top30['score']]
        fig.add_trace(go.Bar(
            x=top30['symbol'],
            y=top30['score'],
            marker=dict(color=colors),
            hovertemplate='<b>%{x}</b><br>Score: %{y:,.4f}<extra></extra>'
        ))
        
        layout = CHART_LAYOUT.copy()
        layout.update({
            'height': 450,
            'margin': dict(l=20, r=20, t=60, b=80),
            'hovermode': 'closest',
            'xaxis': dict(showgrid=False, showline=True, linecolor='rgba(255, 255, 255, 0.2)'),
            'title': dict(text=f"Signal Scores on {asof}", font=dict(color='#ffffff', size=18))
        })
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
        
        st.markdown('<div class="section-header">📋 Full Signal Data</div>', unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True, hide_index=True, height=400)
    else:
        st.warning(f"No dates found for signal {signal_name}")
else:
    st.info("👈 Select a signal from the dropdown above to view rankings.")
