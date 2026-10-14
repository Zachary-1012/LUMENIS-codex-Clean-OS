# -*- coding: utf-8 -*-
"""Shared Reporting 标准化预览路由测试（Shared Owner contract）。"""
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CTH_FOCUS = {
    'X-Domain-Id': 'CTH',
    'X-Product-Id': 'CTH',
    'X-Lumenis-Context-Mode': 'FOCUS',
    'X-Subject-ID': 'SUBJ-REPORT-CTH',
}
BMP_FOCUS = {
    'X-Domain-Id': 'BMP',
    'X-Product-Id': 'BMP',
    'X-Lumenis-Context-Mode': 'FOCUS',
    'X-Subject-ID': 'SUBJ-REPORT-BMP',
}


def _allow_scoped_preview(monkeypatch, *, domain, subject_id, subject_type, brand_focus_id=None):
    import database
    import subject_registry
    from lumenis.auth import service as auth_service
    from lumenis.system.security import permission

    actor = {'id': 17, 'role': 'owner'}
    entry = {
        'subject_id': subject_id,
        'brand_focus_id': brand_focus_id,
        'domain_id': domain,
        'subject_type': subject_type,
        'name_zh': '隔离测试主体',
        'name_en': 'Isolated report subject',
        'status': 'active',
        'keywords': [],
    }
    monkeypatch.setattr(
        subject_registry, 'get_subject_by_id', lambda _domain, _subject_id: entry
    )
    monkeypatch.setattr(subject_registry, 'list_subjects', lambda _domain=None: [entry])
    monkeypatch.setattr(auth_service, 'get_current_user', lambda *, read_only=False: actor)
    monkeypatch.setattr(permission, 'resolve_local_workspace_principal', lambda **_kwargs: None)
    permission_calls = []

    def allow_permission(received_actor, **kwargs):
        permission_calls.append((received_actor, kwargs))
        return SimpleNamespace(
            allowed=True, verification_state='verified', scope_audit_id='isolated-audit'
        )

    monkeypatch.setattr(permission, 'check_actor_scope_permission', allow_permission)
    monkeypatch.setattr(
        database,
        'get_scoped_event_source_rows',
        lambda *_args, **_kwargs: {'sources': [], 'truncated': False, 'rejected_count': 0},
    )
    monkeypatch.setattr(
        database,
        'get_scoped_events',
        lambda *_args, **_kwargs: {'events': [], 'truncated': False, 'rejected_count': 0},
    )
    return actor, permission_calls


def test_preview_returns_standard_sections_through_permission_owner(client, auth_headers, monkeypatch):
    actor, permission_calls = _allow_scoped_preview(
        monkeypatch, domain='CTH', subject_id='SUBJ-REPORT-CTH', subject_type='company'
    )
    r = client.get('/api/v2/report-center/preview?period=daily&brand_mode=cth',
                   headers={**auth_headers, **CTH_FOCUS})
    assert r.status_code == 200, r.get_json()
    j = r.get_json()
    assert j['ok'] is True and isinstance(j['report'], dict)
    assert len(j['report']) == 19
    assert j['report']['period'] == 'daily'
    assert '不替代既有报告 Owner' in j['note']
    assert len(permission_calls) == 1
    assert permission_calls[0][0] == actor
    assert permission_calls[0][1] == {
        'module': 'reports', 'action': 'read', 'domain_id': 'cth',
        'subject_id': 'SUBJ-REPORT-CTH', 'brand_focus_id': None,
        'global_scope': False,
    }


def test_preview_zbmp_mode_uses_registered_focus(client, auth_headers, monkeypatch):
    _allow_scoped_preview(
        monkeypatch, domain='BMP', subject_id='SUBJ-REPORT-BMP',
        subject_type='brand', brand_focus_id='BRAND-REPORT-BMP',
    )
    r = client.get('/api/v2/report-center/preview?period=weekly&brand_mode=zbmp',
                   headers={**auth_headers, **BMP_FOCUS})
    assert r.status_code == 200, r.get_json()
    rep = r.get_json()['report']
    assert rep['brand_mode'] == 'zbmp' and rep['period'] == 'weekly'


@pytest.mark.parametrize('qs', [
    'period=xxx',
    'brand_mode=xx',
    'start_date=2026-9-1',
    'end_date=bad',
])
def test_preview_rejects_invalid_params(client, auth_headers, qs):
    r = client.get('/api/v2/report-center/preview?' + qs, headers=auth_headers)
    assert r.status_code == 400 and r.get_json()['ok'] is False


def test_preview_requires_auth(client):
    r = client.get('/api/v2/report-center/preview?period=daily', headers=CTH_FOCUS)
    assert r.status_code == 401
