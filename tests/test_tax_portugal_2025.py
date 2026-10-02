"""Official 2025 component fixtures, not complete Portuguese net tax cases."""
from decimal import Decimal as D, localcontext
from fractions import Fraction

import pytest

from app.tax_engine import calculate, monetary
from app.tax_portugal import SCENARIO
from app.tax_portugal_2025 import (TABLE, STANDARD_DEDUCTION, specific_deduction,
    minimum_existence_abatement, practical_general_collection,
    solidarity_collection, general_expense_credit)


# Independently transcribed from the AT 2025 practical table. Fixed expected
# values calculated in cents/rational arithmetic, not using production helpers.
@pytest.mark.parametrize('taxable,expected', [
    ('8058.99', '1007.37375'), ('8059', '1007.375'), ('8059.01', '1007.37160'),
    ('12159.99', '1663.52840'), ('12160', '1663.530'), ('12160.01', '1663.49215'),
    ('17232.99', '2754.18285'), ('17233', '2754.185'), ('17233.01', '2754.18444'),
    ('22305.99', '3991.99156'), ('22306', '3991.994'), ('22306.01', '3992.10714'),
    ('28399.99', '5905.61686'), ('28400', '5905.620'), ('28400.01', '5905.50349'),
    ('41628.99', '10522.41751'), ('41629', '10522.421'), ('41629.01', '10522.56331'),
    ('44986.99', '11969.85269'), ('44987', '11969.857'), ('44987.01', '11969.69646'),
    ('83695.99', '29233.90154'), ('83696', '29233.906'), ('83696.01', '29234.18480'),
    ('0', '0'), ('10000', '1317.930'), ('100000', '37060.100'),
])
def test_official_practical_table_boundary_reference_values(taxable, expected):
    assert practical_general_collection(D(taxable)) == D(expected)


@pytest.mark.parametrize('gross,contributions,expected', [
    ('1000', '100', '1000'), ('30000', '3300', '4462.15'),
    ('4462.14', '100', '4462.14'), ('4462.15', '100', '4462.15'),
    ('4462.16', '100', '4462.15'), ('50000', '4462.14', '4462.15'),
    ('50000', '4462.15', '4462.15'), ('50000', '4462.16', '4462.16'),
    ('50000', '5500', '5500'),
])
def test_specific_deduction_known_contributions(gross, contributions, expected):
    # Contributions are independently known input, NOT a verified 11% rate.
    assert specific_deduction(D(gross), D(contributions)) == D(expected)


@pytest.mark.parametrize('gross,deduction,expected', [
    ('1000', '1000', '0'), ('10000', '4462.15', '5537.85'),
    ('12179.99', '4462.15', '5717.85'), ('12180', '4462.15', '5717.85'),
    ('12180.01', '4462.15', '5717.824'), ('13000', '4462.15', '3585.85'),
    ('13863.05', '4462.15', '1341.92'), ('13863.06', '4462.15', '1341.894'),
    ('13863.07', '4462.15', '1341.8965'), ('14000', '4462.15', '1157.041'),
    ('14856.41', '4462.15', '.8875'), ('14857.06', '4462.15', '.01'),
    ('14857.07', '4462.15', '0'), ('16092.99', '4462.15', '0'),
    ('16093', '4462.15', '0'), ('16093.01', '4462.15', '0'),
    ('13000', '0', '8048'),  # Cap at gross minus deductions is enforced below.
])
def test_minimum_existence_official_simplified_formulas(gross, deduction, expected):
    assert minimum_existence_abatement(D(gross), D(deduction)) == D(expected)


@pytest.mark.parametrize('taxable,expected', [
    ('79999.99', '0'), ('80000', '0'), ('80000.01', '.00025'),
    ('100000', '500'), ('249999.99', '4249.99975'),
    ('250000', '4250'), ('250000.01', '4250.0005'), ('300000', '6750'),
])
def test_solidarity_thresholds(taxable, expected):
    assert solidarity_collection(D(taxable)) == D(expected)


@pytest.mark.parametrize('expenses,expected', [
    ('0', '0'), ('100', '35'), ('714.28', '249.998'),
    ('714.29', '250'), ('1000', '250')])
def test_general_expense_credit_requires_actual_eligible_expenses(expenses, expected):
    assert general_expense_credit(D(expenses)) == D(expected)


def test_missing_contributions_and_credits_stay_unknown():
    assert specific_deduction(D('30000'), None) is None
    assert minimum_existence_abatement(D('12000'), None) is None
    assert general_expense_credit(None) is None
    # Explicit statutory exclusion can be known without the specific deduction.
    assert minimum_existence_abatement(D('30000'), None) == 0


def test_table_is_historical_2025_not_initial_2025_or_2026():
    assert [row[1] for row in TABLE] == list(map(D,
        ['.125', '.16', '.215', '.244', '.314', '.349', '.431', '.446', '.48']))
    assert STANDARD_DEDUCTION == D('8.54') * D('522.50')


