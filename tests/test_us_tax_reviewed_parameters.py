"""Official pre-credit table anchors, not official final tax returns."""
from decimal import Decimal as D
import pytest
from app.tax_us import illustrations, SCENARIO
from app.tax_engine import calculate, metadata, source_evidence_complete
from app.us_tax_evidence import sources_for
from app.us_tax_california import calculate as california
from app.us_tax_pennsylvania import calculate as pennsylvania
from app.us_tax_new_york import calculate as new_york


@pytest.mark.parametrize('taxable,base', [
    ('12400','1240'), ('50400','5800'), ('105700','17966'),
    ('201775','41024'), ('256225','58448'), ('640600','192979.25'),
])
def test_irs_rev_proc_2025_32_table3_statutory_anchors(taxable, base):
    # Published accumulated amounts independently check marginal integration.
    result = dict(illustrations(D(taxable) + D('16100')))
    assert result['federal_schedule_before_credits'] == D(base)


def test_parameter_evidence_does_not_authorize_complete_net():
    result = calculate('US', '100000', 2026, SCENARIO, 'TX')
    assert all(s['verification_status'] == 'parameters_reviewed' for s in result['sources'])
    assert all(len(s['sha256']) == 64 and s['bytes'] > 0 for s in result['sources'])
    assert not source_evidence_complete(result['sources'], 2026)
    assert result['net_income'] is result['income_tax'] is None
    assert metadata('US')['reviewed_parameter_tax_years'] == [2026]
    assert metadata('US')['supported_tax_years'] == []
    assert metadata('US')['benchmark_tax_years'] == []


def test_state_parameter_review_is_scoped_and_missing_rules_stay_unknown():
    ca = california('100000')
    pa = pennsylvania('100000', taxable_compensation='90000')
    ny = new_york('100000')
    assert ca['components'][0]['amount'] == '1300.00'
    assert pa['components'][0]['amount'] == '2763.00'
    assert ca['sources'][-1]['verification_status'] == 'parameters_reviewed'
    assert pa['sources'][0]['verification_status'] == 'parameters_reviewed'
    assert ny['sources'][0]['verification_status'] == 'blocked'
    assert '403' in ny['sources'][0]['error']
    for result in (ca, pa, ny):
        assert result['income_tax'] is result['employee_contributions'] is result['net_income'] is None
        assert all(c['amount'] is None for c in result['components'][1:])


def test_unknown_rule_and_metadata_mutation_cannot_reuse_a_review():
    url = 'https://www.irs.gov/publications/p15'
    first = sources_for((url,))[0]
    first['verification_status'] = 'verified'
    assert sources_for((url,))[0]['verification_status'] == 'parameters_reviewed'
    unknown = sources_for(('https://www.irs.gov/unreviewed',))[0]
    assert unknown['verification_status'] == 'blocked' and 'sha256' not in unknown
