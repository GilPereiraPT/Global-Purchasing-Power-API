"""Legislation-based component references; final liquidation remains unverified."""
from decimal import Decimal as D
from fractions import Fraction

import pytest

from app.tax_engine import calculate, eligible_expenses_amount
from app.tax_portugal import SCENARIO
from app.tax_portugal_2025 import (employee_contribution_unrounded, EMPLOYEE_RATE,
                                 statutory_general_collection)


@pytest.mark.parametrize('gross,expected', [('15000', '1650'), ('25000', '2750'),
    ('40000', '4400'), ('60000', '6600'), ('100000', '11000'),
    ('0.01', '.0011'), ('1000.05', '110.0055'), ('1000.04', '110.0044')])
def test_general_employee_rate_including_unrounded_boundaries(gross, expected):
    # Code articles 13, 44, 53; these are unrounded amounts, not payroll totals.
    assert employee_contribution_unrounded(D(gross)) == D(expected)
    assert EMPLOYEE_RATE == D('.11')


@pytest.mark.parametrize('gross', [D('-1'), D('NaN'), D('Infinity'), 15000.0])
def test_contribution_base_requires_nonnegative_finite_decimal(gross):
    with pytest.raises(ValueError):
        employee_contribution_unrounded(gross)


# Values independently computed with integer/rational arithmetic from the
# historical article 68(1) B rates and 68(2) split, not progressive integration
# of A rates or the practical table's rounded deductions.
@pytest.mark.parametrize('taxable,lower,average,normal,expected', [
    ('10537.85', '8059', '12500', '16000', '1403.99100'),
    ('20537.85', '17233', '15982', '24400', '3560.56146'),
    ('35537.85', '28400', '20794', '34900', '8396.60565'),
    ('53400', '44987', '26607', '44600', '15721.88909'),
    ('89000', '83696', '34929', '48000', '31780.09584'),
])
def test_article68_component_references_for_requested_salary_bases(taxable, lower, average, normal, expected):
    rc = Fraction(taxable)
    limit = Fraction(lower)
    reference = limit * Fraction(int(average), 100000) + (rc - limit) * Fraction(int(normal), 100000)
    actual = statutory_general_collection(D(taxable))
    assert Fraction(actual) == reference
    assert actual == D(expected)


@pytest.mark.parametrize('gross', ['15000', '25000', '40000', '60000', '100000'])
def test_requested_annual_cases_are_not_falsely_activated(gross):
    result = calculate('PT', gross, 2025, SCENARIO, 'mainland', '1000')
    assert result['status'] == 'partial'
    assert result['employee_social_security'] is None
    assert result['income_tax'] is None and result['net_income'] is None
    assert result['monthly_equivalent_12'] is None
    items = {item['id']: item for item in result['components']}
    assert items['employee_social_security_rate']['value'] == '0.11'
    assert D(items['employee_social_security_unrounded']['unrounded_value']) == D(gross) * D('.11')
    assert items['general_expense_credit']['value'] == '250.00'


@pytest.mark.parametrize('supplied,expected', [(None, None), ('0', '0.00'),
    ('100', '35.00'), ('714.28', '250.00'), ('1000', '250.00')])
def test_missing_expenses_differ_from_explicit_zero_and_cap(supplied, expected):
    result = calculate('PT', '25000', 2025, SCENARIO, 'mainland', supplied)
    credit = next(item for item in result['components'] if item['id'] == 'general_expense_credit')
    assert credit['value'] == expected
    assert result['net_income'] is None
    if supplied is None:
        assert credit['status'] == 'unavailable'
        assert 'eligible_household_expenses' not in result
    else:
        assert credit['status'] == 'verified'
        assert result['eligible_household_expenses'] == format(D(supplied), '.2f')


@pytest.mark.parametrize('value', ['-1', 'NaN', 'Infinity', '100000001', '0.001', '', 'abc', '0.' + '0'*100])
def test_expense_inputs_invalid(value):
    with pytest.raises(ValueError):
        eligible_expenses_amount(value)


@pytest.mark.parametrize('gross,expected', [('12180', '5717.85'), ('13863.05', '1341.92'),
                                           ('15000', '0'), ('16093.01', '0')])
def test_statutory_minimum_references(gross, expected):
    from app.tax_portugal_2025 import statutory_minimum_existence_abatement
    assert statutory_minimum_existence_abatement(D(gross), D('4462.15')) == D(expected)


