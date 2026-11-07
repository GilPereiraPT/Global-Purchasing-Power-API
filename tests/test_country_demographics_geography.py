"""Regression tests for the eleven newly configured WDI geography/demography series."""
import json
from pathlib import Path

from app.country_insights import INDICATORS
from app.country_insights_store import connect, read_indicator, save_result

NEW = {
    "population_total": ("SP.POP.TOTL", "persons"),
    "population_growth": ("SP.POP.GROW", "annual_percent"),
    "population_density": ("EN.POP.DNST", "people_per_square_km_land"),
    "urban_population": ("SP.URB.TOTL.IN.ZS", "percent_of_population"),
    "fertility_rate": ("SP.DYN.TFRT.IN", "births_per_woman"),
    "birth_rate": ("SP.DYN.CBRT.IN", "births_per_1000_people"),
    "death_rate": ("SP.DYN.CDRT.IN", "deaths_per_1000_people"),
    "surface_area": ("AG.SRF.TOTL.K2", "square_km"),
    "land_area": ("AG.LND.TOTL.K2", "square_km"),
    "population_ages_0_14": ("SP.POP.0014.TO.ZS", "percent_of_population"),
    "population_ages_65_plus": ("SP.POP.65UP.TO.ZS", "percent_of_population"),
}

def test_expected_official_codes_and_units():
    assert len(INDICATORS) == 40
    for name, value in NEW.items():
        assert INDICATORS[name] == value

def test_new_indicators_are_missing_until_imported(tmp_path, monkeypatch):
    monkeypatch.setenv("EARNWAGE_INSIGHTS_DB", str(tmp_path / "insights.sqlite3"))
    with connect() as db:
        missing = read_indicator(db, "PT", "population_total")
        assert missing["status"] == "not_imported"
        assert missing["value"] is None
        save_result(db, "PT", "population_total", [
            {"year": 2024, "value": 10500000.0},
            {"year": 2022, "value": 10300000.0},
        ], "available")
        saved = read_indicator(db, "PT", "population_total", history=True)
        assert saved["year"] == 2024
        assert saved["value"] == 10500000.0
        assert len(saved["history"]) == 2
        assert saved["source_url"].startswith("https://api.worldbank.org/")
        save_result(db, "PT", "population_total", [], "upstream_unavailable", "TimeoutError")
        retained = read_indicator(db, "PT", "population_total")
        assert retained["status"] == "available"
        assert retained["refresh_status"] == "upstream_unavailable"

def test_country_site_locales_and_metric_lists():
    website = Path(__file__).resolve().parents[1] / "website"
    js=(website / "country-data-i18n.js").read_text(encoding="utf-8")
    prefix="window.EarnWageCountryDataLocale="
    data=json.loads(js.removeprefix(prefix).strip().rstrip(";"))
    for language in ("pt", "en", "es", "de", "fr", "it", "nl"):
        assert len(data[language]["metric"]) == 40
        assert data[language]["geography"]
        assert data[language]["demography"]
        assert all(data[language]["metric"][name] for name in NEW)
    ui=(website / "country-data.js").read_text(encoding="utf-8")
    for name in NEW:
        assert '"'+name+'"' in ui
    assert '"square_km"' in ui
    assert '"people_per_square_km_land"' in ui
