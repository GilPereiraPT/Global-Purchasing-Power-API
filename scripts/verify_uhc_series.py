"""Read-only live-source check for WHO's revised UHC Service Coverage Index.

Checks WHO's official OData source (and separately documents World Bank's
published SH_UHC_SCI mirror). GitHub-hosted: no cPanel terminal, no DB writes.
"""
import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.country_insights import INDICATORS, ISO3, UHC_SERIES

WHO_SOURCE = "https://ghoapi.azureedge.net/api/UHC_INDEX_REPORTED"


def verify(country="PT"):
    assert country in ISO3
    code, unit = INDICATORS["health_coverage"]
    assert code == UHC_SERIES["current"] == "SH_UHC_SCI"
    assert unit == "index_0_100"
    url = WHO_SOURCE + "?" + urlencode({
        "$filter": "SpatialDim eq '" + ISO3[country] + "'",
        "$top": "1000",
        "$select": "SpatialDim,TimeDim,NumericValue,SpatialDimType",
    })
    request = Request(url, headers={
        "User-Agent": "EarnWage-UHC-Source-Validation/1.0",
        "Accept": "application/json"})
    for attempt in (1, 2):
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.load(response)
            break
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            print("WHO provider attempt", attempt, type(exc).__name__, flush=True)
            if attempt == 2:
                raise
            time.sleep(2)
    if not isinstance(payload, dict) or not isinstance(payload.get("value"), list):
        raise ValueError("WHO source returned unexpected format")
    records = [
        {"year": int(row["TimeDim"]), "value": float(row["NumericValue"])}
        for row in payload["value"]
        if isinstance(row, dict) and row.get("NumericValue") is not None
        and str(row.get("TimeDim", "")).isdigit()
        and row.get("SpatialDim") == ISO3[country]
        and row.get("SpatialDimType") in (None, "COUNTRY")
    ]
    if not records:
        raise ValueError("WHO source has no non-null UHC records for " + country)
    if any(not 0 <= row["value"] <= 100 for row in records):
        raise ValueError("Official UHC index outside 0-100")
    newest = max(row["year"] for row in records)
    if newest < 2023:
        raise ValueError("Unexpected last UHC year; inspect WHO dataset methodology")
    print("VALIDATED WHO OData UHC_INDEX_REPORTED / World Bank SH_UHC_SCI",
          country, len(records), "observations;",
          "latest published year:", newest,
          "latest index:", next(row["value"] for row in records
                                 if row["year"] == newest),
          flush=True)
    print("No EarnWage database or server state was changed", flush=True)


if __name__ == "__main__":
    sys.exit(verify("PT"))
