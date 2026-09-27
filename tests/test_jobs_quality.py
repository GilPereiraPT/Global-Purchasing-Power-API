"""Regression tests for EarnWage international job quality; synthetic rows only."""
from app.ats_job_feeds import _record, _url
from app.jobs import ats_location_matches
from app.job_dedup import merge_jobs
from app.native_wsgi import recent_jobs


def test_stripe_verified_custom_url_and_untrusted_domains():
    assert _url("https://stripe.com/jobs/search?gh_jid=123", "greenhouse")
    assert _url("https://stripe.com/careers/apply/software/123", "greenhouse")
    assert _url("https://stripe.com.evil.example/jobs/search", "greenhouse") is None
    assert _url("https://stripe.com/account", "greenhouse") is None
    row = {"id": 123, "title": "Software Engineer",
           "location": {"name": "Lisbon, Portugal"},
           "absolute_url": "https://stripe.com/jobs/search?gh_jid=123"}
    job = _record("greenhouse", "stripe", row, "2026-09-27T00:00:00Z")
    assert job["company"] == "Stripe"
    assert job["salary_display"] == "Não divulgado"


def test_eu_region_requires_explicit_union():
    for code in ("PT", "ES", "DE", "FR", "NL", "IT", "IE"):
        assert ats_location_matches("Remote - European Union", code) == "eu_region_mentioned"
    for code in ("GB", "CH", "US", "CA", "IN", "BR", "PK"):
        assert ats_location_matches("Remote - European Union", code) is None
    assert ats_location_matches("Remote - EMEA", "PT") is None
    assert ats_location_matches("Remote", "PT") is None


def test_same_board_distinct_ids_preserved():
    base = {"company": "Bjak", "title": "Staff Software Engineer",
            "candidate_required_location": "Portugal", "destination_country": "PT",
            "source": "Ashby", "salary_text": None, "salary_structured": None,
            "published_at": "2026-09-25T00:00:00Z"}
    a = {**base, "id": "a", "source_url": "https://jobs.ashbyhq.com/bjakcareer/a"}
    b = {**base, "id": "b", "source_url": "https://jobs.ashbyhq.com/bjakcareer/b"}
    assert len(merge_jobs([a, b])) == 2
    assert len(merge_jobs([a, dict(a)])) == 1


def test_salary_display_no_inference():
    result = recent_jobs({"jobs": [
        {"id": "1", "published_at": None, "salary_text": None, "salary_structured": None},
        {"id": "2", "published_at": None, "salary_text": "€50,000–€60,000", "salary_structured": None},
    ]}, 180, 100)
    assert result["jobs"][0]["salary_display"] == "Não divulgado"
    assert result["jobs"][0]["salary_disclosed"] is False
    assert result["jobs"][1]["salary_display"] == "€50,000–€60,000"
    assert result["jobs"][1]["salary_disclosed"] is True
