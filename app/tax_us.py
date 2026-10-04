"""2026 US single employee adapter; inherited illustrations, no net activation.

Federal parameters were checked against archived IRS sources on 2026-10-04.
Complete liability and wage coverage remain unvalidated; no net activation.
"""
from decimal import Decimal as D
from app.tax_engine import TaxOutcome, annual_amount, monetary, progressive_tax
from app.tax_components import US_SINGLE_BRACKETS, IRS_FICA, IRS_ADDITIONAL_MEDICARE
from app.us_tax_evidence import sources_for
IRS_2026 = "https://www.irs.gov/irb/2025-45_IRB"
IRS_2026_FICA = "https://www.irs.gov/publications/p15"

SCENARIO = 'single_employee_no_dependents_standard_deduction'
SSA_URL = 'https://www.ssa.gov/oact/cola/cbb.html'
SOURCE_URLS = (IRS_2026, IRS_2026_FICA, IRS_FICA, IRS_ADDITIONAL_MEDICARE)
ASSUMPTIONS = (
    'Single full-year US resident employee, no dependents, wage income only',
    'Candidate illustration: ordinary wages fully covered by FICA; no retirement/health exclusions',
    'Standard deduction candidate only; no itemized deductions or other income',
    'Age, blindness, SSN/EITC eligibility and other credit facts have not been supplied',
    'TX/FL selection alone does not validate local taxes or employee contributions',
)
MISSING = (
    'Annual liability tables/rounding versus bracket illustration are not validated',
    'Credits including childless EITC and deductions including age/blindness, qualified tips/overtime need facts and 2026 rules',
    'AMT and other applicable mandatory federal components have not been validated',
    'State/local wage taxes and mandatory employee contributions require official jurisdiction-specific verification',
    'Annualized cents do not reproduce payroll-period rounding or withholding',
)
SOURCES = sources_for(SOURCE_URLS)


def illustrations(gross, facts=None):
    """Decimal re-expression of existing federal illustrations, not final tax."""
    gross = annual_amount(gross)
    facts = facts or {}
    federal = D(facts.get('federal_wages', gross))
    social = D(facts.get('social_security_wages', gross))
    medicare = D(facts.get('medicare_wages', gross))
    taxable = max(D(0), federal - D('16100'))
    brackets = tuple((D(cap) if cap is not None else None, D(rate))
                     for cap,rate in US_SINGLE_BRACKETS)
    return (
        ('standard_deduction_candidate', D('16100')),
        ('taxable_income_before_credits', taxable),
        ('federal_schedule_before_credits', progressive_tax(taxable, brackets)),
        ('employee_social_security_candidate', min(social,D('184500')) * D('.062')),
        ('employee_medicare_candidate', medicare * D('.0145')),
        ('employee_additional_medicare_candidate', max(D(0),medicare-D('200000')) * D('.009')),
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
                'source_candidates':list(SOURCES),
                'reviewed_parameter_tax_years':[2026],
                'parameter_review_scope':'Federal single brackets/basic deduction and covered-wage contribution rates only',
                'optional_us_facts':['age','blind','valid_ssn','can_be_claimed_as_dependent',
                                     'federal_wages','social_security_wages','medicare_wages',
                                     'qualified_tips','qualified_overtime']}

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
                            'status':'reviewed_parameters_assumed_facts'}
                           for name,value in illustrations(request.annual_gross, request.us_facts))
        components += tuple({'name':name,'amount':None,'status':'unavailable'} for name in (
            'federal_credits_and_adjustments','alternative_minimum_tax',
            'state_income_tax','local_income_tax','mandatory_state_employee_contributions'))
        reason = ('Explicit state required; no state/local deductions inferred' if request.region is None else
                  'Credit/local/contribution coverage and complete annual liability evidence incomplete; net income withheld')
        return TaxOutcome('partial',sources=SOURCES, applicable_rules=(
            'Reviewed 2026 federal parameters applied to assumed or supplied wage bases; not final liability',),
            assumptions=ASSUMPTIONS if request.us_facts is None else (
                ASSUMPTIONS[0], ASSUMPTIONS[2], ASSUMPTIONS[4],
                'Supplied facts are unverified; missing wage bases still use gross for illustrations only',
                'Supplied age/credit/qualified-pay facts do not establish eligibility or activate deductions'),
            limitations=MISSING,reason=reason,components=components)
