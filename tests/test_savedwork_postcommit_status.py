"""Original-owner post-commit status, real isolated registry and permission checks."""
import json
import pytest
from tests.test_saved_document_workflow import workspace, _save


def _count(ws):
    with ws["repo"].connection(read_only=True, wal=False) as con:
        return con.execute("SELECT count(*) FROM lumenis_shared_artifacts").fetchone()[0]


def _http(call):
    from experience_runtime import _shared_work_response
    result = _shared_work_response(call)
    return result if isinstance(result, tuple) else (result, result.status_code)


def _revoke_during_committed_read(ws, monkeypatch):
    work = ws["work"]
    original_reopen, original_read = work.reopen_work, work._read
    reading = {"active": False}
    def read(*args, **kwargs):
        result = original_read(*args, **kwargs)
        if reading["active"]:
            ws["app"].config["LUMENIS_OPEN_WORKSPACE"] = False
        return result
    def reopen(*args, **kwargs):
        reading["active"] = True
        try:
            return original_reopen(*args, **kwargs)
        finally:
            reading["active"] = False
    monkeypatch.setattr(work, "_read", read)
    monkeypatch.setattr(work, "reopen_work", reopen)
    return original_reopen, original_read


def test_revoke_midread_preserves_commit_and_returns_only_unconfirmed_state(workspace, monkeypatch):
    work = workspace["work"]
    before = _count(workspace)
    original_reopen, original_read = _revoke_during_committed_read(workspace, monkeypatch)
    response, status = _http(lambda: _save(workspace, request_id="postcommit-same-request",
        markdown="PRIVATE MANUSCRIPT NOT FOR REVOKED READER"))
    body = response.get_json()
    assert status == 403
    assert body == {"ok": False, "code": "WORK_PERMISSION_DENIED",
        "publish_status": "not_performed", "persistence_state": "COMMITTED_READBACK_UNCONFIRMED"}
    assert response.headers["Cache-Control"] == "no-store"
    assert _count(workspace) == before + 1
    assert "PRIVATE" not in response.get_data(as_text=True)
    assert "ART-" not in response.get_data(as_text=True)
    assert "WORK-" not in response.get_data(as_text=True)
    monkeypatch.setattr(work, "reopen_work", original_reopen)
    monkeypatch.setattr(work, "_read", original_read)
    # A rejected retry still has to pass current access; previous commit is not a grant.
    denied, denied_status = _http(lambda: _save(workspace, request_id="postcommit-same-request",
        markdown="PRIVATE MANUSCRIPT NOT FOR REVOKED READER"))
    assert denied_status == 403
    assert "persistence_state" not in denied.get_json()
    assert _count(workspace) == before + 1
    workspace["app"].config["LUMENIS_OPEN_WORKSPACE"] = True
    restored = _save(workspace, request_id="postcommit-same-request",
        markdown="PRIVATE MANUSCRIPT NOT FOR REVOKED READER")
    assert restored["replayed"] is True
    assert restored["document"]["version"] == 1
    assert _count(workspace) == before + 1


def test_plain_precommit_denial_remains_plain_failure(workspace):
    workspace["app"].config["LUMENIS_OPEN_WORKSPACE"] = False
    before = _count(workspace)
    response, status = _http(lambda: _save(workspace))
    assert status == 403
    assert response.get_json() == {"ok": False, "code": "WORK_PERMISSION_DENIED",
        "publish_status": "not_performed"}
    assert _count(workspace) == before


