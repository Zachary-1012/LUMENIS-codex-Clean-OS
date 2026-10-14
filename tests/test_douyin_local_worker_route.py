"""Offline routing and resident-launcher contracts for the isolated Douyin worker."""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


def test_remote_worker_configuration_remains_unchanged(monkeypatch):
    from lumenis.adapters.douyin import _configured_browser_worker_url

    monkeypatch.setenv('DOUYIN_CDP_URL', 'https://worker.example:9443')
    monkeypatch.delenv('DOUYIN_LOCAL_WORKER_ENABLED', raising=False)
    monkeypatch.delenv('DOUYIN_LOCAL_WORKER_ACCOUNT', raising=False)
    assert _configured_browser_worker_url() == 'https://worker.example:9443'


def test_exact_local_douyin_worker_requires_opt_in_and_profile_owner(monkeypatch, tmp_path):
    import cdp_helper
    from lumenis.adapters import douyin

    monkeypatch.setenv('DOUYIN_CDP_URL', 'http://127.0.0.1:9225')
    monkeypatch.setenv('DOUYIN_LOCAL_WORKER_ENABLED', 'true')
    monkeypatch.setenv('DOUYIN_LOCAL_WORKER_ACCOUNT', 'DOUYIN_READONLY')
    monkeypatch.setenv('ZBC_DATA_DIR', str(tmp_path))
    seen = {}

    def registered_owner(port, profile_dir, *, headless):
        seen.update(port=port, profile=profile_dir, headless=headless)
        return 'edge' if port == 9225 and headless is True else None

    monkeypatch.setattr(cdp_helper, 'registered_cdp_browser_for_port', registered_owner)
    assert douyin._configured_browser_worker_url() == 'http://127.0.0.1:9225'
    assert seen['port'] == 9225
    assert Path(seen['profile']).parts[-3:] == ('private', 'profiles', 'douyin-readonly')
    assert seen['headless'] is True


@pytest.mark.parametrize('url', [
    'http://127.0.0.1:9222',
    'http://127.0.0.1:9223',
    'http://127.0.0.1:9224',
    'http://127.0.0.1:9226',
    'http://localhost:9225',
    'http://localhost.:9225',
    'http://127.0.0.1.:9225',
    'http://0.0.0.0:9225',
    'http://[::1]:9225',
    'http://user:pass@127.0.0.1:9225',
    'http://127.0.0.1:9225/path',
    'http://127.0.0.1:9225/?query=1',
    'http://127.0.0.1:9225/#fragment',
])
def test_local_worker_rejects_nonexact_endpoint(monkeypatch, url):
    from lumenis.adapters.douyin import _configured_browser_worker_url

    monkeypatch.setenv('DOUYIN_CDP_URL', url)
    monkeypatch.setenv('DOUYIN_LOCAL_WORKER_ENABLED', '1')
    monkeypatch.setenv('DOUYIN_LOCAL_WORKER_ACCOUNT', 'DOUYIN_READONLY')
    with pytest.raises(RuntimeError):
        _configured_browser_worker_url()


@pytest.mark.parametrize(('enabled', 'account'), [
    ('', 'DOUYIN_READONLY'),
    ('1', ''),
    ('1', 'XHS_RETINAUT'),
])
def test_local_worker_requires_explicit_identity_opt_in(monkeypatch, enabled, account):
    from lumenis.adapters.douyin import _configured_browser_worker_url

    monkeypatch.setenv('DOUYIN_CDP_URL', 'http://127.0.0.1:9225')
    monkeypatch.setenv('DOUYIN_LOCAL_WORKER_ENABLED', enabled)
    monkeypatch.setenv('DOUYIN_LOCAL_WORKER_ACCOUNT', account)
    with pytest.raises(RuntimeError, match='opted-in'):
        _configured_browser_worker_url()


def test_local_endpoint_rejected_when_process_profile_does_not_match(monkeypatch):
    import cdp_helper
    from lumenis.adapters import douyin

    monkeypatch.setenv('DOUYIN_CDP_URL', 'http://127.0.0.1:9225')
    monkeypatch.setenv('DOUYIN_LOCAL_WORKER_ENABLED', '1')
    monkeypatch.setenv('DOUYIN_LOCAL_WORKER_ACCOUNT', 'DOUYIN_READONLY')
    monkeypatch.setattr(cdp_helper, 'registered_cdp_browser_for_port',
                        lambda port, _profile, *, headless: None
                        if port == 9225 and headless is True else 'edge')
    with pytest.raises(RuntimeError, match='READONLY_WORKER_PROFILE_MODE_OR_KERNEL_UNAVAILABLE'):
        douyin._configured_browser_worker_url()