def test_statutory_minimum_does_not_silently_round_the_L_threshold():
    from decimal import localcontext
    from app.tax_portugal_2025 import statutory_minimum_existence_abatement, minimum_existence_abatement
    # Exact legislative formula using rational arithmetic, independent of the
    # Decimal adapter and the AT simplified published threshold 13863.06.
    limit = Fraction(12180) - Fraction(250) / (Fraction(1, 8) * Fraction(18, 5)) + Fraction(8059) / Fraction(18, 5)
    assert limit == Fraction(249535, 18)
    expected = limit - 8059 - Fraction(27, 20) * (Fraction('13863.06') - limit) - Fraction('4462.15')
    with localcontext() as context:
        context.prec = 30
        value = D(expected.numerator) / D(expected.denominator)
        assert abs(statutory_minimum_existence_abatement(D('13863.06'), D('4462.15')) - value) < D('1e-25')
    assert statutory_minimum_existence_abatement(D('13863.06'), D('4462.15')) != minimum_existence_abatement(D('13863.06'), D('4462.15'))


def test_unverified_rounding_cannot_turn_partial_into_verified():
    from app.tax_engine import TaxRequest
    from app.tax_portugal import PortugalAdapter
    request = TaxRequest('PT', 2025, D('25000'), SCENARIO, 'mainland', D('1000'))
    result = PortugalAdapter().calculate(request)
    assert result.status == 'partial' and result.income_tax is None
    assert result.employee_contributions is None
    assert PortugalAdapter().metadata()['supported_tax_years'] == []


@pytest.mark.parametrize('taxable,expected', [
    ('8058.99', '1007.37375'), ('8059', '1007.375'), ('8059.01', '1007.37660'),
    ('12159.99', '1663.53340'), ('12160', '1663.535'), ('12160.01', '1663.49015'),
    ('17232.99', '2754.18085'), ('17233', '2754.183'), ('17233.01', '2754.18050'),
    ('22305.99', '3991.98762'), ('22306', '3991.99006'), ('22306.01', '3992.10796'),
    ('28399.99', '5905.61768'), ('28400', '5905.62082'), ('28400.01', '5905.49949'),
    ('41628.99', '10522.41351'), ('41629', '10522.417'), ('41629.01', '10522.56664'),
    ('44986.99', '11969.85602'), ('44987', '11969.86033'), ('44987.01', '11969.69555'),
    ('83695.99', '29233.90063'), ('83696', '29233.90509'), ('83696.01', '29234.18064'),
])
def test_article68_raw_boundaries(taxable, expected):
    assert statutory_general_collection(D(taxable)) == D(expected)


def test_practical_and_statutory_methods_cannot_be_silently_interchanged():
    from app.tax_engine import monetary
    from app.tax_portugal_2025 import practical_general_collection
    taxable = D('20537.85')
    assert statutory_general_collection(taxable) == D('3560.56146')
    assert practical_general_collection(taxable) == D('3560.5654')
    assert monetary(statutory_general_collection(taxable) - D('250')) == '3310.56'
    assert monetary(practical_general_collection(taxable) - D('250')) == '3310.57'


def test_published_reference_file_is_conditional_and_never_claims_net_validation():
    import json
    from pathlib import Path
    from app.tax_portugal_2025 import specific_deduction, statutory_minimum_existence_abatement, solidarity_collection, general_expense_credit
    data = json.loads((Path(__file__).resolve().parents[1] / 'docs/tax/portugal_2025_reference_components.json').read_text())
    assert data['complete_annual_validation'] is False
    assert {case['annual_gross'] for case in data['cases']} == {'15000', '25000', '40000', '60000', '100000'}
    for case in data['cases']:
        gross = D(case['annual_gross'])
        contribution = employee_contribution_unrounded(gross)
        assert contribution == D(case['employee_contribution_unrounded'])
        deduction = specific_deduction(gross, contribution)
        assert deduction == D(case['specific_deduction_given_contributions_equal_unrounded_product'])
        minimum = statutory_minimum_existence_abatement(gross, deduction)
        assert minimum == D(case['minimum_existence_abatement'])
        taxable = gross - deduction - minimum
        assert taxable == D(case['conditional_taxable_income'])
        assert statutory_general_collection(taxable) == D(case['article68_collection_unrounded_before_credits'])
        assert solidarity_collection(taxable) == D(case['solidarity_unrounded'])
        assert general_expense_credit(D(case['eligible_household_expenses'])) == D(case['general_family_expense_credit_unrounded'])
        assert case['final_annual_irs'] is None and case['annual_net'] is None and case['monthly_equivalent_12'] is None
