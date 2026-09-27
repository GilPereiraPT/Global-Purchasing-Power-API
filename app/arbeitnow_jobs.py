"""Arbeitnow public job-board adapter. Preserve location and source attribution."""
from datetime import datetime, timezone
from urllib.parse import urlsplit
import httpx
from app import store
from app.providers import UpstreamUnavailable
from app.jobs import title_matches, COUNTRY_NAMES

API = "https://www.arbeitnow.com/api/job-board-api"
TTL = 6 * 60 * 60
PAGES = 3
CITY_COUNTRY = {
    "berlin":"DE","hamburg":"DE","munich":"DE","münchen":"DE","frankfurt":"DE",
    "cologne":"DE","köln":"DE","düsseldorf":"DE","stuttgart":"DE","leipzig":"DE",
    "london":"GB","manchester":"GB","birmingham":"GB","bristol":"GB",
    "paris":"FR","lyon":"FR","marseille":"FR","toulouse":"FR",
    "amsterdam":"NL","rotterdam":"NL","utrecht":"NL",
    "lisbon":"PT","lisboa":"PT","porto":"PT",
    "madrid":"ES","barcelona":"ES","valencia":"ES",
    "dublin":"IE","cork":"IE",
    "rome":"IT","roma":"IT","milan":"IT","milano":"IT",
    "zurich":"CH","zürich":"CH","geneva":"CH","genève":"CH",
}
def location_country(location):
    text = location.strip().casefold()
    for code, names in COUNTRY_NAMES.items():
        if any(text == name or text.endswith(", "+name) for name in names):
            return code
    return CITY_COUNTRY.get(text.split(",")[0].strip())

def normalize(row, fetched_at):
    url = row.get("url")
    if not isinstance(url,str):
        return None
    parsed=urlsplit(url)
    if parsed.scheme!="https" or parsed.hostname not in ("arbeitnow.com","www.arbeitnow.com"):
        return None
    slug=row.get("slug")
    title=row.get("title")
    if not isinstance(slug,str) or not slug or not isinstance(title,str) or not title.strip():
        return None
    timestamp=row.get("created_at")
    try:
        published=datetime.fromtimestamp(int(timestamp),timezone.utc).isoformat()
    except (ValueError,TypeError,OverflowError,OSError):
        return None
    location=row.get("location") if isinstance(row.get("location"),str) else ""
    remote=row.get("remote") is True
    return {
        "id":"arbeitnow:"+slug,"provider_id":slug,"title":title.strip(),
        "company":row.get("company_name") if isinstance(row.get("company_name"),str) else None,
        "candidate_required_location":location,"location_country":location_country(location),
        "category":None,"salary_text":None,"salary_structured":None,
        "employment_type":", ".join(x for x in row.get("job_types",[]) if isinstance(x,str)) if isinstance(row.get("job_types"),list) else None,
        "published_at":published,"last_checked_at":fetched_at,"source":"Arbeitnow",
        "source_url":url,"apply_url":url,"remote":remote,"status":"listed_by_source",
        "note":"Location is the advertised job location, not proof of remote eligibility or visa rights."
    }

async def feed():
    cached=store.get("jobs:arbeitnow:v1",TTL)
    if cached is not None:
        return cached
    found=[]
    fetched_at=datetime.now(timezone.utc).isoformat()
    try:
        async with httpx.AsyncClient(timeout=30,follow_redirects=True,headers={"User-Agent":"EarnWage/0.5 (+source attribution)"}) as client:
            for page in range(1,PAGES+1):
                response=await client.get(API,params={"page":page})
                response.raise_for_status()
                payload=response.json()
                if not isinstance(payload,dict) or not isinstance(payload.get("data"),list):
                    raise UpstreamUnavailable("Unexpected Arbeitnow response schema")
                found.extend(job for row in payload["data"] if isinstance(row,dict)
                             if (job:=normalize(row,fetched_at)) is not None)
                if not payload.get("links",{}).get("next"):
                    break
    except (httpx.HTTPError,ValueError) as exc:
        raise UpstreamUnavailable("Arbeitnow feed unavailable") from exc
    data={"jobs":found,"fetched_at":fetched_at,"provider":"Arbeitnow"}
    store.set_value("jobs:arbeitnow:v1",data)
    return data

async def search(country,occupation,salary_published=False,limit=20):
    data=await feed()
    matched=[{**job,"destination_country":country,"location_match":"advertised_location"}
             for job in data["jobs"] if job["location_country"]==country
             and title_matches(job["title"],occupation)
             and (not salary_published or job["salary_text"])]
    matched.sort(key=lambda x:x["published_at"],reverse=True)
    return {"status":"available" if matched else "no_results","provider":"Arbeitnow",
            "country":country,"occupation":occupation,"count":len(matched),
            "returned":min(len(matched),limit),"jobs":matched[:limit],
            "fetched_at":data["fetched_at"],"source_url":"https://www.arbeitnow.com/",
            "scope":"Only jobs with an identifiable advertised country from the first three feed pages.",
            "notice":"Remote flag does not establish eligibility from another country. Source: Arbeitnow.com."}
