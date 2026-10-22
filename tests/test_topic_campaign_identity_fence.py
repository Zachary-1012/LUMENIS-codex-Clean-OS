# -*- coding: utf-8 -*-
"""Hermetic checks for the legacy topic campaign identity fence.

These tests exercise only policy/configuration and mocks. They never import the
Flask application, read a profile/Cookie/database, connect to CDP, or start a
collector process.
"""
import builtins
import inspect

import pytest

import topic_campaign as campaign


def _set_allowed_policy(monkeypatch):
    monkeypatch.setenv('REDNOTE_KIND_TOPIC', 'true')
    monkeypatch.setenv('REDNOTE_AUTO_RUN', 'true')


def test_default_and_invalid_worker_endpoints_fail_closed(monkeypatch):
    _set_allowed_policy(monkeypatch)
    monkeypatch.delenv('XHS_CDP_URL', raising=False)
    assert campaign._legacy_campaign_route_status()['code'] == 'CANONICAL_COLLECTOR_BINDING_REQUIRED'

    for endpoint in (
        'http://127.0.0.1:9222',
        'https://worker.example:9222',
        'http://127.0.0.1:9224',
        'http://127.0.0.2:9223',
        'http://collector-worker.example:9223',
        'https://collector-worker.example:9443',
        'http://localhost:9223',
        'https://127.0.0.1:9223',
        'http://127.0.0.1:9223/',
        'http://127.0.0.1:9223/path',
        'http://127.0.0.1:9223?query=1',
        'http://127.0.0.1:9223#fragment',
        'file:///tmp/browser',
        'https://user:secret@worker.example:9443',
        'https://worker.example:9443/path',
        ' https://worker.example:9443',
    ):
        monkeypatch.setenv('XHS_CDP_URL', endpoint)
        route = campaign._legacy_campaign_route_status()
        assert route['ok'] is False, endpoint
        assert route['code'] == 'CANONICAL_COLLECTOR_BINDING_REQUIRED', endpoint
        assert route['identity']['cdp_url'] is None


def test_policy_can_allow_hk_route_but_legacy_caller_stays_unavailable(monkeypatch):
    _set_allowed_policy(monkeypatch)
    monkeypatch.setenv('XHS_CDP_URL', 'http://127.0.0.1:9223')
    identity = campaign._canonical_campaign_identity()
    assert identity['ok'] is True
    assert identity['account'] == 'XHS_RETINAUT'
    assert identity['region'] == 'intl'
    assert identity['cdp_port'] is None
    assert identity['host'] == 'www.rednote.com'

    route = campaign._legacy_campaign_route_status()
    assert route['ok'] is False
    assert route['code'] == 'CANONICAL_COLLECTOR_BINDING_REQUIRED'
    result = campaign._run_collector('#test')
    assert result['ok'] is False
    assert result['status'] == 'CANONICAL_COLLECTOR_BINDING_REQUIRED'


def test_blocked_default_paths_do_not_probe_files_cdp_database_or_processes(monkeypatch):
    monkeypatch.delenv('XHS_CDP_URL', raising=False)
    monkeypatch.setenv('XHS_PROFILE_DIR', 'must-not-be-read')
    monkeypatch.delenv('ZBC_TEST_OFFLINE', raising=False)
    monkeypatch.delenv('ZBC_ENV', raising=False)
    monkeypatch.delenv('XHS_PRODUCTION', raising=False)

    def forbidden(*args, **kwargs):
        raise AssertionError(f'forbidden side effect attempted: args={args!r}')

    monkeypatch.setattr(campaign, '_node_bin', forbidden)
    monkeypatch.setattr(campaign.os.path, 'exists', forbidden)
    monkeypatch.setattr(campaign.os.path, 'isdir', forbidden)
    monkeypatch.setattr(campaign.subprocess, 'run', forbidden)
    monkeypatch.setattr(campaign, '_db', forbidden)
    monkeypatch.setattr(campaign, '_campaign_in_window', forbidden)
    monkeypatch.setattr(campaign, '_campaign_circuit_state', forbidden)
    monkeypatch.setattr(campaign, '_check_campaign_rate_limit', forbidden)
    monkeypatch.setattr(campaign, 'state_from_circuit', forbidden)
    monkeypatch.setattr(campaign.threading, 'Thread', forbidden)
    monkeypatch.setattr(campaign, 'XHSAppTopicAdapter', forbidden)

    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == 'cdp_helper' or name == 'collector' or name.startswith('playwright'):
            raise AssertionError(f'forbidden import attempted: {name}')
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', guarded_import)

    assert campaign._run_collector('#test')['status'] == 'CANONICAL_COLLECTOR_BINDING_REQUIRED'
    assert campaign._probe_xhs_health_via_cdp()[0] is False
    assert campaign._probe_runtime_state()['overall'] == 'unavailable'
    assert campaign._half_open_probe()[0] is False
    assert campaign.run_campaign()['unavailable'] is True
    assert campaign.start_scheduler() is False
    assert campaign._app_topic_collect('#test')['enabled'] is False


def test_auto_route_requires_explicit_automatic_policy(monkeypatch):
    monkeypatch.setenv('REDNOTE_KIND_TOPIC', 'true')
    monkeypatch.setenv('REDNOTE_AUTO_RUN', 'false')
    monkeypatch.setenv('XHS_CDP_URL', 'http://127.0.0.1:9223')
    route = campaign._canonical_campaign_identity(auto_trigger=True)
    assert route['ok'] is False
    assert route['code'] == 'AUTO_RUN_DISABLED'


