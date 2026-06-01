"""
E-AII Headless Terminal Agent.
Executes trailing telemetry scans, enforces TEMA filters, and runs multi-day background loops.
Optimized for memory with explicit garbage collection and zero UI library overhead.
"""

import sys
import os
import time
import math
import gc
import socket
import json
import traceback
import subprocess

# --- 0. PIP DEPENDENCY AUTO-INSTALLER ---
def auto_install_dependencies():
    required_packages = ['scipy', 'pandas', 'boto3', 'numpy']
    for pkg in required_packages:
        try:
            __import__(pkg)
        except ImportError:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet"])
            except Exception as e:
                try:
                    with open("terminal_runtime_error.log", "a") as f:
                        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Auto-install failed for {pkg}: {e}\n")
                except Exception:
                    pass

auto_install_dependencies()

import pandas as pd
import numpy as np

# Load local components
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from e_aii_engine.thermo_arbitrage_bot import ThermodynamicArbitrageBot


def print_ascii_table_header():
    border = "+" + "-"*21 + "+" + "-"*13 + "+" + "-"*15 + "+" + "-"*17 + "+" + "-"*20 + "+" + "-"*15 + "+"
    header = "| {:<19} | {:<11} | {:<13} | {:<15} | {:<18} | {:<13} |".format(
        "TIMESTAMP", "GATE_STATUS", "TEMA_SIGNAL", "CURRENT_ERROR", "ALLOCATION_CEILING", "SWEEP_STATE"
    )
    print(border)
    print(header)
    print(border)

def print_ascii_row(timestamp, gate_status, tema_signal, current_error, allocation_ceiling, sweep_state):
    row_str = "| {:<19} | {:<11} | {:<13} | {:<15} | ${:<17,.2f} | ${:<12,.2f} |".format(
        timestamp, gate_status, tema_signal, current_error, allocation_ceiling, sweep_state
    )
    print(row_str)
    # Flush stdout to ensure real-time visibility in terminal logs
    sys.stdout.flush()

def run_headless_agent():
    print("=========================================================================")
    print("           E-AII HEADLESS TERMINAL TRADING AGENT INITIALIZING")
    print("=========================================================================")
    
    # Ingest historical data
    telemetry_path = r"D:\HP\Downloads\live_execution_telemetry (3).csv"
    if not os.path.exists(telemetry_path):
        telemetry_path = r"D:\HP\Downloads\live_execution_telemetry.csv"
        
    try:
        df = pd.read_csv(telemetry_path)
        num_rows = len(df)
        print(f"Loaded telemetry dataset successfully: {telemetry_path} ({num_rows} rows).")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to load telemetry dataset: {e}")
        return

    # Initialize bot
    bot = ThermodynamicArbitrageBot()
    idx = 0
    tick_count = 0
    
    print_ascii_table_header()
    
    # Main Daemon loop with socket fail-safe re-warming
    while True:
        try:
            # Process single tick
            row = df.iloc[idx].to_dict()
            idx = (idx + 1) % num_rows
            tick_count += 1
            
            # Formulate environmental inputs
            telemetry_tick = {
                'u_wind': math.sqrt(row.get('raw_u', 2.0)**2 + row.get('raw_v', 1.5)**2),
                'ahf': row.get('raw_ahf', 40.0),
                'cin': row.get('cin', -20.0),
                'cape': row.get('cape', 500.0),
                'tau_infra': row.get('tau_infra', 4.0),
                'fossil_fraction': row.get('fossil_fraction', 0.65),
                'raw_spread_bps': row.get('mpcsignal', 1.5) * 1000.0
            }
            
            # Execute step on the defensive bot engine
            res = bot.run_tick(telemetry_tick)
            
            # Construct ASCII display variables
            t_stamp = time.strftime("%Y-%m-%d %H:%M:%S")
            g_status = res.get('status', 'HOLD')
            t_sig = "{:.2f} bps".format(res.get('net_spread_bps', 0.0)) if g_status == 'FILLED' else 'NONE'
            c_err = res.get('error', 'NONE')[:15]
            alloc_ceil = res.get('bankroll', bot.bankroll_mgr.Deployed_Bankroll)
            sweep_state = res.get('cash_pool', bot.bankroll_mgr.Overflow_Cash_Pool)
            
            print_ascii_row(t_stamp, g_status, t_sig, c_err, alloc_ceil, sweep_state)
            
            # Memory Optimization: Explicit garbage collection to prevent leaks over long windows
            gc.collect()
            
            # Sleep for exactly 30 seconds between telemetry checks
            time.sleep(30.0)
            
        except Exception as e:
            # Daemon fail-safe socket re-warming and exception trapping
            try:
                with open("terminal_runtime_error.log", "a") as f:
                    f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] --- DAEMON ERROR INTERRUPT ---\n")
                    traceback.print_exc(file=f)
                    f.flush()
            except Exception:
                pass
                
            print(f"\n[DAEMON WARNING] Exception caught: {e}. Initiating socket re-warm sequence...")
            
            # Simulate socket re-warming by creating a test connection to Vast.ai API / local target
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5.0)
                # Test connection to deep space (google dns / standard gateway port) to re-warm network stack
                s.connect(("8.8.8.8", 53))
                s.close()
                print("[DAEMON INFO] Socket re-warmed and network connectivity verified successfully.")
            except Exception as conn_err:
                print(f"[DAEMON WARNING] Socket re-warming failed: {conn_err}. Continuing anyway.")
            
            # Enforce the exactly 15 seconds pause before resuming operations
            time.sleep(15.0)


if __name__ == "__main__":
    try:
        run_headless_agent()
    except KeyboardInterrupt:
        print("\nHeadless agent stopped manually via KeyboardInterrupt.")
    except Exception as e:
        try:
            with open("terminal_runtime_error.log", "a") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CRITICAL MAIN EXIT: {e}\n")
        except Exception:
            pass
        print(f"CRITICAL MAIN FAILURE: {e}")
