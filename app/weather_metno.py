"""MET Norway Locationforecast proxy for EarnWage capital-city forecasts.

No direct browser requests to api.met.no. Only fixed, reviewed approximate city
centre coordinates; no arbitrary geocoding or unbounded user-supplied coordinates.
Use an identifying EARNWAGE_WEATHER_CONTACT URL/email in the User-Agent.
Forecast values are *model predictions*, not live observed weather or climate normals.
"""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import os
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

PROVIDER = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
ATTRIBUTION = "https://api.met.no/"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
# Approximate city-centre positions (WGS84 degrees, <=4 decimals), not GPS precision.
# Index 0 matches each existing country's first city in website/city-timezones.js.
CAPITALS = {
 "PT": ("Lisboa", 38.7223, -9.1393, "Europe/Lisbon"),
 "ES": ("Madrid", 40.4168, -3.7038, "Europe/Madrid"),
 "DE": ("Berlim", 52.5200, 13.4050, "Europe/Berlin"),
 "FR": ("Paris", 48.8566, 2.3522, "Europe/Paris"),
 "GB": ("Londres", 51.5074, -0.1278, "Europe/London"),
 "IE": ("Dublin", 53.3498, -6.2603, "Europe/Dublin"),
 "NL": ("Amesterdão", 52.3676, 4.9041, "Europe/Amsterdam"),
 "CH": ("Berna", 46.9480, 7.4474, "Europe/Zurich"),
 "IT": ("Roma", 41.9028, 12.4964, "Europe/Rome"),
 "US": ("Washington, D.C.", 38.9072, -77.0369, "America/New_York"),
 "CA": ("Ottawa", 45.4215, -75.6972, "America/Toronto"),
 "BR": ("Brasília", -15.7939, -47.8828, "America/Sao_Paulo"),
 "IN": ("Nova Deli", 28.6139, 77.2090, "Asia/Kolkata"),
 "PK": ("Islamabad", 33.6844, 73.0479, "Asia/Karachi"),
}
_CACHE = {}
_LOCK = threading.RLock()
MIN_CACHE_SECONDS = 3600
MAX_BYTES = 3_000_000

def _configured_contact():
    value = os.environ.get("EARNWAGE_WEATHER_CONTACT", "").strip()
    if not value or len(value) > 150 or any(c in value for c in "\r\n"):
        return None
    if not (value.startswith("https://") or ("@" in value and " " not in value)):
        return None
    return value

def _expiry(headers, now):
    raw = headers.get("Expires")
    if raw:
        try:
            parsed = parsedate_to_datetime(raw).astimezone(timezone.utc).timestamp()
            return max(now + MIN_CACHE_SECONDS, parsed)
        except (ValueError, TypeError, OverflowError):
            pass
    return now + MIN_CACHE_SECONDS

def _num(value):
    return round(float(value), 1) if isinstance(value, (float, int)) and not isinstance(value, bool) else None

def _forecast(payload, code):
    entries = payload.get("properties", {}).get("timeseries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Missing forecast timeseries")
    name, lat, lon, zone = CAPITALS[code]
    now = datetime.now(timezone.utc)
    rows = []
    for r in entries:
        if not isinstance(r, dict): continue
        try:
            moment = datetime.fromisoformat(r["time"].replace("Z", "+00:00"))
            if moment.tzinfo is None or moment < now: continue
            instant = r["data"]["instant"]["details"]
            temperature = _num(instant.get("air_temperature"))
            wind = _num(instant.get("wind_speed"))
            humidity = _num(instant.get("relative_humidity"))
            next1 = r["data"].get("next_1_hours", {})
            next6 = r["data"].get("next_6_hours", {})
            symbol = next1.get("summary", {}).get("symbol_code") or next6.get("summary", {}).get("symbol_code")
            rows.append({
              "time": moment.isoformat(), "local_date": moment.astimezone(ZoneInfo(zone)).date().isoformat(),
              "temperature_c": temperature, "wind_m_s": wind, "humidity_percent": humidity,
              "symbol_code": symbol if isinstance(symbol, str) else None,
            })
        except (KeyError, TypeError, ValueError):
            continue
    if not rows:
        raise ValueError("No future forecast observations")
    current = rows[0]
    dates = list(dict.fromkeys(r["local_date"] for r in rows))[:7]
    daily = []
    for date in dates:
        selection = [r for r in rows if r["local_date"] == date and r["temperature_c"] is not None]
        if not selection: continue
        temps = [r["temperature_c"] for r in selection]
        daily.append({"date": date, "min_temp_c": min(temps), "max_temp_c": max(temps),
                      "sample_count": len(temps), "partial_day": date == now.astimezone(ZoneInfo(zone)).date().isoformat()})
    return {
        "status": "available", "country": code, "city_id": 0, "city": name,
        "time_zone": zone, "location": {"latitude": lat, "longitude": lon,
             "note": "Approximate city-centre coordinates; forecasts represent model grid cells."},
        "current_forecast": current, "daily_forecast": daily,
        "forecast_reference": "Forecast time, not a local measured observation.",
        "daily_note": "Daily minima/maxima of available predicted samples, not observed daily extremes. First day may be partial.",
        "source": "MET Norway Locationforecast 2.0", "source_url": ATTRIBUTION,
        "license_url": LICENSE, "modified": "EarnWage groups hourly predicted temperatures into local forecast days.",
        "climate_normals": {"status": "not_connected", "value": None},
    }

def forecast(code, city_id=0):
    if code not in CAPITALS:
        raise ValueError("Unsupported country")
    if city_id != 0:
        return {"status": "not_covered", "country": code, "city_id": city_id,
                "reason": "Only capital-city weather coordinates are currently verified.",
                "current_forecast": None, "daily_forecast": []}
    contact = _configured_contact()
    if not contact:
        return {"status": "not_configured", "country": code, "city_id": city_id,
                "reason": "Set EARNWAGE_WEATHER_CONTACT in the API environment; no live request was sent.",
                "current_forecast": None, "daily_forecast": []}
    now = time.time()
    with _LOCK:
        cached = _CACHE.get(code)
        if cached and now < cached["expires"]:
            return cached["data"]
        name, lat, lon, _ = CAPITALS[code]
        headers = {"Accept": "application/json", "Accept-Encoding": "identity",
                   "User-Agent": "EarnWage/0.5 (" + contact + ")"}
        if cached and cached.get("last_modified"):
            headers["If-Modified-Since"] = cached["last_modified"]
        request = Request(PROVIDER + "?" + urlencode({"lat": f"{lat:.4f}", "lon": f"{lon:.4f}"}), headers=headers)
        try:
            with urlopen(request, timeout=12) as response:
                raw = response.read(MAX_BYTES+1)
                if len(raw)>MAX_BYTES: raise ValueError("Oversized weather response")
                data = _forecast(json.loads(raw), code)
                expires = _expiry(response.headers, now)
                _CACHE[code] = {"data": data, "expires": expires,
                    "last_modified": response.headers.get("Last-Modified")}
                return data
        except HTTPError as error:
            if error.code == 304 and cached:
                cached["expires"] = _expiry(error.headers, now)
                return cached["data"]
            reason = "upstream_unavailable"
        except (URLError, TimeoutError, ValueError, OSError, TypeError):
            reason = "upstream_unavailable"
        if cached:
            return {**cached["data"], "stale": True, "refresh_status": reason}
        return {"status": reason, "country": code, "city_id": city_id,
                "current_forecast": None, "daily_forecast": [], "reason": "Weather service unavailable."}
