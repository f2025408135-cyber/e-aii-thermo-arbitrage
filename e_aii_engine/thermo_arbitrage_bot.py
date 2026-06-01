"""
E-AII Thermodynamic Arbitrage Production Bot Script.
Natively built according to E-AII Alpha Validation Report specifications.
Tracks trailing climate vectors, implements triple-gate logic, dual-account balance sweep mechanics,
Feynman 4-mode thermal decay overhang, and stochastic network execution latency delays.
"""

import sys
import os
import time
import math
import random
import logging
import traceback
import json

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
                # Fallback to local error logging if write permissions allow
                try:
                    with open("bot_runtime_error.log", "a") as f:
                        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Auto-install failed for {pkg}: {e}\n")
                except Exception:
                    pass

# Execute auto-installer silently at absolute top of the script
auto_install_dependencies()

# Import dependencies after installer execution
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
    Applies the $4,000 safety position size cap and automatically sweeps settlement profits.
    """
    MAX_TRADE_SIZE = 4000.00

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

    def determine_order_size(self) -> float:
        """
        Safety cap: If Deployed_Bankroll >= 4000.00, maximum allocation is flat locked at $4,000.00.
        Otherwise, allocate the entire Deployed_Bankroll.
        """
        try:
            if self.Deployed_Bankroll >= self.MAX_TRADE_SIZE:
                size = self.MAX_TRADE_SIZE
            else:
                size = self.Deployed_Bankroll
            logger.debug(f"Allocating trade size: ${size:.2f} (Bankroll: ${self.Deployed_Bankroll:.2f})")
            return size
        except Exception as e:
            log_exception_to_file(e, "AccountBalanceManager.determine_order_size")
            return 0.0

    def process_settlement(self, allocated_size: float, net_return_pct: float):
        """
        Slices all settlement profits off the trade and routes them to the Overflow_Cash_Pool.
        If there's a loss, it reduces the Deployed_Bankroll.
        """
        try:
            gross_pnl = allocated_size * net_return_pct
            logger.info(f"Trade settled. Allocated Size: ${allocated_size:.2f}, Net Return: {net_return_pct*100.0:+.4f}% -> Gross PnL: ${gross_pnl:+.4f}")
            
            if gross_pnl > 0.0:
                temp_bankroll = self.Deployed_Bankroll + gross_pnl
                if temp_bankroll > self.MAX_TRADE_SIZE:
                    if self.Deployed_Bankroll < self.MAX_TRADE_SIZE:
                        added_to_bankroll = self.MAX_TRADE_SIZE - self.Deployed_Bankroll
                        sweep_amount = temp_bankroll - self.MAX_TRADE_SIZE
                        self.Deployed_Bankroll = self.MAX_TRADE_SIZE
                    else:
                        added_to_bankroll = 0.0
                        sweep_amount = gross_pnl
                    self.Overflow_Cash_Pool += sweep_amount
                    logger.info(f"Sweep executed: ${sweep_amount:.4f} routed to Overflow_Cash_Pool. Bankroll locked at ${self.Deployed_Bankroll:.2f}")
                else:
                    self.Deployed_Bankroll = temp_bankroll
                    logger.info(f"No sweep: Bankroll increased to ${self.Deployed_Bankroll:.2f} (under cap)")
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
    Simulates network friction layers including execution latency and Kyle's Lambda slippage.
    """
    VENUES = {
        'RENDER': {'lambda_dollar': 5.00e-08, 'v_daily': 30_000_000.0, 'sigma': 0.05, 'c_sqrt': 0.50},
        'Vast.ai': {'lambda_dollar': 5.00e-05, 'v_daily': 100_000.0, 'sigma': 0.25, 'c_sqrt': 2.00}
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
        Three-Regime Impact Model:
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


# --- 5. CONTINUOUS SIMULATION ENGINE (EXECUTION LOOP) ---

class ThermodynamicArbitrageBot:
    """
    Main loop coordinator executing the E-AII Quantitative Bot script.
    """
    def __init__(self, db_path: str = None):
        try:
            self.monitor = RegionalThermalMonitor()
            self.bankroll_mgr = AccountBalanceManager(initial_bankroll=10.00)
            self.thermal_monitor = ThermalInertiaMonitor(t_ambient=302.0)
            self.friction_sim = NetworkFrictionSimulator()
            self.db_path = db_path
            self.tick_count = 0
        except Exception as e:
            log_exception_to_file(e, "ThermodynamicArbitrageBot.__init__")

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
                logger.info("Signal blocked by triple-gate logic. No trade routed.")
                status_data = {'status': 'BLOCKED', 'bankroll': self.bankroll_mgr.Deployed_Bankroll, 'cash_pool': self.bankroll_mgr.Overflow_Cash_Pool}
            else:
                trade_size = self.bankroll_mgr.determine_order_size()
                if trade_size <= 0.0:
                    logger.error("Deployed Bankroll depleted. Cannot trade.")
                    status_data = {'status': 'DEPLETED', 'bankroll': self.bankroll_mgr.Deployed_Bankroll, 'cash_pool': self.bankroll_mgr.Overflow_Cash_Pool}
                else:
                    delay_sec = self.friction_sim.simulate_latency_delay()
                    degrade_factor = self.friction_sim.compute_spread_degradation(delay_sec)
                    
                    if degrade_factor <= 0.0:
                        logger.warning("Trade missed completely due to latency delay.")
                        status_data = {'status': 'MISSED', 'bankroll': self.bankroll_mgr.Deployed_Bankroll, 'cash_pool': self.bankroll_mgr.Overflow_Cash_Pool}
                    else:
                        size_render = trade_size * 0.70
                        size_vast = trade_size * 0.30
                        
                        slip_render = self.friction_sim.compute_kyle_slippage('RENDER', size_render)
                        slip_vast = self.friction_sim.compute_kyle_slippage('Vast.ai', size_vast)
                        
                        weighted_slippage = 0.70 * slip_render + 0.30 * slip_vast
                        raw_spread = raw_spread_bps / 10000.0
                        degraded_spread = raw_spread * degrade_factor
                        net_spread = degraded_spread - weighted_slippage - opex_surcharge
                        
                        logger.info(
                            f"Friction Decomposition:\n"
                            f"  Raw Spread: {raw_spread_bps:.2f} bps ({raw_spread*10000.0:.2f} bps)\n"
                            f"  After Latency Decay: {degraded_spread*10000.0:.2f} bps (degrade_mult={degrade_factor:.4f})\n"
                            f"  Weighted Venue Slippage: {weighted_slippage*10000.0:.2f} bps\n"
                            f"  Thermal OpEx Surcharge: {opex_surcharge*10000.0:.2f} bps\n"
                            f"  Net Realized Spread: {net_spread*10000.0:+.2f} bps"
                        )
                        
                        self.bankroll_mgr.process_settlement(trade_size, net_spread)
                        status_data = {
                            'status': 'FILLED',
                            'delay_sec': delay_sec,
                            'degrade_factor': degrade_factor,
                            'weighted_slippage_bps': weighted_slippage * 10000.0,
                            'net_spread_bps': net_spread * 10000.0,
                            'bankroll': self.bankroll_mgr.Deployed_Bankroll,
                            'cash_pool': self.bankroll_mgr.Overflow_Cash_Pool
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
            # Code Extractor & Exception catching: Gracefully return to a HOLD state rather than crashing
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
