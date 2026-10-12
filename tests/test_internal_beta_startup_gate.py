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


def _guard_manual_core_startup_effects(monkeypatch):
    effects = []
    blocked_modules = {
        'cdp_helper', 'auto_recovery', 'system_guardian', 'runtime_guardian',
    }

    def guarded_import(name, *args, **kwargs):
        if name in blocked_modules or name.startswith('lumenis.shared.learning'):
            effects.append(f'import:{name}')
            raise AssertionError(f'manual Core must not start optional service: {name}')
        return _original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', guarded_import)
    monkeypatch.setattr(
        app.threading, 'Thread',
        lambda *_args, **_kwargs: effects.append('thread') or SimpleNamespace(
            start=lambda: effects.append('thread.start')),
    )
    return effects


def test_manual_core_runs_preflight_and_skips_platform_and_automated_services(monkeypatch):
    monkeypatch.setattr(app, 'INTERNAL_BETA_SAFE_STARTUP', False)
    monkeypatch.setenv('ZBC_GUARDIAN_ENABLED', '1')
    effects = _guard_manual_core_startup_effects(monkeypatch)
    calls = []
    report = {'overall': 'pass'}
    monkeypatch.setattr(
        app.runtime_preflight, 'run_preflight',
        lambda: calls.append('preflight') or report,
    )
    monkeypatch.setattr(
        app.runtime_preflight, 'format_summary',
        lambda value: calls.append(('summary', value)) or 'summary',
    )

    assert app._start_optional_runtime_services(False, no_scheduler=True) is False
    assert calls == ['preflight', ('summary', report)]
    assert effects == []


def test_manual_core_propagates_preflight_failure_without_optional_services(monkeypatch):
    monkeypatch.setattr(app, 'INTERNAL_BETA_SAFE_STARTUP', False)
    monkeypatch.setenv('ZBC_GUARDIAN_ENABLED', '1')
    effects = _guard_manual_core_startup_effects(monkeypatch)
    calls = []

    def fail_enforced_preflight():
        calls.append('preflight')
        raise SystemExit(3)

    monkeypatch.setattr(app.runtime_preflight, 'run_preflight', fail_enforced_preflight)
    monkeypatch.setattr(
        app.runtime_preflight, 'format_summary',
        lambda _value: calls.append('summary') or 'summary',
    )

    with pytest.raises(SystemExit) as error:
        app._start_optional_runtime_services(False, no_scheduler=True)

    assert error.value.code == 3
    assert calls == ['preflight']
    assert effects == []


def test_ordinary_startup_does_not_run_retired_inference_heartbeat(monkeypatch):
    import intelligence
    from lumenis.system.ai_gateway import channel

    calls = []
    monkeypatch.setattr(app, 'INTERNAL_BETA_SAFE_STARTUP', False)
    monkeypatch.setattr(app, 'INTERNAL_BETA_ACCEPTANCE', False)
    monkeypatch.setattr(app, 'INTERNAL_BETA_WORKSPACE_CONTEXT_ACCEPTANCE', False)
    monkeypatch.setattr(
        app.memory_optimizer, 'get_memory_optimizer',
        lambda: SimpleNamespace(start_monitoring=lambda: None),
    )
    monkeypatch.setattr(
        app.stability_monitor, 'get_stability_monitor',
        lambda: SimpleNamespace(start_monitoring=lambda: None),
    )
    monkeypatch.setattr(
        intelligence, '_chat',
        lambda *_args, **_kwargs: calls.append('inference') or ('ok', 'retired'),
    )
    # Exercise any registered heartbeat once without starting a background thread
    # or contacting a provider. A safe metadata-only heartbeat may still register.
    monkeypatch.setattr(channel, 'start_health_monitor', lambda probe, **_kwargs: probe())

    assert app._start_app_automations(SimpleNamespace(
        no_scheduler=True, internal_beta_acceptance=False,
        internal_beta_workspace_context_acceptance=False,
    )) is True
    assert calls == []


def test_ordinary_startup_cdp_status_uses_approved_collection_account(monkeypatch):
    import cdp_helper
    import logging

    ports = []
    monkeypatch.setattr(app, 'INTERNAL_BETA_SAFE_STARTUP', False)
    monkeypatch.setattr(app, 'logging', logging, raising=False)
    monkeypatch.setenv('ZBC_GUARDIAN_ENABLED', '0')
    monkeypatch.setattr(app.runtime_preflight, 'run_preflight', lambda: {})
    monkeypatch.setattr(app.runtime_preflight, 'format_summary', lambda _report: '')
    monkeypatch.setattr(
        cdp_helper, 'get_cdp_status',
        lambda port=cdp_helper.DEFAULT_CDP_PORT: ports.append(port) or {'available': False},
    )
    monkeypatch.setattr(
        app.threading, 'Thread',
        lambda **_kwargs: SimpleNamespace(start=lambda: None),
    )
    # The startup helper installs hooks; retain their real prior values on exit.
    monkeypatch.setattr(app.sys, 'excepthook', app.sys.excepthook)
    monkeypatch.setattr(app.threading, 'excepthook', app.threading.excepthook)

    assert app._start_optional_runtime_services(False) is True
    assert ports == [app.xhs_cookie_bridge.cdp_port_for(
        app.xhs_cookie_bridge.DEFAULT_COLLECTION_ACCOUNT,
    )]
    assert 9222 not in ports


