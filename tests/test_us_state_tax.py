"""Tests for scoped US 2026 state wage/payroll components."""
import unittest
from app.us_state_tax import state_wage_income_tax
from app.client_config import region_configuration

class StateTaxTest(unittest.TestCase):
    def test_texas(self):
        r = state_wage_income_tax("TX", 2026, 94750)
        self.assertEqual(r["state_wage_income_tax"], 0.0)
        self.assertEqual(region_configuration("US", "TX")["tax_region_model_status"], "wage_income_tax_only")

    def test_california_sdi_not_income_tax(self):
        r = state_wage_income_tax("CA", 2026, 94750)
        self.assertEqual(r["status"], "partial_components")
        self.assertEqual(r["employee_state_disability_insurance"], 1231.75)
        self.assertIsNone(r["state_wage_income_tax"])
        self.assertEqual(region_configuration("US", "CA")["tax_region_model_status"], "partial_components")

    def test_new_york_not_fabricated(self):
        r = state_wage_income_tax("NY", 2026, 94750)
        self.assertIsNone(r["state_wage_income_tax"])
        self.assertEqual(r["standard_deduction_single_reference"], 8000)

    def test_unsupported_year(self):
        self.assertEqual(state_wage_income_tax("TX", 2025)["status"], "unavailable")

if __name__ == "__main__":
    unittest.main()
