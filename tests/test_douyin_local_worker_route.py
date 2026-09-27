"""Offline routing and resident-launcher contracts for the isolated Douyin worker."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_remote_worker_configuration_remains_unchanged(monkeypatch):
    from lumenis.adapters.douyin import _configured_browser_worker_url

    monkeypatch.setenv('DOUYIN_CDP_URL', 'https://worker.example:9443')
    monkeypatch.delenv('DOUYIN_LOCAL_WORKER_ENABLED', raising=False)
    monkeypatch.delenv('DOUYIN_LOCAL_WORKER_ACCOUNT', raising=False)
    assert _configured_browser_worker_url() == 'https://worker.example:9443'


def test_exact_local_douyin_worker_requires_opt_in_and_profile_owner(monkeypatch, tmp_path):
    from lumenis.adapters import douyin
    import cdp_helper

    monkeypatch.setenv('DOUYIN_CDP_URL', 'http://127.0.0.1:9225')
    monkeypatch.setenv('DOUYIN_LOCAL_WORKER_ENABLED', 'true')
    monkeypatch.setenv('DOUYIN_LOCAL_WORKER_ACCOUNT', 'DOUYIN_READONLY')
    monkeypatch.setenv('ZBC_DATA_DIR', str(tmp_path))
    seen = {}

    def owns_profile(port, profile_dir):
        seen['port'] = port
        seen['profile'] = profile_dir
        return True

    monkeypatch.setattr(cdp_helper, 'is_cdp_profile_running', owns_profile)
    assert douyin._configured_browser_worker_url() == 'http://127.0.0.1:9225'
    assert seen['port'] == 9225
    assert Path(seen['profile']).parts[-3:] == ('private', 'profiles', 'douyin-readonly')


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
    from lumenis.adapters import douyin
    import cdp_helper

    monkeypatch.setenv('DOUYIN_CDP_URL', 'http://127.0.0.1:9225')
    monkeypatch.setenv('DOUYIN_LOCAL_WORKER_ENABLED', '1')
    monkeypatch.setenv('DOUYIN_LOCAL_WORKER_ACCOUNT', 'DOUYIN_READONLY')
    monkeypatch.setattr(cdp_helper, 'is_cdp_profile_running', lambda *_args: False)
    with pytest.raises(RuntimeError, match='profile is not bound'):
        douyin._configured_browser_worker_url()


def test_douyin_process_helper_matches_port_and_exact_profile(monkeypatch, tmp_path):
    import cdp_helper

    profile = str(tmp_path / 'private' / 'profiles' / 'douyin-readonly')
    good = SimpleNamespace(info={
        'name': 'msedge.exe',
        'cmdline': ['msedge.exe', '--remote-debugging-port=9225',
                    '--remote-debugging-address=127.0.0.1', f'--user-data-dir={profile}'],
    })
    bad_port = SimpleNamespace(info={
        'name': 'msedge.exe',
        'cmdline': ['msedge.exe', '--remote-debugging-port=9223',
                    '--remote-debugging-address=127.0.0.1', f'--user-data-dir={profile}'],
    })
    bad_profile = SimpleNamespace(info={
        'name': 'msedge.exe',
        'cmdline': ['msedge.exe', '--remote-debugging-port=9225',
                    '--remote-debugging-address=127.0.0.1', f'--user-data-dir={tmp_path / "other"}'],
    })
    process_module = SimpleNamespace(process_iter=lambda _attrs: [bad_port, bad_profile, good])
    monkeypatch.setitem(sys.modules, 'psutil', process_module)

    assert cdp_helper.is_cdp_profile_running(9225, profile) is True
    process_module.process_iter = lambda _attrs: [bad_port, bad_profile]
    assert cdp_helper.is_cdp_profile_running(9225, profile) is False

    public_bind = SimpleNamespace(info={
        'name': 'msedge.exe',
        'cmdline': ['msedge.exe', '--remote-debugging-port=9225',
                    '--remote-debugging-address=0.0.0.0', f'--user-data-dir={profile}'],
    })
    process_module.process_iter = lambda _attrs: [public_bind]
    assert cdp_helper.is_cdp_profile_running(9225, profile) is False


def test_douyin_resident_profile_plan_is_exact_and_isolated(tmp_path):
    from scripts import start_resident_browsers as launcher

    plan = launcher.douyin_worker_spec(str(tmp_path))
    assert plan == {
        'account': 'DOUYIN_READONLY',
        'port': 9225,
        'profile': str(tmp_path / 'profiles' / 'douyin-readonly'),
        'home': 'https://www.douyin.com',
        'direct': False,
    }


def test_douyin_launch_uses_system_default_and_loopback_only(monkeypatch, tmp_path):
    from scripts import start_resident_browsers as launcher

    plan = {'account': 'DOUYIN_READONLY', 'port': 9225,
            'profile': str(tmp_path / 'profiles' / 'douyin-readonly'),
            'home': 'https://www.douyin.com', 'direct': False}
    monkeypatch.setattr(launcher, 'douyin_worker_spec', lambda: plan)
    monkeypatch.setattr(launcher, 'port_online', lambda _port: False)
    monkeypatch.setattr(launcher.cdp_helper, 'system_default_cdp_browser', lambda: 'chrome')
    monkeypatch.setattr(launcher.os, 'makedirs', lambda *_args, **_kwargs: None)
    seen = {}

    def fake_start(**kwargs):
        seen.update(kwargs)
        return {'success': True, 'pid': 123, 'message': 'started'}

    monkeypatch.setattr(launcher.cdp_helper, 'start_cdp_browser', fake_start)
    online = iter([False, True])
    monkeypatch.setattr(launcher, 'port_online', lambda _port: next(online))

    row = launcher.launch_douyin_readonly()

    assert row['online'] is True
    assert seen == {
        'port': 9225, 'profile_dir': plan['profile'], 'launch_url': plan['home'],
        'direct_connection': False, 'browser': 'chrome', 'loopback_only': True,
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
            'home': 'https://www.douyin.com', 'direct': False}
    monkeypatch.setattr(launcher, 'douyin_worker_spec', lambda: plan)
    monkeypatch.setattr(launcher, 'port_online', lambda _port: True)
    monkeypatch.setattr(launcher.cdp_helper, 'system_default_cdp_browser', lambda: 'edge')
    monkeypatch.setattr(launcher.cdp_helper, 'start_cdp_browser',
                        lambda **_kwargs: pytest.fail('occupied port must not launch/reuse'))

    monkeypatch.setattr(launcher.cdp_helper, 'is_cdp_profile_running',
                        lambda port, profile: port == 9225 and profile == plan['profile'])
    assert launcher.launch_douyin_readonly()['action'] == 'already_online'

    monkeypatch.setattr(launcher.cdp_helper, 'is_cdp_profile_running', lambda *_args: False)
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
                         'home': 'https://www.douyin.com', 'action': 'started'})
    monkeypatch.setattr(launcher, 'launch_one', lambda *_args, **_kwargs:
                        calls.append('existing resident'))
    monkeypatch.setattr(launcher, 'launch_general', lambda *_args, **_kwargs:
                        calls.append('general'))

    assert launcher.main() == 0
    assert calls == []
