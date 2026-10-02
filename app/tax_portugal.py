"""Portugal adapter: verified 2025 AT components, full annual net still inactive.

No remembered rates, withholding tables or third-party calculators are used as
substitutes for verified legislation. Candidate years are NOT supported years.
"""
from app.tax_engine import TaxOutcome
from app import tax_portugal_2025 as pt2025

SCENARIO = 'single_employee_no_dependents'
ASSUMPTIONS = (
    'Full-year Portuguese tax resident in mainland Portugal',
    'Single adult without dependents or disability',
    'Employment income (category A) only, under the general Social Security regime',
    'Entire annual gross income subject to employee contributions',
    'No IRS Jovem, NHR, IFICI or other special tax regime',
    'No other income, union/professional dues or employment termination indemnities',
)
MISSING_RULES = (
    'Employee contribution rate, assessment base, exceptions and applicable 2025 evidence',
    'Actual eligible invoice credits and other collection deductions; not assumed zero',
    'Legal annual liquidation rounding and reconciliation of article 68(2) with AT practical table',
    'Independent complete annual reference cases before activating net salary',
)
SOURCE_CANDIDATES = (
    {'publisher': 'Autoridade Tributária e Aduaneira',
     'url': 'https://info.portaldasfinancas.gov.pt/pt/informacao_fiscal/codigos_tributarios/cirs_rep/ra/Pages/irs68ra_202512.aspx',
     'verification_status': 'verified', 'tax_year': 2025, 'purpose': 'Historical 2025 article 68; components only'},
    {'publisher': 'Diário da República', 'url': 'https://diariodarepublica.pt/',
     'verification_status': 'not_verified', 'purpose': 'Applicable enacted legislation and amendments'},
    {'publisher': 'Segurança Social', 'url': 'https://seg-social.pt/documents/10152/58902/trabalhadores_conta_outrem/55116df3-c41d-4bc9-983a-b591c8db1bcf',
     'verification_status': 'not_verified', 'purpose': 'General employee contribution rules'},
)


class PortugalAdapter:
    def metadata(self):
        return {'country': 'PT', 'currency': 'EUR', 'status': 'partial',
                'supported_tax_years': [], 'candidate_tax_years': [2025],
                'validated_component_tax_years': [2025],
                'scenarios': [{'id': SCENARIO, 'status': 'partial',
                               'regions': ['mainland'], 'supported_tax_years': []}],
                'assumptions': list(ASSUMPTIONS),
                'limitations': ['No validated annual tax year is active',
                                'Married households, dependents, islands and special regimes are unsupported',
                                'Monthly withholding and actual 12/14 payroll payments are not calculated',
                                'International net purchasing power is not calculated'],
                'missing_rules': list(MISSING_RULES),
                'source_candidates': list(SOURCE_CANDIDATES),
                'verified_component_sources': list(pt2025.SOURCES),
                'verified_component_rules': list(pt2025.RULES),
                'reason': '2025 AT components verified; complete annual model remains unvalidated'}

    def calculate(self, request):
        if request.scenario != SCENARIO:
            reason = 'Unsupported household or employment scenario'
        elif request.region != 'mainland':
            reason = 'Explicit mainland region required; islands are unsupported'
        elif request.tax_year != 2025:
            reason = 'No verified Portuguese annual rules for the selected tax year'
        else:
            module = pt2025
            return TaxOutcome('partial', sources=module.SOURCES, applicable_rules=module.RULES,
                              assumptions=ASSUMPTIONS, limitations=MISSING_RULES,
                              reason='Verified 2025 components only; final IRS, contributions and net remain unavailable',
                              components=module.available_components(request.annual_gross))
        return TaxOutcome('unavailable', assumptions=ASSUMPTIONS,
                          limitations=MISSING_RULES, reason=reason)
