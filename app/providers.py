"""Official, free upstream connectors. No invented or silently extrapolated observations."""
import csv
import math
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
    """Decode only monthly all-items HICP indices for the requested geography."""
    try:
        dimensions = payload["id"]
        sizes = payload["size"]
        expected = {"geo", "unit", "coicop", "time"}
        if (not isinstance(dimensions, list) or len(set(dimensions)) != len(dimensions)
                or set(dimensions) not in (expected, expected | {"freq"})
                or len(sizes) != len(dimensions)):
            raise ValueError("Unexpected dimensions")
        indexes = {}
        for dimension, size in zip(dimensions, sizes):
            index = payload["dimension"][dimension]["category"]["index"]
            if (type(size) is not int or size <= 0 or not isinstance(index, dict)
                    or len(index) != size
                    or any(type(offset) is not int for offset in index.values())
                    or set(index.values()) != set(range(size))):
                raise ValueError("Invalid dimension offsets")
            indexes[dimension] = index
        unit = next((code for code in ("I25", "I15") if code in indexes["unit"]), None)
        if unit is None:
            raise ValueError("Expected HICP index unit")
        selected = {"geo": country, "unit": unit, "coicop": "CP00"}
        if "freq" in indexes:
            selected["freq"] = "M"
        fixed = {name: indexes[name][code] for name, code in selected.items()}
        values = payload["value"]
        if not isinstance(values, (dict, list)):
            raise ValueError("Invalid observations")
        series = []
        for period, offset in sorted(indexes["time"].items()):
            if (len(period) != 7 or period[4] != "-" or not period[:4].isdigit()
                    or not period[5:].isdigit() or not 1 <= int(period[5:]) <= 12):
                raise ValueError("Expected monthly periods")
            positions = {**fixed, "time": offset}
            linear = 0
            for dimension, size in zip(dimensions, sizes):
                linear = linear * size + positions[dimension]
            value = values.get(str(linear)) if isinstance(values, dict) else values[linear]
            if value is not None:
                number = float(value)
                if isinstance(value, bool) or not math.isfinite(number) or number <= 0:
                    raise ValueError("Invalid HICP index")
                series.append({"period": period, "index": number})
    except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
        raise UpstreamUnavailable("Unexpected Eurostat data structure") from exc
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
