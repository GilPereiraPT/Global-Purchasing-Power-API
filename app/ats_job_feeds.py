"""Public employer job boards: Greenhouse, Lever and Ashby.

Each API is company-scoped, NOT a searchable global jobs database. Curated
board identifiers are explicit and expandable after verification. No credentials.
"""
import asyncio
from datetime import datetime, timezone
from urllib.parse import urlsplit
import httpx
from app import store
from app.jobs import title_matches, ats_location_matches
from app.providers import UpstreamUnavailable

BOARDS = {
    "greenhouse": ("stripe", "cloudflare", "fluxon", "arcesiumllc", "icapitalnetwork", "dashlane"),
    "lever": ("lever", "teamsnap", "zoox", "finch", "truv", "sambatv", "integrate", "jobgether", "xsolla", "PocketHealth", "cscgeneration-2", "magnetforensics", "pointclickcare"),
    "ashby": ("Ashby", "zego", "bjakcareer"),
}
LABELS = {"greenhouse": "Greenhouse", "lever": "Lever", "ashby": "Ashby"}
HOSTS = {"greenhouse": {"boards.greenhouse.io", "job-boards.greenhouse.io", "boards-api.greenhouse.io"},
         "lever": {"jobs.lever.co", "jobs.eu.lever.co"},
         "ashby": {"jobs.ashbyhq.com"}}
COMPANIES = {"icapitalnetwork": "iCapital", "arcesiumllc": "Arcesium", "sambatv": "Samba TV", "jobgether": "Jobgether", "bjakcareer": "Bjak", "pointclickcare": "PointClickCare", "magnetforensics": "Magnet Forensics", "PocketHealth": "PocketHealth", "cscgeneration-2": "CSC Generation", "teamsnap": "TeamSnap", "xsolla": "Xsolla", "zego": "Zego", "dashlane": "Dashlane", "fluxon": "Fluxon", "stripe": "Stripe", "cloudflare": "Cloudflare", "zoox": "Zoox", "finch": "Finch", "truv": "Truv", "integrate": "Integrate", "lever": "Lever", "Ashby": "Ashby"}
TTL = 6 * 3600

def _url(value, provider):
    if not isinstance(value, str):
        return None
    parsed = urlsplit(value)
    allowed = parsed.hostname in HOSTS[provider]
    # Stripe publishes its Greenhouse postings on its own verified careers domain.
    if provider == "greenhouse" and parsed.hostname == "stripe.com":
        allowed = parsed.path.startswith(("/jobs/", "/careers/"))
    return value if parsed.scheme == "https" and allowed else None

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
        company = COMPANIES.get(board, board)
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
            "salary_display": "Não divulgado", "salary_disclosed": False,
            "employment_type": employment, "published_at": published,
            "publication_date_status": ("last_updated" if provider == "greenhouse" else "reported") if published else "unknown",
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
    key = "jobs:ats:" + provider + ":v6"
    cached = store.get(key, TTL)
    if cached is not None:
        return cached
    fetched = datetime.now(timezone.utc).isoformat()
    jobs = []
    succeeded, failed, board_stats = [], [], {}
    semaphore = asyncio.Semaphore(5)
    async with httpx.AsyncClient(timeout=25, follow_redirects=True,
                                 headers={"User-Agent": "EarnWage/0.5 (+source attribution)"}) as client:
        async def fetch_board(board):
            async with semaphore:
                try:
                    response = await client.get(_endpoint(provider, board),
                        params={"mode": "json"} if provider == "lever" else
                               {"includeCompensation": "true"} if provider == "ashby" else None)
                    response.raise_for_status()
                    payload = response.json()
                    rows = payload if provider == "lever" else payload.get("jobs") if isinstance(payload, dict) else None
                    if not isinstance(rows, list):
                        return board, "invalid_response", 0, []
                    normalized = [item for row in rows if isinstance(row, dict)
                                  if (item := _record(provider, board, row, fetched)) is not None]
                    return board, "ok", len(rows), normalized
                except (httpx.HTTPError, ValueError):
                    return board, "failed", 0, []
        for board, status, row_count, normalized in await asyncio.gather(
                *(fetch_board(board) for board in BOARDS[provider])):
            if status == "ok":
                succeeded.append(board)
                jobs.extend(normalized)
            else:
                failed.append(board)
            board_stats[board] = {"status": status, "jobs_before_filter": row_count,
                                  "jobs_normalized": len(normalized)}
    if not succeeded:
        raise UpstreamUnavailable(LABELS[provider] + " boards unavailable")
    result = {"jobs": jobs, "fetched_at": fetched,
              "boards_checked": list(BOARDS[provider]),
              "boards_succeeded": succeeded, "boards_failed": failed,
              "board_stats": board_stats}
    store.set_value(key, result)
    return result

