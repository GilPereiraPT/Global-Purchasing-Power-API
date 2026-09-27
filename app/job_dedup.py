"""Conservative cross-provider job deduplication with provenance preservation."""
import re
import unicodedata
from urllib.parse import urlsplit

COUNTRY_EQUIVALENTS = {
    "united kingdom": "gb", "uk": "gb", "great britain": "gb",
    "united states": "us", "usa": "us", "united states of america": "us",
    "germany": "de", "deutschland": "de", "portugal": "pt",
    "france": "fr", "spain": "es", "canada": "ca",
    "netherlands": "nl", "ireland": "ie", "italy": "it",
    "switzerland": "ch", "brazil": "br", "brasil": "br",
    "india": "in", "pakistan": "pk",
}

def _norm(value):
    text = unicodedata.normalize("NFKD", str(value or "")).casefold()
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^\w]+", " ", text).strip()

def _location(job):
    raw = _norm(job.get("candidate_required_location"))
    if raw in COUNTRY_EQUIVALENTS:
        return COUNTRY_EQUIVALENTS[raw]
    if raw in ("worldwide", "anywhere", "global", "work from anywhere"):
        return "worldwide"
    return raw

def _source(job):
    return {"source": job.get("source"), "source_url": job.get("source_url"),
            "apply_url": job.get("apply_url"), "provider_id": job.get("provider_id")}

def merge_jobs(listings):
    """Merge exact company/title/location matches, not fuzzy or seniority matches.

    A shared source URL is always the same advert. Cross-provider merging
    additionally requires a nonempty company, title and equivalent location.
    Keep all attributed URLs and structured salary if available.
    """
    results = []
    by_url = {}
    by_identity = {}
    for original in listings:
        job = dict(original)
        url = job.get("source_url")
        if not isinstance(url, str) or not url:
            continue
        parsed = urlsplit(url)
        url_key = (parsed.netloc.casefold(), parsed.path.rstrip("/"))
        company, title, location = (_norm(job.get("company")),
                                    _norm(job.get("title")), _location(job))
        identity = (company, title, location, job.get("destination_country"))
        # Worldwide and country-specific offers must not be merged.
        valid_identity = bool(company and title and location)
        target = by_url.get(url_key)
        if target is None and valid_identity:
            target = by_identity.get(identity)
        if target is None:
            job["sources"] = [_source(job)]
            results.append(job)
            target = job
        else:
            entry = _source(job)
            if not any(x.get("source_url") == url for x in target["sources"]):
                target["sources"].append(entry)
            if not target.get("salary_structured") and job.get("salary_structured"):
                target["salary_structured"] = job["salary_structured"]
                target["salary_text"] = job.get("salary_text")
            elif not target.get("salary_text") and job.get("salary_text"):
                target["salary_text"] = job["salary_text"]
            if job.get("published_at", "") > target.get("published_at", ""):
                target["published_at"] = job["published_at"]
        by_url[url_key] = target
        if valid_identity:
            by_identity[identity] = target
    results.sort(key=lambda x: x.get("published_at") or "", reverse=True)
    return results
