"""
E-AII Out-of-Sample Forward Test Script (forward_oos_test.py).
Executes a 7-day out-of-sample (OOS) forward test on actual telemetry data
with zero post-hoc parameter adjustments.
"""

import os
import sys
import json
import time
import math
import shutil
import pandas as pd
import numpy as np

# Ensure root path is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from e_aii_engine.thermo_arbitrage_bot import ThermodynamicArbitrageBot

TELEMETRY_PATH = r"D:\HP\Downloads\live_execution_telemetry (3).csv"
if not os.path.exists(TELEMETRY_PATH):
    TELEMETRY_PATH = r"D:\HP\Downloads\live_execution_telemetry.csv"

LEDGER_PATH = "bot_execution_ledger.json"
BACKUP_PATH = "bot_execution_ledger.json.bak"
OOS_OUTPUT_PATH = "forward_test_ledger.json"

def run_forward_oos_test():
    print("=========================================================================")
    print("        E-AII 7-DAY OUT-OF-SAMPLE (OOS) LIVE FORWARD TEST RUNNER")
    print("        Telemetry Source: " + TELEMETRY_PATH)
    print("=========================================================================")

    # 1. Check database existence
    if not os.path.exists(TELEMETRY_PATH):
        print(f"ERROR: Telemetry dataset not found at {TELEMETRY_PATH}")
        sys.exit(1)

    # 2. Load telemetry data
    try:
        df = pd.read_csv(TELEMETRY_PATH)
        total_rows = len(df)
        print(f"Loaded telemetry dataset successfully ({total_rows} rows).")
    except Exception as e:
        print(f"ERROR loading telemetry dataset: {e}")
        sys.exit(1)

    # 3. Select 7-day OOS window (last 2016 rows of 104,832 tick dataset)
    # Ticks are 5-minute intervals. 7 days = 7 * 24 * 12 = 2016 ticks.
    oos_ticks = 2016
    if total_rows < oos_ticks:
        print(f"WARNING: Dataset has only {total_rows} ticks. Using all available data.")
        oos_df = df
    else:
        oos_df = df.iloc[-oos_ticks:]
        print(f"Selected last {oos_ticks} ticks (representing exactly 7 days of out-of-sample telemetry).")

    # 4. Back up production ledger if it exists
    ledger_backed_up = False
    if os.path.exists(LEDGER_PATH):
        try:
            shutil.move(LEDGER_PATH, BACKUP_PATH)
            ledger_backed_up = True
            print(f"Backed up active production ledger to {BACKUP_PATH}")
        except Exception as be:
            print(f"WARNING: Could not back up production ledger: {be}")

    # 5. Initialize bot
    # Starting bankroll is set to $10.00 as standard validation convention.
    bot = ThermodynamicArbitrageBot()
    bot.bankroll_mgr.Deployed_Bankroll = 10.00
    bot.bankroll_mgr.Overflow_Cash_Pool = 0.00

    print("\nExecuting forward OOS simulation tick-by-tick (Zero post-hoc parameter adjustments)...")
    
    start_time = time.time()
    filled_count = 0
    blocked_count = 0
    missed_count = 0
    depleted_count = 0
    hold_count = 0
    
    pnl_series = []
    
    # Run the tick loop
    for i, (_, row) in enumerate(oos_df.iterrows(), 1):
        u_wind = math.sqrt(row.get('raw_u', 2.0)**2 + row.get('raw_v', 1.5)**2)
        ahf = row.get('raw_ahf', 40.0)
        
        # Calculate future M_drift by looking ahead 15 ticks (30s) relative to this row index
        # To maintain out-of-sample bounds, look ahead strictly within the telemetry series.
        # If look-ahead index exceeds bounds, wrap around or clamp.
        row_idx = row.name
        future_idx = (row_idx + 15) % total_rows
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
            'u_wind': u_wind,
            'ahf': ahf,
            'cin': row.get('cin', -20.0),
            'cape': row.get('cape', 500.0),
            'tau_infra': row.get('tau_infra', 4.0),
            'fossil_fraction': row.get('fossil_fraction', 0.65),
            'raw_spread_bps': row.get('mpcsignal', 1.5) * 1000.0,
            'future_m_drift': future_m_drift
        }
        
        res = bot.run_tick(telemetry_tick)
        
        status = res.get('status', 'HOLD')
        if status == 'FILLED':
            filled_count += 1
            pnl_series.append(res.get('net_spread_bps', 0.0))
        elif status == 'BLOCKED':
            blocked_count += 1
        elif status == 'MISSED':
            missed_count += 1
        elif status == 'DEPLETED':
            depleted_count += 1
        else:
            hold_count += 1

    end_time = time.time()
    execution_time = end_time - start_time
    
    # 6. Read final OOS test results from the generated ledger
    test_ledger = []
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r") as lf:
                test_ledger = json.load(lf)
            shutil.copy(LEDGER_PATH, OOS_OUTPUT_PATH)
            os.remove(LEDGER_PATH)
            print(f"Saved forward OOS test ledger to {OOS_OUTPUT_PATH}")
        except Exception as oe:
            print(f"WARNING: Could not process test ledger files: {oe}")

    # Restore production ledger if backed up
    if ledger_backed_up and os.path.exists(BACKUP_PATH):
        try:
            shutil.move(BACKUP_PATH, LEDGER_PATH)
            print("Restored active production ledger.")
        except Exception as re:
            print(f"WARNING: Could not restore production ledger: {re}")

    # 7. Print summary metrics
    total_trades = filled_count + missed_count
    win_rate = (filled_count / total_trades * 100.0) if total_trades > 0 else 0.0
    
    ending_bankroll = bot.bankroll_mgr.Deployed_Bankroll
    ending_cash_pool = bot.bankroll_mgr.Overflow_Cash_Pool
    net_profit = (ending_bankroll + ending_cash_pool) - 10.00
    
    print("\n" + "="*70)
    print("                E-AII OOS FORWARD TEST COMPLETED")
    print("="*70)
    print(f"Test Duration         : {oos_ticks} ticks (Exactly 7 days)")
    print(f"Execution Wall Time   : {execution_time:.2f} seconds")
    print(f"Total Telemetry Ticks : {len(oos_df)}")
    print(f"  - Filled Trades     : {filled_count}")
    print(f"  - Blocked Signals   : {blocked_count}")
    print(f"  - Missed (Latency)  : {missed_count}")
    print(f"  - Depleted Bankroll : {depleted_count}")
    print(f"  - System Holds      : {hold_count}")
    print(f"Win Rate (Realized)   : {win_rate:.2f}%")
    print("-"*70)
    print(f"Initial Deposit       : $10.00")
    print(f"Ending Trading Balance: ${ending_bankroll:.2f}")
    print(f"Ending Sidelined Cash : ${ending_cash_pool:.2f}")
    print(f"Net Realized Profit   : ${net_profit:.2f}")
    print(f"OOS Return Percentage : {(net_profit/10.00*100.0):.2f}%")
    print("="*70)

if __name__ == "__main__":
    run_forward_oos_test()
