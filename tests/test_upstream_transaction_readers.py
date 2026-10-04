"""Public upstream readers retain complete receipts and caller-transaction checks."""
import copy
import json
import sqlite3

import pytest

from tests.test_saved_document_workflow import workspace, _source, _save
from tests.test_source_brief_job import job_db
from tests.test_source_brief_job_routes import client, GLOBAL, URL


def test_saved_public_reader_borrows_transaction_keeps_parent_and_rejects_withdrawal(workspace):
    import subject_registry
    from lumenis.shared.reporting import saved_work
    ws = workspace
    with ws["repo"].transaction() as con:
        subject_registry.ensure_schema(con)
    entry, _ = subject_registry.add_subject({"domain_id": "CTH", "subject_type": "company",
                                           "name_en": "Scoped upstream source", "name_zh": "上游来源"})
    global_scope = ws["scope"]
    ws["scope"] = {**global_scope, "global_scope": False, "subject_id": entry["subject_id"]}
    _path, _args, source = _source(ws)
    cited = ws["documents"].locate_quote(source["evidence_id"], actor=ws["actor"], scope=ws["scope"], start=0, end=20)["citation"]
    ws["scope"] = global_scope
    first = _save(ws, citations=[cited])
    second = _save(ws, citations=[cited], request_id="upstream-reader-revision-02", work_id=first["document"]["work_id"],
                   previous_artifact_id=first["artifact"]["artifact_id"], markdown="Second complete research version.")
    with ws["repo"].connection() as con:
        con.execute("BEGIN IMMEDIATE")
        read = saved_work.read_committed_work(second["artifact"]["artifact_id"], actor=ws["actor"], scope=global_scope, connection=con)
        assert read["receipt"]["parent"]["ref"] == first["artifact"]["artifact_id"]
        assert read["receipt"]["sources"][0]["evidence_id"] == source["evidence_id"]
        assert con.in_transaction
        con.execute("UPDATE lumenis_subject_registry SET status='inactive' WHERE subject_id=?", (entry["subject_id"],))
        with pytest.raises(ValueError, match="WORK_PERMISSION_DENIED"):
            saved_work.read_committed_work(second["artifact"]["artifact_id"], actor=ws["actor"], scope=global_scope, connection=con)
        assert con.in_transaction
        con.rollback()
    assert saved_work.reopen_work(second["artifact"]["artifact_id"], actor=ws["actor"], scope=global_scope)["document"]["version"] == 2


def test_uncommitted_artifact_cannot_receive_committed_reader_receipt(workspace):
    import shared_artifacts
    from lumenis.shared.reporting import saved_work
    ws = workspace
    saved = _save(ws)
    with ws["repo"].connection() as con:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute("SELECT * FROM lumenis_shared_artifacts WHERE artifact_id=?", (saved["artifact"]["artifact_id"],))
        old = dict(zip([column[0] for column in cur.description], cur.fetchone()))
        old["artifact_id"] = "ART-" + "a" * 16
        fields = list(old)
        con.execute("INSERT INTO lumenis_shared_artifacts (" + ",".join(fields) + ") VALUES (" + ",".join("?" for _ in fields) + ")",
                    [old[key] for key in fields])
        with pytest.raises(ValueError, match="WORK_NOT_COMMITTED"):
            saved_work.read_committed_work(old["artifact_id"], actor=ws["actor"], scope=ws["scope"], connection=con)
        assert con.in_transaction
        con.rollback()


def test_source_brief_public_reader_checks_actual_actor_and_same_transaction_scope(client):
    from lumenis.shared.database import get_repository
    from lumenis.shared.reporting.source_brief_job import get_source_brief_job
    from lumenis.system.security.permission import resolve_local_workspace_principal
    api, app, db, entry, _gate = client
    headers = {**GLOBAL, "X-Lumenis-Context-Mode": "FOCUS", "X-Subject-ID": entry["subject_id"]}
    result = api.post(URL + "/generate", headers=headers, json={}).get_json()["result"]
    with app.test_request_context("/", headers={**headers, "Host": "localhost"}, environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        actor = resolve_local_workspace_principal(module="reports", action="read")
        with get_repository().connection() as con:
            con.execute("BEGIN IMMEDIATE")
            read = get_source_brief_job(result["job_id"], actor_id=actor.principal_ref,
                expected_scope=result["source_brief"]["scope"], actor=actor, connection=con)
            assert read["source_brief"] == result["source_brief"] and con.in_transaction
            con.execute("UPDATE lumenis_subject_registry SET status='inactive' WHERE subject_id=?", (entry["subject_id"],))
            with pytest.raises(ValueError, match="WORK_PERMISSION_DENIED"):
                get_source_brief_job(result["job_id"], actor_id=actor.principal_ref,
                    expected_scope=result["source_brief"]["scope"], actor=actor, connection=con)
            assert con.in_transaction
            con.rollback()


def test_public_reader_rejects_client_dictionary_as_connection(workspace):
    from lumenis.shared.reporting import saved_work
    from lumenis.shared.reporting.source_brief_job import get_source_brief_job
    ws = workspace
    item = _save(ws)
    with pytest.raises((ValueError, RuntimeError, TypeError)):
        saved_work.read_committed_work(item["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"], connection={"role": "owner"})
    with pytest.raises((ValueError, RuntimeError, TypeError)):
        get_source_brief_job("job-" + "a" * 32, actor_id=ws["actor"].principal_ref, actor=ws["actor"], connection={"role": "owner"})
