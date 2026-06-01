import os
import json
import numpy as np
import pandas as pd

def run_backtest():
    print("=========================================================================")
    print("      E-AII TRADITIONAL ASSET PIVOT HISTORICAL BACKTEST ENGINE")
    print("=========================================================================\n")
    
    # 1. Historical Ingestion
    telemetry_path = r"D:\HP\Downloads\live_execution_telemetry (3).csv"
    if not os.path.exists(telemetry_path):
        telemetry_path = r"D:\HP\Downloads\live_execution_telemetry.csv"
        
    if not os.path.exists(telemetry_path):
        print(f"ERROR: Telemetry dataset not found at {telemetry_path}")
        return
        
    df = pd.read_csv(telemetry_path)
    total_ticks = len(df)
    print(f"Loaded telemetry dataset: {telemetry_path} ({total_ticks} rows).\n")
    
    # Compute u_wind and filter signals
    u_wind = np.sqrt(df['raw_u']**2 + df['raw_v']**2)
    mask = (u_wind < 1.5) & (df['raw_ahf'] >= 55.0)
    indices = df[mask].index.tolist()
    total_signals = len(indices)
    print(f"Total Signals Generated (Relaxed Gate: wind < 1.5m/s, AHF >= 55W/m²): {total_signals}\n")
    
    if total_signals == 0:
        print("No signals matched the filter criteria.")
        return
        
    # Asset Pricing models based on mpcsignal (spread proxy)
    # POWER_FUTURES: more volatile
    price_pf = lambda mpc: 100.0 * (1.0 + mpc / 50.0)
    # XLE ETF: less volatile
    price_xle = lambda mpc: 100.0 * (1.0 + mpc / 100.0)
    
    # Transaction Frictions
    broker_fee_pct = 0.0005  # 0.05% per transaction
    spread_slippage_pct = 0.0001  # 1 tick = 0.01%
    # Two transactions per position (enter + exit)
    total_friction_pct = 2 * (broker_fee_pct + spread_slippage_pct)  # 0.12% total
    
    # Windows
    # 30 minutes = 60 ticks (30s intervals)
    # 2 hours = 240 ticks
    windows = {
        '30m': 60,
        '2h': 240
    }
    
    backtest_report = {
        'total_signals': total_signals,
        'frictions': {
            'broker_fee_pct': broker_fee_pct,
            'spread_slippage_pct': spread_slippage_pct,
            'total_friction_pct': total_friction_pct
        },
        'results': {}
    }
    
    for w_name, w_ticks in windows.items():
        trade_results = []
        
        for idx in indices:
            # Check boundary limits
            if idx + w_ticks >= total_ticks:
                continue
                
            mpc_entry = df.loc[idx, 'mpcsignal']
            mpc_exit = df.loc[idx + w_ticks, 'mpcsignal']
            
            p_pf_entry = price_pf(mpc_entry)
            p_pf_exit = price_pf(mpc_exit)
            
            p_xle_entry = price_xle(mpc_entry)
            p_xle_exit = price_xle(mpc_exit)
            
            # Raw returns
            r_pf = (p_pf_exit - p_pf_entry) / p_pf_entry
            r_xle = (p_xle_exit - p_xle_entry) / p_xle_entry
            
            # Net returns after frictions
            net_r_pf = r_pf - total_friction_pct
            net_r_xle = r_xle - total_friction_pct
            
            # 100x Leveraged Returns
            lev_r_pf = net_r_pf * 100.0
            lev_r_xle = net_r_xle * 100.0
            
            # Portfolio allocation: 50% POWER_FUTURES, 50% XLE
            lev_r_port = 0.5 * lev_r_pf + 0.5 * lev_r_xle
            
            trade_results.append({
                'POWER_FUTURES': lev_r_pf,
                'XLE': lev_r_xle,
                'Portfolio': lev_r_port
            })
            
        res_df = pd.DataFrame(trade_results)
        
        backtest_report['results'][w_name] = {
            'trades_executed': len(res_df)
        }
        
        print(f"--- HOLDING PERIOD: {w_name.upper()} ({w_ticks} TICKS / {w_name}) ---")
        print(f"Trades Evaluated: {len(res_df)}")
        print("-" * 80)
        print(f"{'Asset/Portfolio':<20} | {'Win Rate':<10} | {'Profit Factor':<15} | {'Max Drawdown':<15}")
        print("-" * 80)
        
        for col in res_df.columns:
            trades = res_df[col]
            wins = (trades > 0).sum()
            win_rate = wins / len(trades) if len(trades) > 0 else 0.0
            
            gross_profits = trades[trades > 0].sum()
            gross_losses = abs(trades[trades < 0].sum())
            profit_factor = gross_profits / gross_losses if gross_losses > 0 else (float('inf') if gross_profits > 0 else 1.0)
            
            # Drawdown Calculation (Compounding Cash Balance starting at $10.00)
            equity = 10.00
            eq_series = [equity]
            for r in trades:
                equity *= (1.0 + r)
                # Fail-safe liquidation
                if equity <= 0.0:
                    equity = 0.0
                eq_series.append(equity)
                
            peaks = np.maximum.accumulate(eq_series)
            drawdowns = (peaks - eq_series) / np.where(peaks > 0, peaks, 1.0)
            max_dd = drawdowns.max() * 100.0
            
            pf_str = f"{profit_factor:.2f}" if profit_factor != float('inf') else "INF"
            print(f"{col:<20} | {win_rate*100.0:<8.2f}% | {pf_str:<15} | {max_dd:<13.2f}%")
            
            backtest_report['results'][w_name][col] = {
                'win_rate': float(win_rate),
                'profit_factor': float(profit_factor) if profit_factor != float('inf') else "INF",
                'max_drawdown': float(max_dd)
            }
        print("=" * 80 + "\n")
        
    # Write report JSON
    report_json_path = "broker_pivot_backtest_report.json"
    with open(report_json_path, "w") as rf:
        json.dump(backtest_report, rf, indent=2)
    print(f"Backtesting metrics logged successfully to {os.path.abspath(report_json_path)}")

if __name__ == "__main__":
    run_backtest()
