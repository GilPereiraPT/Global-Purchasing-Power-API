"""Opt-in ordinary-wage federal model; never infer omitted eligibility facts."""
from decimal import Decimal as D
from app.tax_engine import monetary
from app.tax_components import US_SINGLE_BRACKETS
from app.tax_engine import progressive_tax

SCENARIO = 'single_ordinary_wages_federal_benchmark'
REQUIRED = ('age', 'blind', 'valid_ssn', 'can_be_claimed_as_dependent',
            'federal_wages', 'social_security_wages', 'medicare_wages',
            'qualified_tips', 'qualified_overtime',
            'nonitemizer_charitable_contributions', 'ordinary_wage_model_confirmed')
ASSUMPTIONS = (
    'Single full-year resident, no dependents, age 25-64, not blind or claimable as a dependent',
    'Ordinary employee wages only; all three taxable wage bases equal supplied gross',
    'No tips, qualified overtime, charitable deductions, other deductions, credits, AMT preferences or prior-year credits',
    'Explicit model confirmation excludes investment/business/foreign income, special compensation and special taxes',
    'Federal annual component estimate; state/local taxes, state premiums and voluntary deductions excluded',
)


def components(gross, facts):
    """Return federal-only amounts or specific reasons why the model cannot run."""
    facts = facts or {}
    missing = [name for name in REQUIRED if name not in facts]
    if missing:
        return (), ('Explicit facts required: ' + ', '.join(missing),)
    if not D('19540') <= gross <= D('500000'):
        return (), ('Model covers gross 19540-500000 only; EITC eligibility/refunds and AMT phaseout outside this range remain unavailable',)
    if (not 25 <= facts['age'] <= 64 or facts['blind']
            or not facts['valid_ssn'] or facts['can_be_claimed_as_dependent']
            or not facts['ordinary_wage_model_confirmed']):
        return (), ('Facts do not match the explicitly selected ordinary-wage model',)
    if any(D(facts[name]) != gross for name in
           ('federal_wages', 'social_security_wages', 'medicare_wages')):
        return (), ('Distinct wage bases require separate eligibility/base review',)
    if any(D(facts[name]) != 0 for name in
           ('qualified_tips', 'qualified_overtime', 'nonitemizer_charitable_contributions')):
        return (), ('Nonzero special deductions require eligibility and AMT treatment review',)
    taxable = gross - D('16100')
    regular = progressive_tax(taxable, tuple((D(c) if c is not None else None, D(r))
                                            for c, r in US_SINGLE_BRACKETS))
    # Ordinary wages and no preferences: AMTI restores the standard deduction.
    # Range ends at phaseout start, so no older 25% phaseout is imported.
    amt_excess = max(D(0), gross - D('90100'))
    tentative = min(amt_excess, D('244500')) * D('.26') + max(D(0), amt_excess-D('244500')) * D('.28')
    amt = max(D(0), tentative - regular)
    income_tax = regular + amt
    ss = min(gross, D('184500')) * D('.062')
    medicare = gross * D('.0145')
    additional = max(D(0), gross-D('200000')) * D('.009')
    values = (
        ('federal_standard_deduction_model', D('16100')),
        ('federal_taxable_income_model', taxable),
        ('federal_regular_income_tax_model', regular),
        ('federal_amti_model', gross),
        ('federal_tentative_minimum_tax_model', tentative),
        ('federal_additional_amt_model', amt),
        ('federal_childless_eitc_model', D(0)),
        ('federal_income_tax_model', income_tax),
        ('federal_employee_social_security_model', ss),
        ('federal_employee_medicare_model', medicare),
        ('federal_employee_additional_medicare_model', additional),
        ('federal_contributions_model', ss+medicare+additional),
        ('income_after_federal_components_before_state_local_and_other_deductions',
         gross-income_tax-ss-medicare-additional),
    )
    return tuple({'name': name, 'amount': monetary(value),
                  'status': 'scoped_federal_model_estimate'} for name, value in values), ()
