"""Offline contract tests for the explicitly approved HK local worker route."""
from types import SimpleNamespace
from typing import ClassVar

import pytest

TEST_HK_ID = 'a' * 24
TEST_WORKER_PORT = 9234


def _patch_registered_worker(monkeypatch, *, port=TEST_WORKER_PORT, available=True,
                             code='XHS_REGISTERED_WORKER_UNAVAILABLE'):
    import cdp_helper

    state = ({
        'available': True, 'account': 'XHS_RETINAUT', 'profile': 'registered-profile',
        'browser': 'edge', 'port': port, 'endpoint': f'http://127.0.0.1:{port}',
        'headless': True, 'loopback_only': True,
    } if available else {'available': False, 'account': 'XHS_RETINAUT', 'code': code})
    monkeypatch.setattr(cdp_helper, 'resolve_registered_xhs_worker',
                        lambda **_kwargs: dict(state))


def _configure_remote_worker(monkeypatch, endpoint='https://worker.example:9443',
                             user_id='synthetic-approved-user-id'):
    import collector
    import xhs_cookie_bridge as bridge

    monkeypatch.setenv('XHS_CDP_URL', endpoint)
    monkeypatch.setattr(collector, 'CDP_URL', endpoint)
    monkeypatch.setattr(bridge, 'XHS_RETINAUT', user_id)
    monkeypatch.setattr(bridge, 'ALLOWED_USER_IDS', (user_id,))
    monkeypatch.setattr(
        bridge, 'collection_policy_gate',
        lambda account=None, region='intl': {
            'ok': True, 'account': account, 'region': region,
        },
    )


class _FakePage:
    def __init__(self, links, url='https://www.rednote.com/explore'):
        self.links = links
        self.url = url

    def locator(self, _selector):
        return SimpleNamespace(evaluate_all=lambda _script: self.links)


def _identity_context(cookies, ids=(), *, author_links=(), page_url='https://www.rednote.com/explore', extra_pages=()):
    links = [
        {'classes': [css_class], 'text': '我', 'href': f'/user/profile/{user_id}'}
        for css_class, user_id in ids
    ]
    links.extend(author_links)
    pages = [_FakePage(links, url=page_url)]
    pages.extend(extra_pages)
    return SimpleNamespace(cookies=lambda _urls: cookies, pages=pages)


@pytest.mark.parametrize('candidate', [
    f'http://127.0.0.1:{TEST_WORKER_PORT}',
    f'http://127.0.0.1:{TEST_WORKER_PORT}/',
])
def test_approved_identity_can_resolve_exact_local_worker(monkeypatch, candidate):
    import collector

    _patch_registered_worker(monkeypatch)
    monkeypatch.setattr(collector, '_approved_local_profile_contract',
                        lambda account, region: TEST_HK_ID)
    endpoint, error = collector._resolve_server_cdp_url(
        candidate, account='XHS_RETINAUT', region='intl')

    assert endpoint == f'http://127.0.0.1:{TEST_WORKER_PORT}'
    assert error == ''


def test_approved_online_local_worker_is_discovered_without_config(monkeypatch):
    import collector

    class _Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.delenv('XHS_CDP_URL', raising=False)
    monkeypatch.setattr(collector, 'CDP_URL', '')
    monkeypatch.setattr(collector, '_approved_local_profile_contract',
                        lambda account, region: TEST_HK_ID)
    _patch_registered_worker(monkeypatch)
    monkeypatch.setattr('urllib.request.urlopen',
                        lambda *_args, **_kwargs: (_ for _ in ()).throw(
                            AssertionError('Endpoint resolution must use the SYSTEM owner, not a port probe')))

    endpoint, error = collector._resolve_server_cdp_url(
        account='XHS_RETINAUT', region='intl')

    assert endpoint == f'http://127.0.0.1:{TEST_WORKER_PORT}'
    assert error == ''


def test_approved_offline_local_worker_keeps_fail_closed(monkeypatch):
    import collector

    monkeypatch.delenv('XHS_CDP_URL', raising=False)
    monkeypatch.setattr(collector, 'CDP_URL', '')
    monkeypatch.setattr(collector, '_approved_local_profile_contract',
                        lambda account, region: TEST_HK_ID)
    _patch_registered_worker(monkeypatch, available=False,
                             code='XHS_REGISTERED_WORKER_UNAVAILABLE')
    monkeypatch.setattr('urllib.request.urlopen',
                        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError('offline')))

    endpoint, error = collector._resolve_server_cdp_url(
        account='XHS_RETINAUT', region='intl')

    assert endpoint == ''
    assert error == 'XHS_REGISTERED_WORKER_UNAVAILABLE'


@pytest.mark.parametrize(('candidate', 'account', 'region', 'profile_id', 'expected_error'), [
    ('', 'XHS_RETINAUT', 'intl', TEST_HK_ID, 'XHS_REGISTERED_WORKER_UNAVAILABLE'),
    ('http://127.0.0.1:9222', 'XHS_RETINAUT', 'intl', TEST_HK_ID, 'COLLECTOR_ENDPOINT_OWNER_MISMATCH'),
    (f'http://localhost:{TEST_WORKER_PORT}', 'XHS_RETINAUT', 'intl', TEST_HK_ID, 'COLLECTOR_ENDPOINT_OWNER_MISMATCH'),
    (f'http://127.0.0.1:{TEST_WORKER_PORT}', 'XHS_CN_PRIMARY', 'cn', None, 'POLICY_BLOCKED'),
    (f'http://127.0.0.1:{TEST_WORKER_PORT}', 'XHS_RETINAUT', 'cn', None, 'POLICY_BLOCKED'),
    (f'http://127.0.0.1:{TEST_WORKER_PORT}/unknown', 'XHS_RETINAUT', 'intl', TEST_HK_ID, 'COLLECTOR_ENDPOINT_OWNER_MISMATCH'),
])
def test_unapproved_local_routes_fail_closed(monkeypatch, candidate, account, region,
                                              profile_id, expected_error):
    import collector

    monkeypatch.setattr(collector, '_approved_local_profile_contract',
                        lambda requested_account, requested_region: profile_id)
    _patch_registered_worker(monkeypatch)
    if not candidate:
        # Do not inspect the host's process list in this isolated no-worker case.
        _patch_registered_worker(monkeypatch, available=False,
                                 code='XHS_REGISTERED_WORKER_UNAVAILABLE')
    endpoint, error = collector._resolve_server_cdp_url(
        candidate, account=account, region=region)

    assert endpoint == ''
    assert error == expected_error