def test_component_chain_with_independently_given_inputs_has_rational_reference():
    # Gross 30000 and actual mandatory contributions 3300 are explicit inputs.
    # Deduction 4462.15, minimum zero, taxable 25537.85.
    gross = D('30000')
    deduction = specific_deduction(gross, D('3300'))
    assert deduction == D('4462.15')
    minimum = minimum_existence_abatement(gross, deduction)
    assert minimum == 0
    taxable = gross - deduction - minimum
    reference = Fraction(2553785, 100) * Fraction(314, 1000) - Fraction(301198, 100)
    with localcontext() as context:
        context.prec = 40
        expected = D(reference.numerator) / D(reference.denominator)
    assert practical_general_collection(taxable) == expected == D('5006.9049')
    assert monetary(expected) == '5006.90'  # Presentation, not legal liquidation rounding.
    assert solidarity_collection(taxable) == 0
    assert general_expense_credit(D('100')) == D('35')
    # These components are not a validated annual IRS/net reference case.


def test_partial_api_reports_proven_nonapplicability_but_never_net():
    result = calculate('PT', '30000', 2025, SCENARIO, 'mainland')
    assert result['status'] == 'partial'
    components = {item['id']: item for item in result['components']}
    assert components['minimum_existence_abatement']['value'] == '0.00'
    assert components['solidarity_collection']['value'] == '0.00'
    assert components['general_expense_credit']['value'] is None
    assert result['income_tax'] is None and result['employee_social_security'] is None
    assert result['net_income'] is None and result['monthly_equivalent_12'] is None
    assert all(source['tax_year'] == 2025 for source in result['sources'])


@pytest.mark.parametrize('year,scenario,region', [
    (2024, SCENARIO, 'mainland'), (2026, SCENARIO, 'mainland'),
    (2025, 'married', 'mainland'), (2025, SCENARIO, 'azores'),
    (2025, SCENARIO, None)])
def test_components_do_not_leak_to_other_years_or_scenarios(year, scenario, region):
    result = calculate('PT', '30000', year, scenario, region)
    assert result['status'] == 'unavailable' and result['sources'] == []
    assert 'components' not in result


@pytest.mark.parametrize('function', [practical_general_collection, solidarity_collection,
                                      general_expense_credit])
@pytest.mark.parametrize('value', [D('-1'), D('NaN'), D('Infinity'), 1.0])
def test_component_inputs_reject_invalid_or_binary_float(function, value):
    with pytest.raises(ValueError):
        function(value)


def test_minimum_existence_exclusion_is_strictly_above_threshold():
    # Independently given zero deduction isolates the exclusion rule, not the
    # employee scenario's standard deduction.
    assert minimum_existence_abatement(D('16093'), D(0)) == D('2793.641')
    assert minimum_existence_abatement(D('16093.01'), D(0)) == 0


@pytest.mark.parametrize('gross', ['1000', '12000', '90000', '300000'])
def test_partial_results_keep_unknown_components_unknown(gross):
    result = calculate('PT', gross, 2025, SCENARIO, 'mainland')
    components = {component['id']: component for component in result['components']}
    assert result['net_income'] is None
    assert components['category_a_specific_deduction']['value'] is None
    assert components['general_expense_credit']['value'] is None
    assert components['annual_irs']['value'] is None
    if D(gross) <= D('16093'):
        assert components['minimum_existence_abatement']['value'] is None
    if D(gross) > D('80000'):
        assert components['solidarity_collection']['value'] is None


@pytest.mark.parametrize('deduction', [D('NaN'), D('-1'), D('30001')])
def test_invalid_deduction_rejected_even_when_minimum_is_excluded(deduction):
    with pytest.raises(ValueError):
        minimum_existence_abatement(D('30000'), deduction)


def test_minimum_uses_limit_not_an_assumed_actual_general_expense_credit():
    # Article 70 uses the statutory LIMIT 250/.125, not unknown actual invoices.
    assert minimum_existence_abatement(D('12180'), D('4462.15')) == D('5717.85')
    assert general_expense_credit(None) is None


def test_preserves_decimal_precision_under_external_context_changes():
    with localcontext() as context:
        context.prec = 6
        assert practical_general_collection(D('100000.01')) == D('37060.1048')
        assert minimum_existence_abatement(D('13863.07'), D('4462.15')) == D('1341.8965')
        assert solidarity_collection(D('250000.01')) == D('4250.0005')


def test_source_evidence_has_2025_historical_versions_and_retrieved_hashes():
    import json
    from pathlib import Path
    report = json.loads((Path(__file__).resolve().parents[1] /
                         'docs/tax/portugal_2025_sources.json').read_text())
    assert all(source['tax_year'] == 2025 for source in report['documents'])
    assert all(len(source['sha256_retrieved_document']) == 64 for source in report['documents'])
    assert any('irs70ra_202512' in source['url'] for source in report['documents'])
    assert any('irs68ra_202512' in source['url'] for source in report['documents'])
