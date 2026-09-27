"""GitHub Actions scheduler client for a *deployed*, token-protected EarnWage API.

Does not access the cPanel filesystem or GitHub-stored SQLite copies.
Only sends bounded one-indicator imports through the same admin interface.
Requires repository Actions secret EARNWAGE_ADMIN_TOKEN, matching the API
environment variable. Set EARNWAGE_SCHEDULE_ENABLED=true as repository
Actions variable only after deployment and the first manual backup test.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

API = "https://earnwage-api.policlinicosdesantoandre.com"
WORLD_BANK_WEEK = (
    ("PT", "ES"), ("DE", "FR"), ("GB", "IE"), ("NL", "CH"),
    ("IT", "US"), ("CA", "BR"), ("IN", "PK"),
)
EUROSTAT_WEEK = (
    ("PT", "ES"), ("DE", "FR"), ("IE", "NL"), ("IT", "GB"),
    ("CH",), (), (),
)
ECONOMIC = (
    "hicp_annual_change_monthly",
    "household_price_level_eu27",
    "net_annual_earnings_reference",
)
ESSENTIAL = ("inflation_annual", "ppp_private_consumption")
# This World Bank code fails for all 14 countries in the exported baseline.
# Do not generate a predictable failing scheduled run until its official
# replacement/lineage has been validated; keep the browser diagnostic available.
PENDING_SOURCE_REVIEW = frozenset({"health_coverage"})


def post(token, route, payload=None, timeout=60):
    body = json.dumps(payload if payload is not None else {}).encode("utf-8")
    request = Request(
        API + "/v1/admin/data-manager/" + route,
        data=body,
        headers={"Content-Type": "application/json",
                 "X-EarnWage-Admin-Token": token,
                 "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            result = json.load(response)
    except HTTPError as exc:
        # No tokens or response bodies in public runner logs.
        raise RuntimeError(route + ": API HTTP " + str(exc.code)) from None
    except (URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError(route + ": API connection/JSON failure (" +
                           type(exc).__name__ + ")") from None
    if not isinstance(result, dict):
        raise RuntimeError(route + ": invalid JSON structure")
    return result


def plan(source, country, essentials=False, weekday=None, indicators=None):
    if weekday is None:
        weekday = datetime.now(ZoneInfo("Europe/Lisbon")).weekday()
    if weekday not in range(7):
        raise ValueError("Invalid weekday")
    pairs = WORLD_BANK_WEEK if source == "world_bank" else EUROSTAT_WEEK
    selected_countries = (country,) if country != "AUTO" else pairs[weekday]
    if source == "world_bank":
        selected_indicators = (ESSENTIAL if essentials else indicators)
        if not selected_indicators:
            raise ValueError("World Bank indicator catalogue missing")
        selected_indicators = tuple(i for i in selected_indicators
                                    if i not in PENDING_SOURCE_REVIEW)
        return [(source, c, i) for c in selected_countries
                for i in selected_indicators]
    return [(source, c, i) for c in selected_countries for i in ECONOMIC]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True,
                        choices=("world_bank", "eurostat"))
    parser.add_argument("--country", default="AUTO")
    parser.add_argument("--mode", default="refresh", choices=("refresh", "missing"))
    parser.add_argument("--essentials", action="store_true")
    args = parser.parse_args(argv)
    token = os.environ.get("EARNWAGE_ADMIN_TOKEN", "")
    if len(token) < 32:
        raise RuntimeError("Actions secret EARNWAGE_ADMIN_TOKEN not configured")
    info = post(token, "status")
    if info.get("status") != "ok":
        raise RuntimeError("Data Manager status not ready")
    today = datetime.now(ZoneInfo("Europe/Lisbon")).weekday()
    if not info.get("backups") or (args.country == "AUTO" and
                                  args.source == "world_bank" and today == 0):
        result = post(token, "backup", timeout=90)
        if result.get("status") != "available":
            raise RuntimeError("Verified private backup was not created")
        print("Verified private backup:", result["backup_id"], flush=True)
    selected = plan(args.source, args.country, args.essentials,
                    weekday=today, indicators=info.get("indicators"))
    if not selected:
        print("No countries assigned today to this importer", flush=True)
        return 0
    errors = 0
    for source, country, indicator in selected:
        item = {"source": source, "country": country,
                "indicator": indicator, "mode": args.mode}
        try:
            result = post(token, "import", item, timeout=55)
            status = result.get("import_status", "invalid_reply")
        except RuntimeError as exc:
            status = "failed"
            print(country, indicator, str(exc), flush=True)
        print(source, country, indicator, status, flush=True)
        if status not in ("available", "skipped_existing", "empty"):
            errors += 1
        time.sleep(1)
    print("Completed:", len(selected), "series;", errors,
          "failed or unavailable.", flush=True)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
