"""Static checks for the standalone EarnWage Compare page.

Browser QA remains necessary before deployment.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/"website"
LANGUAGES=("en","pt","es","de","fr","it","nl")


def test_compare_page_links_and_accessible_tabs():
    page=(ROOT/"compare.html").read_text(encoding="utf-8")
    assert 'id="compareForm"' in page
    assert 'id="countryA"' in page and 'id="countryB"' in page
    assert 'id="grossA"' in page and 'id="grossB"' in page
    assert 'id="occupation"' in page
    assert 'id="taxScenarioA"' in page and 'id="taxScenarioB"' in page
    assert 'role="tablist"' in page
    assert 'role="tabpanel"' in page
    assert 'id="lang"' in page
    for path in ("compare.js","compare-i18n.js","explore-i18n.js"):
        assert './'+path in page
    for route in ("index","salaries","countries","jobs","insights"):
        assert './'+route+'.html' in page


def test_compare_locale_catalogue_complete():
    raw=(ROOT/"compare-i18n.js").read_text(encoding="utf-8").strip()
    prefix="window.EarnWageCompareI18n="
    assert raw.startswith(prefix)
    catalogue=json.loads(raw.removeprefix(prefix).rstrip(";"))
    assert tuple(catalogue)==LANGUAGES
    expected=set(catalogue["en"])
    for lang in LANGUAGES:
        assert set(catalogue[lang])==expected
        assert all(isinstance(v,str) and v.strip() for v in catalogue[lang].values())


def test_compare_uses_real_api_and_does_not_infer_net_income():
    js=(ROOT/"compare.js").read_text(encoding="utf-8")
    for endpoint in (
        "/v1/countries","/v1/occupations?lang=",
        "/v1/regions/","/v1/tax/assumptions/","/v1/earnwage/compare?",
    ):
        assert endpoint in js
    assert '["verified","benchmark_estimate"]' in js
    assert 'p?.status==="available"' in js
    assert 'gross_purchasing_power_equivalence' in js
    assert 'net_purchasing_power' in js
    assert 'localStorage.setItem("earnwage_lang"' in js
    assert 'URLSearchParams' in js


def test_navigation_to_compare_page():
    home=(ROOT/"index.html").read_text(encoding="utf-8")
    assert 'href="./compare.html"' in home
    explorer=(ROOT/"explore.js").read_text(encoding="utf-8")
    assert "./compare.html?country_a=" in explorer
