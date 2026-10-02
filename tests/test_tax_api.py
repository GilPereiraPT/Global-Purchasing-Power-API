"""Same annual-tax contract in FastAPI and production WSGI."""
import io
import json
from decimal import Decimal
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.native_wsgi import application
from app import tax_engine
from app.tax_engine import TaxOutcome
from app.tax_portugal import SCENARIO


def wsgi(path, params):
    status = []
    raw = b''.join(application({'PATH_INFO': path, 'REQUEST_METHOD': 'GET',
        'QUERY_STRING': urlencode(params), 'wsgi.input': io.BytesIO(b'')},
        lambda code, headers: status.append(int(code.split()[0]))))
    return status[0], json.loads(raw)


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


PARAMS = {'country': 'PT', 'annual_gross': '30000.01', 'tax_year': '2025',
          'scenario': SCENARIO, 'region': 'mainland'}


@pytest.mark.parametrize('path,params', [
    ('/v1/tax/countries', {}), ('/v1/tax/years/PT', {}),
    ('/v1/tax/assumptions/PT', {}), ('/v1/tax/years/US', {}),
    ('/v1/tax/calculate', PARAMS),
    ('/v1/tax/calculate', {**PARAMS, 'scenario': 'married'}),
    ('/v1/tax/calculate', {**PARAMS, 'country': 'US'}),
    ('/v1/tax/calculate', {**PARAMS, 'region': 'madeira'}),
    ('/v1/tax/calculate', {**PARAMS, 'tax_year': '2026'}),
])
def test_successful_responses_match(client, path, params):
    response = client.get(path, params=params)
    code, body = wsgi(path, params)
    assert response.status_code == code == 200
    assert response.json() == body


@pytest.mark.parametrize('changed', [
    {'tax_year': ''}, {'scenario': ''}, {'annual_gross': 'NaN'},
    {'annual_gross': 'Infinity'}, {'annual_gross': '0.001'},
    {'annual_gross': '-1'}, {'annual_gross': '100000001'},
    {'tax_year': '2025.0'}, {'tax_year': '2101'}, {'country': 'Portugal'},
    {'dependents': '2'}, {'annual_gross': '1e-999999'},
])
def test_invalid_inputs_rejected_in_both_runtimes(client, changed):
    params = {**PARAMS, **changed}
    assert client.get('/v1/tax/calculate', params=params).status_code == 422
    assert wsgi('/v1/tax/calculate', params)[0] == 422


@pytest.mark.parametrize('omitted', ['country', 'annual_gross', 'tax_year', 'scenario'])
def test_required_inputs_are_explicit(client, omitted):
    params = {key: value for key, value in PARAMS.items() if key != omitted}
    assert client.get('/v1/tax/calculate', params=params).status_code == 422
    assert wsgi('/v1/tax/calculate', params)[0] == 422


def test_duplicate_parameters_rejected(client):
    params = list(PARAMS.items()) + [('tax_year', '2026')]
    assert client.get('/v1/tax/calculate', params=params).status_code == 422
    assert wsgi('/v1/tax/calculate', params)[0] == 422


def test_overview_explicit_scenario_has_parity_and_keeps_ppp_unavailable(client):
    params = {'country': 'PT', 'occupation': 'nurse', 'annual_gross': '30000.01',
              'tax_scenario': SCENARIO, 'tax_region': 'mainland', 'net_tax_year': 2025}
    response = client.get('/v1/earnwage/overview', params=params)
    code, body = wsgi('/v1/earnwage/overview', params)
    assert response.status_code == code == 200 and response.json() == body
    assert body['tax_scenario']['status'] == 'partial'
    assert body['tax_scenario']['net_income'] is None
    assert body['net_purchasing_power']['value'] is None
    params.pop('net_tax_year')
    assert client.get('/v1/earnwage/overview', params=params).status_code == 422
    assert wsgi('/v1/earnwage/overview', params)[0] == 422


def test_comparison_independently_selected_scenarios(client):
    params = {'country_a': 'PT', 'country_b': 'PT', 'occupation': 'nurse',
              'annual_gross_a': '30000', 'annual_gross_b': '40000',
              'tax_scenario_a': SCENARIO, 'tax_scenario_b': SCENARIO,
              'tax_region_a': 'mainland', 'tax_region_b': 'azores',
              'net_tax_year_a': 2025, 'net_tax_year_b': 2026}
    response = client.get('/v1/earnwage/compare', params=params)
    code, body = wsgi('/v1/earnwage/compare', params)
    assert response.status_code == code == 200 and response.json() == body
    assert body['country_a']['tax_scenario']['tax_year'] == 2025
    assert body['country_b']['tax_scenario']['tax_year'] == 2026
    assert body['net_purchasing_power']['value'] is None


