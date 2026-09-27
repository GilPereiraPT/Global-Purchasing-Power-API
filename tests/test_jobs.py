"""Provider contract tests use synthetic examples, never fictional production jobs."""
from fastapi.testclient import TestClient

from app.jobs import ats_location_matches, location_matches, normalize, search, title_matches
from app.main import app


def fake_row(job_id=12, title="Senior Software Developer", location="Worldwide", salary=""):
    return {
        "id": job_id, "title": title, "company_name": "Example employer",
        "candidate_required_location": location, "salary": salary,
        "publication_date": "2026-09-20T12:00:00", "url": f"https://remotive.com/remote-jobs/software-dev/example-{job_id}",
        "job_type": "full_time",
    }


def test_title_and_location_are_conservative():
    assert title_matches("Senior Software Developer", "software_developer")
    assert not title_matches("Senior Security Guard", "cybersecurity_specialist")
    assert not title_matches("Office Manager", "manager")
    assert location_matches("Worldwide", "PK") == "worldwide"
    assert location_matches("Germany only", "DE") == "country_mentioned"
    assert location_matches("Germany only", "IN") is None


def test_untrusted_application_url_rejected():
    row = fake_row()
    row["url"] = "https://example.com/steal"
    assert normalize(row, "2026-09-26T00:00:00Z") is None


def test_jobs_endpoint(monkeypatch):
    async def fake_feed():
        return {
            "fetched_at": "2026-09-26T00:00:00Z",
            "provider_url": "https://remotive.com/remote-jobs/api",
            "scope": "Synthetic fixture, not production data",
            "jobs": [
                normalize(fake_row(), "2026-09-26T00:00:00Z"),
                normalize(fake_row(13, "Registered Nurse", "Germany", "€50k - €60k"),
                          "2026-09-26T00:00:00Z"),
            ],
        }
    monkeypatch.setattr("app.jobs.feed", fake_feed)
    with TestClient(app) as client:
        res = client.get("/v1/jobs?country=PK&occupation=software_developer")
        assert res.status_code == 200
        assert res.json()["count"] == 1
        assert res.json()["jobs"][0]["salary_structured"] is None
        assert res.json()["jobs"][0]["location_match"] == "worldwide"
        assert client.get("/v1/jobs?country=IN&occupation=nurse").json()["status"] == "no_results"
        assert client.get("/v1/jobs?country=DE&occupation=nurse&salary_published=true").json()["count"] == 1
        assert client.get("/v1/jobs?country=DE&occupation=manager").json()["status"] == "unavailable"
        assert client.get("/v1/jobs?country=XX&occupation=nurse").status_code == 404
        assert client.get("/v1/jobs?country=DE&occupation=not_real").status_code == 422
        assert client.get("/v1/jobs/remotive/12").json()["source"] == "Remotive"

def test_ats_us_locations_do_not_infer_remote_eligibility():
    assert ats_location_matches("Foster City, CA", "US") == "us_state_code"
    assert ats_location_matches("San Diego, CA", "US") == "us_state_code"
    assert ats_location_matches("Los Angeles, CA", "US") == "us_state_code"
    assert ats_location_matches("San Francisco, New York City", "US") == "us_city_mentioned"
    assert ats_location_matches("Remote", "US") is None
    assert ats_location_matches("Remote", "CA") is None
    assert ats_location_matches("Foster City, CA", "CA") is None
    assert ats_location_matches("Germany", "US") is None
    assert title_matches("Full-Stack Engineer (Backend Focused)", "software_developer")
