"""
Empirical parameter sweep script for the E-AII Thermodynamic Arbitrage Engine.
Executes a multi-dimensional sweep over wind speeds, heat fluxes, atmospheric emissivities,
and financial market shocks to map the boundaries of project feasibility and Ghost Zones.
"""

import csv
import os
import numpy as np
from thermo_arbitrage_engine import (
    BoundaryLayerStagnationEngine,
    FinancialCascadeGatingEngine
)

def run_empirical_sweep():
    print("Initializing empirical multi-dimensional parameter sweep...")
    
    # Sweep Grid parameters
    wind_speeds = [0.0, 0.1, 0.3, 0.5, 1.0, 2.0, 3.0, 5.0]  # m/s
    heat_fluxes = [50.0, 90.0, 100.0, 120.0, 150.0, 200.0]  # W/m²
    emissivities = [0.5, 0.75, 0.9]                        # ratio
    shocks = [0.0, 0.2, 0.4, 0.6, 0.8]                      # revenue compression
    
    # Constants
    z_0 = 4.5
    T_surface = 302.0
    opex_base = 50000.0
    
    stagnation_engine = BoundaryLayerStagnationEngine(gamma=0.5)
    gating_engine = FinancialCascadeGatingEngine(hurdle_rate=0.25)
    
    csv_file = "empirical_test_results.csv"
    headers = [
        "u_wind", "ahf", "emissivity", "market_shock",
        "u_stagnation", "m_drift", "scaled_opex",
        "irr_base", "gated_lock", "timeline_penalty", "irr_final"
    ]
    
    count = 0
    with open(csv_file, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for uw in wind_speeds:
            for ahf in heat_fluxes:
                for eps in emissivities:
                    # Compute meteorological boundary layer state
                    u_stagn = stagnation_engine.compute_stagnation_velocity(ahf, z_0, eps, T_surface)
                    md, scaled_op = stagnation_engine.evaluate_margin_decay(uw, u_stagn, ahf, opex_base, eps)
                    
                    for shock in shocks:
                        # Compute financial gating metrics
                        res = gating_engine.evaluate_gating(shock, md, opex_base)
                        
                        writer.writerow([
                            uw, ahf, eps, shock,
                            u_stagn, md, scaled_op,
                            res['irr_base'], int(res['gated_lock']),
                            res['timeline_penalty'], res['irr_final']
                        ])
                        count += 1
                        
    print(f"Sweep complete. Saved {count} data rows to {os.path.abspath(csv_file)}")

if __name__ == "__main__":
    run_empirical_sweep()
