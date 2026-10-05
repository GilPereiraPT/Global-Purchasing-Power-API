"""National consumption-PPP equivalent of a user-entered annual gross wage."""
import math
from app.catalog import COUNTRY_MAP
from app.country_insights import indicator


def _positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def coverage():
    rows = []
    for code, country in COUNTRY_MAP.items():
        data = indicator(code, 'ppp_private_consumption', history=True)
        years = sorted({r['year'] for r in data.get('history', []) if _positive(r.get('value'))}, reverse=True)
        rows.append({'country': code, 'currency': country['currency'], 'years': years,
                     'status': 'available' if years else 'not_imported', 'scope': 'national'})
    return {'countries': rows, 'indicator_code': 'PA.NUS.PRVT.PP', 'scope': 'national',
            'note': 'A pair requires a common observation year; national PPP does not measure regional prices.'}


def equivalent(country_a, country_b, annual_gross, year=None):
    a, b = str(country_a).upper(), str(country_b).upper()
    if a not in COUNTRY_MAP or b not in COUNTRY_MAP:
        raise ValueError('Unsupported country')
    if not _positive(annual_gross) or annual_gross > 100000000:
        raise ValueError('annual_gross must be finite, positive and at most 100000000')
    if year is not None and (type(year) is not int or not 1960 <= year <= 2100):
        raise ValueError('year must be between 1960 and 2100')
    sources = [indicator(code, 'ppp_private_consumption', history=True) for code in (a, b)]
    series = [{r['year']: r['value'] for r in source.get('history', []) if _positive(r.get('value'))}
              for source in sources]
    common = sorted(series[0].keys() & series[1].keys(), reverse=True)
    selected = year if year is not None else (common[0] if common else None)
    result = {'country_a': a, 'country_b': b, 'annual_gross': annual_gross,
              'currency_a': COUNTRY_MAP[a]['currency'], 'currency_b': COUNTRY_MAP[b]['currency'],
              'status': 'partial', 'equivalent_annual_gross': None, 'equivalent_monthly_12': None,
              'international_dollars': None, 'year': selected, 'available_common_years': common,
              'scope': 'national', 'indicator_code': 'PA.NUS.PRVT.PP',
              'method': 'annual_gross / consumption_ppp_a * consumption_ppp_b',
              'net_salary': {'status': 'not_calculated', 'value': None},
              'sources': [{k: s.get(k) for k in ('country', 'source', 'source_url', 'last_successful_refresh')}
                          for s in sources],
              'context': {code: {'inflation': indicator(code, 'inflation_annual')}
                          for code in dict.fromkeys((a, b))},
              'warnings': ['Approximate gross consumption-PPP equivalence, not net disposable income or a job offer.',
                           'National averages do not estimate regional housing costs or personal spending.',
                           'Amounts use the PPP reference-year price structure; no inflation extrapolation.',
                           'Monthly display is annual / 12, not contractual payments.']}
    if selected not in common:
        result['reason'] = 'No positive consumption PPP observations for both countries in the same year.'
        return result
    pa, pb = series[0][selected], series[1][selected]
    value = annual_gross / pa * pb
    result.update(status='partial_estimate', equivalent_annual_gross=round(value, 2),
                  equivalent_monthly_12=round(value / 12, 2), international_dollars=round(annual_gross / pa, 2),
                  ppp_a=pa, ppp_b=pb)
    return result
