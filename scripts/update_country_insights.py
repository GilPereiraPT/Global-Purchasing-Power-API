"""Cron-only World Bank importer. Never run this from a public HTTP request.

Examples:
  python -m scripts.update_country_insights
  python -m scripts.update_country_insights --day 0
  python -m scripts.update_country_insights --country PT
"""
import argparse
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from app.country_insights import INDICATORS, ISO3, _fetch
from app.country_insights_store import connect, save_result

# Monday = 0; two countries per day; each country refreshed once a week.
WEEK = (
    ("PT", "ES"), ("DE", "FR"), ("GB", "IE"), ("NL", "CH"),
    ("IT", "US"), ("CA", "BR"), ("IN", "PK"),
)


def run(countries, pause=1.0):
    if not countries or len(countries) > 2 or len(set(countries)) != len(countries):
        raise ValueError("Run one or two distinct countries per invocation")
    if any(country not in ISO3 for country in countries):
        raise ValueError("Unsupported country")
    counts = {"available": 0, "empty": 0, "failed": 0}
    with connect() as db:
        for country in countries:
            print("Refreshing", country, flush=True)
            for name, (code, _) in INDICATORS.items():
                # The importer alone contacts the upstream source; no parallel
                # requests and a small delay between series to reduce load.
                status, observations, error = _fetch(country, code)
                if status == "available":
                    outcome = "available" if observations else "empty"
                else:
                    outcome = "failed"
                save_result(db, country, name, observations, status, error)
                counts[outcome] += 1
                print(country, name, outcome,
                      observations[0]["year"] if observations else "-",
                      error or "", flush=True)
                time.sleep(pause)
    print("Summary:", counts, flush=True)
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--country", choices=sorted(ISO3))
    selection.add_argument("--day", type=int, choices=range(7),
                           metavar="{0,1,2,3,4,5,6}",
                           help="Backfill a specific weekday pair")
    args = parser.parse_args(argv)
    weekday = datetime.now(ZoneInfo("Europe/Lisbon")).weekday()
    countries = ((args.country,) if args.country else
                 WEEK[args.day if args.day is not None else weekday])
    counts = run(countries)
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