def test_remote_worker_config_is_not_identity_authority(monkeypatch):
    import cdp_helper
    import collector

    _configure_remote_worker(monkeypatch)
    monkeypatch.setattr(
        cdp_helper, 'resolve_registered_xhs_worker',
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError('Remote configuration must be rejected before local discovery')),
    )
    endpoint, error = collector._resolve_server_cdp_url(
        'https://worker.example:9443', account='XHS_RETINAUT', region='intl')

    assert endpoint == ''
    assert error == 'COLLECTOR_REMOTE_WORKER_IDENTITY_UNVERIFIED'


def test_remote_worker_config_is_rejected_before_network_probe(monkeypatch):
    import urllib.request

    import collector

    _configure_remote_worker(monkeypatch)
    monkeypatch.setattr(
        urllib.request, 'urlopen',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError('Unregistered remote workers must not receive a network request')),
    )

    assert collector._cdp_online(
        timeout=0.1, cdp_url='https://worker.example:9443',
        account='XHS_RETINAUT', region='intl') is False

    import xhs_cookie_bridge as bridge
    monkeypatch.setattr(bridge, 'collection_policy_gate',
                        lambda **_kwargs: {'ok': False, 'code': 'account_paused',
                                           'account': 'XHS_RETINAUT', 'region': 'intl'})
    endpoint, error = collector._resolve_server_cdp_url(
        'https://worker.example:9443', account='XHS_RETINAUT', region='intl')
    assert endpoint == ''
    assert error == 'POLICY_BLOCKED'


def test_remote_worker_requires_server_config_and_exact_hk_policy(monkeypatch):
    import cdp_helper
    import collector

    monkeypatch.delenv('XHS_CDP_URL', raising=False)
    monkeypatch.setattr(collector, 'CDP_URL', '')
    monkeypatch.setattr(collector, '_approved_local_profile_contract', lambda *_args: None)
    monkeypatch.setattr(
        cdp_helper, 'resolve_registered_xhs_worker',
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError('A remote caller URL must not trigger local worker discovery')),
    )
    endpoint, error = collector._resolve_server_cdp_url(
        'https://worker.example:9443', account='XHS_RETINAUT', region='intl')
    assert endpoint == ''
    assert error == 'COLLECTOR_ENDPOINT_NOT_CONFIGURED'

    _configure_remote_worker(monkeypatch, 'https://worker.example:9443')
    endpoint, error = collector._resolve_server_cdp_url(
        'https://worker.example:9443', account='XHS_RETINAUT', region='intl')
    assert endpoint == ''
    assert error == 'COLLECTOR_REMOTE_WORKER_IDENTITY_UNVERIFIED'
    endpoint, error = collector._resolve_server_cdp_url(
        'https://other-worker.example:9443', account='XHS_RETINAUT', region='intl')
    assert endpoint == ''
    assert error == 'COLLECTOR_ENDPOINT_OWNER_MISMATCH'


@pytest.mark.parametrize('endpoint', [
    'https://user:pass@worker.example:9443',
    'https://worker.example:9443/path',
    'https://worker.example:9443/?token=secret',
    'https://worker.example:9443/#fragment',
    'http://127.0.0.1:9223',
    'http://worker.example:9222',
])
def test_remote_worker_server_config_rejects_unsafe_endpoint_shape(monkeypatch, endpoint):
    import collector

    _configure_remote_worker(monkeypatch, endpoint)
    resolved, error = collector._resolve_server_cdp_url(
        account='XHS_RETINAUT', region='intl')
    assert resolved == ''
    assert error == 'COLLECTOR_ENDPOINT_INVALID'


def test_local_route_profile_contract_matches_registered_hk_profile(monkeypatch, tmp_path):
    import collector
    import xhs_cookie_bridge as bridge

    registered = str(tmp_path / 'profiles' / 'xhs-retinaut')
    monkeypatch.setattr(bridge, 'PRIVATE_DATA_DIR', str(tmp_path))
    monkeypatch.setitem(bridge.ACCOUNT_PROFILES, bridge.XHS_RETINAUT_NAME,
                        ('private-cookie-path-not-read', registered))
    monkeypatch.setitem(bridge.ACCOUNT_CDP_PORTS, bridge.XHS_RETINAUT_NAME, None)
    assert bridge.ACCOUNT_CDP_PORTS[bridge.XHS_RETINAUT_NAME] is None
    assert collector._approved_local_profile_contract(
        bridge.XHS_RETINAUT_NAME, 'intl') == bridge.XHS_RETINAUT

    monkeypatch.setitem(bridge.ACCOUNT_PROFILES, bridge.XHS_RETINAUT_NAME,
                        ('private-cookie-path-not-read', str(tmp_path / 'profiles' / 'unknown')))
    assert collector._approved_local_profile_contract(
        bridge.XHS_RETINAUT_NAME, 'intl') is None


def test_attached_context_must_have_exact_expected_hk_identity(monkeypatch):
    import xhs_cdp_collector as worker

    monkeypatch.setenv('XHS_EXPECTED_COLLECTION_USER_ID', TEST_HK_ID)
    context = _identity_context(
        [{'name': 'web_session', 'value': 'test-session'}],
        [('link-wrapper', TEST_HK_ID), ('bottom-channel', TEST_HK_ID)])
    worker._assert_collection_identity(context)