def test_douyin_process_helper_matches_port_and_exact_profile(monkeypatch, tmp_path):
    import cdp_helper

    # The registered worker profile is rooted in the current protected data
    # directory; bind that existing runtime contract to this test's isolated root.
    monkeypatch.setenv('ZBC_DATA_DIR', str(tmp_path))
    profile = str(tmp_path / 'private' / 'profiles' / 'douyin-readonly')
    def fake_process(process_profile, port, address='127.0.0.1'):
        name = 'msedge.exe'
        args = [name, f'--remote-debugging-port={port}',
                f'--remote-debugging-address={address}',
                f'--user-data-dir={process_profile}']
        return SimpleNamespace(
            info={'name': name, 'cmdline': args},
            name=lambda: name,
            cmdline=lambda: list(args),
        )

    processes = {
        11: fake_process(profile, 9223),
        12: fake_process(str(tmp_path / 'other'), 9225),
        13: fake_process(profile, 9225),
        14: fake_process(profile, 9225, address='0.0.0.0'),
    }
    active_pid = {'value': 13}
    process_module = SimpleNamespace(
        process_iter=lambda _attrs: list(processes.values()),
        Process=lambda pid: processes[int(pid)],
    )
    monkeypatch.setitem(sys.modules, 'psutil', process_module)
    monkeypatch.setattr(cdp_helper, '_cdp_listener_pids',
                        lambda _port: ({active_pid['value']}, True))

    assert cdp_helper.is_cdp_profile_running(9225, profile) is True
    active_pid['value'] = 11
    assert cdp_helper.is_cdp_profile_running(9225, profile) is False
    active_pid['value'] = 12
    assert cdp_helper.is_cdp_profile_running(9225, profile) is False
    active_pid['value'] = 14
    assert cdp_helper.is_cdp_profile_running(9225, profile) is False


def test_douyin_resident_profile_plan_is_exact_and_isolated(tmp_path):
    from scripts import start_resident_browsers as launcher

    plan = launcher.douyin_worker_spec(str(tmp_path))
    assert plan == {
        'account': 'DOUYIN_READONLY',
        'port': 9225,
        'profile': str(tmp_path / 'profiles' / 'douyin-readonly'),
        'env_prefix': 'DOUYIN',
        'home': 'about:blank',
        'direct': False,
    }


def test_douyin_launch_uses_system_default_and_loopback_only(monkeypatch, tmp_path):
    from scripts import start_resident_browsers as launcher

    plan = {'account': 'DOUYIN_READONLY', 'port': 9225,
            'profile': str(tmp_path / 'profiles' / 'douyin-readonly'),
            'env_prefix': 'DOUYIN',
            'home': 'about:blank', 'direct': False}
    monkeypatch.setattr(launcher, 'douyin_worker_spec', lambda: plan)
    monkeypatch.setattr(launcher, 'port_online', lambda _port: False)
    monkeypatch.setattr(launcher.cdp_helper, 'system_default_cdp_browser', lambda: 'chrome')
    monkeypatch.setattr(launcher.os, 'makedirs', lambda *_args, **_kwargs: None)
    seen = {}

    def fake_start(**kwargs):
        seen.update(kwargs)
        return {'success': True, 'pid': 123, 'message': 'started'}

    monkeypatch.setattr(launcher.cdp_helper, 'start_cdp_browser', fake_start)
    owner_check = Mock(return_value=True)
    monkeypatch.setattr(launcher.cdp_helper, 'is_cdp_profile_running', owner_check)

    row = launcher.launch_douyin_readonly()

    assert row['online'] is True
    owner_check.assert_called_once_with(
        9225, plan['profile'], headless=True, loopback_only=True, browser='chrome')
    assert seen == {
        'port': 9225, 'profile_dir': plan['profile'], 'launch_url': plan['home'],
        'direct_connection': False, 'browser': 'chrome', 'headless': True,
        'loopback_only': True, 'task_id': None, 'actor_ref': None,
    }


