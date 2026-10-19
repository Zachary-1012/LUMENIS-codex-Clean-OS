"""Generated offline fixtures exercise real Importer/SQLite/Permission owners.

These are bounded integration regressions, not production factual acceptance.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sqlite3

import pytest

from tests.test_permission_exact_resource_scope import isolated_scope_database, _grant
from tests.test_saved_document_workflow import workspace, _source


@pytest.fixture
def material(isolated_scope_database, monkeypatch, tmp_path):
    import canonical_data
    import shared_artifacts
    from lumenis.importer import documents
    from lumenis.shared.database import DatabaseRepository
    from lumenis.shared.evidence import store
    from lumenis.shared.reporting import saved_work
    from lumenis.system.security import permission

    monkeypatch.setenv("ZBC_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    repository = DatabaseRepository(str(isolated_scope_database))
    for module in (documents, saved_work, shared_artifacts, store):
        monkeypatch.setattr(module, "get_repository", lambda: repository)
    shared_artifacts.ensure_artifact_table()
    canonical_data.ensure_canonical_table(str(isolated_scope_database))
    store.init_evidence_store(str(isolated_scope_database))
    with repository.transaction() as con:
        store.ensure_evidence_schema(con)
    actor = {"id": 1, "role": "user"}
    scope = {"domain_id": "cth", "subject_id": "SUBJ-CTH-A",
             "brand_focus_id": None, "global_scope": False}
    for action in ("read", "write"):
        _grant(isolated_scope_database, 1, "CTH", "reports", action,
               {"subject_ids": ["SUBJ-CTH-A"]})
    gate = permission.PermissionGate()
    gate.grant_permission(permission.PermissionLevel.COMMIT)
    monkeypatch.setattr(permission, "get_permission_gate", lambda: gate)
    monkeypatch.setattr(permission, "_TESTING_BYPASS_ENABLED", False)
    text = "店铺营业至 20:00。\n相同引文。\n相同引文。\n"
    path = tmp_path / "source.txt"
    path.write_text(text, encoding="utf-8")
    provenance = {"source_url": None, "published_at": None,
                  "captured_at": "2026-10-18T00:00:00Z", "rights": "owner-approved",
                  "title": "Generated exact-quotation source", "intended_use": "internal_draft",
                  "source_origin": {"kind": "approved-file", "ref": "factwall-fixture"}}
    args = {"actor": actor, "scope": scope, "provenance": provenance}
    resource = documents.document_import_resource(str(path), **args)
    gate.grant_approval(permission.OperationType.DATA_IMPORT.value, resource=resource,
                        granted_by="isolated-generated-test")
    imported = documents.import_document(str(path), **args)
    located = documents.locate_quote(imported["evidence_id"], actor=actor,
                                     scope=scope, start=0, end=text.index("\n"))
    row = repository.query_one("SELECT relative_path FROM lumenis_shared_artifacts WHERE artifact_id=?",
                               (imported["source_artifact_ref"],))
    return {"actor": actor, "scope": scope, "citation": located["citation"],
            "text": text, "source": imported, "repo": repository, "work": saved_work,
            "db": isolated_scope_database, "bytes": path.read_bytes(),
            "artifact_path": shared_artifacts.artifact_root() / row[0]}


def _claims(material):
    return [{"claim_id": "closing-time", "text": "店铺 19:00 关门。",
             "citations": [copy.deepcopy(material["citation"])]}]


def _verify(material, claims=None, **changes):
    from lumenis.shared.evidence.api import verify_fact_wall_claims
    args = {"actor": material["actor"], "scope": material["scope"],
            "claims": _claims(material) if claims is None else claims}
    args.update(changes)
    return verify_fact_wall_claims(**args)


def _validate(material, verified, *, con=None, context=None):
    from lumenis.shared.evidence.api import validate_fact_wall_saved_payload
    if con is None:
        with material["repo"].connection(read_only=True, wal=False) as con:
            return _validate(material, verified, con=con, context=context)
    context = context or material["work"].authorize_saved_work(
        material["actor"], material["scope"], action="read", connection=con,
    )
    return validate_fact_wall_saved_payload(connection=con, payload={"fact_wall": verified["fact_wall"]},
                                           citations=verified["citations"], context=context,
                                           actor=material["actor"])


def _resign(material, *, field=None, value=None, declaration=None):
    from lumenis.shared.evidence import store
    with material["repo"].transaction() as con:
        eid = material["citation"]["evidence_id"]
        if declaration is not None:
            metadata = json.loads(con.execute(
                "SELECT collection_metadata FROM app_evidence_records WHERE id=?", (eid,),
            ).fetchone()[0])
            metadata["provenance"].update(declaration)
            con.execute("UPDATE app_evidence_records SET collection_metadata=? WHERE id=?",
                        (json.dumps(metadata), eid))
        else:
            assert field in {"version", "provider", "content_hash"}
            con.execute(f"UPDATE app_evidence_records SET {field}=? WHERE id=?", (value, eid))
        store._sign_evidence_record(con, eid)


def test_real_import_exact_source_version_never_promotes_semantic_truth(material):
    result = _verify(material)
    claim = result["fact_wall"]["claims"][0]
    check = claim["source_checks"][0]
    assert result["fact_wall"]["claim_assessment_authority"] == "HUMAN_ONLY"
    assert claim["claim_status"] == "UNKNOWN"
    assert claim["assessment_origin"] == "NOT_REVIEWED"
    assert claim["machine_semantic_assessment"] == "NOT_PERFORMED"
    assert check["claim_relation"] == "NOT_ASSESSED"
    assert check["quote_binding"] == "EXACT_SOURCE_TEXT"
    assert check["original_artifact_bytes"] == "VERIFIED"
    assert check["source_scope"] == material["scope"]
    assert check["evidence_version"] == "document-import/1"
    assert check["source_fingerprint"] == hashlib.sha256(material["bytes"]).hexdigest()
    assert check["content_sha256"] == hashlib.sha256(material["text"].encode()).hexdigest()
    assert check["source_artifact_ref"] == material["source"]["source_artifact_ref"]
    assert result["publication_state"] == "NOT_PERFORMED"
    _validate(material, result)
    # Reusing the returned source_scope does not introduce caller truth flags.
    assert _verify(material, [{"claim_id": "again", "text": "Different interpretation",
                              "citations": result["citations"]}])["citations"] == result["citations"]


@pytest.mark.parametrize("status", ["SUPPORTED", "CONFLICTED", "UNKNOWN"])
def test_explicit_human_judgment_is_retained_as_declaration(material, status):
    claims = _claims(material)
    claims[0]["human_judgment"] = {"status": status, "note": "人工对照原文的声明"}
    claim = _verify(material, claims)["fact_wall"]["claims"][0]
    assert claim["claim_status"] == status
    assert claim["assessment_origin"] == "EXPLICIT_HUMAN_JUDGMENT"
    assert claim["source_checks"][0]["claim_relation"] == "NOT_ASSESSED"
    assert claim["machine_semantic_assessment"] == "NOT_PERFORMED"


def test_unreferenced_claim_remains_unknown_and_cannot_assert_support(material):
    claim = {"claim_id": "not-read", "text": "No citation available", "citations": []}
    assert _verify(material, [claim])["fact_wall"]["claims"][0]["claim_status"] == "UNKNOWN"
    claim["human_judgment"] = {"status": "SUPPORTED"}
    with pytest.raises(ValueError, match="FACT_WALL_JUDGMENT_REQUIRES_SOURCE"):
        _verify(material, [claim])


@pytest.mark.parametrize("change", [{"quote": "店铺营业至 19:00。"}, {"start": 1}, {"end": 999}])
def test_wrong_exact_quote_or_range_is_denied(material, change):
    claims = _claims(material)
    claims[0]["citations"][0].update(change)
    with pytest.raises(ValueError, match="WORK_CITATION_UNGROUNDED"):
        _verify(material, claims)


def test_repeated_unicode_quote_keeps_explicit_character_offset(material):
    claims = _claims(material)
    start = material["text"].rindex("相同引文。")
    claims[0]["citations"][0].update(start=start, end=start + 5, quote="相同引文。")
    result = _verify(material, claims)
    assert result["citations"][0]["start"] == start
    assert result["citations"][0]["end"] == start + 5


@pytest.mark.parametrize("case", ["duplicate", "truth_flag", "bool_id", "bool_start", "scope_forgery",
                                  "too_many_claims", "invalid_status", "purpose", "too_many_citations"])
def test_malformed_or_forged_input_fails_closed(material, case):
    claims = _claims(material)
    if case == "duplicate":
        claims *= 2
    elif case == "truth_flag":
        claims[0]["claim_status"] = "SUPPORTED"
    elif case == "bool_id":
        claims[0]["citations"][0]["evidence_id"] = True
    elif case == "bool_start":
        claims[0]["citations"][0]["start"] = False
    elif case == "scope_forgery":
        claims[0]["citations"][0]["source_scope"] = {**material["scope"], "subject_id": "SUBJ-CTH-B"}
    elif case == "too_many_claims":
        claims = [{**claims[0], "claim_id": str(i)} for i in range(51)]
    elif case == "invalid_status":
        claims[0]["human_judgment"] = {"status": "AI_VERIFIED"}
    elif case == "purpose":
        claims[0]["citations"][0]["purpose"] = "method_reference"
    else:
        claims[0]["citations"] *= 21
    with pytest.raises(ValueError):
        _verify(material, claims)


@pytest.mark.parametrize("case", ["other_actor", "other_scope", "revoked", "inactive", "wrong_role"])
def test_current_actor_and_scope_permission_are_required(material, case):
    args = {}
    if case == "other_actor":
        args["actor"] = {"id": 2, "role": "admin"}
    elif case == "other_scope":
        args["scope"] = {**material["scope"], "subject_id": "SUBJ-CTH-B"}
    elif case == "wrong_role":
        args["actor"] = {"id": 4, "role": "owner"}
    else:
        with material["repo"].transaction() as con:
            if case == "revoked":
                con.execute("DELETE FROM v4_member_authorizations WHERE user_id=1 AND action='read'")
            else:
                con.execute("UPDATE v4_users SET status='inactive' WHERE id=1")
    with pytest.raises(ValueError, match="WORK_(PERMISSION_DENIED|EVIDENCE_CONTEXT_MISMATCH)"):
        _verify(material, **args)


@pytest.mark.parametrize("case", ["modified", "missing"])
def test_original_artifact_bytes_are_required_on_every_verification(material, case):
    result = _verify(material)
    if case == "modified":
        material["artifact_path"].write_bytes(material["bytes"] + b"modified")
    else:
        material["artifact_path"].unlink()
    for operation in (lambda: _verify(material), lambda: _validate(material, result)):
        with pytest.raises(ValueError, match="DOCUMENT_SOURCE_ARTIFACT_INVALID"):
            operation()


def test_valid_new_producer_version_invalidates_saved_exact_binding(material):
    original = _verify(material)
    _resign(material, field="version", value="document-import/2")
    current = _verify(material)
    assert current["fact_wall"]["claims"][0]["source_checks"][0]["evidence_version"] == "document-import/2"
    with pytest.raises(ValueError, match="WORK_FACT_WALL_VERIFICATION_CHANGED"):
        _validate(material, original)
    _validate(material, current)


@pytest.mark.parametrize("case", ["rights", "use", "producer", "content"])
def test_trusted_signature_cannot_override_source_use_or_producer(material, case):
    if case == "rights":
        _resign(material, declaration={"rights": "unknown"})
    elif case == "use":
        _resign(material, declaration={"intended_use": "model_training"})
    elif case == "producer":
        _resign(material, field="provider", value="unrelated_writer")
    else:
        _resign(material, field="content_hash", value="0" * 64)
    with pytest.raises(ValueError, match="WORK_SOURCE_RIGHTS_UNVERIFIED|FACT_WALL_SOURCE_USE_DENIED|DOCUMENT_SOURCE_PRODUCER_INVALID|WORK_EVIDENCE_INTEGRITY_FAILED"):
        _verify(material)


@pytest.mark.parametrize("case", ["nested_citations", "authority", "status", "origin", "machine", "version", "extra_check"])
def test_saved_payload_is_recomputed_instead_of_trusting_flags(material, case):
    result = _verify(material)
    wall = result["fact_wall"]
    claim = wall["claims"][0]
    if case == "nested_citations":
        claim["citations"] = []
        claim["source_checks"] = []
    elif case == "authority":
        wall["claim_assessment_authority"] = "AI"
    elif case == "status":
        claim["claim_status"] = "SUPPORTED"
    elif case == "origin":
        claim["assessment_origin"] = "EXPLICIT_HUMAN_JUDGMENT"
    elif case == "machine":
        claim["machine_semantic_assessment"] = "VERIFIED"
    elif case == "version":
        claim["source_checks"][0]["evidence_version"] = "document-import/2"
    else:
        claim["source_checks"][0]["canonical_truth"] = True
    with pytest.raises(ValueError, match="WORK_FACT_WALL"):
        _validate(material, result)


def test_saved_hook_rejects_context_from_another_actor(material):
    result = _verify(material)
    with pytest.raises(ValueError, match="WORK_CONTEXT_MISMATCH"):
        _validate(material, result, context={**material["scope"], "actor_id": 2})


def test_permission_revoked_during_read_is_not_returned_successfully(material, monkeypatch):
    from lumenis.shared.evidence import api
    original = api._fact_wall_source_check
    def revoke(con, citation, context, actor):
        check = original(con, citation, context, actor)
        with sqlite3.connect(material["db"]) as other:
            other.execute("DELETE FROM v4_member_authorizations WHERE user_id=1 AND action='read'")
        return check
    monkeypatch.setattr(api, "_fact_wall_source_check", revoke)
    with pytest.raises(ValueError, match="WORK_PERMISSION_DENIED"):
        _verify(material)


def test_shared_scope_uses_current_local_workspace_permission_without_new_grant(workspace):
    from lumenis.shared.evidence.api import verify_fact_wall_claims, validate_fact_wall_saved_payload
    _, _, source = _source(workspace)
    citation = workspace["documents"].locate_quote(source["evidence_id"], actor=workspace["actor"],
                                                 scope=workspace["scope"], start=0, end=20)["citation"]
    scope = {"scope_kind": "shared_workspace", "version": 1}
    result = verify_fact_wall_claims(actor=workspace["actor"], scope=scope,
                                    claims=[{"claim_id": "local", "text": "A declaration", "citations": [citation]}])
    assert result["fact_wall"]["scope"] == scope
    with workspace["repo"].connection(read_only=True, wal=False) as con:
        context = workspace["work"].authorize_saved_work(workspace["actor"], scope, action="read", connection=con)
        validate_fact_wall_saved_payload(connection=con, payload={"fact_wall": result["fact_wall"]},
                                         citations=result["citations"], context=context, actor=workspace["actor"])


def test_saved_work_transaction_hook_and_independent_reopen(material):
    result = _verify(material)
    def check(con, record, document):
        _validate(material, {"fact_wall": document["payload"]["fact_wall"],
                             "citations": document["citations"]}, con=con)
    saved = material["work"].save_work(title="Exact source review", markdown="Human review pending.",
        kind="research", payload={"fact_wall": result["fact_wall"]}, citations=result["citations"],
        request_id="fact-wall-save", actor=material["actor"], scope=material["scope"], before_commit=check)
    reopened = material["work"].reopen_work(saved["artifact"]["artifact_id"],
                                            actor=material["actor"], scope=material["scope"])
    assert reopened["document"]["payload"]["fact_wall"] == result["fact_wall"]
    assert reopened["receipt"]["constraint_observations"]["factual_verification"] == "NOT_ESTABLISHED_BY_STORAGE"
    _validate(material, {"fact_wall": reopened["document"]["payload"]["fact_wall"],
                         "citations": reopened["document"]["citations"]})


def test_precommit_version_change_rolls_back_work(material):
    result = _verify(material)
    before = material["repo"].query_one("SELECT COUNT(*) FROM lumenis_shared_artifacts")[0]
    def changed(con, record, document):
        from lumenis.shared.evidence import store
        con.execute("UPDATE app_evidence_records SET version='document-import/2' WHERE id=?",
                    (material["citation"]["evidence_id"],))
        store._sign_evidence_record(con, material["citation"]["evidence_id"])
        _validate(material, result, con=con)
    with pytest.raises(ValueError, match="WORK_FACT_WALL_VERIFICATION_CHANGED"):
        material["work"].save_work(title="Stale source review", markdown="Do not persist stale bindings.",
            kind="research", payload={"fact_wall": result["fact_wall"]}, citations=result["citations"],
            request_id="fact-wall-rollback", actor=material["actor"], scope=material["scope"], before_commit=changed)
    assert material["repo"].query_one("SELECT COUNT(*) FROM lumenis_shared_artifacts")[0] == before
    assert material["repo"].query_one("SELECT version FROM app_evidence_records WHERE id=?",
                                     (material["citation"]["evidence_id"],))[0] == "document-import/1"


def test_source_changed_between_quote_and_version_check_is_rejected(material, monkeypatch):
    from lumenis.shared.evidence import store
    work = material["work"]
    original = work._validate_citations
    changed = False
    def replace_after_quote(con, citations, context, actor=None):
        nonlocal changed
        result = original(con, citations, context, actor)
        if not changed:
            changed = True
            text = material["text"].replace("20:00", "19:00")
            raw = text.encode()
            digest = hashlib.sha256(raw).hexdigest()
            eid = material["citation"]["evidence_id"]
            material["artifact_path"].write_bytes(raw)
            with material["repo"].transaction() as other:
                metadata = json.loads(other.execute(
                    "SELECT collection_metadata FROM app_evidence_records WHERE id=?", (eid,),
                ).fetchone()[0])
                metadata.update(parsed_text=text, source_fingerprint=digest)
                other.execute("UPDATE lumenis_shared_artifacts SET sha256=?,size_bytes=? WHERE artifact_id=?",
                              (digest, len(raw), material["source"]["source_artifact_ref"]))
                other.execute("UPDATE app_evidence_records SET collection_metadata=?,content_hash=? WHERE id=?",
                              (json.dumps(metadata), digest, eid))
                store._sign_evidence_record(other, eid)
        return result
    monkeypatch.setattr(work, "_validate_citations", replace_after_quote)
    with pytest.raises(ValueError, match="WORK_CITATION_UNGROUNDED"):
        _verify(material)


def test_alternate_database_cannot_supply_authority(material):
    with sqlite3.connect(":memory:") as con:
        con.row_factory = sqlite3.Row
        with pytest.raises(ValueError, match="RESOURCE_SCOPE_CONNECTION_INVALID"):
            _verify(material, connection=con)


def test_verification_writes_no_source_artifact_canonical_or_evaluation_rows(material):
    def snapshot():
        with material["repo"].connection(read_only=True, wal=False) as con:
            tables = [row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            return {name: [tuple(row) for row in con.execute('SELECT * FROM "' + name.replace('"', '""') + '"')]
                    for name in tables}
    before = snapshot()
    result = _verify(material)
    _validate(material, result)
    assert snapshot() == before


@pytest.mark.parametrize("key,value", [("evidence_version", None), ("integrity_digest", True),
                                      ("source_fingerprint", "0" * 64), ("source_artifact_ref", 1),
                                      ("rights", "unknown"), ("intended_use", "model_training")])
def test_source_pin_types_and_values_cannot_be_substituted(material, key, value):
    result = _verify(material)
    result["fact_wall"]["claims"][0]["source_checks"][0][key] = value
    with pytest.raises(ValueError, match="WORK_FACT_WALL_VERIFICATION_CHANGED"):
        _validate(material, result)
