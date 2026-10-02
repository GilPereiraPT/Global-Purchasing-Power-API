"""Synthetic arithmetic fixtures are NOT Portuguese fiscal rules."""
from decimal import Decimal as D

import pytest

from app.tax_engine import (TaxOutcome, TaxRequest, annual_amount, calculate,
                            countries, monetary, present, progressive_tax, years)
from app.tax_portugal import SCENARIO

BRACKETS = ((D('10000'), D('.10')), (D('20000'), D('.20')), (None, D('.30')))


@pytest.mark.parametrize('gross,expected', [
    ('0', '0'), ('9999.99', '999.999'), ('10000', '1000'),
    ('10000.01', '1000.002'), ('19999.99', '2999.998'),
    ('20000', '3000'), ('20000.01', '3000.003'), ('30000', '6000'),
])
def test_synthetic_progressive_bracket_boundaries(gross, expected):
    assert progressive_tax(D(gross), BRACKETS) == D(expected)


@pytest.mark.parametrize('brackets', [(), ((D('100'), D('.1')),),
    ((None, D('.1')), (None, D('.2'))),
    ((D('100'), D('.1')), (D('99'), D('.2')), (None, D('.3'))),
    ((None, D('NaN')),), ((None, D('1.01')),), ((None, .1),)])
def test_invalid_brackets_are_rejected(brackets):
    with pytest.raises(ValueError):
        progressive_tax(D('200'), brackets)


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-1', '0', '100000001', 'abc', '0.001'])
def test_invalid_gross_rejected(value):
    with pytest.raises(ValueError):
        annual_amount(value)


@pytest.mark.parametrize('value,expected', [('1.005', '1.01'), ('1.004', '1.00'),
                                           ('2.675', '2.68'), ('0', '0.00')])
def test_explicit_decimal_rounding(value, expected):
    assert monetary(D(value)) == expected


def test_verified_synthetic_adapter_output_and_monthly_equivalent():
    request = TaxRequest('ZZ', 2025, D('30000.01'), 'synthetic', 'region')
    outcome = TaxOutcome('verified', D('3000.01'), D('3300.00'),
                         sources=({'url': 'https://example.invalid/synthetic-test'},),
                         applicable_rules=('synthetic test fixture only',))
    result = present(request, outcome, 'TEST')
    assert result['net_income'] == '23700.00'
    assert result['monthly_equivalent_12'] == '1975.00'
    assert result['calculation_basis'] == 'final_annual_income_tax_estimate'
    assert 'not_payroll_or_withholding' in result['monthly_equivalent_basis']


@pytest.mark.parametrize('outcome', [TaxOutcome('partial', D('100'), None),
    TaxOutcome('verified', D('100'), None), TaxOutcome('verified', D('100'), D('50')),
    TaxOutcome('unavailable')])
def test_incomplete_adapters_never_expose_net(outcome):
    result = present(TaxRequest('ZZ', 2025, D('1000'), 'test', None), outcome, 'TEST')
    assert result['status'] != 'verified'
    assert result['net_income'] is None and result['monthly_equivalent_12'] is None


@pytest.mark.parametrize('scenario,region,year', [
    (SCENARIO, 'mainland', 2025), (SCENARIO, 'mainland', 2026),
    ('married', 'mainland', 2025), (SCENARIO, 'azores', 2025),
    (SCENARIO, None, 2025)])
def test_portugal_pending_rules_and_unsupported_scenarios_never_estimate(scenario, region, year):
    result = calculate('PT', '30000', year, scenario, region)
    assert result['status'] == 'unavailable'
    assert result['tax_year'] == year
    assert result['annual_gross'] == '30000.00'
    assert result['income_tax'] is None and result['employee_social_security'] is None
    assert result['net_income'] is None and result['sources'] == []
    assert result['applicable_rules'] == []


def test_country_registry_does_not_advertise_pending_year_as_supported():
    assert countries()['available_countries'] == []
    assert years('PT')['supported_tax_years'] == []
    assert countries()['countries'][0]['source_candidates'][0]['verification_status'] == 'not_verified'
    assert calculate('US', '30000', 2025, 'single')['status'] == 'unavailable'


@pytest.mark.parametrize('year', [None, True, '2025', 2025.0, 1899, 2101])
def test_explicit_valid_year_required(year):
    with pytest.raises(ValueError):
        calculate('PT', '30000', year, SCENARIO, 'mainland')


@pytest.mark.parametrize('taxable', [D('-1'), D('NaN'), D('Infinity'), 100.0])
def test_invalid_taxable_input(taxable):
    with pytest.raises(ValueError):
        progressive_tax(taxable, BRACKETS)


@pytest.mark.parametrize('outcome', [TaxOutcome('verified', D('-1'), D('0')),
    TaxOutcome('partial', D('NaN'), None), TaxOutcome('invented'),
    TaxOutcome('verified', D('1001'), D('0'), sources=('test',), applicable_rules=('test',))])
def test_invalid_adapter_results_fail_closed(outcome):
    with pytest.raises(ValueError):
        present(TaxRequest('ZZ', 2025, D('1000'), 'test', None), outcome, 'TEST')


def test_amount_bounds_and_input_length():
    assert annual_amount('100000000.00') == D('100000000')
    assert annual_amount('0.01') == D('0.01')
    with pytest.raises(ValueError):
        annual_amount('0.' + '0' * 10000 + '1')
