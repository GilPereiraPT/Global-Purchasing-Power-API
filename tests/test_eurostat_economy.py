"""Eurostat importer: exact JSON-stat selection, safe cache, no HTTP-time downloads."""
import json
from urllib.parse import parse_qs, urlparse

import pytest

from app import eurostat_economy as eu


def payload(spec, country, value=123.4):
    dimensions = ["freq", "unit", "coicop", "geo", "time"] if (
        spec["dataset"] == "prc_hicp_minr") else [
        "freq", "na_item", "ppp_cat", "geo", "time"] if (
        spec["dataset"] == "prc_ppp_ind") else [
        "freq", "currency", "estruct", "ecase", "geo", "time"]
    periods = ["2024-12", "2025-01"] if spec["frequency"] == "monthly" else ["2023", "2024"]
    categories = {key: [val] for key, val in spec["filters"].items()}
    categories.update(geo=[country], time=periods)
    return {
        "id": dimensions, "size": [len(categories[key]) for key in dimensions],
        "dimension": {key: {"category": {"index": {
            val: index for index, val in enumerate(categories[key])}}}
            for key in dimensions},
        "value": {"0": 100.0, "1": value},
    }


@pytest.mark.parametrize("name", eu.SERIES)
def test_decode_exact_dimensions(name):
    spec = eu.SERIES[name]
    observations = eu.decode(payload(spec, "PT"), "PT", spec)
    assert len(observations) == 2
    assert observations[-1][1] == 123.4
    url = urlparse(eu.source_url("PT", spec))
    assert url.path.endswith(spec["dataset"])
    assert parse_qs(url.query)["geo"] == ["PT"]
    for key, value in spec["filters"].items():
        assert parse_qs(url.query)[key] == [value]


def test_decode_rejects_ambiguous_series():
    spec = eu.SERIES["net_annual_earnings_reference"]
    raw = payload(spec, "PT")
    raw["id"].append("unexpected")
    raw["size"].append(1)
    with pytest.raises(ValueError):
        eu.decode(raw, "PT", spec)


def test_failed_refresh_retains_verified_observation(tmp_path, monkeypatch):
    from app import country_insights_store as store
    monkeypatch.setenv("EARNWAGE_INSIGHTS_DB", str(tmp_path / "insights.sqlite3"))
    with store.connect() as db:
        eu.ensure_tables(db)
        eu.save(db, "PT", "net_annual_earnings_reference",
                [("2024", 23000.0)], "available")
        eu.save(db, "PT", "net_annual_earnings_reference",
                [], "failed", "TimeoutError")
        record = eu.read(db, "PT", "net_annual_earnings_reference")
    assert record["status"] == "available"
    assert record["value"] == 23000.0
    assert record["period"] == "2024"
    assert record["refresh_status"] == "failed"
    assert record["error_type"] == "TimeoutError"


def test_native_eurostat_routes_without_live_fetch(tmp_path, monkeypatch):
    from app import country_insights_store as store
    from tests.test_native_wsgi import request
    monkeypatch.setenv("EARNWAGE_INSIGHTS_DB", str(tmp_path / "insights.sqlite3"))
    code, coverage, _ = request("/v1/eurostat/coverage")
    assert code == 200 and coverage["count"] == 9
    code, row, _ = request("/v1/eurostat/PT/hicp_annual_change_monthly")
    assert code == 200 and row["status"] == "not_imported"
    assert request("/v1/eurostat/US/hicp_annual_change_monthly")[0] == 404
    assert request("/v1/eurostat/compare", {"country_a": "PT", "country_b": "DE"})[0] == 200
    assert request("/v1/eurostat/compare", {"country_a": "PT", "country_b": "US"})[0] == 422
