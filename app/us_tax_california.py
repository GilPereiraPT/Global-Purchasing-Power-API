"""CA 2026 wage-only components; no 2025 FTB schedule transplanted into 2026."""
from decimal import Decimal as D
from app.tax_engine import annual_amount,monetary
from app.us_tax_evidence import sources_for

SCENARIO = 'single_employee_no_dependents_wages_only'
URLS = ('https://www.ftb.ca.gov/forms/2026/2026-540-tax-rate-schedules.pdf',
        'https://www.ftb.ca.gov/forms/2026/2026-540-booklet.html',
        'https://edd.ca.gov/en/payroll_taxes/rates_and_withholding/')


def sdi_illustration(annual_wages):
    """Inherited EDD rate candidate; annual cents, not actual pay-period sum."""
    return annual_amount(annual_wages)*D('.013')


def calculate(annual_gross,tax_year=2026,scenario=SCENARIO):
    gross=annual_amount(annual_gross)
    if isinstance(tax_year,bool) or not isinstance(tax_year,int):
        raise ValueError('Explicit integer tax year required')
    supported=tax_year==2026 and scenario==SCENARIO
    sources=list(sources_for(URLS))
    return {'status':'partial' if supported else 'unavailable','state':'CA',
            'tax_year':tax_year,'scenario':scenario,'currency':'USD',
            'annual_gross':monetary(gross),'income_tax':None,
            'employee_contributions':None,'net_income':None,
            'components':[
                {'name':'employee_sdi_all_wages_covered_illustration',
                 'amount':monetary(sdi_illustration(gross)) if supported else None,
                 'status':'reviewed_parameters_assumed_facts' if supported else 'unavailable'},
                *({'name':name,'amount':None,'status':'unavailable'} for name in (
                    'state_annual_tax_schedule','standard_deduction',
                    'personal_exemption_credit','other_applicable_credits',
                    'state_income_adjustments','high_income_additional_tax',
                    'employee_final_sdi'))],
            'sources':sources,
            'assumptions':['Single full-year CA resident employee, no dependents, wages only',
                           'SDI illustration only: all wages covered, ordinary state plan, no approved voluntary plan or exemption'],
            'missing_components':['Official 2026 annual FTB brackets/deduction/credits/adjustments, never substituted with 2025',
                                  'Applicable high-income additional tax and its legal taxable base',
                                  'SDI coverage/exemptions and actual pay-period rounding; rate/no ceiling reviewed'],
            'basis':'annual_component_illustration_not_withholding',
            'reason':'FTB/EDD 2026 evidence incomplete; no annual tax or net activated'}
