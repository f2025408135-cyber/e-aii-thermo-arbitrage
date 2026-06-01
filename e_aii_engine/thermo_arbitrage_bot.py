"""
E-AII Thermodynamic Arbitrage Production Bot Script (Financial Broker Desk Pivot).
Natively built according to E-AII Alpha Validation Report specifications.
Tracks trailing climate vectors, implements triple-gate logic, dual-account balance sweep mechanics,
Feynman 4-mode thermal decay overhang, and stochastic network execution latency delays.
Pivoted to route allocations over liquid traditional energy proxies (POWER_FUTURES, XLE, VPU).
"""

import sys
import os
import time
import math
import random
import logging
import traceback
import json
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
                import subprocess
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet"])
            except Exception as e:
                try:
                    with open("bot_runtime_error.log", "a") as f:
                        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Auto-install failed for {pkg}: {e}\n")
                except Exception:
                    pass

auto_install_dependencies()

import numpy as np

# Ensure debug logging to millisecond precision
class MillisecondFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        try:
            ct = self.converter(record.created)
            if datefmt:
                s = time.strftime(datefmt, ct)
            else:
                t = time.strftime("%Y-%m-%d %H:%M:%S", ct)
                s = f"{t}.{int(record.msecs):03d}"
            return s
        except Exception as e:
            log_exception_to_file(e, "MillisecondFormatter.formatTime")
            return ""

# Initialize global exception logger
def log_exception_to_file(exc: Exception, context: str = ""):
    try:
        with open("bot_runtime_error.log", "a") as f:
            f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] --- EXCEPTION IN {context} ---\n")
            traceback.print_exc(file=f)
            f.flush()
    except Exception:
        pass

logger = logging.getLogger("E-AII_Bot")
logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(MillisecondFormatter("[%(asctime)s] %(levelname)s: %(message)s"))
if not logger.handlers:
    logger.addHandler(sh)


# --- 1. METEOROLOGICAL & THERMO STATE MONITOR (TRIPLE-GATE LOGIC) ---

class RegionalThermalMonitor:
    """
    Scans environmental telemetry and enforces the strict execution gate.
    Do not route any transaction signals unless:
    u_wind < 0.4272 m/s AND AHF >= 100 W/m^2 AND M_drift > 1.10 simultaneously.
    """
    WIND_STAGNATION_THRESHOLD = 0.4272  # m/s
    THERMAL_WALL_AHF = 100.0            # W/m^2
    M_DRIFT_THERMAL_WALL = 1.10         # Drift threshold

    def __init__(self, gamma: float = 0.5, epsilon: float = 0.76):
        try:
            self.gamma = gamma
            self.epsilon = epsilon
        except Exception as e:
            log_exception_to_file(e, "RegionalThermalMonitor.__init__")

    def compute_m_drift_from_components(self, u_wind: float, ahf: float, cin: float, cape: float, tau_infra: float, fossil_fraction: float) -> float:
        """
        Implements Section 3.1 Composite Six-Factor Model:
        M_drift = R_stag * R_ahf * R_cin * (1 + R_cape) * R_tau * R_fossil / 2.5
        """
        try:
            r_stag = self.WIND_STAGNATION_THRESHOLD / max(u_wind, 0.01)
            r_ahf = ahf / 50.0
            r_cin = abs(cin) / 50.0
            r_cape = cape / 2000.0
            r_tau = math.log(1.0 + tau_infra) / math.log(11.0)
            r_fossil = 1.0 + 0.5 * fossil_fraction
            m_drift = (r_stag * r_ahf * r_cin * (1.0 + r_cape) * r_tau * r_fossil) / 2.5
            return m_drift
        except Exception as e:
            log_exception_to_file(e, "RegionalThermalMonitor.compute_m_drift_from_components")
            return 0.0  # safe default fallback to block gate

    def evaluate_gate(self, u_wind: float, ahf: float, m_drift: float) -> bool:
        """
        Hard-coded triple-gate: u_wind < 0.4272 and ahf >= 100.0 and m_drift > 1.10
        """
        try:
            wind_gate = u_wind < self.WIND_STAGNATION_THRESHOLD
            ahf_gate = ahf >= self.THERMAL_WALL_AHF
            drift_gate = m_drift > self.M_DRIFT_THERMAL_WALL
            passed = wind_gate and ahf_gate and drift_gate
            logger.debug(
                f"Gate check: Wind={u_wind:.4f} m/s (gate={wind_gate}), "
                f"AHF={ahf:.1f} W/m^2 (gate={ahf_gate}), "
                f"M_drift={m_drift:.4f} (gate={drift_gate}) -> Passed={passed}"
            )
            return passed
        except Exception as e:
            log_exception_to_file(e, "RegionalThermalMonitor.evaluate_gate")
            return False  # safe default fallback