def test_attached_context_accepts_exact_self_navigation_without_identity_cookie(monkeypatch):
    import xhs_cdp_collector as worker

    monkeypatch.setenv('XHS_EXPECTED_COLLECTION_USER_ID', TEST_HK_ID)
    context = _identity_context(
        [{'name': 'web_session', 'value': 'test-session'}],
        [('bottom-channel', TEST_HK_ID)])
    worker._assert_collection_identity(context)


@pytest.mark.parametrize('cookies', [
    [],
    [{'name': 'web_session', 'value': 'test-session'},
     {'name': 'x-user-id-pro', 'value': 'b' * 24}],
    [
        {'name': 'web_session', 'value': 'test-session'},
        {'name': 'x-user-id-pro', 'value': TEST_HK_ID},
        {'name': 'x-user-id-pro', 'value': 'b' * 24},
    ],
])
def test_attached_context_rejects_missing_or_wrong_identity(monkeypatch, cookies):
    import xhs_cdp_collector as worker

    monkeypatch.setenv('XHS_EXPECTED_COLLECTION_USER_ID', TEST_HK_ID)
    context = _identity_context(cookies, [('link-wrapper', TEST_HK_ID)])
    expected_error = ('COLLECTOR_IDENTITY_NOT_VERIFIED'
                      if not any(c.get('name') == 'web_session' for c in cookies)
                      else 'COLLECTOR_IDENTITY_MISMATCH')
    with pytest.raises(RuntimeError, match=expected_error):
        worker._assert_collection_identity(context)


def test_article_author_named_me_does_not_verify_identity(monkeypatch):
    import xhs_cdp_collector as worker

    monkeypatch.setenv('XHS_EXPECTED_COLLECTION_USER_ID', TEST_HK_ID)
    context = _identity_context(
        [{'name': 'web_session', 'value': 'test-session'}],
        author_links=[{'classes': ['author-link'], 'text': '我',
                       'href': f'/user/profile/{TEST_HK_ID}'}])
    with pytest.raises(RuntimeError, match='COLLECTOR_IDENTITY_NOT_VERIFIED'):
        worker._assert_collection_identity(context)


def test_self_navigation_on_non_rednote_page_is_not_trusted(monkeypatch):
    import xhs_cdp_collector as worker

    monkeypatch.setenv('XHS_EXPECTED_COLLECTION_USER_ID', TEST_HK_ID)
    context = _identity_context(
        [{'name': 'web_session', 'value': 'test-session'}],
        [('bottom-channel', TEST_HK_ID)],
        page_url='https://www.xiaohongshu.com/explore')
    with pytest.raises(RuntimeError, match='COLLECTOR_IDENTITY_NOT_VERIFIED'):
        worker._assert_collection_identity(context)


def test_blank_tab_before_valid_rednote_page_does_not_hide_identity(monkeypatch):
    import xhs_cdp_collector as worker

    monkeypatch.setenv('XHS_EXPECTED_COLLECTION_USER_ID', TEST_HK_ID)
    context = _identity_context(
        [{'name': 'web_session', 'value': 'test-session'}],
        [('bottom-channel', TEST_HK_ID)],
        page_url='about:blank',
        extra_pages=[_FakePage([
            {'classes': ['bottom-channel'], 'text': '我',
             'href': f'/user/profile/{TEST_HK_ID}'}
        ])])
    worker._assert_collection_identity(context)


def test_conflicting_self_navigation_ids_reject_identity(monkeypatch):
    import xhs_cdp_collector as worker

    monkeypatch.setenv('XHS_EXPECTED_COLLECTION_USER_ID', TEST_HK_ID)
    context = _identity_context(
        [{'name': 'web_session', 'value': 'test-session'}],
        [('link-wrapper', TEST_HK_ID), ('bottom-channel', 'b' * 24)])
    with pytest.raises(RuntimeError, match='COLLECTOR_IDENTITY_MISMATCH'):
        worker._assert_collection_identity(context)


def test_hk_holder_and_sg_data_country_do_not_replace_exact_self_identity(monkeypatch):
    import xhs_cdp_collector as worker

    monkeypatch.setenv('XHS_EXPECTED_COLLECTION_USER_ID', TEST_HK_ID)
    context = _identity_context(
        [{'name': 'web_session', 'value': 'test-session'},
         {'name': 'x-rednote-holderctry', 'value': 'HK'},
         {'name': 'x-rednote-datactry', 'value': 'SG'}],
        [('bottom-channel', TEST_HK_ID)])
    worker._assert_collection_identity(context)


def test_non_hk_holder_is_rejected_even_when_self_identity_matches(monkeypatch):
    import xhs_cdp_collector as worker

    monkeypatch.setenv('XHS_EXPECTED_COLLECTION_USER_ID', TEST_HK_ID)
    context = _identity_context(
        [{'name': 'web_session', 'value': 'test-session'},
         {'name': 'x-rednote-holderctry', 'value': 'CN'}],
        [('bottom-channel', TEST_HK_ID)])
    with pytest.raises(RuntimeError, match='COLLECTOR_IDENTITY_MISMATCH'):
        worker._assert_collection_identity(context)


def test_attached_context_requires_identity_contract(monkeypatch):
    import xhs_cdp_collector as worker

    monkeypatch.delenv('XHS_EXPECTED_COLLECTION_USER_ID', raising=False)
    with pytest.raises(RuntimeError, match='COLLECTOR_IDENTITY_NOT_CONFIGURED'):
        worker._assert_collection_identity(SimpleNamespace(cookies=lambda _urls: []))


def test_worker_requires_existing_context_without_creating_one():
    import xhs_cdp_collector as worker

    with pytest.raises(RuntimeError, match='COLLECTOR_IDENTITY_CONTEXT_UNAVAILABLE'):
        worker._existing_collection_context(SimpleNamespace(contexts=[]))


