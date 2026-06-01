"""
E-AII High-Granularity Volatility & Weekly Telemetry Parser.
Ingests weekly boundary-layer stagnation factors, grid electricity spot prices, and
compute-token index pricing to live-evaluate capital cascade gating and route signals.
"""

import os
import sys
import numpy as np
from thermo_arbitrage_engine import (
    BoundaryLayerStagnationEngine,
    FinancialCascadeGatingEngine
)

# Ensure local path is importable
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class WeeklyVolatilityTracker:
    """
    Simulates and parses highly granular weekly environmental and asset telemetry.
    Calculates forward-looking project feasibility (IRR) and routes tactical signals.
    """
    
    def __init__(self, region: str = "Silicon Valley, USA", seed: int = 42):
        self.region = region
        self.seed = seed
        self.stagnation_engine = BoundaryLayerStagnationEngine(gamma=0.5)
        self.gating_engine = FinancialCascadeGatingEngine(hurdle_rate=0.25)
        
    def generate_52_week_series(self) -> list[dict]:
        """
        Generates a 52-week synthetic volatility series simulating seasonal boundary-layer
        stagnation, grid electricity pricing spikes, and compute-token market compression shocks.
        """
        np.random.seed(self.seed)
        series = []
        
        # Base values
        base_wind = 1.6          # m/s
        base_ahf = 120.0         # W/m²
        base_emissivity = 0.75
        base_temp = 302.0        # Kelvin
        base_token_index = 1.0   # Start normalized
        base_elec_price = 45.0   # $ per MWh
        
        for week in range(1, 53):
            # 1. Weekly Wind speed: fluctuates naturally; inject severe stagnation episodes
            u_wind = np.random.normal(base_wind, 0.5)
            u_wind = max(0.05, u_wind)
            
            # Inject extreme stagnation weeks (e.g. late summer heat domes or winter inversions)
            stagnation_weeks = [12, 13, 24, 38, 42]
            if week in stagnation_weeks:
                u_wind = np.random.uniform(0.08, 0.35)
                
            # 2. Anthropogenic Heat Flux
            ahf = base_ahf + np.random.normal(0, 10)
            ahf = max(50.0, ahf)
            
            # 3. Electricity Spot Price: correlated with stagnation (low wind generation, high HVAC load)
            elec_price = base_elec_price + np.random.normal(0, 5)
            if u_wind < 0.4272:
                # Supply-side pinch: wind drop + heat surge doubles spot price
                elec_price += np.random.uniform(40.0, 120.0)
            elec_price = max(10.0, elec_price)
            
            # 4. Token Valuation Index & Shocks
            # Weekly natural fluctuation
            token_change_pct = np.random.normal(0.01, 0.05)
            # Inject severe market compression shock events (e.g., tech sell-offs)
            shock_weeks = {12: -0.40, 24: -0.55, 38: -0.20, 48: -0.15}
            if week in shock_weeks:
                token_change_pct = shock_weeks[week]
                
            token_index = base_token_index * (1.0 + token_change_pct)
            base_token_index = token_index  # Update for cumulative tracking
            
            series.append({
                "week": week,
                "u_wind": u_wind,
                "ahf": ahf,
                "emissivity": base_emissivity,
                "temp_surf": base_temp,
                "elec_price": elec_price,
                "token_index": token_index,
                "token_delta": token_change_pct
            })
            
        return series

    def run_weekly_simulation(self):
        """
        Runs the 52-week simulation, evaluates margin decay, projected IRR,
        gating thresholds, and routes tactical asset allocator signals.
        """
        series = self.generate_52_week_series()
        
        # OpEx constants
        opex_cooling_base = 50000.0
        
        print("\n=========================================================================================")
        print(f"             E-AII HIGH-GRANULARITY VOLATILITY TRACKER & TRADING LEDGER")
        print(f"             Region: {self.region} | Stagnation Limit Threshold: 0.4272 m/s")
        print("=========================================================================================")
        print(f"{'Week':<5} | {'Wind (m/s)':<10} | {'Token Delta':<11} | {'Weekly IRR':<10} | {'M_drift':<8} | {'Feasibility / Tactical Route'}")
        print("-" * 115)
        
        for w_data in series:
            week = w_data["week"]
            u_wind = w_data["u_wind"]
            ahf = w_data["ahf"]
            eps = w_data["emissivity"]
            temp_surf = w_data["temp_surf"]
            token_idx = w_data["token_index"]
            token_delta = w_data["token_delta"]
            elec_price = w_data["elec_price"]
            
            # Compute boundary layer metrics
            u_stagn = self.stagnation_engine.compute_stagnation_velocity(ahf, 4.5, eps, temp_surf)
            m_drift, scaled_op = self.stagnation_engine.evaluate_margin_decay(
                u_wind, u_stagn, ahf, opex_cooling_base, eps
            )
            
            # Weekly projected cash flows based on current week's spot metrics
            # Phase 1: CapEx = -200,000, Revenue scales with token_index, cost with electricity
            p1_capex = 200000.0
            # Weekly cash flow converted to annual scale for consistency in solver
            p1_annual_rev = 80000.0 * token_idx
            p1_annual_opex = 20000.0 * (elec_price / 45.0)
            
            # Phase 2: CapEx = -1,000,000, Revenue scales with token_index, cost with opex_drift
            p2_capex = 1000000.0
            p2_annual_rev = 400000.0 * token_idx
            p2_annual_opex = 100000.0 * (elec_price / 45.0)
            
            # Construct cash flows
            cf = self.gating_engine.simulate_capital_cascade(
                shock_factor=0.0,  # Already captured in token_idx
                m_drift=m_drift,
                opex_cooling_base=scaled_op,
                phase1_capex=p1_capex,
                phase1_revenue=p1_annual_rev,
                phase1_opex=p1_annual_opex,
                phase2_capex=p2_capex,
                phase2_revenue=p2_annual_rev,
                phase2_opex=p2_annual_opex,
                delay_years=0
            )
            
            # Solve projected IRR
            irr = self.gating_engine.calculate_irr(cf)
            
            # Hurdle Gate Check
            is_locked = irr < 0.25
            
            # Tactical Routing Signal Logic
            if is_locked or m_drift > 1.10:
                # High wind stagnation or severe token drawdowns trigger lock
                if token_delta <= -0.15:
                    route = "GATE_LOCKED / SUBLEASE_HOLD (Severe Drawdown & Thermal Wall)"
                else:
                    route = "GATE_LOCKED / AVOID (Hurdle Rate Breach)"
            else:
                route = "GATE_UNLOCKED / LONG (Cascade Feasible)"
                
            irr_str = f"{irr*100:.2f}%" if irr > -0.99 else "N/A"
            delta_str = f"{token_delta*100:+.2f}%"
            
            print(f"{week:<5} | {u_wind:<10.4f} | {delta_str:<11} | {irr_str:<10} | {m_drift:<8.4f} | {route}")
            
        print("=========================================================================================")

if __name__ == "__main__":
    tracker = WeeklyVolatilityTracker()
    tracker.run_weekly_simulation()
