"""Attributable job listings: Remotive public remote-jobs API, not a countrywide vacancy census.

This provider is limited to adverts shared by Remotive. Worldwide remote eligibility
does not establish an employer's country, tax residence or capital-city living costs.
"""
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

from app import store
from app.catalog import COUNTRY_MAP, OCCUPATIONS
from app.providers import UpstreamUnavailable

import httpx

API = "https://remotive.com/api/remote-jobs"
SOURCE = "Remotive"
TTL_SECONDS = 6 * 60 * 60  # Provider recommends at most four fetches daily.
CACHE_KEY = "jobs:remotive:v1"
MAX_LISTINGS = 1000
# Exact word/phrase matching on original job title. Unsupported jobs remain unavailable.
TITLES = {
    "accountant": ("accountant", "accounting specialist"),
    "auditor": ("auditor", "audit specialist"),
    "financial_analyst": ("financial analyst",),
    "doctor": ("physician", "medical doctor"),
    "nurse": ("registered nurse", "staff nurse"),
    "pharmacist": ("pharmacist",),
    "psychologist": ("psychologist",),
    "physiotherapist": ("physiotherapist", "physical therapist"),
    "teacher": ("teacher",),
    "preschool_teacher": ("preschool teacher", "kindergarten teacher"),
    "software_developer": ("software engineer", "software developer", "web developer", "backend developer", "frontend developer"),
    "it_technician": ("it support technician", "it technician", "help desk technician"),
    "civil_engineer": ("civil engineer",),
    "mechanical_engineer": ("mechanical engineer",),
    "architect": ("architect",),
    "administrative_assistant": ("administrative assistant",),
    "manager": (),  # Too broad for title matching.
    "receptionist": ("receptionist",),
    "sales_assistant": ("sales assistant", "retail associate"),
    "supermarket_worker": ("supermarket worker", "grocery clerk"),
    "truck_driver": ("truck driver",),
    "bus_driver": ("bus driver",),
    "electrician": ("electrician",),
    "plumber": ("plumber",),
    "construction_worker": ("construction worker",),
    "cook": ("cook", "chef"),
    "waiter": ("waiter", "waitress"),
    "cleaner": ("cleaner", "cleaning operative"),
    "security_guard": ("security guard",),
    "lawyer": ("lawyer", "legal counsel"),
    "dentist": ("dentist",),
    "healthcare_assistant": ("healthcare assistant",),
    "data_analyst": ("data analyst",),
    "cybersecurity_specialist": ("cybersecurity specialist", "security engineer"),
    "secondary_teacher": ("secondary school teacher", "high school teacher"),
    "warehouse_operator": ("warehouse operator", "warehouse associate"),
    "industrial_operator": ("machine operator",),
    "welder": ("welder",),
    "automotive_mechanic": ("automotive mechanic", "car mechanic"),
    "agricultural_worker": ("farm worker", "agricultural worker"),
}
assert set(TITLES) == {x["id"] for x in OCCUPATIONS}

COUNTRY_NAMES = {
    "PT": ("portugal",),
    "ES": ("spain",),
    "DE": ("germany", "deutschland"),
    "FR": ("france",),
    "GB": ("united kingdom", "uk", "great britain"),
    "IN": ("india",),
    "BR": ("brazil", "brasil"),
    "PK": ("pakistan",),
    "NL": ("netherlands", "holland"),
    "CH": ("switzerland",),
    "IT": ("italy",),
    "IE": ("ireland",),
    "US": ("united states", "usa", "u.s.", "united states of america"),
    "CA": ("canada",),
}
WORLDWIDE = re.compile(r"\b(worldwide|anywhere|global|work from anywhere|any location)\b", re.I)


def title_matches(title: str, occupation: str) -> bool:
    """Match curated seven-language occupation titles without broad catch-all stems."""
    if occupation not in TITLES or not TITLES[occupation]:
        return False
    from app.job_dictionary import matches
    return matches(title, occupation)


def location_matches(location: str, country: str) -> str | None:
    """Remote eligibility is not place of employment."""
    if WORLDWIDE.search(location):
        return "worldwide"
    names = COUNTRY_NAMES.get(country, ())
    if any(re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", location, re.I)
           for name in names):
        return "country_mentioned"
    return None



# ATS employer boards commonly supply US cities/states without a country name.
# Do not interpret a bare "Remote" as permission to work from the US.
US_STATE_CODES = frozenset((
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI "
    "MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT "
    "VT VA WA WV WI WY DC").split())
US_CITY_NAMES = ("san francisco", "new york city", "los angeles",
                 "san diego", "foster city")

EU_COUNTRIES = frozenset(("PT ES DE FR NL IT IE").split())
EU_REGION = re.compile(r"(?<!\\w)(?:european union|eu countries|eu member states|eu only|eu remote|remote[ -]+eu)(?!\\w)", re.I)
# UK and Switzerland are not EU member states. EMEA/Europe is not proof of EU eligibility.

