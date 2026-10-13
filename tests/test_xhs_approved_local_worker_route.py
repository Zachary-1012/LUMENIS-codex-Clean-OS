"""Offline contract tests for the explicitly approved HK local worker route."""
from types import SimpleNamespace

import pytest

TEST_HK_ID = 'a' * 24


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
    'http://127.0.0.1:9223',
    'http://127.0.0.1:9223/',
])
def test_approved_identity_can_resolve_exact_local_worker(monkeypatch, candidate):
    import collector

    monkeypatch.setattr(collector, '_approved_local_profile_contract',
                        lambda account, region: TEST_HK_ID)
    endpoint, error = collector._resolve_server_cdp_url(
        candidate, account='XHS_RETINAUT', region='intl')

    assert endpoint == 'http://127.0.0.1:9223'
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
    calls = []
    monkeypatch.setattr('urllib.request.urlopen',
                        lambda url, timeout: (calls.append((url, timeout)) or _Response()))

    endpoint, error = collector._resolve_server_cdp_url(
        account='XHS_RETINAUT', region='intl')

    assert endpoint == 'http://127.0.0.1:9223'
    assert error == ''
    assert calls == [('http://127.0.0.1:9223/json/version', 1.5)]


def test_approved_offline_local_worker_keeps_fail_closed(monkeypatch):
    import collector

    monkeypatch.delenv('XHS_CDP_URL', raising=False)
    monkeypatch.setattr(collector, 'CDP_URL', '')
    monkeypatch.setattr(collector, '_approved_local_profile_contract',
                        lambda account, region: TEST_HK_ID)
    monkeypatch.setattr('urllib.request.urlopen',
                        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError('offline')))

    endpoint, error = collector._resolve_server_cdp_url(
        account='XHS_RETINAUT', region='intl')

    assert endpoint == ''
    assert error == 'COLLECTOR_ENDPOINT_NOT_CONFIGURED'


@pytest.mark.parametrize(('candidate', 'account', 'region', 'profile_id', 'expected_error'), [
    ('', 'XHS_RETINAUT', 'intl', TEST_HK_ID, 'COLLECTOR_ENDPOINT_NOT_CONFIGURED'),
    ('http://127.0.0.1:9222', 'XHS_RETINAUT', 'intl', TEST_HK_ID, 'POLICY_BLOCKED'),
    ('http://localhost:9223', 'XHS_RETINAUT', 'intl', TEST_HK_ID, 'LOCAL_COLLECTOR_ENDPOINT_FORBIDDEN'),
    ('http://127.0.0.1:9223', 'XHS_CN_PRIMARY', 'cn', None, 'LOCAL_COLLECTOR_ENDPOINT_FORBIDDEN'),
    ('http://127.0.0.1:9223', 'XHS_RETINAUT', 'cn', None, 'LOCAL_COLLECTOR_ENDPOINT_FORBIDDEN'),
    ('http://127.0.0.1:9223/unknown', 'XHS_RETINAUT', 'intl', TEST_HK_ID, 'LOCAL_COLLECTOR_ENDPOINT_FORBIDDEN'),
])
def test_unapproved_local_routes_fail_closed(monkeypatch, candidate, account, region,
                                              profile_id, expected_error):
    import collector

    monkeypatch.setattr(collector, '_approved_local_profile_contract',
                        lambda requested_account, requested_region: profile_id)
    if not candidate:
        # The discovery path is covered above; keep this policy case
        # deterministic and independent of a developer browser being open.
        monkeypatch.setattr(
            'urllib.request.urlopen',
            lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError('offline')),
        )
    endpoint, error = collector._resolve_server_cdp_url(
        candidate, account=account, region=region)

    assert endpoint == ''
    assert error == expected_error


def test_remote_worker_route_remains_available(monkeypatch):
    import collector

    endpoint, error = collector._resolve_server_cdp_url(
        'https://worker.example:9443', account='XHS_RETINAUT', region='intl')

    assert endpoint == 'https://worker.example:9443'
    assert error == ''


def test_local_route_profile_contract_matches_registered_hk_profile(monkeypatch, tmp_path):
    import collector
    import xhs_cookie_bridge as bridge

    registered = str(tmp_path / 'profiles' / 'xhs-retinaut')
    monkeypatch.setattr(bridge, 'PRIVATE_DATA_DIR', str(tmp_path))
    monkeypatch.setitem(bridge.ACCOUNT_PROFILES, bridge.XHS_RETINAUT_NAME,
                        ('private-cookie-path-not-read', registered))
    monkeypatch.setitem(bridge.ACCOUNT_CDP_PORTS, bridge.XHS_RETINAUT_NAME, 9223)
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
            return 'http://127.0.0.1:9223', ''

        def _cdp_online(self, *, timeout, cdp_url, account=None, region=None):
            calls.append(('probe', cdp_url, account, region))
            return True

    result = XiaohongshuAdapter(backend=Backend()).health_check()

    assert result.status is CollectionStatus.NEED_VERIFY
    assert result.ok is False
    assert calls == [
        ('policy', None, 'intl'),
        ('resolve', 'XHS_RETINAUT', 'intl'),
        ('probe', 'http://127.0.0.1:9223', 'XHS_RETINAUT', 'intl'),
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
    remote_env = collector._collection_env(
        account=bridge.XHS_RETINAUT_NAME, region='intl',
        cdp_url='https://worker.example:9443', require_local_cookie=False,
    )
    assert remote_env['XHS_EXPECTED_COLLECTION_USER_ID'] == TEST_HK_ID
    assert remote_env['XHS_CDP_URL'] == 'https://worker.example:9443'
    assert 'XHS_COOKIE_FILE' not in remote_env
    assert 'XHS_PROFILE_DIR' not in remote_env


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


def test_cdp_search_propagates_session_expired_summary(monkeypatch, tmp_path):
    import json
    import collector
    import xhs_cookie_bridge as bridge

    payload = {'ok': False, 'notes': [],
               'summary': {'session_expired': True, 'matched': 'SESSION_EXPIRED'}}
    monkeypatch.setattr(collector.subprocess, 'run', lambda *args, **kwargs:
                        SimpleNamespace(stdout='---RESULT_JSON---' + json.dumps(payload), stderr='', returncode=0))

    result = collector._search_via_cdp(
        'synthetic keyword', 1, str(tmp_path / 'output.json'),
        cdp_url='https://worker.example:9443', account=bridge.XHS_RETINAUT_NAME,
        region='intl')

    assert result['error'] == 'SESSION_EXPIRED'
    assert result['summary']['session_expired'] is True


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
