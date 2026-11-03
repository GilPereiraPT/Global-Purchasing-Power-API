"""Regression checks for methodological and detail pages in EarnWage website."""
import json
import re
from pathlib import Path

SITE = Path(__file__).resolve().parents[1] / "website"
PAGES = ("methodology", "sources", "country", "occupation")
LANGS = ("en", "pt", "es", "de", "fr", "it", "nl")


def test_pages_and_shared_navigation():
    for name in PAGES:
        html = (SITE / f"{name}.html").read_text(encoding="utf-8")
        assert f'data-page="{name}"' in html
        assert './details.js' in html
        assert './details-i18n.js' in html
        assert 'id="lang"' in html
        for common in ("compare", "salaries", "countries", "jobs", "insights", "about"):
            assert f'./{common}.html' in html


def test_source_and_detail_pages_do_not_embed_fake_numbers():
    js = (SITE / "details.js").read_text(encoding="utf-8")
    for path in ("/v1/countries", "/v1/occupations?lang=",
                 "/v1/economy/compare?", "/v1/earnwage/overview?"):
        assert path in js
    assert 'indicator?.status==="available"' in js
    assert 'record?.status==="available"' in js
    assert 'urlSource(' in js
    assert 'T("unavailable")' in js
    assert "./occupation.html?country=" in (SITE / "explore.js").read_text(encoding="utf-8")
    assert "./country.html?country=" in (SITE / "explore.js").read_text(encoding="utf-8")


def test_translations_have_same_keys_and_are_complete():
    content = (SITE / "details-i18n.js").read_text(encoding="utf-8").strip()
    prefix = "window.EarnWageDetailsI18n="
    assert content.startswith(prefix)
    parsed = json.loads(content.removeprefix(prefix).rstrip(";"))
    assert tuple(parsed) == LANGS
    keys = set(parsed["en"])
    for language in LANGS:
        assert set(parsed[language]) == keys
        assert all(isinstance(value, str) and value.strip() for value in parsed[language].values())
    js = (SITE / "details.js").read_text(encoding="utf-8")
    used = set(re.findall(r'T\("([A-Za-z0-9]+)"\)', js))
    for name in PAGES:
        html = (SITE / f"{name}.html").read_text(encoding="utf-8")
        used.update(re.findall(r'data-d="([A-Za-z0-9]+)"', html))
    assert used <= keys