@pytest.mark.parametrize("failure,status,code", [
    (RuntimeError("READBACK_UNAVAILABLE"), 503, "READBACK_UNAVAILABLE"),
    (LookupError("WORK_NOT_FOUND"), 404, "WORK_NOT_FOUND"),
    (ValueError("WORK_INTEGRITY_FAILED"), 409, "WORK_INTEGRITY_FAILED"),
    (RuntimeError("private arbitrary text"), 503, "SHARED_WORK_UNAVAILABLE"),
])
def test_postcommit_error_classification_and_same_request_replay(workspace, monkeypatch, failure, status, code):
    work = workspace["work"]
    before = _count(workspace)
    original = work.reopen_work
    def fail(*args, **kwargs):
        raise failure
    monkeypatch.setattr(work, "reopen_work", fail)
    response, actual_status = _http(lambda: _save(workspace, request_id="readback-error-request"))
    assert actual_status == status
    assert response.get_json() == {"ok": False, "code": code, "publish_status": "not_performed",
        "persistence_state": "COMMITTED_READBACK_UNCONFIRMED"}
    assert _count(workspace) == before + 1
    monkeypatch.setattr(work, "reopen_work", original)
    result = _save(workspace, request_id="readback-error-request")
    assert result["replayed"] is True and _count(workspace) == before + 1


def test_replay_readback_denial_is_committed_without_extra_write(workspace, monkeypatch):
    result = _save(workspace, request_id="already-committed-request")
    before = _count(workspace)
    original = workspace["work"].reopen_work
    def denied(*args, **kwargs):
        raise PermissionError("WORK_PERMISSION_DENIED")
    monkeypatch.setattr(workspace["work"], "reopen_work", denied)
    response, status = _http(lambda: _save(workspace, request_id="already-committed-request"))
    assert status == 403 and response.get_json()["persistence_state"] == "COMMITTED_READBACK_UNCONFIRMED"
    assert _count(workspace) == before
    monkeypatch.setattr(workspace["work"], "reopen_work", original)
    replay = _save(workspace, request_id="already-committed-request")
    assert replay["artifact"]["artifact_id"] == result["artifact"]["artifact_id"]
    assert _count(workspace) == before


@pytest.mark.parametrize("adapter", ["shared", "source_brief"])
@pytest.mark.parametrize("error_type,message", [
    (PermissionError, "WORK_PERMISSION_DENIED"),
    (ValueError, "WORK_INTEGRITY_FAILED"),
    (RuntimeError, "READBACK_UNAVAILABLE"),
    (OSError, "PRIVATE_INTERNAL_IDENTIFIER"),
    (TypeError, "PRIVATE_INTERNAL_IDENTIFIER"),
])
def test_existing_error_adapters_keep_exact_classification(workspace, monkeypatch, adapter, error_type, message):
    from experience_runtime import _source_brief_job_error
    work = workspace["work"]
    def adapt(exc):
        if adapter == "source_brief":
            return _source_brief_job_error(exc)
        def raise_original():
            raise exc
        return _http(raise_original)
    ordinary, ordinary_status = adapt(error_type(message))
    expected = ordinary.get_json()
    original_reopen = work.reopen_work
    def fail(*args, **kwargs):
        raise error_type(message)
    monkeypatch.setattr(work, "reopen_work", fail)
    with pytest.raises(error_type) as caught:
        _save(workspace, request_id="adapter-classification")
    assert type(caught.value) is error_type
    assert caught.value.args == (message,)
    response, status = adapt(caught.value)
    assert status == ordinary_status
    assert response.get_json() == {**expected, "persistence_state": "COMMITTED_READBACK_UNCONFIRMED"}
    assert response.headers["Cache-Control"] == "no-store"
    if adapter == "shared" and error_type in {OSError, TypeError}:
        assert status == 503 and response.get_json()["code"] == "SHARED_WORK_UNAVAILABLE"
        assert message not in response.get_data(as_text=True)
    monkeypatch.setattr(work, "reopen_work", original_reopen)
    assert _save(workspace, request_id="adapter-classification")["replayed"] is True


def test_string_marker_does_not_masquerade_as_committed_owner_state(workspace):
    exc = ValueError("WORK_PERMISSION_DENIED")
    exc._saved_work_persistence_state = "COMMITTED_READBACK_UNCONFIRMED"
    def fail():
        raise exc
    response, status = _http(fail)
    assert status == 403 and "persistence_state" not in response.get_json()
