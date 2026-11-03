"""Read-only economic history API and public website page checks."""
import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.country_insights_store import connect, save_result
from app.main import economy_history

SITE = Path(__file__).resolve().parents[1] / "website"
LANGS = ("en", "pt", "es", "de", "fr", "it", "nl")


def test_history_preserves_true_observation_years_and_missing_gaps(monkeypatch, tmp_path):
    monkeypatch.setenv("EARNWAGE_INSIGHTS_DB", str(tmp_path / "insights.sqlite3"))
    with connect() as db:
        save_result(db, "PT", "inflation_annual",
                    [{"year": 2021, "value": 1.3}, {"year": 2023, "value": 4.3}],
                    "available")
    response = economy_history("pt", "inflation_annual")
    assert response["country"] == "PT"
    assert response["status"] == "available"
    assert [v["year"] for v in response["history"]] == [2023, 2021]
    assert response["value"] == 4.3
    assert response["source_url"].startswith("https://")


def test_history_rejects_unsupported_indicator_and_country():
    with pytest.raises(HTTPException) as err:
        economy_history("PT", "gdp_per_capita")
    assert err.value.status_code == 422
    with pytest.raises(HTTPException) as err:
        economy_history("ZZ", "inflation_annual")
    assert err.value.status_code == 404


def test_history_and_coverage_pages_and_locale_catalogue():
    for page in ("history", "coverage"):
        html = (SITE / (page + ".html")).read_text(encoding="utf-8")
        assert 'data-page="' + page + '"' in html
        assert 'src="./history.js"' in html
        assert 'id="lang"' in html
        assert 'id="results"' in html
    code = (SITE / "history-i18n.js").read_text(encoding="utf-8").strip()
    prefix = "window.EarnWageHistoryI18n="
    assert code.startswith(prefix)
    data = json.loads(code.removeprefix(prefix).rstrip(";"))
    assert tuple(data) == LANGS
    for lang in LANGS:
        assert set(data[lang]) == set(data["en"])
        assert all(isinstance(t, str) and t.strip() for t in data[lang].values())


def test_history_charts_never_interpolate_or_fabricate_observations():
    js = (SITE / "history.js").read_text(encoding="utf-8")
    assert "/v1/economy/history/" in js
    assert "/v1/economy/coverage" in js
    assert "if(b.year!==a.year+1)continue" in js
    assert "status===\"available\"" in js
    assert "Number.isFinite" in js
