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
        assert data["observed_pairs"] >= 135
        country = {x["code"]: x for x in data["by_country"]}
        assert country["CA"]["observed_occupations"] == 28
        assert country["US"]["observed_occupations"] == 10
        assert country["DE"]["observed_occupations"] == 27
        assert country["FR"]["observed_occupations"] == 23
        assert country["NL"]["observed_occupations"] == 21
        assert country["PT"]["observed_occupations"] == 0
        assert client.get("/v1/earnwage/overview?country=PT&occupation=nurse&region=TX").status_code == 422
        assert client.get("/v1/earnwage/overview?country=US&occupation=nurse&region=QC").status_code == 422
        assert client.get("/v1/earnwage/overview?country=XX&occupation=nurse").status_code == 404
        assert client.get("/v1/earnwage/compare?country_a=US&country_b=CA&occupation=invalid").status_code == 422
        assert client.get("/v1/earnwage/overview?country=US&occupation=nurse&annual_gross=0").status_code == 422


def test_group_context_does_not_replace_exact_profession_wage():
    with TestClient(app) as client:
        response = client.get("/v1/earnwage/overview?country=PT&occupation=nurse")
        assert response.status_code == 200
        data = response.json()
        assert data["national_occupation_wage"]["status"] == "unavailable"
        assert data["annual_presentation"]["status"] == "unavailable"
        assert data["annual_presentation"]["value"] is None
        assert data["salary_display"]["status"] == "unavailable"
        assert data["salary_display"]["major_group_context_available"] is True
        context = data["national_major_group_context"]
        assert context["precision"] == "isco08_major_group"
        assert context["isco08_major_group"] == "2"
        assert context["country"] == "PT"
        assert data["net_purchasing_power"]["value"] is None
        comparison = client.get("/v1/earnwage/compare?country_a=PT&country_b=US&occupation=nurse")
        assert comparison.status_code == 200
        assert comparison.json()["country_a"]["national_major_group_context"]["precision"] == "isco08_major_group"
        assert comparison.json()["country_a"]["national_occupation_wage"]["status"] == "unavailable"


def test_all_40_jobs_have_curated_group_and_fallback_is_explicit():
    with TestClient(app) as client:
        jobs = client.get("/v1/occupations?lang=pt").json()["occupations"]
        assert len(jobs) == 40
        assert all(job["isco08_major_group"] in "123456789" for job in jobs)
        for job in jobs:
            if job["isco08"] is not None:
                assert job["isco08_major_group"] == job["isco08"][0]
        pt = client.get("/v1/earnwage/overview?country=PT&occupation=nurse").json()
        assert pt["salary_display"]["source"] == "isco08_major_group_context"
        assert pt["national_occupation_wage"]["status"] == "unavailable"
        ca = client.get("/v1/earnwage/overview?country=CA&occupation=nurse").json()
        assert ca["salary_display"]["source"] == "exact_occupation"


def test_portugal_health_professions_never_inherit_same_group_salary():
    """An ISCO-08 group is useful context but not a doctor/nurse/psychologist wage."""
    with TestClient(app) as client:
        results = {
            job: client.get("/v1/earnwage/overview",
                            params={"country": "PT", "occupation": job}).json()
            for job in ("doctor", "nurse", "psychologist")
        }
    assert {x["occupation"]["isco08"] for x in results.values()}
    for job, result in results.items():
        assert result["national_occupation_wage"]["status"] == "unavailable", job
        assert result["annual_presentation"]["status"] == "unavailable", job
        assert result["annual_presentation"]["value"] is None, job
        assert result["salary_display"]["status"] == "unavailable", job
        assert result["salary_display"]["source"] == "isco08_major_group_context", job
        assert result["national_major_group_context"]["isco08_major_group"] == "2", job
        assert result["national_major_group_context"]["precision"] == "isco08_major_group", job
    # The aggregate may be equal, but it must NEVER become the occupation amount.
    group = [r["national_major_group_context"] for r in results.values()]
    assert all(r["values"] == group[0]["values"] for r in group)


def test_occupation_specific_annual_salary_still_visible_when_verified():
    with TestClient(app) as client:
        result = client.get("/v1/earnwage/overview",
                            params={"country": "US", "occupation": "nurse"}).json()
    assert result["national_occupation_wage"]["status"] == "available"
    assert result["annual_presentation"]["status"] == "available"
    assert result["salary_display"]["status"] == "available"
    assert result["salary_display"]["source"] == "exact_occupation"