def test_verified_synthetic_adapter_can_flow_to_overview_without_net_ppp(client, monkeypatch):
    """Integration plumbing only: no Portuguese fiscal rates in this fixture."""
    class SyntheticAdapter:
        def metadata(self):
            return {'country': 'PT', 'currency': 'TEST', 'status': 'verified',
                    'supported_tax_years': [2025], 'scenarios': []}
        def calculate(self, request):
            return TaxOutcome('verified', Decimal('123.45'), Decimal('67.89'),
                              sources=({'url': 'https://example.invalid/test-only'},),
                              applicable_rules=('Synthetic integration fixture',))
    monkeypatch.setattr(tax_engine, '_adapters', lambda: {'PT': SyntheticAdapter()})
    params = {'country': 'PT', 'occupation': 'nurse', 'annual_gross': '30000.01',
              'tax_scenario': 'synthetic', 'tax_region': 'mainland', 'net_tax_year': 2025}
    response = client.get('/v1/earnwage/overview', params=params)
    code, body = wsgi('/v1/earnwage/overview', params)
    assert response.status_code == code == 200 and response.json() == body
    assert body['tax_scenario']['net_income'] == '29808.67'
    assert body['net_purchasing_power']['value'] is None


@pytest.mark.parametrize('expenses,expected', [('0.00', '0.00'), ('100', '35.00'),
                                             ('1000', '250.00'), ('714.28', '250.00')])
def test_explicit_household_expenses_match_in_both_runtimes(client, expenses, expected):
    params = {**PARAMS, 'eligible_household_expenses': expenses}
    response = client.get('/v1/tax/calculate', params=params)
    code, body = wsgi('/v1/tax/calculate', params)
    assert response.status_code == code == 200 and response.json() == body
    credit = next(item for item in body['components'] if item['id'] == 'general_expense_credit')
    assert credit['value'] == expected
    assert body['net_income'] is None


@pytest.mark.parametrize('expenses', ['NaN', 'Infinity', '-1', '0.001', '', '100000001'])
def test_invalid_household_expenses_rejected_in_both_runtimes(client, expenses):
    params = {**PARAMS, 'eligible_household_expenses': expenses}
    assert client.get('/v1/tax/calculate', params=params).status_code == 422
    assert wsgi('/v1/tax/calculate', params)[0] == 422


def test_duplicate_expenses_rejected_in_calculation(client):
    params = list(PARAMS.items()) + [('eligible_household_expenses', '0'),
                                   ('eligible_household_expenses', '1000')]
    assert client.get('/v1/tax/calculate', params=params).status_code == 422
    assert wsgi('/v1/tax/calculate', params)[0] == 422


def test_expenses_flow_through_overview_and_independent_comparison(client):
    params = {'country': 'PT', 'occupation': 'nurse', 'annual_gross': '25000',
              'tax_scenario': SCENARIO, 'tax_region': 'mainland', 'net_tax_year': 2025,
              'eligible_household_expenses': '1000'}
    response = client.get('/v1/earnwage/overview', params=params)
    code, body = wsgi('/v1/earnwage/overview', params)
    assert response.status_code == code == 200 and response.json() == body
    assert body['tax_scenario']['eligible_household_expenses'] == '1000.00'
    assert body['tax_scenario']['net_income'] is None
    comparison = {'country_a': 'PT', 'country_b': 'PT', 'occupation': 'nurse',
                  'annual_gross_a': '25000', 'annual_gross_b': '25000',
                  'tax_scenario_a': SCENARIO, 'tax_scenario_b': SCENARIO,
                  'tax_region_a': 'mainland', 'tax_region_b': 'mainland',
                  'net_tax_year_a': 2025, 'net_tax_year_b': 2025,
                  'eligible_household_expenses_a': '0', 'eligible_household_expenses_b': '1000'}
    response = client.get('/v1/earnwage/compare', params=comparison)
    code, body = wsgi('/v1/earnwage/compare', comparison)
    assert response.status_code == code == 200 and response.json() == body
    assert body['country_a']['tax_scenario']['eligible_household_expenses'] == '0.00'
    assert body['country_b']['tax_scenario']['eligible_household_expenses'] == '1000.00'


def test_expenses_cannot_be_silently_ignored_by_legacy_overview(client):
    params = {'country': 'PT', 'occupation': 'nurse', 'eligible_household_expenses': '100'}
    assert client.get('/v1/earnwage/overview', params=params).status_code == 422
    assert wsgi('/v1/earnwage/overview', params)[0] == 422


def test_disability_does_not_select_a_reduced_employee_rate(client):
    params = {**PARAMS, 'disability': 'true'}
    assert client.get('/v1/tax/calculate', params=params).status_code == 422
    assert wsgi('/v1/tax/calculate', params)[0] == 422


@pytest.mark.parametrize('path,params,name', [
    ('/v1/earnwage/overview', {'country': 'PT', 'occupation': 'nurse'}, 'eligible_household_expenses'),
    ('/v1/earnwage/compare', {'country_a': 'PT', 'country_b': 'PT', 'occupation': 'nurse'}, 'eligible_household_expenses_a'),
    ('/v1/earnwage/compare', {'country_a': 'PT', 'country_b': 'PT', 'occupation': 'nurse'}, 'eligible_household_expenses_b'),
])
def test_duplicate_expenses_rejected_in_overview_and_comparison(client, path, params, name):
    repeated = list(params.items()) + [(name, '0'), (name, '1000')]
    assert client.get(path, params=repeated).status_code == 422
    assert wsgi(path, repeated)[0] == 422
