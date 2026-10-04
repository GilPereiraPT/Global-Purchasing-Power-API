"""Private policy standards never become an employee public payroll levy."""
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.tax_engine import calculate,metadata
from app.us_tax_jurisdictions import coverage,PRIVATE_INSURANCE_RULES
from app.us_federal_benchmark import SCENARIO
from tests.test_us_employee_contributions import employee_facts
from tests.test_portugal_benchmark_2025 import wsgi


@pytest.mark.parametrize('state',['TX','FL'])
def test_private_insurance_rules_are_scoped_and_never_quantify_public_levy(state):
    row=coverage(state,employee_facts('100000'))
    private=row['private_family_leave_insurance']
    assert private['status']=='reviewed_private_insurance_rules'
    assert private['kind']=='private_employer_group_insurance'
    assert private['these_rules_create_universal_public_employee_contribution'] is False
    assert private['premium_amount'] is None
    assert private['public_contribution_applicability']=='not_established_by_these_documents'
    assert 'not an assertion that premiums cost zero' in private['benchmark_treatment']
    result=calculate('US','100000',2026,SCENARIO,state,us_facts=employee_facts('100000'))
    c={x['name']:x['amount'] for x in result['components']}
    assert c['employee_paid_leave_contribution'] is c['local_income_tax'] is c['mandatory_state_employee_contributions'] is None
    assert result['net_income'] is None and result['status']=='partial'
    assert any('not establish existence or absence' in s for s in result['limitations'])


@pytest.mark.parametrize('state',['TX','FL'])
@pytest.mark.parametrize('failure',['blocked','missing_source'])
def test_failed_or_incomplete_insurance_review_never_establishes_kind_of_levy(monkeypatch,state,failure):
    from app.us_tax_evidence import sources_for
    def faulty(urls):
        original=sources_for(urls)
        if tuple(urls)==PRIVATE_INSURANCE_RULES[state]:
            if failure=='missing_source': return original[:1]
            return tuple(dict(r,verification_status='blocked') for r in original)
        return original
    monkeypatch.setattr('app.us_tax_jurisdictions.sources_for',faulty)
    private=coverage(state)['private_family_leave_insurance']
    assert private['status']=='unavailable'
    assert private['these_rules_create_universal_public_employee_contribution'] is None
    assert private['premium_amount'] is None


def test_environmental_effective_date_is_no_longer_a_document_request_or_tax_rule():
    row=coverage('FL',employee_facts('100000'))
    assert any('environmental amendment effective 2026-07-01' in rule for rule in row['missing_rules'])
    assert not any('effective date requires' in rule for rule in row['missing_rules'])
    assert all('1217' not in s['url'] for s in row['sources'])
    assert next(c['amount'] for c in row['components'] if c['name']=='local_income_tax') is None


@pytest.mark.parametrize('state',['TX','FL'])
def test_metadata_and_http_parity_preserve_private_public_distinction(state):
    model=next(s for s in metadata('US')['scenarios'] if s['id']==SCENARIO)
    row=next(r for r in model['jurisdiction_coverage'] if r['state']==state)
    assert row['private_family_leave_insurance']['premium_amount'] is None
    params=dict(country='US',annual_gross='100000',tax_year='2026',scenario=SCENARIO,region=state,
                us_facts=json.dumps(employee_facts('100000')))
    with TestClient(app) as client:r=client.get('/v1/tax/calculate',params=params)
    code,body=wsgi('/v1/tax/calculate',params)
    assert code==r.status_code==200 and body==r.json()
    assert body['net_income'] is None
