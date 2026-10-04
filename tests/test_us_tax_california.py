import pytest
from decimal import Decimal as D
from app.us_tax_california import calculate,sdi_illustration

# Independent decimal products of the inherited 1.3% candidate, not EDD payslips.
@pytest.mark.parametrize('gross,result',[
    ('5','0.07'),('4.99','0.06'),('5.01','0.07'),
    ('100000','1300.00'),('200000','2600.00'),('1000000','13000.00')])
def test_sdi_rounding_and_no_invented_cap(gross,result):
    r=calculate(gross)
    assert r['components'][0]['amount']==result
    assert r['status']=='partial' and r['employee_contributions'] is None
    assert r['income_tax'] is r['net_income'] is None
    assert isinstance(r['components'][0]['amount'],str)
    assert sdi_illustration(D(gross))==D(gross)*D('.013')

@pytest.mark.parametrize('gross',['1','10000','50000','999999.99','1000000','1000000.01','100000000'])
def test_unverified_brackets_exemptions_and_high_income_tax_are_not_zero(gross):
    r=calculate(gross)
    assert all(c['amount'] is None for c in r['components'][1:])
    assert r['net_income'] is None

@pytest.mark.parametrize('value',[True,'NaN','Infinity','0','-1','0.001','100000001'])
def test_invalid_inputs(value):
    with pytest.raises(ValueError):calculate(value)


def test_no_2025_rules_relabelled_as_2026_and_no_other_household():
    for r in (calculate('100000',2025),calculate('100000',scenario='married')):
        assert r['status']=='unavailable'
        assert all(c['amount'] is None for c in r['components'])
    with pytest.raises(ValueError):calculate('100000',tax_year=True)
