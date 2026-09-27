"""EarnWage country insights: sourced World Bank observations, no invented values.

This module does not calculate an EarnWage quality-of-life score.
Gallup Law and Order data are not fetched/scraped without a redistribution licence.
"""
import json
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

ISO3 = {
    "PT": "PRT", "ES": "ESP", "DE": "DEU", "FR": "FRA",
    "GB": "GBR", "IE": "IRL", "NL": "NLD", "CH": "CHE",
    "IT": "ITA", "US": "USA", "CA": "CAN", "BR": "BRA",
    "IN": "IND", "PK": "PAK",
}
INDICATORS = {
    "life_expectancy": ("SP.DYN.LE00.IN", "years"),
    "unemployment": ("SL.UEM.TOTL.ZS", "percent_of_labor_force"),
    "gdp_per_capita": ("NY.GDP.PCAP.CD", "USD_current_per_person"),
    "gini": ("SI.POV.GINI", "index_0_100"),
    "health_coverage": ("SH_UHC_SCI", "index_0_100"),
    "primary_completion": ("SE.PRM.CMPT.ZS", "percent_of_relevant_age_group"),
    "adult_literacy": ("SE.ADT.LITR.ZS", "percent_of_adults_15_plus"),
    "electricity_access": ("EG.ELC.ACCS.ZS", "percent_of_population"),
    "safe_drinking_water": ("SH.H2O.SMDW.ZS", "percent_of_population"),
    "safe_sanitation": ("SH.STA.SMSS.ZS", "percent_of_population"),
    "internet_use": ("IT.NET.USER.ZS", "percent_of_population"),
    "inflation_annual": ("FP.CPI.TOTL.ZG", "annual_percent"),
    "ppp_private_consumption": ("PA.NUS.PRVT.PP", "local_currency_units_per_international_dollar"),
}
# SH.UHC.SRVS.CV.XD is the archived 2000-2021 WHO index. The official
# revised SDG 3.8.1 indicator is SH_UHC_SCI (2025 methodology; available
# years include 2000-2023). It is not a population coverage percentage.
# Existing production inventory (2026-09-27) had zero observations under
# health_coverage, so the new source must be imported afresh, not spliced
# onto records calculated under the previous methodology.
UHC_SERIES = {
    "current": "SH_UHC_SCI",
    "legacy": "SH.UHC.SRVS.CV.XD",
    "methodology": "WHO 2025 revised SDG 3.8.1 Service Coverage Index",
    "methodology_url":
        "https://blogs.worldbank.org/en/opendata/tracking-universal-health-coverage-with-updated-indicators-in-th0",
    "note": ("Index 0-100 of essential health service coverage (2025 WHO methodology); "
             "not the share of people covered or a guarantee of financial protection. "
             "Compare years and methodologies before making time-trend claims."),
}
SOURCE = "https://api.worldbank.org/v2/country/{country}/indicator/{indicator}?format=json&per_page=1000"
WHO_UHC_SOURCE = "https://ghoapi.azureedge.net/api/UHC_INDEX_REPORTED"
CACHE_SECONDS = 86400
_CACHE = {}
_LOCK = threading.Lock()


def _fetch_world_bank(country, indicator):
    """Official World Bank indicator mirror. No fabricated missing years."""
    url = SOURCE.format(country=quote(ISO3[country]),
                        indicator=quote(indicator))
    request = Request(url, headers={"User-Agent": "EarnWage/0.5 CountryInsights",
                                    "Accept": "application/json"})
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.load(response)
        if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
            raise ValueError("Unexpected World Bank response")
        observations = [
            {"year": int(row["date"]), "value": float(row["value"])}
            for row in payload[1]
            if isinstance(row, dict) and row.get("value") is not None
            and str(row.get("date", "")).isdigit()
        ]
        observations.sort(key=lambda item: item["year"], reverse=True)
        return "available", observations, None
    except (HTTPError, URLError, TimeoutError, ValueError,
            TypeError, KeyError, OSError) as exc:
        return "upstream_unavailable", [], type(exc).__name__


