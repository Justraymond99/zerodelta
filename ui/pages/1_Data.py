from __future__ import annotations

import os
import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine, text

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
        📊 Market Data
    </h1>
    <p style="color: #94a3b8; font-size: 14px; margin: 8px 0 0 0;">
        Explore historical price data and volumes
    </p>
</div>
""", unsafe_allow_html=True)

settings = get_settings()
engine = create_engine(f"duckdb:///{settings.duckdb_path}?read_only=TRUE")

# Default popular tickers if database is empty
POPULAR_TICKERS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'NFLX', 
    'AMD', 'INTC', 'AVGO', 'QCOM', 'CRM', 'ORCL', 'ADBE', 'PYPL',
    'SPY', 'QQQ', 'DIA', 'IWM', 'VTI', 'VOO', 'VEA', 'VWO',
    'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'XOM', 'CVX',
    'JNJ', 'PG', 'KO', 'PEP', 'WMT', 'HD', 'MCD', 'NKE',
    'DIS', 'VZ', 'T', 'CMCSA', 'NFLX', 'AMZN', 'GOOGL', 'META'
]

try:
    symbols = pd.read_sql(text("SELECT DISTINCT symbol FROM prices ORDER BY symbol"), engine)['symbol'].tolist()
    
    # If no symbols in DB, suggest popular ones
    if not symbols:
        st.info("💡 No data loaded yet. Click below to fetch popular tickers or manually add symbols.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 Fetch Popular Tickers", type="primary"):
                with st.spinner("Fetching data for popular tickers..."):
                    try:
                        from qs.data.ingest_prices import ingest_prices
                        count = ingest_prices(tickers=POPULAR_TICKERS, start='2018-01-01')
                        st.success(f"✅ Fetched data for {count} price records!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error fetching data: {e}")
        
        # Show popular tickers as suggestions
        st.markdown("**Popular tickers to fetch:**")
        popular_cols = st.columns(6)
        for i, ticker in enumerate(POPULAR_TICKERS[:24]):  # Show first 24
            with popular_cols[i % 6]:
                st.text(ticker)
        
        symbols = []  # Keep empty so UI shows suggestions
        default_symbols = []
    else:
        # Filter to show popular ones if available
        popular_available = [s for s in POPULAR_TICKERS if s in symbols]
        default_symbols = popular_available[:5] if popular_available else (symbols[:5] if len(symbols) >= 5 else symbols)
except Exception as e:
    st.warning(f"Database error: {e}")
    symbols = []
    default_symbols = []

col1, col2 = st.columns([3, 1])
with col1:
    if symbols:
        sel = st.multiselect(
            "Select Symbols", 
            symbols, 
            default=default_symbols if symbols else [],
            key="symbol_selector"
        )
    else:
        sel = []

if sel:
    placeholders = ",".join([f":sym{i}" for i in range(len(sel))])
    params = {f"sym{i}": s for i, s in enumerate(sel)}
    q = text(f"SELECT symbol, date, adj_close, volume FROM prices WHERE symbol IN ({placeholders}) ORDER BY date")
    df = pd.read_sql(q, engine, params=params)
    
    if not df.empty:
        pivot = df.pivot(index='date', columns='symbol', values='adj_close')
        
        st.markdown('<div class="section-header">📈 Price Chart</div>', unsafe_allow_html=True)
        
        try:
            fig = go.Figure()
            
            colors = ['#00d4ff', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4']
            for i, symbol in enumerate(pivot.columns):
                fig.add_trace(go.Scatter(
                    x=pivot.index,
                    y=pivot[symbol],
                    mode='lines',
                    name=symbol,
                    line=dict(color=colors[i % len(colors)], width=2.5),
                    hovertemplate=f'<b>{symbol}</b><br>Date: %{{x}}<br>Price: $%{{y:,.2f}}<extra></extra>'
                ))
            
            # Update layout using the shared layout template
            fig.update_layout(**CHART_LAYOUT)
            fig.update_layout(
                height=500,
                xaxis_title='Date',
                yaxis_title='Price ($)',
                legend=dict(
                    bgcolor='rgba(0, 0, 0, 0.3)',
                    bordercolor='rgba(255, 255, 255, 0.1)',
                    borderwidth=1,
                    font=dict(color='#ffffff')
                )
            )
            # Render the chart
            st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
        except Exception as e:
            st.error(f"Error rendering chart: {e}")
            st.exception(e)
        except Exception as e:
            st.error(f"Error rendering chart: {e}")
            st.exception(e)

        st.markdown('<div class="section-header">📋 Data Table</div>', unsafe_allow_html=True)
        st.dataframe(
            df.tail(500),
            use_container_width=True,
            hide_index=True,
            height=400
        )
else:
    st.info("👈 Select at least one symbol from the dropdown above to view data.")
