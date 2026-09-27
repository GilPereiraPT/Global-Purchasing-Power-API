"""No live network required for country-insights contract tests."""
import unittest
from unittest.mock import patch

from app import country_insights as ci


class CountryInsightsTests(unittest.TestCase):
    def test_latest_non_null_observation_and_history(self):
        observations = [{"year": 2024, "value": 82.1},
                        {"year": 2022, "value": 81.3}]
        with patch.object(ci, "_fetch", return_value=("available", observations, None)):
            current = ci.indicator("PT", "life_expectancy")
            self.assertEqual((current["year"], current["value"]), (2024, 82.1))
            self.assertEqual(ci.indicator("PT", "life_expectancy", year=2023)["status"], "unavailable")
            self.assertEqual(len(ci.indicator("PT", "life_expectancy", history=True)["history"]), 2)

    def test_upstream_failure_not_zero(self):
        with patch.object(ci, "_fetch", return_value=("upstream_unavailable", [], "URLError")):
            item = ci.indicator("US", "health_coverage")
            self.assertIsNone(item["value"])
            self.assertEqual(item["status"], "upstream_unavailable")

    def test_safety_never_substitutes_homicide(self):
        item = ci.safety("BR")
        self.assertIsNone(item["value"])
        self.assertEqual(item["alternative"]["sdg_indicator"], "16.1.4")

    def test_country_mapping(self):
        self.assertEqual(len(ci.ISO3), 14)
        self.assertEqual(ci.ISO3["GB"], "GBR")


if __name__ == "__main__":
    unittest.main()
