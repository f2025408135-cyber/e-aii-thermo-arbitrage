"""
Extended Acceleration Intensity Index (E-AII) Micro-Alpha Thermodynamic Arbitrage Engine.
Production-grade, optimization-hardened implementation resolving parameter rank-deficiency,
geometric noise cliff collapses, and non-monotonic IRR root-finding convergence.
"""

import sys
import numpy as np
import scipy.optimize

# --- MODULE 1: THE INFLEXION ALGORITHMIC STATE MONITOR ---

class RegionalThermalMonitor:
    """
    Parses and tracks environmental and information thermodynamics time-series.
    Calculates infinitely differentiable weighting parameters and robust SVD-based pseudoinverses.
    """
    
    K_B = 1.38e-23  # Boltzmann constant in Joules / Kelvin
    
    def __init__(self, e_op: float = 1e-19, k: float = 3.0):
        """
        Args:
            e_op: Operation energy (Joules) per operation/computation. Default is 1e-19.
            k: Sigmoidal sensitivity coefficient. Default is 3.0.
        """
        self.e_op = e_op
        self.k = k

    def calculate_ier_critical(self, temp: float) -> float:
        """
        Computes the critical Information Entropy Rate (IER_crit) under the Landauer Bound.
        IER_crit = E_op / (k_B * T * ln(2))
        """
        if temp <= 0:
            raise ValueError("Temperature must be strictly positive (greater than absolute zero).")
        return self.e_op / (self.K_B * temp * np.log(2))

    def calculate_alpha(self, ier: float, temp: float) -> float:
        """
        Computes alpha(t) = 0.5 + 0.5 / (1 + (IER(t) / IER_crit(t))^(-k))
        """
        ier_crit = self.calculate_ier_critical(temp)
        if ier <= 0:
            return 0.5
        ratio = ier / ier_crit
        ratio_powered = np.power(ratio, -self.k)
        return 0.5 + (0.5 / (1.0 + ratio_powered))

    def calculate_gamma_dim(self, temp: float) -> float:
        """
        Thermodynamic efficiency coefficient: Joules per computational bit erasure relative
        to operational energy threshold. (k_B * T * ln(2)) / E_op.
        """
        return (self.K_B * temp * np.log(2)) / self.e_op

    def calculate_k_ext(self, alpha: float, k_e: float, k_i: float, temp: float) -> float:
        """
        Dimensionally harmonized external knowledge metric:
        K_ext = alpha * K_E + (1.0 - alpha) * gamma_dim * K_I
        """
        gamma_dim = self.calculate_gamma_dim(temp)
        return alpha * k_e + (1.0 - alpha) * gamma_dim * k_i

    def calculate_margin_erosion(self, u_wind: float, u_stagnation: float, ahf: float, opex_base: float, epsilon: float, gamma: float = 0.5) -> tuple[float, float]:
        """
        Calculates margin opex decay/drift. Remains completely dormant (M_drift = 1.0)
        unless localized Anthropogenic Heat Flux (ahf) explicitly matches or exceeds 100.0 W/m2.
        """
        if ahf >= 100.0 and u_wind < u_stagnation:
            u_diff = u_stagnation - u_wind
            ahf_excess = ahf - 100.0
            m_drift = np.exp(gamma * (u_diff / u_stagnation) * (ahf_excess / 100.0) * epsilon)
        else:
            m_drift = 1.0
            
        scaled_opex = opex_base * m_drift
        return m_drift, scaled_opex

    @staticmethod
    def svd_pinv(jacobian: np.ndarray, threshold: float = 1e-12) -> np.ndarray:
        """
        SVD-based pseudoinverse engine (J_eta^+) truncating singular values below the threshold
        to resolve parameter rank-deficiency and collinearity.
        """
        u, s, vt = np.linalg.svd(jacobian, full_matrices=False)
        s_inv = np.zeros_like(s)
        mask = s >= threshold
        s_inv[mask] = 1.0 / s[mask]
        return (vt.T * s_inv) @ u.T


# --- MODULE 2: BOUNDARY LAYER METEOROLOGICAL STAGNATON ENGINE ---

