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
        🔬 Feature Analysis
    </h1>
    <p style="color: #94a3b8; font-size: 14px; margin: 8px 0 0 0;">
        Explore engineered features and technical indicators
    </p>
</div>
""", unsafe_allow_html=True)

from qs.db import get_engine
settings = get_settings()
engine = get_engine()

try:
    symbols = pd.read_sql(text("SELECT DISTINCT symbol FROM features ORDER BY symbol"), engine)['symbol'].tolist()
    features = pd.read_sql(text("SELECT DISTINCT feature FROM features ORDER BY feature"), engine)['feature'].tolist()
except Exception:
    st.warning("Database is busy; retry in a few seconds while data is loading.")
    symbols, features = [], []

col1, col2 = st.columns(2)
with col1:
    sym = st.selectbox("Symbol", symbols, index=0 if symbols else None, key="feat_symbol")
with col2:
    feat = st.selectbox("Feature", features, index=0 if features else None, key="feat_name")

if sym and feat:
    q = text("SELECT date, value FROM features WHERE symbol = :s AND feature = :f ORDER BY date")
    df = pd.read_sql(q, engine, params={"s": sym, "f": feat})
    
    if not df.empty:
        st.markdown('<div class="section-header">📈 Feature Time Series</div>', unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['value'],
            mode='lines',
            name=feat,
            line=dict(color='#00d4ff', width=2.5),
            fill='tozeroy',
            fillcolor='rgba(0, 212, 255, 0.1)',
            hovertemplate=f'<b>{feat}</b><br>Date: %{{x}}<br>Value: %{{y:,.4f}}<extra></extra>'
        ))
        
        layout = CHART_LAYOUT.copy()
        layout.update({
            'height': 450,
            'title': dict(text=f"{feat} - {sym}", font=dict(color='#ffffff', size=18))
        })
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
        
        st.markdown('<div class="section-header">📋 Feature Data</div>', unsafe_allow_html=True)
        st.dataframe(df.tail(500), use_container_width=True, hide_index=True, height=350)
    else:
        st.warning(f"No data found for {feat} - {sym}")
else:
    st.info("👈 Select a symbol and feature from the dropdowns above to view feature data.")
