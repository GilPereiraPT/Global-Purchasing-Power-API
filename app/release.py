"""Immutable identity loaded once per application worker at startup."""
import re

from pathlib import Path

marker = Path(__file__).with_name('_release.py')
COMMIT = None
if marker.exists():
    match = re.fullmatch(r"COMMIT = ['\"]([0-9a-f]{40})['\"]\n", marker.read_text())
    if not match:
        raise ValueError('Invalid deployed release identity')
    COMMIT = match.group(1)


def ready():
    """Check the two local stores without calling external data providers."""
    import sqlite3
    from app.store import connect as wage_connect
    from app.country_insights_store import connect as economic_connect
    try:
        for connect, table in ((wage_connect, 'cache'), (economic_connect, 'observations')):
            db = connect()
            try:
                db.execute('SELECT 1 FROM ' + table + ' LIMIT 1').fetchone()
            finally:
                db.close()
    except (sqlite3.Error, OSError, ValueError):
        return False
    return True
