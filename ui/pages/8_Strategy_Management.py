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
from qs.strategies.manager import get_strategy_manager
# Import from qs.strategies.py file (not the package directory)
import importlib.util
from pathlib import Path

# Load strategies.py file directly
parent_dir = Path(__file__).parent.parent.parent / "qs"
strategies_file = parent_dir / "strategies.py"

if strategies_file.exists():
    spec = importlib.util.spec_from_file_location("qs_strategies_module", strategies_file)
    qs_strategies_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qs_strategies_module)
    
    MomentumStrategy = getattr(qs_strategies_module, 'MomentumStrategy', None)
    MeanReversionStrategy = getattr(qs_strategies_module, 'MeanReversionStrategy', None)
    MLStrategy = getattr(qs_strategies_module, 'MLStrategy', None)
else:
    MomentumStrategy = None
    MeanReversionStrategy = None
    MLStrategy = None
from qs.backtest import backtest_signal

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_css import SHARED_CSS, CHART_LAYOUT, CHART_CONFIG

# Inject modern CSS
st.markdown(SHARED_CSS, unsafe_allow_html=True)

st.markdown("""
<div style="padding: 20px 0 30px 0;">
    <h1 style="font-size: 36px; font-weight: 800; background: linear-gradient(135deg, #00d4ff 0%, #0096ff 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin: 0;">
        🎯 Strategy Management
    </h1>
    <p style="color: #94a3b8; font-size: 14px; margin: 8px 0 0 0;">
        Manage multiple trading strategies, enable/disable, allocation, and compare performance
    </p>
</div>
""", unsafe_allow_html=True)

settings = get_settings()
engine = get_engine()
strategy_manager = get_strategy_manager()

# Get available signals from database
try:
    with engine.begin() as conn:
        signals = pd.read_sql(
            text("SELECT DISTINCT signal_name FROM signals ORDER BY signal_name"),
            conn
        )['signal_name'].tolist()
except Exception:
    signals = []
    st.warning("Database is busy; retry in a few seconds.")

# Strategy types
strategy_types = {
    "Momentum": MomentumStrategy,
    "Mean Reversion": MeanReversionStrategy,
    "ML-Based": MLStrategy
}

# Register default strategies if not already registered
if not strategy_manager.strategies:
    st.info("ℹ️ No strategies registered. Register strategies below.")