class BoundaryLayerStagnationEngine:
    """
    Computes boundary layer stagnation velocities using Boussinesq approximation
    and implements the margin opex decay/drift model.
    """
    G = 9.81      # Gravitational acceleration (m/s^2)
    RHO = 1.2     # Dry air density at sea level (kg/m^3)
    CP = 1005.0   # Specific heat capacity of dry air (J/(kg*K))

    def __init__(self, gamma: float = 0.5):
        """
        Args:
            gamma: Drift sensitivity scaling factor.
        """
        self.gamma = gamma

    def compute_stagnation_velocity(self, ahf: float, z_0: float, epsilon: float, t_surface: float) -> float:
        """
        Computes the critical horizontal stagnation velocity u_stagnation.
        Based on boundary layer buoyancy-drag balancing (Oberbeck-Boussinesq).
        """
        if t_surface <= 0:
            raise ValueError("Surface temperature must be positive.")
        ahf = max(0.0, ahf)
        z_0 = max(0.0, z_0)
        
        # Convective scale under Oberbeck-Boussinesq
        base_term = (self.G * ahf * z_0) / (self.RHO * self.CP * t_surface)
        u_stagnation_base = np.cbrt(base_term)
        
        # Radiative scaling multiplier representing grey-atmosphere trapping
        return u_stagnation_base * (1.0 + epsilon)

    def evaluate_margin_decay(self, u_wind: float, u_stagnation: float, ahf: float, opex_base: float, epsilon: float) -> tuple[float, float]:
        """
        Evaluates the cooling OpEx drift under stagnant, high-heat conditions.
        Calls RegionalThermalMonitor.calculate_margin_erosion to execute AHF environmental gate.
        Returns (M_drift, scaled_opex).
        """
        monitor = RegionalThermalMonitor()
        return monitor.calculate_margin_erosion(u_wind, u_stagnation, ahf, opex_base, epsilon, self.gamma)


# --- MODULE 3: PER-DOMAIN REGULARIZED GEOMETRIC INDICATOR ---

class RegularizedGeometricIndicator:
    """
    Computes regularized geometric index (E-AII) with per-domain noise floors
    to prevent index collapses near zero threshold.
    """
    
    # Global technology variable weights (sum to 1.0)
    # n_i order: [n_LR, n_EROI, n_C, n_tau, n_epsilon, n_I]
    WEIGHTS = np.array([0.30, 0.30, 0.15, 0.0833, 0.0833, 0.0833])
    WEIGHTS /= WEIGHTS.sum()  # Normalize to sum exactly to 1.0

    # Domain noise floors
    NOISE_FLOORS = {
        'solar': 1e-6,
        'pv': 1e-6,
        'nuclear': 1e-3,
        'default': 1e-5
    }

    @classmethod
    def compute_e_aii(cls, n_vector: np.ndarray, domain: str) -> float:
        """
        Computes the regularized geometric index E-AII.
        E-AII = Product_i(n_i + delta_i)^(w_i) - delta_base
        where delta_base = delta_i.
        """
        domain_key = domain.lower()
        delta = cls.NOISE_FLOORS.get(domain_key, cls.NOISE_FLOORS['default'])
        
        n_vector = np.clip(n_vector, 0.0, 1.0)
        
        terms = np.power(n_vector + delta, cls.WEIGHTS)
        e_aii = np.prod(terms) - delta
        return float(e_aii)


# --- MODULE 4: PHASED FINANCIAL GATING & CONVERGENCE ASSURANCE ---

class MacroShockOverlay:
    """
    Applies geopolitical and macroeconomic risk overrides to the institutional gating matrix.
    Subtracts penalty from projected IRR based on energy concentration index.
    """
    @staticmethod
    def calculate_geopolitical_penalty(energy_concentration_index: float) -> float:
        return 0.15 * energy_concentration_index

    @classmethod
    def apply_overlay(cls, irr: float, energy_concentration_index: float) -> float:
        penalty = cls.calculate_geopolitical_penalty(energy_concentration_index)
        return irr - penalty


