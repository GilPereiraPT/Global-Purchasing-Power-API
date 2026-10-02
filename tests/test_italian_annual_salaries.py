import pytest
from fastapi.testclient import TestClient

from app.earnwage_queries import annual_presentation
from app.it_istat_wages import INITIAL_RAL, occupation_wage
from app.main import app


@pytest.mark.parametrize('occupation', sorted(INITIAL_RAL))
def test_italian_annual_salary_preserves_source_and_ranges(occupation):
    wage = occupation_wage(occupation)
    result = annual_presentation(wage, {})
    assert result['status'] == 'available' and result['unit'] == 'per_year'
    assert result['kind'] == 'reported_annual'
    assert result['reference_period'] == wage['period']
    for key in ('currency', 'source', 'source_url', 'measure', 'precision'):
        assert result[key] == wage[key]
    assert result['payments_per_year'] is None and result['payments_verified'] is False
    if wage.get('value_type') == 'range':
        assert result['value_type'] == 'range'
        assert result['value'] is None and result['monthly_optional'] is None
        assert result['min_value'] == wage['min_value']
        assert result['max_value'] == wage['max_value']
    else:
        assert result['value'] == wage['value']
        assert result['monthly_optional'] == wage['value'] / 12


def test_italian_overview_exposes_annual_scalar_and_range():
    with TestClient(app) as client:
        scalar = client.get('/v1/earnwage/overview', params={'country': 'IT', 'occupation': 'lawyer'})
        assert scalar.status_code == 200
        assert scalar.json()['annual_presentation']['value'] == 46800
        ranged = client.get('/v1/earnwage/overview', params={'country': 'IT', 'occupation': 'cook'})
        assert ranged.status_code == 200
        data = ranged.json()
        assert data['national_occupation_wage']['value_type'] == 'range'
        assert data['annual_presentation']['value'] is None
        assert (data['annual_presentation']['min_value'], data['annual_presentation']['max_value']) == (24500, 25000)
