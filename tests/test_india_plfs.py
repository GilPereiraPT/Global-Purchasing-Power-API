"""India PLFS broad salary context stays separate from occupation wages."""
from fastapi.testclient import TestClient
from app.main import app
from app.in_plfs import earnings, wage_sources


def test_official_plfs_2025_statement_11_values_and_scope():
    item = earnings()
    assert item["national_average"] == 22699
    assert item["values"]["rural"]["person"] == 17841
    assert item["values"]["urban"]["person"] == 26247
    assert item["values"]["rural_urban"]["male"] == 24217
    assert item["unit"] == "INR/month"
    assert item["precision"] == "all_regular_wage_salaried_workers"
    assert item["published_year"] == 2026
    assert item["geography"] == "national"


def test_india_sources_do_not_fabricate_specific_wages():
    sources = wage_sources()
    assert sources["exact_occupation_wages"]["status"] == "pending_official_microdata_analysis"
    assert sources["regional_occupation_wages"]["status"] == "pending_official_microdata_analysis"
    assert "2016" in sources["older_occupational_wage_survey"]["reference_period"]


def test_india_api_context_independent_of_profession():
    with TestClient(app) as client:
        r = client.get("/v1/in/plfs/earnings")
        assert r.status_code == 200
        assert r.json()["national_average"] == 22699
        sources = client.get("/v1/in/wage-sources")
        assert sources.status_code == 200
        overview = client.get("/v1/earnwage/overview?country=IN&occupation=nurse")
        assert overview.status_code == 200
        result = overview.json()
        assert result["india_plfs_employee_earnings_context"]["national_average"] == 22699
        assert result["india_plfs_employee_earnings_context"]["precision"] == "all_regular_wage_salaried_workers"
        assert result["country"]["currency"] == "INR"
        assert client.get("/v1/earnwage/overview?country=US&occupation=nurse").json()[
            "india_plfs_employee_earnings_context"]["status"] == "not_applicable"


def test_published_india_nco_dataset_carries_derivative_provenance():
    with TestClient(app) as client:
        coverage = client.get("/v1/in/plfs/nco/coverage").json()
        assert coverage["status"] == "available"
        assert coverage["observations"] == 597
        assert coverage["nco_occupations"] == 113
        assert coverage["states_or_territories"] == 33
        assert coverage["precision"] == "broad_nco2015_three_digit_group"
        assert coverage["provenance"] == "public_third_party_harmonised_microdata"
        assert coverage["reuse_license"] == "ODbL 1.0"
        detail = client.get("/v1/in/wage-sources").json()
        assert detail["broad_nco2015_group_wages"]["observations"] == 597
        assert detail["exact_occupation_wages"]["status"] == "pending_official_microdata_analysis"