def test_adapter_health_resolves_identity_and_reports_reachable_as_need_verify():
    from lumenis.system.collector.adapters.base import CollectionStatus
    from lumenis.system.collector.adapters.xhs import XiaohongshuAdapter

    calls = []

    class Backend:
        def _collection_policy_gate(self, *, account=None, region=None):
            calls.append(('policy', account, region))
            return {'ok': True, 'account': 'XHS_RETINAUT', 'region': 'intl'}

        def _resolve_server_cdp_url(self, *, account=None, region=None):
            calls.append(('resolve', account, region))
            return f'http://127.0.0.1:{TEST_WORKER_PORT}', ''

        def _cdp_online(self, *, timeout, cdp_url, account=None, region=None):
            calls.append(('probe', cdp_url, account, region))
            return True

    result = XiaohongshuAdapter(backend=Backend()).health_check()

    assert result.status is CollectionStatus.NEED_VERIFY
    assert result.ok is False
    assert calls == [
        ('policy', None, 'intl'),
        ('resolve', 'XHS_RETINAUT', 'intl'),
        ('probe', f'http://127.0.0.1:{TEST_WORKER_PORT}', 'XHS_RETINAUT', 'intl'),
    ]


def test_adapter_health_blocks_wrong_account_before_endpoint_or_probe():
    from lumenis.system.collector.adapters.base import CollectionStatus
    from lumenis.system.collector.adapters.xhs import XiaohongshuAdapter

    class Backend:
        def _collection_policy_gate(self, *, account=None, region=None):
            return {'ok': False, 'code': 'account_paused'}

        def _resolve_server_cdp_url(self, **kwargs):
            raise AssertionError('blocked identity must not resolve endpoint')

        def _cdp_online(self, **kwargs):
            raise AssertionError('blocked identity must not contact CDP')

    result = XiaohongshuAdapter(backend=Backend()).health_check(
        account='XHS_CN_PRIMARY', region='cn')

    assert result.status is CollectionStatus.NOT_CONFIGURED
    assert result.metadata['error_type'] == 'account_paused'


def test_collection_env_none_region_keeps_intl_default(monkeypatch, tmp_path):
    import collector
    import xhs_cookie_bridge as bridge

    private = tmp_path / 'private'
    profile = private / 'profiles' / 'xhs-retinaut'
    profile.mkdir(parents=True)
    cookie = private / 'xhs_cookie_retinaut.txt'
    cookie.write_text(f'x-user-id-pro={TEST_HK_ID}', encoding='utf-8')
    monkeypatch.setattr(bridge, 'PRIVATE_DATA_DIR', str(private))
    monkeypatch.setattr(bridge, 'XHS_RETINAUT', TEST_HK_ID)
    monkeypatch.setattr(bridge, 'ACCOUNT_PROFILES', {
        bridge.XHS_RETINAUT_NAME: (str(cookie), str(profile)),
    })
    monkeypatch.setenv('XHS_EXPECTED_COLLECTION_USER_ID', 'untrusted-inherited-value')
    monkeypatch.setenv('XHS_PROFILE_DIR', str(tmp_path / 'personal-profile'))
    monkeypatch.setenv('XHS_CDP_URL', 'http://127.0.0.1:9999')
    monkeypatch.setenv('XHS_COOKIE_HEADER', 'inherited-not-approved')
    monkeypatch.setenv('XHS_COOKIES_JSON', 'inherited-not-approved')
    env = collector._collection_env(account=bridge.XHS_RETINAUT_NAME, region=None)

    assert env['XHS_COLLECTION_REGION'] == 'intl'
    assert env['XHS_COLLECTION_HOST'] == 'www.rednote.com'
    assert env['XHS_EXPECTED_COLLECTION_USER_ID'] == bridge.XHS_RETINAUT
    assert env['XHS_PROFILE_DIR'] == str(profile.resolve())
    assert env['XHS_COOKIE_FILE'] == str(cookie.resolve())
    assert 'XHS_CDP_URL' not in env
    assert 'XHS_COOKIE_HEADER' not in env
    assert 'XHS_COOKIES_JSON' not in env
    cookie.write_text('x-user-id-pro=wrong-synthetic-identity', encoding='utf-8')
    with pytest.raises(PermissionError, match='XHS_REGISTERED_COOKIE_IDENTITY_MISMATCH'):
        collector._collection_env(account=bridge.XHS_RETINAUT_NAME, region=None)
    _configure_remote_worker(monkeypatch, user_id=bridge.XHS_RETINAUT)
    with pytest.raises(PermissionError, match='COLLECTOR_REMOTE_WORKER_IDENTITY_UNVERIFIED'):
        collector._collection_env(
            account=bridge.XHS_RETINAUT_NAME, region='intl',
            cdp_url='https://worker.example:9443', require_local_cookie=False,
        )


def test_existing_context_helper_returns_only_preexisting_context():
    import xhs_cdp_collector as worker

    existing = object()
    assert worker._existing_collection_context(
        SimpleNamespace(contexts=[existing])) is existing


def test_login_device_limit_precedes_generic_verification_classification():
    import xhs_cdp_collector as worker

    page_text = '电脑设备登录超限，请重新登录 扫码登录 手机号登录 获取验证码'
    assert worker.classify_page(page_text) == ('session_expired', 'SESSION_EXPIRED')


def test_real_captcha_and_platform_risk_keep_distinct_classification():
    import xhs_cdp_collector as worker

    assert worker.classify_page('请完成验证，拖动下方滑块') == ('verify', '请完成验证')
    assert worker.classify_page('IP存在风险 300012') == ('ip', '300012')


def test_risk_check_preserves_session_expired_summary():
    import xhs_cdp_collector as worker

    page = SimpleNamespace(evaluate=lambda _script: '电脑设备登录超限，请重新登录')
    result = {'summary': {}, 'error': ''}

    assert worker._risk_check(page, result) is True
    assert result['error'] == 'SESSION_EXPIRED'
    assert result['summary']['session_expired'] is True