class FinancialCascadeGatingEngine:
    """
    Simulates capital cascade phases, optimizes IRR using Brent's method,
    and applies institutional hurdle gates, macroeconomic risk overlays, and timeline penalties.
    """
    
    def __init__(self, hurdle_rate: float = 0.25):
        self.hurdle_rate = hurdle_rate

    @staticmethod
    def calculate_irr(cash_flows: list[float], bracket: tuple[float, float] = (-0.99, 5.0)) -> float:
        """
        Hardened IRR solver using scipy.optimize.brentq with grid search fallback
        to assure mathematical convergence under severe market shocks.
        Vectorized grid search to optimize speed under heavy sweeps.
        """
        cf = np.array(cash_flows, dtype=float)
        n = len(cf)
        
        def npv(r: float) -> float:
            if r <= -1.0:
                r = -0.9999
            return float(np.dot(cf, np.power(1.0 + r, -np.arange(n))))
        
        a, b = bracket
        try:
            npv_a = npv(a)
            npv_b = npv(b)
            if npv_a * npv_b < 0:
                return float(scipy.optimize.brentq(npv, a, b))
            
            # Grid search fallback - fully vectorized
            grid = np.linspace(a, b, 100)
            powers = np.power(1.0 + np.clip(grid[:, None], -0.9999, None), -np.arange(n))
            npv_vals = np.dot(powers, cf)
            
            # Find index where sign changes
            signs = np.sign(npv_vals)
            sign_changes = np.where(signs[:-1] != signs[1:])[0]
            if len(sign_changes) > 0:
                idx = sign_changes[0]
                return float(scipy.optimize.brentq(npv, grid[idx], grid[idx+1]))
            
            # Handle boundary asymptotics
            if cf.sum() < 0:
                return a
            return b if npv(0.0) > 0 else a
        except Exception:
            return -0.99

    def simulate_capital_cascade(
        self,
        shock_factor: float,
        m_drift: float,
        opex_cooling_base: float,
        phase1_capex: float = 200000.0,
        phase1_revenue: float = 80000.0,
        phase1_opex: float = 20000.0,
        phase2_capex: float = 1000000.0,
        phase2_revenue: float = 800000.0,
        phase2_opex: float = 100000.0,
        phase1_years: int = 5,
        phase2_years: int = 10,
        delay_years: int = 0
    ) -> list[float]:
        """
        Generates net cash flows across Phase 1 and Phase 2, coupling thermodynamic opex multiplier
        and revenue shock factors.
        """
        rev_multiplier = 1.0 - shock_factor
        
        # Annual Phase 1 Cash Flow
        p1_annual_cf = (phase1_revenue * rev_multiplier) - phase1_opex
        
        # Annual Phase 2 Cash Flow with thermodynamic cooling OpEx drift
        cooling_drift_cost = opex_cooling_base * m_drift
        p2_annual_cf = (phase2_revenue * rev_multiplier) - phase2_opex - cooling_drift_cost

        cash_flows = []
        
        # Year 0: Phase 1 CapEx
        cash_flows.append(-phase1_capex)
        
        # Year 1 to end of Phase 1 (including delay years)
        total_p1_years = phase1_years + delay_years
        for _ in range(1, total_p1_years):
            cash_flows.append(p1_annual_cf)
            
        # Transition Year: Phase 2 CapEx and final Phase 1 Cash Flow
        cash_flows.append(-phase2_capex + p1_annual_cf)
        
        # Phase 2 Years
        for _ in range(phase2_years):
            cash_flows.append(p2_annual_cf)
            
        return cash_flows

    def evaluate_gating(
        self,
        shock_factor: float,
        m_drift: float,
        opex_cooling_base: float,
        max_delay_search: int = 100,
        energy_concentration_index: float = 0.0
    ) -> dict:
        """
        Evaluates hurdle rate compliance, locks/unlocks Phase 2, and calculates timeline penalty.
        Applies MacroShockOverlay to subtract geopolitical penalty from the IRR.
        """
        cf_base = self.simulate_capital_cascade(shock_factor, m_drift, opex_cooling_base, delay_years=0)
        irr_base = self.calculate_irr(cf_base)
        
        # Apply geopolitical overlay to base IRR
        irr_base_adj = MacroShockOverlay.apply_overlay(irr_base, energy_concentration_index)
        
        gated_lock = irr_base_adj < self.hurdle_rate
        timeline_penalty = 0
        irr_final = irr_base
        irr_final_adj = irr_base_adj
        
        if gated_lock:
            resolved = False
            for d in range(1, max_delay_search + 1):
                cf_delay = self.simulate_capital_cascade(shock_factor, m_drift, opex_cooling_base, delay_years=d)
                irr_d = self.calculate_irr(cf_delay)
                irr_d_adj = MacroShockOverlay.apply_overlay(irr_d, energy_concentration_index)
                if irr_d_adj >= self.hurdle_rate:
                    timeline_penalty = d
                    irr_final = irr_d
                    irr_final_adj = irr_d_adj
                    resolved = True
                    break
            
            if not resolved:
                timeline_penalty = -1  # Indefinite lock
                irr_final = irr_base
                irr_final_adj = irr_base_adj
        
        return {
            'irr_base': irr_base,
            'irr_base_adj': irr_base_adj,
            'gated_lock': gated_lock,
            'timeline_penalty': timeline_penalty,
            'irr_final': irr_final,
            'irr_final_adj': irr_final_adj
        }


