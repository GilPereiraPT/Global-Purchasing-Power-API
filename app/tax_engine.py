"""Country-neutral annual tax engine. Monetary JSON values are decimal strings.

Only audited country adapters can produce a verified net estimate. Missing
components never become zero and partial results never expose net income.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from typing import Protocol

CENT = Decimal('0.01')
MAX_GROSS = Decimal('100000000')


def annual_amount(value):
    raw = str(value)
    if len(raw) > 64:
        raise ValueError('annual_gross monetary input is too long')
    try:
        amount = Decimal(raw)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError('annual_gross must be a decimal monetary amount') from None
    if not amount.is_finite() or not 0 < amount <= MAX_GROSS:
        raise ValueError('annual_gross must be positive and at most 100000000')
    with localcontext() as context:
        context.prec = 40
        if amount != amount.quantize(CENT):
            raise ValueError('annual_gross must have at most two decimal places')
    return amount


def eligible_expenses_amount(value):
    """Explicit eligible invoices: zero is valid, missing is not zero."""
    raw = str(value)
    if len(raw) > 64:
        raise ValueError('eligible_household_expenses monetary input is too long')
    try:
        amount = Decimal(raw)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError('eligible_household_expenses must be a decimal amount') from None
    if not amount.is_finite() or not 0 <= amount <= MAX_GROSS:
        raise ValueError('eligible_household_expenses must be non-negative and at most 100000000')
    with localcontext() as context:
        context.prec = 40
        if amount != amount.quantize(CENT):
            raise ValueError('eligible_household_expenses must have at most two decimal places')
    return amount


def monetary(value):
    """Round once at the output boundary; never convert through binary float."""
    with localcontext() as context:
        context.prec = 40
        return format(value.quantize(CENT, rounding=ROUND_HALF_UP), '.2f')


def progressive_tax(taxable, brackets):
    """Pure progressive arithmetic; brackets are data supplied by an adapter.

    This is not a Portuguese tax table. Country-specific abatements, credits,
    special rates and legally required intermediate rounding belong in adapters.
    """
    if not isinstance(taxable, Decimal) or not taxable.is_finite() or taxable < 0:
        raise ValueError('taxable must be a non-negative finite Decimal')
    lower = Decimal(0)
    checked = []
    for index, (ceiling, rate) in enumerate(brackets):
        if not isinstance(rate, Decimal) or not rate.is_finite() or not 0 <= rate <= 1:
            raise ValueError('rates must be finite Decimal fractions')
        if ceiling is None:
            if index != len(brackets) - 1:
                raise ValueError('only the final bracket may be open')
        elif (not isinstance(ceiling, Decimal) or not ceiling.is_finite()
              or ceiling <= lower):
            raise ValueError('bracket ceilings must strictly increase')
        checked.append((lower, ceiling, rate))
        if ceiling is not None:
            lower = ceiling
    if not checked or checked[-1][1] is not None:
        raise ValueError('a final open bracket is required')
    with localcontext() as context:
        context.prec = 40
        return sum((max(Decimal(0), (taxable if ceiling is None else min(taxable, ceiling))
                        - floor) * rate for floor, ceiling, rate in checked), Decimal(0))


@dataclass(frozen=True)
class TaxRequest:
    country: str
    tax_year: int
    annual_gross: Decimal
    scenario: str
    region: str | None
    eligible_household_expenses: Decimal | None = None


@dataclass(frozen=True)
class TaxOutcome:
    """Amounts and provenance must be independently validated by an adapter."""
    status: str
    income_tax: Decimal | None = None
    employee_contributions: Decimal | None = None
    sources: tuple = ()
    applicable_rules: tuple = ()
    assumptions: tuple = ()
    limitations: tuple = ()
    reason: str | None = None
    components: tuple = ()


class CountryAdapter(Protocol):
    def metadata(self) -> dict: ...
    def calculate(self, request: TaxRequest) -> TaxOutcome: ...


def _adapters():
    from app.tax_portugal import PortugalAdapter
    return {'PT': PortugalAdapter()}


def countries():
    rows = [adapter.metadata() for adapter in _adapters().values()]
    return {'countries': rows, 'count': len(rows),
            'available_countries': [row['country'] for row in rows if row['supported_tax_years']]}


def metadata(country):
    adapter = _adapters().get(str(country).upper())
    if adapter is None:
        return {'country': str(country).upper(), 'status': 'unavailable',
                'supported_tax_years': [], 'scenarios': [],
                'reason': 'No validated country adapter'}
    return adapter.metadata()


def years(country):
    details = metadata(country)
    return {key: details[key] for key in ('country', 'status', 'supported_tax_years')}


def calculate(country, annual_gross, tax_year, scenario, region=None, eligible_household_expenses=None):
    code = str(country).upper()
    if len(code) != 2 or not code.isascii() or not code.isalpha():
        raise ValueError('country must be a two-letter code')
    if isinstance(tax_year, bool) or not isinstance(tax_year, int) or not 1900 <= tax_year <= 2100:
        raise ValueError('tax_year must be an explicitly selected year from 1900 to 2100')
    if not isinstance(scenario, str) or not scenario.strip():
        raise ValueError('scenario must be explicitly selected')
    expenses = (eligible_expenses_amount(eligible_household_expenses)
                if eligible_household_expenses is not None else None)
    request = TaxRequest(code, tax_year, annual_amount(annual_gross), scenario, region, expenses)
    adapter = _adapters().get(code)
    outcome = (adapter.calculate(request) if adapter else
               TaxOutcome('unavailable', reason='No validated country adapter'))
    return present(request, outcome, metadata(code).get('currency'))


def present(request, outcome, currency):
    """Fail closed if an adapter claims verification with incomplete evidence."""
    if outcome.status not in ('verified', 'partial', 'unavailable'):
        raise ValueError('Invalid adapter result status')
    amounts = (outcome.income_tax, outcome.employee_contributions)
    for amount in amounts:
        if amount is not None and (not isinstance(amount, Decimal) or not amount.is_finite()
                                   or amount < 0):
            raise ValueError('Invalid adapter monetary result')
    status = outcome.status
    reason = outcome.reason
    if status == 'verified' and (any(v is None for v in amounts)
                                 or not outcome.sources or not outcome.applicable_rules
                                 or not currency):
        status = 'partial' if any(v is not None for v in amounts) else 'unavailable'
        reason = 'Adapter verification incomplete; net income withheld'
    net = None
    monthly = None
    if status == 'verified':
        with localcontext() as context:
            context.prec = 40
            net_amount = request.annual_gross - sum(amounts)
            if net_amount < 0:
                raise ValueError('Validated deductions exceed gross income')
            net = monetary(net_amount)
            monthly = monetary(net_amount / Decimal(12))
    result = {'status': status, 'country': request.country, 'currency': currency,
            'tax_year': request.tax_year, 'scenario': request.scenario,
            'region': request.region, 'annual_gross': monetary(request.annual_gross),
            'income_tax': monetary(outcome.income_tax) if outcome.income_tax is not None else None,
            'employee_social_security': (monetary(outcome.employee_contributions)
                                         if outcome.employee_contributions is not None else None),
            'net_income': net, 'monthly_equivalent_12': monthly,
            'calculation_basis': 'final_annual_income_tax_estimate',
            'monthly_equivalent_basis': 'annual_net_divided_by_12_not_payroll_or_withholding',
            'sources': list(outcome.sources), 'applicable_rules': list(outcome.applicable_rules),
            'assumptions': list(outcome.assumptions), 'limitations': list(outcome.limitations),
            'reason': reason}
    if request.eligible_household_expenses is not None:
        result['eligible_household_expenses'] = monetary(request.eligible_household_expenses)
    if outcome.components:
        result['components'] = list(outcome.components)
    return result


def calculate_query(params):
    """Shared strict HTTP input validation for ASGI and native WSGI."""
    allowed = {'country', 'annual_gross', 'tax_year', 'scenario', 'region', 'eligible_household_expenses'}
    if set(params) - allowed:
        raise ValueError('Unexpected tax calculation parameters')
    values = {}
    for key, entries in params.items():
        if len(entries) != 1:
            raise ValueError('Supply one value for ' + key)
        values[key] = entries[0]
    for key in ('country', 'annual_gross', 'tax_year', 'scenario'):
        if not values.get(key):
            raise ValueError('Explicit ' + key + ' is required')
    raw_year = values['tax_year']
    if len(raw_year) != 4 or not raw_year.isascii() or not raw_year.isdigit():
        raise ValueError('tax_year must be a four-digit year')
    return calculate(values['country'], values['annual_gross'], int(raw_year),
                     values['scenario'], values.get('region'), values.get('eligible_household_expenses'))
