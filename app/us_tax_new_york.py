"""NY 2026 annual single-employee components. Recapture/credits remain unknown.

Preserves inherited TAX 601 rounded bases; does not integrate a continuous rate
schedule or mistake withholding tables for annual liability. No net output.
"""
from decimal import Decimal as D
from app.tax_engine import annual_amount, monetary
from app.us_tax_evidence import sources_for

SCENARIO = 'single_employee_no_dependents_wages_only'
SCHEDULE = ((D('8500'),D('0'),D('0'),D('.039')),
            (D('11700'),D('8500'),D('332'),D('.044')),
            (D('13900'),D('11700'),D('473'),D('.0515')),
            (D('80650'),D('13900'),D('586'),D('.054')),
            (D('215400'),D('80650'),D('4191'),D('.059')))
URLS = (
    'https://www.nysenate.gov/legislation/laws/TAX/601',
    'https://www.tax.ny.gov/pit/file/tax-tables/2026.htm',
    'https://www.tax.ny.gov/pit/credits/household_credit.htm',
    'https://www.wcb.ny.gov/content/main/DisabilityBenefits/Employer/WhoPaysBenefits.jsp',
    'https://paidfamilyleave.ny.gov/2026',
)


def schedule_illustration(gross):
    gross = annual_amount(gross)
    if gross > D('107650'):
        return None  # Do not extrapolate pre-recapture schedule at higher AGI.
    taxable = max(D(0),gross-D('8000'))
    for ceiling,floor,base,rate in SCHEDULE:
        if taxable <= ceiling:
            return base+(taxable-floor)*rate
    return None


def calculate(annual_gross, tax_year=2026, scenario=SCENARIO, *,
              residence_locality=None, work_locality=None):
    gross = annual_amount(annual_gross)
    if isinstance(tax_year,bool) or not isinstance(tax_year,int):
        raise ValueError('Explicit integer tax year required')
    for place in (residence_locality,work_locality):
        if place is not None and place not in ('NYC','Yonkers','other'):
            raise ValueError('Locality must be NYC, Yonkers, other or missing')
    supported = tax_year==2026 and scenario==SCENARIO
    schedule = schedule_illustration(gross) if supported else None
    sources = list(sources_for(URLS))
    components = [
        {'name':'state_schedule_before_credits_illustration',
         'amount':monetary(schedule) if schedule is not None else None,
         'status':'inherited_illustration' if schedule is not None else 'unavailable'},
        *({'name':name,'amount':None,'status':'unavailable'} for name in (
            'state_supplemental_tax_recapture','state_credits','state_final_income_tax',
            'nyc_income_tax','yonkers_resident_surcharge','yonkers_nonresident_earnings_tax',
            'employee_disability_benefits','employee_paid_family_leave')),
    ]
    missing = ['Official 2026 annual instructions, tax-table rounding and credit applicability',
               'Dependent eligibility/household and federal EITC facts; no credit assumed zero',
               'Disability/PFL coverage, employer financing and pay periods; no mandatory contribution assumed zero']
    if gross>D('107650'):missing.append('Supplemental tax/recapture above 107650 NY AGI, including high-income regimes')
    if residence_locality is None or work_locality is None:
        missing.append('Residence AND work locality required to separate NYC/Yonkers resident and nonresident taxes')
    else:
        missing.append('Locality supplied, but NYC/Yonkers/non-applicability rules still require official verification')
    return {'status':'partial' if supported else 'unavailable', 'state':'NY','tax_year':tax_year,
            'scenario':scenario,'currency':'USD','annual_gross':monetary(gross),
            'residence_locality':residence_locality,'work_locality':work_locality,
            'income_tax':None,'employee_contributions':None,'net_income':None,
            'components':components,'missing_components':missing,'sources':sources,
            'assumptions':['Full-year NY resident, single, no dependents, wages only',
                           'Illustration only: NY AGI equals gross, no state adjustments, standard deduction 8000 for nondependent single'],
            'rounding':'Inherited rounded statutory bases preserved; output cents ROUND_HALF_UP, not verified legal annual rounding',
            'basis':'annual_pre_credit_illustration_not_withholding',
            'reason':'Incomplete official rules and required facts; final state/local tax and net withheld'}
