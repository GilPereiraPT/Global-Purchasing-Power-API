"""TX/FL rule coverage, distinct from a complete employee contribution model.

Only previously reviewed official rule parameters may produce scoped zeroes.
Unknown local charges or employment coverage never inherit the state zero.
"""
import re
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


def _reviewed_parameter(source, expected_url):
    """A scoped zero needs intact evidence for this exact rule, not a placeholder.

    Metadata checks cannot replace legal review or prove raw-source integrity.
    They only reject incomplete, malformed or unrelated review declarations.
    """
    return (source.get('verification_status') == 'parameters_reviewed'
            and type(source.get('tax_year')) is int and source['tax_year'] == 2026
            and source.get('status') == 200
            and source.get('url') == expected_url
            and isinstance(source.get('scope'), str) and bool(source['scope'].strip())
            and type(source.get('bytes')) is int and source['bytes'] > 0
            and isinstance(source.get('sha256'), str)
            and re.fullmatch(r'[0-9a-f]{64}', source['sha256']) is not None)


def coverage(state):
    """Fresh metadata, no IO or DB mutation; wage-only full-year resident scope."""
    rules = RULES.get(state, {})
    components, sources = [], []
    for name, (url, rule) in rules.items():
        source = sources_for((url,))[0]
        reviewed = _reviewed_parameter(source, url)
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