def test_backfill_route_has_no_legacy_child_process_binding():
    source = inspect.getsource(campaign.register_topic_campaign)
    assert '/api/topic-campaign/backfill-detail' in source
    assert 'topic_note_detail_backfill.py' not in source
    assert 'subprocess.run' not in source


def test_missing_note_text_does_not_become_neutral_or_low_risk():
    content_type, sentiment, risk, quality = campaign._classify_note({}, False)

    assert content_type == 'UGC'
    assert sentiment == 'unknown'
    assert risk == 'unknown'
    assert quality == 'search_only'


def test_sentiment_analyzer_failure_stays_unknown(monkeypatch):
    original_import = builtins.__import__

    def unavailable(name, *args, **kwargs):
        if name == 'canonical_data':
            raise ImportError('isolated failure')
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', unavailable)
    assert campaign._classify_note({'title': '有标题但分析器不可用'}, False) == (
        'UGC', 'unknown', 'unknown', 'search_only')


class _RouteCursor:
    def __init__(self, row=None):
        self._row = row

    def fetchone(self):
        return self._row


class _RouteConnection:
    def execute(self, sql, params=()):
        if 'COUNT(*) c FROM topic_campaign_notes' in sql:
            return _RouteCursor({'c': 0})
        return _RouteCursor(None)


class _RouteDatabase:
    def get_db(self):
        from contextlib import nullcontext
        return nullcontext(_RouteConnection())


def _register_hermetic_app(monkeypatch):
    from flask import Flask
    monkeypatch.setattr(campaign, 'init_campaign', lambda: None)
    monkeypatch.setattr(campaign, 'start_scheduler', lambda: False)
    app = Flask('topic-campaign-hermetic-test')
    campaign.register_topic_campaign(app)
    return app.test_client()


def test_status_route_reports_blocked_runtime_instead_of_circuit_health(monkeypatch):
    _set_allowed_policy(monkeypatch)
    monkeypatch.delenv('XHS_CDP_URL', raising=False)
    monkeypatch.setattr(campaign, '_db', lambda: _RouteDatabase())
    monkeypatch.setattr(campaign, '_latest', lambda conn, campaign_key: None)
    monkeypatch.setattr(campaign, '_campaign_active', lambda: False)
    monkeypatch.setattr(campaign, '_campaign_circuit_state', lambda: None)
    monkeypatch.setattr(campaign, 'get_campaign_rate_status', lambda: {})

    def forbidden(*args, **kwargs):
        raise AssertionError('status must not report circuit-derived runtime health')

    monkeypatch.setattr(campaign, 'state_from_circuit', forbidden)
    client = _register_hermetic_app(monkeypatch)
    response = client.get('/api/topic-campaign/status')
    assert response.status_code == 200
    runtime = response.get_json()['runtime_state']
    assert runtime['overall'] == 'unavailable'
    assert runtime['healthy'] is False
    assert runtime['detail']['code'] == 'CANONICAL_COLLECTOR_BINDING_REQUIRED'


def test_half_open_route_serializes_blocked_runtime_dict(monkeypatch):
    _set_allowed_policy(monkeypatch)
    monkeypatch.delenv('XHS_CDP_URL', raising=False)
    client = _register_hermetic_app(monkeypatch)
    response = client.post('/api/topic-campaign/half-open-probe')
    assert response.status_code == 200
    payload = response.get_json()
    assert payload['half_open_success'] is False
    assert payload['overall'] == 'unavailable'
    assert payload['healthy'] is False
    assert payload['detail']['code'] == 'CANONICAL_COLLECTOR_BINDING_REQUIRED'


def test_registration_with_missing_endpoint_does_not_probe_legacy_identity(monkeypatch):
    from flask import Flask
    _set_allowed_policy(monkeypatch)
    monkeypatch.delenv('XHS_CDP_URL', raising=False)
    monkeypatch.setenv('ZBC_TEST_OFFLINE', '0')
    monkeypatch.setenv('ZBC_ENV', 'production')
    monkeypatch.setenv('XHS_PRODUCTION', 'true')
    monkeypatch.setattr(campaign, 'init_campaign', lambda: None)
    monkeypatch.setattr(campaign, '_scheduler_running', False)

    def forbidden(*args, **kwargs):
        raise AssertionError('default registration must not probe profile/CDP or start work')

    monkeypatch.setattr(campaign.threading, 'Thread', forbidden)
    monkeypatch.setattr(campaign, '_probe_xhs_health_via_cdp', forbidden)
    monkeypatch.setattr(campaign, 'XHSAppTopicAdapter', forbidden)
    app = Flask('topic-campaign-registration-test')
    campaign.register_topic_campaign(app)
    assert campaign._scheduler_running is False


@pytest.mark.parametrize('mismatch', [
    {'account': 'XHS_CN_PRIMARY'}, {'region': 'cn'}, {'host': 'www.xiaohongshu.com'}, {'ok': False},
])
def test_retired_campaign_still_rejects_noncanonical_identity(monkeypatch, mismatch):
    from lumenis.system.collector.adapters import rednote_policy
    _set_allowed_policy(monkeypatch)
    allowed = rednote_policy.collection_gate(account='XHS_RETINAUT', region='intl')
    monkeypatch.setattr(rednote_policy, 'collection_gate', lambda **kw: {**allowed, **mismatch})
    assert campaign._canonical_campaign_identity()['code'] == 'IDENTITY_BLOCKED'
    assert campaign._legacy_campaign_route_status()['ok'] is False
