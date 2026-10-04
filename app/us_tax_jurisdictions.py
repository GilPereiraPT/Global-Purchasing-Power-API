"""TX/FL rule coverage, distinct from a complete employee contribution model.

Only previously reviewed official rule parameters may produce scoped zeroes.
Unknown local charges or employment coverage never inherit the state zero.
"""
import re
from app.us_tax_evidence import sources_for

RULES = {
    'TX': {
        'employee_unemployment_contribution': ('https://tcss.legis.texas.gov/resources/LA/htm/LA.204.htm',
            'Sections 204.002/204.003: employer UI contributions may not be deducted from employee wages'),
        'employee_workers_compensation_contribution': ('https://tcss.legis.texas.gov/resources/LA/htm/LA.415.htm',
            'Section 415.006: employee premium/fee chargebacks prohibited, except 406.123/406.144; explicit exception exclusion required'),
        'state_income_tax_final': ('https://tlc.texas.gov/docs/legref/TxConst.pdf',
                                   'Article VIII section 24-a: individual net-income tax prohibition'),
    },
    'FL': {
        'employee_workers_compensation_contribution': ('https://www.flsenate.gov/Laws/Statutes/2026/440.21',
            'Section 440.21(1): employee financing of employer compensation premiums/statutory benefit funds is invalid'),
        'state_income_tax_final': ('https://www.flsenate.gov/Laws/Statutes/2026/220.02',
                                   'Section 220.02: natural-person income-tax exclusion'),
        'employee_reemployment_contribution': ('https://www.flsenate.gov/Laws/Statutes/2026/443.041',
                                               'Section 443.041: employer contributions cannot be financed by employee deductions'),
    },
}
PRIVATE_INSURANCE_RULES = {
    'TX': ('https://tcss.legis.texas.gov/resources/IN/htm/IN.1255.htm',
           'https://www.tdi.texas.gov/bulletins/2023/B-0012-23.html'),
    'FL': ('https://www.flsenate.gov/Laws/Statutes/2026/624.6086',
           'https://www.flsenate.gov/Laws/Statutes/2026/627.445'),
}

UNKNOWN = ('local_income_tax', 'employee_paid_leave_contribution', 'mandatory_state_employee_contributions')
WORKERS_COMP_FACTS = ('employment_type', 'workers_compensation_exception_agreement')
SCOPED_EMPLOYEE_RULES = frozenset({'employee_unemployment_contribution',
                                 'employee_workers_compensation_contribution'})


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


def coverage(state, facts=None):
    """Fresh metadata, no IO or DB mutation; wage-only full-year resident scope."""
    facts = facts or {}
    rules = RULES.get(state, {})
    components, sources = [], []
    for name, (url, rule) in rules.items():
        source = sources_for((url,))[0]
        reviewed = _reviewed_parameter(source, url)
        scoped = name not in SCOPED_EMPLOYEE_RULES or facts.get('employment_type') == 'ordinary_private_employee'
        if name == 'employee_workers_compensation_contribution':
            scoped = scoped and facts.get('workers_compensation_exception_agreement') is False
        eligible = reviewed and scoped
        components.append({'name': name, 'amount': '0.00' if eligible else None,
                           'status': 'reviewed_rule_parameter' if eligible else 'facts_required' if reviewed else 'unavailable',
                           'rule': rule, 'source_url': url})
        sources.append(source)
    if state == 'TX':
        sources.extend(sources_for(('https://tcss.legis.texas.gov/resources/LA/htm/LA.406.htm',)))
    private_sources = sources_for(PRIVATE_INSURANCE_RULES.get(state, ()))
    private_reviewed = (bool(private_sources)
                        and len(private_sources) == len(PRIVATE_INSURANCE_RULES.get(state, ()))
                        and all(
        _reviewed_parameter(source, url) for source, url in
        zip(private_sources, PRIVATE_INSURANCE_RULES.get(state, ()))))
    sources.extend(private_sources)
    if state == 'FL':
        sources.extend(sources_for(('https://www.floridarevenue.com/faq/Pages/FAQDetails.aspx?FAQID=1466',)))
    components.extend({'name': name, 'amount': None, 'status': 'unavailable'}
                      for name in UNKNOWN)
    missing = [
        'Official local wage-tax/non-applicability evidence for residence and work jurisdiction',
        '2026 public paid leave/disability employee contribution applicability remains unvalidated; private insurance rules do not establish existence or absence of a public levy',
        'Mandatory employee contribution applicability: private/public employment, retirement and special regimes; no zero inferred',
        'Explicit full-year same-state residence/work and ordinary private-sector employment scope required before net activation',
    ]
    if state == 'TX':
        missing.append('Texas Tax Code 302 is NOT an income-tax prohibition; local wage-tax authority remains unvalidated')
    if state == 'FL':
        missing.append('Florida local salary-tax applicability remains unvalidated; 2026-45 environmental amendment effective 2026-07-01 was reviewed through enrolled text and official legislative history, not as a salary-tax rule')
    if facts.get('employment_type') != 'ordinary_private_employee':
        missing.append('Explicit ordinary_private_employee employment_type required for newly reviewed employee contribution rules; contracting/public/special regimes excluded')
    if facts.get('workers_compensation_exception_agreement') is not False:
        missing.append('Explicit false workers_compensation_exception_agreement required; Texas 406.123/406.144 deductions must not be inferred zero')
    if state not in ('TX','FL'):
        missing.append('Jurisdiction is outside the TX/FL coverage review')
    return {'state': state, 'tax_year': 2026, 'status': 'partial',
            'components': components, 'sources': sources, 'missing_rules': missing,
            'required_employee_contribution_facts': list(WORKERS_COMP_FACTS),
            'assumptions': ['Conditional state components assume selected state law governs the employment; multistate residence/work remains unvalidated',
                            'Ordinary private employee; voluntary benefits are excluded, not asserted to cost zero'],
            'private_family_leave_insurance': {
                'status': 'reviewed_private_insurance_rules' if private_reviewed else 'unavailable',
                'kind': 'private_employer_group_insurance',
                'these_rules_create_universal_public_employee_contribution': False if private_reviewed else None,
                'public_contribution_applicability': 'not_established_by_these_documents',
                'premium_amount': None,
                'benchmark_treatment': 'Before private benefit premiums; not an assertion that premiums cost zero or that individual contracts are optional',
                'source_urls': list(PRIVATE_INSURANCE_RULES.get(state, ()))},
            'evidence_limitations': ['Missing evidence is not evidence that a levy exists; no presumed public contribution is calculated'],
            'employee_contribution_scope': 'Ordinary private employee only; no independent-contractor/subcontractor/owner-operator coverage agreement; no public or special occupational regime'}
