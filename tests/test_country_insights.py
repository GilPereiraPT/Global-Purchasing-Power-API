"""Offline tests for persistent country insights and weekly import schedule."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import country_insights as ci
from app.country_insights_store import connect, save_result, read_indicator
from scripts.update_country_insights import WEEK, run


class CountryInsightsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            "EARNWAGE_INSIGHTS_DB": str(Path(self.temp.name) / "insights.sqlite3")})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_latest_non_null_observation_and_history(self):
        with connect() as db:
            save_result(db, "PT", "life_expectancy",
                        [{"year": 2024, "value": 82.1},
                         {"year": 2022, "value": 81.3}], "available")
        current = ci.indicator("PT", "life_expectancy")
        self.assertEqual((current["year"], current["value"]), (2024, 82.1))
        self.assertEqual(ci.indicator("PT", "life_expectancy", year=2023)["status"], "unavailable")
        self.assertEqual(len(ci.indicator("PT", "life_expectancy", history=True)["history"]), 2)

    def test_upstream_failure_keeps_last_valid_value(self):
        with connect() as db:
            save_result(db, "US", "health_coverage",
                        [{"year": 2023, "value": 80}], "available")
            save_result(db, "US", "health_coverage", [],
                        "upstream_unavailable", "TimeoutError")
            item = read_indicator(db, "US", "health_coverage")
        self.assertEqual(item["value"], 80)
        self.assertEqual(item["status"], "available")
        self.assertEqual(item["refresh_status"], "upstream_unavailable")
        self.assertEqual(item["error_type"], "TimeoutError")

    def test_no_data_stays_null(self):
        item = ci.indicator("US", "health_coverage")
        self.assertIsNone(item["value"])
        self.assertEqual(item["status"], "not_imported")

    def test_country_insights_does_not_fetch_network(self):
        with patch.object(ci, "_fetch", side_effect=AssertionError("Network called")):
            item = ci.country_insights("PT")
        self.assertEqual(item["indicators"]["life_expectancy"]["status"], "not_imported")

    def test_importer_stores_real_observations_and_handles_failures(self):
        def fake_fetch(country, code):
            if code == "SP.DYN.LE00.IN":
                return "available", [{"year": 2024, "value": 82.1}], None
            return "upstream_unavailable", [], "TimeoutError"
        with patch("scripts.update_country_insights._fetch", side_effect=fake_fetch), \
             patch("scripts.update_country_insights.time.sleep"):
            counts = run(("PT",), pause=0)
        self.assertEqual(counts["available"], 1)
        self.assertEqual(counts["failed"], len(ci.INDICATORS)-1)
        self.assertEqual(ci.indicator("PT", "life_expectancy")["value"], 82.1)

    def test_uhc_source_is_revised_who_2025_not_legacy(self):
        self.assertEqual(ci.INDICATORS["health_coverage"],
                         ("SH_UHC_SCI", "index_0_100"))
        self.assertEqual(ci.UHC_SERIES["legacy"], "SH.UHC.SRVS.CV.XD")
        with connect() as db:
            result = read_indicator(db, "PT", "health_coverage")
        self.assertEqual(result["indicator_code"], "SH_UHC_SCI")
        self.assertEqual(result["sdg_indicator"], "3.8.1")
        self.assertEqual(result["legacy_indicator_code"], "SH.UHC.SRVS.CV.XD")
        self.assertIn("not the share of people covered", result["note"])
        self.assertIn("/SH_UHC_SCI?", result["source_url"])

    def test_uhc_mocked_official_json_import_preserves_year(self):
        import json
        payload = {
            "value": [
                {"SpatialDim": "PRT", "TimeDim": 2023, "NumericValue": 83.0},
                {"SpatialDim": "PRT", "TimeDim": 2021, "NumericValue": 78.0},
                {"SpatialDim": "PRT", "TimeDim": 2020, "NumericValue": None},
                {"SpatialDim": "USA", "TimeDim": 2023, "NumericValue": 99.0},
            ]
        }

        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self, *args):
                return json.dumps(payload).encode("utf-8")

        def fake_urlopen(request, timeout):
            self.assertIn("/api/UHC_INDEX_REPORTED?", request.full_url)
            self.assertIn("PRT", request.full_url)
            self.assertEqual(timeout, 15)
            return Response()

        with patch.object(ci, "urlopen", side_effect=fake_urlopen):
            status, observations, error = ci._fetch("PT", "SH_UHC_SCI")
        self.assertEqual(status, "available")
        self.assertIsNone(error)
        self.assertEqual(observations, [
            {"year": 2023, "value": 83.0},
            {"year": 2021, "value": 78.0},
        ])
        with connect() as db:
            save_result(db, "PT", "health_coverage", observations, status)
            result = read_indicator(db, "PT", "health_coverage")
        self.assertEqual(result["year"], 2023)
        self.assertEqual(result["value"], 83.0)
        self.assertEqual(result["unit"], "index_0_100")

    def test_uhc_who_failure_can_use_valid_world_bank_mirror(self):
        with patch.object(ci, "_fetch_who_uhc",
                          return_value=("upstream_unavailable", [], "TimeoutError")), \\
             patch.object(ci, "_fetch_world_bank",
                          return_value=("available", [
                              {"year": 2023, "value": 82.0}], None)) as mirror:
            status, observations, error = ci._fetch("ES", "SH_UHC_SCI")
        self.assertEqual(status, "available")
        self.assertEqual(observations[0]["year"], 2023)
        self.assertIsNone(error)
        mirror.assert_called_once_with("ES", "SH_UHC_SCI")

    def test_uhc_invalid_who_values_do_not_reach_database(self):
        import json
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self, *args):
                return json.dumps({"value": [
                    {"SpatialDim": "PRT", "TimeDim": 2023,
                     "NumericValue": 150}]}).encode("utf-8")
        with patch.object(ci, "urlopen", return_value=Response()):
            result = ci._fetch_who_uhc("PT")
        self.assertEqual(result[0], "upstream_unavailable")
        self.assertEqual(result[1], [])
        self.assertEqual(result[2], "ValueError")

    def test_weekly_rotation_and_safety(self):
        self.assertEqual(len(WEEK), 7)
        self.assertEqual(set(sum((list(pair) for pair in WEEK), [])), set(ci.ISO3))
        self.assertEqual(ci.safety("BR")["alternative"]["sdg_indicator"], "16.1.4")


if __name__ == "__main__":
    unittest.main()
