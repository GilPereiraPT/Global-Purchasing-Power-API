"""Verified 2025 AT components, NOT a complete annual liquidation.

Functions consume independently known bases. They never infer employee
contributions or expenses from gross wages. Raw Decimal results are retained;
legal liquidation rounding is not asserted by this module.
"""
from decimal import Decimal as D, localcontext

ANNUAL_URL = ('https://info.portaldasfinancas.gov.pt/pt/apoio_ao_contribuinte/'
              'Cidadaos/Rendimentos/Declaracao/Deducoes_beneficios_taxas/Paginas/default.aspx')
ARTICLE68_URL = ('https://info.portaldasfinancas.gov.pt/pt/informacao_fiscal/'
                 'codigos_tributarios/cirs_rep/ra/Pages/irs68ra_202512.aspx')
ARTICLE70_URL = ('https://info.portaldasfinancas.gov.pt/pt/informacao_fiscal/'
                 'codigos_tributarios/cirs_rep/ra/Pages/irs70ra_202512.aspx')
LAW55_URL = ('https://info.portaldasfinancas.gov.pt/pt/informacao_fiscal/'
             'legislacao/diplomas_legislativos/Documents/Lei_55_A_2025.pdf')
CONTRIBUTIVE_CODE_URL = 'https://diariodarepublica.pt/dr/legislacao-consolidada/lei/2009-34514575'
CONTRIBUTIVE_ORIGINAL_URL = 'https://files.diariodarepublica.pt/1s/2009/09/18000/0649006528.pdf'
EMPLOYEE_RATE = D('.11')
STANDARD_DEDUCTION = D('4462.15')
IAS = D('522.50')
MINIMUM_REFERENCE = D('12180')
# Published AT simplified formula, not an inferred legal rounding convention.
MINIMUM_L_AT = D('13863.06')
MINIMUM_EXCLUSION = D('16093.00')
GENERAL_EXPENSE_LIMIT = D('250')
# Upper limit, normal rate A, average rate B, published practical deduction.
TABLE = (
    (D('8059'), D('.125'), D('.12500'), D('0')),
    (D('12160'), D('.160'), D('.13680'), D('282.07')),
    (D('17233'), D('.215'), D('.15982'), D('950.91')),
    (D('22306'), D('.244'), D('.17897'), D('1450.67')),
    (D('28400'), D('.314'), D('.20794'), D('3011.98')),
    (D('41629'), D('.349'), D('.25277'), D('4006.10')),
    (D('44987'), D('.431'), D('.26607'), D('7419.54')),
    (D('83696'), D('.446'), D('.34929'), D('8094.51')),
    (None, D('.480'), None, D('10939.90')),
)
SOURCES = tuple({'publisher': 'Autoridade Tributária e Aduaneira', 'url': url,
                 'tax_year': 2025, 'verification_status': 'verified',
                 'verified_on': '2026-10-02', 'scope': scope}
                for url, scope in ((ANNUAL_URL, 'Explicit 2025 annual component tables'),
                                   (ARTICLE68_URL, 'Historical article 68, December 2025'),
                                   (ARTICLE70_URL, 'Historical article 70, December 2025'),
                                   (LAW55_URL, 'Law 55-A/2025 published 22 July 2025')))
SOURCES += ({'publisher': 'Diário da República', 'url': CONTRIBUTIVE_CODE_URL,
             'tax_year': 2025, 'verification_status': 'verified', 'verified_on': '2026-10-02',
             'scope': 'Unchanged articles 13, 44, 53: standard 11% employee rate and contribution base; annual monetary rounding NOT verified'},
            {'publisher': 'Diário da República', 'url': CONTRIBUTIVE_ORIGINAL_URL,
             'tax_year': 2025, 'verification_status': 'verified', 'verified_on': '2026-10-02',
             'scope': 'Original Law 110/2009, matched against unchanged rate/base articles; not all original provisions remain effective in 2025'})
