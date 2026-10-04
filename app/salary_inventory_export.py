"""Shared read-only salary exporter for authenticated Data Manager and offline CLI.

Standard library only; no application initialization, credentials, network or
publication. Raw rows preserve target identities for offline normalization.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import re
from pathlib import Path
import shutil
import sqlite3
import time
from urllib.parse import urlsplit

SCHEMA = 'earnwage-salary-table-inventory-v1'
MAX_BYTES = 100 * 1024 * 1024
MAX_ROWS = 200_000
TIMEOUT_SECONDS = 30
PRIMARY_KEYS = {
    'nl_cbs_wages': ('country', 'occupation', 'reference_period', 'source'),
    'us_oews': ('reference_period', 'source_file', 'area', 'area_type',
        'prim_state', 'naics', 'i_group', 'own_code', 'occ_code'),
    'north_america_wages': ('country', 'occupation', 'geography', 'classification',
        'reference_period', 'measure', 'source'),
    'ca_province_wages': ('occupation', 'province', 'classification',
        'reference_period', 'measure', 'source'),
}
TABLE_COLUMNS = {
    'nl_cbs_wages': ('country', 'occupation', 'geography', 'reference_period',
        'publication_status', 'currency', 'measure', 'unit', 'value', 'source',
        'source_url', 'source_page', 'dataset', 'classification', 'brc_code',
        'cbs_identifier', 'brc_label', 'employees_thousand', 'salary_concept', 'precision'),
    'us_oews': ('reference_period', 'published_year', 'source_file', 'area',
        'area_title', 'area_type', 'prim_state', 'naics', 'naics_title', 'i_group',
        'own_code', 'occ_code', 'occ_title', 'o_group', 'h_mean', 'a_mean',
        'h_pct10', 'h_pct25', 'h_median', 'h_pct75', 'h_pct90',
        'a_pct10', 'a_pct25', 'a_median', 'a_pct75', 'a_pct90', 'source_url'),
    'north_america_wages': ('country', 'occupation', 'geography', 'classification',
        'job_title', 'reference_period', 'published_year', 'currency', 'measure',
        'unit', 'value', 'source', 'source_url'),
    'ca_province_wages': ('occupation', 'province', 'classification', 'job_title',
        'reference_period', 'published_year', 'measure', 'unit', 'value',
        'source', 'source_url'),
}


def digest(path, deadline=None):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError('Inventory export timeout')
            result.update(chunk)
    return result.hexdigest()


def private_path(value):
    path = Path(value)
    if not path.is_absolute() or 'public_html' in path.parts:
        raise ValueError('An absolute private path outside public_html is required')
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Symlink paths are not permitted')
    return path


def safe_record(record, forbidden_values):
    # Raw identity metadata must never export stored local filenames/credentials.
    filename = record.get('source_file', '')
    if not isinstance(filename, str) or any(c in filename for c in ('/', '\\', '\x00')):
        raise ValueError('Unsafe stored source filename')
    for field, value in record.items():
        if (field == 'value' or field.startswith(('h_', 'a_'))) and value is not None:
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError('Invalid stored numeric salary')
    url = urlsplit(record['source_url'])
    if (url.scheme != 'https' or url.hostname not in
        ('www.bls.gov', 'open.canada.ca', 'opencanada.blob.core.windows.net', 'datasets.cbs.nl')
        or url.username or url.password or url.query or url.fragment
        or url.port not in (None, 443)):
        raise ValueError('Unsafe stored source URL')
    if url.hostname == 'datasets.cbs.nl' and url.path != '/odata/v1/CBS/86355NED':
        raise ValueError('Unsafe stored CBS dataset URL')
    if 'source_page' in record and record['source_page'] != 'https://www.cbs.nl/nl-nl/cijfers/detail/86355NED':
        raise ValueError('Unsafe stored CBS source page')
    employees = record.get('employees_thousand')
    if 'employees_thousand' in record and (isinstance(employees, bool) or not isinstance(employees, (int, float)) or not math.isfinite(employees) or employees <= 0):
        raise ValueError('Invalid stored CBS employee count')
    for value in record.values():
        if isinstance(value, str) and any(secret and secret in value for secret in forbidden_values):
            raise ValueError('Sensitive stored salary metadata')
    for field, value in record.items():
        if field not in ('source_url', 'source_page') and isinstance(value, str) and re.search(r'(^|\s)/\S|[A-Za-z]:[\\/]', value):
            raise ValueError('Private path in stored salary metadata')


def export(database, output, *, authorization, deadline=None, forbidden_values=()):
    if not isinstance(authorization, str) or not authorization.strip():
        raise ValueError('Owner authorization reference required; never supply a token')
    source, destination = private_path(database), private_path(output)
    if not source.is_file():
        raise ValueError('Existing wage database required')
    if destination.exists() or not destination.parent.is_dir():
        raise ValueError('Choose a new directory inside an existing private parent')
    if destination.parent.stat().st_mode & 0o077:
        raise ValueError('Export parent must have private permissions (0700)')
    if shutil.disk_usage(destination.parent).free < MAX_BYTES + 64 * 1024 * 1024:
        raise OSError('Insufficient free space for bounded inventory export')
    deadline = deadline if deadline is not None else time.monotonic() + TIMEOUT_SECONDS
    forbidden_values = (*forbidden_values, str(source))
    if len(source.parent.parts) > 1:
        forbidden_values += (str(source.parent),)
    def check_deadline():
        if time.monotonic() >= deadline:
            raise TimeoutError('Inventory export timeout; no partial inventory is usable')
    manifest = {
        'schema': SCHEMA, 'exported_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'all_rows_of_listed_salary_tables_only',
        'authorization_reference': authorization.strip(),
        'sqlite_version': sqlite3.sqlite_version,
        'database_bytes': source.stat().st_size,
        'wal_bytes': Path(str(source) + '-wal').stat().st_size
            if Path(str(source) + '-wal').is_file() else 0,
        'tables': {},
        'note': 'Raw target-model inventory, not a normalized observation inventory. '
                'Normalize offline before comparing; do not claim complete global coverage.',
    }
    destination.mkdir(mode=0o700)
    total_bytes = total_rows = 0
    try:
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=5)) as db:
            db.execute('PRAGMA query_only=ON')
            db.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
            db.execute('BEGIN')  # One consistent read transaction across all tables.
            objects = dict(db.execute('SELECT name,type FROM sqlite_master'))
            for table, columns in TABLE_COLUMNS.items():
                check_deadline()
                if table not in objects:
                    manifest['tables'][table] = {'status': 'absent', 'rows': 0}
                    continue
                if objects[table] != 'table':
                    raise ValueError('Expected salary table, not a view')
                info = db.execute('PRAGMA table_info(' + table + ')').fetchall()
                if not set(columns) <= {r[1] for r in info}:
                    raise ValueError('Unrecognized salary schema; stop and review offline')
                primary = [r[1] for r in sorted((r for r in info if r[5]), key=lambda r:r[5])]
                if tuple(primary) != PRIMARY_KEYS[table]:
                    raise ValueError('Unrecognized salary primary key')
                filename = table + '.json'
                count = 0
                target = destination / filename
                descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, 'wb') as stream:
                    def write(raw):
                        nonlocal total_bytes
                        total_bytes += len(raw)
                        if total_bytes > MAX_BYTES:
                            raise ValueError('Inventory exceeds 100 MiB export limit')
                        stream.write(raw)
                    write(b'{"records":[')
                    # Only fixed salary columns, never cache/users/environment tables.
                    for values in db.execute('SELECT ' + ','.join(columns) + ' FROM ' + table):
                        check_deadline()
                        count += 1
                        total_rows += 1
                        if total_rows > MAX_ROWS:
                            raise ValueError('Inventory exceeds row limit')
                        record = dict(zip(columns, values))
                        safe_record(record, forbidden_values)
                        raw = json.dumps(record, allow_nan=False,
                            ensure_ascii=False, separators=(',', ':')).encode()
                        write((b',' if count > 1 else b'') + raw)
                    write(b']}\n')
                manifest['tables'][table] = {
                    'status': 'exported', 'file': filename, 'rows': count,
                    'bytes': target.stat().st_size, 'columns': list(columns),
                    'primary_key': primary,
                    'sha256': digest(target, deadline),
                }
            db.rollback()
        check_deadline()
        manifest['total_rows'] = total_rows
        manifest['total_bytes'] = total_bytes
        path = destination / 'manifest.json'
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        return manifest
    except BaseException:
        shutil.rmtree(destination)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wages-db', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--authorization', required=True)
    args = parser.parse_args()
    result = export(args.wages_db, args.output, authorization=args.authorization)
    print(json.dumps({'status': 'exported', 'tables': result['tables'],
                      'total_rows': result['total_rows']}))


if __name__ == '__main__':
    main()
