"""Cold import and deferred owner initialization regressions, not product E2E."""
import json
import os
from pathlib import Path
import subprocess
import sys


def test_importing_session_and_ai_owners_does_not_open_database(tmp_path):
    env = dict(os.environ, ZBC_DB_PATH=str(tmp_path / 'monitor.db'),
               ZBC_DATA_DIR=str(tmp_path), ZBC_TEST_OFFLINE='1')
    script = '''
import sqlite3
calls = []

def forbidden(*args, **kwargs):
    calls.append(args)
    raise AssertionError("owner import attempted DB connection")
sqlite3.connect = forbidden
import xhs_cookie_bridge
import ai_governance
import runtime_guardian
assert not calls
assert not xhs_cookie_bridge._stats_loaded
assert not ai_governance._desensitizer._patterns_loaded
'''
    result = subprocess.run([sys.executable, '-c', script], env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'owner import attempted DB connection' not in result.stdout + result.stderr
    assert not (tmp_path / 'monitor.db').exists()


def test_deferred_stats_restore_is_idempotent_before_rate_limit(tmp_path, monkeypatch):
    import xhs_cookie_bridge as bridge
    stamp = bridge.time.time()
    path = tmp_path / 'stats.json'
    path.write_text(json.dumps({'date': bridge.datetime.now().strftime('%Y-%m-%d'),
                               'daily_runs': [stamp], 'manual_runs': 1,
                               'auto_runs': 0, 'last_run_time': stamp}))
    monkeypatch.setattr(bridge, 'STATS_FILE', str(path))
    monkeypatch.setattr(bridge, '_stats_loaded', False)
    monkeypatch.setattr(bridge, '_daily_runs', [])
    monkeypatch.setattr(bridge, '_daily_manual_runs', 0)
    monkeypatch.setattr(bridge, '_daily_auto_runs', 0)
    monkeypatch.setattr(bridge, '_last_run_time', None)
    def forbidden():
        raise AssertionError('current persisted stats must not read DB')
    monkeypatch.setattr(bridge, '_load_stats_from_db', forbidden)
    allowed, _ = bridge.check_rate_limit('manual')
    assert not allowed  # Existing cooldown is preserved on first explicit use.
    assert bridge._stats_loaded and bridge._daily_runs == [stamp]
    bridge._load_stats()
    assert bridge._daily_manual_runs == 1 and bridge._daily_runs == [stamp]


def test_deferred_desensitizer_keeps_registry_entities_and_restore(monkeypatch):
    import ai_governance as governance
    import subject_registry
    calls = []
    def names():
        calls.append(True)
        return ('Registered Example Brand',)
    monkeypatch.setattr(subject_registry, 'registered_subject_names', names)
    owner = governance.AIDesensitizer()
    assert not calls
    text = 'Registered Example Brand and Zachary'
    redacted, mapping = owner.desensitize(text)
    assert 'Registered Example Brand' not in redacted and 'Zachary' not in redacted
    assert owner.restore(redacted, mapping) == text
    count = len(calls)
    owner.desensitize(text)
    assert len(calls) == count


def test_core_restores_stats_only_after_canonical_migration():
    source = Path('app.py').read_text(encoding='utf-8')
    assert source.index('db.init_db()') < source.index('if not _dm.migrate():')
    assert source.index('if not _dm.migrate():') < source.index('xhs_cookie_bridge._load_stats()')
    assert source.index('xhs_cookie_bridge._load_stats()') < source.index('def _start_app_automations(')


def test_manual_workspace_validates_paths_and_keeps_normal_routes(tmp_path):
    import app
    root = tmp_path / 'persistent-workspace'
    env = {'ZBC_DATA_DIR': str(root), 'ZBC_DB_PATH': str(root / 'monitor.db')}
    argv = ['--manual-workspace', '--host', '127.0.0.1', '--port', '18375']
    database, data = app._activate_manual_workspace(argv, env)
    assert database == str(root / 'monitor.db') and data == str(root)
    assert env['LUMENIS_OPEN_WORKSPACE'] == '1'
    assert env['ZBC_ARTIFACT_DIR'] == str(root / 'artifacts')
    assert env['ZBC_AI_GOV_STATS_FILE'] == str(root / 'ai_governance_stats.json')
    assert not root.exists()  # Configuration validation performs no DB write.
    # Restart configuration retains the same existing dedicated data.
    root.mkdir()
    (root / 'monitor.db').write_bytes(b'isolated-test-sentinel')
    app._activate_manual_workspace(argv, env)
    assert (root / 'monitor.db').read_bytes() == b'isolated-test-sentinel'


def test_manual_workspace_refuses_unsafe_configuration(tmp_path):
    import app
    import pytest
    root = tmp_path / 'manual'
    valid = {'ZBC_DATA_DIR': str(root), 'ZBC_DB_PATH': str(root / 'monitor.db')}
    argv = ['--manual-workspace', '--host', '127.0.0.1', '--port', '18375']
    invalid = [
        (argv, {}),
        (argv, {**valid, 'ZBC_DATA_DIR': '.'}),
        (argv, {**valid, 'ZBC_DB_PATH': str(tmp_path / 'outside.db')}),
        (argv, {'ZBC_DATA_DIR': str(Path.cwd() / 'data'), 'ZBC_DB_PATH': str(Path.cwd() / 'data' / 'monitor.db')}),
        (['--manual-workspace', '--host', '0.0.0.0', '--port', '18375'], valid),
        (['--manual-workspace', '--host', '127.0.0.1', '--port', '8201'], valid),
        (argv + ['--internal-beta-acceptance'], valid),
        (argv + ['--manual-workspace'], valid),
    ]
    for arguments, environment in invalid:
        with pytest.raises(ValueError):
            app._activate_manual_workspace(arguments, dict(environment))


def test_manual_workspace_suppresses_only_automatic_services(monkeypatch):
    import app
    from types import SimpleNamespace
    monkeypatch.setattr(app, 'MANUAL_WORKSPACE', True)
    monkeypatch.setattr(app, 'INTERNAL_BETA_SAFE_STARTUP', False)
    monkeypatch.setattr(app, 'INTERNAL_BETA_ACCEPTANCE', False)
    monkeypatch.setattr(app, 'INTERNAL_BETA_WORKSPACE_CONTEXT_ACCEPTANCE', False)
    def forbidden(*args, **kwargs):
        raise AssertionError('manual startup attempted an automatic service')
    monkeypatch.setattr(app, '_ensure_node_on_path', forbidden)
    monkeypatch.setattr(app.threading, 'Thread', forbidden)
    monkeypatch.setattr(app.runtime_preflight, 'run_preflight', forbidden)
    assert app._prepare_node_runtime(False) is False
    assert app._start_app_automations(SimpleNamespace(no_scheduler=False)) is False
    assert app._start_optional_runtime_services(False) is False
    with app.app.test_request_context('/api/experience/saved-work', method='POST'):
        assert app._internal_beta_health_only_request_fence() is None
        assert app._internal_beta_workspace_context_request_fence() is None


def test_isolated_profiles_do_not_read_or_override_dotenv(tmp_path, monkeypatch):
    import config
    isolated = tmp_path / 'isolated' / 'monitor.db'
    local_env = tmp_path / 'unrelated.env'
    local_env.write_text('ZBC_DB_PATH=/unrelated/never-open.db\nLUMENIS_CONFIG_SENTINEL=loaded\n')
    monkeypatch.setattr(config, 'ENV_FILE', str(local_env))
    monkeypatch.setenv('ZBC_DB_PATH', str(isolated))
    monkeypatch.delenv('LUMENIS_CONFIG_SENTINEL', raising=False)
    def forbidden(*args, **kwargs):
        raise AssertionError('isolated profile must not even inspect dotenv')
    monkeypatch.setattr(config.os.path, 'exists', forbidden)
    monkeypatch.setattr(config, 'load_dotenv', forbidden)
    for flag in ('--manual-workspace', '--internal-beta-acceptance',
                 '--internal-beta-workspace-context-acceptance',
                 '--internal-beta-browser-outcome-acceptance'):
        monkeypatch.setattr(sys, 'argv', ['app.py', flag])
        config.load_env()
        assert os.environ['ZBC_DB_PATH'] == str(isolated)
        assert 'LUMENIS_CONFIG_SENTINEL' not in os.environ


def test_ordinary_profile_retains_existing_dotenv_override(tmp_path, monkeypatch):
    import config
    local_env = tmp_path / 'ordinary.env'
    value = str(tmp_path / 'explicit-ordinary-config.db')
    local_env.write_text('ZBC_DB_PATH=' + value + '\n')
    monkeypatch.setattr(config, 'ENV_FILE', str(local_env))
    monkeypatch.setattr(sys, 'argv', ['app.py', '--no-scheduler'])
    monkeypatch.setenv('ZBC_DB_PATH', str(tmp_path / 'prior.db'))
    config.load_env()
    assert os.environ['ZBC_DB_PATH'] == value


def test_guardian_uses_call_time_canonical_path_without_import_side_effect(tmp_path, monkeypatch):
    import runtime_guardian
    target = tmp_path / 'guardian.db'
    stale = tmp_path / 'stale-import-time.db'
    monkeypatch.setattr(runtime_guardian, 'DB_PATH', str(stale))
    monkeypatch.setenv('ZBC_DB_PATH', str(target))
    guardian = runtime_guardian.RuntimeGuardian(name='isolated-explicit-construction')
    assert guardian._db_path == str(target)
    assert target.exists() and not stale.exists()
    with runtime_guardian._get_db() as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {'runtime_guardian_workers', 'runtime_guardian_checkpoints', 'runtime_guardian_dlq'} <= tables


def test_watchdog_explicit_lifecycle_stops_and_restarts():
    import app
    import threading
    assert not any(t.name == 'hang_watchdog' for t in threading.enumerate())
    try:
        first = app._start_hang_watchdog()
        assert first.is_alive()
        assert app._start_hang_watchdog() is first
        assert app._stop_hang_watchdog(timeout=1)
        assert not first.is_alive()
        second = app._start_hang_watchdog()
        assert second is not first and second.is_alive()
    finally:
        assert app._stop_hang_watchdog(timeout=1)
    assert not any(t.name == 'hang_watchdog' for t in threading.enumerate())


def test_scheduler_owner_interrupts_wait_and_restarts_without_task_admission(monkeypatch):
    import app
    import threading
    entered = threading.Event()
    def idle_loop():
        entered.set()
        app._SCHEDULER_STOP.wait(60)
    monkeypatch.setattr(app, 'scheduler_loop', idle_loop)
    try:
        first = app._start_scheduler()
        assert entered.wait(1)
        assert app._start_scheduler() is first
        assert app._stop_scheduler(timeout=1)
        assert not first.is_alive()
        entered.clear()
        second = app._start_scheduler()
        assert entered.wait(1) and second is not first
    finally:
        assert app._stop_scheduler(timeout=1)


def test_stopped_scheduler_never_enters_collection_tick(monkeypatch):
    import app
    app._SCHEDULER_STOP.set()
    class ForbiddenClock:
        @staticmethod
        def now():
            raise AssertionError('stopped scheduler admitted a tick')
    monkeypatch.setattr(app, 'datetime', ForbiddenClock)
    app.scheduler_loop()


def test_scheduler_shutdown_does_not_complete_or_kill_inflight_task(monkeypatch, tmp_path):
    import app
    import threading
    entered, release = threading.Event(), threading.Event()
    from runtime_guardian import RuntimeGuardian
    owner = RuntimeGuardian(name='shutdown-test', db_path=str(tmp_path / 'guardian.db'))
    worker = owner.register_worker('local-checkpoint-test')
    owner.acquire_lease(worker, 'local-test', ttl_seconds=60)
    owner.save_checkpoint(run_id='shutdown-run', worker_id=worker, position='step-1')
    before = owner.get_worker(worker)
    checkpoint = owner.get_latest_checkpoint('shutdown-run')
    def active_loop():
        entered.set()
        release.wait(5)
    monkeypatch.setattr(app, 'scheduler_loop', active_loop)
    try:
        thread = app._start_scheduler()
        assert entered.wait(1)
        assert not app._stop_scheduler(timeout=0.01)
        assert thread.is_alive()
        assert owner.get_worker(worker) == before
        assert owner.get_latest_checkpoint('shutdown-run') == checkpoint
        assert app._start_scheduler() is thread  # No duplicate while draining.
    finally:
        release.set()
        assert app._stop_scheduler(timeout=1)