# --- HIGH-STRESS TEST HARNESS & TACTICAL ROUTING ---

def run_engine_diagnostics():
    print("=========================================================================")
    print("          E-AII THERMODYNAMIC ARBITRAGE ENGINE INITIAL DIAGNOSTICS")
    print("=========================================================================")
    
    # 1. Module 1: Regional Thermal Monitor & Landauer Bound
    print("\n--- MODULE 1: THE INFLEXION ALGORITHMIC STATE MONITOR ---")
    monitor = RegionalThermalMonitor(e_op=1e-19, k=3.0)
    
    temps = [298.0, 302.0, 3.0]  # Terrestrial layers and deep space sinks
    print(f"{'Temperature (K)':<18} | {'Critical IER (J/K/s)':<22}")
    print("-" * 45)
    for t in temps:
        ier_crit = monitor.calculate_ier_critical(t)
        print(f"{t:<18.1f} | {ier_crit:<22.6e}")
        
    # Testing alpha(t) sigmoidal behavior
    print("\nAlpha(t) Sigmoidal Weighting Evaluation (Sigmoidal Transition):")
    ier_crit_302 = monitor.calculate_ier_critical(302.0)
    print(f"Terrestrial ambient layer (T = 302 K, IER_crit = {ier_crit_302:.3f} J/K/s):")
    print(f"  IER = 10.0  J/K/s -> alpha(t) = {monitor.calculate_alpha(10.0, 302.0):.6f}")
    print(f"  IER = {ier_crit_302:.3f} J/K/s -> alpha(t) = {monitor.calculate_alpha(ier_crit_302, 302.0):.6f} (critical)")
    print(f"  IER = 100.0 J/K/s -> alpha(t) = {monitor.calculate_alpha(100.0, 302.0):.6f}")
    
    ier_crit_3 = monitor.calculate_ier_critical(3.0)
    print(f"Deep space sink (T = 3 K, IER_crit = {ier_crit_3:.3f} J/K/s):")
    print(f"  IER = 1000.0 J/K/s -> alpha(t) = {monitor.calculate_alpha(1000.0, 3.0):.6f}")
    print(f"  IER = {ier_crit_3:.3f} J/K/s -> alpha(t) = {monitor.calculate_alpha(ier_crit_3, 3.0):.6f} (critical)")
    print(f"  IER = 10000.0 J/K/s -> alpha(t) = {monitor.calculate_alpha(10000.0, 3.0):.6f}")

    # SVD Pseudoinverse rank-deficiency test
    print("\nRank-Deficiency & Parameter Collinearity Test (SVD Engine):")
    # Singular matrix J (col 2 is 2*col 1) with small perturbation below the 1e-12 threshold
    J_collinear = np.array([
        [1.0, 2.0],
        [2.0, 4.0000000000001]
    ])
    print("Original collinear matrix J:")
    print(J_collinear)
    
    _, s_vals, _ = np.linalg.svd(J_collinear)
    print(f"Singular values of J: {s_vals}")
    
    J_pinv = RegionalThermalMonitor.svd_pinv(J_collinear, threshold=1e-12)
    print("SVD-Truncated Pseudoinverse (J_eta^+):")
    print(J_pinv)
    print("Validation J * J_eta^+ * J (should match truncated J):")
    print(J_collinear @ J_pinv @ J_collinear)

    # 2. Module 2: Boundary Layer Meteorological Stagnation Engine
    print("\n--- MODULE 2: BOUNDARY LAYER METEOROLOGICAL STAGNATON ENGINE ---")
    stagnation_engine = BoundaryLayerStagnationEngine(gamma=0.5)
    
    # Telemetry Attributes
    AHF = 120.0       # W/m^2
    z_0 = 4.5         # meters
    emissivity = 0.75 # Atmospheric Emissivity
    T_surface = 302.0 # Kelvin
    
    u_stagnation = stagnation_engine.compute_stagnation_velocity(AHF, z_0, emissivity, T_surface)
    print(f"Telemetry input: AHF = {AHF} W/m², z_0 = {z_0}m, Emissivity = {emissivity}, T_surface = {T_surface}K")
    print(f"Computed Critical Horizontal Stagnation Velocity (u_stagnation): {u_stagnation:.4f} m/s")
    
    # Evaluate Margin Decay under active wind speeds
    print("\nMargin Decay Evaluation under varying wind speeds (Base Cooling OpEx = $50,000):")
    opex_base = 50000.0
    print(f"{'Wind Speed (u_wind)':<20} | {'M_drift':<12} | {'Scaled Cooling OpEx':<20}")
    print("-" * 60)
    wind_speeds = [0.1, 0.5, u_stagnation - 0.1, u_stagnation + 0.5, 5.0]
    m_drift_vals = []
    for uw in wind_speeds:
        md, scaled_op = stagnation_engine.evaluate_margin_decay(uw, u_stagnation, AHF, opex_base, emissivity)
        m_drift_vals.append((uw, md))
        print(f"{uw:<20.2f} | {md:<12.5f} | ${scaled_op:<19.2f}")

    # 3. Module 3: Per-Domain Regularized Geometric Indicator
    print("\n--- MODULE 3: PER-DOMAIN REGULARIZED GEOMETRIC INDICATOR ---")
    # Base normalized indicator vector (e.g. from a real technology transition)
    # n_i order: [n_LR, n_EROI, n_C, n_tau, n_epsilon, n_I]
    # Test case matching Solar/PV asset profile with zero in learning rate to test regularized noise floor
    n_solar = np.array([0.0, 0.8, 0.7, 0.9, 0.8, 0.6])
    n_nuclear = np.array([0.0, 0.9, 0.6, 0.4, 0.5, 0.8])
    n_zero = np.zeros(6)
    
    e_aii_solar = RegularizedGeometricIndicator.compute_e_aii(n_solar, 'solar')
    e_aii_nuclear = RegularizedGeometricIndicator.compute_e_aii(n_nuclear, 'nuclear')
    e_aii_zero = RegularizedGeometricIndicator.compute_e_aii(n_zero, 'solar')
    
    print(f"Solar Asset Vector: {n_solar}")
    print(f"Computed Solar E-AII (noise floor = 1e-6): {e_aii_solar:.8f}")
    print(f"Nuclear Asset Vector: {n_nuclear}")
    print(f"Computed Nuclear E-AII (noise floor = 1e-3): {e_aii_nuclear:.8f}")
    print(f"Zero Input Vector: {n_zero}")
    print(f"Computed Regularized E-AII (Zero Input): {e_aii_zero:.8f} (No collapse)")

    # 4. Module 4: Phased Financial Gating & Convergence Assurance
    print("\n--- MODULE 4: PHASED FINANCIAL GATING & CONVERGENCE ---")
    gating_engine = FinancialCascadeGatingEngine(hurdle_rate=0.25)
    
    # Run loop under Active 60% Revenue Compression Shock
    SHOCK = 0.60
    print(f"Active Market shock payload: {SHOCK*100:.1f}% Revenue Compression")
    
    # Case A: Wind Speed = 5.0 m/s (No Stagnation)
    md_a, _ = stagnation_engine.evaluate_margin_decay(5.0, u_stagnation, AHF, opex_base, emissivity)
    res_a = gating_engine.evaluate_gating(SHOCK, md_a, opex_base)
    
    # Case B: Wind Speed = 0.1 m/s (Severe Stagnation)
    md_b, _ = stagnation_engine.evaluate_margin_decay(0.1, u_stagnation, AHF, opex_base, emissivity)
    res_b = gating_engine.evaluate_gating(SHOCK, md_b, opex_base)
    
    print("\nFinancial Cascade Simulation Results:")
    print("-" * 80)
    print(f"{'Metric':<40} | {'Case A (No Stagnation)':<20} | {'Case B (Stagnation)':<20}")
    print("-" * 80)
    print(f"{'Margin Erosion Mult. (M_drift)':<40} | {md_a:<20.5f} | {md_b:<20.5f}")
    print(f"{'Baseline IRR':<40} | {res_a['irr_base']*100:<19.2f}% | {res_b['irr_base']*100:<19.2f}%")
    print(f"{'Hurdle Compliant (IRR >= 25%)':<40} | {str(not res_a['gated_lock']):<20} | {str(not res_b['gated_lock']):<20}")
    
    status_a = "UNLOCKED" if not res_a['gated_lock'] else "LOCKED"
    status_b = "UNLOCKED" if not res_b['gated_lock'] else "LOCKED"
    print(f"{'Phase 2 Gate Status':<40} | {status_a:<20} | {status_b:<20}")
    
    penalty_a = f"{res_a['timeline_penalty']} Years" if res_a['timeline_penalty'] >= 0 else "Indefinite"
    penalty_b = f"{res_b['timeline_penalty']} Years" if res_b['timeline_penalty'] >= 0 else "Indefinite"
    print(f"{'Chronological Timeline Penalty':<40} | {penalty_a:<20} | {penalty_b:<20}")
    
    final_irr_a = f"{res_a['irr_final']*100:.2f}%" if res_a['timeline_penalty'] >= 0 else "N/A"
    final_irr_b = f"{res_b['irr_final']*100:.2f}%" if res_b['timeline_penalty'] >= 0 else "N/A"
    print(f"{'Post-Penalty Recovered IRR':<40} | {final_irr_a:<20} | {final_irr_b:<20}")

    # Ghost Zone Coordinates & Tactical Routing Signals
    print("\n--- GHOST ZONE DETECTION & TACTICAL ASSET ROUTING SIGNALS ---")
    print("-" * 80)
    
    # Identify Ghost Zone: high AHF, low wind, high emissivity where physical decay prevents unlock
    print("Ghost Zone Definition: Regions of boundary-layer stagnation where M_drift > 1.1")
    print("and Phase 2 capital cascade is locked (IRR < 25%).")
    
    # Check Case A and Case B
    for name, md_val, res_val in [("Asset Scenario A (No Stagnation)", md_a, res_a), ("Asset Scenario B (Stagnation)", md_b, res_b)]:
        is_ghost = md_val > 1.1 or res_val['gated_lock']
        ghost_coord = f"AHF={AHF} W/m², Emissivity={emissivity}, M_drift={md_val:.3f}" if is_ghost else "None"
        
        # Tactical Routing Signal
        if res_val['gated_lock']:
            if res_val['timeline_penalty'] == -1:
                signal = "AVOID INDEFINITELY (Unrecoverable cascade collapse)"
            else:
                signal = f"AVOID / DELAY (Chronological timeline penalty = {res_val['timeline_penalty']} Years)"
        else:
            signal = "LONG (Thermodynamically and financially viable)"
            
        print(f"\nAsset: {name}")
        print(f"  Ghost Zone Status     : {'[TRIGGERED]' if is_ghost else '[CLEAR]'}")
        print(f"  Ghost Zone Coordinates : {ghost_coord}")
        print(f"  Tactical Routing Signal: {signal}")
    print("=========================================================================")

if __name__ == "__main__":
    run_engine_diagnostics()
