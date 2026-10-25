"""Cookie Vault runtime-root tests; all files stay under pytest tmp_path."""
from __future__ import annotations

import json


def test_cookie_vault_follows_runtime_data_dir_without_reimport(monkeypatch, tmp_path):
    from lumenis.adapters import cookie_vault

    runtime_root = tmp_path / "protected-runtime"
    cookie_dir = runtime_root / "cookies"
    cookie_dir.mkdir(parents=True)
    cookie_file = cookie_dir / "douyin.json"
    cookie_file.write_text(json.dumps([{"name": "sessionid", "value": "fixture"}]), encoding="utf-8")

    monkeypatch.setenv("ZBC_DATA_DIR", str(runtime_root))
    monkeypatch.delenv("ZBC_DB_PATH", raising=False)

    assert cookie_vault._resolve_path("douyin") == cookie_file.resolve()
    assert cookie_vault.load_cookies("douyin")[0]["name"] == "sessionid"


def test_registered_profile_reference_does_not_redirect_cookie_or_runtime_writes(monkeypatch, tmp_path):
    from lumenis.adapters import cookie_vault
    from lumenis.adapters.human_browser import readonly_worker_spec
    runtime, sessions = tmp_path / 'isolated-runtime', tmp_path / 'registered-sessions'
    runtime.mkdir()
    sessions.mkdir()
    monkeypatch.setenv('ZBC_DATA_DIR', str(runtime))
    monkeypatch.setenv('LUMENIS_COLLECTOR_SESSION_DATA_DIR', str(sessions))
    assert cookie_vault._current_data_dir() == runtime.resolve()
    assert cookie_vault.registered_session_data_dir() == sessions.resolve()
    assert readonly_worker_spec('douyin')['profile'] == str((sessions / 'private/profiles/douyin-readonly').resolve())
    assert cookie_vault._current_cookie_paths('douyin') == [runtime / 'cookies/douyin.json']


def test_registered_profile_reference_rejects_relative_missing_or_redirected_root(tmp_path):
    import pytest
    from lumenis.adapters.cookie_vault import registered_session_data_dir
    for value in ['relative-session-root', str(tmp_path / 'missing')]:
        with pytest.raises(ValueError, match='REGISTERED_SESSION_ROOT_INVALID'):
            registered_session_data_dir(environ={'LUMENIS_COLLECTOR_SESSION_DATA_DIR': value})


def test_collection_checkpoints_use_runtime_root_and_reject_session_root(monkeypatch, tmp_path):
    import collector
    import xhs_cookie_bridge as bridge
    runtime, sessions = tmp_path / 'runtime/private', tmp_path / 'registered/private'
    runtime.mkdir(parents=True)
    sessions.mkdir(parents=True)
    monkeypatch.setattr(bridge, 'RUNTIME_PRIVATE_DATA_DIR', str(runtime))
    monkeypatch.setattr(bridge, 'PRIVATE_DATA_DIR', str(sessions))
    path = collector.new_xhs_raw_checkpoint_path('a' * 64, 'explicit user topic')
    assert __import__('pathlib').Path(path).is_relative_to(runtime)
    import pytest
    with pytest.raises(ValueError, match='XHS_CHECKPOINT_PATH_INVALID'):
        collector.validate_xhs_raw_checkpoint_path(str(sessions / 'foreign.json'))