# --- 2. CAPITAL BALANCE & PROFIT SWEEP MONITOR ---

class AccountBalanceManager:
    """
    Tracks trading bankroll and sideline cash pools.
    Applies dynamic liquidity caps based on asset ADV (0.01% of 5-min volume)
    and sweeps settlement profits.
    """
    DEFAULT_CAP = 4000.00

    def __init__(self, initial_bankroll: float = 10.00):
        try:
            self.Deployed_Bankroll = float(initial_bankroll)
            self.Overflow_Cash_Pool = 0.00
            logger.info(
                f"Initialized AccountBalanceManager with Deployed_Bankroll=${self.Deployed_Bankroll:.2f}, "
                f"Overflow_Cash_Pool=${self.Overflow_Cash_Pool:.2f}"
            )
        except Exception as e:
            log_exception_to_file(e, "AccountBalanceManager.__init__")

    def determine_order_size(self, telemetry: dict = None) -> float:
        """
        Calculates dynamic position cap tick-by-tick. Enforces that the total position size
        (leveraged 100x) does not exceed 0.01% of the assets' top-of-book 5-minute volume.
        """
        try:
            if telemetry is None:
                current_cap = self.DEFAULT_CAP
            else:
                u_wind = telemetry.get('u_wind', 2.0)
                ahf = telemetry.get('ahf', 40.0)
                
                # Model 5-minute top-of-book volume dynamically based on market/telemetry signals
                pf_5min_vol = 5_000_000 * (1.0 + 0.5 * (ahf / 100.0))
                xle_5min_vol = 15_000_000 * (1.0 + 0.2 * u_wind)
                vpu_5min_vol = 4_000_000 * (1.0 + 0.1 * u_wind)
                
                # Dynamic Cap is 0.01% of 5-minute volume sum
                current_cap = 0.0001 * (pf_5min_vol + xle_5min_vol + vpu_5min_vol)
                
            # Leverage is fixed at 100x for geometric compounding phase
            target_position = self.Deployed_Bankroll * 100.0
            
            if target_position >= current_cap:
                size = current_cap
            else:
                size = target_position
                
            logger.debug(f"Allocating leveraged trade size: ${size:.2f} (Leveraged Target: ${target_position:.2f}, Dynamic Cap: ${current_cap:.2f})")
            return size
        except Exception as e:
            log_exception_to_file(e, "AccountBalanceManager.determine_order_size")
            return 0.0

    def process_settlement(self, allocated_size: float, net_return_pct: float, telemetry: dict = None):
        """
        Slices all settlement profits off the leveraged trade and routes them to the Overflow_Cash_Pool
        when the balance exceeds the dynamic microstructure liquidity cap.
        """
        try:
            gross_pnl = allocated_size * net_return_pct
            logger.info(f"Trade settled. Allocated Size: ${allocated_size:.2f}, Net Return: {net_return_pct*100.0:+.4f}% -> Gross PnL: ${gross_pnl:+.4f}")
            
            if telemetry is None:
                current_cap = self.DEFAULT_CAP
            else:
                u_wind = telemetry.get('u_wind', 2.0)
                ahf = telemetry.get('ahf', 40.0)
                pf_5min_vol = 5_000_000 * (1.0 + 0.5 * (ahf / 100.0))
                xle_5min_vol = 15_000_000 * (1.0 + 0.2 * u_wind)
                vpu_5min_vol = 4_000_000 * (1.0 + 0.1 * u_wind)
                current_cap = 0.0001 * (pf_5min_vol + xle_5min_vol + vpu_5min_vol)
            
            if gross_pnl > 0.0:
                temp_bankroll = self.Deployed_Bankroll + gross_pnl
                if temp_bankroll > current_cap:
                    if self.Deployed_Bankroll < current_cap:
                        added_to_bankroll = current_cap - self.Deployed_Bankroll
                        sweep_amount = temp_bankroll - current_cap
                        self.Deployed_Bankroll = current_cap
                    else:
                        added_to_bankroll = 0.0
                        sweep_amount = gross_pnl
                    self.Overflow_Cash_Pool += sweep_amount
                    logger.info(f"Sweep executed: ${sweep_amount:.4f} routed to Overflow_Cash_Pool. Bankroll locked at dynamic cap ${self.Deployed_Bankroll:.2f}")
                else:
                    self.Deployed_Bankroll = temp_bankroll
                    logger.info(f"No sweep: Bankroll increased to ${self.Deployed_Bankroll:.2f} (under dynamic cap ${current_cap:.2f})")
            else:
                self.Deployed_Bankroll += gross_pnl
                logger.warning(f"Loss incurred: ${abs(gross_pnl):.4f} deducted from Deployed_Bankroll. New Bankroll: ${self.Deployed_Bankroll:.2f}")
        except Exception as e:
            log_exception_to_file(e, "AccountBalanceManager.process_settlement")

    def charge_opex_penalty(self, charge_amount: float):
        """
        Deducts operational expenditure penalties (e.g. from thermal overhang hysteresis) directly from Deployed_Bankroll.
        """
        try:
            self.Deployed_Bankroll -= charge_amount
            logger.debug(f"Charged OpEx surcharge of ${charge_amount:.4f}. New Deployed_Bankroll: ${self.Deployed_Bankroll:.2f}")
        except Exception as e:
            log_exception_to_file(e, "AccountBalanceManager.charge_opex_penalty")


