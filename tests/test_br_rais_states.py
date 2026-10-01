"""Brazil 2025 regional RAIS: source-specific CBO/UF observations only."""
from fastapi.testclient import TestClient

from app.br_rais_states import coverage, wage, load
from app.main import app


def test_2025_brazil_state_import_and_provenance():
    assert load() == 993
    c = coverage()
    assert c["status"] == "available"
    assert c["observed_occupations"] == 38
    assert c["states_with_data"] == c["total_states"] == 27
    assert c["observed_cells"] == 993
    sp = wage("accountant", "SP")
    assert sp["status"] == "available"
    assert sp["value"] == 6266
    assert sp["currency"] == "BRL"
    assert sp["measure"] == "median_december_remuneration"
    assert sp["cbo_code"] == "252210"
    assert sp["links"] == 55862
    assert sp["source_url"] == "https://99k.com.br/carreiras/contador"
    assert wage("accountant", "DF")["value"] == 8427
    assert wage("accountant", None)["status"] == "not_requested"
    assert wage("manager", "SP")["status"] == "unavailable"


def test_brazil_ui_and_api_state_selection():
    with TestClient(app) as c:
        regions = c.get("/v1/regions/BR")
        assert regions.status_code == 200
        data = regions.json()
        assert data["visible"] is True
        options = {item["code"]: item["name"] for item in data["options"]}
        assert len(options) == 27
        assert options["SP"] == "São Paulo"
        assert options["DF"] == "Distrito Federal"

        coverage_data = c.get("/v1/br/rais/regional/coverage")
        assert coverage_data.status_code == 200
        assert coverage_data.json()["observed_cells"] == 993

        page = c.get("/v1/earnwage/overview", params={
            "country": "BR", "occupation": "accountant", "region": "SP"
        })
        assert page.status_code == 200
        result = page.json()
        assert result["regional_occupation_wage"]["value"] == 6266
        assert result["national_occupation_wage"]["geography"] == "national"
        assert result["regional_occupation_wage"]["precision"] == "occupation_cbo2002_6_digit"
        assert result["region"]["selected"] == "SP"

        missing = c.get("/v1/earnwage/overview", params={
            "country": "BR", "occupation": "manager", "region": "SP"
        }).json()
        assert missing["regional_occupation_wage"]["status"] == "unavailable"
        assert missing["national_occupation_wage"]["status"] == "available"

        bad = c.get("/v1/earnwage/overview", params={
            "country": "BR", "occupation": "accountant", "region": "INVALID"
        })
        assert bad.status_code == 422

        pair = c.get("/v1/earnwage/compare", params={
            "country_a": "BR", "country_b": "IN",
            "occupation": "accountant", "region_a": "DF"
        })
        assert pair.status_code == 200
        assert pair.json()["country_a"]["regional_occupation_wage"]["value"] == 8427