def test_cdp_search_blocks_remote_worker_identity_before_child_spawn(monkeypatch, tmp_path):
    import collector
    import xhs_cookie_bridge as bridge
    _configure_remote_worker(monkeypatch)

    child_calls = []
    monkeypatch.setattr(collector.subprocess, 'run', lambda *args, **kwargs:
                        child_calls.append((args, kwargs)))

    result = collector._search_via_cdp(
        'synthetic keyword', 1, str(tmp_path / 'output.json'),
        cdp_url='https://worker.example:9443', account=bridge.XHS_RETINAUT_NAME,
        region='intl')

    assert result['error'] == 'COLLECTOR_REMOTE_WORKER_IDENTITY_UNVERIFIED'
    assert result['channel'] == 'cdp'
    assert child_calls == []


def test_system_xhs_adapter_preserves_session_expired_status():
    from lumenis.system.collector.adapters.base import CollectionStatus
    from lumenis.system.collector.adapters.xhs import XiaohongshuAdapter

    class Backend:
        def search_xiaohongshu(self, *_args, **_kwargs):
            return {'notes': [], 'total': 0, 'error': 'SESSION_EXPIRED',
                    'summary': {'session_expired': True}, 'channel': 'authorized_browser_worker'}

    result = XiaohongshuAdapter(backend=Backend()).search('synthetic keyword')
    assert result.status is CollectionStatus.SESSION_EXPIRED
    assert result.metadata['error_type'] == 'SESSION_EXPIRED'


def test_denied_identity_stops_before_new_page_creation():
    import xhs_cdp_collector as worker

    created_pages = []
    context = _identity_context(
        [{'name': 'web_session', 'value': 'test-session'}],
        [('bottom-channel', 'b' * 24)])
    context.new_page = lambda: created_pages.append(object())

    class Browser:
        contexts = [context]

    class Chromium:
        def connect_over_cdp(self, *_args, **_kwargs):
            return Browser()

    class Playwright:
        chromium = Chromium()

    import os
    previous = os.environ.get('XHS_EXPECTED_COLLECTION_USER_ID')
    os.environ['XHS_EXPECTED_COLLECTION_USER_ID'] = TEST_HK_ID
    try:
        with pytest.raises(RuntimeError, match='COLLECTOR_IDENTITY_MISMATCH'):
            worker._connect_verified_collection_context(Playwright(), 'http://127.0.0.1:9223')
    finally:
        if previous is None:
            os.environ.pop('XHS_EXPECTED_COLLECTION_USER_ID', None)
        else:
            os.environ['XHS_EXPECTED_COLLECTION_USER_ID'] = previous

    assert created_pages == []


def test_registered_xhs_worker_counts_browser_main_not_same_profile_children(
        monkeypatch, tmp_path):
    import sys

    import cdp_helper

    profile = str(tmp_path / 'registered-profile')
    executable = str(tmp_path / 'msedge.exe')

    class FakeProcess:
        def __init__(self, pid, process_type=None):
            args = [
                executable,
                f'--user-data-dir={profile}',
                '--remote-debugging-port=9234',
                '--remote-debugging-address=127.0.0.1',
                '--headless=new',
            ]
            if process_type:
                args.append(f'--type={process_type}')
            self.pid = pid
            self.info = {'pid': pid, 'name': 'msedge.exe', 'cmdline': args}

        def exe(self):
            return executable

        def create_time(self):
            return float(self.pid)

    main = FakeProcess(101)
    renderer = FakeProcess(102, 'renderer')
    fake_psutil = SimpleNamespace(process_iter=lambda _attrs: [main, renderer])
    monkeypatch.setitem(sys.modules, 'psutil', fake_psutil)
    monkeypatch.setattr(cdp_helper, '_registered_edge_executable', lambda: executable)

    owners, incomplete = cdp_helper._registered_xhs_profile_processes(
        {'profile': profile})

    assert incomplete is False
    assert [owner['pid'] for owner in owners] == [101]


def test_dynamic_worker_port_requires_exact_listener_and_process_binding(
        monkeypatch, tmp_path):
    """DevToolsActivePort is only a candidate; the socket PID must match the worker."""
    import sys

    import cdp_helper

    profile = tmp_path / 'registered-profile'
    profile.mkdir()
    (profile / 'DevToolsActivePort').write_text(
        '9234\n/devtools/browser/synthetic-id\n', encoding='ascii')
    executable = str(tmp_path / 'msedge.exe')

    class FakeProcess:
        pid = 101
        info: ClassVar[dict] = {
            'pid': 101,
            'name': 'msedge.exe',
            'cmdline': [
                executable, f'--user-data-dir={profile}',
                '--remote-debugging-port=0',
                '--remote-debugging-address=127.0.0.1', '--headless=new',
            ],
        }

        def exe(self):
            return executable

        def create_time(self):
            return 101.0

        def cmdline(self):
            return self.info['cmdline']

    process = FakeProcess()
    monkeypatch.setitem(sys.modules, 'psutil', SimpleNamespace(
        process_iter=lambda _attrs: [process], Process=lambda _pid: process,
    ))
    monkeypatch.setattr(cdp_helper, '_registered_edge_executable', lambda: executable)
    monkeypatch.setattr(cdp_helper, '_registered_xhs_binding', lambda _account=None: {
        'account': 'XHS_RETINAUT', 'profile': str(profile), 'browser': 'edge',
    })
    monkeypatch.setattr(cdp_helper, '_cdp_listener_pids', lambda _port: ({999}, True))

    state = cdp_helper.resolve_registered_xhs_worker(account='XHS_RETINAUT', headless=True)

    assert state == {
        'available': False,
        'code': 'XHS_WORKER_LISTENER_UNVERIFIED',
        'account': 'XHS_RETINAUT',
        'pid': 101,
    }