def test_douyin_launcher_fails_closed_on_occupied_port_or_unsupported_default(monkeypatch):
    from scripts import start_resident_browsers as launcher

    monkeypatch.setattr(launcher, 'port_online', lambda _port: True)
    monkeypatch.setattr(launcher.cdp_helper, 'system_default_cdp_browser', lambda: 'edge')
    monkeypatch.setattr(launcher.cdp_helper, 'start_cdp_browser',
                        lambda **_kwargs: pytest.fail('must not reuse unknown port owner'))
    assert launcher.launch_douyin_readonly()['action'] == 'port_in_use_unverified'

    monkeypatch.setattr(launcher, 'port_online', lambda _port: False)
    monkeypatch.setattr(launcher.cdp_helper, 'system_default_cdp_browser', lambda: None)
    row = launcher.launch_douyin_readonly()
    assert row['action'] == 'unsupported_system_default_browser'


def test_douyin_launcher_reuses_only_exact_existing_profile(monkeypatch, tmp_path):
    from scripts import start_resident_browsers as launcher

    plan = {'account': 'DOUYIN_READONLY', 'port': 9225,
            'profile': str(tmp_path / 'profiles' / 'douyin-readonly'),
            'env_prefix': 'DOUYIN',
            'home': 'about:blank', 'direct': False}
    monkeypatch.setattr(launcher, 'douyin_worker_spec', lambda: plan)
    monkeypatch.setattr(launcher, 'port_online', lambda _port: True)
    monkeypatch.setattr(launcher.cdp_helper, 'system_default_cdp_browser', lambda: 'edge')
    monkeypatch.setattr(launcher.cdp_helper, 'start_cdp_browser',
                        lambda **_kwargs: pytest.fail('occupied port must not launch/reuse'))

    def registered_owner(port, profile, *, headless):
        if port == 9225 and profile == plan['profile'] and headless is True:
            return 'edge'
        return None

    monkeypatch.setattr(launcher.cdp_helper, 'registered_cdp_browser_for_port', registered_owner)
    monkeypatch.setattr(launcher.cdp_helper, 'is_cdp_profile_running',
                        lambda port, profile, **kwargs:
                        port == 9225 and profile == plan['profile']
                        and kwargs == {'headless': True, 'loopback_only': True,
                                       'browser': 'edge'})
    assert launcher.launch_douyin_readonly()['action'] == 'already_online'

    monkeypatch.setattr(launcher.cdp_helper, 'registered_cdp_browser_for_port',
                        lambda *_args, **_kwargs: None)
    assert launcher.launch_douyin_readonly()['action'] == 'port_in_use_unverified'


def test_default_resident_start_does_not_provision_douyin(monkeypatch):
    from scripts import start_resident_browsers as launcher

    calls = []
    monkeypatch.setattr(sys, 'argv', ['start_resident_browsers.py'])
    monkeypatch.setattr(launcher, 'launch_one', lambda account, direct, status_only=False:
                        (calls.append(('resident', account)) or {
                            'account': account, 'port': 9223, 'online': True,
                            'profile': 'existing', 'home': 'https://www.rednote.com',
                            'action': 'already_online', 'pages': [], 'direct': direct}))
    monkeypatch.setattr(launcher, 'launch_general', lambda status_only=False:
                        (calls.append(('general',)) or {
                            'account': 'GENERAL_BROWSE', 'port': 9224, 'online': True,
                            'profile': 'general', 'home': 'https://www.bing.com',
                            'action': 'already_online', 'pages': [], 'direct': True}))
    monkeypatch.setattr(launcher, 'launch_douyin_readonly', lambda **_kwargs:
                        calls.append(('douyin',)))

    assert launcher.main() == 0
    assert calls == [('resident', 'XHS_RETINAUT'), ('general',)]


def test_explicit_douyin_account_selects_only_douyin_launcher(monkeypatch):
    from scripts import start_resident_browsers as launcher

    calls = []
    monkeypatch.setattr(sys, 'argv', ['start_resident_browsers.py', '--account', 'DOUYIN_READONLY'])
    monkeypatch.setattr(launcher, 'launch_douyin_readonly', lambda status_only=False:
                        {'account': 'DOUYIN_READONLY', 'port': 9225, 'online': True,
                         'browser': 'edge', 'profile': 'isolated-profile',
                         'home': 'about:blank', 'action': 'started'})
    monkeypatch.setattr(launcher, 'launch_one', lambda *_args, **_kwargs:
                        calls.append('existing resident'))
    monkeypatch.setattr(launcher, 'launch_general', lambda *_args, **_kwargs:
                        calls.append('general'))

    assert launcher.main() == 0
    assert calls == []
