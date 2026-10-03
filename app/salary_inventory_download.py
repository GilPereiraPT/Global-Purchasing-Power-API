"""Private, bounded ZIP response; no public URLs or persisted download tokens."""
import hashlib
import logging
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from app import salary_inventory_export as inventory

LOG = logging.getLogger('earnwage.salary_inventory')
CHUNK_BYTES = 65536
ORPHAN_SECONDS = 15 * 60
DOWNLOAD_SECONDS = 5 * 60
MAX_PENDING = 4
ZIP_OVERHEAD = 1024 * 1024


def cleanup_stale(root):
    """Only our reserved temporary directories, under the private export root."""
    cutoff = time.time() - ORPHAN_SECONDS
    for path in root.iterdir():
        if (re.fullmatch(r'export-[a-z0-9_]{8}', path.name) and not path.is_symlink()
            and path.is_dir() and path.stat().st_mtime < cutoff):
            shutil.rmtree(path)


class Download:
    """WSGI iterable owns its temporary directory until exhausted or closed."""
    def __init__(self, directory, archive, checksum):
        self.directory = directory
        self.size = archive.stat().st_size
        self.checksum = checksum
        self.file = archive.open('rb')
        self.closed = False
        self.sent = 0
        self.deadline = time.monotonic() + DOWNLOAD_SECONDS

    def response(self, start_response, origin):
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        headers = [
            ('Content-Type', 'application/zip'), ('Content-Length', str(self.size)),
            ('Content-Disposition', 'attachment; filename="earnwage-salary-inventory-' + stamp + '.zip"'),
            ('Cache-Control', 'private, no-store, max-age=0'), ('Pragma', 'no-cache'),
            ('X-Content-Type-Options', 'nosniff'), ('Vary', 'Origin'),
            ('X-EarnWage-Inventory-SHA256', self.checksum),
        ]
        if origin:
            headers.extend([
                ('Access-Control-Allow-Origin', origin),
                ('Access-Control-Expose-Headers',
                 'Content-Disposition, Content-Length, X-EarnWage-Inventory-SHA256'),
            ])
        try:
            start_response('200 OK', headers)
        except BaseException:
            self.close()
            raise
        return self

    def __iter__(self):
        return self

    def __next__(self):
        if self.closed:
            raise StopIteration
        try:
            if time.monotonic() >= self.deadline:
                raise TimeoutError('Inventory download timeout')
            chunk = self.file.read(CHUNK_BYTES)
            if not chunk:
                if self.sent != self.size:
                    raise OSError('Incomplete inventory download')
                self.close()
                raise StopIteration
            self.sent += len(chunk)
            if self.sent > self.size:
                raise OSError('Unexpected inventory download size')
            return chunk
        except BaseException:
            self.close()
            raise

    def close(self):
        if not self.closed:
            self.closed = True
            try:
                self.file.close()
            except OSError as error:
                LOG.warning('Inventory download close failed (%s)', type(error).__name__)
            try:
                shutil.rmtree(self.directory)
            except OSError as error:
                # No paths/credentials in logs; next authorized export retries GC.
                LOG.warning('Inventory temporary cleanup failed (%s)', type(error).__name__)


def prepare(database, root, *, forbidden_values=()):
    """Called under the existing Data Manager operation lock, after admin auth."""
    root = inventory.private_path(root)
    if not root.parent.is_dir() or root.parent.stat().st_mode & 0o077:
        raise ValueError('Private export parent required')
    root.mkdir(mode=0o700, exist_ok=True)
    if not root.is_dir() or root.stat().st_mode & 0o077:
        raise ValueError('Private export directory required')
    cleanup_stale(root)
    pending = sum(1 for p in root.iterdir() if
        re.fullmatch(r'export-[a-z0-9_]{8}', p.name) and p.is_dir())
    if pending >= MAX_PENDING:
        raise RuntimeError('too_many_inventory_downloads')
    required = 2 * inventory.MAX_BYTES + ZIP_OVERHEAD + 64 * 1024 * 1024
    if shutil.disk_usage(root).free < required:
        raise OSError('insufficient_inventory_disk_space')
    deadline = time.monotonic() + inventory.TIMEOUT_SECONDS
    directory = Path(tempfile.mkdtemp(prefix='export-', dir=root))
    try:
        report = inventory.export(database, directory / 'rows',
            authorization='authenticated_data_manager_read_only_export',
            deadline=deadline, forbidden_values=forbidden_values)
        archive = directory / 'inventory.zip'
        members = {'manifest.json': None}
        for table, record in report['tables'].items():
            if record['status'] == 'exported':
                members[table + '.json'] = record['sha256']
        descriptor = os.open(archive, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'wb') as output:
            with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipped:
                for name, expected in members.items():
                    info = zipfile.ZipInfo(name)
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o600 << 16
                    digest = hashlib.sha256()
                    with (directory / 'rows' / name).open('rb') as source, zipped.open(info, 'w') as target:
                        for chunk in iter(lambda: source.read(CHUNK_BYTES), b''):
                            if time.monotonic() >= deadline:
                                raise TimeoutError('Inventory export timeout')
                            target.write(chunk)
                            digest.update(chunk)
                    if expected is not None and digest.hexdigest() != expected:
                        raise ValueError('Inventory checksum mismatch')
        if archive.stat().st_size > inventory.MAX_BYTES + ZIP_OVERHEAD:
            raise ValueError('Inventory archive exceeds byte limit')
        checksum = inventory.digest(archive, deadline)
        return Download(directory, archive, checksum)
    except BaseException:
        shutil.rmtree(directory)
        raise
