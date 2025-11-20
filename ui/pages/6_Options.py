from __future__ import annotations

import os
import sys
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from qs.config import get_settings
from qs.db import get_engine
from qs.options import (
    black_scholes, black_scholes_greeks, implied_volatility,
    options_chain_pricing, calculate_historical_volatility,
    volatility_surface, monte_carlo_option_price
)
# Optional import for options anomalies
try:
    from qs.notify.alerts import check_options_anomalies
    HAS_ALERTS = True
except ImportError:
    HAS_ALERTS = False
    def check_options_anomalies(*args, **kwargs):
        return None
from sqlalchemy import text

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_css import SHARED_CSS, CHART_LAYOUT, CHART_CONFIG

# Inject modern CSS
st.markdown(SHARED_CSS, unsafe_allow_html=True)

st.markdown("""
<div style="padding: 20px 0 30px 0;">
    <h1 style="font-size: 36px; font-weight: 800; background: linear-gradient(135deg, #00d4ff 0%, #0096ff 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin: 0;">
        📊 Options Trading
    </h1>
    <p style="color: #94a3b8; font-size: 14px; margin: 8px 0 0 0;">
        Black-Scholes pricing, Greeks, options chain, and anomaly detection
    </p>
</div>
""", unsafe_allow_html=True)

settings = get_settings()
engine = get_engine()

# Option pricing calculator
st.markdown('<div class="section-header">💰 Option Pricing Calculator</div>', unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])

with col1:
    symbol = st.text_input("Symbol", value="AAPL", key="opt_symbol")
    
    col_price, col_strike, col_expiry = st.columns(3)
    with col_price:
        S = st.number_input("Stock Price ($)", value=150.0, min_value=0.01, step=0.01, format="%.2f")
    with col_strike:
        K = st.number_input("Strike Price ($)", value=155.0, min_value=0.01, step=0.01, format="%.2f")
    with col_expiry:
        T_days = st.number_input("Days to Expiry", value=30, min_value=1, step=1)
    
    T = T_days / 365.0
    
    col_rate, col_vol, col_type = st.columns(3)
    with col_rate:
        r = st.number_input("Risk-Free Rate (%)", value=5.0, min_value=0.0, step=0.1, format="%.2f") / 100.0
    with col_vol:
        sigma = st.number_input("Volatility (%)", value=25.0, min_value=0.01, step=0.1, format="%.2f") / 100.0
    with col_type:
        option_type = st.selectbox("Option Type", ["call", "put"])

# Fetch current price and volatility if available
try:
    with engine.begin() as conn:
        price_result = conn.execute(
            text("SELECT adj_close FROM prices WHERE symbol = :sym ORDER BY date DESC LIMIT 1"),
            {"sym": symbol.upper()}
        ).fetchone()
        if price_result:
            current_price = float(price_result[0])
            if st.button("Use Current Price"):
                S = current_price
                st.rerun()
        
        hist_vol = calculate_historical_volatility(symbol.upper(), days=30, engine=engine)
        if hist_vol:
            if st.button("Use Historical Volatility"):
                sigma = hist_vol
                st.rerun()
except Exception:
    pass

with col2:
    # Calculate price
    price = black_scholes(S, K, T, r, sigma, option_type)
    greeks = black_scholes_greeks(S, K, T, r, sigma, option_type)
    
    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size: 12px; color: #94a3b8; margin-bottom: 8px;">OPTION PRICE</div>
        <div style="font-size: 32px; font-weight: 700; color: #00d4ff; margin: 12px 0;">
            ${price:.2f}
        </div>
        <div style="font-size: 11px; color: #94a3b8; margin-top: 16px;">GREEKS</div>
        <div style="font-size: 14px; margin-top: 8px;">
            <div style="display: flex; justify-content: space-between; padding: 4px 0;">
                <span>Δ Delta:</span>
                <span style="color: #10b981;">{greeks['delta']:.4f}</span>
            </div>
            <div style="display: flex; justify-content: space-between; padding: 4px 0;">
                <span>Γ Gamma:</span>
                <span style="color: #10b981;">{greeks['gamma']:.4f}</span>
            </div>
            <div style="display: flex; justify-content: space-between; padding: 4px 0;">
                <span>Θ Theta:</span>
                <span style="color: #ef4444;">{greeks['theta']:.2f}</span>
            </div>
            <div style="display: flex; justify-content: space-between; padding: 4px 0;">
                <span>ν Vega:</span>
                <span style="color: #10b981;">{greeks['vega']:.2f}</span>
            </div>
            <div style="display: flex; justify-content: space-between; padding: 4px 0;">
                <span>ρ Rho:</span>
                <span style="color: #10b981;">{greeks['rho']:.2f}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Check for anomalies
    if HAS_ALERTS:
        try:
            anomaly = check_options_anomalies(symbol.upper(), K, T_days, price, option_type)
            if anomaly:
                st.warning(f"⚠️ **Anomaly Detected!**\n\n{anomaly.get('message', 'Unusual option pricing detected')}")
        except Exception:
            pass

