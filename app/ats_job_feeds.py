"""Public employer job boards: Greenhouse, Lever and Ashby.

Each API is company-scoped, NOT a searchable global jobs database. Curated
board identifiers are explicit and expandable after verification. No credentials.
"""
from datetime import datetime, timezone
from urllib.parse import urlsplit
import httpx
from app import store
from app.jobs import title_matches, location_matches
from app.providers import UpstreamUnavailable

BOARDS = {
    "greenhouse": ("stripe",),
    "lever": ("lever",),
    "ashby": ("Ashby",),
}
LABELS = {"greenhouse": "Greenhouse", "lever": "Lever", "ashby": "Ashby"}
HOSTS = {"greenhouse": {"boards.greenhouse.io", "job-boards.greenhouse.io", "boards-api.greenhouse.io"},
         "lever": {"jobs.lever.co", "jobs.eu.lever.co"},
         "ashby": {"jobs.ashbyhq.com"}}
TTL = 6 * 3600

def _url(value, provider):
    if not isinstance(value, str):
        return None
    parsed = urlsplit(value)
    return value if parsed.scheme == "https" and parsed.hostname in HOSTS[provider] else None

def _iso(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
    except ValueError:
        return None

def _record(provider, board, row, fetched):
    if provider == "greenhouse":
        title = row.get("title")
        place = row.get("location")
        place = place.get("name", "") if isinstance(place, dict) else ""
        url = _url(row.get("absolute_url"), provider)
        published = _iso(row.get("updated_at"))
        identity = row.get("id")
        remote = "remote" in str(place).lower()
        company = board
        employment = None
        pay = None
    elif provider == "lever":
        title = row.get("text")
        cats = row.get("categories") or {}
        if not isinstance(cats, dict):
            cats = {}
        place = cats.get("location") or ""
        url = _url(row.get("hostedUrl"), provider)
        identity = row.get("id")
        published = _iso(row.get("createdAt")) if isinstance(row.get("createdAt"), str) else None
        if not published and isinstance(row.get("createdAt"), (int, float)):
            try:
                published = datetime.fromtimestamp(row["createdAt"]/1000, timezone.utc).isoformat()
            except (OverflowError, ValueError, OSError):
                pass
        remote = str(row.get("workplaceType", "")).lower() == "remote"
        company = board
        employment = cats.get("commitment")
        pay = None
    else:
        title = row.get("title")
        place = row.get("location") or ""
        address = row.get("address") or {}
        if isinstance(address, dict) and address.get("addressCountry"):
            place = str(place) + ", " + str(address["addressCountry"])
        url = _url(row.get("jobUrl"), provider)
        identity = row.get("id") or row.get("jobUrl")
        published = _iso(row.get("publishedAt"))
        remote = bool(row.get("isRemote"))
        company = board
        employment = row.get("employmentType")
        pay = None  # Do not infer currency, period or pay from free text.
    if not identity or not isinstance(title, str) or not title.strip() or not isinstance(place, str) or not place.strip() or not url:
        return None
    return {"id": provider + ":" + board + ":" + str(identity),
            "provider_id": identity, "title": title.strip(), "company": company,
            "candidate_required_location": place, "category": None,
            "salary_text": None, "salary_structured": pay,
            "employment_type": employment, "published_at": published or fetched,
            "last_checked_at": fetched, "source": LABELS[provider],
            "source_url": url, "apply_url": url, "remote": remote,
            "status": "listed_by_source",
            "note": "Company-scoped public job board; confirm eligibility, location and availability at source."}

def _endpoint(provider, board):
    if provider == "greenhouse":
        return "https://boards-api.greenhouse.io/v1/boards/" + board + "/jobs"
    if provider == "lever":
        return "https://api.lever.co/v0/postings/" + board
    return "https://api.ashbyhq.com/posting-api/job-board/" + board

async def feed(provider):
    if provider not in BOARDS:
        raise ValueError("Unknown provider")
    key = "jobs:ats:" + provider + ":v1"
    cached = store.get(key, TTL)
    if cached is not None:
        return cached
    fetched = datetime.now(timezone.utc).isoformat()
    jobs = []
    success = 0
    async with httpx.AsyncClient(timeout=25, follow_redirects=True,
                                 headers={"User-Agent": "EarnWage/0.5 (+source attribution)"}) as client:
        for board in BOARDS[provider]:
            try:
                response = await client.get(_endpoint(provider, board),
                    params={"mode": "json"} if provider == "lever" else
                           {"includeCompensation": "true"} if provider == "ashby" else None)
                response.raise_for_status()
                payload = response.json()
                rows = payload if provider == "lever" else payload.get("jobs") if isinstance(payload, dict) else None
                if not isinstance(rows, list):
                    continue
                success += 1
                jobs.extend(item for row in rows if isinstance(row, dict)
                            if (item := _record(provider, board, row, fetched)) is not None)
            except (httpx.HTTPError, ValueError):
                continue
    if not success:
        raise UpstreamUnavailable(LABELS[provider] + " boards unavailable")
    result = {"jobs": jobs, "fetched_at": fetched}
    store.set_value(key, result)
    return result

async def search(provider, country, occupation, salary_published=False, limit=20):
    data = await feed(provider)
    found = []
    for item in data["jobs"]:
        if not title_matches(item["title"], occupation):
            continue
        scope = location_matches(item["candidate_required_location"], country)
        if not scope or (salary_published and not item["salary_structured"]):
            continue
        found.append({**item, "destination_country": country, "location_match": scope})
    found.sort(key=lambda item: item["published_at"], reverse=True)
    return {"status": "available" if found else "no_results", "provider": LABELS[provider],
            "country": country, "occupation": occupation, "count": len(found),
            "returned": min(len(found), limit), "jobs": found[:limit],
            "fetched_at": data["fetched_at"], "source_url": _endpoint(provider, BOARDS[provider][0]),
            "scope": "Curated employer boards only, not a national vacancy census.",
            "notice": "Check the employer listing for eligibility and availability."}
