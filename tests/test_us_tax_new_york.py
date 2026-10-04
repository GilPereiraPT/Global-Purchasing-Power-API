from decimal import Decimal as D
import pytest
from app.us_tax_new_york import calculate,schedule_illustration

# Independently hand-computed inherited schedule cases, not official final returns.
@pytest.mark.parametrize('gross,tax',[
    ('8000','0.00'),('8005','0.20'),('16500','331.50'),
    ('16500.01','332.00'),('19700','472.80'),('19700.01','473.00'),
    ('21900','586.30'),('21900.01','586.00'),
    ('88650','4190.50'),('88650.01','4191.00'),
    ('94750','4550.90'),('107650','5312.00')])
def test_rounded_legal_bases_are_not_reconstructed(gross,tax):
    r=calculate(gross)
    assert r['components'][0]['amount']==tax
    assert r['status']=='partial' and r['income_tax'] is r['net_income'] is None

@pytest.mark.parametrize('gross',['107650.01','200000','1000000','25000000'])
def test_recapture_and_high_income_stay_unavailable(gross):
    assert schedule_illustration(D(gross)) is None
    r=calculate(gross,residence_locality='NYC',work_locality='Yonkers')
    assert all(c['amount'] is None for c in r['components'])
    assert any('recapture' in s for s in r['missing_components'])

@pytest.mark.parametrize('residence,work',[(None,None),('NYC',None),(None,'Yonkers'),('NYC','NYC'),('Yonkers','other'),('other','Yonkers'),('other','other')])
def test_locality_does_not_implicitly_zero_taxes_or_contributions(residence,work):
    r=calculate('100000',residence_locality=residence,work_locality=work)
    assert r['net_income'] is None
    assert all(c['amount'] is None for c in r['components'][1:])

@pytest.mark.parametrize('value',['NaN','Infinity','0','-1','1.001',True,'100000001'])
def test_invalid_money(value):
    with pytest.raises(ValueError):calculate(value)


def test_unsupported_year_scenario_and_locality():
    assert calculate('10000',tax_year=2025)['status']=='unavailable'
    assert calculate('10000',scenario='married')['status']=='unavailable'
    with pytest.raises(ValueError):calculate('10000',tax_year=True)
    with pytest.raises(ValueError):calculate('10000',residence_locality='unknown')
