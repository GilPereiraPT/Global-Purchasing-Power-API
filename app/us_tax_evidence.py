"""Reviewed parameter evidence is never evidence of a complete tax outcome."""
import json
from pathlib import Path

_REVIEW = json.loads((Path(__file__).resolve().parents[1] /
                     'data/us_tax_2026_source_evidence.json').read_text())


def sources_for(urls):
    """Return fresh audit metadata; do not promote parameters to verified tax."""
    def canonical(url):
        return url.lower().rstrip('/')
    index = {canonical(row['url']): row for row in _REVIEW['sources']}
    result = []
    for url in urls:
        row = index.get(canonical(url))
        if row is None:
            row = {'url': url, 'tax_year': 2026, 'verification_status': 'blocked',
                   'scope': 'Unreviewed rule candidate',
                   'reason': 'No official source snapshot reviewed for this rule'}
        result.append(dict(row))
    return tuple(result)