async def search(provider, country, occupation, salary_published=False, limit=20, debug=False):
    data = await feed(provider)
    found = []
    remote_unverified = []
    stats = {board: {**values, "jobs_matching_occupation": 0,
                     "jobs_matching_country": 0, "jobs_matching_both": 0,
                     "jobs_after_filter": 0, "remote_unverified": 0, "rejected_samples": []}
             for board, values in data["board_stats"].items()}
    for item in data["jobs"]:
        board = item["id"].split(":", 2)[1]
        entry = stats[board]
        matches_title = title_matches(item["title"], occupation)
        scope = ats_location_matches(item["candidate_required_location"], country)
        matches_country = bool(scope)
        if matches_title:
            entry["jobs_matching_occupation"] += 1
        if matches_country:
            entry["jobs_matching_country"] += 1
        if matches_title and matches_country:
            entry["jobs_matching_both"] += 1
        if matches_title and not matches_country and item["remote"] and (
                item["candidate_required_location"].strip().lower() == "remote"):
            entry["remote_unverified"] += 1
            remote_unverified.append({**item, "destination_country": country,
                "location_match": "unverified_remote",
                "eligibility_note": "Remote job: eligible countries not confirmed by the source location."})
        if not matches_title or not matches_country:
            if len(entry["rejected_samples"]) < 8 and (
                    matches_title or len(entry["rejected_samples"]) < 3):
                entry["rejected_samples"].append({
                    "title": item["title"],
                    "location": item["candidate_required_location"],
                    "matches_occupation": matches_title,
                    "matches_country": matches_country})
            continue
        if salary_published and not item["salary_structured"]:
            continue
        found.append({**item, "destination_country": country, "location_match": scope})
        entry["jobs_after_filter"] += 1
    found.sort(key=lambda item: item["published_at"] or "", reverse=True)
    remote_unverified.sort(key=lambda item: item["published_at"] or "", reverse=True)
    result = {"status": "available" if found else "no_results", "provider": LABELS[provider],
            "country": country, "occupation": occupation, "count": len(found),
            "returned": min(len(found), limit), "jobs": found[:limit],
            "remote_unverified_count": len(remote_unverified),
            "remote_unverified": remote_unverified[:limit],
            "fetched_at": data["fetched_at"],
            "boards_checked": data["boards_checked"],
            "boards_succeeded": data["boards_succeeded"],
            "boards_failed": data["boards_failed"],
            "jobs_before_filter": sum(v["jobs_before_filter"] for v in stats.values()),
            "jobs_normalized": len(data["jobs"]),
            "jobs_matching_occupation": sum(v["jobs_matching_occupation"] for v in stats.values()),
            "jobs_matching_country": sum(v["jobs_matching_country"] for v in stats.values()),
            "jobs_matching_both": sum(v["jobs_matching_both"] for v in stats.values()),
            "jobs_after_filter": len(found),
            "remote_unverified_total": len(remote_unverified),
            "board_stats": stats,
            "source_url": "https://boards-api.greenhouse.io/" if provider == "greenhouse" else
                          "https://api.lever.co/" if provider == "lever" else
                          "https://api.ashbyhq.com/",
            "scope": "Curated employer boards only, not a national vacancy census.",
            "notice": "Check the employer listing for eligibility and availability."}
    if not debug:
        for field in ("boards_checked", "boards_succeeded", "boards_failed",
                      "jobs_before_filter", "jobs_normalized", "jobs_matching_occupation",
                      "jobs_matching_country", "jobs_matching_both", "jobs_after_filter",
                      "board_stats"):
            result.pop(field, None)
    return result
