"""
E-AII Real Data Historical Backtester & Empirical Correlation Analyzer.
Ingests real global primary energy, fuel mix, and GDP data from 1800 to 2024,
computes year-by-year composite E-AII global index, and correlates it with
actual observed civilization energy acceleration rates (dK/dt).
"""

import os
import sys
import pandas as pd
import numpy as np
import scipy.stats
import matplotlib.pyplot as plt

# Ensure local path is importable
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from thermo_arbitrage_engine import RegularizedGeometricIndicator

def run_real_data_analysis():
    # File Path to real historical harmonized master dataset
    master_data_path = os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "../aii_pipeline/master_energy_data.csv"
    ))
    
    if not os.path.exists(master_data_path):
        print(f"ERROR: Real master energy data not found at {master_data_path}")
        return
        
    print(f"Loading real historical energy telemetry from: {master_data_path}...")
    df = pd.read_csv(master_data_path)
    
    # 1. Define standard regularized E-AII parameters for each energy technology
    # n_i order: [n_LR, n_EROI, n_C, n_tau, n_epsilon, n_I]
    tech_profiles = {
        'coal': np.array([0.0, 30.0, 1e13, 50, 0.1, 2.0]),       # EROI=30, low LR, low I
        'oil': np.array([0.0, 33.0, 1.5e13, 50, 0.3, 5.0]),     # EROI=33, low LR, moderate I
        'gas': np.array([0.05, 28.0, 1.2e13, 40, 0.4, 6.0]),    # EROI=28, slight LR, moderate I
        'nuclear': np.array([0.0, 40.0, 2e13, 999, 0.1, 15.0]), # EROI=40, low/neg LR, high I
        'hydro': np.array([0.02, 50.0, 5e12, 60, 0.2, 8.0]),    # EROI=50, low LR, moderate I
        'wind': np.array([0.15, 18.0, 5e14, 30, 0.7, 20.0]),    # EROI=18, moderate LR, high I
        'solar': np.array([0.20, 12.0, 1e15, 25, 0.8, 25.0])    # EROI=12, high LR, high I
    }
    
    # Normalize profiles using the spec normalizer logic
    def normalize_profile(p, domain):
        # normalize:
        # LR
        n_LR = max(0.0, p[0] / 0.35)
        # EROI
        lambda_p = 0.0624
        n_EROI = 0.0 if p[1] <= 2 else 1.0 - np.exp(-lambda_p * (p[1] - 2.0))
        # C_max
        P_curr, P_t2 = 2.016e13, 4e26
        n_C = max(0.0, (np.log10(p[2]) - np.log10(P_curr)) / (np.log10(P_t2) - np.log10(P_curr)))
        # tau
        n_tau = 1.0 / (1.0 + 0.02 * p[3])
        # epsilon
        n_eps = min(1.0, p[4])
        # I
        n_I = np.exp(-0.10 * p[5])
        
        n_vector = np.array([n_LR, n_EROI, n_C, n_tau, n_eps, n_I])
        return RegularizedGeometricIndicator.compute_e_aii(n_vector, domain)

    # Pre-calculate E-AII score for each tech domain
    tech_scores = {}
    for name, prof in tech_profiles.items():
        domain_type = 'solar' if name in ['solar', 'wind'] else ('nuclear' if name == 'nuclear' else 'default')
        tech_scores[name] = normalize_profile(prof, domain_type)
        
    print("\nCalculated baseline regularized E-AII scores for individual technologies:")
    for t_name, score in tech_scores.items():
        print(f"  - {t_name.upper():<8}: E-AII = {score:.6f}")
        
    # 2. Compute year-by-year composite E-AII global index based on real energy mix
    # We will sum: E-AII_global(t) = Sum(f_i(t) * E-AII_i)
    # where f_i(t) is the fraction of primary energy consumption
    energy_sources = ['coal_TW', 'oil_TW', 'gas_TW', 'nuclear_TW', 'hydro_TW', 'wind_TW', 'solar_TW']
    
    e_aii_global = []
    for idx, row in df.iterrows():
        total_energy = row['global_primary_energy_TW']
        if total_energy <= 0:
            e_aii_global.append(0.0)
            continue
            
        composite_score = 0.0
        for src in energy_sources:
            tech_key = src.split('_')[0]
            val = row[src]
            fraction = val / total_energy
            composite_score += fraction * tech_scores[tech_key]
        e_aii_global.append(composite_score)
        
    df['e_aii_global'] = e_aii_global

    # 3. Correlation analysis: compare E-AII global index against civilization growth rates (dKdt and dKdt_roll10)
    # Filter rows with valid dKdt values (drop first/last transitions if necessary)
    analysis_df = df.dropna(subset=['dKdt', 'dKdt_roll10']).copy()
    
    pearson_r, p_pearson = scipy.stats.pearsonr(analysis_df['e_aii_global'], analysis_df['dKdt_roll10'])
    spearman_r, p_spearman = scipy.stats.spearmanr(analysis_df['e_aii_global'], analysis_df['dKdt_roll10'])
    
    print("\n=========================================================================")
    print("                REAL DATA HISTORICAL CORRELATION ANALYSIS")
    print("=========================================================================")
    print(f"Analyzed Timeline                   : 1800 - 2024 ({len(analysis_df)} Years)")
    print(f"Pearson Correlation (E-AII vs dKdt) : r = {pearson_r:.6f} (p-value = {p_pearson:.3e})")
    print(f"Spearman Correlation (E-AII vs dKdt): rs = {spearman_r:.6f} (p-value = {p_spearman:.3e})")
    
    # Interpretation
    if spearman_r > 0.70 and p_spearman < 0.01:
        verdict = "EXTREMELY SIGNIFICANT CO-ACCELERATION (Micro-Alpha Confirmed)"
    elif spearman_r > 0.40 and p_spearman < 0.05:
        verdict = "MODERATE POSITIVE CORRELATION"
    else:
        verdict = "NO SIGNIFICANT STATISTICAL LINK"
    print(f"Analysis Verdict                    : {verdict}")
    print("=========================================================================")

    # 4. Detailed analysis of key historical transition epochs
    print("\nTransition Epoch In-Depth Study:")
    epochs = [
        ("1800-1850", "Early Coal Transition", df[df['year'].between(1800, 1850)]),
        ("1900-1950", "Oil & Industrialization", df[df['year'].between(1900, 1950)]),
        ("1970-2000", "Nuclear & Gas Expansion", df[df['year'].between(1970, 2000)]),
        ("2010-2024", "Solar & Wind Exponential Runout", df[df['year'].between(2010, 2024)])
    ]
    
    print(f"{'Epoch/Era':<28} | {'Avg E-AII':<12} | {'Avg dK/dt (e-5)':<16} | {'GDP Growth (B/yr)':<18}")
    print("-" * 83)
    for era_range, name, sub_df in epochs:
        avg_e_aii = sub_df['e_aii_global'].mean()
        avg_dkdt = sub_df['dKdt'].mean() * 1e5
        gdp_diff = sub_df['world_gdp_2011_USD'].iloc[-1] - sub_df['world_gdp_2011_USD'].iloc[0]
        gdp_rate = gdp_diff / len(sub_df)
        print(f"{era_range:<10} ({name[:15]:<15}) | {avg_e_aii:<12.6f} | {avg_dkdt:<16.4f} | ${gdp_rate:<17.2f}B")
        
    # 5. Plotting real historical transition curves
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # Left Y-Axis: E-AII global composite index
    color = '#1f77b4'
    ax1.set_xlabel('Year', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Global Composite E-AII Index', color=color, fontsize=11, fontweight='bold')
    line1 = ax1.plot(df['year'], df['e_aii_global'], color=color, linewidth=2.5, label='E-AII Index (Global)')
    ax1.tick_params(axis='y', labelcolor=color)

    # Right Y-Axis: Actual 10-year rolling dK/dt
    ax2 = ax1.twinx()
    color = '#ff7f0e'
    ax2.set_ylabel('Civilization Energy Acceleration dK/dt (10-yr Rolling)', color=color, fontsize=11, fontweight='bold')
    line2 = ax2.plot(df['year'], df['dKdt_roll10'], color=color, linewidth=2.0, linestyle='--', label='Actual dK/dt (Rolling)')
    ax2.tick_params(axis='y', labelcolor=color)

    # Title & Layout
    plt.title('Multi-Century Historical Backtest: E-AII vs Actual Civilization Acceleration\n(Real Telemetry 1800 - 2024)', fontsize=12, fontweight='bold')
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper left', frameon=True)
    
    plt.tight_layout()
    plot_name = "real_data_feasibility_curves.png"
    plt.savefig(plot_name, dpi=150)
    plt.close()
    print(f"\nFeasibility transition curves plot saved as {os.path.abspath(plot_name)}")
    
    # Save the updated data frame with E-AII composite scores to CSV
    updated_csv = "master_energy_data_e_aii.csv"
    df.to_csv(updated_csv, index=False)
    print(f"Saved E-AII enriched master data to {os.path.abspath(updated_csv)}")

if __name__ == "__main__":
    run_real_data_analysis()