RULES = ('Contributive Code articles 13, 44, 53: general employee rate 11%; annual sum of rounded monthly liabilities remains pending',
         'CIRS article 25: standard deduction 4462.15 EUR, capped at gross; '
         'actual mandatory contributions replace it when higher',
         'CIRS article 68 / Law 55-A/2025: 2025 rates and AT practical table',
         'CIRS article 70: 2025 AT simplified minimum-existence formulas for one taxpayer',
         'CIRS article 68-A: solidarity 2.5% over 80000, 5% over 250000 taxable income',
         'CIRS article 78-B: eligible invoiced general expenses at 35%, capped at 250 EUR')


def _amount(value, name):
    if not isinstance(value, D) or not value.is_finite() or value < 0:
        raise ValueError(name + ' must be a non-negative finite Decimal')
    if value > D('100000000'):
        raise ValueError(name + ' exceeds supported monetary bound')
    return value


def employee_contribution_unrounded(contribution_base):
    """Verified general-regime rate applied to a known fully subject base.

    This is not the sum of monthly payroll amounts. No legally unverified
    annual rounding convention or disability-related reduction is applied.
    """
    _amount(contribution_base, 'contribution_base')
    with localcontext() as context:
        context.prec = 40
        return contribution_base * EMPLOYEE_RATE


def specific_deduction(gross, mandatory_contributions):
    """Restricted scenario excludes union/professional dues and indemnities.

    None means unknown, including at zero gross; never assume zero contributions.
    """
    _amount(gross, 'gross')
    if mandatory_contributions is None:
        return None
    _amount(mandatory_contributions, 'mandatory_contributions')
    return min(gross, max(STANDARD_DEDUCTION, mandatory_contributions))


def minimum_existence_abatement(gross, deduction):
    """Published 2025 AT simplified formulas, sole category-A taxpayer only."""
    _amount(gross, 'gross')
    if deduction is not None:
        _amount(deduction, 'deduction')
        if deduction > gross:
            raise ValueError('deduction cannot exceed gross')
    if gross > MINIMUM_EXCLUSION:
        return D(0)
    if deduction is None:
        return None
    with localcontext() as context:
        context.prec = 40
        if gross <= MINIMUM_REFERENCE:
            raw = MINIMUM_REFERENCE - (deduction + GENERAL_EXPENSE_LIMIT / TABLE[0][1])
        elif gross <= MINIMUM_L_AT:
            raw = (MINIMUM_REFERENCE - D('2.6') * (gross - MINIMUM_REFERENCE)
                   - deduction - GENERAL_EXPENSE_LIMIT / TABLE[0][1])
        else:
            raw = (MINIMUM_L_AT - TABLE[0][0] - D('1.35') * (gross - MINIMUM_L_AT)
                   - deduction)
        return min(gross - deduction, max(D(0), raw))


def statutory_minimum_existence_abatement(gross, deduction):
    """Historical article 70 using the unrounded statutory L formula.

    This is separate from the published simplified rounded-L helper. It does
    not claim that the internal precision/rounding of the AT is reproduced.
    """
    _amount(gross, 'gross')
    if deduction is not None:
        _amount(deduction, 'deduction')
        if deduction > gross:
            raise ValueError('deduction cannot exceed gross')
    if gross > MINIMUM_EXCLUSION:
        return D(0)
    if deduction is None:
        return None
    with localcontext() as context:
        context.prec = 40
        first_rate = TABLE[0][1]
        limit = (MINIMUM_REFERENCE - GENERAL_EXPENSE_LIMIT / (first_rate * D('3.6'))
                 + TABLE[0][0] / D('3.6'))
        if gross <= MINIMUM_REFERENCE:
            raw = MINIMUM_REFERENCE - deduction - GENERAL_EXPENSE_LIMIT / first_rate
        elif gross <= limit:
            raw = (MINIMUM_REFERENCE - D('2.6') * (gross - MINIMUM_REFERENCE)
                   - deduction - GENERAL_EXPENSE_LIMIT / first_rate)
        else:
            raw = limit - TABLE[0][0] - D('1.35') * (gross - limit) - deduction
        return min(gross - deduction, max(D(0), raw))


