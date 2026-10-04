from decimal import Decimal as D
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.tax_engine import calculate, metadata
from app.tax_us import SCENARIO, illustrations
from tests.test_portugal_benchmark_2025 import wsgi

# Hand-derived checks of the inherited illustration, NOT validated IRS returns.
@pytest.mark.parametrize('gross,tax,ss,med,additional',[
    ('16100','0.00','998.20','233.45','0.00'),
    ('28500','1240.00','1767.00','413.25','0.00'),
    ('66500','5800.00','4123.00','964.25','0.00'),
    ('100000','13170.00','6200.00','1450.00','0.00'),
    ('250000','51304.00','11439.00','3625.00','450.00'),
])
def test_independent_arithmetic_not_mislabelled_as_verified(gross,tax,ss,med,additional):
    r=calculate('US',gross,2026,SCENARIO,'TX');values={v['name']:v['amount'] for v in r['components']}
    assert values['federal_schedule_before_credits']==tax
    assert values['employee_social_security_candidate']==ss
    assert values['employee_medicare_candidate']==med
    assert values['employee_additional_medicare_candidate']==additional
    assert r['status']=='partial' and r['net_income'] is None
    assert r['income_tax'] is None and r['employee_social_security'] is None
    assert all(isinstance(v['amount'],str) for v in r['components'] if v['amount'] is not None)

@pytest.mark.parametrize('ceiling,rate', [('12400','.12'),('50400','.22'),('105700','.24'),('201775','.32'),('256225','.35'),('640600','.37')])
def test_all_bracket_boundaries(ceiling,rate):
    base=D(ceiling)+D('16100')
    tax=dict(illustrations(base))['federal_schedule_before_credits']
    assert dict(illustrations(base+D('.01')))['federal_schedule_before_credits']-tax==D('.01')*D(rate)


def test_contribution_caps_and_additional_threshold():
    assert dict(illustrations(D('184500')))['employee_social_security_candidate']==D('11439')
    assert dict(illustrations(D('184500.01')))['employee_social_security_candidate']==D('11439')
    assert dict(illustrations(D('200000')))['employee_additional_medicare_candidate']==0
    assert dict(illustrations(D('200000.01')))['employee_additional_medicare_candidate']==D('.00009')

@pytest.mark.parametrize('region',[None,'TX','FL','NY','CA','PA'])
def test_regions_cannot_enable_unjustified_net(region):
    r=calculate('US','100000',2026,SCENARIO,region)
    assert r['status']=='partial' and r['monthly_equivalent_12'] is None
    assert metadata('US')['benchmark_tax_years']==[]

@pytest.mark.parametrize('gross',['0','-1','NaN','Infinity','12.001',True,'100000001'])
def test_invalid_input(gross):
    with pytest.raises(ValueError):calculate('US',gross,2026,SCENARIO,'TX')


def test_unsupported_scenarios_years_and_inapplicable_inputs():
    assert calculate('US','10000',2025,SCENARIO,'TX')['status']=='unavailable'
    assert calculate('US','10000',2026,'married','TX')['status']=='unavailable'
    with pytest.raises(ValueError):calculate('US','10000',2026,SCENARIO,'ZZ')
    with pytest.raises(ValueError):calculate('US','10000',2026,SCENARIO,'TX','0')

@pytest.mark.parametrize('region',[None,'TX','FL'])
def test_asgi_wsgi_parity(region):
    params=dict(country='US',annual_gross='100000',tax_year='2026',scenario=SCENARIO)
    if region:params['region']=region
    with TestClient(app) as client:
        response=client.get('/v1/tax/calculate',params=params)
    status,result=wsgi('/v1/tax/calculate',params)
    assert response.status_code==status==200 and response.json()==result
    assert result['net_income'] is None