def ats_location_matches(location: str, country: str) -> str | None:
    """Country match for employer-board location strings; no remote inference."""
    if not isinstance(location, str):
        return None
    direct = location_matches(location, country)
    if direct:
        return direct
    if country in EU_COUNTRIES and EU_REGION.search(location):
        return "eu_region_mentioned"
    if country != "US":
        return None
    # An uppercase state code after a comma, e.g. "Foster City, CA".
    # Case-sensitive to avoid confusing "in" with Indiana or "ca" with Canada.
    state_codes = re.findall(r",\s*([A-Z]{2})(?=\s*(?:[,;/()]|$))", location)
    if any(code in US_STATE_CODES for code in state_codes):
        return "us_state_code"
    if any(re.search(r"(?<!\w)" + re.escape(city) + r"(?!\w)", location, re.I)
           for city in US_CITY_NAMES):
        return "us_city_mentioned"
    return None

def normalize(row: dict, fetched_at: str) -> dict | None:
    url = row.get("url")
    if not isinstance(url, str):
        return None
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ("remotive.com", "www.remotive.com"):
        return None
    raw_id = row.get("id")
    if not isinstance(raw_id, int):
        return None
    title = row.get("title", "")
    if not isinstance(title, str) or not title.strip():
        return None
    published = row.get("publication_date")
    if not isinstance(published, str) or not published:
        return None
    return {
        "id": f"remotive:{raw_id}", "provider_id": raw_id,
        "title": title.strip(),
        "company": row.get("company_name") if isinstance(row.get("company_name"), str) else None,
        "candidate_required_location": row.get("candidate_required_location") if isinstance(row.get("candidate_required_location"), str) else "",
        "category": row.get("category") if isinstance(row.get("category"), str) else None,
        "salary_text": row.get("salary") if isinstance(row.get("salary"), str) and row.get("salary").strip() else None,
        "salary_structured": None,
        "employment_type": row.get("job_type") if isinstance(row.get("job_type"), str) else None,
        "published_at": published,
        "last_checked_at": fetched_at,
        "source": SOURCE,
        "source_url": url,
        "apply_url": url,
        "remote": True,
        "status": "listed_by_source",
        "note": "Remote eligibility is not an employer location or a guaranteed right to work."
    }


async def feed() -> dict:
    cached = store.get(CACHE_KEY, TTL_SECONDS)
    if cached is not None:
        return cached
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                     headers={"User-Agent": "GlobalPurchasingPowerAPI/0.3 (+source attribution)"}) as client:
            response = await client.get(API, params={"limit": MAX_LISTINGS})
            response.raise_for_status()
            raw = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise UpstreamUnavailable("Remotive job feed unavailable; no verified live vacancies") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("jobs"), list):
        raise UpstreamUnavailable("Unexpected Remotive response schema")
    fetched_at = datetime.now(timezone.utc).isoformat()
    listings = [x for row in raw["jobs"] if isinstance(row, dict)
                if (x := normalize(row, fetched_at)) is not None]
    data = {
        "provider": SOURCE,
        "provider_url": "https://remotive.com/remote-jobs/api",
        "fetched_at": fetched_at,
        "limit": MAX_LISTINGS,
        "total_feed_listings": len(listings),
        "scope": "Remotive remote listings only; not a count of all national jobs.",
        "jobs": listings
    }
    store.set_value(CACHE_KEY, data)
    return data


async def search(country: str, occupation: str, salary_published: bool = False,
                 limit: int = 20) -> dict:
    if occupation not in TITLES or not TITLES[occupation]:
        return {
            "status": "unavailable", "provider": SOURCE, "country": country,
            "occupation": occupation, "jobs": [], "count": 0,
            "reason": "Title mapping not specific enough to search this occupation safely"
        }
    data = await feed()
    found = []
    for job in data["jobs"]:
        if not title_matches(job["title"], occupation):
            continue
        scope = location_matches(job["candidate_required_location"], country)
        if not scope:
            continue
        if salary_published and not job["salary_text"]:
            continue
        found.append({**job, "destination_country": country, "location_match": scope})
    found.sort(key=lambda x: x["published_at"], reverse=True)
    return {
        "status": "available" if found else "no_results",
        "provider": SOURCE, "country": country, "occupation": occupation,
        "count": len(found), "returned": min(len(found), limit),
        "jobs": found[:limit], "fetched_at": data["fetched_at"],
        "source_url": data["provider_url"],
        "scope": data["scope"],
        "notice": "These are remote vacancies listed by Remotive at fetch time; availability can change. Visit source to apply.",
    }


async def detail(job_id: int) -> dict | None:
    data = await feed()
    return next((x for x in data["jobs"] if x["provider_id"] == job_id), None)
