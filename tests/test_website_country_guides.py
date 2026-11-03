"""Smoke checks for the three sourced country-guide integrations."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/"website"

def test_country_page_loads_data_guides():
    page=(ROOT/"country.html").read_text(encoding="utf-8")
    js=(ROOT/"details.js").read_text(encoding="utf-8")
    assert 'id="countryGuide"' in page
    assert 'src="./country-guides.js"' in page
    assert "EarnWageCountryGuides?.render" in js

def test_countries_page_has_links():
    page=(ROOT/"countries.html").read_text(encoding="utf-8")
    assert 'id="countryGuidesLinks"' in page
    assert 'src="./country-guides.js"' in page

def test_sources_and_source_categories_are_distinct():
    code=(ROOT/"country-guides.js").read_text(encoding="utf-8")
    for country in ('"ES"','"IE"','"GB"'):
        assert country in code
    assert "es_ine_eaes" not in code  # no invented numeric series
    assert "ireland_public_sector_entry" in code
    assert "ireland_cso_occupational_group_context" in code
    assert "national_occupation_wage" in code
    assert "record?.status" in code
    assert "new Intl.NumberFormat" in code
    assert "http://www." not in code
