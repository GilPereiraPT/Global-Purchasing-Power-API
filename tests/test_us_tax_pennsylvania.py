import pytest
from app.us_tax_pennsylvania import calculate

# Manual pre-credit products; not independently verified final PA assessments.
@pytest.mark.parametrize('gross,compensation,tax',[
    ('100000','100000','3070.00'),('100000','90000','2763.00'),
    ('100','5','0.15'),('100','0','0.00'),('6500','6500','199.55'),
    ('9000','9000','276.30')])
def test_explicit_compensation_not_gross_and_output_precision(gross,compensation,tax):
    r=calculate(gross,taxable_compensation=compensation)
    assert r['components'][0]['amount']==tax
    assert r['income_tax'] is r['employee_contributions'] is r['net_income'] is None
    assert r['status']=='partial'

@pytest.mark.parametrize('gross',['1','6500','6500.01','9000','9000.01','1000000'])
def test_low_and_high_income_do_not_invent_forgiveness_or_eitc(gross):
    r=calculate(gross)
    assert r['taxable_compensation'] is None
    assert all(c['amount'] is None for c in r['components'])
    assert any('EITC' in m for m in r['missing_components'])

@pytest.mark.parametrize('home,work',[(None,None),('510101',None),(None,'510101'),('510101','510101'),('010101','010101')])
def test_local_and_unemployment_not_implicitly_zero(home,work):
    r=calculate('100000',taxable_compensation='100000',residence_psd=home,work_psd=work,
                forgiveness_eligibility_income='100000',federal_eitc='0')
    assert all(c['amount'] is None for c in r['components'][1:])
    assert r['net_income'] is None

@pytest.mark.parametrize('value',[True,'NaN','Infinity','-1','0.001','100000001'])
def test_invalid_taxable_compensation(value):
    with pytest.raises(ValueError):calculate('100000',taxable_compensation=value)


def test_invalid_gross_year_psd_and_unsupported_scenario():
    for value in ('0','NaN','1.001',True):
        with pytest.raises(ValueError):calculate(value)
    with pytest.raises(ValueError):calculate('1000',taxable_compensation='1001')
    with pytest.raises(ValueError):calculate('1000',residence_psd='Philadelphia')
    with pytest.raises(ValueError):calculate('1000',tax_year=True)
    assert calculate('1000',tax_year=2025)['status']=='unavailable'
    assert calculate('1000',scenario='married')['status']=='unavailable'


def test_missing_credits_are_distinct_from_explicit_zero():
    missing=calculate('1000');explicit=calculate('1000',taxable_compensation='0',
        forgiveness_eligibility_income='0',federal_eitc='0')
    assert missing['federal_eitc'] is None and explicit['federal_eitc']=='0.00'
    assert explicit['net_income'] is None  # Supplied facts do not validate missing legal rules.
