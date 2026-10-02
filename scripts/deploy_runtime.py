"""Install/recover runtime files only. Never replace databases or configuration."""
import argparse
from contextlib import contextmanager
import fcntl
import ast
import io
import json
import os
import subprocess
import re
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

MANIFEST = 'runtime-manifest.json'
REQUIRED = {'app/native_wsgi.py', 'passenger_wsgi.py', 'requirements.txt',
            'scripts/backup_earnwage_data.py', 'scripts/restore_earnwage_data.py',
            'scripts/deploy_runtime.py', 'scripts/verify_release.py',
            'app/release.py', 'app/_release.py'}


def allowed(name):
    p = PurePosixPath(name)
    return (p.as_posix() == name and not p.is_absolute() and '..' not in p.parts
            and not any(part.startswith('.') for part in p.parts) and
            ((len(p.parts) == 2 and p.parts[0] in ('app', 'scripts') and p.suffix == '.py')
             or (len(p.parts) == 2 and p.parts[0] == 'data' and p.suffix == '.json')
             or name in ('passenger_wsgi.py', 'requirements.txt')))


def safe_target(root, name):
    if not allowed(name):
        raise ValueError('Unsafe runtime path')
    target = root / name
    if any(p.is_symlink() for p in (target, *target.parents) if p != root.parent):
        raise ValueError('Symlink runtime path')
    return target


def read_archive(path, recovery=False):
    files, manifest = {}, None
    with tarfile.open(path, 'r:gz') as archive:
        for member in archive.getmembers():
            if not member.isfile() or member.size > 5_000_000:
                raise ValueError('Unsafe archive member')
            if member.name == MANIFEST and recovery:
                if manifest is not None:
                    raise ValueError('Duplicate manifest')
                manifest = json.load(archive.extractfile(member))
                continue
            if not allowed(member.name) or member.name in files:
                raise ValueError('Unexpected runtime file')
            if sum(map(len, files.values())) + member.size > 100_000_000:
                raise ValueError('Runtime archive too large')
            files[member.name] = archive.extractfile(member).read()
    if sum(map(len, files.values())) > 100_000_000:
        raise ValueError('Runtime archive too large')
    if not recovery and not REQUIRED <= files.keys():
        raise ValueError('Incomplete runtime package')
    for name, content in files.items():
        if name.endswith('.py'):
            ast.parse(content.decode('utf-8'))
        elif name.endswith('.json'):
            json.loads(content)
    if recovery:
        if (not isinstance(manifest, dict) or manifest.get('schema') != 1
                or not isinstance(manifest.get('installed'), list)
                or not all(isinstance(n, str) and allowed(n) for n in manifest['installed'])):
            raise ValueError('Invalid recovery manifest')
    return files, manifest


def write_files(root, files):
    for name, content in files.items():
        target = safe_target(root, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temp:
            temporary = Path(temp.name)
            temp.write(content)
        try:
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)


def _recover(root, backup):
    root = Path(root).resolve()
    files, manifest = read_archive(backup, recovery=True)
    for name in set(files) | set(manifest['installed']):
        safe_target(root, name)
    write_files(root, files)
    for name in set(manifest['installed']) - set(files):
        safe_target(root, name).unlink(missing_ok=True)
    restart(root)


def restart(root):
    directory = root / 'tmp'
    if directory.is_symlink() or (directory / 'restart.txt').is_symlink():
        raise ValueError('Unsafe restart path')
    directory.mkdir(exist_ok=True)
    (directory / 'restart.txt').touch()


def _install(root, package):
    root = Path(root).resolve()
    files, _ = read_archive(package)
    for name in files:
        safe_target(root, name)
    old = {}
    for directory, pattern in [('app', '*.py'), ('scripts', '*.py'), ('data', '*.json')]:
        for path in (root / directory).glob(pattern):
            name = path.relative_to(root).as_posix()
            old[name] = safe_target(root, name).read_bytes()
    for name in ('passenger_wsgi.py', 'requirements.txt'):
        path = safe_target(root, name)
        if path.is_file():
            old[name] = path.read_bytes()
    backup_dir = root / '_earnwage_backups'
    if backup_dir.is_symlink():
        raise ValueError('Unsafe backup directory')
    backup_dir.mkdir(mode=0o700, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = backup_dir / ('code-predeploy-' + stamp + '.tgz')
    with tarfile.open(backup, 'w:gz') as archive:
        for name, content in {**old, MANIFEST: json.dumps({'schema': 1, 'installed': list(files)}).encode()}.items():
            member = tarfile.TarInfo(name)
            member.size = len(content)
            member.mode = 0o600
            archive.addfile(member, io.BytesIO(content))
    os.chmod(backup, 0o600)
    try:
        write_files(root, files)
        for name in set(old) - set(files):
            safe_target(root, name).unlink()
        restart(root)
    except Exception:
        _recover(root, backup)
        raise
    return backup


@contextmanager
def exclusive(root):
    root = Path(root).resolve()
    if 'public_html' in root.parts:
        raise ValueError('Runtime backups require a private application root')
    directory = root / '_earnwage_backups'
    if directory.is_symlink():
        raise ValueError('Unsafe backup directory')
    directory.mkdir(mode=0o700, exist_ok=True)
    lock_path = directory / '.runtime-deploy.lock'
    if lock_path.is_symlink():
        raise ValueError('Unsafe deployment lock')
    with lock_path.open('a+b') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def install(root, package):
    with exclusive(root):
        return _install(root, package)


def recover(root, backup):
    with exclusive(root):
        _recover(root, backup)


def build(root, archive, commit):
    root = Path(root).resolve()
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Invalid release commit')
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    if actual != commit:
        raise ValueError('Checkout differs from tested commit')
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    names = [name for name in tracked if allowed(name) and name != 'app/_release.py']
    files = {name: safe_target(root, name).read_bytes() for name in names}
    files['app/_release.py'] = ('COMMIT = ' + repr(commit) + '\n').encode()
    if not REQUIRED <= files.keys():
        raise ValueError('Missing required runtime files')
    with tarfile.open(archive, 'w:gz') as tar:
        for name, content in files.items():
            member = tarfile.TarInfo(name)
            member.size = len(content)
            member.mode = 0o644
            tar.addfile(member, io.BytesIO(content))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['build', 'install', 'recover'])
    parser.add_argument('--root', required=True)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--commit')
    args = parser.parse_args()
    if args.action == 'build':
        build(args.root, args.archive, args.commit or '')
        return
    if args.action == 'install':
        print(install(args.root, args.archive).name)
    else:
        recover(args.root, args.archive)
        print('Runtime recovered; restart requested; verify health before resuming traffic.')


if __name__ == '__main__':
    main()