def test_dynamic_worker_resolves_only_after_exact_process_and_listener_readback(
        monkeypatch, tmp_path):
    import sys

    import cdp_helper

    profile = tmp_path / 'registered-profile'
    profile.mkdir()
    (profile / 'DevToolsActivePort').write_text(
        '9234\n/devtools/browser/synthetic-id\n', encoding='ascii')
    executable = str(tmp_path / 'msedge.exe')

    class FakeProcess:
        pid = 101
        info: ClassVar[dict] = {
            'pid': 101,
            'name': 'msedge.exe',
            'cmdline': [
                executable, f'--user-data-dir={profile}',
                '--remote-debugging-port=0',
                '--remote-debugging-address=127.0.0.1', '--headless=new',
            ],
        }

        def exe(self):
            return executable

        def create_time(self):
            return 101.0

        def cmdline(self):
            return self.info['cmdline']

    process = FakeProcess()
    monkeypatch.setitem(sys.modules, 'psutil', SimpleNamespace(
        process_iter=lambda _attrs: [process], Process=lambda _pid: process,
    ))
    monkeypatch.setattr(cdp_helper, '_registered_edge_executable', lambda: executable)
    monkeypatch.setattr(cdp_helper, '_registered_xhs_binding', lambda _account=None: {
        'account': 'XHS_RETINAUT', 'profile': str(profile), 'browser': 'edge',
    })
    listener_reads = []

    def exact_listener(_port):
        listener_reads.append(_port)
        return {101}, True

    monkeypatch.setattr(cdp_helper, '_cdp_listener_pids', exact_listener)

    state = cdp_helper.resolve_registered_xhs_worker(account='XHS_RETINAUT', headless=True)

    assert state == {
        'available': True, 'account': 'XHS_RETINAUT', 'profile': str(profile),
        'browser': 'edge', 'port': 9234, 'endpoint': 'http://127.0.0.1:9234',
        'pid': 101, 'headless': True, 'loopback_only': True,
    }
    assert listener_reads == [9234, 9234]


def test_registered_xhs_multiple_main_processes_remain_ambiguous(monkeypatch, tmp_path):
    import sys

    import cdp_helper

    profile = str(tmp_path / 'registered-profile')
    executable = str(tmp_path / 'msedge.exe')

    class FakeProcess:
        def __init__(self, pid):
            self.pid = pid
            self.info = {
                'pid': pid, 'name': 'msedge.exe',
                'cmdline': [executable, f'--user-data-dir={profile}',
                            '--remote-debugging-port=9234',
                            '--remote-debugging-address=127.0.0.1', '--headless=new'],
            }

        def exe(self):
            return executable

        def create_time(self):
            return float(self.pid)

    fake_psutil = SimpleNamespace(process_iter=lambda _attrs: [
        FakeProcess(101), FakeProcess(103), FakeProcess(102),
    ])
    monkeypatch.setitem(sys.modules, 'psutil', fake_psutil)
    monkeypatch.setattr(cdp_helper, '_registered_edge_executable', lambda: executable)
    monkeypatch.setattr(cdp_helper, '_registered_xhs_binding', lambda _account=None: {
        'account': 'XHS_RETINAUT', 'profile': profile, 'browser': 'edge',
    })

    state = cdp_helper.resolve_registered_xhs_worker(account='XHS_RETINAUT', headless=True)

    assert state == {'available': False, 'code': 'XHS_WORKER_IDENTITY_AMBIGUOUS',
                     'account': 'XHS_RETINAUT'}


def _xhs_worker_state(port, *, headless):
    return {
        'available': True, 'account': 'XHS_RETINAUT',
        'profile': 'registered-profile', 'browser': 'edge', 'port': port,
        'endpoint': f'http://127.0.0.1:{port}', 'pid': port + 100,
        'headless': headless, 'loopback_only': True,
    }


def test_registered_xhs_mode_switch_uses_fresh_dynamic_port_each_time(
        monkeypatch):
    import cdp_helper
    from lumenis.adapters import human_browser
    import scripts.start_resident_browsers as resident

    active = {'state': _xhs_worker_state(9234, headless=True)}
    launches = []
    closes = []
    spec = {
        'platform': 'xiaohongshu', 'account': 'XHS_RETINAUT', 'port': 9234,
        'profile': 'registered-profile', 'browser': 'edge',
    }

    def resolve(*, account=None, headless=None, port=None):
        current = active['state']
        if current is None:
            return {'available': False, 'account': 'XHS_RETINAUT',
                    'code': 'XHS_REGISTERED_WORKER_UNAVAILABLE'}
        if account not in (None, 'XHS_RETINAUT'):
            return {'available': False, 'code': 'XHS_REGISTERED_IDENTITY_UNAVAILABLE'}
        if headless is not None and current['headless'] is not headless:
            return {'available': False, 'code': 'XHS_WORKER_MODE_MISMATCH'}
        if port is not None and int(port) != current['port']:
            return {'available': False, 'code': 'XHS_WORKER_ENDPOINT_MISMATCH'}
        return dict(current)

    def close(port, profile, *, headless, browser):
        closes.append((port, profile, headless, browser))
        assert active['state']['port'] == port
        assert active['state']['headless'] is headless
        active['state'] = None
        return {'success': True}

    def launch(worker, *, mode, browser, task_id, platform, actor_ref):
        assert worker['port'] == 0
        assert worker['profile'] == spec['profile']
        assert worker['account'] == platform == 'XHS_RETINAUT'
        assert task_id == 'task-xhs-human'
        assert actor_ref == 'actor-verified'
        headless = mode == 'BACKGROUND'
        port = 9236 if headless else 9235
        active['state'] = _xhs_worker_state(port, headless=headless)
        launches.append((mode, worker['port'], port, task_id, actor_ref))
        return {
            **worker, 'online': True, 'action': 'started', 'browser': browser,
            'port': port, 'endpoint': active['state']['endpoint'],
            'pid': active['state']['pid'], 'profile': active['state']['profile'],
            'account': active['state']['account'],
        }

    monkeypatch.setattr(cdp_helper, 'resolve_registered_xhs_worker', resolve)
    monkeypatch.setattr(cdp_helper, 'close_cdp_browser', close)
    monkeypatch.setattr(human_browser, '_authorize_human_interactive',
                        lambda identity, task_id, actor_ref: 'xiaohongshu')
    monkeypatch.setattr(human_browser, '_require_human_browser_lease',
                        lambda task_id, platform: None)
    monkeypatch.setattr(resident, '_launch_readonly_worker', launch)

    human = human_browser._switch_registered_worker_mode(
        spec, target_mode='HUMAN_INTERACTIVE', task_id='task-xhs-human',
        actor_ref='actor-verified')
    assert human['online'] is True
    assert (human['port'], human['endpoint'], human['pid']) == (
        9235, 'http://127.0.0.1:9235', 9335)

    background = human_browser._switch_registered_worker_mode(
        {**spec, 'port': human['port']}, target_mode='BACKGROUND',
        task_id='task-xhs-human', actor_ref='actor-verified')
    assert background['online'] is True
    assert (background['port'], background['endpoint'], background['pid']) == (
        9236, 'http://127.0.0.1:9236', 9336)
    assert launches == [
        ('HUMAN_INTERACTIVE', 0, 9235, 'task-xhs-human', 'actor-verified'),
        ('BACKGROUND', 0, 9236, 'task-xhs-human', 'actor-verified'),
    ]
    assert closes == [
        (9234, 'registered-profile', True, 'edge'),
        (9235, 'registered-profile', False, 'edge'),
    ]


