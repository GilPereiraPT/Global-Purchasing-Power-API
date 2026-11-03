"""Validate wage-group pages and faithful representation of published source data."""
import json
from pathlib import Path

from app.official_group_earnings import catalogue as official_catalogue
from app.official_group_earnings import history as official_history
from app.es_eaes_groups import catalogue as es_catalogue

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "website"


def test_wage_group_and_directory_pages_exist_and_use_api():
    for name in ("wage-groups", "source-directory"):
        html = (WEB / (name + ".html")).read_text(encoding="utf-8")
        assert f'data-page="{name}"' in html
        assert 'src="./wage-library.js"' in html
        assert 'src="./wage-library-i18n.js"' in html
        assert 'id="lang"' in html
    js = (WEB / "wage-library.js").read_text(encoding="utf-8")
    assert '"/v1/sources"' in js
    assert '"/v1/es/earnings/groups"' in js
    assert '"/v1/"+current.toLowerCase()+"/earnings/groups"' in js
    assert 'r.status==="available"' in js
    assert 'if(i>0&&p.year===valid[i-1].year+1)' in js
    assert 'T("noTrend")' in js


def test_translation_catalogue_complete():
    script = (WEB / "wage-library-i18n.js").read_text(encoding="utf-8").strip()
    prefix = "window.EarnWageLibraryI18n="
    assert script.startswith(prefix)
    catalogue = json.loads(script.removeprefix(prefix).rstrip(";"))
    assert tuple(catalogue) == ("en", "pt", "es", "de", "fr", "it", "nl")
    keys = set(catalogue["en"])
    assert "groupNotice" in keys and "noTrend" in keys
    for language in catalogue:
        assert set(catalogue[language]) == keys
        assert all(isinstance(value, str) and value.strip() for value in catalogue[language].values())


def test_official_group_periods_and_precision_remain_unchanged():
    pt = official_catalogue("PT")
    assert pt["precision"] == "published_major_occupation_group"
    assert pt["periods"] == ["2024"]
    sample = official_history("PT", "T")
    assert sample["precision"] == "all_occupations"
    assert sample["observations"]
    assert all(row["period"] == "2024" for row in sample["observations"])

    pk = official_catalogue("PK")
    assert pk["periods"] == ["2020-21", "2024-25"]
    assert official_history("PK", "total")["observations"]

    es = es_catalogue()
    assert es["precision"] == "cno11_major_group"
    assert es["group_count"] == 17


def test_homepage_reaches_new_pages():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'href="./wage-groups.html"' in html
    assert 'href="./source-directory.html"' in html
