from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from app import data_manager as dm

WORKFLOW = Path(__file__).resolve().parents[1] / '.github/workflows/deploy-production.yml'


def permitted(repository=dm.GITHUB_REPOSITORY, enabled="true", **changes):
    run = dict(event='push', status='completed', conclusion='success', head_branch='main',
               head_repository=NS(full_name=dm.GITHUB_REPOSITORY))
    run.update(changes)
    github = NS(repository=repository, event=NS(workflow_run=NS(**run)))
    expression = WORKFLOW.read_text().split('${{', 1)[1].split('}}', 1)[0]
    return eval(expression.replace('&&', ' and ').strip().replace('\n', ' '),
                {'__builtins__': {}}, {'github': github, 'vars': NS(EARNWAGE_DEPLOY_ENABLED=enabled)})


def test_original_main_push_is_allowed():
    assert permitted()


@pytest.mark.parametrize('changes', [dict(event='pull_request'), dict(event='workflow_run'),
    dict(event='workflow_dispatch'), dict(head_branch='feature'), dict(conclusion='failure'),
    dict(status='in_progress'), dict(head_repository=NS(full_name='fork/project'))])
def test_other_triggers_are_rejected(changes):
    assert not permitted(**changes)


def test_activation_switch_preserved_and_manual_bypass_removed():
    text = WORKFLOW.read_text()
    assert "vars.EARNWAGE_DEPLOY_ENABLED == 'true'" in text
    assert 'workflow_dispatch:' not in text


@pytest.mark.parametrize('event,repo', [('push', dm.GITHUB_REPOSITORY),
                                      ('pull_request', dm.GITHUB_REPOSITORY), ('push', 'fork/project')])
def test_browser_deployment_requires_original_push(monkeypatch, event, repo):
    sha = 'a' * 40
    run = dict(name='API tests', head_sha=sha, head_branch='main', event=event,
               status='completed', conclusion='success', head_repository={'full_name': repo})
    monkeypatch.setattr(dm, '_github_json', lambda url: {'sha': sha} if '/commits/' in url else {'workflow_runs': [run]})
    if event == 'push' and repo == dm.GITHUB_REPOSITORY:
        assert dm._tested_main_commit() == sha
    else:
        with pytest.raises(RuntimeError, match='github_tests_not_green'):
            dm._tested_main_commit()


def test_ssh_uses_only_pretrusted_keys():
    text = WORKFLOW.read_text()
    assert 'ssh-keyscan' not in text
    assert 'secrets.EARNWAGE_SSH_KNOWN_HOSTS' in text
    for line in text.splitlines():
        if line.strip().startswith(('scp ', 'ssh ')):
            assert 'StrictHostKeyChecking=yes' in line
            assert 'UserKnownHostsFile=' in line
            assert 'BatchMode=yes' in line
    assert 'set -x' not in text
    assert 'echo "$SSH_PRIVATE_KEY"' not in text


@pytest.mark.parametrize('changes', [dict(repository='fork/project'), dict(enabled='false'), dict(enabled='')])
def test_fork_workflow_and_disabled_activation_are_rejected(changes):
    assert not permitted(**changes)
