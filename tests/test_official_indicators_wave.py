"""EarnWage official open-data expansion: catalogue and read-only guarantees."""
from unittest.mock import patch

from app.country_insights import INDICATORS, INDICATOR_METADATA, _fetch
from app.country_insights_store import connect, read_indicator, save_result
from scripts.update_country_insights import run


def test_wave_catalogue_unique_and_correct():
    assert len(INDICATORS) == 29
    assert len(INDICATOR_METADATA) == 16
    assert len({code for code, _ in INDICATORS.values()}) == 29
    assert INDICATORS["intentional_homicides"] == (
        "VC.IHR.PSRC.P5", "per_100000_people")
    assert INDICATORS["intentional_homicides_female"][0] == "VC.IHR.PSRC.FE.P5"
    assert INDICATORS["intentional_homicides_male"][0] == "VC.IHR.PSRC.MA.P5"
    assert INDICATORS["control_of_corruption"] == (
        "GOV_WGI_CC_SC", "governance_score_0_100")
    assert INDICATORS["pm25_air_pollution"][0] == "EN.ATM.PM25.MC.M3"


def test_new_indicators_do_not_imply_data_before_import(tmp_path, monkeypatch):
    monkeypatch.setenv("EARNWAGE_INSIGHTS_DB", str(tmp_path / "insights.sqlite3"))
    with connect() as db:
        corruption = read_indicator(db, "PT", "control_of_corruption")
        crime = read_indicator(db, "BR", "intentional_homicides")
        assert corruption["value"] is None
        assert corruption["status"] == "not_imported"
        assert corruption["family"] == "corruption"
        assert corruption["underlying_source"] == "World Bank Worldwide Governance Indicators"
        assert crime["status"] == "not_imported"


def test_wave_import_retains_exact_year_and_source(tmp_path, monkeypatch):
    monkeypatch.setenv("EARNWAGE_INSIGHTS_DB", str(tmp_path / "insights.sqlite3"))
    with connect() as db:
        save_result(db, "PT", "control_of_corruption",
                    [{"year": 2024, "value": 71.5}], "available")
        item = read_indicator(db, "PT", "control_of_corruption", history=True)
        assert item["year"] == 2024
        assert item["value"] == 71.5
        assert item["source_url"].endswith(
            "/indicator/GOV_WGI_CC_SC?format=json&per_page=1000")
        assert len(item["history"]) == 1
        save_result(db, "PT", "control_of_corruption", [],
                    "upstream_unavailable", "TimeoutError")
        retained = read_indicator(db, "PT", "control_of_corruption")
        assert retained["value"] == 71.5
        assert retained["refresh_status"] == "upstream_unavailable"


def test_dry_run_never_fetches_official_api(tmp_path, monkeypatch):
    monkeypatch.setenv("EARNWAGE_INSIGHTS_DB", str(tmp_path / "insights.sqlite3"))
    with patch("scripts.update_country_insights._fetch",
               side_effect=AssertionError("Network called")):
        summary = run(("PT",), pause=0,
                      indicators=["control_of_corruption", "intentional_homicides"],
                      missing_only=True, dry_run=True)
    assert summary["planned"] == 2
    assert summary["available"] == 0
    with connect() as db:
        assert db.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 0


def test_unknown_year_never_assumes_zero_conflict_deaths(tmp_path, monkeypatch):
    monkeypatch.setenv("EARNWAGE_INSIGHTS_DB", str(tmp_path / "insights.sqlite3"))
    with connect() as db:
        missing = read_indicator(db, "US", "battle_related_deaths")
    assert missing["value"] is None
    assert missing["status"] == "not_imported"
    assert "never be interpreted as zero" in missing["note"]
