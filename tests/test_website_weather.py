"""Website weather panel wiring and licensing guards."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/"website"

def test_weather_panel_is_loaded_before_city_clock_and_retains_existing_sections():
    html=(ROOT/"country.html").read_text(encoding="utf-8")
    assert 'src="./country-weather.js"' in html
    assert 'href="./country-weather.css"' in html
    assert html.index('src="./country-weather.js"') < html.index('src="./country-city-time.js"')
    assert 'id="countryCityTime"' in html
    assert 'id="countryCityCompare"' in html
    assert 'id="countryPolitics"' in html

def test_no_direct_weather_api_calls_or_unlicensed_historical_data():
    panel=(ROOT/"country-weather.js").read_text(encoding="utf-8")
    city=(ROOT/"country-city-time.js").read_text(encoding="utf-8")
    assert 'window.EarnWageConfig.apiBase' in panel
    assert '"/v1/weather/"' in panel
    assert 'window.EarnWageWeather?.load' in city
    assert 'https://api.met.no/' in panel
    assert 'https://creativecommons.org/licenses/by/4.0/' in panel
    assert 'fetch("https://api.met.no/' not in panel
    assert 'climate_normals' not in panel or 'not_connected' not in panel

def test_weather_translations_present():
    panel=(ROOT/"country-weather.js").read_text(encoding="utf-8")
    for locale in ("en","pt","es","de","fr","it","nl"):
        assert "\n"+locale+":{pending:" in panel
