from fastapi.testclient import TestClient

from app.main import app
from app.providers import parse_eurostat

def test_catalogue_and_health():
    with TestClient(app) as client:
        assert client.get("/v1/health").json()["status"] == "ok"
        countries = client.get("/v1/countries").json()["countries"]
        assert {"IN", "BR", "PK"} <= {c["code"] for c in countries}
        jobs = client.get("/v1/occupations?lang=pt").json()["occupations"]
        assert any(j["id"] == "accountant" and j["label"] == "Contabilista" for j in jobs)

def test_missing_data_not_invented():
    with TestClient(app) as client:
        response = client.get("/v1/inflation/IN")
        assert response.json()["status"] == "unavailable"
        assert client.get("/v1/compare?country_a=PT&country_b=XX").status_code == 404
        assert client.get("/v1/compare?country_a=PT&country_b=DE&occupation=unknown").status_code == 422

def test_sparse_jsonstat_dimension_order():
    payload = {
        "id": ["geo", "unit", "coicop", "time"], "size": [1, 1, 1, 2],
        "dimension": {
            "geo": {"category": {"index": {"PT": 0}}},
            "unit": {"category": {"index": {"I25": 0}}},
            "coicop": {"category": {"index": {"CP00": 0}}},
            "time": {"category": {"index": {"2026-01": 0, "2026-02": 1}}},
        },
        "value": {"0": 101.5, "1": 102.0},
    }
    assert parse_eurostat(payload, "PT") == [
        {"period": "2026-01", "index": 101.5},
        {"period": "2026-02", "index": 102.0},
    ]
