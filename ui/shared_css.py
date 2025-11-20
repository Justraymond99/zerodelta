# Shared CSS for all ZeroDelta pages

SHARED_CSS = """
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
        font-size: 20px;
        font-weight: 700;
        color: #ffffff;
        margin: 20px 0 16px 0;
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
    
    /* Streamlit widget styling */
    .stSelectbox > div > div > select,
    .stMultiSelect > div > div > div {
        background-color: rgba(255, 255, 255, 0.05);
        color: white;
    }
</style>
"""

# Chart layout template for consistent styling
CHART_LAYOUT = {
    'plot_bgcolor': 'rgba(0, 0, 0, 0)',
    'paper_bgcolor': 'rgba(0, 0, 0, 0)',
    'font': dict(color='#ffffff', family='-apple-system, BlinkMacSystemFont'),
    'xaxis': dict(
        showgrid=True,
        gridcolor='rgba(255, 255, 255, 0.1)',
        showline=True,
        linecolor='rgba(255, 255, 255, 0.2)'
    ),
    'yaxis': dict(
        showgrid=True,
        gridcolor='rgba(255, 255, 255, 0.1)',
        showline=True,
        linecolor='rgba(255, 255, 255, 0.2)'
    ),
    'margin': dict(l=20, r=20, t=40, b=20),
    'hovermode': 'x unified'
}

# Chart config
CHART_CONFIG = {
    'displayModeBar': True,  # Enable for debugging - can set to False later
    'displaylogo': False,
    'modeBarButtonsToRemove': [],
    'responsive': True
}