def practical_general_collection(taxable):
    """AT 2025 practical table: taxable*A - published deduction, BEFORE credits.

    Not final annual IRS and not a substitute for validating statutory rounding
    and the relationship to article 68(2)'s published average-rate method.
    """
    _amount(taxable, 'taxable')
    with localcontext() as context:
        context.prec = 40
        for ceiling, rate, average, deduction in TABLE:
            if ceiling is None or taxable <= ceiling:
                return taxable * rate - deduction


def statutory_general_collection(taxable):
    """Article 68(2): completed lower band at B, excess at next normal A.

    Raw arithmetic only. Boundaries follow the published normal-rate bands;
    no rounding of intermediate amounts or assertion of final liquidation.
    The practical-table helper remains separate for comparison, not net tax.
    """
    _amount(taxable, 'taxable')
    lower = D(0)
    lower_average = D(0)
    with localcontext() as context:
        context.prec = 40
        for ceiling, normal, average, practical_deduction in TABLE:
            if ceiling is None or taxable <= ceiling:
                return lower * lower_average + (taxable - lower) * normal
            lower, lower_average = ceiling, average


def solidarity_collection(taxable):
    _amount(taxable, 'taxable')
    with localcontext() as context:
        context.prec = 40
        first = max(D(0), min(taxable, D('250000')) - D('80000')) * D('.025')
        return first + max(D(0), taxable - D('250000')) * D('.05')


def general_expense_credit(eligible_expenses):
    """Known eligible invoice total only. None is NOT zero or the maximum credit."""
    if eligible_expenses is None:
        return None
    _amount(eligible_expenses, 'eligible_expenses')
    with localcontext() as context:
        context.prec = 40
        return min(GENERAL_EXPENSE_LIMIT, eligible_expenses * D('.35'))


def available_components(gross, eligible_expenses=None):
    """Only report known parameters or mathematically proved non-applicability."""
    _amount(gross, 'gross')
    credit = general_expense_credit(eligible_expenses)
    from app.tax_engine import monetary
    return (
        {'id': 'employee_social_security_rate', 'status': 'verified', 'value': '0.11',
         'unit': 'fraction', 'rule': 'Contributive Code article 53, general employees only'},
        {'id': 'employee_social_security_unrounded', 'status': 'partial', 'value': None,
         'unrounded_value': format(employee_contribution_unrounded(gross), 'f'),
         'rule': 'Fully subject annual contribution base multiplied by 11%',
         'reason': 'Not actual annual payroll contributions; periodic monetary rounding is not yet verified'},
        {'id': 'category_a_standard_deduction_limit', 'status': 'verified',
         'value': '4462.15', 'rule': 'CIRS 25 / AT annual 2025 table',
         'note': 'A limit, not the actual deduction; actual contributions remain unknown'},
        {'id': 'category_a_specific_deduction', 'status': 'unavailable', 'value': None,
         'reason': 'Actual mandatory contributions are not validated'},
        {'id': 'minimum_existence_abatement',
         'status': 'verified' if gross > MINIMUM_EXCLUSION else 'unavailable',
         'value': '0.00' if gross > MINIMUM_EXCLUSION else None,
         'rule': 'CIRS 70(4)(a), one taxpayer, gross above 16093 EUR',
         'reason': None if gross > MINIMUM_EXCLUSION else 'Specific deduction is unknown'},
        {'id': 'solidarity_collection', 'status': 'verified' if gross <= D('80000') else 'unavailable',
         'value': '0.00' if gross <= D('80000') else None,
         'rule': 'CIRS 68-A; taxable income cannot exceed category A gross',
         'reason': None if gross <= D('80000') else 'Taxable base is unknown'},
        {'id': 'general_expense_credit', 'status': 'verified' if credit is not None else 'unavailable',
         'value': monetary(credit) if credit is not None else None,
         'unrounded_value': format(credit, 'f') if credit is not None else None,
         'rule': 'CIRS 78-B: 35% of explicitly supplied eligible expenses, capped at 250 EUR',
         'rounding': 'Presentation only; legal liquidation rounding remains pending',
         'reason': None if credit is not None else 'Eligible expenses must be explicitly supplied; never assumed zero'},
        {'id': 'annual_irs', 'status': 'unavailable', 'value': None,
         'reason': 'Contributions, actual credits and annual liquidation rounding are incomplete'},
    )
