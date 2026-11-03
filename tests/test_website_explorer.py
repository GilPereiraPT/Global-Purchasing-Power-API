"""Static wiring tests for the four public EarnWage explorer pages."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "website"
PAGES = ("salaries", "countries", "jobs", "insights")
LANGS = ("en", "pt", "es", "de", "fr", "it", "nl")


def test_explorer_pages_exist_and_use_shared_assets():
    for page in PAGES:
        html = (ROOT / f"{page}.html").read_text(encoding="utf-8")
        assert f'data-page="{page}"' in html
        assert 'id="lang"' in html
        assert 'id="exploreForm"' in html
        assert 'id="results"' in html
        assert 'src="./explore.js"' in html
        assert 'src="./explore-i18n.js"' in html
        for other in PAGES:
            assert f'./{other}.html' in html


def test_language_catalogue_complete():
    raw = (ROOT / "explore-i18n.js").read_text(encoding="utf-8").strip()
    prefix = "window.EarnWageExploreI18n="
    assert raw.startswith(prefix)
    data = json.loads(raw.removeprefix(prefix).rstrip(";"))
    assert tuple(data) == LANGS
    keys = set(data["en"])
    for language in LANGS:
        assert set(data[language]) == keys
        assert all(isinstance(x, str) and x.strip() for x in data[language].values())


def test_homepage_menu_reaches_all_explorer_pages():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    for page in PAGES:
        assert f'href="./{page}.html"' in html


def test_live_api_and_missing_data_policy_are_explicit():
    js = (ROOT / "explore.js").read_text(encoding="utf-8")
    assert "/v1/earnwage/overview?" in js
    assert "/v1/jobs?" in js
    assert "/v1/economy/compare?" in js
    assert 'status==="available"' in js
    assert "rel=\"noopener noreferrer\"" in js
