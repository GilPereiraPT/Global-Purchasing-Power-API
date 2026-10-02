import pytest

from app import store
from app.earnwage_history import exact_history, observation_year
from app.north_america import persist


@pytest.mark.parametrize('period,year', [('May 2025', 2025), ('December 2024', 2024),
                                         ('2025', 2025), ('2023-2024', 2023)])
def test_observation_year(period, year):
    assert observation_year(period) == year


@pytest.mark.parametrize('period', ['Unknown 2025', 'May unknown', '', '202'])
def test_unknown_period_does_not_invent_year(period):
    with pytest.raises(ValueError):
        observation_year(period)


@pytest.mark.parametrize('unit,value', [('USD/year', 101420), ('USD/hour', 48.75)])
def test_bls_history_preserves_period_and_source(tmp_path, monkeypatch, unit, value):
    monkeypatch.setattr(store, 'DB_PATH', str(tmp_path / 'history.sqlite'))
    persist([('US', 'nurse', 'national', 'SOC2018:29-1141', 'Registered Nurses',
              'May 2025', 2026, 'USD', 'mean', unit, value, 'BLS OEWS',
              'https://www.bls.gov/oes/tables.htm')])
    result = exact_history('US', 'nurse', 2024, 2025)['observations']
    assert result[0]['status'] == 'unavailable'
    observed = result[1]
    assert observed['year'] == 2025 and observed['status'] == 'available'
    source = observed['source_observations'][0]
    assert source['reference_period'] == 'May 2025'
    assert source['published_year'] == 2026
    assert source['source'] == 'BLS OEWS'
    assert source['source_url'] == 'https://www.bls.gov/oes/tables.htm'
    display = observed['annual_presentation'] if unit.endswith('/year') else observed['reported_hourly']
    assert display['reference_period'] == 'May 2025'
    assert display['source'] == 'BLS OEWS' and display['value'] == value
    assert exact_history('US', 'nurse', 2026, 2026)['observations'][0]['status'] == 'unavailable'
