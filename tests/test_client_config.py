from fastapi.testclient import TestClient

from app.client_config import PRODUCT, REGIONS
from app.main import app


def test_earnwage_public_config():
    with TestClient(app) as client:
        config = client.get("/v1/app-config")
        assert config.status_code == 200
        data = config.json()
        assert data["product"]["name"] == "EarnWage"
        assert data["product"]["portuguese_language"] == "pt"
        assert data["product"]["supported_languages"] == ["en","pt","es","de","fr","it","nl"]
        assert data["country_count"] == 14
        assert data["occupation_count"] == 40
        assert data["region_selector"]["visibility"] == "conditional"
        assert data["region_selector"]["required_for_initial_comparison"] is False


def test_progressive_region_selector_and_national_tax_only():
    with TestClient(app) as client:
        assert client.get("/v1/regions/PT").json()["visible"] is False
        us = client.get("/v1/regions/US").json()
        assert us["visible"] is True
        assert us["region_type"] == "state"
        assert len(us["options"]) == 50
        assert {x["code"] for x in us["options"]} == {x[0] for x in REGIONS["US"]["options"]}
        assert us["tax_region_model_status"] == "not_implemented"
        ca = client.get("/v1/regions/CA").json()
        assert len(ca["options"]) == 13
        assert any(x["code"] == "QC" for x in ca["options"])
        assert "Québec" in ca["note"]["pt"]
        assert client.get("/v1/regions/XX").status_code == 404
        resp = client.get("/v1/tax-components/US?annual_gross=101420")
        assert resp.json()["net_income"] is None
