"""Eurostat importer: exact JSON-stat selection, safe cache, no HTTP-time downloads."""
import io
import json
from urllib.parse import parse_qs, urlparse

import pytest

from app import eurostat_economy as eu


def payload(spec, country, value=123.4):
    dimensions = ["freq", "unit", "coicop18", "geo", "time"] if (
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
    from app.native_wsgi import application
    from urllib.parse import urlencode
    def request(path, params=None):
        statuses = []
        def start_response(status, headers):
            statuses.append(status)
        environ = {"PATH_INFO": path, "REQUEST_METHOD": "GET",
                   "QUERY_STRING": urlencode(params or {}),
                   "wsgi.input": io.BytesIO(b"")}
        body = b"".join(application(environ, start_response))
        return int(statuses[0].split()[0]), json.loads(body), {}
    monkeypatch.setenv("EARNWAGE_INSIGHTS_DB", str(tmp_path / "insights.sqlite3"))
    code, coverage, _ = request("/v1/eurostat/coverage")
    assert code == 200 and coverage["count"] == 9
    code, row, _ = request("/v1/eurostat/PT/hicp_annual_change_monthly")
    assert code == 200 and row["status"] == "not_imported"
    assert request("/v1/eurostat/US/hicp_annual_change_monthly")[0] == 404
    assert request("/v1/eurostat/compare", {"country_a": "PT", "country_b": "DE"})[0] == 200
    assert request("/v1/eurostat/compare", {"country_a": "PT", "country_b": "US"})[0] == 422


def test_admin_import_requires_configured_secret(tmp_path, monkeypatch):
    from app.native_wsgi import application
    monkeypatch.setenv("EARNWAGE_INSIGHTS_DB", str(tmp_path / "insights.sqlite3"))
    monkeypatch.delenv("EARNWAGE_ADMIN_TOKEN", raising=False)
    statuses = []
    def start_response(status, headers):
        statuses.append(status)
    environ = {"PATH_INFO": "/v1/admin/eurostat/import",
               "REQUEST_METHOD": "POST", "CONTENT_LENGTH": "2",
               "wsgi.input": io.BytesIO(b"{}")}
    result = json.loads(b"".join(application(environ, start_response)))
    assert statuses[0].startswith("503")
    assert result["error"] == "admin_not_configured"


def test_admin_import_auth_and_cors(tmp_path, monkeypatch):
    from app.native_wsgi import application
    monkeypatch.setenv("EARNWAGE_INSIGHTS_DB", str(tmp_path / "insights.sqlite3"))
    monkeypatch.setenv("EARNWAGE_ADMIN_TOKEN", "z" * 40)
    payload = json.dumps({"country": "PT", "indicator": "hicp_annual_change_monthly"}).encode()
    def send(method, token=None, origin="https://gilpereirapt.github.io"):
        statuses, headers = [], []
        def start_response(status, response_headers):
            statuses.append(status)
            headers.extend(response_headers)
        environ = {"PATH_INFO": "/v1/admin/eurostat/import",
                   "REQUEST_METHOD": method, "HTTP_ORIGIN": origin,
                   "CONTENT_LENGTH": str(len(payload)),
                   "wsgi.input": io.BytesIO(payload)}
        if token is not None:
            environ["HTTP_X_EARNWAGE_ADMIN_TOKEN"] = token
        result = b"".join(application(environ, start_response))
        return statuses[0], dict(headers), json.loads(result) if result else None
    assert send("POST")[0].startswith("401")
    assert send("POST", "wrong")[0].startswith("401")
    assert send("POST", "z" * 40, "https://evil.example")[0].startswith("403")
    status, headers, _ = send("OPTIONS")
    assert status.startswith("204")
    assert headers["Access-Control-Allow-Headers"].find("X-EarnWage-Admin-Token") >= 0
    monkeypatch.setattr(eu, "fetch", lambda code, spec: [("2025-01", 2.5)])
    status, _, result = send("POST", "z" * 40)
    assert status.startswith("200")
    assert result["import_status"] == "available"
    assert result["indicator"]["value"] == 2.5


def test_hicp_2026_uses_coicop18_dimension_and_total():
    spec = eu.SERIES["hicp_annual_change_monthly"]
    assert spec["dataset"] == "prc_hicp_minr"
    assert spec["filters"]["coicop18"] == "TOTAL"
    assert spec["filters"]["unit"] == "RCH_A"
    assert parse_qs(urlparse(eu.source_url("PT", spec)).query)["coicop18"] == ["TOTAL"]


def test_ons_monthly_cpi():
    raw = {"months": [{"date": "2026 JUL", "value": "3.2"},
                      {"date": "2026 AUG", "value": "3.1"},
                      {"date": "2025", "value": "5.0"}]}
    assert eu.decode_ons_cpi(raw) == [("2026-07", 3.2), ("2026-08", 3.1)]


def test_uk_cpi_metadata_and_missing_other_series(tmp_path, monkeypatch):
    from app import country_insights_store as store
    monkeypatch.setenv("EARNWAGE_INSIGHTS_DB", str(tmp_path / "ons.sqlite3"))
    monkeypatch.setattr(eu, "fetch_ons_cpi", lambda: [("2026-08", 3.1)])
    assert eu.fetch("GB", eu.SERIES["hicp_annual_change_monthly"]) == [("2026-08", 3.1)]
    assert eu.fetch("GB", eu.SERIES["net_annual_earnings_reference"]) == [("2024", 41074.0), ("2025", 43027.0)]
    assert "prc_ppp_ind" in eu.source_url("GB", eu.SERIES["household_price_level_eu27"])
    with store.connect() as db:
        eu.ensure_tables(db)
        eu.save(db, "GB", "hicp_annual_change_monthly", [("2026-08", 3.1)], "available")
        row = eu.read(db, "GB", "hicp_annual_change_monthly")
    assert row["source"] == "ONS" and row["dataset"] == "MM23/D7G7"
    assert row["value"] == 3.1 and row["period"] == "2026-08"


def test_uk_oecd_net_earnings_provenance(tmp_path, monkeypatch):
    from app import country_insights_store as store
    monkeypatch.setenv("EARNWAGE_INSIGHTS_DB", str(tmp_path / "uk.sqlite3"))
    with store.connect() as db:
        eu.ensure_tables(db)
        eu.save(db, "GB", "net_annual_earnings_reference",
                eu.fetch("GB", eu.SERIES["net_annual_earnings_reference"]), "available")
        row = eu.read(db, "GB", "net_annual_earnings_reference")
    assert row["value"] == 43027.0 and row["period"] == "2025"
    assert row["unit"] == "GBP_per_year" and row["source"] == "OECD"
    assert "Table 6.26" in row["dataset"]