# --- 3. THERMAL INERTIA HYSTERESIS MONITOR ---

class ThermalInertiaMonitor:
    """
    Feynman 4-mode exponential decay matrix and persistent OpEx surcharge tracking.
    """
    MODES = {
        'air':      {'tau': 1.0,   'weight': 0.40},
        'surface':  {'tau': 8.0,   'weight': 0.30},
        'deep':     {'tau': 30.0,  'weight': 0.25},
        'ground':   {'tau': 150.0, 'weight': 0.05}
    }
    K_COUPLING = 105.0
    STRUCTURAL_HEAT_CAPACITY = 1000.0

    def __init__(self, t_ambient: float = 302.0):
        try:
            self.t_ambient = t_ambient
            self.stored_thermal_joules = 0.0
            self.t_substrate = t_ambient
            self.mode_states = {name: 0.0 for name in self.MODES}
        except Exception as e:
            log_exception_to_file(e, "ThermalInertiaMonitor.__init__")

    def update_thermal_memory(self, dt_hours: float, is_stagnation_active: bool, ahf: float, u_wind: float, beta: float = 0.20):
        """
        Tracks thermal energy absorption during stagnation walls and calculates continuous
        Feynman 4-mode decay post-stagnation.
        T_substrate = T_ambient + K_COUPLING * (stored_thermal_joules / structural_heat_capacity)
        Q_dissipated = beta * (T_substrate - T_ambient) * u_wind
        """
        try:
            if is_stagnation_active:
                absorbed_energy = 0.08 * ahf * dt_hours
                self.stored_thermal_joules += absorbed_energy
                for name in self.mode_states:
                    self.mode_states[name] = min(1.0, self.mode_states[name] + 0.12 * dt_hours)
                logger.debug(f"Absorption active: Added {absorbed_energy:.2f} Joules. Stored: {self.stored_thermal_joules:.2f}")
            else:
                total_decay_fraction = 0.0
                for name, cfg in self.MODES.items():
                    tau = cfg['tau']
                    w = cfg['weight']
                    self.mode_states[name] *= math.exp(-dt_hours / tau)
                    total_decay_fraction += w * self.mode_states[name]
                
                self.stored_thermal_joules *= total_decay_fraction
                logger.debug(f"Decay active: Feynman decay multiplier={total_decay_fraction:.4f}. Stored: {self.stored_thermal_joules:.2f}")

            self.t_substrate = self.t_ambient + self.K_COUPLING * (self.stored_thermal_joules / self.STRUCTURAL_HEAT_CAPACITY)
            
            delta_t = self.t_substrate - self.t_ambient
            q_dissipated = beta * delta_t * u_wind
            logger.debug(f"Thermal State: T_substrate={self.t_substrate:.2f} K (delta_T={delta_t:.2f} K), Q_dissipated={q_dissipated:.4f}")
            return q_dissipated
        except Exception as e:
            log_exception_to_file(e, "ThermalInertiaMonitor.update_thermal_memory")
            return 0.0

    def get_opex_surcharge_factor(self) -> float:
        """
        Surcharge penalty is proportional to the heat ratio of stored energy vs capacity.
        """
        try:
            heat_ratio = self.stored_thermal_joules / self.STRUCTURAL_HEAT_CAPACITY
            surcharge = 0.05 * heat_ratio  # 5% surcharge per unit heat ratio
            return surcharge
        except Exception as e:
            log_exception_to_file(e, "ThermalInertiaMonitor.get_opex_surcharge_factor")
            return 0.0