def test_automatic_collection_startup_is_manual_without_full_opt_in(monkeypatch):
    for name in (
        'REDNOTE_AUTO_RUN', 'REDNOTE_AUTO_SCOPE', 'REDNOTE_AUTO_SOURCE',
        'REDNOTE_AUTO_CADENCE_MINUTES',
    ):
        monkeypatch.delenv(name, raising=False)

    assert app._automatic_collection_opted_in() is False

    monkeypatch.setenv('REDNOTE_AUTO_RUN', 'true')
    assert app._automatic_collection_opted_in() is False

    monkeypatch.setenv('REDNOTE_AUTO_SCOPE', 'GUANGZHOU_TAIKOO_HUI')
    monkeypatch.setenv('REDNOTE_AUTO_SOURCE', 'rednote_hk')
    monkeypatch.setenv('REDNOTE_AUTO_CADENCE_MINUTES', '720')
    assert app._automatic_collection_opted_in() is True


def test_bridge_rejects_scheduled_collection_before_identity_checks(monkeypatch):
    for name in (
        'REDNOTE_AUTO_RUN', 'REDNOTE_AUTO_SCOPE', 'REDNOTE_AUTO_SOURCE',
        'REDNOTE_AUTO_CADENCE_MINUTES',
    ):
        monkeypatch.delenv(name, raising=False)

    # Use the same valid registry shape as the acquisition-plan tests, then
    # let the bridge build its bounded plan through the canonical resolver.
    monkeypatch.setattr('subject_registry.list_subjects', lambda: [
        {
            'subject_id': 'CTH-NORTH-1',
            'domain_id': 'CTH',
            'subject_type': 'company',
            'name_en': 'North Star Mall',
            'keywords': ['North Star'],
            'status': 'configured',
        },
        {
            'subject_id': 'BMP-NORTH-1',
            'brand_focus_id': 'BRAND-NORTH-1',
            'domain_id': 'BMP',
            'subject_type': 'brand',
            'name_en': 'North Star Brand',
            'keywords': ['North Brand'],
            'status': 'configured',
        },
    ])
    plan = app.xhs_cookie_bridge._resolve_acquisition_plan()
    assert plan.status == 'READY'
    assert plan.is_runnable is True
    assert len(plan.queries) <= plan.query_limit

    identity_checks = []
    monkeypatch.setattr(
        app.xhs_cookie_bridge, 'collection_policy_gate',
        lambda **_kwargs: identity_checks.append('policy') or {'ok': True},
    )

    with pytest.raises(RuntimeError, match='Automatic collection is blocked'):
        app.xhs_cookie_bridge.create_task(run_type='auto')

    assert identity_checks == []


def test_manual_mode_suppresses_rednote_resident_until_explicit_auto_opt_in(monkeypatch):
    events = []
    monkeypatch.setattr(app, 'INTERNAL_BETA_SAFE_STARTUP', False)
    monkeypatch.setattr(
        app.threading, 'Thread',
        lambda **_kwargs: SimpleNamespace(start=lambda: events.append('scheduler')),
    )
    monkeypatch.setattr(app.xhs_p0_orchestrator, 'start_resident', lambda: events.append('resident'))
    monkeypatch.setattr(
        app.memory_optimizer, 'get_memory_optimizer',
        lambda: SimpleNamespace(start_monitoring=lambda: None),
    )
    monkeypatch.setattr(
        app.stability_monitor, 'get_stability_monitor',
        lambda: SimpleNamespace(start_monitoring=lambda: None),
    )
    from lumenis.system.ai_gateway import channel
    monkeypatch.setattr(channel, 'start_health_monitor', lambda *_args, **_kwargs: None)
    for name in (
        'REDNOTE_AUTO_RUN', 'REDNOTE_AUTO_SCOPE', 'REDNOTE_AUTO_SOURCE',
        'REDNOTE_AUTO_CADENCE_MINUTES',
    ):
        monkeypatch.delenv(name, raising=False)

    args = SimpleNamespace(
        no_scheduler=False, internal_beta_acceptance=False,
        internal_beta_workspace_context_acceptance=False,
    )
    assert app._start_app_automations(args) is True
    assert events == ['scheduler']

    monkeypatch.setenv('REDNOTE_AUTO_RUN', 'true')
    monkeypatch.setenv('REDNOTE_AUTO_SCOPE', 'GUANGZHOU_TAIKOO_HUI')
    monkeypatch.setenv('REDNOTE_AUTO_SOURCE', 'rednote_hk')
    monkeypatch.setenv('REDNOTE_AUTO_CADENCE_MINUTES', '720')
    assert app._start_app_automations(args) is True
    assert events == ['scheduler', 'scheduler', 'resident']

    args.no_scheduler = True
    assert app._start_app_automations(args) is True
    assert events == ['scheduler', 'scheduler', 'resident']


def test_manual_scheduler_does_not_probe_rednote_session(monkeypatch):
    from datetime import datetime as real_datetime
    for name in (
        'REDNOTE_AUTO_RUN', 'REDNOTE_AUTO_SCOPE', 'REDNOTE_AUTO_SOURCE',
        'REDNOTE_AUTO_CADENCE_MINUTES',
    ):
        monkeypatch.delenv(name, raising=False)

    def forbidden(*_args, **_kwargs):
        raise AssertionError('manual mode must not probe session or collection scheduler')

    class FixedDatetime:
        @staticmethod
        def now():
            return real_datetime(2026, 9, 27, 10, 10)

    monkeypatch.setattr(app, 'datetime', FixedDatetime)
    monkeypatch.setattr(app, '_get_shadow_planner', forbidden)
    monkeypatch.setattr(app.xhs_cookie_bridge, 'check_rate_limit', forbidden)
    monkeypatch.setitem(sys.modules, 'xhs_collection_optimizer',
                        SimpleNamespace(recheck_keepalive=forbidden))

    def stop_after_first_tick(_seconds):
        raise StopIteration

    monkeypatch.setattr(app.time, 'sleep', stop_after_first_tick)
    with pytest.raises(StopIteration):
        app.scheduler_loop()
