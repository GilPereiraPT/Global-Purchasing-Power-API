"""Offline weather proxy contracts: no live external weather requests in tests."""
import json
from datetime import datetime, timedelta, timezone
from email.message import Message
from unittest.mock import patch

from app import weather_metno as met

def test_capitals_are_whitelisted_and_no_external_call_without_contact(monkeypatch):
    monkeypatch.delenv("EARNWAGE_WEATHER_CONTACT", raising=False)
    with patch.object(met, "urlopen", side_effect=AssertionError("No request expected")):
        assert len(met.CAPITALS) == 14
        assert met.forecast("PT", 0)["status"] == "not_configured"
        assert met.forecast("PT", 1)["status"] == "not_covered"
    assert met.CAPITALS["PT"][0] == "Lisboa"
    assert met.CAPITALS["CA"][0] == "Ottawa"

def test_model_forecast_preserves_source_and_local_days():
    now=datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)+timedelta(hours=1)
    rows=[]
    for i in range(30):
        instant=now+timedelta(hours=i*6)
        rows.append({"time":instant.isoformat().replace("+00:00","Z"),
            "data":{"instant":{"details":{"air_temperature":10+i/3,
                                         "wind_speed":3.2,
                                         "relative_humidity":70}},
                    "next_1_hours":{"summary":{"symbol_code":"cloudy"}}}})
    report=met._forecast({"properties":{"timeseries":rows}},"PT")
    assert report["status"]=="available"
    assert report["current_forecast"]["temperature_c"] == 10.0
    assert report["source"]=="MET Norway Locationforecast 2.0"
    assert len(report["daily_forecast"]) <= 7
    assert report["climate_normals"]["status"]=="not_connected"
    assert all(r["sample_count"]>0 for r in report["daily_forecast"])

def test_weather_requests_use_contact_and_cache(monkeypatch):
    monkeypatch.setenv("EARNWAGE_WEATHER_CONTACT","https://github.com/GilPereiraPT/Global-Purchasing-Power-API")
    met._CACHE.clear()
    now=datetime.now(timezone.utc)+timedelta(hours=1)
    payload={"properties":{"timeseries":[{"time":now.isoformat(),"data":{
       "instant":{"details":{"air_temperature":21,"wind_speed":2,
                             "relative_humidity":55}}}}]}}
    headers=Message()
    headers["Expires"]="Wed, 09 Dec 2099 00:00:00 GMT"
    headers["Last-Modified"]="Sat, 07 Nov 2026 10:00:00 GMT"
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):return None
        def read(self,count):return json.dumps(payload).encode()
        @property
        def headers(self):return headers
    seen=[]
    def fetch(request,timeout):
        seen.append(request)
        assert timeout==12
        assert "lat=38.7223" in request.full_url
        assert "lon=-9.1393" in request.full_url
        assert "Earnwage/0.5" in request.get_header("User-agent").replace("EarnWage","Earnwage")
        return Response()
    with patch.object(met,"urlopen",side_effect=fetch):
        first=met.forecast("PT",0)
        second=met.forecast("PT",0)
    assert first["status"]=="available"
    assert second==first
    assert len(seen)==1
    met._CACHE.clear()