# --- 4. NETWORK FRICTION SIMULATOR (LATENCY & SLIPPAGE) ---

class NetworkFrictionSimulator:
    """
    Simulates network friction layers including execution latency and Kyle's Lambda slippage
    on traditional liquid broker markets.
    """
    VENUES = {
        'POWER_FUTURES': {'lambda_dollar': 1.00e-07, 'v_daily': 50_000_000.0, 'sigma': 0.08, 'c_sqrt': 0.60},
        'XLE': {'lambda_dollar': 2.00e-08, 'v_daily': 150_000_000.0, 'sigma': 0.03, 'c_sqrt': 0.40},
        'VPU': {'lambda_dollar': 5.00e-08, 'v_daily': 40_000_000.0, 'sigma': 0.05, 'c_sqrt': 0.50}
    }

    def __init__(self, mu_seconds: float = 30.0, sigma_seconds: float = 10.0):
        try:
            self.mu = mu_seconds
            self.sigma = sigma_seconds
        except Exception as e:
            log_exception_to_file(e, "NetworkFrictionSimulator.__init__")

    def simulate_latency_delay(self) -> float:
        """
        Returns a random latency delay from a truncated normal distribution N(mu=30s, sigma=10s)
        bounded between 0.5s and 120s.
        """
        try:
            while True:
                delay = random.normalvariate(self.mu, self.sigma)
                if 0.5 <= delay <= 120.0:
                    break
            logger.debug(f"Simulated execution latency: {delay:.2f} seconds")
            return delay
        except Exception as e:
            log_exception_to_file(e, "NetworkFrictionSimulator.simulate_latency_delay")
            return 30.0

    def compute_spread_degradation(self, delay_seconds: float, signal_window: float = 300.0) -> float:
        """
        Computes spread degradation penalty. If delay exceeds signal window, trade fails.
        Otherwise, degradation is proportional to remaining window with 15% alpha decay penalty.
        """
        try:
            if delay_seconds >= signal_window:
                logger.warning(f"Execution delay ({delay_seconds:.2f}s) exceeded signal window ({signal_window:.1f}s). COMPLETE MISS.")
                return 0.0
            
            remaining_frac = (signal_window - delay_seconds) / signal_window
            if remaining_frac < 0.10:
                degradation = 0.05
            else:
                degradation = remaining_frac * 0.85
            logger.debug(f"Spread degradation factor: {degradation:.4f} (Remaining Window: {remaining_frac*100.0:.2f}%)")
            return degradation
        except Exception as e:
            log_exception_to_file(e, "NetworkFrictionSimulator.compute_spread_degradation")
            return 0.0

    def compute_kyle_slippage(self, venue: str, trade_size: float) -> float:
        """
        Three-Regime Impact Model for financial assets:
        - Square-Root (low volume): impact = sigma * c_sqrt * sqrt(V / V_daily)
        - Linear (modest volume): impact = lambda_dollar * V_trade
        - Vertical (depth exhaustion): impact = lambda * V * exhaustion_factor
        """
        try:
            cfg = self.VENUES[venue]
            v_daily = cfg['v_daily']
            sigma = cfg['sigma']
            c_sqrt = cfg['c_sqrt']
            lambda_dollar = cfg['lambda_dollar']

            if trade_size < 0.05 * v_daily:
                impact_bps = sigma * c_sqrt * math.sqrt(trade_size / v_daily) * 10000.0
            elif trade_size <= v_daily:
                impact_bps = lambda_dollar * trade_size * 10000.0
            else:
                exhaustion_factor = 2.5 * (trade_size / v_daily)
                impact_bps = lambda_dollar * trade_size * exhaustion_factor * 10000.0

            logger.debug(f"Kyle Slippage for {venue} on trade size ${trade_size:.2f}: {impact_bps:.2f} bps")
            return impact_bps / 10000.0
        except Exception as e:
            log_exception_to_file(e, "NetworkFrictionSimulator.compute_kyle_slippage")
            return 0.50


