from io import BytesIO
import json
from pathlib import Path
import subprocess
import pytest
from app import main, native_wsgi
from scripts import verify_release as verifier
from scripts import deploy_runtime as runtime

SHA = 'a' * 40


@pytest.mark.parametrize('changes', [{'commit': 'b' * 40}, {'status': 'error'}, {'version': 'old'}, {'commit': None}])
def test_wrong_release_or_unhealthy_is_rejected(changes):
    payload = {'commit': SHA, 'status': 'ok', 'version': '0.5.20', **changes}
    assert not verifier.healthy(payload, SHA, '0.5.20')


def test_verifier_retries_and_never_reports_failure_as_success(monkeypatch):
    class Response(BytesIO):
        status = 200
    calls = []
    def wrong(request, timeout):
        calls.append(1)
        return Response(json.dumps({'status': 'ok', 'version': '0.5.20', 'commit': 'b' * 40}).encode())
    monkeypatch.setattr(verifier, 'urlopen', wrong)
    monkeypatch.setattr(verifier.time, 'sleep', lambda n: None)
    with pytest.raises(RuntimeError, match='verification failed'):
        verifier.verify('https://example.invalid/health', SHA, '0.5.20', attempts=2)
    assert len(calls) == 2
    monkeypatch.setattr(verifier, 'urlopen', lambda *a, **k: Response(json.dumps({'status': 'ok', 'version': '0.5.20', 'commit': SHA}).encode()))
    verifier.verify('https://example.invalid/health', SHA, '0.5.20', attempts=1)


def test_both_adapters_identify_commit_and_reject_unready_store(monkeypatch):
    for adapter in (main, native_wsgi):
        monkeypatch.setattr(adapter, 'COMMIT', SHA)
        monkeypatch.setattr(adapter, 'ready', lambda: True)
    assert main.health()['commit'] == SHA
    assert native_wsgi.dispatch('/v1/health', {})['commit'] == SHA
    monkeypatch.setattr(main, 'ready', lambda: False)
    monkeypatch.setattr(native_wsgi, 'ready', lambda: False)
    with pytest.raises(main.HTTPException) as failed:
        main.health()
    assert failed.value.status_code == 503
    with pytest.raises(native_wsgi.ApiError) as failed:
        native_wsgi.dispatch('/v1/health', {})
    assert failed.value.code == 503


def test_package_commit_is_generated_without_editing_checkout(tmp_path):
    root = Path(__file__).resolve().parents[1]
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    archive = tmp_path / 'release.tgz'
    runtime.build(root, archive, sha)
    files, _ = runtime.read_archive(archive)
    assert files['app/_release.py'] == ('COMMIT = ' + repr(sha) + '\n').encode()
    assert not (root / 'app/_release.py').exists()
    with pytest.raises(ValueError, match='differs'):
        runtime.build(root, archive, '0' * 40)


def test_ready_rejects_corrupt_database(tmp_path, monkeypatch):
    from app import release, store
    database = tmp_path / 'bad.sqlite'
    database.write_bytes(b'not a database')
    monkeypatch.setattr(store, 'DB_PATH', str(database))
    assert release.ready() is False


def test_browser_install_requests_restart_and_embeds_exact_sha(tmp_path, monkeypatch):
    import io
    import zipfile
    from app import data_manager as dm
    root = Path(__file__).resolve().parents[1]
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    package = tmp_path / 'runtime.tgz'
    runtime.build(root, package, sha)
    files, _ = runtime.read_archive(package)
    zipped = io.BytesIO()
    with zipfile.ZipFile(zipped, 'w') as archive:
        for name, content in files.items():
            if name != 'app/_release.py':
                archive.writestr('repo-' + SHA + '/' + name, content)
    class Response:
        content = zipped.getvalue()
        def raise_for_status(self): pass
    server = tmp_path / 'server'
    server.mkdir()
    monkeypatch.setattr(dm, 'ROOT', server)
    monkeypatch.setattr(dm, '_tested_main_commit', lambda: SHA)
    monkeypatch.setattr(dm.httpx, 'get', lambda *a, **k: Response())
    result = dm._deploy({'confirm': 'deploy_tested_main'})
    assert result['status'] == 'restart_requested'
    assert result['commit'] == SHA
    assert (server / 'app/_release.py').read_text() == 'COMMIT = ' + repr(SHA) + '\n'
    assert (server / '_earnwage_backups' / result['backup_id']).is_file()


def test_worker_identity_stays_at_boot_commit_until_restart(tmp_path):
    import sys
    root = Path(__file__).resolve().parents[1]
    app = tmp_path / 'app'
    app.mkdir()
    (app / '__init__.py').touch()
    (app / 'release.py').write_text((root / 'app/release.py').read_text())
    marker = app / '_release.py'
    marker.write_text('COMMIT = ' + repr(SHA) + '\n')
    script = "from app import release; from pathlib import Path; print(release.COMMIT); Path('app/_release.py').write_text(\"COMMIT = '" + 'b' * 40 + "'\\n\"); print(release.COMMIT)"
    result = subprocess.check_output([sys.executable, '-c', script], cwd=tmp_path, text=True)
    assert result.splitlines() == [SHA, SHA]
    result = subprocess.check_output([sys.executable, '-c', 'from app.release import COMMIT; print(COMMIT)'], cwd=tmp_path, text=True)
    assert result.strip() == 'b' * 40


def test_browser_health_gate_executes_same_commit_checks():
    import re
    root = Path(__file__).resolve().parents[1]
    page = (root / 'docs/data-manager.html').read_text()
    function = re.search(r'function releaseHealthy\(response,health,release\)\{[\s\S]*?\n\}', page).group()
    javascript = function + '''
const release={version:"0.5.20",commit:"a".repeat(40)};
const good={status:"ok",version:"0.5.20",commit:release.commit};
if(!releaseHealthy({ok:true},good,release))process.exit(1);
for(const bad of [{...good,commit:"b".repeat(40)},{...good,status:"error"},{...good,version:"old"}]){
if(releaseHealthy({ok:true},bad,release))process.exit(1);
}
if(releaseHealthy({ok:false},good,release))process.exit(1);
if(releaseHealthy({ok:true},good,{version:"0.5.20"}))process.exit(1);
'''
    subprocess.run(['node', '-e', javascript], check=True)
    assert 'if(releaseHealthy(response,health,r))' in page
    assert 'Deploy GitHub concluído' not in page
