"""Official, free upstream connectors. No invented or silently extrapolated observations."""
import csv
from io import StringIO

import httpx

from app import store

EUROSTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_minr"
ECB = "https://data-api.ecb.europa.eu/service/data/EXR"
HEADERS = {"User-Agent": "GlobalPurchasingPowerAPI/0.1 (economic statistics)"}


class UpstreamUnavailable(Exception):
    pass


async def fetch_json(url, params, cache_key, ttl=86400):
    cached = store.get(cache_key, ttl)
    if cached is not None:
        return cached
    try:
        async with httpx.AsyncClient(timeout=25, headers=HEADERS, follow_redirects=True) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            result = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise UpstreamUnavailable("Official data provider unavailable") from exc
    store.set_value(cache_key, result)
    return result


def parse_eurostat(payload, country):
    """Decode JSON-stat sparse values using official dimension order."""
    dimensions = payload.get("id", [])
    sizes = payload.get("size", [])
    dim_info = payload.get("dimension", {})
    if not dimensions or not sizes or "time" not in dimensions:
        raise UpstreamUnavailable("Unexpected Eurostat data structure")
    time_info = dim_info["time"]["category"]["index"]
    # Explicitly restrict the other dimensions, especially unit and COICOP.
    fixed = {}
    for dimension in dimensions:
        if dimension == "time":
            continue
        indices = dim_info[dimension]["category"]["index"]
        if dimension == "geo" and country in indices:
            fixed[dimension] = indices[country]
        elif dimension == "coicop" and "CP00" in indices:
            fixed[dimension] = indices["CP00"]
        elif dimension == "unit":
            preferred = next((v for v in ("I25", "I15") if v in indices), None)
            fixed[dimension] = indices[preferred] if preferred else min(indices.values())
        else:
            fixed[dimension] = min(indices.values())
    values = payload.get("value", {})
    series = []
    for period, offset in sorted(time_info.items()):
        positions = {**fixed, "time": offset}
        linear = 0
        for dimension, size in zip(dimensions, sizes):
            linear = linear * size + positions[dimension]
        value = values.get(str(linear)) if isinstance(values, dict) else values[linear]
        if value is not None:
            series.append({"period": period, "index": float(value)})
    if not series:
        raise UpstreamUnavailable("No observations for selected country")
    return series


async def inflation_series(country):
    payload = await fetch_json(
        EUROSTAT, {"geo": country, "coicop": "CP00", "lang": "EN"},
        f"eurostat:hicp:minr:{country}", ttl=86400,
    )
    series = parse_eurostat(payload, country)
    return {"country": country, "frequency": "monthly", "series": series,
            "source": "Eurostat", "dataset": "prc_hicp_minr",
            "source_url": EUROSTAT, "geography": "national",
            "note": "HICP index: not an observed cost-of-living basket in the capital."}


async def exchange_rate(currency):
    if currency == "EUR":
        return {"currency": "EUR", "units_per_eur": 1.0, "period": None, "source": "identity"}
    key = f"ecb:exchange:{currency}"
    cached = store.get(key, 86400)
    if cached is not None:
        return cached
    url = f"{ECB}/D.{currency}.EUR.SP00.A"
    try:
        async with httpx.AsyncClient(timeout=25, headers=HEADERS, follow_redirects=True) as client:
            response = await client.get(url, params={"format": "csvdata", "lastNObservations": 1})
            if response.status_code == 404:
                return None
            response.raise_for_status()
            rows = list(csv.DictReader(StringIO(response.text)))
    except httpx.HTTPError as exc:
        raise UpstreamUnavailable("ECB unavailable") from exc
    if not rows:
        return None
    row = rows[-1]
    try:
        value = float(row["OBS_VALUE"])
    except (KeyError, ValueError, TypeError) as exc:
        raise UpstreamUnavailable("Unexpected ECB data structure") from exc
    result = {"currency": currency, "units_per_eur": value, "period": row.get("TIME_PERIOD"),
              "source": "ECB", "source_url": url,
              "note": "Reference rate; not a retail money-transfer rate."}
    store.set_value(key, result)
    return result
