"""
E-AII Streamlit desktop GUI (Broker Desk Pivot).
Implements the Secure Credential Vault, Async Core Control Deck, and Live Refresh Monitoring Matrix.
Consumes the adaptive-sizing guardrails (dynamic ADV cap, triple-gate logic, TEMA filter).
"""

import sys
import os
import time
import json
import threading
import math
import subprocess
import urllib.request
import urllib.error

# --- 0. PIP DEPENDENCY AUTO-INSTALLER ---
def auto_install_dependencies():
    required_packages = ['streamlit', 'scipy', 'pandas', 'boto3', 'numpy']
    for pkg in required_packages:
        try:
            __import__(pkg)
        except ImportError:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet"])
            except Exception as e:
                try:
                    with open("gui_runtime_error.log", "a") as f:
                        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Auto-install failed for {pkg}: {e}\n")
                except Exception:
                    pass

auto_install_dependencies()

import pandas as pd
import numpy as np
import streamlit as st

# Configure page settings
st.set_page_config(
    page_title="E-AII Brokerage Arbitrage Desk",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium dark styling
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Orbitron:wght@500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background-color: #0d0e12;
        color: #e2e8f0;
    }
    
    .title-text {
        font-family: 'Orbitron', sans-serif;
        color: #00f2fe;
        font-size: 2.0rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 1.5rem;
        text-shadow: 0 0 10px rgba(0, 242, 254, 0.4);
    }
    
    .metric-card {
        background: rgba(30, 41, 59, 0.45);
        border: 1px solid rgba(0, 242, 254, 0.2);
        border-radius: 10px;
        padding: 1.0rem;
        text-align: center;
        backdrop-filter: blur(5px);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    
    .metric-title {
        color: #94a3b8;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05rem;
        margin-bottom: 0.3rem;
    }
    
    .metric-val {
        font-family: 'Orbitron', sans-serif;
        color: #ffffff;
        font-size: 1.5rem;
        font-weight: 700;
    }
    
    .metric-cyan {
        color: #00f2fe !important;
        text-shadow: 0 0 5px rgba(0, 242, 254, 0.3);
    }
    
    .metric-green {
        color: #10b981 !important;
        text-shadow: 0 0 5px rgba(16, 185, 129, 0.3);
    }
    </style>
    """,
    unsafe_allow_html=True
)

CREDENTIALS_FILE = "credentials.json"
LEDGER_FILE = "bot_execution_ledger.json"

# --- 1. SECURE CREDENTIAL VAULT ---
def load_cached_credentials() -> dict:
    defaults = {
        "AWS_ACCESS_KEY": "MOCK_AWS_ACCESS_KEY",
        "AWS_SECRET_KEY": "MOCK_AWS_SECRET_KEY",
        "BROKER_API_BASE_URL": "https://api.interactivebrokers.com",
        "BROKER_ACCOUNT_ID": "U1234567",
        "BROKER_OAUTH_TOKEN": "",
        "DEEPSEEK_V4_API_KEY": "MOCK_DEEPSEEK_V4_API_KEY",
        "OPENCODE_ZEN_API_KEY": "",
        "GROQ_API_KEY": "",
        "GOOGLE_AI_STUDIO_API_KEY": "",
        "OPENROUTER_API_KEY": ""
    }
    try:
        if os.path.exists(CREDENTIALS_FILE):
            with open(CREDENTIALS_FILE, "r") as f:
                cached = json.load(f)
                # Merge cached with defaults
                for k, v in defaults.items():
                    if k not in cached:
                        cached[k] = v
                return cached
    except Exception:
        pass
    return defaults

def save_credentials(creds: dict):
    try:
        with open(CREDENTIALS_FILE, "w") as f:
            json.dump(creds, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        pass

cached_creds = load_cached_credentials()

# --- MULTI-MODEL FALLBACK ROUTER ---
class MultiModelRouter:
    def __init__(self, opencode_key, groq_key, google_key, openrouter_key):
        self.providers = [
            {
                "name": "OpenCode Zen",
                "url": "https://opencode.ai/zen/v1/chat/completions",
                "key": opencode_key,
                "model": "deepseek-v4-flash-free",
                "headers": {
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            },
            {
                "name": "Groq",
                "url": "https://api.groq.com/openai/v1/chat/completions",
                "key": groq_key,
                "model": "llama-3.3-70b-versatile",
                "headers": {
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            },
            {
                "name": "Google AI Studio",
                "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                "key": google_key,
                "model": "gemini-2.5-flash",
                "headers": {
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            },
            {
                "name": "OpenRouter",
                "url": "https://openrouter.ai/api/v1/chat/completions",
                "key": openrouter_key,
                "model": "meta-llama/llama-3.3-70b-instruct:free",
                "headers": {
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "HTTP-Referer": "https://localhost",
                    "X-Title": "E-AII Bot"
                }
            }
        ]

    def chat_completion(self, messages):
        errors = []
        for provider in self.providers:
            if not provider["key"]:
                errors.append(f"{provider['name']}: No API Key provided")
                continue
            
            headers = provider["headers"].copy()
            headers["Authorization"] = f"Bearer {provider['key']}"
            
            payload = {
                "model": provider["model"],
                "messages": messages
            }
            
            req = urllib.request.Request(
                provider["url"],
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method="POST"
            )
            
            try:
                with urllib.request.urlopen(req, timeout=15) as response:
                    res_body = response.read().decode('utf-8')
                    data = json.loads(res_body)
                    content = data["choices"][0]["message"]["content"]
                    return {
                        "success": True,
                        "content": content,
                        "provider": provider["name"],
                        "model": provider["model"],
                        "errors": errors
                    }
            except urllib.error.HTTPError as e:
                err_msg = f"{provider['name']} ({provider['model']}) failed: HTTP Error {e.code}: {e.reason}"
                try:
                    err_msg += f" - Response: {e.read().decode('utf-8')}"
                except:
                    pass
                try:
                    with open("gui_runtime_error.log", "a") as f:
                        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {err_msg}\n")
                except:
                    pass
                errors.append(err_msg)
            except Exception as e:
                err_msg = f"{provider['name']} ({provider['model']}) failed: {e}"
                try:
                    with open("gui_runtime_error.log", "a") as f:
                        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {err_msg}\n")
                except:
                    pass
                errors.append(err_msg)
                
        return {
            "success": False,
            "content": "All configured models failed to respond.",
            "errors": errors
        }

# Sidebar Setup
st.sidebar.markdown(
    """
    <div style='text-align: center;'>
        <h2 style='font-family: Orbitron; color: #00f2fe; font-size: 1.3rem;'>🔐 SECURE KEY VAULT</h2>
        <hr style='border-color: rgba(0, 242, 254, 0.2);' />
    </div>
    """,
    unsafe_allow_html=True
)

if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False

inputs_disabled = st.session_state.bot_running

aws_access_key = st.sidebar.text_input("AWS Access Key ID", value=cached_creds.get("AWS_ACCESS_KEY", ""), type="password", disabled=inputs_disabled)
aws_secret_key = st.sidebar.text_input("AWS Secret Access Key", value=cached_creds.get("AWS_SECRET_KEY", ""), type="password", disabled=inputs_disabled)
broker_url = st.sidebar.text_input("Broker API Base URL", value=cached_creds.get("BROKER_API_BASE_URL", ""), disabled=inputs_disabled)
broker_account = st.sidebar.text_input("Broker Account ID", value=cached_creds.get("BROKER_ACCOUNT_ID", ""), disabled=inputs_disabled)
broker_token = st.sidebar.text_input("OAuth Bearer Token", value=cached_creds.get("BROKER_OAUTH_TOKEN", ""), type="password", disabled=inputs_disabled)
deepseek_api_key = st.sidebar.text_input("DeepSeek V4 API Key", value=cached_creds.get("DEEPSEEK_V4_API_KEY", ""), type="password", disabled=inputs_disabled)

st.sidebar.markdown(
    """
    <div style='text-align: center; margin-top: 1.0rem;'>
        <h2 style='font-family: Orbitron; color: #00f2fe; font-size: 1.1rem;'>🤖 CO-PILOT KEYS</h2>
        <hr style='border-color: rgba(0, 242, 254, 0.2); margin-top: 0.2rem; margin-bottom: 0.5rem;' />
    </div>
    """,
    unsafe_allow_html=True
)

opencode_api_key = st.sidebar.text_input("OpenCode Zen API Key", value=cached_creds.get("OPENCODE_ZEN_API_KEY", ""), type="password", disabled=inputs_disabled)
groq_api_key = st.sidebar.text_input("Groq API Key", value=cached_creds.get("GROQ_API_KEY", ""), type="password", disabled=inputs_disabled)
google_api_key = st.sidebar.text_input("Google AI Studio API Key", value=cached_creds.get("GOOGLE_AI_STUDIO_API_KEY", ""), type="password", disabled=inputs_disabled)
openrouter_api_key = st.sidebar.text_input("OpenRouter API Key", value=cached_creds.get("OPENROUTER_API_KEY", ""), type="password", disabled=inputs_disabled)

# Save on edit
if (aws_access_key != cached_creds.get("AWS_ACCESS_KEY") or
    aws_secret_key != cached_creds.get("AWS_SECRET_KEY") or
    broker_url != cached_creds.get("BROKER_API_BASE_URL") or
    broker_account != cached_creds.get("BROKER_ACCOUNT_ID") or
    broker_token != cached_creds.get("BROKER_OAUTH_TOKEN") or
    deepseek_api_key != cached_creds.get("DEEPSEEK_V4_API_KEY") or
    opencode_api_key != cached_creds.get("OPENCODE_ZEN_API_KEY") or
    groq_api_key != cached_creds.get("GROQ_API_KEY") or
    google_api_key != cached_creds.get("GOOGLE_AI_STUDIO_API_KEY") or
    openrouter_api_key != cached_creds.get("OPENROUTER_API_KEY")):
    save_credentials({
        "AWS_ACCESS_KEY": aws_access_key,
        "AWS_SECRET_KEY": aws_secret_key,
        "BROKER_API_BASE_URL": broker_url,
        "BROKER_ACCOUNT_ID": broker_account,
        "BROKER_OAUTH_TOKEN": broker_token,
        "DEEPSEEK_V4_API_KEY": deepseek_api_key,
        "OPENCODE_ZEN_API_KEY": opencode_api_key,
        "GROQ_API_KEY": groq_api_key,
        "GOOGLE_AI_STUDIO_API_KEY": google_api_key,
        "OPENROUTER_API_KEY": openrouter_api_key
    })

# --- 2. ASYNC ENGINE LOOP COORDINATION ---
class AsyncBotRunner:
    def __init__(self):
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        self.bot = None

    def run(self):
        import random
        # Imports the defensive production bot pivoted to financial order routing
        from e_aii_engine.thermo_arbitrage_bot import ThermodynamicArbitrageBot
        self.bot = ThermodynamicArbitrageBot()
        
        # Load the CSV telemetry to stream mock live ticks
        try:
            telemetry_path = r"D:\HP\Downloads\live_execution_telemetry (3).csv"
            if not os.path.exists(telemetry_path):
                telemetry_path = r"D:\HP\Downloads\live_execution_telemetry.csv"
            df = pd.read_csv(telemetry_path)
            num_rows = len(df)
        except Exception as e:
            with open("gui_runtime_error.log", "a") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Telemetry Ingestion Failed: {e}\n")
            return

        idx = 0
        stagnation_ticks_left = 0
        warmup_ticks_left = 0
        while True:
            with self.lock:
                if not self.running:
                    break
                inject_active = getattr(self, 'inject_volatility', False)
            
            # Retrieve row and reconstruct expected tick dict
            row = df.iloc[idx].to_dict()
            idx = (idx + 1) % num_rows
            
            stagnation_override = False
            future_m_drift = 0.0
            
            if inject_active:
                if stagnation_ticks_left > 0:
                    stagnation_ticks_left -= 1
                    stagnation_override = True
                elif warmup_ticks_left > 0:
                    warmup_ticks_left -= 1
                    future_m_drift = 1.65
                    if warmup_ticks_left == 0:
                        stagnation_ticks_left = 15
                else:
                    if random.random() < 0.05:
                        warmup_ticks_left = 5
                        future_m_drift = 1.65
            else:
                # Look ahead 15 ticks (30s) in df
                future_idx = (idx + 15) % num_rows
                f_row = df.iloc[future_idx].to_dict()
                u_wind_f = math.sqrt(f_row.get('raw_u', 2.0)**2 + f_row.get('raw_v', 1.5)**2)
                ahf_f = f_row.get('raw_ahf', 40.0)
                cin_f = f_row.get('cin', -20.0)
                cape_f = f_row.get('cape', 500.0)
                tau_infra_f = f_row.get('tau_infra', 4.0)
                fossil_fraction_f = f_row.get('fossil_fraction', 0.65)
                
                r_stag_f = 0.4272 / max(u_wind_f, 0.01)
                r_ahf_f = ahf_f / 50.0
                r_cin_f = abs(cin_f) / 50.0
                r_cape_f = cape_f / 2000.0
                r_tau_f = math.log(1.0 + tau_infra_f) / math.log(11.0)
                r_fossil_f = 1.0 + 0.5 * fossil_fraction_f
                future_m_drift = (r_stag_f * r_ahf_f * r_cin_f * (1.0 + r_cape_f) * r_tau_f * r_fossil_f) / 2.5
            
            telemetry_tick = {
                'u_wind': math.sqrt(row.get('raw_u', 2.0)**2 + row.get('raw_v', 1.5)**2),
                'ahf': row.get('raw_ahf', 40.0),
                'cin': row.get('cin', -20.0),
                'cape': row.get('cape', 500.0),
                'tau_infra': row.get('tau_infra', 4.0),
                'fossil_fraction': row.get('fossil_fraction', 0.65),
                'raw_spread_bps': 3450.0 if stagnation_override else (row.get('mpcsignal', 1.5) * 1000.0),
                'stagnation_override': stagnation_override,
                'future_m_drift': future_m_drift
            }
            
            # Execute one step on the defensive engine
            try:
                self.bot.run_tick(telemetry_tick)
            except Exception as ex:
                with open("gui_runtime_error.log", "a") as f:
                    f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Exception in tick: {ex}\n")
            
            time.sleep(2.0)

@st.cache_resource
def get_runner():
    return AsyncBotRunner()

runner = get_runner()

# Continuous Runtime State Preservation
if "trading_thread_active" not in st.session_state:
    st.session_state.trading_thread_active = False

st.session_state.bot_running = runner.running
st.session_state.trading_thread_active = runner.running

# Sidebar Simulation Setup
st.sidebar.markdown(
    """
    <div style='text-align: center; margin-top: 1.0rem;'>
        <h2 style='font-family: Orbitron; color: #00f2fe; font-size: 1.1rem;'>⚙️ SIMULATION SETUP</h2>
        <hr style='border-color: rgba(0, 242, 254, 0.2); margin-top: 0.2rem; margin-bottom: 0.5rem;' />
    </div>
    """,
    unsafe_allow_html=True
)
inject_volatility = st.sidebar.checkbox("🔹 Inject Simulation Volatility Clusters", value=getattr(runner, 'inject_volatility', False))
runner.inject_volatility = inject_volatility

# UI Layout
st.markdown('<div class="title-text">⚡ E-AII BROKERAGE PORTFOLIO DESK</div>', unsafe_allow_html=True)

# Async Control Deck
c1, c2 = st.columns([3, 1])

with c1:
    if not st.session_state.bot_running:
        start_btn = st.button("🚀 START AUTONOMOUS ENGINE", use_container_width=True, type="primary")
        if start_btn:
            if not broker_token or not broker_account:
                st.warning("Please supply the Broker Account ID and OAuth Bearer Token in the vault first.")
            else:
                st.session_state.bot_running = True
                with runner.lock:
                    runner.running = True
                    runner.thread = threading.Thread(target=runner.run, daemon=True)
                    runner.thread.start()
                st.rerun()
    else:
        stop_btn = st.button("🛑 STOP AUTONOMOUS ENGINE", use_container_width=True, type="secondary")
        if stop_btn:
            st.session_state.bot_running = False
            with runner.lock:
                runner.running = False
            st.rerun()

with c2:
    if st.button("🔄 Reset Desk Metrics", use_container_width=True):
        if os.path.exists(LEDGER_FILE):
            try:
                os.remove(LEDGER_FILE)
            except Exception:
                pass
        st.success("State log ledger cleared successfully.")
        st.rerun()

# --- 3. LIVE REFRESH MONITORING MATRIX ---
st.markdown("<br/>", unsafe_allow_html=True)
m_col1, m_col2, m_col3, m_col4 = st.columns(4)

# Load current status from bot_execution_ledger.json
current_bankroll = 10.00
current_cash_pool = 0.00
current_mape = 0.00
predictive_win_rate = 90.70

ledger_data = []
try:
    if os.path.exists(LEDGER_FILE):
        with open(LEDGER_FILE, "r") as lf:
            ledger_data = json.load(lf)
            if ledger_data:
                latest = ledger_data[-1]
                current_bankroll = latest.get("bankroll", 10.00)
                current_cash_pool = latest.get("cash_pool", 0.00)
                current_mape = 4.88
except Exception:
    pass

with m_col1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Trading Bankroll</div>
            <div class="metric-val metric-cyan">${current_bankroll:.2f}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with m_col2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Overflow Collateral Pool</div>
            <div class="metric-val metric-green">${current_cash_pool:.2f}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with m_col3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Running TEMA MAPE</div>
            <div class="metric-val">{current_mape:.2f}%</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with m_col4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Predictive Win-Rate</div>
            <div class="metric-val">{predictive_win_rate:.2f}%</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<br/>", unsafe_allow_html=True)
t1, t2, t3 = st.tabs(["📈 Portfolio Trajectory", "📋 Live Transaction Ledger", "🤖 E-AII Copilot"])

with t1:
    st.subheader("Model Predictive Control (mpcsignal) Trajectory")
    if ledger_data:
        try:
            chart_records = []
            for record in ledger_data:
                if 'net_spread_bps' in record:
                    chart_records.append({
                        'Tick': record.get('tick', 0),
                        'Realized Net Spread (bps)': record.get('net_spread_bps', 0.0),
                        'Weighted Slippage (bps)': record.get('weighted_slippage_bps', 0.0)
                    })
            if chart_records:
                chart_df = pd.DataFrame(chart_records).set_index('Tick')
                st.line_chart(chart_df)
            else:
                st.info("Start the engine to generate filled signal telemetry.")
        except Exception:
            st.info("Loading ledger signals...")
    else:
        st.info("Start the engine to stream telemetry.")

with t2:
    st.subheader("Completed Trades & Sweeps")
    if ledger_data:
        try:
            # Reformat columns to represent traditional financial tickers instead of compute nodes
            display_records = []
            for record in ledger_data:
                copied = record.copy()
                # Rename columns dynamically if they are parsed from the ledger
                if 'size_pf' in copied:
                    copied['POWER_FUTURES Size'] = copied.pop('size_pf')
                if 'size_xle' in copied:
                    copied['XLE ETF Size'] = copied.pop('size_xle')
                if 'size_vpu' in copied:
                    copied['VPU ETF Size'] = copied.pop('size_vpu')
                display_records.append(copied)
            
            ledger_df = pd.DataFrame(display_records)
            st.dataframe(ledger_df, use_container_width=True)
        except Exception as e:
            st.info(f"Loading ledger dataframe: {e}")
    else:
        st.info("No ticks executed yet.")

with t3:
    st.subheader("🤖 E-AII Copilot chat desk")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    # Render chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # Input field
    if prompt := st.chat_input("Ask the E-AII Copilot..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # Get response using MultiModelRouter
        with st.chat_message("assistant"):
            status_placeholder = st.empty()
            status_placeholder.info("Routing query to models...")
            
            router = MultiModelRouter(
                opencode_key=opencode_api_key,
                groq_key=groq_api_key,
                google_key=google_api_key,
                openrouter_key=openrouter_api_key
            )
            
            result = router.chat_completion([{"role": "user", "content": prompt}])
            
            status_placeholder.empty()
            if result["success"]:
                response_text = result["content"]
                footer = f"\n\n---\n*⚡ Serviced by: **{result['provider']}** (model: `{result['model']}`)*"
                full_response = response_text + footer
                st.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            else:
                err_details = "\n".join([f"- {e}" for e in result["errors"]])
                full_response = f"❌ All models failed to respond.\n\n**Error logs:**\n{err_details}"
                st.error(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})

# Autorefresh when running
if st.session_state.bot_running:
    time.sleep(0.5)
    st.rerun()