def _fetch_who_uhc(country):
    """WHO GHO, revised SDG 3.8.1 index (not percent or old methodology)."""
    url = WHO_UHC_SOURCE + "?" + urlencode({
        "$filter": "SpatialDim eq '" + ISO3[country] + "'",
        "$top": "1000",
        "$select": "SpatialDim,TimeDim,NumericValue,SpatialDimType",
    })
    request = Request(url, headers={"User-Agent": "EarnWage/0.5 WHO-UHC",
                                    "Accept": "application/json"})
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.load(response)
        if not isinstance(payload, dict) or not isinstance(payload.get("value"), list):
            raise ValueError("Unexpected WHO UHC response")
        if payload.get("@odata.nextLink"):
            # Fail closed rather than silently discarding part of a time series.
            raise ValueError("Unexpected paginated WHO UHC response")
        observations = []
        for row in payload["value"]:
            if not isinstance(row, dict) or row.get("NumericValue") is None:
                continue
            if row.get("SpatialDim") != ISO3[country] or row.get("SpatialDimType") not in (None, "COUNTRY"):
                continue
            if not str(row.get("TimeDim", "")).isdigit():
                continue
            year, value = int(row["TimeDim"]), float(row["NumericValue"])
            if not 0 <= value <= 100:
                raise ValueError("Invalid WHO UHC 0-100 index")
            observations.append({"year": year, "value": value})
        observations.sort(key=lambda item: item["year"], reverse=True)
        if not observations:
            return "upstream_unavailable", [], "NoWHOObservations"
        if len({row["year"] for row in observations}) != len(observations):
            raise ValueError("Duplicate WHO country-year records")
        return "available", observations, None
    except (HTTPError, URLError, TimeoutError, ValueError,
            TypeError, KeyError, OSError) as exc:
        return "upstream_unavailable", [], type(exc).__name__


def _fetch(country, indicator):
    key = (country, indicator)
    with _LOCK:
        cached = _CACHE.get(key)
        if cached and time.time() - cached[0] < CACHE_SECONDS:
            return cached[1]
    if indicator == UHC_SERIES["current"]:
        # WHO's live 2025-methodology index was verified on 2026-09-27
        # for Portugal: 24 records, latest year 2023, index 83.0.
        # World Bank has the same published SH_UHC_SCI indicator but its
        # API timed out twice on the GitHub-hosted source verification.
        result = _fetch_who_uhc(country)
        if result[0] != "available":
            mirror = _fetch_world_bank(country, indicator)
            if mirror[0] == "available" and mirror[1] and all(
                    0 <= item["value"] <= 100 for item in mirror[1]):
                result = mirror
            elif mirror[0] == "available" and mirror[1]:
                result = ("upstream_unavailable", [], "InvalidUHCIndex")
    else:
        result = _fetch_world_bank(country, indicator)
    with _LOCK:
        _CACHE[key] = (time.time(), result)
    return result


def indicator(country, name, year=None, history=False):
    """Serve only locally imported data; never call the World Bank on HTTP."""
    from app.country_insights_store import connect, read_indicator
    with connect() as db:
        return read_indicator(db, country, name, year=year, history=history)


def safety(country):
    if country not in ISO3:
        raise ValueError("Unsupported country")
    return {
        "country": country, "status": "unavailable", "value": None, "year": None,
        "name": "Gallup Law and Order Index",
        "unit": "index_0_100",
        "source": "Gallup World Poll",
        "source_url": "https://www.gallup.com/analytics/694904/what-is-law-order-index.aspx",
        "reason": "Automated licensed country-level dataset not yet connected; do not substitute homicide rates or scrape Gallup.",
        "alternative": {
            "name": "Feeling safe walking alone after dark",
            "sdg_indicator": "16.1.4",
            "sdg_series": "VC_SNS_WALN_DRK",
            "source_url": "https://unstats.un.org/sdgs/metadata/files/Metadata-16-01-04.pdf",
            "status": "not_connected",
        },
    }


def country_insights(country):
    if country not in ISO3:
        raise ValueError("Unsupported country")
    from app.country_insights_store import connect, read_indicator
    with connect() as db:
        result = {name: read_indicator(db, country, name) for name in INDICATORS}
    result["safety"] = safety(country)
    return {"country": country, "iso3": ISO3[country], "indicators": result,
            "note": "Locally cached independent official indicators; no live World Bank calls, composite score or personal access guarantee."}