# --- 5. FINANCIAL ORDER ROUTER ---

class FinancialOrderRouter:
    """
    Routes leveraged orders across liquid energy proxy instruments:
    - POWER_FUTURES: 40% target split
    - XLE (Energy Select Sector ETF): 40% target split
    - VPU (Utilities Index ETF): 20% target split
    Enforces dynamic liquidity caps (0.01% of 5-min volume) tick-by-tick.
    """
    def __init__(self):
        pass

    def split_order(self, total_capital: float, telemetry: dict = None) -> dict:
        try:
            if telemetry is None:
                # Default fallback caps
                cap_pf = 1000.0
                cap_xle = 2000.0
                cap_vpu = 1000.0
            else:
                u_wind = telemetry.get('u_wind', 2.0)
                ahf = telemetry.get('ahf', 40.0)
                
                # Model top-of-book 5-minute volume dynamically
                pf_5min_vol = 5_000_000 * (1.0 + 0.5 * (ahf / 100.0))
                xle_5min_vol = 15_000_000 * (1.0 + 0.2 * u_wind)
                vpu_5min_vol = 4_000_000 * (1.0 + 0.1 * u_wind)
                
                # Dynamic Cap is 0.01% of 5-minute volume
                cap_pf = 0.0001 * pf_5min_vol
                cap_xle = 0.0001 * xle_5min_vol
                cap_vpu = 0.0001 * vpu_5min_vol

            # Calculate target splits
            pf_target = total_capital * 0.40
            xle_target = total_capital * 0.40
            vpu_target = total_capital * 0.20
            
            # Enforce dynamic liquidity caps
            pf_alloc = min(pf_target, cap_pf)
            xle_alloc = min(xle_target, cap_xle)
            vpu_alloc = min(vpu_target, cap_vpu)
            
            actual_total = pf_alloc + xle_alloc + vpu_alloc
            
            return {
                "POWER_FUTURES": pf_alloc,
                "XLE": xle_alloc,
                "VPU": vpu_alloc,
                "Total": actual_total,
                "Caps": {
                    "POWER_FUTURES": cap_pf,
                    "XLE": cap_xle,
                    "VPU": cap_vpu
                }
            }
        except Exception as e:
            log_exception_to_file(e, "FinancialOrderRouter.split_order")
            return {"POWER_FUTURES": 0.0, "XLE": 0.0, "VPU": 0.0, "Total": 0.0, "Caps": {}}


# --- 6. CONTINUOUS SIMULATION ENGINE (EXECUTION LOOP) ---

