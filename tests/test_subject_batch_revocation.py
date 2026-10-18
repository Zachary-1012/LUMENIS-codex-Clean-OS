import pytest
from tests.test_saved_document_workflow import workspace


def test_registry_rechecks_inside_write_transaction_and_rolls_back(workspace):
    import subject_registry as registry

    ws = workspace
    with ws["repo"].transaction() as con:
        registry.ensure_schema(con)
    calls = []

    def authorize():
        calls.append(True)
        if len(calls) == 2:
            raise PermissionError("synthetic exact approval revoked before commit")

    with pytest.raises(PermissionError, match="revoked"):
        registry.add_subject(
            {
                "domain_id": "BMP",
                "subject_type": "brand",
                "name_en": "Revoked brand",
                "name_zh": "撤销品牌",
            },
            strict_identity=True,
            _authorize_write=authorize,
        )
    assert len(calls) == 2
    assert not registry.list_subjects("BMP")


def test_registry_revocation_while_waiting_for_write_lock(workspace, monkeypatch):
    import contextlib
    import threading
    import subject_registry as registry
    ws = workspace
    with ws['repo'].transaction() as con:
        registry.ensure_schema(con)
    resource = 'subject-registry-batch:v1:synthetic-lock-test'
    token = ws['gate'].grant_approval('config_modify', resource=resource, granted_by='synthetic-explicit-review')
    opened = threading.Event()
    original = registry._db_ready
    @contextlib.contextmanager
    def observed_connection():
        with original() as con:
            opened.set()
            yield con
    monkeypatch.setattr(registry, '_db_ready', observed_connection)
    failures = []
    def authorize():
        if ws['gate'].get_valid_approval_token('config_modify', resource, exact=True) is None:
            raise PermissionError('EXACT_APPROVAL_REVOKED_WHILE_WAITING')
    def writer():
        try:
            registry.add_subject({'domain_id':'BMP','subject_type':'brand','name_en':'Locked brand','name_zh':'锁定品牌'},
                                 strict_identity=True, _authorize_write=authorize)
        except Exception as exc:
            failures.append(exc)
    with ws['repo'].transaction() as blocker:
        blocker.execute('BEGIN IMMEDIATE') if not blocker.in_transaction else None
        thread = threading.Thread(target=writer)
        thread.start()
        assert opened.wait(3)
        ws['gate'].revoke_approval(token)
    thread.join(5)
    assert not thread.is_alive()
    assert len(failures) == 1 and 'REVOKED_WHILE_WAITING' in str(failures[0])
    assert not registry.list_subjects('BMP')
