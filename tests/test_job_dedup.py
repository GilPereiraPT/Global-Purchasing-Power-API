from app.job_dedup import merge_jobs


def listing(source, title, place, salary=None, company="Ashby"):
    return {"id": source + ":" + title, "source": source,
            "source_url": "https://example.com/" + source + "/" + title.replace(" ", "-"),
            "apply_url": "https://example.com/" + source + "/" + title.replace(" ", "-"),
            "provider_id": title, "company": company, "title": title,
            "candidate_required_location": place, "destination_country": "GB",
            "salary_structured": salary, "salary_text": None,
            "published_at": "2026-09-27T00:00:00+00:00"}


def test_ashby_jobicy_merge_preserves_salary_and_sources():
    title = "Staff Software Engineer, Product Engineering - UK"
    jobicy = listing("Jobicy", title, "UK",
                     {"min": 151000, "max": 184000, "currency": "GBP", "period": "yearly"})
    ashby = listing("Ashby", title, "United Kingdom")
    found = merge_jobs([ashby, jobicy])
    assert len(found) == 1
    assert found[0]["salary_structured"]["currency"] == "GBP"
    assert {x["source"] for x in found[0]["sources"]} == {"Jobicy", "Ashby"}


def test_seniority_and_cities_remain_separate():
    rows = [listing("Jobicy", "Senior Software Engineer", "UK"),
            listing("Ashby", "Staff Software Engineer", "United Kingdom"),
            listing("Lever", "Senior Software Engineer", "London")]
    assert len(merge_jobs(rows)) == 3


def test_no_company_no_cross_provider_merge():
    rows = [listing("Jobicy", "Software Engineer", "UK", company=""),
            listing("Ashby", "Software Engineer", "United Kingdom", company="")]
    assert len(merge_jobs(rows)) == 2
