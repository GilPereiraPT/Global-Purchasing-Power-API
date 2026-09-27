"""Aggregate ATS smoke test for all 14 EarnWage countries and several occupations.

Run after cPanel deployment:
  python scripts/jobs_international_smoke.py https://earnwage-api.policlinicosdesantoandre.com
This checks a 14 x 3 x 3 matrix without printing thousands of individual jobs.
"""
import json
import sys
import time
from urllib.parse import urlencode
from urllib.request import urlopen

COUNTRIES = ("PT", "ES", "DE", "FR", "GB", "IN", "BR", "PK",
             "NL", "CH", "IT", "IE", "US", "CA")
OCCUPATIONS = ("software_developer", "nurse", "accountant")
PROVIDERS = ("lever", "greenhouse", "ashby")


def run(base):
    summary = []
    for provider in PROVIDERS:
        for country in COUNTRIES:
            for occupation in OCCUPATIONS:
                query = urlencode({"provider": provider, "country": country,
                                   "occupation": occupation, "limit": 1,
                                   "debug": "true"})
                url = base.rstrip("/") + "/v1/jobs?" + query
                try:
                    with urlopen(url, timeout=100) as response:
                        data = json.load(response)
                    summary.append({"provider": provider, "country": country,
                                    "occupation": occupation, "count": data.get("count"),
                                    "boards_failed": data.get("boards_failed", []),
                                    "jobs_before_filter": data.get("jobs_before_filter"),
                                    "error": None})
                except Exception as exc:
                    summary.append({"provider": provider, "country": country,
                                    "occupation": occupation, "error": str(exc)})
                time.sleep(0.15)
    print(json.dumps({"version": "0.5.14", "queries": len(summary),
                      "errors": sum(bool(x["error"]) for x in summary),
                      "results": summary}, ensure_ascii=False, indent=2))
    return 1 if any(x["error"] for x in summary) else 0


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1] if len(sys.argv) > 1 else
                         "https://earnwage-api.policlinicosdesantoandre.com"))
