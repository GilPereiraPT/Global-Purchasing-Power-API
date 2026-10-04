"""PA 2026 compensation, credits and local components; never assume net facts."""
from decimal import Decimal as D,InvalidOperation
from app.tax_engine import annual_amount,monetary

SCENARIO='single_employee_no_dependents_wages_only'
URLS=(
 'https://www.pa.gov/agencies/revenue/resources/tax-types-and-information/personal-income-tax',
 'https://www.pa.gov/agencies/revenue/resources/tax-types-and-information/personal-income-tax/tax-forgiveness',
 'https://www.pa.gov/agencies/revenue/resources/tax-types-and-information/personal-income-tax/working-pennsylvanians-tax-credit',
 'https://www.pa.gov/agencies/dli/programs-services/unemployment/for-employers/uc-tax-information',
 'https://www.phila.gov/services/payments-assistance-taxes/taxes/income-taxes/wage-tax-salaried-employees/')


def nonnegative(value):
    if isinstance(value,bool) or len(str(value))>64:
        raise ValueError('Invalid monetary input')
    try:amount=D(str(value))
    except (ValueError,InvalidOperation):raise ValueError('Invalid monetary input') from None
    if amount.is_finite() and amount==0:return D(0)
    return annual_amount(value)


def calculate(annual_gross,tax_year=2026,scenario=SCENARIO,*,taxable_compensation=None,
              forgiveness_eligibility_income=None,federal_eitc=None,
              residence_psd=None,work_psd=None):
    gross=annual_amount(annual_gross)
    if isinstance(tax_year,bool) or not isinstance(tax_year,int):
        raise ValueError('Explicit integer tax year required')
    for code in (residence_psd,work_psd):
        if code is not None and (not isinstance(code,str) or len(code)!=6 or not code.isascii() or not code.isdigit()):
            raise ValueError('PSD must be six ASCII digits or missing')
    compensation=nonnegative(taxable_compensation) if taxable_compensation is not None else None
    if compensation is not None and compensation>gross:
        raise ValueError('Taxable compensation exceeds supported wage-only gross')
    eligibility=nonnegative(forgiveness_eligibility_income) if forgiveness_eligibility_income is not None else None
    eitc=nonnegative(federal_eitc) if federal_eitc is not None else None
    supported=tax_year==2026 and scenario==SCENARIO
    precredit=compensation*D('.0307') if compensation is not None and supported else None
    missing=['2026 state credit/Tax Forgiveness schedule and eligibility definition',
             'Working Pennsylvanians Tax Credit rule and federal EITC eligibility',
             'Employee unemployment contribution rate/base and periodic rounding',
             'Local EIT/LST and Philadelphia residence/work tax, sourcing and effective dates']
    if compensation is None:missing.append('PA taxable compensation required; gross is not automatically PA taxable wages')
    if eligibility is None:missing.append('Explicit Tax Forgiveness eligibility income required, not merely taxable wages')
    if eitc is None:missing.append('Federal EITC determination required; no credit inferred zero')
    if residence_psd is None or work_psd is None:missing.append('Both residence and work PSD/locality required; local taxes not assumed zero')
    return {'status':'partial' if supported else 'unavailable','state':'PA',
            'tax_year':tax_year,'scenario':scenario,'currency':'USD',
            'annual_gross':monetary(gross),
            'taxable_compensation':monetary(compensation) if compensation is not None else None,
            'forgiveness_eligibility_income':monetary(eligibility) if eligibility is not None else None,
            'federal_eitc':monetary(eitc) if eitc is not None else None,
            'residence_psd':residence_psd,'work_psd':work_psd,
            'income_tax':None,'employee_contributions':None,'net_income':None,
            'components':[
                {'name':'state_schedule_before_credits_illustration',
                 'amount':monetary(precredit) if precredit is not None else None,
                 'status':'inherited_illustration_not_verified' if precredit is not None else 'unavailable'},
                *({'name':name,'amount':None,'status':'unavailable'} for name in (
                    'tax_forgiveness','working_pennsylvanians_tax_credit','state_final_tax',
                    'employee_unemployment','local_earned_income_tax','local_services_tax',
                    'philadelphia_wage_tax'))],
            'missing_components':missing,
            'sources':[{'url':u,'tax_year':2026,'verification_status':'blocked',
                        'reason':'2026-10-04 GET ProxyError; no original obtained'} for u in URLS],
            'assumptions':['Single full-year PA resident employee, no dependents, salary only',
                           'No automatic standard deduction, exclusion or credit from household label',
                           'Supplied taxable compensation/eligibility amounts require independent determination'],
            'basis':'annual_component_illustration_not_withholding',
            'reason':'Mandatory state/local/contribution facts or rules not validated; net withheld'}
