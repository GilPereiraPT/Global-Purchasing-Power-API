"""Controlled, incremental World Bank importer. Never expose on public HTTP.

Examples (one country first; then pairs on separate invocations):
  python -m scripts.update_country_insights --country PT --dry-run --missing-only
  python -m scripts.update_country_insights --country PT --missing-only
  python -m scripts.update_country_insights --day 0 --missing-only
  python -m scripts.update_country_insights --country PT --indicator inflation_annual --indicator ppp_private_consumption

Keep EARNWAGE_INSIGHTS_DB pointing to the same persistent SQLite file as Passenger.
Back up both EarnWage databases before the first consolidation import.
"""
import argparse
import json
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from app.country_insights import INDICATORS, ISO3, _fetch
from app.country_insights_store import connect, read_indicator, save_result

# Monday = 0. At most two countries per invocation; never import all at once.
WEEK = (
    ("PT", "ES"), ("DE", "FR"), ("GB", "IE"), ("NL", "CH"),
    ("IT", "US"), ("CA", "BR"), ("IN", "PK"),
)


def run(countries, pause=1.0, indicators=None, missing_only=False, dry_run=False):
    if not countries or len(countries) > 2 or len(set(countries)) != len(countries):
        raise ValueError("Choose one or two distinct countries")
    if any(country not in ISO3 for country in countries):
        raise ValueError("Unsupported country")
    selected = tuple(dict.fromkeys(indicators if indicators is not None else INDICATORS))
    if not selected or any(name not in INDICATORS for name in selected):
        raise ValueError("Unknown or empty indicator selection")
    if pause < 0:
        raise ValueError("Invalid pause")
    counts = {"available": 0, "empty": 0, "failed": 0,
              "skipped_existing": 0, "planned": 0}
    # Connect through exactly the same persistent store as public Country Insights.
    with connect() as db:
        for country in countries:
            print("Country:", country, flush=True)
            for name in selected:
                if missing_only:
                    existing = read_indicator(db, country, name)
                    if existing["status"] == "available":
                        counts["skipped_existing"] += 1
                        print(country, name, "skipped_existing",
                              existing.get("year"), flush=True)
                        continue
                counts["planned"] += 1
                if dry_run:
                    print(country, name, "would_import", INDICATORS[name][0],
                          flush=True)
                    continue
                status, observations, error = _fetch(country, INDICATORS[name][0])
                outcome = ("available" if observations else "empty") if (
                    status == "available") else "failed"
                # Failed/empty responses update refresh status but NEVER wipe observations.
                save_result(db, country, name, observations, status, error)
                counts[outcome] += 1
                print(country, name, outcome,
                      observations[0]["year"] if observations else "-",
                      error or "", flush=True)
                time.sleep(pause)
    print("Summary:", json.dumps(counts, sort_keys=True), flush=True)
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--country", choices=sorted(ISO3))
    selection.add_argument("--day", type=int, choices=range(7),
                           metavar="{0,1,2,3,4,5,6}")
    parser.add_argument("--indicator", choices=sorted(INDICATORS), action="append",
                        help="Import only this named indicator (repeatable)")
    parser.add_argument("--missing-only", action="store_true",
                        help="Skip an indicator only if a real stored value exists")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be imported without requesting/saving data")
    args = parser.parse_args(argv)
    weekday = datetime.now(ZoneInfo("Europe/Lisbon")).weekday()
    countries = ((args.country,) if args.country else
                 WEEK[args.day if args.day is not None else weekday])
    counts = run(countries, indicators=args.indicator,
                 missing_only=args.missing_only, dry_run=args.dry_run)
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
