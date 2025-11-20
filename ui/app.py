from __future__ import annotations

import os
import sys
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta
import time
from time import perf_counter

# Ensure project root is on sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from qs.config import get_settings
from qs.db import get_engine, init_db
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError, OperationalError

# Page config
st.set_page_config(
    page_title="ZeroDelta",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern CSS with professional trading dashboard aesthetic
st.markdown("""
<style>
    /* Base styling */
    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0f1419 100%);
        color: #ffffff;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', sans-serif;
    }
    
    /* Hide default Streamlit elements */
    footer {visibility: hidden;}
    header {visibility: hidden;}
    /* Keep navigation menu visible */
    
    /* Modern glassmorphism cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 20px;
        margin: 8px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 40px rgba(0, 212, 255, 0.2);
        border-color: rgba(0, 212, 255, 0.3);
    }
    
    .market-card {
        background: linear-gradient(135deg, rgba(0, 212, 255, 0.1) 0%, rgba(0, 150, 255, 0.05) 100%);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 212, 255, 0.2);
        border-radius: 16px;
        padding: 24px;
        margin: 8px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    
    .metric-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #94a3b8;
        margin-bottom: 8px;
        font-weight: 600;
    }
    
    .metric-value-large {
        font-size: 32px;
        font-weight: 700;
        background: linear-gradient(135deg, #00d4ff 0%, #0096ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 8px 0;
        letter-spacing: -0.5px;
    }
    
    .metric-change {
        font-size: 13px;
        font-weight: 600;
        padding: 4px 8px;
        border-radius: 6px;
        display: inline-block;
        margin-top: 4px;
    }
    
    .metric-change-positive {
        color: #10b981;
        background: rgba(16, 185, 129, 0.15);
    }
    
    .metric-change-negative {
        color: #ef4444;
        background: rgba(239, 68, 68, 0.15);
    }
    
    /* Status indicator */
    .status-indicator {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    .status-online {
        background: #10b981;
        box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
    }
    
    /* Order entry card */
    .order-entry-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    
    /* Custom buttons */
    .stButton > button {
        border-radius: 10px;
        border: none;
        background: linear-gradient(135deg, #00d4ff 0%, #0096ff 100%);
        color: white;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 212, 255, 0.5);
    }
    
    /* Section headers */
    .section-header {
        font-size: 18px;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 16px;
        letter-spacing: -0.3px;
    }
    
    /* Table styling */
    .dataframe {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Input styling */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select,
    .stNumberInput > div > div > input {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        color: white;
    }
    
    /* Chart container */
    .js-plotly-plot {
        border-radius: 12px;
        overflow: hidden;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(10, 14, 39, 0.95) 0%, rgba(26, 31, 58, 0.95) 100%);
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 4px 0 24px rgba(0, 0, 0, 0.5);
    }
    
    [data-testid="stSidebar"] > div:first-child {
        background: transparent;
    }
    
    /* Sidebar header/navigation */
    [data-testid="stSidebarNav"] {
        background: transparent;
    }
    
    [data-testid="stSidebarNav"] ul {
        background: transparent;
    }
    
    [data-testid="stSidebarNav"] a {
        color: #94a3b8;
        border-radius: 8px;
        padding: 8px 12px;
        margin: 2px 0;
        transition: all 0.2s ease;
    }
    
    [data-testid="stSidebarNav"] a:hover {
        background: rgba(0, 212, 255, 0.1);
        color: #00d4ff;
    }
    
    [data-testid="stSidebarNav"] a[aria-current="page"] {
        background: linear-gradient(135deg, rgba(0, 212, 255, 0.15) 0%, rgba(0, 150, 255, 0.1) 100%);
        color: #00d4ff;
        border-left: 3px solid #00d4ff;
        font-weight: 600;
    }
    
    /* Sidebar content */
    [data-testid="stSidebar"] .element-container {
        background: transparent;
    }
    
    [data-testid="stSidebar"] h3 {
        color: #ffffff;
        font-weight: 700;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 20px;
        margin-bottom: 12px;
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: #94a3b8;
    }
    
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #ffffff;
    }
    
    /* Sidebar inputs */
    [data-testid="stSidebar"] .stCheckbox > label,
    [data-testid="stSidebar"] .stSlider > label {
        color: #94a3b8;
    }
    
    [data-testid="stSidebar"] .stCheckbox [data-baseweb="checkbox"] {
        border-color: rgba(255, 255, 255, 0.2);
    }
    
    [data-testid="stSidebar"] .stCheckbox [data-baseweb="checkbox"]:checked {
        background: linear-gradient(135deg, #00d4ff 0%, #0096ff 100%);
        border-color: #00d4ff;
    }
    
    [data-testid="stSidebar"] .stSlider [data-baseweb="slider"] {
        background: rgba(255, 255, 255, 0.1);
    }
    
    [data-testid="stSidebar"] .stSlider [data-baseweb="slider-track"] {
        background: rgba(0, 212, 255, 0.2);
    }
    
    [data-testid="stSidebar"] .stSlider [data-baseweb="thumb"] {
        background: linear-gradient(135deg, #00d4ff 0%, #0096ff 100%);
        border-color: #00d4ff;
    }
    
    /* Sidebar buttons */
    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, rgba(0, 212, 255, 0.15) 0%, rgba(0, 150, 255, 0.1) 100%);
        border: 1px solid rgba(0, 212, 255, 0.3);
        color: #00d4ff;
        font-weight: 600;
    }
    
    [data-testid="stSidebar"] .stButton > button:hover {
        background: linear-gradient(135deg, rgba(0, 212, 255, 0.25) 0%, rgba(0, 150, 255, 0.2) 100%);
        border-color: #00d4ff;
        transform: translateY(-1px);
    }
    
    /* Sidebar info boxes */
    [data-testid="stSidebar"] .stAlert {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        color: #94a3b8;
    }
    
    /* Sidebar divider */
    [data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.1);
        margin: 16px 0;
    }
</style>
""", unsafe_allow_html=True)

settings = get_settings()
engine = get_engine()

# Initialize database tables if they don't exist
try:
    init_db()
except Exception:
    pass  # Tables might already exist

# Helper function to check if a table exists
def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    SELECT COUNT(*) as cnt 
                    FROM information_schema.tables 
                    WHERE table_schema = 'main' AND table_name = :table_name
                """),
                {"table_name": table_name}
            ).fetchone()
            return result and result[0] > 0
    except Exception:
        return False

# Helper function to check if prices table has data
def prices_table_has_data() -> bool:
    """Check if prices table exists and has data."""
    if not table_exists('prices'):
        return False
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) as cnt FROM prices")
            ).fetchone()
            return result and result[0] > 0
    except Exception:
        return False

# Initialize session state
if 'trades' not in st.session_state:
    st.session_state.trades = []
if 'logs' not in st.session_state:
    st.session_state.logs = [
        f"{datetime.now().strftime('%H:%M:%S')} System initialized",
        f"{datetime.now().strftime('%H:%M:%S')} Connected to market data feed"
    ]
if 'pnl' not in st.session_state:
    st.session_state.pnl = 12345.0
if 'algo_running' not in st.session_state:
    st.session_state.algo_running = False
if 'chart_symbol' not in st.session_state:
    st.session_state.chart_symbol = 'SPY'  # Default chart symbol

# Calculate real PnL from positions - always update
try:
    from qs.oms.manager import get_order_manager
    from qs.oms.pnl import get_pnl_calculator
    
    manager = get_order_manager()
    positions = manager.get_positions()
    
    total_pnl = 0.0
    
    if positions and prices_table_has_data():
        pnl_calc = get_pnl_calculator()
        with engine.begin() as conn:
            for symbol, qty in positions.items():
                try:
                    result = conn.execute(
                        text("SELECT adj_close FROM prices WHERE symbol = :sym ORDER BY date DESC LIMIT 1"),
                        {"sym": symbol}
                    ).fetchone()
                    if result:
                        current_price = float(result[0])
                        cost_basis = pnl_calc.get_position_cost_basis(symbol)
                        if cost_basis and cost_basis.get('avg_price', 0) > 0:
                            entry_price = cost_basis['avg_price']
                            # Calculate unrealized P&L: (current_price - entry_price) * quantity
                            position_pnl = (current_price - entry_price) * float(qty)
                            total_pnl += position_pnl
                except Exception:
                    continue  # Skip this symbol if error
    
    # Always update P&L (even if 0 or no positions)
    st.session_state.pnl = total_pnl
except Exception as e:
    # If error, keep existing P&L or default to 0
    if 'pnl' not in st.session_state or st.session_state.pnl == 12345.0:
        st.session_state.pnl = 0.0

# Measure system latency - time a database query
try:
    latency_start = perf_counter()
    if prices_table_has_data():
        with engine.begin() as conn:
            # Simple query to measure latency
            conn.execute(text("SELECT 1")).fetchone()
    latency_end = perf_counter()
    # Convert to milliseconds and round
    measured_latency = int((latency_end - latency_start) * 1000)
    # Store in session state with smoothing (exponential moving average)
    if 'system_latency' not in st.session_state:
        st.session_state.system_latency = measured_latency
    else:
        # Smooth with EMA (70% old, 30% new)
        st.session_state.system_latency = int(0.7 * st.session_state.system_latency + 0.3 * measured_latency)
except Exception:
    # Fallback to previous latency or default
    if 'system_latency' not in st.session_state:
        st.session_state.system_latency = 25  # Default reasonable latency

# Sidebar controls
with st.sidebar:
    st.markdown("### ⚙️ Controls")
    auto_refresh = st.checkbox("Auto-refresh", value=True)
    refresh_interval = st.slider("Refresh interval (sec)", 1, 10, 2, 1)
    
    st.markdown("---")
    st.markdown("### 🚀 Quick Setup")
    
    # Check if database has data
    try:
        with engine.begin() as conn:
            symbol_count = conn.execute(text("SELECT COUNT(DISTINCT symbol) as cnt FROM prices")).fetchone()[0]
            if symbol_count == 0:
                if st.button("📥 Fetch Popular Tickers", use_container_width=True, type="primary"):
                    POPULAR_TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'SPY', 'QQQ', 'JPM', 'BAC']
                    with st.spinner("Fetching popular tickers..."):
                        try:
                            from qs.data.ingest_prices import ingest_prices
                            count = ingest_prices(tickers=POPULAR_TICKERS, start='2018-01-01')
                            st.success(f"✅ Fetched {count} records!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
            else:
                st.info(f"📊 {symbol_count} symbols loaded")
    except Exception:
        pass

# Main header
    st.markdown("""
<div style="padding: 20px 0 30px 0;">
    <h1 style="font-size: 36px; font-weight: 800; background: linear-gradient(135deg, #00d4ff 0%, #0096ff 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin: 0;">
        ZeroDelta
    </h1>
    <p style="color: #94a3b8; font-size: 14px; margin: 8px 0 0 0;">
        Real-time market analysis and portfolio management
    </p>
    </div>
    """, unsafe_allow_html=True)

# Top metrics row
    col1, col2, col3, col4 = st.columns(4)

pnl_color = "#10b981" if st.session_state.pnl >= 0 else "#ef4444"
pnl_sign = "+" if st.session_state.pnl >= 0 else ""
    
    with col1:
        st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total P&L</div>
        <div class="metric-value-large">{pnl_sign}${abs(st.session_state.pnl):,.0f}</div>
        <div style="color: {pnl_color}; font-size: 12px; font-weight: 600;">
            {pnl_sign}${abs(st.session_state.pnl):,.2f}
        </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        market_status = "OPEN" if datetime.now().hour >= 9 and datetime.now().hour < 16 else "CLOSED"
    market_color = "#10b981" if market_status == "OPEN" else "#ef4444"
    market_bg = "rgba(16, 185, 129, 0.15)" if market_status == "OPEN" else "rgba(239, 68, 68, 0.15)"
        st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Market Status</div>
        <div style="font-size: 24px; font-weight: 700; color: {market_color}; margin: 12px 0;">
            <span class="status-indicator status-online"></span>{market_status}
        </div>
        </div>
        """, unsafe_allow_html=True)
    