def test_resident_xhs_launcher_returns_only_post_start_registered_endpoint(
        monkeypatch, tmp_path):
    import cdp_helper
    import scripts.start_resident_browsers as resident

    profile = tmp_path / 'registered-profile'
    worker = {
        'platform': 'xiaohongshu', 'account': 'XHS_RETINAUT', 'port': 0,
        'profile': str(profile), 'env_prefix': 'XHS', 'home': 'about:blank',
        'direct': False, 'browser': 'edge',
    }
    launched = []
    expected = {**_xhs_worker_state(9235, headless=True), 'profile': str(profile)}

    def start(**kwargs):
        launched.append(kwargs)
        return {'success': True, 'port': 9235, 'pid': 9335,
                'endpoint': 'http://127.0.0.1:9235'}

    monkeypatch.setattr(resident, 'port_online', lambda _port: False)
    monkeypatch.setattr(cdp_helper, 'start_cdp_browser', start)
    monkeypatch.setattr(cdp_helper, 'resolve_registered_xhs_worker',
                        lambda **_kwargs: dict(expected))
    monkeypatch.setattr(
        cdp_helper, 'is_cdp_profile_running',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError('dynamic start must use registered endpoint readback')),
    )

    result = resident._launch_readonly_worker(worker, mode='BACKGROUND', browser='edge')

    assert launched[0]['port'] == 0
    assert result['online'] is True
    assert (result['port'], result['endpoint'], result['pid'], result['profile']) == (
        9235, 'http://127.0.0.1:9235', 9335, str(profile))
    assert result['account'] == 'XHS_RETINAUT'


def _setup_human_login_transition(monkeypatch, *, fail_connect=False,
                                  fail_rollback=False, no_worker=False):
    import sys
    from contextlib import contextmanager

    import cdp_helper
    import lumenis.adapters.human_browser as human_browser
    from lumenis.adapters import collector_service

    active = {'state': None if no_worker else _xhs_worker_state(9234, headless=True)}
    spec = {
        'platform': 'xiaohongshu', 'account': 'XHS_RETINAUT', 'port': 9234,
        'profile': 'registered-profile', 'browser': 'edge',
    }
    resolved_specs = []
    endpoint_requests = []
    connected = []
    brought_forward = []
    updates = []
    transitions = []

    def registered_spec(identity, *, profile=None, **_kwargs):
        assert identity in {'xiaohongshu', 'XHS_RETINAUT'}
        if profile is not None:
            assert profile == spec['profile']
        result = {**spec, 'port': active['state']['port'] if active['state'] else 0}
        resolved_specs.append(result)
        return result

    def resolve(*, account=None, headless=None, port=None):
        current = active['state']
        if current is None:
            return {'available': False, 'account': 'XHS_RETINAUT',
                    'code': 'XHS_REGISTERED_WORKER_UNAVAILABLE'}
        if account not in (None, 'XHS_RETINAUT'):
            return {'available': False, 'code': 'XHS_REGISTERED_IDENTITY_UNAVAILABLE'}
        if headless is not None and current['headless'] is not headless:
            return {'available': False, 'code': 'XHS_WORKER_MODE_MISMATCH'}
        if port is not None and current['port'] != port:
            return {'available': False, 'code': 'XHS_WORKER_ENDPOINT_MISMATCH'}
        return dict(current)

    def switch(_spec, *, target_mode, task_id, actor_ref):
        transitions.append((target_mode, task_id, actor_ref))
        if target_mode == 'BACKGROUND' and fail_rollback:
            raise RuntimeError('SIMULATED_BACKGROUND_ROLLBACK_FAILURE')
        headless = target_mode == 'BACKGROUND'
        port = 9235 if not headless else 9236
        active['state'] = _xhs_worker_state(port, headless=headless)
        return {
            'online': True, 'browser': 'edge', 'action': 'started',
            'port': port, 'endpoint': active['state']['endpoint'],
            'pid': active['state']['pid'], 'profile': active['state']['profile'],
            'account': active['state']['account'],
        }

    class Page:
        url = 'https://www.rednote.com/'

        def bring_to_front(self):
            brought_forward.append(self.url)

    class Context:
        def __init__(self):
            self.pages = [Page()]

    class Browser:
        def __init__(self):
            self.contexts = [Context()]

    class Chromium:
        def connect_over_cdp(self, endpoint, *, timeout):
            connected.append((endpoint, timeout))
            if fail_connect:
                raise RuntimeError('SIMULATED_CDP_CONNECT_FAILURE')
            return Browser()

    class PlaywrightRuntime:
        chromium = Chromium()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setitem(sys.modules, 'playwright', SimpleNamespace(__path__=[]))
    monkeypatch.setitem(sys.modules, 'playwright.sync_api', SimpleNamespace(
        sync_playwright=PlaywrightRuntime))
    monkeypatch.setattr(human_browser, 'registered_browser_worker_spec', registered_spec)
    monkeypatch.setattr(human_browser, '_authorize_human_interactive',
                        lambda identity, task_id, actor_ref: 'xiaohongshu')
    monkeypatch.setattr(human_browser, '_require_human_browser_lease',
                        lambda task_id, platform: None)
    monkeypatch.setattr(human_browser, '_worker_endpoint',
                        lambda worker: endpoint_requests.append(worker['port'])
                        or f"http://127.0.0.1:{worker['port']}")
    monkeypatch.setattr(human_browser, '_switch_registered_worker_mode', switch)
    monkeypatch.setattr(human_browser, '_worker_mode_state',
                        lambda _spec, *, headless: (
                            'edge' if active['state']
                            and active['state']['headless'] is headless else None))
    monkeypatch.setattr(cdp_helper, 'resolve_registered_xhs_worker', resolve)
    monkeypatch.setattr(cdp_helper, 'is_cdp_port_open', lambda _port: False)
    monkeypatch.setattr(collector_service, 'begin_human_browser', lambda *_args: True)
    monkeypatch.setattr(collector_service, 'human_browser_lease_owned', lambda *_args: True)

    @contextmanager
    def platform_lock(_platform):
        yield True

    monkeypatch.setattr(collector_service, 'platform_activity_lock', platform_lock)
    monkeypatch.setattr(
        collector_service, 'update_human_browser_state',
        lambda task_id, platform, state, *, release_lease: (
            updates.append((task_id, platform, state, release_lease)) or True),
    )
    return {
        'human_browser': human_browser, 'connected': connected,
        'endpoint_requests': endpoint_requests, 'brought_forward': brought_forward,
        'updates': updates, 'transitions': transitions,
        'resolved_specs': resolved_specs, 'active': active,
    }


