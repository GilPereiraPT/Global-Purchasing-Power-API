"""Bounded private package intake; never opens salary databases or publishes."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from app import bulk_publication as bulk
from app.salary_inventory_export import private_path

MAX_PACKAGES = 20
RESERVE_BYTES = 64 * 1024 * 1024


def _unique(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def accept(environ, backup_dir):
    """Called under the authenticated Data Manager's cross-worker lock."""
    if environ.get('CONTENT_TYPE', '').split(';')[0].strip().lower() != 'application/json':
        raise ValueError('JSON content type required')
    size = int(environ.get('CONTENT_LENGTH', '0') or '0')
    if not 0 < size <= bulk.MAX_BYTES:
        raise ValueError('Invalid package length')
    checksum = environ.get('HTTP_X_EARNWAGE_PACKAGE_SHA256', '')
    if not re.fullmatch('[0-9a-f]{64}', checksum):
        raise ValueError('Expected checksum required')
    raw = environ['wsgi.input'].read(size)
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != checksum:
        raise ValueError('Package integrity mismatch')
    package = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique,
                         parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    bulk.validate(package)
    targets = bulk._targets(package)
    if raw != bulk.encode(package):
        raise ValueError('Canonical package required')
    root = private_path(backup_dir)
    directory = private_path(root / 'bulk-packages')
    for path in (root, directory):
        path.mkdir(mode=0o700, exist_ok=True)
        if not path.is_dir() or path.stat().st_mode & 0o077:
            raise ValueError('Private package permissions required')
    target = directory / (checksum + '.json')
    if target.exists() or target.is_symlink():
        raise FileExistsError('Package already stored')
    if len(list(directory.iterdir())) >= MAX_PACKAGES:
        raise RuntimeError('package_storage_limit')
    if shutil.disk_usage(directory).free < size + RESERVE_BYTES:
        raise RuntimeError('package_space_insufficient')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix='.upload-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        # Atomic exclusive creation: no window exposes an incomplete accepted file.
        os.link(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {'status': 'package_stored', 'checksum': checksum, 'bytes': size,
            'observations': len(package['observations']),
            'target_rows': len(targets),
            'publication_authorized': False}
