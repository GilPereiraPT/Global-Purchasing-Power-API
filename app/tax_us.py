"""2026 US single employee adapter; inherited illustrations, no net activation.

Official-source retrieval is blocked in the current review. Candidate constants
are inherited from tax_components, not newly verified statutory liability.
"""
from decimal import Decimal as D
from app.tax_engine import TaxOutcome, annual_amount, monetary, progressive_tax
from app.tax_components import US_SINGLE_BRACKETS, IRS_2026, IRS_FICA, IRS_ADDITIONAL_MEDICARE

SCENARIO = 'single_employee_no_dependents_standard_deduction'
SSA_URL = 'https://www.ssa.gov/oact/cola/cbb.html'
SOURCE_URLS = (IRS_2026, IRS_FICA, IRS_ADDITIONAL_MEDICARE, SSA_URL)
ASSUMPTIONS = (
    'Single full-year US resident employee, no dependents, wage income only',
    'Candidate illustration: ordinary wages fully covered by FICA; no retirement/health exclusions',
    'Standard deduction candidate only; no itemized deductions or other income',
    'Age, blindness, SSN/EITC eligibility and other credit facts have not been supplied',
    'TX/FL selection alone does not validate local taxes or employee contributions',
)
MISSING = (
    'Official IRS/SSA 2026 schedule, deduction, contribution bases and rates could not be retrieved',
    'Annual liability tables/rounding versus bracket illustration are not validated',
    'Credits including childless EITC and deductions including age/blindness, qualified tips/overtime need facts and 2026 rules',
    'AMT and other applicable mandatory federal components have not been validated',
    'State/local wage taxes and mandatory employee contributions require official jurisdiction-specific verification',
    'Annualized cents do not reproduce payroll-period rounding or withholding',
)
SOURCES = tuple({'url':url, 'tax_year':2026, 'verification_status':'blocked',
                 'reviewed_on':'2026-10-04', 'reason':'ProxyError; no official response acquired'}
                for url in SOURCE_URLS)


def illustrations(gross):
    """Decimal re-expression of existing federal illustrations, not final tax."""
    gross = annual_amount(gross)
    taxable = max(D(0), gross - D('16100'))
    brackets = tuple((D(cap) if cap is not None else None, D(rate))
                     for cap,rate in US_SINGLE_BRACKETS)
    return (
        ('standard_deduction_candidate', D('16100')),
        ('taxable_income_before_credits', taxable),
        ('federal_schedule_before_credits', progressive_tax(taxable, brackets)),
        ('employee_social_security_candidate', min(gross,D('184500')) * D('.062')),
        ('employee_medicare_candidate', gross * D('.0145')),
        ('employee_additional_medicare_candidate', max(D(0),gross-D('200000')) * D('.009')),
    )


class USAdapter:
    def metadata(self):
        return {'country':'US', 'currency':'USD', 'status':'partial',
                'supported_tax_years':[], 'benchmark_tax_years':[], 'candidate_tax_years':[2026],
                'validated_component_tax_years':[],
                'scenarios':[{'id':SCENARIO,'status':'partial','regions':['TX','FL'],
                              'supported_tax_years':[], 'benchmark_tax_years':[]}],
                'assumptions':list(ASSUMPTIONS), 'missing_rules':list(MISSING),
                'limitations':['No verified/benchmark net, no withholding, no international net purchasing power'],
                'source_candidates':list(SOURCES)}

    def calculate(self, request):
        if request.scenario != SCENARIO or request.tax_year != 2026:
            return TaxOutcome('unavailable',reason='Unsupported US scenario or tax year',
                              assumptions=ASSUMPTIONS,limitations=MISSING)
        if request.eligible_household_expenses is not None:
            raise ValueError('Portuguese eligible household expenses do not apply to US taxes')
        if request.region is not None:
            from app.client_config import REGIONS
            states = {code for code, _ in REGIONS['US']['options']}
            if request.region not in states:
                raise ValueError('Select a registered US state code')
        components = tuple({'name':name,'amount':monetary(value),
                            'status':'inherited_illustration_not_verified'}
                           for name,value in illustrations(request.annual_gross))
        components += tuple({'name':name,'amount':None,'status':'unavailable'} for name in (
            'federal_credits_and_adjustments','alternative_minimum_tax',
            'state_income_tax','local_income_tax','mandatory_state_employee_contributions'))
        reason = ('Explicit state required; no state/local deductions inferred' if request.region is None else
                  'Official 2026 and credit/local/contribution evidence incomplete; net income withheld')
        return TaxOutcome('partial',sources=SOURCES, applicable_rules=(
            'Inherited 2026 federal-only illustration; not independently verified in this review',),
            assumptions=ASSUMPTIONS,limitations=MISSING,reason=reason,components=components)