# Implied Volatility Calculator
st.markdown('<div class="section-header">📈 Implied Volatility Calculator</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    market_price = st.number_input("Market Price ($)", value=price, min_value=0.01, step=0.01, format="%.2f", key="iv_price")
    iv_calc = st.button("Calculate Implied Volatility", type="primary")

if iv_calc:
    try:
        iv = implied_volatility(market_price, S, K, T, r, option_type)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Implied Volatility", f"{iv*100:.2f}%")
        with col2:
            st.metric("Historical Volatility", f"{sigma*100:.2f}%")
        with col3:
            diff = (iv - sigma) / sigma * 100
            st.metric("Difference", f"{diff:+.2f}%")
        
        if abs(diff) > 10:
            st.info("📊 Significant difference between implied and historical volatility detected.")
    except Exception as e:
        st.error(f"Error calculating IV: {e}")

# Options Chain
st.markdown('<div class="section-header">📋 Options Chain</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    chain_symbol = st.text_input("Chain Symbol", value=symbol, key="chain_symbol")
with col2:
    chain_strikes_range = st.number_input("Strikes Range (%)", value=20.0, min_value=5.0, max_value=100.0, step=5.0)
with col3:
    chain_expiry = st.number_input("Expiry (days)", value=30, min_value=1, step=1, key="chain_expiry")

if st.button("Generate Options Chain", type="primary"):
    try:
        # Get current price
        with engine.begin() as conn:
            price_result = conn.execute(
                text("SELECT adj_close FROM prices WHERE symbol = :sym ORDER BY date DESC LIMIT 1"),
                {"sym": chain_symbol.upper()}
            ).fetchone()
        
        if price_result:
            current_S = float(price_result[0])
            hist_vol = calculate_historical_volatility(chain_symbol.upper(), days=30, engine=engine)
            if not hist_vol:
                hist_vol = 0.25
            
            # Generate strikes
            num_strikes = 10
            strike_range = current_S * (chain_strikes_range / 100)
            strikes = np.linspace(current_S - strike_range/2, current_S + strike_range/2, num_strikes)
            
            chain = options_chain_pricing(current_S, strikes.tolist(), chain_expiry/365.0, r, hist_vol)
            
            # Display chain
            st.dataframe(
                chain.style.format({
                    'price': '${:.2f}',
                    'delta': '{:.4f}',
                    'gamma': '{:.4f}',
                    'theta': '{:.2f}',
                    'vega': '{:.2f}',
                    'rho': '{:.2f}'
                }),
                use_container_width=True,
                hide_index=True
            )
            
            # Visualize chain
            calls = chain[chain['type'] == 'call']
            puts = chain[chain['type'] == 'put']
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=calls['strike'], y=calls['price'],
                mode='lines+markers', name='Calls',
                line=dict(color='#10b981', width=2),
                marker=dict(size=8)
            ))
            fig.add_trace(go.Scatter(
                x=puts['strike'], y=puts['price'],
                mode='lines+markers', name='Puts',
                line=dict(color='#ef4444', width=2),
                marker=dict(size=8)
            ))
            
            layout = CHART_LAYOUT.copy()
            layout.update({
                'height': 400,
                'xaxis': dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', showline=True, linecolor='rgba(255, 255, 255, 0.2)', title='Strike Price'),
                'yaxis': dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', showline=True, linecolor='rgba(255, 255, 255, 0.2)', title='Option Price'),
                'legend': dict(
                    bgcolor='rgba(0, 0, 0, 0.3)',
                    bordercolor='rgba(255, 255, 255, 0.1)',
                    font=dict(color='#ffffff')
                )
            })
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
        else:
            st.warning(f"No price data found for {chain_symbol}")
    except Exception as e:
        st.error(f"Error generating options chain: {e}")

# Monte Carlo Pricing
with st.expander("🎲 Monte Carlo Pricing (Advanced)"):
    col1, col2 = st.columns(2)
    with col1:
        mc_simulations = st.number_input("Number of Simulations", value=10000, min_value=1000, step=1000, format="%d")
    with col2:
        if st.button("Run Monte Carlo", type="primary"):
            try:
                mc_result = monte_carlo_option_price(S, K, T, r, sigma, option_type, n_simulations=mc_simulations)
                mc_price = mc_result['price']
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Monte Carlo Price", f"${mc_price:.2f}")
                with col2:
                    bs_price = black_scholes(S, K, T, r, sigma, option_type)
                    diff = abs(mc_price - bs_price)
                    st.metric("Difference from BS", f"${diff:.4f}")
            except Exception as e:
                st.error(f"Error: {e}")

