"""Special-report compatibility calls must retain source and claim boundaries."""
import pytest


def _notes():
    return [{"note_id": "approved-note", "title": "服务反馈", "content": "服务反馈正文",
             "sentiment": "negative", "risk_level": "high", "negative_confirmed": 0,
             "likes": None, "comments": 4, "publish_date": None,
             "source_platform": None}]


@pytest.fixture
def scoped_reader(monkeypatch):
    import data_query_api
    import app as app_module
    calls = []

    def reader(**kwargs):
        calls.append(kwargs)
        return {"scope": {"domain_id": "cth", "subject_id": "SUBJECT-A"},
                "notes": _notes(), "total": 1, "truncated": False, "data_state": "READY"}

    def forbidden(*args, **kwargs):
        raise AssertionError("special report bypassed scoped Canonical source reader")

    monkeypatch.setattr(data_query_api, "read_scoped_legacy_note_rows", reader)
    monkeypatch.setattr(app_module.db, "get_high_risk_notes", forbidden)
    monkeypatch.setattr(app_module.db, "get_note_by_id", forbidden, raising=False)
    monkeypatch.setattr(app_module, "_load_cases", lambda: [])
    return calls


def test_special_report_retains_scope_and_unknown_source_fields(client, auth_headers, scoped_reader):
    response = client.post('/api/special-report/generate', headers=auth_headers,
                           json={"note_id": "approved-note"})
    assert response.status_code == 200, response.get_json()
    report = response.get_json()["report"]
    assert scoped_reader == [{"module": "reports", "filters": {"note_id": "approved-note"},
                              "limit": 100, "require_complete": True}]
    assert report["scope"]["subject_id"] == "SUBJECT-A"
    assert report["first_platform"] is None and report["first_date"] is None
    assert report["max_engagement"] is None
    assert report["related_notes"][0]["engagement"] is None
    assert report["analysis_kind"] == "RULE_BASED_PROPOSAL"
    assert report["business_outcome"] == "UNKNOWN"
    assert report["owned_model_execution"] == "NOT_RUN"
    assert report["spread_path_status"] == "HYPOTHESIS_NOT_OBSERVED"


def test_trigger_does_not_replace_unknown_measurements_with_zero(client, auth_headers, scoped_reader):
    response = client.get('/api/special-report/check-trigger', headers=auth_headers)
    assert response.status_code == 200, response.get_json()
    result = response.get_json()
    assert result["max_engagement"] is None and result["triggered"] is None
    assert result["negative_count"] == 1


@pytest.mark.parametrize('path,method', [
    ('/api/special-report/check-trigger', 'get'),
    ('/api/special-report/generate', 'post'),
])
def test_special_report_scope_denial_cannot_fall_back(client, auth_headers, monkeypatch, path, method):
    import data_query_api
    from api_dual_domain import CTHScopedReadError

    def denied(**kwargs):
        raise CTHScopedReadError('CTH_SCOPE_READ_DENIED', 403)

    monkeypatch.setattr(data_query_api, 'read_scoped_legacy_note_rows', denied)
    response = getattr(client, method)(path, headers=auth_headers)
    assert response.status_code == 403
    assert response.get_json()['code'] == 'CTH_SCOPE_READ_DENIED'


@pytest.mark.parametrize('likes,comments,expected', [
    (0, 0, 0), (10, 4, 22), (None, 4, None), ('unknown', 1, None), (True, 1, None),
])
def test_special_engagement_preserves_measurement_semantics(likes, comments, expected):
    import app as app_module
    assert app_module._special_report_engagement({'likes': likes, 'comments': comments}) == expected
