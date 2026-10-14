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


def test_report_verify_limits_source_scan_to_requested_period(
        client, auth_headers, monkeypatch):
    from datetime import date, timedelta

    import database

    _allow_scoped_preview(
        monkeypatch, domain='CTH', subject_id='SUBJ-REPORT-CTH',
        subject_type='company',
    )
    anchor = date(2026, 10, 14)
    start = anchor - timedelta(days=anchor.weekday())
    end = start + timedelta(days=6)
    calls = []

    def read_sources(scope, *, source_types, limit, date_start=None, date_end=None):
        calls.append((date_start, date_end, source_types, limit))
        if date_start != start.isoformat() or date_end != end.isoformat():
            # An unbounded historical scan exceeds its limit and must not be used
            # to reject a small, fully covered requested period.
            return {"sources": [], "truncated": True, "rejected_count": 0}
        return {
            "sources": [{
                "source_id": "period-note-1", "publish_date": "2026-10-12",
                "captured_at": "2026-10-13", "sentiment": "negative",
                "negative_confirmed": 1, "risk_level": "high",
            }],
            "truncated": False, "rejected_count": 0,
        }

    monkeypatch.setattr(database, "get_scoped_event_source_rows", read_sources)
    response = client.get(
        "/api/report/verify?type=weekly&date=2026-10-14",
        headers={**auth_headers, **CTH_FOCUS},
    )

    assert response.status_code == 200, response.get_json()
    assert response.get_json()["period_start"] == start.isoformat()
    assert response.get_json()["period_end"] == end.isoformat()
    assert response.get_json()["published_in_period"] == 1
    assert calls == [(start.isoformat(), end.isoformat(), ("note",), 5000)]


def test_preview_requires_auth(client):
    r = client.get('/api/v2/report-center/preview?period=daily', headers=CTH_FOCUS)
    assert r.status_code == 401


def test_reporting_generate_uses_authenticated_scope_and_source_checked_builder(monkeypatch):
    from flask import Flask

    from lumenis.shared.reporting import export_api, routes
    from lumenis.shared.reporting.api import reporting_bp

    actor = {"id": 17, "role": "owner"}
    scope = {"domain_id": "cth", "product_id": "CTH", "subject_id": "SUBJ-REPORT-CTH",
             "brand_focus_id": None, "global_scope": False}
    selected = {"subject_id": "SUBJ-REPORT-CTH", "name_zh": "隔离测试主体"}
    monkeypatch.setenv("LUMENIS_REPORTING", "1")
    monkeypatch.setattr(routes, "_authorized_report_scope",
                        lambda **_kwargs: (actor, scope, [], selected))
    calls = []

    def build_report(kind, start, end, **kwargs):
        calls.append((kind, start, end, kwargs))
        return kind, "2026-10-01", "2026-10-02", {"report_id": "R-1"}, 0, [], []

    monkeypatch.setattr(export_api, "_build_report", build_report)
    app = Flask(__name__)
    app.register_blueprint(reporting_bp)
    response = app.test_client().post("/api/reporting/generate", json={
        "brand_mode": "cth", "period": "daily", "start_date": "2026-10-01",
        "end_date": "2026-10-02",
    })

    assert response.status_code == 200, response.get_json()
    assert response.get_json()["report"]["report_id"] == "R-1"
    assert calls == [("daily", "2026-10-01", "2026-10-02", {
        "actor": actor, "scope": scope, "scope_entry": selected,
    })]


def test_reporting_export_passes_authenticated_scope_to_exporter(monkeypatch):
    from flask import Flask

    from lumenis.shared import reporting
    from lumenis.shared.reporting import routes
    from lumenis.shared.reporting.api import reporting_bp

    actor = {"id": 17, "role": "owner"}
    scope = {"domain_id": "cth", "product_id": "CTH", "subject_id": "SUBJ-REPORT-CTH",
             "brand_focus_id": None, "global_scope": False}
    selected = {"subject_id": "SUBJ-REPORT-CTH", "name_zh": "隔离测试主体"}
    monkeypatch.setenv("LUMENIS_REPORTING", "1")
    monkeypatch.setattr(routes, "_authorized_report_scope",
                        lambda **_kwargs: (actor, scope, [], selected))
    calls = []

    class Exporter:
        def generate_and_export(self, **kwargs):
            calls.append(kwargs)
            return {"word_path": "word.docx", "pdf_path": "report.pdf"}

    monkeypatch.setattr(reporting, "ReportExporter", Exporter)
    app = Flask(__name__)
    app.register_blueprint(reporting_bp)
    response = app.test_client().post("/api/reporting/export", json={
        "brand_mode": "cth", "period": "weekly",
        "start_date": "2026-10-01", "end_date": "2026-10-07",
    })

    assert response.status_code == 200, response.get_json()
    assert calls == [{"brand_mode": "cth", "period": "weekly",
                      "start_date": "2026-10-01", "end_date": "2026-10-07", "actor": actor,
                      "scope": scope, "scope_entry": selected}]


@pytest.mark.parametrize("path", ["/api/reporting/generate", "/api/reporting/export"])
def test_reporting_rejects_unsupported_custom_period_before_build(monkeypatch, path):
    from flask import Flask

    from lumenis.shared.reporting.api import reporting_bp

    monkeypatch.setenv("LUMENIS_REPORTING", "1")
    app = Flask(__name__)
    app.register_blueprint(reporting_bp)

    response = app.test_client().post(path, json={"period": "custom"})

    assert response.status_code == 400
