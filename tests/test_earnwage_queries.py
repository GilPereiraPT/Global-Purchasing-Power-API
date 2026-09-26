from fastapi.testclient import TestClient

from app.main import app


def test_screen_ready_salary_and_tax_scenarios():
    with TestClient(app) as client:
        r = client.get("/v1/earnwage/overview", params={
            "country": "US", "occupation": "nurse", "region": "NY",
            "annual_gross": 101420})
        assert r.status_code == 200
        data = r.json()
        assert data["country"]["code"] == "US"
        assert data["region"]["selected"] == "NY"
        assert data["national_occupation_wage"]["status"] == "available"
        obs = data["national_occupation_wage"]["observations"][0]
        assert obs["unit"] == "USD/year"
        assert obs["value"] == 101420
        assert data["tax_scenario"]["status"] == "partial_estimate"
        assert data["tax_scenario"]["net_income"] is None
        assert data["net_purchasing_power"]["status"] == "unavailable"
        assert any("state and local" in note for note in data["warnings"])


def test_canadian_hourly_wage_not_annualized_and_quebec_safe():
    with TestClient(app) as client:
        r = client.get("/v1/earnwage/overview?country=CA&occupation=nurse&region=ON")
        assert r.status_code == 200
        data = r.json()
        assert data["tax_scenario"]["status"] == "not_requested"
        assert all(x["unit"] == "CAD/hour"
                   for x in data["national_occupation_wage"]["observations"])
        assert data["national_occupation_wage"]["reference_period"] == "2023-2024"
        missing = client.get("/v1/earnwage/overview?country=CA&occupation=nurse&annual_gross=100000")
        assert missing.json()["tax_scenario"]["status"] == "region_needed"
        qc = client.get("/v1/earnwage/overview?country=CA&occupation=nurse&region=QC&annual_gross=100000")
        assert qc.status_code == 200
        assert qc.json()["tax_scenario"]["status"] == "unavailable"
        assert qc.json()["tax_scenario"]["net_income"] is None


def test_multi_country_compare_does_not_infer_net_or_ppp():
    with TestClient(app) as client:
        res = client.get("/v1/earnwage/compare", params={
            "country_a": "US", "country_b": "CA", "occupation": "nurse",
            "region_a": "TX", "region_b": "ON",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["country_a"]["national_occupation_wage"]["status"] == "available"
        assert data["country_b"]["national_occupation_wage"]["status"] == "available"
        assert data["wage_comparability"]["status"] == "not_normalized"
        assert data["net_purchasing_power"]["value"] is None
        assert data["country_a"]["national_occupation_wage"]["observations"][0]["unit"] == "USD/year"
        assert data["country_b"]["national_occupation_wage"]["observations"][0]["unit"] == "CAD/hour"


def test_real_coverage_and_invalid_region():
    with TestClient(app) as client:
        data = client.get("/v1/earnwage/coverage").json()
        assert data["possible_pairs"] == 560
        assert data["observed_pairs"] == 37
        country = {x["code"]: x for x in data["by_country"]}
        assert country["CA"]["observed_occupations"] == 28
        assert country["US"]["observed_occupations"] == 9
        assert country["PT"]["observed_occupations"] == 0
        assert client.get("/v1/earnwage/overview?country=PT&occupation=nurse&region=TX").status_code == 422
        assert client.get("/v1/earnwage/overview?country=US&occupation=nurse&region=QC").status_code == 422
        assert client.get("/v1/earnwage/overview?country=XX&occupation=nurse").status_code == 404
        assert client.get("/v1/earnwage/compare?country_a=US&country_b=CA&occupation=invalid").status_code == 422
        assert client.get("/v1/earnwage/overview?country=US&occupation=nurse&annual_gross=0").status_code == 422
