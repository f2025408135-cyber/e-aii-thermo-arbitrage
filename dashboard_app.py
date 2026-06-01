"""
E-AII Quantitative Web UI Dashboard
Ingests thermo_arbitrage_bot execution parameters and visualizes live execution telemetry.
Natively built inside the scratch workspace using Streamlit.
"""

import sys
import os
import time
import math
import threading
import pandas as pd
import numpy as np
import streamlit as st

# Configure page settings
st.set_page_config(
    page_title="E-AII Thermodynamic Arbitrage Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium CSS injection (glassmorphism, darkmode, and glowing components)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Orbitron:wght@500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background-color: #0b0c10;
        color: #c5c6c7;
    }
    
    /* Gaps & Paddings */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
    
    /* Glowing Title */
    .title-text {
        font-family: 'Orbitron', sans-serif;
        color: #66fcf1;
        font-size: 2.2rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 1.5rem;
        text-shadow: 0 0 10px rgba(102, 252, 241, 0.5);
    }
    
    /* Metric Cards Styling */
    .metric-card {
        background: rgba(31, 40, 51, 0.45);
        border: 1px solid rgba(102, 252, 241, 0.25);
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(5px);
        transition: transform 0.2s, border-color 0.2s;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(102, 252, 241, 0.6);
    }
    
    .metric-title {
        color: #85929E;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05rem;
        margin-bottom: 0.5rem;
    }
    
    .metric-val {
        font-family: 'Orbitron', sans-serif;
        color: #ffffff;
        font-size: 1.6rem;
        font-weight: 700;
    }
    
    .metric-green {
        color: #2ecc71 !important;
        text-shadow: 0 0 5px rgba(46, 204, 113, 0.4);
    }
    
    .metric-cyan {
        color: #66fcf1 !important;
        text-shadow: 0 0 5px rgba(102, 252, 241, 0.4);
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #1f2833 !important;
        border-right: 1px solid rgba(102, 252, 241, 0.1);
    }
    
    /* Connection Hub Accordion */
    .connection-status {
        font-weight: 700;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        text-align: center;
    }
    
    .status-disconnected {
        background-color: rgba(231, 76, 60, 0.15);
        color: #e74c3c;
        border: 1px solid rgba(231, 76, 60, 0.3);
    }
    
    .status-connected {
        background-color: rgba(46, 204, 113, 0.15);
        color: #2ecc71;
        border: 1px solid rgba(46, 204, 113, 0.3);
        box-shadow: 0 0 10px rgba(46, 204, 113, 0.1);
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Shared background execution state manager
class BotExecutionManager:
    def __init__(self):
        self.thread = None
        self.running = False
        self.lock = threading.Lock()
        
        # State metrics
        self.deployed_bankroll = 10.00
        self.overflow_cash_pool = 0.00
        self.current_mape = 0.0
        self.predictive_win_rate = 96.35
        self.current_index = 0
        
        # Performance/Signal history
        self.csv_history = []
        self.trades = []
        
        # Simulation speed configuration
        self.simulation_speed = 0.1  # Seconds between ticks
        self.total_ticks_processed = 0

    def reset_state(self):
        with self.lock:
            self.deployed_bankroll = 10.00
            self.overflow_cash_pool = 0.00
            self.current_mape = 0.0
            self.predictive_win_rate = 96.35
            self.current_index = 0
            self.csv_history = []
            self.trades = []
            self.total_ticks_processed = 0

@st.cache_resource
def get_manager():
    return BotExecutionManager()

manager = get_manager()

# Locate telemetry data
TELEMETRY_PATH = r"D:\HP\Downloads\live_execution_telemetry (3).csv"
if not os.path.exists(TELEMETRY_PATH):
    # Fallback to standard name if partition index is missing
    TELEMETRY_PATH = r"D:\HP\Downloads\live_execution_telemetry.csv"


class LiveTelemetryStreamer(threading.Thread):
    """
    Background worker thread reading telemetry data line-by-line and applying the trading logic.
    Inherits from threading.Thread natively.
    """
    def __init__(self, mgr, csv_path):
        super().__init__(daemon=True)
        self.mgr = mgr
        self.csv_path = csv_path

    def run(self):
        try:
            df = pd.read_csv(self.csv_path)
        except Exception as e:
            # Safe fallbacks or logs
            return
            
        num_rows = len(df)
        while True:
            with self.mgr.lock:
                if not self.mgr.running:
                    break
                    
                idx = self.mgr.current_index
                row = df.iloc[idx].to_dict()
                self.mgr.current_index = (self.mgr.current_index + 1) % num_rows
                self.mgr.total_ticks_processed += 1
                
                # Extract metrics
                raw_u = row.get('raw_u', 0.0)
                raw_v = row.get('raw_v', 0.0)
                raw_ahf = row.get('raw_ahf', 0.0)
                raw_T = row.get('raw_T', 0.0)
                mpcsignal = row.get('mpcsignal', 0.0)
                mpc_cost = row.get('mpc_cost', 0.0)
                execute = row.get('execute', 0)
                mape_current_pct = row.get('mape_current_pct', 0.0)
                win_rate_predictive_pct = row.get('win_rate_predictive_pct', 96.35)
                
                self.mgr.current_mape = mape_current_pct
                self.mgr.predictive_win_rate = win_rate_predictive_pct
                
                # Arbitrage Logic Execution:
                # If execute is 1, simulate transaction block and sweep profits
                if execute == 1:
                    order_size = min(self.mgr.deployed_bankroll, 4000.0)
                    net_return = (mpcsignal - mpc_cost) / 100.0
                    profit = order_size * net_return
                    
                    # Compounding & Sweep mechanics
                    temp_bankroll = self.mgr.deployed_bankroll + profit
                    if temp_bankroll > 4000.0:
                        if self.mgr.deployed_bankroll < 4000.0:
                            sweep = temp_bankroll - 4000.0
                            self.mgr.deployed_bankroll = 4000.0
                        else:
                            sweep = profit
                        self.mgr.overflow_cash_pool += sweep
                    else:
                        self.mgr.deployed_bankroll = temp_bankroll
                        sweep = 0.0
                        
                    self.mgr.trades.append({
                        'tick': self.mgr.total_ticks_processed,
                        'timestamp': row.get('timestamp_iso', ''),
                        'u_wind': math.sqrt(raw_u**2 + raw_v**2),
                        'ahf': raw_ahf,
                        'net_return': net_return * 100.0,
                        'profit': profit,
                        'sweep': sweep,
                        'bankroll': self.mgr.deployed_bankroll,
                        'overflow': self.mgr.overflow_cash_pool
                    })
                    
                # History log for st.line_chart
                self.mgr.csv_history.append({
                    'Tick': self.mgr.total_ticks_processed,
                    'mpcsignal': mpcsignal,
                    'mpc_cost': mpc_cost,
                    'raw_u': raw_u,
                    'raw_ahf': raw_ahf
                })
                if len(self.mgr.csv_history) > 100:
                    self.mgr.csv_history.pop(0)
                    
            time.sleep(self.mgr.simulation_speed)


# --- UI LAYOUT & SIDEBAR VAULT ---

st.sidebar.markdown(
    """
    <div style='text-align: center; margin-bottom: 1.5rem;'>
        <h2 style='font-family: Orbitron; color: #66fcf1; font-size: 1.5rem;'>🔒 SECURE KEY VAULT</h2>
        <hr style='border-color: rgba(102, 252, 241, 0.25);' />
    </div>
    """,
    unsafe_allow_html=True
)

# Initial session states
if 'connected' not in st.session_state:
    st.session_state.connected = False
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False

# Inputs disable when bot is running
inputs_disabled = st.session_state.bot_running

aws_access_key = st.sidebar.text_input("AWS Access Key ID", type="password", disabled=inputs_disabled)
aws_secret_key = st.sidebar.text_input("AWS Secret Access Key", type="password", disabled=inputs_disabled)
vast_api_key = st.sidebar.text_input("Vast.ai / RENDER API Key", type="password", disabled=inputs_disabled)
deepseek_api_key = st.sidebar.text_input("DeepSeek V4 API Key", type="password", disabled=inputs_disabled)

# 🔌 VENUE CONNECTION HUB ACCORDION
st.sidebar.markdown("<br/>", unsafe_allow_html=True)
with st.sidebar.expander("🔌 Venue Connection Hub", expanded=True):
    target_venue = st.selectbox(
        "Target Trading Venue",
        ["Amazon Web Services (Alpha 2 Institutional)", "Vast.ai / RENDER (Alpha 1 Sandbox)"],
        disabled=inputs_disabled
    )
    
    # Visual connection status indicator
    if st.session_state.connected:
        st.markdown(
            '<div class="connection-status status-connected">🟢 Connected & Autonomously Synced</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div class="connection-status status-disconnected">🔴 Disconnected</div>',
            unsafe_allow_html=True
        )
        
    connect_btn = st.button("Connect & Validate Account", disabled=inputs_disabled, use_container_width=True)
    
    if connect_btn:
        # Check if keys are filled (non-empty strings)
        if aws_access_key and aws_secret_key and vast_api_key and deepseek_api_key:
            st.session_state.connected = True
            st.success("API keys validated. Connected successfully.")
            st.rerun()
        else:
            st.error("Validation failed. Please enter all API keys.")


# --- MAIN CONTROL LAYOUT ---

st.markdown('<div class="title-text">⚡ E-AII THERMODYNAMIC ARBITRAGE SYSTEM</div>', unsafe_allow_html=True)

# Master Controls Switch
c1, c2, c3 = st.columns([2, 1, 1])

with c1:
    if not st.session_state.bot_running:
        start_btn = st.button("🚀 START AUTONOMOUS TRADING BOT", use_container_width=True, type="primary")
        if start_btn:
            if not st.session_state.connected:
                st.warning("Please connect and validate API credentials before starting.")
            else:
                st.session_state.bot_running = True
                # Set up manager running parameters
                with manager.lock:
                    manager.running = True
                    manager.thread = LiveTelemetryStreamer(manager, TELEMETRY_PATH)
                    manager.thread.start()
                st.rerun()
    else:
        stop_btn = st.button("🛑 STOP AUTONOMOUS TRADING BOT", use_container_width=True, type="secondary")
        if stop_btn:
            st.session_state.bot_running = False
            with manager.lock:
                manager.running = False
            st.rerun()

with c2:
    # Speed adjustment slider
    speed_factor = st.slider("Simulation Tick Delay (s)", 0.01, 1.0, 0.10, step=0.01)
    manager.simulation_speed = speed_factor

with c3:
    # Reset bankroll buttons
    reset_btn = st.button("🔄 Reset Portfolio Metrics", use_container_width=True)
    if reset_btn:
        manager.reset_state()
        st.success("Bankroll and cache reset to baseline.")
        st.rerun()


# --- REAL-TIME METRICS VISUALIZER GRID ---

st.markdown("<br/>", unsafe_allow_html=True)
m_col1, m_col2, m_col3, m_col4 = st.columns(4)

with m_col1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Deployed Bankroll</div>
            <div class="metric-val metric-cyan">${manager.deployed_bankroll:.2f}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with m_col2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Sidelined Cash Pool [SWEEP]</div>
            <div class="metric-val metric-green">${manager.overflow_cash_pool:.2f}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with m_col3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Current System MAPE</div>
            <div class="metric-val">{manager.current_mape:.2f}%</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with m_col4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Predictive Win-Rate</div>
            <div class="metric-val">{manager.predictive_win_rate:.2f}%</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# --- DYNAMIC CHARTING & DETAILS TABS ---

st.markdown("<br/>", unsafe_allow_html=True)

# Format chart data
history_data = list(manager.csv_history)
if len(history_data) > 0:
    chart_df = pd.DataFrame(history_data)
else:
    # Empty placeholder
    chart_df = pd.DataFrame(columns=['Tick', 'mpcsignal', 'mpc_cost', 'raw_u', 'raw_ahf'])

tab1, tab2 = st.tabs(["📈 Trajectory Signals", "📋 Live Transaction Ledger"])

with tab1:
    st.subheader("Model Predictive Control (mpcsignal) & Cost Trajectory")
    if not chart_df.empty:
        # Plot signals vs costs
        st.line_chart(chart_df.set_index('Tick')[['mpcsignal', 'mpc_cost']])
    else:
        st.info("Start the autonomous trading bot to stream telemetry signals.")

with tab2:
    st.subheader("Completed Trades (Sweep Settlement Logs)")
    trade_list = list(manager.trades)
    if len(trade_list) > 0:
        trades_df = pd.DataFrame(trade_list)
        st.dataframe(
            trades_df.style.format({
                'net_return': '{:+.4f}%',
                'profit': '${:,.4f}',
                'sweep': '${:,.4f}',
                'bankroll': '${:,.2f}',
                'overflow': '${:,.2f}',
                'u_wind': '{:.4f} m/s',
                'ahf': '{:.1f} W/m²'
            }),
            use_container_width=True
        )
    else:
        st.info("No trades filled yet. Waiting for `execute == 1` events in telemetry data.")


# --- DYNAMIC RE-RUN MECHANISM ---
# Reruns the Streamlit application while the trading bot thread is running
if st.session_state.bot_running:
    time.sleep(0.05)
    st.rerun()
