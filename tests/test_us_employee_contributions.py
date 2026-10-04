"""Statutory employee non-chargeback reference cases; not full-net references."""
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.tax_engine import calculate, metadata
from app.us_federal_benchmark import SCENARIO
from app.us_tax_jurisdictions import coverage
from tests.test_us_federal_benchmark import facts
from tests.test_portugal_benchmark_2025 import wsgi


def employee_facts(gross):
    return dict(facts(gross), employment_type='ordinary_private_employee',
                workers_compensation_exception_agreement=False)


@pytest.mark.parametrize('state', ['TX','FL'])
@pytest.mark.parametrize('gross', ['19540','100000','184500','200001','500000'])
def test_statutory_non_chargeback_employee_reference_cases(state,gross):
    # TX 204.003/415.006 and FL 443.041/440.21 prohibit these employee charges;
    # the expected zero follows the independently reviewed statute, not a rate.
    r=calculate('US',gross,2026,SCENARIO,state,us_facts=employee_facts(gross))
    c={v['name']:v['amount'] for v in r['components']}
    assert c['employee_workers_compensation_contribution']=='0.00'
    assert c['employee_unemployment_contribution' if state=='TX' else 'employee_reemployment_contribution']=='0.00'
    assert c['employee_paid_leave_contribution'] is c['local_income_tax'] is c['mandatory_state_employee_contributions'] is None
    assert r['status']=='partial' and r['net_income'] is r['income_tax'] is None


@pytest.mark.parametrize('state', ['TX','FL'])
@pytest.mark.parametrize('omitted', ['employment_type','workers_compensation_exception_agreement'])
def test_missing_employee_fact_is_not_implied_by_federal_model(state,omitted):
    f=employee_facts('100000');del f[omitted]
    r=calculate('US','100000',2026,SCENARIO,state,us_facts=f)
    c={v['name']:v['amount'] for v in r['components']}
    assert c['employee_workers_compensation_contribution'] is None
    assert r['net_income'] is None


@pytest.mark.parametrize('state', ['TX','FL'])
@pytest.mark.parametrize('kind', ['independent_contractor','subcontractor','owner_operator','public_employee','special_regime'])
def test_excluded_categories_never_receive_employee_zeroes(state,kind):
    f=dict(employee_facts('100000'),employment_type=kind)
    direct=coverage(state,f)
    assert next(c['amount'] for c in direct['components'] if c['name']=='employee_workers_compensation_contribution') is None
    r=calculate('US','100000',2026,SCENARIO,state,us_facts=f)
    assert r['status']=='partial' and r['net_income'] is None
    assert all(c['amount'] is None for c in r['components'])


@pytest.mark.parametrize('state', ['TX','FL'])
def test_coverage_agreement_exception_never_defaults_to_zero(state):
    f=dict(employee_facts('100000'),workers_compensation_exception_agreement=True)
    assert next(c['amount'] for c in coverage(state,f)['components'] if c['name']=='employee_workers_compensation_contribution') is None
    r=calculate('US','100000',2026,SCENARIO,state,us_facts=f)
    assert all(c['amount'] is None for c in r['components'])
    assert any('agreement' in s for s in r['limitations'])


@pytest.mark.parametrize('invalid', [None,'employee',False,[],{}])
def test_employment_type_strict_input(invalid):
    with pytest.raises(ValueError):
        calculate('US','100000',2026,SCENARIO,'TX',us_facts=dict(employee_facts('100000'),employment_type=invalid))


@pytest.mark.parametrize('invalid', [None,'false',0,1,[]])
def test_exception_declaration_requires_boolean(invalid):
    with pytest.raises(ValueError):
        calculate('US','100000',2026,SCENARIO,'TX',us_facts=dict(employee_facts('100000'),workers_compensation_exception_agreement=invalid))


@pytest.mark.parametrize('state', ['TX','FL'])
def test_http_parity_for_conditional_employee_contribution_rules(state):
    params=dict(country='US',annual_gross='100000',tax_year='2026',scenario=SCENARIO,region=state,
                us_facts=json.dumps(employee_facts('100000')))
    with TestClient(app) as client:r=client.get('/v1/tax/calculate',params=params)
    code,body=wsgi('/v1/tax/calculate',params)
    assert code==r.status_code==200 and body==r.json()
    assert body['net_income'] is None


def test_sources_and_required_facts_are_available_in_metadata():
    model=next(s for s in metadata('US')['scenarios'] if s['id']==SCENARIO)
    for jurisdiction in model['jurisdiction_coverage']:
        assert jurisdiction['required_employee_contribution_facts']==['employment_type','workers_compensation_exception_agreement']
        assert all(c['amount'] is None for c in jurisdiction['components'] if c['name']=='employee_workers_compensation_contribution')
        if jurisdiction['state']=='TX':
            assert any('302 is NOT' in rule for rule in jurisdiction['missing_rules'])
    tx=coverage('TX',employee_facts('100000'))
    assert any(s['url'].endswith('/LA.406.htm') and '406.123/406.144' in s['scope'] for s in tx['sources'])
    assert all('TX.302.htm' not in s['url'] for s in tx['sources'])


@pytest.mark.parametrize('state', ['TX','FL'])
def test_explicit_employee_facts_cannot_replace_official_rule_evidence(monkeypatch,state):
    from app.us_tax_evidence import sources_for
    def no_review(urls):
        return tuple(dict(s,verification_status='blocked') for s in sources_for(urls))
    monkeypatch.setattr('app.us_tax_jurisdictions.sources_for',no_review)
    result=coverage(state,employee_facts('100000'))
    assert all(c['amount'] is None for c in result['components'])
    r=calculate('US','100000',2026,SCENARIO,state,us_facts=employee_facts('100000'))
    assert r['net_income'] is None and r['status']=='partial'
