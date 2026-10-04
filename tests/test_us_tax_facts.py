import json
from decimal import Decimal as D
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.tax_engine import calculate, present, TaxRequest, TaxOutcome
from app.tax_us import SCENARIO
from tests.test_portugal_benchmark_2025 import wsgi


def result(facts):
    return calculate('US', '100000', 2026, SCENARIO, 'TX', us_facts=facts)


def test_explicit_bases_and_zero_do_not_validate_net():
    r = result({'federal_wages':'90000', 'social_security_wages':'0',
                'medicare_wages':'80000', 'age':40, 'blind':False,
                'valid_ssn':True, 'can_be_claimed_as_dependent':False,
                'qualified_tips':'0', 'qualified_overtime':'0'})
    parts = {p['name']:p['amount'] for p in r['components']}
    assert parts['employee_social_security_candidate'] == '0.00'
    assert parts['employee_medicare_candidate'] == '1160.00'
    assert parts['taxable_income_before_credits'] == '73900.00'
    assert r['us_facts']['social_security_wages'] == '0.00'
    assert r['status'] == 'partial' and r['net_income'] is None
    assert 'us_facts' not in calculate('US','100000',2026,SCENARIO,'TX')
    assert result({})['us_facts'] == {}


@pytest.mark.parametrize('facts',[
    '[]', '{"age":20,"age":30}', '{', ' ' * 2049,
    {'ssn':'123'}, {'valid_ssn':'yes'}, {'age':True}, {'age':121},
    {'age':-1}, {'federal_wages':100}, {'federal_wages':'NaN'},
    {'federal_wages':'Infinity'}, {'medicare_wages':'100000.01'},
    {'qualified_tips':'0.001'}, {'blind':None},
])
def test_invalid_facts(facts):
    with pytest.raises(ValueError): result(facts)


def test_non_us_facts_rejected():
    with pytest.raises(ValueError):
        calculate('PT','20000',2025,'single_employee_no_dependents','mainland',us_facts={})


@pytest.mark.parametrize('facts',[{'age':40,'valid_ssn':True}, {'social_security_wages':'0'}, {'ssn':'123'}])
def test_facts_asgi_wsgi_parity(facts):
    params = dict(country='US',annual_gross='100000',tax_year='2026',scenario=SCENARIO,
                  region='TX',us_facts=json.dumps(facts))
    with TestClient(app) as client:
        response = client.get('/v1/tax/calculate',params=params)
    status, body = wsgi('/v1/tax/calculate',params)
    assert response.status_code == status
    if status == 200:
        assert response.json() == body and body['net_income'] is None
    else:
        assert status == 422


SOURCE = dict(url='https://www.irs.gov/example',tax_year=2026,
              verification_status='verified',scope='Test metadata only')

@pytest.mark.parametrize('change',[
    {'verification_status':'blocked'}, {'verification_status':None},
    {'tax_year':2025}, {'tax_year':True}, {'scope':''},
    {'url':'http://www.irs.gov/example'}, {'url':'https://secret:password@www.irs.gov'},
    {'url':'https://['},
])
def test_incomplete_source_cannot_authorize_net(change):
    request = TaxRequest('US',2026,D('1000'),SCENARIO,'TX')
    outcome = TaxOutcome('benchmark_estimate',D('10'),D('20'),
                         sources=({**SOURCE,**change},),applicable_rules=('test',))
    r = present(request,outcome,'USD')
    assert r['status'] == 'partial' and r['net_income'] is None


def test_declared_complete_evidence_and_mixed_sources():
    request = TaxRequest('US',2026,D('1000'),SCENARIO,'TX')
    outcome = TaxOutcome('benchmark_estimate',D('10'),D('20'),
                         sources=(SOURCE,),applicable_rules=('test',))
    assert present(request,outcome,'USD')['net_income'] == '970.00'
    mixed = TaxOutcome('verified',D('10'),D('20'),sources=(SOURCE,{}),applicable_rules=('test',))
    assert present(request,mixed,'USD')['net_income'] is None
