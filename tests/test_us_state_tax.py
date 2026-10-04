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
        self.assertEqual(r["state_taxable_income_preview"], 86750)
        self.assertEqual(r["state_income_tax_schedule_before_credits"], 4550.90)
        self.assertEqual(r["status"], "partial_components")
        self.assertEqual(region_configuration("US", "NY")["tax_region_model_status"], "partial_components")

    def test_pennsylvania_pre_credit_only(self):
        r = state_wage_income_tax("PA", 2026, "100000.00")
        self.assertEqual(r["state_income_tax_schedule_before_credits"], 3070.00)
        self.assertEqual(r["standard_deduction_single_reference"], 0)
        self.assertIsNone(r["state_wage_income_tax"])
        self.assertEqual(region_configuration("US", "PA")["tax_region_model_status"], "partial_components")
        self.assertIsNone(state_wage_income_tax("PA")["state_income_tax_schedule_before_credits"])

    def test_half_cent_rounded_up(self):
        # 5 * 1.3% = 0.065; binary float/banker's rounding must not lose a cent.
        self.assertEqual(state_wage_income_tax("CA", 2026, "5")["employee_state_disability_insurance"], 0.07)
        self.assertEqual(state_wage_income_tax("NY", 2026, "8005")["state_income_tax_schedule_before_credits"], 0.20)

    def test_ny_recapture_boundary(self):
        self.assertEqual(state_wage_income_tax("NY", 2026, "107650")["state_income_tax_schedule_before_credits"], 5312.00)
        self.assertIsNone(state_wage_income_tax("NY", 2026, "107650.01")["state_income_tax_schedule_before_credits"])
        self.assertEqual(state_wage_income_tax("NY", 2026, "16500")["state_income_tax_schedule_before_credits"], 331.50)

    def test_invalid_amounts_do_not_produce_taxes(self):
        for region in ("TX", "CA", "NY", "PA"):
            for gross in ("NaN", "Infinity", "-1", "0", "100000001"):
                with self.subTest(region=region, gross=gross), self.assertRaises(ValueError):
                    state_wage_income_tax(region, 2026, gross)

    def test_overview_preserves_partial_result(self):
        from app.earnwage_queries import fiscal_context
        r = fiscal_context("US", "PA", "100000", 2026)
        self.assertIsNone(r["net_income"])
        self.assertEqual(r["state_wage_income_tax"]["state_income_tax_schedule_before_credits"], 3070.00)

    def test_unsupported_year(self):
        self.assertEqual(state_wage_income_tax("TX", 2025)["status"], "unavailable")

if __name__ == "__main__":
    unittest.main()
