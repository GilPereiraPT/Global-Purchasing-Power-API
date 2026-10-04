"""TX/FL rule coverage, distinct from a complete employee contribution model.

Only previously reviewed official rule parameters may produce scoped zeroes.
Unknown local charges or employment coverage never inherit the state zero.
"""
from app.us_tax_evidence import sources_for

RULES = {
    'TX': {
        'state_income_tax_final': ('https://tlc.texas.gov/docs/legref/TxConst.pdf',
                                   'Article VIII section 24-a: individual net-income tax prohibition'),
    },
    'FL': {
        'state_income_tax_final': ('https://www.flsenate.gov/Laws/Statutes/2026/220.02',
                                   'Section 220.02: natural-person income-tax exclusion'),
        'employee_reemployment_contribution': ('https://www.flsenate.gov/Laws/Statutes/2026/443.041',
                                               'Section 443.041: employer contributions cannot be financed by employee deductions'),
    },
}
UNKNOWN = ('local_income_tax', 'mandatory_state_employee_contributions')


def coverage(state):
    """Fresh metadata, no IO or DB mutation; wage-only full-year resident scope."""
    rules = RULES.get(state, {})
    components, sources = [], []
    for name, (url, rule) in rules.items():
        source = sources_for((url,))[0]
        reviewed = (source.get('verification_status') == 'parameters_reviewed'
                    and source.get('tax_year') == 2026
                    and source.get('status') == 200
                    and len(source.get('sha256', '')) == 64)
        components.append({'name': name, 'amount': '0.00' if reviewed else None,
                           'status': 'reviewed_rule_parameter' if reviewed else 'unavailable',
                           'rule': rule, 'source_url': url})
        sources.append(source)
    if state == 'TX':
        components.append({'name': 'employee_unemployment_contribution',
                           'amount': None, 'status': 'unavailable'})
    components.extend({'name': name, 'amount': None, 'status': 'unavailable'}
                      for name in UNKNOWN)
    missing = [
        'Official local wage-tax/non-applicability evidence for residence and work jurisdiction',
        'Mandatory employee contribution applicability: private/public employment, retirement and special regimes; no zero inferred',
        'Explicit full-year same-state residence/work and ordinary private-sector employment scope required before net activation',
    ]
    if state == 'TX':
        missing.append('Texas employee unemployment contribution prohibition: official TWC/Labor Code acquisition blocked')
    elif state != 'FL':
        missing.append('Jurisdiction is outside the TX/FL coverage review')
    return {'state': state, 'tax_year': 2026, 'status': 'partial',
            'components': components, 'sources': sources, 'missing_rules': missing}