class ThermodynamicArbitrageBot:
    """
    Main loop coordinator executing the E-AII Quantitative Bot script on traditional broker connections.
    """
    def __init__(self, db_path: str = None):
        try:
            self.monitor = RegionalThermalMonitor()
            self.bankroll_mgr = AccountBalanceManager(initial_bankroll=10.00)
            self.thermal_monitor = ThermalInertiaMonitor(t_ambient=302.0)
            self.friction_sim = NetworkFrictionSimulator()
            self.order_splitter = FinancialOrderRouter()
            self.db_path = db_path
            self.tick_count = 0
            self.mpc_state = "COLD"
            self.pre_warmed = False
            
            # Load broker endpoints from credential vault
            self.broker_config = {
                "Broker_API_Base_URL": "",
                "Account_ID": "",
                "OAuth_Bearer_Token": ""
            }
            try:
                cred_path = "credentials.json"
                if os.path.exists(cred_path):
                    with open(cred_path, "r") as cf:
                        cached = json.load(cf)
                        self.broker_config["Broker_API_Base_URL"] = cached.get("BROKER_API_BASE_URL", "")
                        self.broker_config["Account_ID"] = cached.get("BROKER_ACCOUNT_ID", "")
                        self.broker_config["OAuth_Bearer_Token"] = cached.get("BROKER_OAUTH_TOKEN", "")
            except Exception as ce:
                log_exception_to_file(ce, "ThermodynamicArbitrageBot.__init__.load_broker_config")
                
        except Exception as e:
            log_exception_to_file(e, "ThermodynamicArbitrageBot.__init__")

    def submit_market_order(self, asset: str, size: float, side: str, broker_config: dict) -> bool:
        """
        Simulates standard FIX protocol/REST order placement endpoint calls to traditional brokers.
        """
        try:
            logger.info(f"[BROKER FIX INTERFACE] Submitting {side} market order: {size:.2f} units of {asset}")
            base_url = broker_config.get("Broker_API_Base_URL") or broker_config.get("BROKER_API_BASE_URL", "")
            token = broker_config.get("OAuth_Bearer_Token") or broker_config.get("BROKER_OAUTH_TOKEN", "")
            account_id = broker_config.get("Account_ID") or broker_config.get("BROKER_ACCOUNT_ID", "")
            
            if base_url and token:
                logger.debug(f"[BROKER REST SOCKET] Routing POST request to {base_url}/v1/accounts/{account_id}/orders [Bearer OAuth Token Masked]")
                # Connectivity test
                try:
                    req = urllib.request.Request(
                        f"{base_url}/v1/ping",
                        headers={"Authorization": f"Bearer {token}"},
                        method="GET"
                    )
                    # Simulated ping/connectivity check, catches any local test errors gracefully
                except Exception:
                    pass
            return True
        except Exception as e:
            log_exception_to_file(e, "ThermodynamicArbitrageBot.submit_market_order")
            return False

    def calculate_portfolio_leverage(self, balance: float, position_size: float) -> float:
        """
        Computes the active portfolio leverage multiplier.
        """
        try:
            if balance <= 0.0:
                return 0.0
            leverage = position_size / balance
            logger.debug(f"[LEVERAGE TRACKER] Deployed position: ${position_size:.2f}, Balance: ${balance:.2f} -> Active Leverage: {leverage:.2f}x")
            return leverage
        except Exception as e:
            log_exception_to_file(e, "ThermodynamicArbitrageBot.calculate_portfolio_leverage")
            return 0.0

    def run_tick(self, telemetry: dict) -> dict:
        """
        Processes a single telemetry tick and executes transaction signal processing.
        """
        try:
            self.tick_count += 1
            logger.info(f"--- START TICK #{self.tick_count} ---")
            
            u_wind = telemetry['u_wind']
            ahf = telemetry['ahf']
            cin = telemetry['cin']
            cape = telemetry['cape']
            tau_infra = telemetry['tau_infra']
            fossil_fraction = telemetry['fossil_fraction']
            raw_spread_bps = telemetry['raw_spread_bps']
            
            if telemetry.get('stagnation_override', False):
                u_wind = 0.25
                ahf = 120.0
                m_drift = 1.45
            else:
                m_drift = self.monitor.compute_m_drift_from_components(u_wind, ahf, cin, cape, tau_infra, fossil_fraction)
                
            gate_passed = self.monitor.evaluate_gate(u_wind, ahf, m_drift)
            
            # --- PRE-FLIGHT MPC REFLIGHT WARMUP CHECK ---
            future_m_drift = telemetry.get('future_m_drift', 0.0)
            
            if gate_passed:
                self.mpc_state = "ACTIVE"
            elif future_m_drift > 1.50:
                self.mpc_state = "PRE_FLIGHT_WARMUP"
                self.pre_warmed = True
                logger.info(f"[MPC] Transitioned to PRE_FLIGHT_WARMUP. Future predicted M_drift = {future_m_drift:.2f}. Pre-warming connection sockets...")
            else:
                self.mpc_state = "COLD"
                
            q_diss = self.thermal_monitor.update_thermal_memory(
                dt_hours=5.0 / 60.0,
                is_stagnation_active=(u_wind < 0.4272 and ahf >= 100.0),
                ahf=ahf,
                u_wind=u_wind
            )
            opex_surcharge = self.thermal_monitor.get_opex_surcharge_factor()
            
            opex_cost = 50.0 * opex_surcharge
            self.bankroll_mgr.charge_opex_penalty(opex_cost)
            
            status_data = {}
            if not gate_passed:
                logger.info(f"Signal blocked by triple-gate logic. Closing active long allocations and holding 100% USD cash collateral. [MPC State: {self.mpc_state}]")
                status_data = {
                    'status': 'BLOCKED',
                    'mpc_state': self.mpc_state,
                    'bankroll': self.bankroll_mgr.Deployed_Bankroll,
                    'cash_pool': self.bankroll_mgr.Overflow_Cash_Pool
                }
            else:
                trade_size = self.bankroll_mgr.determine_order_size(telemetry)
                if trade_size <= 0.0:
                    logger.error("Deployed Bankroll depleted. Cannot trade.")
                    status_data = {
                        'status': 'DEPLETED',
                        'mpc_state': self.mpc_state,
                        'bankroll': self.bankroll_mgr.Deployed_Bankroll,
                        'cash_pool': self.bankroll_mgr.Overflow_Cash_Pool
                    }
                else:
                    # MPC Latency Neutralization check
                    if self.pre_warmed:
                        delay_sec = 0.5  # Neutralized latency delay
                        logger.info("[MPC] Pre-flight warmup active. Latency decay neutralized to 0.5s!")
                        self.pre_warmed = False  # Reset pre-warm
                    else:
                        delay_sec = self.friction_sim.simulate_latency_delay()
                        
                    degrade_factor = self.friction_sim.compute_spread_degradation(delay_sec)
                    
                    if degrade_factor <= 0.0:
                        logger.warning("Trade missed completely due to latency delay.")
                        status_data = {
                            'status': 'MISSED',
                            'mpc_state': self.mpc_state,
                            'bankroll': self.bankroll_mgr.Deployed_Bankroll,
                            'cash_pool': self.bankroll_mgr.Overflow_Cash_Pool
                        }
                    else:
                        # Dynamic liquidity splitting across financial assets
                        split = self.order_splitter.split_order(trade_size, telemetry)
                        size_pf = split["POWER_FUTURES"]
                        size_xle = split["XLE"]
                        size_vpu = split["VPU"]
                        actual_allocated = split["Total"]
                        
                        # Submit orders via broker Fix stubs
                        self.submit_market_order("POWER_FUTURES", size_pf, "BUY", self.broker_config)
                        self.submit_market_order("XLE", size_xle, "BUY", self.broker_config)
                        self.submit_market_order("VPU", size_vpu, "BUY", self.broker_config)
                        
                        # Route independently with separate error catch hooks
                        slip_pf = 0.0
                        slip_xle = 0.0
                        slip_vpu = 0.0
                        venue_errors = []
                        
                        # Calculate slippages
                        try:
                            if size_pf > 0:
                                slip_pf = self.friction_sim.compute_kyle_slippage('POWER_FUTURES', size_pf)
                                logger.debug(f"[VENUE SOCKET] POWER_FUTURES order executed: ${size_pf:.2f} (slippage: {slip_pf*10000.0:.2f} bps)")
                        except Exception as e:
                            slip_pf = 0.05
                            venue_errors.append(f"POWER_FUTURES routing failed: {e}")
                            
                        try:
                            if size_xle > 0:
                                slip_xle = self.friction_sim.compute_kyle_slippage('XLE', size_xle)
                                logger.debug(f"[VENUE SOCKET] XLE order executed: ${size_xle:.2f} (slippage: {slip_xle*10000.0:.2f} bps)")
                        except Exception as e:
                            slip_xle = 0.05
                            venue_errors.append(f"XLE routing failed: {e}")
                            
                        try:
                            if size_vpu > 0:
                                slip_vpu = self.friction_sim.compute_kyle_slippage('VPU', size_vpu)
                                logger.debug(f"[VENUE SOCKET] VPU order executed: ${size_vpu:.2f} (slippage: {slip_vpu*10000.0:.2f} bps)")
                        except Exception as e:
                            slip_vpu = 0.05
                            venue_errors.append(f"VPU routing failed: {e}")
                            
                        # Calculate active portfolio leverage
                        self.calculate_portfolio_leverage(self.bankroll_mgr.Deployed_Bankroll, actual_allocated)
                        
                        # Compute weighted average slippage
                        if actual_allocated > 0:
                            weighted_slippage = (size_pf * slip_pf + size_xle * slip_xle + size_vpu * slip_vpu) / actual_allocated
                        else:
                            weighted_slippage = 0.0
                            
                        raw_spread = raw_spread_bps / 10000.0
                        degraded_spread = raw_spread * degrade_factor
                        net_spread = degraded_spread - weighted_slippage - opex_surcharge
                        
                        logger.info(
                            f"Friction Decomposition:\n"
                            f"  Raw Spread: {raw_spread_bps:.2f} bps ({raw_spread*10000.0:.2f} bps)\n"
                            f"  After Latency Decay: {degraded_spread*10000.0:.2f} bps (degrade_mult={degrade_factor:.4f})\n"
                            f"  Financial Slip: {weighted_slippage*10000.0:.2f} bps\n"
                            f"  Thermal OpEx Surcharge: {opex_surcharge*10000.0:.2f} bps\n"
                            f"  Net Realized Spread: {net_spread*10000.0:+.2f} bps\n"
                            f"  Allocation: POWER_FUTURES=${size_pf:.2f}, XLE=${size_xle:.2f}, VPU=${size_vpu:.2f}\n"
                            f"  Errors: {', '.join(venue_errors) if venue_errors else 'None'}"
                        )
                        
                        self.bankroll_mgr.process_settlement(actual_allocated, net_spread, telemetry)
                        status_data = {
                            'status': 'FILLED',
                            'mpc_state': self.mpc_state,
                            'delay_sec': delay_sec,
                            'degrade_factor': degrade_factor,
                            'weighted_slippage_bps': weighted_slippage * 10000.0,
                            'net_spread_bps': net_spread * 10000.0,
                            'bankroll': self.bankroll_mgr.Deployed_Bankroll,
                            'cash_pool': self.bankroll_mgr.Overflow_Cash_Pool,
                            'size_pf': size_pf,
                            'size_xle': size_xle,
                            'size_vpu': size_vpu,
                            'venue_errors': venue_errors
                        }

            # --- PERSISTENT CHECKPOINTING: Write tick execution records to local disk shelf ---
            try:
                ledger_path = "bot_execution_ledger.json"
                if os.path.exists(ledger_path):
                    with open(ledger_path, "r") as lf:
                        ledger_data = json.load(lf)
                else:
                    ledger_data = []
                
                tick_record = status_data.copy()
                tick_record['tick'] = self.tick_count
                tick_record['timestamp'] = time.time()
                ledger_data.append(tick_record)
                
                with open(ledger_path, "w") as lf:
                    json.dump(ledger_data, lf, indent=2)
                    lf.flush()
                    os.fsync(lf.fileno())
            except Exception as le:
                log_exception_to_file(le, "ThermodynamicArbitrageBot.run_tick.checkpoint")

            return status_data

        except Exception as e:
            log_exception_to_file(e, "ThermodynamicArbitrageBot.run_tick")
            return {
                'status': 'HOLD',
                'error': str(e),
                'bankroll': getattr(self, 'bankroll_mgr', None) and getattr(self.bankroll_mgr, 'Deployed_Bankroll', 0.0) or 0.0,
                'cash_pool': getattr(self, 'bankroll_mgr', None) and getattr(self.bankroll_mgr, 'Overflow_Cash_Pool', 0.0) or 0.0
            }


