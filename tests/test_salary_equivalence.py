import pytest
from fastapi.testclient import TestClient
from app import salary_equivalence as eq
from app.main import app
from tests.test_native_wsgi import request


@pytest.fixture
def series(monkeypatch):
    def indicator(country, name, **kwargs):
        if name == 'inflation_annual':
            return {'status': 'available', 'value': 2, 'year': 2024}
        rows = {'PT': [{'year': 2024, 'value': .6}, {'year': 2023, 'value': .5}],
                'US': [{'year': 2023, 'value': 1}], 'ES': []}
        return {'country': country, 'source': 'World Bank', 'source_url': 'https://data.worldbank.org',
                'history': rows.get(country, [])}
    monkeypatch.setattr(eq, 'indicator', indicator)


def test_common_year_and_currency(series):
    result = eq.equivalent('PT', 'US', 30000)
    assert result['year'] == 2023
    assert result['equivalent_annual_gross'] == 60000
    assert result['equivalent_monthly_12'] == 5000
    assert result['currency_b'] == 'USD'
    assert result['net_salary']['value'] is None
    assert result['status'] == 'partial_estimate'


def test_partial_preserves_context_and_never_mixes_years(series):
    result = eq.equivalent('PT', 'US', 30000, 2024)
    assert result['equivalent_annual_gross'] is None
    assert result['context']['PT']['inflation']['value'] == 2
    assert eq.equivalent('PT', 'ES', 30000)['status'] == 'partial'


def test_identity_and_coverage(series):
    assert eq.equivalent('PT', 'PT', 30000)['equivalent_annual_gross'] == 30000
    assert eq.coverage()['countries'][0]['years'] == [2024, 2023]


@pytest.mark.parametrize('amount', [0, -1, float('nan'), float('inf'), True, 100000001])
def test_invalid_amount(series, amount):
    with pytest.raises(ValueError):
        eq.equivalent('PT', 'US', amount)


def test_http_parity(series):
    params = {'country_a': 'PT', 'country_b': 'US', 'annual_gross': 30000}
    response = TestClient(app).get('/v1/earnwage/equivalence', params=params)
    status, body, _ = request('/v1/earnwage/equivalence', params)
    assert status == response.status_code == 200
    assert body == response.json()
    for value in ('nan', 'inf', '-1', '0', '100000001'):
        params['annual_gross'] = value
        assert request('/v1/earnwage/equivalence', params)[0] == 422
        assert TestClient(app).get('/v1/earnwage/equivalence', params=params).status_code == 422
