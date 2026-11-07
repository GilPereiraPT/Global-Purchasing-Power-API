"""Static contract tests for the EarnWage city clock website addition."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / "website"
COUNTRIES = ("PT","ES","DE","FR","GB","IE","NL","CH","IT","US","CA","BR","IN","PK")
LANGUAGES = ("en","pt","es","de","fr","it","nl")

def test_city_clock_is_mounted_without_replacing_existing_dashboard():
    html = (ROOT / "country.html").read_text(encoding="utf-8")
    assert 'id="countryCityTime"' in html
    assert 'id="detailsResults"' in html
    assert 'id="countryGuide"' in html
    for resource in ("country-city-time.css","city-timezones.js","country-city-time.js"):
        assert resource in html

def test_all_countries_have_city_choices_and_iata_independent_time_zones():
    script=(ROOT/"city-timezones.js").read_text(encoding="utf-8")
    for code in COUNTRIES:
        assert re.search(r"\b"+code+r":\[",script),code
    assert '"Atlantic/Azores"' in script
    assert '"Atlantic/Canary"' in script
    assert '"America/Los_Angeles"' in script
    assert '"Pacific/Honolulu"' in script

def test_clocks_are_local_and_no_weather_numbers_are_invented():
    script=(ROOT/"country-city-time.js").read_text(encoding="utf-8")
    assert "Intl.DateTimeFormat" in script
    assert "timeZone:city.timeZone" in script
    assert "setInterval(tick,1000)" in script
    assert "weather" in script
    assert "fetch(" not in script
    for language in LANGUAGES:
        assert re.search(r"\b"+language+r":\{",script),language
