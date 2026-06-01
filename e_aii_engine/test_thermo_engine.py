import unittest
import numpy as np
from thermo_arbitrage_engine import (
    RegionalThermalMonitor,
    BoundaryLayerStagnationEngine,
    RegularizedGeometricIndicator,
    FinancialCascadeGatingEngine
)

class TestThermoArbitrageEngine(unittest.TestCase):
    def test_landauer_ier_crit(self):
        monitor = RegionalThermalMonitor(e_op=1e-19)
        # At T = 298 K
        ier_298 = monitor.calculate_ier_critical(298.0)
        self.assertTrue(ier_298 > 0)
        
        # Test lower temp (deep space) -> critical IER should be higher
        ier_3 = monitor.calculate_ier_critical(3.0)
        self.assertTrue(ier_3 > ier_298)

    def test_alpha_sigmoid(self):
        monitor = RegionalThermalMonitor(e_op=1e-19, k=3.0)
        # alpha should always be bounded in [0.5, 1.0) for positive IER
        self.assertAlmostEqual(monitor.calculate_alpha(0.0, 298.0), 0.5)
        
        # Test alpha(t) behavior around critical value
        ier_crit = monitor.calculate_ier_critical(298.0)
        self.assertAlmostEqual(monitor.calculate_alpha(ier_crit, 298.0), 0.75)
        self.assertTrue(0.5 < monitor.calculate_alpha(ier_crit * 2.0, 298.0) < 1.0)

    def test_svd_pinv(self):
        # Deficient matrix J
        J = np.array([
            [1.0, 2.0],
            [2.0, 4.0]
        ])
        J_pinv = RegionalThermalMonitor.svd_pinv(J, threshold=1e-12)
        self.assertEqual(J_pinv.shape, (2, 2))
        
        # Test reconstruction J @ J_pinv @ J = J (up to truncation)
        recon = J @ J_pinv @ J
        np.testing.assert_allclose(recon, J, atol=1e-7)

    def test_stagnation_velocity(self):
        engine = BoundaryLayerStagnationEngine(gamma=0.5)
        u_stagnation = engine.compute_stagnation_velocity(120.0, 4.5, 0.75, 302.0)
        self.assertTrue(u_stagnation > 0.0)
        
        # Check margin opex decay
        # Case A: wind = 5.0 (no decay)
        m_drift_a, _ = engine.evaluate_margin_decay(5.0, u_stagnation, 120.0, 50000.0, 0.75)
        self.assertEqual(m_drift_a, 1.0)
        
        # Case B: wind = 0.1 (decay)
        m_drift_b, _ = engine.evaluate_margin_decay(0.1, u_stagnation, 120.0, 50000.0, 0.75)
        self.assertTrue(m_drift_b > 1.0)

    def test_regularized_e_aii(self):
        # Zero input should not collapse, must return 0.0
        n_zero = np.zeros(6)
        e_aii_zero = RegularizedGeometricIndicator.compute_e_aii(n_zero, 'solar')
        self.assertAlmostEqual(e_aii_zero, 0.0, places=12)

        # Standard non-zero vector
        n_vector = np.array([0.1, 0.5, 0.4, 0.3, 0.6, 0.2])
        e_aii_solar = RegularizedGeometricIndicator.compute_e_aii(n_vector, 'solar')
        e_aii_nuclear = RegularizedGeometricIndicator.compute_e_aii(n_vector, 'nuclear')
        self.assertTrue(0.0 < e_aii_solar < 1.0)
        self.assertTrue(0.0 < e_aii_nuclear < 1.0)
        self.assertNotEqual(e_aii_solar, e_aii_nuclear)

    def test_financial_irr_and_gating(self):
        gating_engine = FinancialCascadeGatingEngine(hurdle_rate=0.25)
        
        # Test standard cash flows with positive IRR
        irr = gating_engine.calculate_irr([-100.0, 50.0, 70.0])
        self.assertTrue(0.0 < irr < 1.0)
        
        # Test gating logic under market shock
        res = gating_engine.evaluate_gating(0.60, 1.5, 50000.0)
        self.assertIn('gated_lock', res)
        self.assertIn('timeline_penalty', res)

if __name__ == '__main__':
    unittest.main()
