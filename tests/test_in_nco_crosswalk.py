"""India 2025 NCO crosswalk: broad salary context is not exact profession pay."""
from fastapi.testclient import TestClient

from app.catalog import OCCUPATIONS
from app.in_nco_crosswalk import ALL_JOBS, CONTEXT, UNMAPPED, context, mapping
from app.main import app


def test_all_40_jobs_reviewed_without_fabricated_exact_mappings():
    assert len(OCCUPATIONS) == len(ALL_JOBS) == 40
    assert len(CONTEXT) == 31
    assert len(UNMAPPED) == 9
    assert set(CONTEXT) | set(UNMAPPED) == ALL_JOBS
    assert set(CONTEXT).isdisjoint(UNMAPPED)
    assert mapping("doctor")["nco2015_group"] == "221"
    assert mapping("software_developer")["nco2015_group"] == "251"
    assert mapping("nurse")["nco2015_group"] == "222"
    assert mapping("dentist")["nco2015_group"] == "226"
    assert mapping("truck_driver")["nco2015_group"] == mapping("bus_driver")["nco2015_group"]
    assert mapping("manager")["status"] == "unmapped_ambiguous"
    assert mapping("data_analyst")["status"] == "unmapped_ambiguous"
    assert all(mapping(name)["exact_occupation_salary"] is False for name in ALL_JOBS)


def test_imported_groups_exposed_separately_and_never_annualized():
    with TestClient(app) as client:
        coverage_response = client.get("/v1/in/earnwage-nco/coverage")
        assert coverage_response.status_code == 200
        coverage = coverage_response.json()
        assert coverage["total_occupations"] == 40
        assert coverage["mapped_to_broad_nco_groups"] == 31
        assert coverage["unmapped_ambiguous"] == 9
        assert coverage["exact_occupation_wages_from_this_mapping"] == 0
        assert coverage["underlying_nco_coverage"]["observations"] == 597
        assert coverage["broad_group_observations_available"] >= 10

        url = "/v1/in/earnwage-nco/software_developer"
        result = client.get(url).json()
        assert result["status"] == "available"
        assert result["precision"] == "broad_nco2015_three_digit_group"
        assert result["nco2015_group"] == "251"
        assert result["exact_occupation_salary"] is False
        assert result["observation"]["unit"] == "INR/month"

        overview = client.get("/v1/earnwage/overview",
                              params={"country": "IN", "occupation": "software_developer"}).json()
        assert overview["india_nco2015_professional_group_context"]["status"] == "available"
        assert overview["india_nco2015_professional_group_context"]["exact_occupation_salary"] is False
        assert overview["india_nco2015_professional_group_context"]["nco2015_group"] == "251"
        assert overview["national_occupation_wage"]["status"] == "unavailable"
        assert overview["annual_presentation"]["status"] == "unavailable"
        assert overview["net_purchasing_power"]["status"] == "unavailable"

        ambiguous = client.get("/v1/in/earnwage-nco/manager").json()
        assert ambiguous["status"] == "unmapped_ambiguous"
        assert client.get("/v1/in/earnwage-nco/not-a-job").status_code == 422
        other = client.get("/v1/earnwage/overview",
                           params={"country": "US", "occupation": "software_developer"}).json()
        assert other["india_nco2015_professional_group_context"]["status"] == "not_applicable"
