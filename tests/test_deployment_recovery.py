import io
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tarfile
import textwrap

import pytest
from scripts import deploy_runtime as runtime
from scripts import restore_earnwage_data as recovery

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def package(tmp_path):
    workflow = (ROOT / '.github/workflows/deploy-production.yml').read_text()
    block = workflow.split('- name: Build allow-listed runtime bundle', 1)[1]
    script = textwrap.dedent(block.split('run: |\n', 1)[1].split('\n      - name:', 1)[0].split('\n        env:', 1)[0])
    env = {**os.environ, 'GITHUB_OUTPUT': str(tmp_path / 'output'),
           'TESTED_SHA': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()}
    subprocess.run(['bash', '-euc', script], cwd=ROOT, env=env, check=True, capture_output=True)
    target = tmp_path / 'package.tgz'
    shutil.copyfile('/tmp/earnwage-runtime.tgz', target)
    return target


def create_db(path, value):
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE observations(value TEXT)')
        db.execute('INSERT INTO observations VALUES (?)', (value,))


def test_actual_package_clean_install_backup_and_data_recovery(package, tmp_path):
    root = tmp_path / 'clean'
    root.mkdir()
    runtime.install(root, package)
    files, _ = runtime.read_archive(package)
    assert runtime.REQUIRED <= files.keys()
    assert not any(n.endswith(('.sqlite3', '.env')) for n in files)
    db_a, db_b = tmp_path / 'insights.sqlite3', tmp_path / 'wages.sqlite3'
    create_db(db_a, 'verified insight')
    create_db(db_b, 'verified wage')
    env = {**os.environ, 'EARNWAGE_INSIGHTS_DB': str(db_a), 'GPP_CACHE_DB': str(db_b)}
    snapshot = tmp_path / 'backup'
    subprocess.run(['python3', '-m', 'scripts.backup_earnwage_data', '--output', str(snapshot)],
                   cwd=root, env=env, check=True, capture_output=True)
    restored = tmp_path / 'restored'
    subprocess.run(['python3', '-m', 'scripts.restore_earnwage_data', '--backup', str(snapshot),
                    '--output', str(restored)], cwd=root, env=env, check=True, capture_output=True)
    for name, expected in [('insights', 'verified insight'), ('wages_cache', 'verified wage')]:
        with sqlite3.connect(restored / (name + '.sqlite3')) as db:
            assert db.execute('SELECT value FROM observations').fetchone()[0] == expected
    assert env['GPP_CACHE_DB'] == str(db_b)
    assert set(p.name for p in (root / 'data').glob('*.json')) <= set(p.name for p in snapshot.glob('*.json'))
    (snapshot / 'insights.sqlite3').write_bytes(b'tampered')
    with pytest.raises(ValueError, match='checksum'):
        recovery.restore(snapshot, tmp_path / 'bad-recovery')
    assert not (tmp_path / 'bad-recovery').exists()
    with pytest.raises(ValueError, match='new private'):
        recovery.restore(snapshot, restored)


def test_runtime_recovery_preserves_private_files(package, tmp_path):
    root = tmp_path / 'server'
    (root / 'app').mkdir(parents=True)
    (root / 'app/native_wsgi.py').write_text('VERSION = "old"\n')
    private = {'.env': b'private configuration', 'db.sqlite3': b'live database', '.htaccess': b'hosting config'}
    for name, content in private.items():
        (root / name).write_bytes(content)
    backup = runtime.install(root, package)
    assert (root / 'app/native_wsgi.py').read_text() != 'VERSION = "old"\n'
    runtime.recover(root, backup)
    assert (root / 'app/native_wsgi.py').read_text() == 'VERSION = "old"\n'
    assert not (root / 'scripts/deploy_runtime.py').exists()
    assert (root / 'tmp/restart.txt').exists()
    for name, content in private.items():
        assert (root / name).read_bytes() == content


def test_install_failure_rolls_back_and_raises(package, tmp_path, monkeypatch):
    root = tmp_path / 'server'
    (root / 'app').mkdir(parents=True)
    (root / 'app/native_wsgi.py').write_text('VERSION = "old"\n')
    original = runtime.write_files
    calls = []
    def fail_once(root, files):
        calls.append(1)
        if len(calls) == 1:
            name = next(iter(files))
            original(root, {name: files[name]})
            raise OSError('simulated installation failure')
        original(root, files)
    monkeypatch.setattr(runtime, 'write_files', fail_once)
    with pytest.raises(OSError, match='simulated'):
        runtime.install(root, package)
    assert (root / 'app/native_wsgi.py').read_text() == 'VERSION = "old"\n'


@pytest.mark.parametrize('name', ['../outside.py', '.env', 'db.sqlite3', 'app/link.py'])
def test_malicious_archive_never_writes_private_files(tmp_path, name):
    archive = tmp_path / 'bad.tgz'
    with tarfile.open(archive, 'w:gz') as tar:
        member = tarfile.TarInfo(name)
        member.size = 4
        if name == 'app/link.py':
            member.type = tarfile.SYMTYPE
            member.linkname = '/tmp/private'
            member.size = 0
        tar.addfile(member, io.BytesIO(b'pass'))
    with pytest.raises(ValueError):
        runtime.install(tmp_path, archive)


def test_runtime_lock_prevents_overlapping_operations(tmp_path):
    with runtime.exclusive(tmp_path):
        with pytest.raises(BlockingIOError):
            with runtime.exclusive(tmp_path):
                pytest.fail('Concurrent installer acquired the same lock')


def test_obsolete_runtime_removed_and_recovered(package, tmp_path):
    root = tmp_path / 'server'
    (root / 'app').mkdir(parents=True)
    (root / 'app/obsolete.py').write_text('OLD = True\n')
    backup = runtime.install(root, package)
    assert not (root / 'app/obsolete.py').exists()
    runtime.recover(root, backup)
    assert (root / 'app/obsolete.py').read_text() == 'OLD = True\n'
