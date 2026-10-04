import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.tax_engine import calculate, metadata
from app.us_federal_benchmark import SCENARIO, REQUIRED
from tests.test_portugal_benchmark_2025 import wsgi


def facts(gross):
    return dict(age=40, blind=False, valid_ssn=True, can_be_claimed_as_dependent=False,
                federal_wages=gross, social_security_wages=gross, medicare_wages=gross,
                qualified_tips='0', qualified_overtime='0',
                nonitemizer_charitable_contributions='0', ordinary_wage_model_confirmed=True)


@pytest.mark.parametrize('gross,tax,fica,residual', [
    ('19540','344.00','1494.81','17701.19'),
    ('100000','13170.00','7650.00','79180.00'),
    ('250000','51304.00','15514.00','183182.00'),
    ('500000','138134.25','21389.00','340476.75'),
])
@pytest.mark.parametrize('state', ['TX','FL'])
def test_scoped_federal_results_and_total_net_withheld(gross,tax,fica,residual,state):
    r = calculate('US', gross, 2026, SCENARIO, state, us_facts=facts(gross))
    c = {v['name']:v['amount'] for v in r['components']}
    assert c['federal_income_tax_model'] == tax
    assert c['federal_contributions_model'] == fica
    assert c['income_after_federal_components_before_state_local_and_other_deductions'] == residual
    assert c['federal_childless_eitc_model'] == c['federal_additional_amt_model'] == '0.00'
    assert c['state_income_tax_final'] == '0.00'
    assert c['local_income_tax'] is c['mandatory_state_employee_contributions'] is None
    assert r['status'] == 'partial' and r['net_income'] is r['income_tax'] is None


@pytest.mark.parametrize('key', REQUIRED)
def test_omitted_fact_never_becomes_zero_or_model_consent(key):
    f = facts('100000'); del f[key]
    r = calculate('US','100000',2026,SCENARIO,'TX',us_facts=f)
    assert all(c['amount'] is None for c in r['components'])
    assert any(key in s for s in r['limitations'])


@pytest.mark.parametrize('change', [
    {'age':24}, {'age':65}, {'blind':True}, {'valid_ssn':False},
    {'can_be_claimed_as_dependent':True}, {'ordinary_wage_model_confirmed':False},
    {'qualified_tips':'1'}, {'qualified_overtime':'1'},
    {'nonitemizer_charitable_contributions':'1'}, {'social_security_wages':'90000'},
    {'federal_wages':'90000'}, {'medicare_wages':'90000'},
])
def test_special_eligibility_and_distinct_bases_not_silently_projected(change):
    r = calculate('US','100000',2026,SCENARIO,'FL',us_facts={**facts('100000'),**change})
    assert all(c['amount'] is None for c in r['components'])


@pytest.mark.parametrize('gross', ['19539.99','500000.01'])
def test_refundable_credit_and_amt_phaseout_range_remain_unavailable(gross):
    r = calculate('US',gross,2026,SCENARIO,'TX',us_facts=facts(gross))
    assert all(c['amount'] is None for c in r['components'])


def test_amt_standard_deduction_addback_and_2026_threshold():
    r = calculate('US','334600',2026,SCENARIO,'TX',us_facts=facts('334600'))
    c = {v['name']:v['amount'] for v in r['components']}
    assert c['federal_amti_model'] == '334600.00'
    assert c['federal_tentative_minimum_tax_model'] == '63570.00'
    r = calculate('US','334600.01',2026,SCENARIO,'TX',us_facts=facts('334600.01'))
    assert r['net_income'] is None


@pytest.mark.parametrize('state', [None,'NY','CA','PA'])
def test_other_regions_do_not_enable_first_model(state):
    r = calculate('US','100000',2026,SCENARIO,state,us_facts=facts('100000'))
    assert r['net_income'] is None and not r.get('components')


def test_http_parity_and_model_metadata():
    import json
    params = dict(country='US',annual_gross='100000',tax_year='2026',scenario=SCENARIO,
                  region='TX',us_facts=json.dumps(facts('100000')))
    with TestClient(app) as client: response = client.get('/v1/tax/calculate',params=params)
    code, body = wsgi('/v1/tax/calculate',params)
    assert response.status_code == code == 200 and response.json() == body
    model = next(x for x in metadata('US')['scenarios'] if x['id']==SCENARIO)
    assert model['required_us_facts'] == list(REQUIRED)
    assert metadata('US')['benchmark_tax_years'] == []


@pytest.mark.parametrize('change', [
    {'ordinary_wage_model_confirmed':'true'}, {'nonitemizer_charitable_contributions':0},
    {'nonitemizer_charitable_contributions':'NaN'}, {'nonitemizer_charitable_contributions':'0.001'},
])
def test_new_facts_remain_strict(change):
    with pytest.raises(ValueError):
        calculate('US','100000',2026,SCENARIO,'TX',us_facts={**facts('100000'),**change})
