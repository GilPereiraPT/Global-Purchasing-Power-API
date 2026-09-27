"""Three no-key remote job feeds: Himalayas, Jobicy and Remote OK.

Country eligibility is conservative: unknown or regional-only locations are not
presented as verified eligibility in a particular country.
"""
from datetime import datetime, timezone
from urllib.parse import urlsplit
import httpx
from app import store
from app.jobs import COUNTRY_NAMES, title_matches, location_matches
from app.providers import UpstreamUnavailable

TTL = {"himalayas": 24*3600, "jobicy": 6*3600, "remoteok": 6*3600}
URLS = {
    "himalayas": "https://himalayas.app/jobs/api",
    "jobicy": "https://jobicy.com/api/v2/remote-jobs",
    "remoteok": "https://remoteok.com/api",
}
SOURCES = {"himalayas":"Himalayas", "jobicy":"Jobicy", "remoteok":"Remote OK"}
HOSTS = {
    "himalayas": {"himalayas.app","www.himalayas.app"},
    "jobicy": {"jobicy.com","www.jobicy.com"},
    "remoteok": {"remoteok.com","www.remoteok.com"},
}

def iso(value):
    if isinstance(value, (int,float)) and not isinstance(value,bool):
        try:
            return datetime.fromtimestamp(value / 1000 if value > 100000000000 else value, timezone.utc).isoformat()
        except (ValueError, OverflowError, OSError):
            return None
    if isinstance(value,str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z","+00:00")).astimezone(timezone.utc).isoformat()
        except ValueError:
            return None
    return None

def safe_url(value, provider):
    if not isinstance(value,str):
        return None
    p=urlsplit(value)
    return value if p.scheme=="https" and p.hostname in HOSTS[provider] else None

def salary(low,high,currency,period):
    if not isinstance(currency,str) or len(currency)!=3 or not currency.isalpha():
        return None
    if not any(isinstance(v,(int,float)) and not isinstance(v,bool) and v>0 for v in (low,high)):
        return None
    return {"min":low if isinstance(low,(int,float)) and not isinstance(low,bool) and low>0 else None,
            "max":high if isinstance(high,(int,float)) and not isinstance(high,bool) and high>0 else None,
            "currency":currency.upper(),"period":period or "unspecified"}

def base(provider,ident,title,company,url,location,published,fetched,structured,employment,scope):
    if not ident or not isinstance(title,str) or not title.strip() or not url or not published:
        return None
    return {"id":provider+":"+str(ident),"provider_id":ident,"title":title.strip(),
            "company":company if isinstance(company,str) else None,
            "candidate_required_location":location,"category":None,
            "salary_text":None,"salary_structured":structured,
            "employment_type":employment,"published_at":published,"last_checked_at":fetched,
            "source":SOURCES[provider],"source_url":url,"apply_url":url,
            "remote":True,"status":"listed_by_source","location_match":scope,
            "note":"Remote work and advertised geographic eligibility do not establish visa or tax rights."}

def normalize(provider,row,fetched):
    if provider=="himalayas":
        url=safe_url(row.get("applicationLink"),provider)
        restrictions=row.get("locationRestrictions")
        if not isinstance(restrictions,list):
            return None
        codes={x.get("alpha2","").upper() for x in restrictions if isinstance(x,dict)
               and isinstance(x.get("alpha2"),str)}
        if restrictions and not codes:
            return None
        item=base(provider,row.get("guid"),row.get("title"),row.get("companyName"),
                  url,", ".join(sorted(codes)) if codes else "Worldwide",
                  iso(row.get("pubDate")),fetched,
                  salary(row.get("minSalary"),row.get("maxSalary"),row.get("currency"),row.get("salaryPeriod") or "annual"),
                  row.get("employmentType"),"country_explicit" if codes else "worldwide")
        if item is not None:
            item["eligible_country_codes"]=sorted(codes)
        return item
    if provider=="jobicy":
        url=safe_url(row.get("url"),provider)
        geo=row.get("jobGeo")
        if not isinstance(geo,str) or not geo.strip():
            return None
        types=row.get("jobType")
        item=base(provider,row.get("id"),row.get("jobTitle"),row.get("companyName"),
                  url,geo,iso(row.get("pubDate")),fetched,
                  salary(row.get("salaryMin"),row.get("salaryMax"),row.get("salaryCurrency"),row.get("salaryPeriod")),
                  ", ".join(types) if isinstance(types,list) else types,"country_mentioned")
        return item
    url=safe_url(row.get("url"),provider)
    location=row.get("location")
    if not isinstance(location,str) or not location.strip():
        return None
    return base(provider,row.get("id"),row.get("position"),row.get("company"),
                url,location,iso(row.get("date")) or iso(row.get("epoch")),fetched,
                salary(row.get("salary_min"),row.get("salary_max"),"USD","annual"),
                None,"country_mentioned")

async def feed(provider):
    key="jobs:"+provider+":v1"
    cached=store.get(key,TTL[provider])
    if cached is not None:
        return cached
    fetched=datetime.now(timezone.utc).isoformat()
    records=[]
    try:
        async with httpx.AsyncClient(timeout=30,follow_redirects=True,
                                     headers={"User-Agent":"EarnWage/0.6 (+source attribution)"}) as client:
            if provider=="himalayas":
                for offset in (0,20,40):
                    response=await client.get(URLS[provider],params={"offset":offset,"limit":20})
                    response.raise_for_status()
                    payload=response.json()
                    if not isinstance(payload,dict) or not isinstance(payload.get("jobs"),list):
                        raise UpstreamUnavailable("Unexpected Himalayas schema")
                    records.extend(payload["jobs"])
                    if offset+20>=payload.get("totalCount",0):
                        break
            else:
                response=await client.get(URLS[provider],params={"count":200} if provider=="jobicy" else None)
                response.raise_for_status()
                payload=response.json()
                if provider=="jobicy" and isinstance(payload,dict):
                    records=payload.get("jobs")
                elif provider=="remoteok" and isinstance(payload,list):
                    records=payload
                else:
                    raise UpstreamUnavailable("Unexpected "+provider+" schema")
                if not isinstance(records,list):
                    raise UpstreamUnavailable("Unexpected "+provider+" listings")
    except (httpx.HTTPError,ValueError) as exc:
        raise UpstreamUnavailable(provider+" job feed unavailable") from exc
    listings=[job for row in records if isinstance(row,dict)
              if (job:=normalize(provider,row,fetched)) is not None]
    data={"jobs":listings,"fetched_at":fetched}
    store.set_value(key,data)
    return data

def eligible(job,provider,country):
    if provider=="himalayas":
        codes=job["eligible_country_codes"]
        return "country_explicit" if country in codes else ("worldwide" if not codes else None)
    # Jobicy's broad regions (e.g. Europe) are not proof of eligibility in every member state.
    return location_matches(job["candidate_required_location"],country)

async def search(provider,country,occupation,salary_published=False,limit=20):
    if provider not in URLS:
        raise ValueError("Unknown provider")
    data=await feed(provider)
    found=[]
    for job in data["jobs"]:
        if not title_matches(job["title"],occupation):
            continue
        scope=eligible(job,provider,country)
        if not scope or (salary_published and not job["salary_structured"]):
            continue
        found.append({**job,"destination_country":country,"location_match":scope})
    found.sort(key=lambda x:x["published_at"],reverse=True)
    return {"status":"available" if found else "no_results","provider":SOURCES[provider],
            "country":country,"occupation":occupation,"count":len(found),
            "returned":min(len(found),limit),"jobs":found[:limit],
            "fetched_at":data["fetched_at"],"source_url":URLS[provider],
            "scope":"A limited recent feed, not a complete national job census.",
            "notice":"Visit the attributed original listing to verify eligibility and availability."}
