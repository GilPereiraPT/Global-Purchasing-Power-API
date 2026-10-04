"""Portugal adapter: 2025 official components plus an explicit annual benchmark.

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
    'Eligible household expenses must be explicitly supplied; missing is not zero',
    'All other personal collection deductions are set to zero only by the benchmark contract',
)
MISSING_RULES = (
    'Employee periodic monetary rounding and annual aggregation of contributions are not reproduced',
    'Legal annual liquidation precision/rounding is not asserted',
    'Benchmark assumptions do not replace a personal tax return or payroll calculation',
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
        return {'country': 'PT', 'currency': 'EUR', 'status': 'benchmark_estimate',
                'supported_tax_years': [], 'benchmark_tax_years': [2025],
                'candidate_tax_years': [2025], 'validated_component_tax_years': [2025],
                'scenarios': [{'id': SCENARIO, 'status': 'benchmark_estimate',
                               'regions': ['mainland'], 'supported_tax_years': [],
                               'benchmark_tax_years': [2025]}],
                'assumptions': list(ASSUMPTIONS),
                'limitations': ['No official-personal-liquidation tax year is advertised as verified',
                                'Married households, dependents, islands and special regimes are unsupported',
                                'Monthly withholding and actual 12/14 payroll payments are not calculated',
                                'International net purchasing power is not calculated'],
                'missing_rules': list(MISSING_RULES),
                'source_candidates': list(SOURCE_CANDIDATES),
                'verified_component_sources': list(pt2025.SOURCES),
                'verified_component_rules': list(pt2025.RULES),
                'inputs': {'eligible_household_expenses': 'Explicit eligible general-family invoice total; required for a complete benchmark'},
                'reason': '2025 official components support an annualized benchmark, not a personal official liquidation'}

    def calculate(self, request):
        if request.scenario != SCENARIO:
            reason = 'Unsupported household or employment scenario'
        elif request.region != 'mainland':
            reason = 'Explicit mainland region required; islands are unsupported'
        elif request.tax_year != 2025:
            reason = 'No verified Portuguese annual rules for the selected tax year'
        else:
            module = pt2025
            estimate = module.benchmark_estimate(request.annual_gross, request.eligible_household_expenses)
            if estimate is None:
                return TaxOutcome('partial', sources=module.SOURCES, applicable_rules=module.RULES,
                                  assumptions=ASSUMPTIONS, limitations=MISSING_RULES,
                                  reason='eligible_household_expenses must be supplied explicitly for the benchmark',
                                  components=module.available_components(request.annual_gross, request.eligible_household_expenses))
            return TaxOutcome('benchmark_estimate', income_tax=estimate['income_tax'],
                              employee_contributions=estimate['employee_contributions'],
                              sources=module.SOURCES, applicable_rules=module.RULES,
                              assumptions=ASSUMPTIONS, limitations=MISSING_RULES,
                              reason='Annualized benchmark only; not an official personal liquidation or payslip',
                              components=module.benchmark_components(request.annual_gross, request.eligible_household_expenses))
        return TaxOutcome('unavailable', assumptions=ASSUMPTIONS,
                          limitations=MISSING_RULES, reason=reason)
