"""Current workflow/helper regression: large diffs cannot silently downgrade."""
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest
from scripts.audit_tools import experience_gate_mode as selector

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/platform-verify.yml"


def test_workflow_executes_current_selector_and_verified_event_base():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "python scripts/audit_tools/experience_gate_mode.py" in text
    assert "github.event.pull_request.base.sha || github.event.before" in text
    assert '--head HEAD --run' in text
    assert 'git diff --name-only HEAD^ HEAD || true' not in text


@pytest.mark.parametrize("large", [False, True], ids=["short", "long"])
@pytest.mark.parametrize("surface_changed", [False, True], ids=["unrelated", "surface"])
def test_current_experience_selector_preserves_strict_for_large_diff(large, surface_changed, monkeypatch):
    paths = ["app/lib/main.dart" if surface_changed else "tests/test_example.py"]
    if large:
        # Exceed the old shell pipe capacity. The current selector consumes the
        # whole NUL-delimited git result, without grep -q / SIGPIPE truncation.
        paths.extend(f"research/history/{index:05d}-{'x' * 250}.json" for index in range(5000))
    calls = []
    def git(args, **kwargs):
        calls.append(args)
        assert kwargs['check'] is True
        return SimpleNamespace(stdout=('\0'.join(paths) + '\0').encode() if args[1] == 'diff' else b'commit\n')
    monkeypatch.setattr(selector.subprocess, 'run', git)
    assert selector.select_mode('base', 'head') == ('--strict' if surface_changed else '--baseline')
    assert calls == [
        ['git', 'rev-parse', '--verify', 'base^{commit}'],
        ['git', 'rev-parse', '--verify', 'head^{commit}'],
        ['git', 'diff', '--name-only', '--no-renames', '-z', 'base', 'head', '--'],
    ]


def test_comparison_error_blocks_cli_instead_of_selecting_baseline(monkeypatch, capsys):
    monkeypatch.setattr(selector.sys, 'argv', ['experience_gate_mode.py', '--base', 'base', '--run'])
    calls = []
    def fail(args, **kwargs):
        calls.append(args)
        raise subprocess.CalledProcessError(128, args)
    monkeypatch.setattr(selector.subprocess, 'run', fail)
    assert selector.main() == 1
    captured = capsys.readouterr()
    assert captured.out == ''
    assert 'blocking, not baseline' in captured.err
    assert len(calls) == 1  # Never invoke the verifier with an invented mode.