def test_open_readonly_worker_login_connects_to_newly_registered_endpoint(monkeypatch):
    state = _setup_human_login_transition(monkeypatch)

    result = state['human_browser'].open_readonly_worker_login(
        'xiaohongshu', task_id='task-xhs-human', actor_ref='actor-verified')

    assert result['status'] == 'HUMAN_LOGIN_REUSED'
    assert state['endpoint_requests'] == [9234, 9235]
    assert state['connected'] == [('http://127.0.0.1:9235', 10000)]
    assert state['brought_forward'] == ['https://www.rednote.com/']
    assert state['updates'] == [
        ('task-xhs-human', 'xiaohongshu', 'ACTIVE', False),
    ]


def test_open_readonly_worker_login_can_launch_authorized_worker_when_none_is_registered(
        monkeypatch):
    state = _setup_human_login_transition(monkeypatch, no_worker=True)

    result = state['human_browser'].open_readonly_worker_login(
        'xiaohongshu', task_id='task-xhs-human', actor_ref='actor-verified')

    assert result['status'] == 'HUMAN_LOGIN_REUSED'
    assert state['transitions'] == [
        ('HUMAN_INTERACTIVE', 'task-xhs-human', 'actor-verified'),
    ]
    assert state['endpoint_requests'] == [9235]
    assert state['connected'] == [('http://127.0.0.1:9235', 10000)]
    assert state['updates'] == [
        ('task-xhs-human', 'xiaohongshu', 'ACTIVE', False),
    ]


def test_human_login_failed_rollback_keeps_task_lease_blocked(monkeypatch):
    state = _setup_human_login_transition(
        monkeypatch, fail_connect=True, fail_rollback=True)

    with pytest.raises(RuntimeError, match='SIMULATED_CDP_CONNECT_FAILURE'):
        state['human_browser'].open_readonly_worker_login(
            'xiaohongshu', task_id='task-xhs-human', actor_ref='actor-verified')

    assert state['connected'] == [('http://127.0.0.1:9235', 10000)]
    assert state['transitions'] == [
        ('HUMAN_INTERACTIVE', 'task-xhs-human', 'actor-verified'),
        ('BACKGROUND', 'task-xhs-human', 'actor-verified'),
    ]
    assert state['updates'] == [
        ('task-xhs-human', 'xiaohongshu', 'BLOCKED', False),
    ]


def test_sync_search_requires_registered_worker_before_cookie_read_or_child_start(
        monkeypatch, tmp_path):
    import xhs_cookie_bridge as bridge

    private_dir = tmp_path / 'private'
    profile = private_dir / 'profiles' / 'xhs-retinaut'
    cookie_file = private_dir / 'xhs_cookie_retinaut.txt'
    monkeypatch.setattr(bridge, 'PRIVATE_DATA_DIR', str(private_dir))
    monkeypatch.setattr(bridge, 'ACCOUNT_PROFILES', {
        bridge.XHS_RETINAUT_NAME: (str(cookie_file), str(profile)),
    })
    monkeypatch.setattr(bridge, 'collection_policy_gate',
                        lambda **_kwargs: {'ok': True})
    monkeypatch.setattr(bridge, 'cdp_url_for', lambda **_kwargs: '')
    monkeypatch.setattr(
        bridge, '_extract_user_id_from_cookie_text',
        lambda _text: pytest.fail('cookie must not be read without a registered worker'),
    )
    monkeypatch.setattr(
        bridge.subprocess, 'Popen',
        lambda *_args, **_kwargs: pytest.fail('child process must not start without a worker'),
    )

    with pytest.raises(RuntimeError, match='XHS_REGISTERED_BROWSER_SESSION_UNAVAILABLE'):
        bridge._run_search('synthetic query')
