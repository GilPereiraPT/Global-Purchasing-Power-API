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
        state_coverage = coverage["regional_nco_group_coverage"]
        assert state_coverage["regions_listed"] == 33
        region_by_code = {row["code"]: row for row in state_coverage["by_state"]}
        assert region_by_code["27"]["name"] == "Maharashtra"
        assert region_by_code["27"]["mapped_professions_with_group_context"] > 0
        assert region_by_code["27"]["exact_occupation_wages"] == 0
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


def test_india_state_dropdown_and_non_fallback_regional_group_wages():
    with TestClient(app) as client:
        options = client.get("/v1/regions/IN").json()
        assert options["visible"] is True
        assert options["region_type"] == "state_or_union_territory"
        labels = {r["code"]: r["name"] for r in options["options"]}
        assert len(labels) == 33
        assert labels["27"] == "Maharashtra"
        assert labels["7"] == "Delhi"
        assert "group" in options["note"]["en"].lower()

        regional = client.get("/v1/earnwage/overview", params={
            "country": "IN", "occupation": "software_developer", "region": "27"
        })
        assert regional.status_code == 200
        body = regional.json()
        national = body["india_nco2015_professional_group_context"]
        regional_group = body["india_nco2015_regional_group_context"]
        assert national["status"] == regional_group["status"] == "available"
        assert national["observation"]["geography"] == "national"
        assert regional_group["observation"]["geography"] == "state"
        assert regional_group["observation"]["state_name"] == "Maharashtra"
        assert regional_group["observation"]["value"] != national["observation"]["value"]
        assert regional_group["exact_occupation_salary"] is False
        assert body["national_occupation_wage"]["status"] == "unavailable"
        assert body["annual_presentation"]["status"] == "unavailable"

        missing = client.get("/v1/earnwage/overview", params={
            "country": "IN", "occupation": "software_developer", "region": "4"
        }).json()
        assert missing["india_nco2015_professional_group_context"]["status"] == "available"
        assert missing["india_nco2015_regional_group_context"]["status"] == "group_observation_unavailable"
        assert client.get("/v1/earnwage/overview?country=IN&occupation=software_developer&region=INVALID").status_code == 422
        compare = client.get("/v1/earnwage/compare", params={
            "country_a": "IN", "country_b": "US", "occupation": "software_developer",
            "region_a": "27", "region_b": "CA"
        })
        assert compare.status_code == 200
        assert compare.json()["country_a"]["india_nco2015_regional_group_context"]["status"] == "available"
