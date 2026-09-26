import builtins
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

import app


def test_app_acceptance_guard_requires_explicit_loopback_before_import_chain():
    assert app._is_internal_beta_loopback('127.0.0.1')
    assert not app._is_internal_beta_loopback('0.0.0.0')
    assert app._cli_option_value(
        ['--internal-beta-acceptance', '--host', '127.0.0.1'], '--host'
    ) == '127.0.0.1'
    assert app._cli_option_value(
        ['--host', '127.0.0.1', '--host', '0.0.0.0'], '--host'
    ) is None

    source = Path(app.__file__).read_text(encoding='utf-8-sig')
    early_profile = source.index("INTERNAL_BETA_ACCEPTANCE = '--internal-beta-acceptance' in sys.argv")
    first_app_import = source.index('import database as db')
    assert early_profile < first_app_import

    prefix = source[:source.index('def _load_dotenv')]
    namespace = {'__name__': 'startup_profile_probe'}
    original_argv = sys.argv
    try:
        sys.argv = ['app.py', '--internal-beta-acceptance', '--host', '0.0.0.0']
        with pytest.raises(SystemExit, match='explicit --host 127.0.0.1'):
            exec(compile(prefix, app.__file__, 'exec'), namespace)
    finally:
        sys.argv = original_argv


def test_acceptance_import_paths_are_explicit_and_confined_to_temp(tmp_path):
    data_dir = tmp_path / 'acceptance-data'
    env = {
        'ZBC_DB_PATH': str(data_dir / 'monitor.db'),
        'ZBC_DATA_DIR': str(data_dir),
        'XHS_COOKIE_FILE': r'D:\private\personal-cookie.txt',
        'XHS_COOKIE_FILE_OVERRIDE': r'D:\private\personal-cookie.txt',
        'XHS_COOKIE_HEADER': 'must be cleared',
        'XHS_COOKIES_JSON': 'must be cleared',
    }

    db_path, validated_data_dir = app._activate_internal_beta_environment(env)
    assert Path(db_path).is_relative_to(Path(tmp_path).resolve())
    assert Path(validated_data_dir).is_relative_to(Path(tmp_path).resolve())
    assert env['XHS_COOKIE_FILE'] == str(data_dir.resolve() / 'private' / 'acceptance-cookie-unavailable.txt')
    assert env['XHS_COOKIE_FILE_OVERRIDE'] == env['XHS_COOKIE_FILE']
    assert env['LOG_DIR'] == str(data_dir.resolve() / 'logs')
    assert env['XHS_COOKIE_HEADER'] == env['XHS_COOKIES_JSON'] == ''

    with pytest.raises(ValueError, match='explicit ZBC_DB_PATH and ZBC_DATA_DIR'):
        app._validate_internal_beta_storage({}, temp_root=tmp_path)
    with pytest.raises(ValueError, match='absolute ZBC_DATA_DIR'):
        app._validate_internal_beta_storage({
            'ZBC_DB_PATH': str(data_dir / 'monitor.db'),
            'ZBC_DATA_DIR': 'acceptance-data',
        }, temp_root=tmp_path)
    with pytest.raises(ValueError, match='dedicated directory under the OS temp root'):
        app._validate_internal_beta_storage({
            'ZBC_DB_PATH': str(tmp_path.parent / 'monitor.db'),
            'ZBC_DATA_DIR': str(tmp_path.parent / 'outside-data'),
        }, temp_root=tmp_path)


def test_acceptance_request_fence_blocks_everything_except_health(monkeypatch):
    monkeypatch.setattr(app, 'INTERNAL_BETA_ACCEPTANCE', True)
    client = app.app.test_client()
    hooks = app.app.before_request_funcs[None]
    original_hooks = list(hooks)
    assert original_hooks[0] is app._internal_beta_health_only_request_fence

    later_hook_calls = []
    handler_calls = []

    def forbidden_later_hook():
        later_hook_calls.append('hook')
        raise AssertionError('acceptance fence must run before later request hooks')

    def forbidden_handler():
        handler_calls.append('handler')
        raise AssertionError('blocked request reached route handler')

    original_accounts = app.app.view_functions['api_xhs_accounts']
    original_switch = app.app.view_functions['api_xhs_switch_account']
    hooks[:] = [original_hooks[0], *[forbidden_later_hook for _ in original_hooks[1:]]]
    app.app.view_functions['api_xhs_accounts'] = forbidden_handler
    app.app.view_functions['api_xhs_switch_account'] = forbidden_handler
    try:
        get_response = client.get('/api/xhs/accounts')
        post_response = client.post('/api/xhs/switch-account', json={'account': 'sentinel'})
        for response in (get_response, post_response):
            assert response.status_code == 403
            assert response.get_json()['status'] == 'BLOCKED'
            assert response.get_json()['code'] == 'INTERNAL_BETA_HEALTH_ONLY'
        assert later_hook_calls == []
        assert handler_calls == []
    finally:
        hooks[:] = original_hooks
        app.app.view_functions['api_xhs_accounts'] = original_accounts
        app.app.view_functions['api_xhs_switch_account'] = original_switch

    health = client.get('/healthz')
    assert health.status_code == 200
    assert health.get_json()['status'] == 'healthy'
    assert health.get_json()['dependencies']['database'] == 'ok'


def test_acceptance_startup_skips_node_profile_probe_and_uses_temp_logs(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(app, '_ensure_node_on_path', lambda: calls.append('node') or True)
    assert app._prepare_node_runtime(True) is False
    assert calls == []
    assert app._prepare_node_runtime(False) is True
    assert calls == ['node']

    data_dir = tmp_path / 'acceptance-data'
    monkeypatch.setenv('LOG_DIR', str(data_dir / 'logs'))
    assert Path(app._startup_log_dir()) == data_dir / 'logs'


def test_acceptance_profile_does_not_read_dotenv(monkeypatch):
    monkeypatch.setattr(app, 'INTERNAL_BETA_ACCEPTANCE', True)
    monkeypatch.setattr(
        app.os.path, 'exists',
        lambda _path: (_ for _ in ()).throw(AssertionError('.env must not be probed')),
    )
    app._load_dotenv('.env')


def test_acceptance_profile_suppresses_all_app_automations(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError('automatic runtime service must not start in acceptance mode')

    monkeypatch.setattr(app.threading, 'Thread', forbidden)
    monkeypatch.setattr(app.xhs_p0_orchestrator, 'start_resident', forbidden)
    monkeypatch.setattr(app.memory_optimizer, 'get_memory_optimizer', forbidden)
    monkeypatch.setattr(app.stability_monitor, 'get_stability_monitor', forbidden)
    monkeypatch.setattr(app.runtime_preflight, 'run_preflight', forbidden)
    monkeypatch.setattr(builtins, '__import__', lambda name, *a, **kw: (
        forbidden() if name in {
            'cdp_helper', 'auto_recovery', 'system_guardian', 'runtime_guardian',
        } else _original_import(name, *a, **kw)
    ))

    assert app._start_app_automations(SimpleNamespace(
        internal_beta_acceptance=True, no_scheduler=False
    )) is False
    assert app._start_optional_runtime_services(True) is False


_original_import = builtins.__import__
