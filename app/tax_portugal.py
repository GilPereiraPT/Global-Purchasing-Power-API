"""Portugal adapter: deliberately inactive until the official annual rules are audited.

No remembered rates, withholding tables or third-party calculators are used as
substitutes for verified legislation. Candidate years are NOT supported years.
"""
from app.tax_engine import TaxOutcome

SCENARIO = 'single_employee_no_dependents'
ASSUMPTIONS = (
    'Full-year Portuguese tax resident in mainland Portugal',
    'Single adult without dependents or disability',
    'Employment income (category A) only, under the general Social Security regime',
    'Entire annual gross income subject to employee contributions',
    'No IRS Jovem, NHR, IFICI or other special tax regime',
    'No other income, optional deductions or claimed expense tax credits',
)
MISSING_RULES = (
    'Year-specific final annual IRS brackets and rates, including enacted amendments',
    'Category A specific deduction and interaction with mandatory contributions',
    'Minimum existence and its income thresholds and formulas',
    'Additional solidarity tax, applicable thresholds and interaction with deductions',
    'Applicable mandatory collection adjustments, credits and annual rounding rules',
    'Employee contribution rate, assessment base and general-regime exceptions',
)
SOURCE_CANDIDATES = (
    {'publisher': 'Autoridade Tributária e Aduaneira',
     'url': 'https://info.portaldasfinancas.gov.pt/pt/informacao_fiscal/codigos_tributarios/irs/Pages/irs68.aspx',
     'verification_status': 'not_verified', 'purpose': 'Annual IRS legislation; locate applicable historical version'},
    {'publisher': 'Diário da República', 'url': 'https://diariodarepublica.pt/',
     'verification_status': 'not_verified', 'purpose': 'Applicable enacted legislation and amendments'},
    {'publisher': 'Segurança Social', 'url': 'https://www.seg-social.pt/',
     'verification_status': 'not_verified', 'purpose': 'General employee contribution rules'},
)


class PortugalAdapter:
    def metadata(self):
        return {'country': 'PT', 'currency': 'EUR', 'status': 'unavailable',
                'supported_tax_years': [], 'candidate_tax_years': [2025],
                'scenarios': [{'id': SCENARIO, 'status': 'unavailable',
                               'regions': ['mainland'], 'supported_tax_years': []}],
                'assumptions': list(ASSUMPTIONS),
                'limitations': ['No validated annual tax year is active',
                                'Married households, dependents, islands and special regimes are unsupported',
                                'Monthly withholding and actual 12/14 payroll payments are not calculated',
                                'International net purchasing power is not calculated'],
                'missing_rules': list(MISSING_RULES),
                'source_candidates': list(SOURCE_CANDIDATES),
                'reason': 'Official fiscal rules could not be verified in the restricted environment'}

    def calculate(self, request):
        if request.scenario != SCENARIO:
            reason = 'Unsupported household or employment scenario'
        elif request.region != 'mainland':
            reason = 'Explicit mainland region required; islands are unsupported'
        else:
            reason = 'No verified Portuguese annual rules for the selected tax year'
        return TaxOutcome('unavailable', assumptions=ASSUMPTIONS,
                          limitations=MISSING_RULES, reason=reason)