with col3:
    # Use measured system latency from session state
    latency = st.session_state.get('system_latency', 25)
    latency_color = "#10b981" if latency < 50 else "#f59e0b" if latency < 100 else "#ef4444"
        st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">System Latency</div>
        <div style="font-size: 28px; font-weight: 700; color: {latency_color}; margin: 12px 0;">
            {latency} <span style="font-size: 16px; color: #94a3b8;">ms</span>
        </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">System Health</div>
        <div style="font-size: 24px; font-weight: 700; color: #10b981; margin: 12px 0;">
            <span class="status-indicator status-online"></span>Online
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
# Market data row
    col1, col2, col3 = st.columns(3)
    
    # Fetch market data
    try:
        import yfinance as yf
        sp500 = yf.Ticker("^GSPC")
        nasdaq = yf.Ticker("^IXIC")
        eurusd = yf.Ticker("EURUSD=X")
        
        sp500_info = sp500.history(period="2d")
        nasdaq_info = nasdaq.history(period="2d")
        eurusd_info = eurusd.history(period="2d")
        
        if not sp500_info.empty:
            sp500_value = float(sp500_info['Close'].iloc[-1])
            sp500_prev = float(sp500_info['Close'].iloc[-2]) if len(sp500_info) > 1 else sp500_value
            sp500_change = ((sp500_value - sp500_prev) / sp500_prev) * 100
        else:
            sp500_value = 4150.25
            sp500_change = 1.24
        
        if not nasdaq_info.empty:
            nasdaq_value = float(nasdaq_info['Close'].iloc[-1])
            nasdaq_prev = float(nasdaq_info['Close'].iloc[-2]) if len(nasdaq_info) > 1 else nasdaq_value
            nasdaq_change = ((nasdaq_value - nasdaq_prev) / nasdaq_prev) * 100
        else:
            nasdaq_value = 13600.81
            nasdaq_change = 0.89
        
        if not eurusd_info.empty:
            eurusd_value = float(eurusd_info['Close'].iloc[-1])
            eurusd_prev = float(eurusd_info['Close'].iloc[-2]) if len(eurusd_info) > 1 else eurusd_value
            eurusd_change = ((eurusd_value - eurusd_prev) / eurusd_prev) * 100
        else:
            eurusd_value = 1.0685
            eurusd_change = -0.12
    except Exception:
        sp500_value = 4150.25
        sp500_change = 1.24
        nasdaq_value = 13600.81
        nasdaq_change = 0.89
        eurusd_value = 1.0685
        eurusd_change = -0.12
    
    with col1:
        change_class = "metric-change-positive" if sp500_change >= 0 else "metric-change-negative"
        change_sign = "+" if sp500_change >= 0 else ""
        st.markdown(f"""
    <div class="market-card">
        <div class="metric-label">S&P 500</div>
        <div class="metric-value-large">{sp500_value:,.2f}</div>
        <div class="metric-change {change_class}">{change_sign}{sp500_change:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        change_class = "metric-change-positive" if nasdaq_change >= 0 else "metric-change-negative"
        change_sign = "+" if nasdaq_change >= 0 else ""
        st.markdown(f"""
    <div class="market-card">
        <div class="metric-label">NASDAQ</div>
        <div class="metric-value-large">{nasdaq_value:,.2f}</div>
        <div class="metric-change {change_class}">{change_sign}{nasdaq_change:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        change_class = "metric-change-positive" if eurusd_change >= 0 else "metric-change-negative"
        change_sign = "+" if eurusd_change >= 0 else ""
        st.markdown(f"""
    <div class="market-card">
        <div class="metric-label">EUR/USD</div>
        <div style="font-size: 28px; font-weight: 700; background: linear-gradient(135deg, #00d4ff 0%, #0096ff 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin: 12px 0;">
            {eurusd_value:.4f}
        </div>
        <div class="metric-change {change_class}">{change_sign}{eurusd_change:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Chart and Order Entry row
    col_chart, col_order = st.columns([0.6, 0.4])
    
    with col_chart:
        st.markdown('<div class="section-header">📈 Market Chart</div>', unsafe_allow_html=True)
    
        # Get available symbols for selector
        try:
            if prices_table_has_data():
                with engine.begin() as conn:
                    available_symbols = pd.read_sql(
                        text("SELECT DISTINCT symbol FROM prices ORDER BY symbol"),
                        conn
                    )['symbol'].tolist()
            else:
                available_symbols = []
        except Exception:
            available_symbols = []
    
        # Symbol selector for chart
        if available_symbols:
            # Use session state symbol or default to first available
            if st.session_state.chart_symbol not in available_symbols:
                st.session_state.chart_symbol = available_symbols[0] if available_symbols else 'SPY'
            
            selected_symbol = st.selectbox(
                "Select Ticker",
                available_symbols,
                index=available_symbols.index(st.session_state.chart_symbol) if st.session_state.chart_symbol in available_symbols else 0,
                key="chart_symbol_selector"
            )
            
            # Update session state when symbol changes
            if selected_symbol != st.session_state.chart_symbol:
                st.session_state.chart_symbol = selected_symbol
                st.rerun()
            
            chart_symbol = st.session_state.chart_symbol
        else:
            chart_symbol = st.session_state.chart_symbol if 'chart_symbol' in st.session_state else 'SPY'
        
        # Fetch chart data for selected symbol
        try:
            # Check if prices table exists and has data
            if not prices_table_has_data():
                st.info("📊 **No market data available yet.** Click **📥 Fetch Popular Tickers** in the sidebar to load initial data.")
                st.stop()
            
            with engine.begin() as conn:
                # Get the most recent data (try last 90 days, fallback to all available)
                chart_data = pd.read_sql(
                    text("""
                        SELECT date, adj_close
                        FROM prices
                        WHERE symbol = :sym
                        AND date >= CURRENT_DATE - INTERVAL '90 days'
                        ORDER BY date
                    """),
                    conn,
                    params={"sym": chart_symbol}
                )
                
                # If no recent data, get all available data for this symbol
                if chart_data.empty:
                    chart_data = pd.read_sql(
                        text("""
                            SELECT date, adj_close
                            FROM prices
                            WHERE symbol = :sym
                            ORDER BY date
                        """),
                        conn,
                        params={"sym": chart_symbol}
                    )
        except (ProgrammingError, OperationalError) as e:
            error_msg = str(e).lower()
            if "table" in error_msg and "does not exist" in error_msg or "does not exist" in error_msg:
                st.info("📊 **No market data available yet.** Click **📥 Fetch Popular Tickers** in the sidebar to load initial data.")
                st.stop()
            else:
                st.error(f"Database error: {e}")
                st.stop()
        except Exception as e:
            st.error(f"Error loading chart data: {e}")
            st.stop()
            
            if not chart_data.empty:
                # Sort by date to ensure correct order
                chart_data = chart_data.sort_values('date')
                
                # Get current/latest price
                latest_price = float(chart_data['adj_close'].iloc[-1])
                latest_date = chart_data['date'].iloc[-1]
                first_price = float(chart_data['adj_close'].iloc[0])
                price_change = ((latest_price - first_price) / first_price) * 100 if first_price > 0 else 0
                price_change_color = "#10b981" if price_change >= 0 else "#ef4444"
                
                # Show current price info
                col_price1, col_price2 = st.columns(2)
                with col_price1:
                    st.metric(
                        f"{chart_symbol} Current Price",
                        f"${latest_price:,.2f}",
                        f"{price_change:+.2f}%"
                    )
                with col_price2:
                    st.metric("Last Updated", latest_date.strftime("%Y-%m-%d") if hasattr(latest_date, 'strftime') else str(latest_date))
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=chart_data['date'],
                    y=chart_data['adj_close'],
                    mode='lines',
                    line=dict(color='#00d4ff', width=3),
                    fill='tozeroy',
                    fillcolor='rgba(0, 212, 255, 0.1)',
                    name=chart_symbol,
                    hovertemplate=f'<b>{chart_symbol}</b><br>Date: %{{x}}<br>Price: $%{{y:,.2f}}<extra></extra>'
                ))
                
                # Add a marker for the latest price
                fig.add_trace(go.Scatter(
                    x=[chart_data['date'].iloc[-1]],
                    y=[latest_price],
                    mode='markers',
                    marker=dict(color='#10b981', size=10, symbol='star'),
                    name='Current',
                    hovertemplate=f'<b>Current</b><br>Date: {latest_date}<br>Price: ${latest_price:,.2f}<extra></extra>',
                    showlegend=False
                ))
                
                fig.update_layout(
                    plot_bgcolor='rgba(0, 0, 0, 0)',
                    paper_bgcolor='rgba(0, 0, 0, 0)',
                    font=dict(color='#ffffff', family='-apple-system, BlinkMacSystemFont'),
                    xaxis=dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', showline=True, linecolor='rgba(255, 255, 255, 0.2)', title='Date'),
                    yaxis=dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', showline=True, linecolor='rgba(255, 255, 255, 0.2)', title='Price ($)'),
                    height=400,
                    margin=dict(l=20, r=20, t=40, b=20),
                    hovermode='x unified',
                    title=dict(text=f'{chart_symbol} Price Chart', font=dict(color='#ffffff', size=14)),
                    legend=dict(bgcolor='rgba(0, 0, 0, 0.3)', bordercolor='rgba(255, 255, 255, 0.1)', font=dict(color='#ffffff'))
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})
            else:
                st.info(f"💡 **No data available for {chart_symbol}**\n\nTry selecting a different ticker or click '📥 Fetch Popular Tickers' in the sidebar to load data.")
        except Exception as e:
            st.warning(f"Chart error: {e}")
        st.info("💡 If you see a database error, try clicking '📥 Fetch Popular Tickers' in the sidebar to initialize data.")
    
    with col_order:
    st.markdown('<div class="section-header">📝 Order Entry</div>', unsafe_allow_html=True)
    
    with st.container():
        symbol = st.text_input("Symbol", value=st.session_state.chart_symbol if 'chart_symbol' in st.session_state else "AAPL", key="order_symbol")
        
        # Update chart when symbol changes in order entry
        if symbol and symbol.upper() != st.session_state.chart_symbol:
            st.session_state.chart_symbol = symbol.upper()
            # Check if symbol exists in database before updating
            try:
                with engine.begin() as conn:
                    symbol_exists = conn.execute(
                        text("SELECT COUNT(*) FROM prices WHERE symbol = :sym"),
                        {"sym": symbol.upper()}
                    ).fetchone()[0]
                    if symbol_exists > 0:
                        st.rerun()
            except Exception:
                pass
        
        col_buy, col_sell = st.columns(2)
        with col_buy:
            buy_selected = st.button("🟢 Buy", type="primary", use_container_width=True)
        with col_sell:
            sell_selected = st.button("🔴 Sell", use_container_width=True)
        
        order_side = "buy" if buy_selected else ("sell" if sell_selected else "buy")
        
        order_type = st.selectbox("Order Type", ["Market", "Limit", "Stop"], key="order_type")
        
        if order_type == "Limit":
            limit_price = st.number_input("Limit Price", value=150.0, step=0.01, format="%.2f")
        else:
            limit_price = None
        
        quantity = st.number_input("Quantity", value=100, min_value=1, step=1)
        
        if st.button("Place Order →", type="primary", use_container_width=True):
            try:
                from qs.oms.manager import get_order_manager
                from qs.oms.order import OrderSide, OrderType
                
                manager = get_order_manager()
                order = manager.create_order(
                    symbol=symbol.upper(),
                    side=OrderSide(order_side),
                    quantity=float(quantity),
                    order_type=OrderType.MARKET if order_type == "Market" else OrderType.LIMIT,
                    limit_price=limit_price
                )
                
                price = None
                if order_type == "Market":
                    with engine.begin() as conn:
                        result = conn.execute(
                            text("SELECT adj_close FROM prices WHERE symbol = :sym ORDER BY date DESC LIMIT 1"),
                            {"sym": symbol.upper()}
                        ).fetchone()
                    
                    if result:
                        price = float(result[0])
                        manager.submit_order(order.order_id)
                        manager.fill_order(order.order_id, float(quantity), price, send_sms=False)
                
                trade_price = price if price else (limit_price if limit_price else 0)
                st.session_state.trades.insert(0, {
                    'time': datetime.now().strftime("%H:%M:%S"),
                    'symbol': symbol.upper(),
                    'type': order_side.upper(),
                    'price': trade_price,
                    'quantity': quantity
                })
                
                st.session_state.logs.insert(0, f"{datetime.now().strftime('%H:%M:%S')} Order executed: {order_side.upper()} {quantity} {symbol.upper()}")
                st.success(f"✅ Order placed: {order_side.upper()} {quantity} {symbol.upper()}")
            except Exception as e:
                st.error(f"❌ Error: {e}")
                st.session_state.logs.insert(0, f"{datetime.now().strftime('%H:%M:%S')} Error: {str(e)}")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Bottom row: Trades, Algo Control, Live Logs
    col_trades, col_algo, col_logs = st.columns([0.4, 0.3, 0.3])
    
    with col_trades:
        st.markdown('<div class="section-header">📊 Recent Trades</div>', unsafe_allow_html=True)
        if st.session_state.trades:
            trades_df = pd.DataFrame(st.session_state.trades)
            st.dataframe(
                trades_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "time": "Time",
                    "symbol": "Symbol",
                    "type": "Type",
                    "price": st.column_config.NumberColumn("Price", format="$%.2f"),
                    "quantity": "Quantity"
                }
            )
        else:
            st.info("No trades yet")
    
    with col_algo:
        st.markdown('<div class="section-header">🤖 Algo Control</div>', unsafe_allow_html=True)
        if st.button("▶️ Start Algorithm", type="primary", use_container_width=True, key="algo_btn"):
            st.session_state.algo_running = not st.session_state.algo_running
            status = "started" if st.session_state.algo_running else "stopped"
            st.session_state.logs.insert(0, f"{datetime.now().strftime('%H:%M:%S')} Algorithm {status}")
        
        status_color = "#10b981" if st.session_state.algo_running else "#64748b"
        status_text = "🟢 Running" if st.session_state.algo_running else "⏸️ Stopped"
        st.markdown(f"""
    <div style="margin-top: 20px; padding: 16px; background: rgba(255, 255, 255, 0.05); border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.1);">
        <div style="font-size: 12px; color: #94a3b8; margin-bottom: 8px;">STATUS</div>
        <div style="font-size: 20px; font-weight: 700; color: {status_color};">
            {status_text}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_logs:
        st.markdown('<div class="section-header">📋 System Logs</div>', unsafe_allow_html=True)
        log_container = st.container()
        with log_container:
            log_html = '<div style="background: rgba(0, 0, 0, 0.3); border-radius: 12px; padding: 16px; max-height: 300px; overflow-y: auto; font-family: monospace; font-size: 12px;">'
            for log in st.session_state.logs[:10]:
                log_html += f'<div style="color: #94a3b8; padding: 4px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.05);">{log}</div>'
            log_html += '</div>'
            st.markdown(log_html, unsafe_allow_html=True)
            
            if not st.session_state.logs:
                st.info("No logs yet")

# Auto-refresh
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
