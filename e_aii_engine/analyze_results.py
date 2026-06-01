"""
Analysis and visualization script for E-AII Empirical Test Sweeps.
Processes the multi-dimensional sweep data, prints diagnostic insights,
and generates feasibility curves mapping the project Feasibility and Ghost Zones.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def analyze_sweep_data():
    csv_file = "empirical_test_results.csv"
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"Missing sweep data. Please run empirical_sweep.py first.")
        
    df = pd.read_csv(csv_file)
    
    total_runs = len(df)
    locked_count = df['gated_lock'].sum()
    unlocked_count = total_runs - locked_count
    
    indefinite_locks = (df['timeline_penalty'] == -1).sum()
    recoverable_locks = locked_count - indefinite_locks
    
    avg_penalty = df[df['timeline_penalty'] > 0]['timeline_penalty'].mean()
    
    print("\n=========================================================================")
    print("               EMPIRICAL PARAMETER SWEEP STATISTICAL REPORT")
    print("=========================================================================")
    print(f"Total Parameter Combinations Tested : {total_runs}")
    print(f"Unlocked Configurations (IRR >= 25%): {unlocked_count} ({unlocked_count/total_runs*100:.2f}%)")
    print(f"Locked Configurations (IRR < 25%)   : {locked_count} ({locked_count/total_runs*100:.2f}%)")
    print(f"  - Recoverable via Timeline Delay  : {recoverable_locks} ({recoverable_locks/total_runs*100:.2f}%)")
    print(f"  - Indefinitely/Permanently Locked : {indefinite_locks} ({indefinite_locks/total_runs*100:.2f}%)")
    if recoverable_locks > 0:
        print(f"Average Timeline Delay Penalty      : {avg_penalty:.2f} years")
    print("=========================================================================")

    # Determine Ghost Zone boundaries
    # Ghost Zone: AHF > 100, wind < u_stagnation, and gated_lock is true
    ghosts = df[(df['m_drift'] > 1.0) & (df['gated_lock'] == 1)]
    print(f"Ghost Zone Configurations Detected  : {len(ghosts)} ({len(ghosts)/total_runs*100:.2f}%)")
    print("=========================================================================\n")

    # Generate Feasibility Transition Curves Plot
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Plot 1: Baseline IRR vs Wind Speed for different shock levels
    # Slice data at ahf = 120.0, emissivity = 0.75
    slice_df = df[(df['ahf'] == 120.0) & (df['emissivity'] == 0.75)]
    
    for shock_val in sorted(slice_df['market_shock'].unique()):
        sub_df = slice_df[slice_df['market_shock'] == shock_val].sort_values('u_wind')
        ax1.plot(sub_df['u_wind'], sub_df['irr_base'] * 100, marker='o', label=f"Market Shock {shock_val*100:.0f}%")
        
    ax1.axhline(25.0, color='red', linestyle='--', linewidth=1.5, label="Hurdle Rate (25%)")
    ax1.set_title("Capital Cascade Feasibility: IRR vs Wind Speed\n(AHF = 120 W/m², Emissivity = 0.75)", fontsize=11, fontweight='bold')
    ax1.set_xlabel("Wind Speed (u_wind) [m/s]", fontsize=10)
    ax1.set_ylabel("Baseline IRR (%)", fontsize=10)
    ax1.legend(loc='lower right', frameon=True)
    ax1.set_ylim(-50, 100)

    # Plot 2: Boundary-Layer Stagnation and Radiative trapping M_drift vs Wind Speed
    # Slice at ahf = 120.0, shock = 0.0, showing emissivity impact
    slice_eps = df[(df['ahf'] == 120.0) & (df['market_shock'] == 0.0)]
    for eps_val in sorted(slice_eps['emissivity'].unique()):
        sub_eps = slice_eps[slice_eps['emissivity'] == eps_val].sort_values('u_wind')
        ax2.plot(sub_eps['u_wind'], sub_eps['m_drift'], marker='x', label=f"Emissivity {eps_val:.2f}")
        
    ax2.axhline(1.0, color='gray', linestyle='-', linewidth=1.0)
    ax2.set_title("Thermodynamic Decay: Margin Erosion (M_drift) vs Wind Speed\n(AHF = 120 W/m²)", fontsize=11, fontweight='bold')
    ax2.set_xlabel("Wind Speed (u_wind) [m/s]", fontsize=10)
    ax2.set_ylabel("Margin Erosion Coefficient (M_drift)", fontsize=10)
    ax2.legend(loc='upper right', frameon=True)
    ax2.set_ylim(0.9, 1.25)

    plt.tight_layout()
    plot_name = "empirical_feasibility_curves.png"
    plt.savefig(plot_name, dpi=150)
    plt.close()
    print(f"Feasibility curve plot saved as {os.path.abspath(plot_name)}")

if __name__ == "__main__":
    analyze_sweep_data()