# Add/Register Strategy
st.markdown('<div class="section-header">➕ Register New Strategy</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    strategy_name = st.text_input("Strategy Name", value="my_strategy", key="new_strat_name")
with col2:
    strategy_type = st.selectbox("Strategy Type", list(strategy_types.keys()), key="strat_type")
with col3:
    capital_allocation = st.number_input("Capital Allocation (%)", value=25.0, min_value=0.0, max_value=100.0, step=5.0, format="%.1f")

if st.button("Register Strategy", type="primary"):
    try:
        StrategyClass = strategy_types[strategy_type]
        
        if strategy_type == "ML-Based":
            strategy = StrategyClass(model_name=signals[0] if signals else "xgb_alpha")
        elif strategy_type == "Momentum":
            strategy = StrategyClass(lookback=20, top_n=5)
        else:  # Mean Reversion
            strategy = StrategyClass(lookback=20, entry_threshold=-2.0)
        
        strategy_manager.register_strategy(
            strategy,
            config={
                'enabled': True,
                'allocation': capital_allocation / 100.0,
                'min_signal_threshold': 0.5,
                'max_positions': 5
            }
        )
        st.success(f"✅ Strategy '{strategy_name}' registered!")
        st.rerun()
    except Exception as e:
        st.error(f"Error registering strategy: {e}")

st.markdown("<br>", unsafe_allow_html=True)

# List and manage strategies
st.markdown('<div class="section-header">📊 Registered Strategies</div>', unsafe_allow_html=True)

if strategy_manager.strategies:
    strategies_list = strategy_manager.list_strategies()
    
    for strategy_info in strategies_list:
        name = strategy_info['name']
        enabled = strategy_info.get('enabled', False)
        allocation = strategy_info.get('allocation', 0.0)
        performance = strategy_info.get('performance', {})
        
        with st.expander(f"{'🟢' if enabled else '🔴'} {name} - Allocation: {allocation*100:.1f}%"):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button(f"{'Disable' if enabled else 'Enable'}", key=f"toggle_{name}"):
                    if enabled:
                        strategy_manager.disable_strategy(name)
                    else:
                        strategy_manager.enable_strategy(name)
                    st.rerun()
            
            with col2:
                new_allocation = st.number_input(
                    "Allocation %",
                    value=float(allocation * 100),
                    min_value=0.0,
                    max_value=100.0,
                    step=5.0,
                    key=f"alloc_{name}"
                )
                if new_allocation != allocation * 100:
                    strategy_manager.set_allocation(name, new_allocation / 100.0)
            
            with col3:
                if st.button("Run Backtest", key=f"backtest_{name}"):
                    with st.spinner(f"Running backtest for {name}..."):
                        try:
                            stats = backtest_signal(signal_name=name if name in signals else (signals[0] if signals else None))
                            if stats:
                                strategy_manager.update_performance(name, stats)
                                st.success("Backtest completed!")
                        except Exception as e:
                            st.error(f"Backtest error: {e}")
            
            with col4:
                if st.button("View Performance", key=f"perf_{name}"):
                    st.session_state[f"show_perf_{name}"] = True
            
            # Show performance if requested
            if st.session_state.get(f"show_perf_{name}", False):
                if performance:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Return", f"{performance.get('total_return', 0)*100:.2f}%")
                    with col2:
                        st.metric("Sharpe Ratio", f"{performance.get('sharpe', 0):.2f}")
                    with col3:
                        st.metric("Max Drawdown", f"{performance.get('max_drawdown', 0)*100:.2f}%")
                    with col4:
                        st.metric("Win Rate", f"{performance.get('win_rate', 0)*100:.2f}%")
                else:
                    st.info("No performance data available. Run backtest first.")
else:
    st.info("👈 No strategies registered yet. Register a strategy above.")

# Strategy Comparison
if len(strategies_list) > 1:
    st.markdown('<div class="section-header">📈 Strategy Comparison</div>', unsafe_allow_html=True)
    
    comparison_df = strategy_manager.compare_strategies()
    if not comparison_df.empty:
        # Display comparison metrics
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
        
        # Visualize comparison
        if 'total_return' in comparison_df.columns:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=comparison_df['strategy'],
                y=comparison_df['total_return'] * 100,
                marker=dict(color='#00d4ff'),
                name='Total Return (%)'
            ))
            
            layout = CHART_LAYOUT.copy()
            layout.update({
                'height': 400,
                'xaxis': dict(showgrid=False, showline=True, linecolor='rgba(255, 255, 255, 0.2)'),
                'yaxis': dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', showline=True, linecolor='rgba(255, 255, 255, 0.2)', title='Return (%)'),
                'hovermode': 'closest'
            })
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)

# Enabled strategies summary
enabled_strategies = strategy_manager.get_enabled_strategies()
st.markdown('<div class="section-header">✅ Enabled Strategies</div>', unsafe_allow_html=True)

if enabled_strategies:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Strategies", len(strategy_manager.strategies))
    with col2:
        st.metric("Enabled", len(enabled_strategies))
    with col3:
        total_allocation = sum(
            strategy_manager.strategy_configs.get(name, {}).get('allocation', 0)
            for name in enabled_strategies
        )
        st.metric("Total Allocation", f"{total_allocation*100:.1f}%")
    with col4:
        st.metric("Available", f"{(1.0 - total_allocation)*100:.1f}%")
    
    st.info(f"📊 Currently running: {', '.join(enabled_strategies) if enabled_strategies else 'None'}")
else:
    st.warning("⚠️ No strategies are currently enabled. Enable strategies above to start trading.")

