"""Read-only live source check for EarnWage's revised WHO UHC index.

Run in the GitHub Actions hosted runner, not on the user's cPanel terminal.
Does not require an admin token and NEVER writes to the production database.
"""
import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.country_insights import INDICATORS, ISO3, UHC_SERIES, SOURCE


def verify(country="PT"):
    assert country in ISO3
    code, unit = INDICATORS["health_coverage"]
    assert code == UHC_SERIES["current"] == "SH_UHC_SCI"
    assert unit == "index_0_100"
    url = SOURCE.format(country=ISO3[country], indicator=code)
    request = Request(url, headers={
        "User-Agent": "EarnWage-UHC-Source-Validation/1.0",
        "Accept": "application/json"})
    for attempt in (1, 2):
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.load(response)
            break
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            print("WHO UHC provider attempt", attempt, type(exc).__name__, flush=True)
            if attempt == 2:
                raise
            time.sleep(2)
    if not isinstance(payload, list) or len(payload) != 2 \
            or not isinstance(payload[1], list):
        raise ValueError("WHO UHC provider returned unexpected format")
    records = [
        {"year": int(row["date"]), "value": float(row["value"])}
        for row in payload[1]
        if isinstance(row, dict) and row.get("value") is not None
        and str(row.get("date", "")).isdigit()
    ]
    if not records:
        raise ValueError("Official source has zero non-null UHC records for " + country)
    if any(not 0 <= row["value"] <= 100 for row in records):
        raise ValueError("Official UHC index outside 0-100")
    newest = max(row["year"] for row in records)
    if newest < 2023:
        raise ValueError("Unexpected last UHC year; inspect dataset metadata")
    print("VALIDATED official WHO/World Bank revised UHC source",
          country, code, len(records), "observations;",
          "latest published year:", newest,
          "latest index:", next(row["value"] for row in records
                                 if row["year"] == newest),
          flush=True)
    print("No EarnWage database or server state was changed", flush=True)


if __name__ == "__main__":
    sys.exit(verify("PT"))