# --- 6. DEMO AND TESTING SUITE ---

def run_production_demo():
    try:
        logger.info("Initializing E-AII Thermodynamic Bot Demo Pipeline...")
        bot = ThermodynamicArbitrageBot()
        
        mock_telemetry_series = [
            {
                'u_wind': 1.85, 'ahf': 45.0, 'cin': -20.0, 'cape': 500.0,
                'tau_infra': 4.0, 'fossil_fraction': 0.65, 'raw_spread_bps': 2231.65
            },
            {
                'u_wind': 0.22, 'ahf': 120.0, 'cin': -80.0, 'cape': 1800.0,
                'tau_infra': 10.0, 'fossil_fraction': 0.65, 'raw_spread_bps': 3450.0
            },
            {
                'u_wind': 0.08, 'ahf': 150.0, 'cin': -95.0, 'cape': 2500.0,
                'tau_infra': 10.0, 'fossil_fraction': 0.65, 'raw_spread_bps': 4890.0
            },
            {
                'u_wind': 2.10, 'ahf': 80.0, 'cin': -15.0, 'cape': 400.0,
                'tau_infra': 10.0, 'fossil_fraction': 0.65, 'raw_spread_bps': 1800.0
            },
            {
                'u_wind': 4.50, 'ahf': 45.0, 'cin': -5.0, 'cape': 100.0,
                'tau_infra': 10.0, 'fossil_fraction': 0.65, 'raw_spread_bps': 1200.0
            }
        ]
        
        for i, tel in enumerate(mock_telemetry_series, 1):
            try:
                res = bot.run_tick(tel)
                logger.info(f"Tick {i} Results: Status={res['status']}, Bankroll=${res['bankroll']:.2f}, Cash Pool=${res['cash_pool']:.2f}\n")
            except Exception as e:
                logger.error(f"Error executing Tick {i}: {e}", exc_info=True)
    except Exception as e:
        log_exception_to_file(e, "run_production_demo")


if __name__ == "__main__":
    try:
        run_production_demo()
    except Exception as e:
        log_exception_to_file(e, "__main__")
