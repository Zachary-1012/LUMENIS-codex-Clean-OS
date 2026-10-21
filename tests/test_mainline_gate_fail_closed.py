"""Mainline path admission and diff selection fail closed; no real credentials."""
import hashlib
import subprocess
from pathlib import Path
from types import SimpleNamespace
import pytest
import data_boundary as boundary
from scripts.audit_tools import experience_gate_mode as experience


def test_reviewed_receipt_requires_exact_path_bytes_and_regular_file(tmp_path, monkeypatch):
    name = 'evidence/credential-scan.json'
    target = tmp_path / name
    target.parent.mkdir()
    target.write_bytes(b'{"unresolved_hits":0}')
    monkeypatch.setattr(boundary, '_REVIEWED_CREDENTIAL_NAMED_EVIDENCE', {name: hashlib.sha256(target.read_bytes()).hexdigest()})
    monkeypatch.setattr(boundary, 'git_tracked_files', lambda root: [name])
    expected = hashlib.sha256(target.read_bytes()).hexdigest()
    monkeypatch.setattr(boundary, '_git_index_digest', lambda root, path: expected)
    assert boundary.assert_no_tracked_credentials(tmp_path)['status'] == 'pass'
    target.write_bytes(b'{"changed":true}')
    assert boundary.assert_no_tracked_credentials(tmp_path)['status'] == 'fail'
    target.unlink()
    other = tmp_path / 'other'
    other.write_bytes(b'{"unresolved_hits":0}')
    target.symlink_to(other)
    assert boundary.assert_no_tracked_credentials(tmp_path)['status'] == 'fail'


def test_missing_receipt_and_unreadable_inventory_cannot_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(boundary, 'git_tracked_files', lambda root: None)
    result = boundary.assert_no_tracked_credentials(tmp_path)
    assert result['status'] == 'fail'
    assert result['reason_code'] == 'TRACKED_INVENTORY_UNAVAILABLE'
    name = next(iter(boundary._REVIEWED_CREDENTIAL_NAMED_EVIDENCE))
    monkeypatch.setattr(boundary, 'git_tracked_files', lambda root: [name])
    assert boundary.assert_no_tracked_credentials(tmp_path)['status'] == 'fail'


@pytest.mark.parametrize('path', ['.env', '.env.production', 'docs/real.pem', 'tests/token.key', 'evidence/session.json', 'elsewhere/public-credential-signature-scan.json'])
def test_real_containers_and_receipt_names_elsewhere_still_block(tmp_path, monkeypatch, path):
    monkeypatch.setattr(boundary, 'git_tracked_files', lambda root: [path])
    assert boundary.assert_no_tracked_credentials(tmp_path)['status'] == 'fail'


@pytest.mark.parametrize('base', ['', '0' * 40])
def test_unknown_base_is_strict(base):
    assert experience.select_mode(base) == '--strict'


@pytest.mark.parametrize('paths,mode', [(b'docs/readme.md\0', '--baseline'), (b'app/lib/main.dart\0', '--strict'), (b'website/home.html\0', '--strict'), ((b'docs/readme.md\0' * 100000) + b'app/lib/main.dart\0', '--strict')])
def test_diff_paths_and_large_diff(monkeypatch, paths, mode):
    monkeypatch.setattr(experience.subprocess, 'run', lambda *args, **kw: SimpleNamespace(stdout=paths, returncode=0))
    assert experience.select_mode('a' * 40) == mode


@pytest.mark.parametrize('failure_at', [1, 2, 3])
def test_git_failure_never_selects_baseline(monkeypatch, failure_at):
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        assert kwargs['check'] is True
        if len(calls) == failure_at:
            raise subprocess.CalledProcessError(128, command)
        return SimpleNamespace(stdout=b'', returncode=0)
    monkeypatch.setattr(experience.subprocess, 'run', run)
    with pytest.raises(subprocess.CalledProcessError):
        experience.select_mode('a' * 40)


def test_workflow_enforces_path_boundary_and_complete_comparison():
    workflow = Path('.github/workflows/platform-verify.yml').read_text()
    assert 'Credential-path boundary (BLOCKING)' in workflow
    assert "raise SystemExit(0 if result['status'] == 'pass' else 1)" in workflow
    assert 'github.event.pull_request.base.sha || github.event.before' in workflow
    assert 'git diff --name-only HEAD^ HEAD || true' not in workflow

@pytest.mark.parametrize('source,target', [('app/lib/old.dart', 'archive/old.dart'), ('archive/old.dart', 'app/lib/new.dart')])
def test_rename_across_surface_boundary_requires_strict(tmp_path, source, target):
    def git(*args):
        return subprocess.run(['git', *args], cwd=tmp_path, check=True, capture_output=True).stdout.decode().strip()
    git('init')
    git('config', 'user.email', 'synthetic@example.invalid')
    git('config', 'user.name', 'Synthetic Fixture')
    old = tmp_path / source
    old.parent.mkdir(parents=True)
    old.write_text('synthetic source\n')
    git('add', source)
    git('commit', '-m', 'fixture')
    base = git('rev-parse', 'HEAD')
    new = tmp_path / target
    new.parent.mkdir(parents=True, exist_ok=True)
    git('mv', source, target)
    git('commit', '-m', 'rename fixture')
    assert experience.select_mode(base, cwd=tmp_path) == '--strict'


def test_reviewed_working_copy_cannot_mask_changed_index(tmp_path, monkeypatch):
    name = 'evidence/credential-scan.json'
    path = tmp_path / name
    path.parent.mkdir()
    path.write_bytes(b'{"unresolved_hits":0}')
    monkeypatch.setattr(boundary, '_REVIEWED_CREDENTIAL_NAMED_EVIDENCE', {name: hashlib.sha256(path.read_bytes()).hexdigest()})
    monkeypatch.setattr(boundary, 'git_tracked_files', lambda root: [name])
    monkeypatch.setattr(boundary, '_git_index_digest', lambda root, path: '0' * 64)
    assert boundary.assert_no_tracked_credentials(tmp_path)['status'] == 'fail'


def test_git_inventory_preserves_special_filename(monkeypatch):
    def run(command, **kwargs):
        assert command[-1] == '-z'
        return SimpleNamespace(returncode=0, stdout='evidence/令牌-session\nname.json\0')
    monkeypatch.setattr(boundary.subprocess, 'run', run)
    assert boundary.git_tracked_files('.') == ['evidence/令牌-session\nname.json']
