"""Synthetic C3 approval-continuity integration; never live-user acceptance."""
from __future__ import annotations

import copy
import hashlib
import json

import pytest

from lumenis.importer.documents import SavedWorkError
from lumenis.system.security import permission
from tests.test_business_result_continuity import adopt, make_options, save, selection

pytest_plugins = (
    "tests.test_business_result_continuity",
    "tests.test_saved_document_workflow",
)


_TEST_RECEIPT_ID = "TEST-ONLY-C3-APPROVED-SOURCE-CONTINUITY"
_RUNTIME_RECEIPT_ID = "PO-20261011-APPROVED-INTERNAL-SOURCE-USE"
_CAPTURED_AT = "2026-10-08T08:00:00Z"
_PUBLISHED_AT = "2026-10-07T09:15:00Z"


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":"))


def _receipt_entry(ws, *, source_id, canonical_id, source_url, body, scope_locator,
                   content_locator, rights_state, snapshot_kind):
    domain = ws["domain_scope"]["domain_id"]
    purposes = ["internal_research", "short_quote",
                "cth_brief" if domain == "cth" else "bmp_brief"]
    return {
        "source_id": source_id,
        "source_url": source_url,
        "canonical_id": canonical_id,
        "domain_id": domain,
        "subject_id": ws["domain_scope"].get("subject_id"),
        "brand_focus_id": ws["domain_scope"].get("brand_focus_id"),
        "scope_evidence_ref": scope_locator,
        "content_evidence_ref": content_locator,
        "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "rights_state": rights_state,
        "snapshot_kind": snapshot_kind,
        "allowed_purposes": purposes,
        "allowed_operations": ["derive_reference", "read", "save", "revise", "reopen"],
        "commercial_state": "UNKNOWN",
        "publication_state": "NOT_APPROVED",
        "training_state": "NOT_APPROVED",
    }


def _install_test_receipt(monkeypatch, entry):
    """Replace only receipt loading; all source, Permission, resolver and save checks stay real."""
    domain = entry["domain_id"]
    purpose = "cth_brief" if domain == "cth" else "bmp_brief"
    receipt = {
        "schema": "lumenis.po-approval-receipt/v1",
        "source_use_schema": "lumenis.approved-internal-source-use/v1",
        "receipt_id": _TEST_RECEIPT_ID,
        "approval_id": _TEST_RECEIPT_ID,
        "approval_source_type": "test_fixture_only",
        "approved_at": "2026-10-11",
        "approved_by": "isolated pytest fixture",
        "status": "TEST_ONLY",
        "constraints": ["Synthetic source only; no legal rights or external use."],
        "scope_manifest": {"test_only": True, "sources": [entry["source_id"]],
                            "purpose_by_domain": {domain: purpose}},
        "sources": [entry],
        "quote_limit": {
            "max_unique_unicode_codepoints_per_source_per_saved_work": 160,
            "measurement": "unicode-codepoints",
            "scope": "Synthetic fixture only.",
        },
    }
    calls = []

    def load_test_receipt(receipt_id):
        calls.append(receipt_id)
        assert receipt_id == _RUNTIME_RECEIPT_ID
        return receipt

    monkeypatch.setattr(permission, "_load_source_use_receipt", load_test_receipt)
    return receipt, calls


def _scope_evidence(ws, source_id):
    from lumenis.shared.evidence import store

    domain = ws["domain_scope"]["domain_id"]
    product = "CTH" if domain == "cth" else "ZBMP"
    with ws["repo"].transaction() as con:
        evidence_id = store.record_evidence(
            connection=con,
            source="test_fixture",
            project="LUMENIS",
            product=product,
            feature_id="C3_APPROVED_SOURCE_SCOPE_FIXTURE",
            asset_id=source_id,
            version="synthetic-source-scope/v1",
            env="staging",
            test_name="c3-approved-source-scope-fixture",
            capture_mode="synthetic_test_fixture",
            inputs={"source_ids": [source_id], "fixture_only": True},
            outputs={"scope_binding": "test-only"},
            result="PASS",
            status="verified",
            domain_id=domain,
            subject_id=ws["domain_scope"].get("subject_id"),
            brand_focus_id=ws["domain_scope"].get("brand_focus_id"),
            global_scope=False,
        )
        return evidence_id


def _install_test_source_scope_declaration(ws, monkeypatch):
    """Model source-scope columns absent from the generic Evidence table fixture.

    The source-use verifier consumes exact top-level scope fields, while the
    generic Evidence writer stores them in inputs_json. Keep create/resolve and
    signing real; adapt only the isolated fixture's current-source declaration.
    """
    from lumenis.shared.evidence import store

    with ws["repo"].transaction() as con:
        columns = {row[1] for row in con.execute(
            "PRAGMA table_info(app_evidence_records)",
        ).fetchall()}
        if "subject_id" not in columns:
            con.execute("ALTER TABLE app_evidence_records ADD COLUMN subject_id TEXT")
        if "brand_focus_id" not in columns:
            con.execute("ALTER TABLE app_evidence_records ADD COLUMN brand_focus_id TEXT")
    record_evidence = store.record_evidence

    def record_with_current_scope(*args, **kwargs):
        evidence_id = record_evidence(*args, **kwargs)
        connection = kwargs.get("connection")
        if type(evidence_id) is int and evidence_id > 0:
            if connection is None:
                raise AssertionError("fixture-scoped Evidence writes must use the isolated transaction")
            connection.execute(
                "UPDATE app_evidence_records SET subject_id=?,brand_focus_id=? WHERE id=?",
                (kwargs.get("subject_id"), kwargs.get("brand_focus_id"), evidence_id),
            )
            store._sign_evidence_record(connection, evidence_id)
        return evidence_id

    monkeypatch.setattr(store, "record_evidence", record_with_current_scope)


def _seed_cth_notes_parent(ws):
    import canonical_data
    from lumenis.shared.database.business_schema import apply_business_schema

    source_id = "fixture-cth-note-parent-20261011"
    source_url = "https://source.example.test/cth/approved-note-fixture"
    body = "门店公开说明与运营问题待人工核对。" + ("来源原文。" * 32)
    scope_evidence_id = _scope_evidence(ws, source_id)

    with ws["repo"].transaction() as con:
        apply_business_schema(con)
        columns = {row[1] for row in con.execute("PRAGMA table_info(notes)").fetchall()}
        if "rights" in columns:
            rights_column = "rights"
        elif "rights_state" in columns:
            rights_column = "rights_state"
        else:
            # Test-only column lets this isolated note model a later rights withdrawal.
            con.execute("ALTER TABLE notes ADD COLUMN rights_state TEXT")
            rights_column = "rights_state"
            columns.add(rights_column)

        fields = {
            "note_id": source_id,
            "title": "Synthetic CTH note source",
            "content": body,
            "url": source_url,
            "source_platform": "public_web_fixture",
            "collected_at": _CAPTURED_AT,
            "publish_date": _PUBLISHED_AT,
            "subject_id": ws["domain_scope"]["subject_id"],
            "scope_status": "VERIFIED",
            "scope_evidence_ref": str(scope_evidence_id),
            rights_column: None,
        }
        names = [name for name in fields if name in columns]
        marks = ", ".join("?" for _ in names)
        con.execute(
            f"INSERT INTO notes ({', '.join(names)}) VALUES ({marks})",
            tuple(fields[name] for name in names),
        )
        note_row = dict(con.execute("SELECT * FROM notes WHERE note_id=?", (source_id,)).fetchone())
        # Some seeded notes schemas predate scoped Canonical fields. Supply the
        # exact signed Evidence scope through the Canonical owner, without
        # changing or promoting the source note itself.
        note_row.update({
            "domain_id": "cth",
            "product_id": "CTH",
            "scope_status": "VERIFIED",
            "scope_evidence_ref": str(scope_evidence_id),
            "subject_id": ws["domain_scope"].get("subject_id"),
        })
        canonical = canonical_data.note_to_canonical(note_row, product_id="CTH")
        canonical_data.persist_canonical(con, canonical)

    note_pk = note_row["id"]
    locator = f"notes:{note_pk}"
    entry = _receipt_entry(
        ws, source_id=source_id, canonical_id=canonical.canonical_id,
        source_url=source_url, body=body, scope_locator=locator,
        content_locator=locator, rights_state="UNKNOWN",
        snapshot_kind="existing_canonical_content_snapshot_not_native_capture",
    )
    return {
        "source_id": source_id,
        "canonical_id": canonical.canonical_id,
        "body": body,
        "entry": entry,
        "note_pk": note_pk,
        "rights_column": rights_column,
        "scope_evidence_id": scope_evidence_id,
        "content_evidence_id": None,
    }


def _seed_bmp_evidence_parent(ws):
    import canonical_data
    from canonical_data import CanonicalRecord
    from lumenis.shared.evidence import store
    from lumenis.shared.reporting import saved_work

    source_id = "fixture-bmp-collected-parent-20261011"
    source_url = "https://source.example.test/bmp/approved-evidence-fixture"
    body = "品牌公开内容样本，传播效果与商业结果尚未测量。" + ("仅供内部研究核对。" * 24)
    raw = body.encode("utf-8")
    body_sha256 = hashlib.sha256(raw).hexdigest()
    scope = ws["scope"]
    context = saved_work.authorize(ws["actor"], scope, action="write")
    owner = {key: value for key, value in context.items()
             if key not in {"domain_id", "subject_id", "brand_focus_id", "global_scope"}}
    scope_evidence_id = _scope_evidence(ws, source_id)
    metadata = {
        "context": context,
        "owner": owner,
        "source_fingerprint": body_sha256,
        "parsed_text": body,
        "capture_mode": "synthetic_test_fixture",
        "autonomous_collection": False,
        "provenance": {
            "source_url": source_url,
            "published_at": _PUBLISHED_AT,
            "captured_at": _CAPTURED_AT,
            "rights": "UNREVIEWED",
            "intended_use": "research_reference",
            "title": "Synthetic BMP source Evidence parent",
            "content_origin": {"kind": "self-authored", "claim_type": "synthetic_sample"},
            "rights_statement": "Test fixture only; no live source or rights grant.",
        },
    }
    with ws["repo"].transaction() as con:
        artifact, _artifact_path = saved_work._stage_bytes(
            con, raw=raw, context=context, kind="imported_document_source",
            source_execution_id=source_id, extension=".txt", media_type="text/plain; charset=utf-8",
        )
        metadata["source_artifact_ref"] = artifact["artifact_id"]
        content_evidence_id = store.record_evidence(
            connection=con,
            source="test_fixture",
            project="LUMENIS",
            product="ZBMP",
            feature_id="C3_APPROVED_SOURCE_CONTENT_FIXTURE",
            asset_id=source_id,
            version="synthetic-source-content/v1",
            env="staging",
            test_name="c3-approved-source-content-fixture",
            capture_mode="synthetic_test_fixture",
            inputs={"source_ids": [source_id], "fixture_only": True},
            outputs={"body_sha256": body_sha256},
            result="PASS",
            status="verified",
            raw_content=body,
            collection_metadata=metadata,
            provider="test_fixture",
            domain_id="zbmp",
            subject_id=None,
            brand_focus_id=scope["brand_focus_id"],
            global_scope=False,
        )
        con.execute(
            "UPDATE lumenis_shared_artifacts SET evidence_id=? WHERE artifact_id=?",
            (str(content_evidence_id), artifact["artifact_id"]),
        )
        canonical = CanonicalRecord(
            canonical_id="canonical-" + source_id,
            product_id="ZBMP",
            domain_id="zbmp",
            subject_id="",
            brand_focus_id=scope["brand_focus_id"],
            scope_status="VERIFIED",
            scope_evidence_ref=str(scope_evidence_id),
            source_id=source_id,
            external_id=source_id,
            source_type="collected_note",
            source_table="app_evidence_records",
            source_platform="test_fixture",
            title="Synthetic BMP source Evidence parent",
            content=body,
            url=source_url,
            canonical_url=source_url,
            publish_datetime=_PUBLISHED_AT,
            captured_at=_CAPTURED_AT,
            provenance=_json({"fixture_only": True, "rights": "UNREVIEWED"}),
            raw_ref=_json({"content_evidence_ref": f"app_evidence_records:{content_evidence_id}"}),
        )
        canonical_data.persist_canonical(con, canonical)

    entry = _receipt_entry(
        ws, source_id=source_id, canonical_id=canonical.canonical_id,
        source_url=source_url, body=body,
        scope_locator=f"app_evidence_records:{scope_evidence_id}",
        content_locator=f"app_evidence_records:{content_evidence_id}",
        rights_state="UNREVIEWED", snapshot_kind="existing_source_evidence_snapshot",
    )
    return {
        "source_id": source_id,
        "canonical_id": canonical.canonical_id,
        "body": body,
        "entry": entry,
        "note_pk": None,
        "rights_column": None,
        "scope_evidence_id": scope_evidence_id,
        "content_evidence_id": content_evidence_id,
    }


def _source_snapshot(ws, source):
    row = ws["repo"].query_one(
        "SELECT canonical_id,source_id,domain_id,product_id,subject_id,brand_focus_id,"
        "scope_status,scope_evidence_ref,content,url,content_hash,provenance "
        "FROM canonical_data WHERE canonical_id=?",
        (source["canonical_id"],),
    )
    return tuple(row)


def _source_rights(ws, source):
    if source["note_pk"] is not None:
        row = ws["repo"].query_one(
            f"SELECT {source['rights_column']} FROM notes WHERE id=?", (source["note_pk"],),
        )
        return row[0]
    row = ws["repo"].query_one(
        "SELECT collection_metadata FROM app_evidence_records WHERE id=?",
        (source["content_evidence_id"],),
    )
    return json.loads(row[0])["provenance"]["rights"]


def _revoke_current_source_rights(ws, source):
    if source["note_pk"] is not None:
        with ws["repo"].transaction() as con:
            con.execute(
                f"UPDATE notes SET {source['rights_column']}='WITHDRAWN' WHERE id=?",
                (source["note_pk"],),
            )
        return

    from lumenis.shared.evidence import store

    with ws["repo"].transaction() as con:
        row = con.execute(
            "SELECT collection_metadata FROM app_evidence_records WHERE id=?",
            (source["content_evidence_id"],),
        ).fetchone()
        metadata = json.loads(row[0])
        metadata["provenance"]["rights"] = "WITHDRAWN"
        con.execute(
            "UPDATE app_evidence_records SET collection_metadata=? WHERE id=?",
            (_json(metadata), source["content_evidence_id"]),
        )
        # Re-sign this synthetic current-source declaration through the Evidence owner.
        store._sign_evidence_record(con, source["content_evidence_id"])


def _prepare_and_choose(ws, source):
    product = "CTH" if ws["domain_scope"]["domain_id"] == "cth" else "ZBMP"
    with ws["repo"].transaction() as con:
        report = ws["jobs"].create_source_brief_job(
            con,
            product_id=product,
            subject_id=ws["domain_scope"].get("subject_id"),
            brand_focus_id=ws["domain_scope"].get("brand_focus_id"),
            global_scope=False,
            entity_label="Isolated C3 approved-source fixture",
            source_ids=[source["source_id"]],
            actor_id=ws["actor"].principal_ref,
            permission_audit_ref="isolated-approved-source-audit",
            trace_id="isolated-approved-source-trace",
            job_id="isolated-approved-source-" + ws["domain_scope"]["domain_id"],
        )

    options = make_options(source["source_id"])
    question = "Which source-bounded internal review should be prepared?"
    kind = "venue_operations" if product == "CTH" else "brand_market"
    prepared = ws["service"].prepare(
        actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
        submission_id="approved-source-prepare-" + ws["domain_scope"]["domain_id"],
        source_job_id=report["job_id"], kind=kind, question=question,
        options=options, authorize=ws["authorize"],
    )
    chosen = ws["service"].advance(
        prepared["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
        authorize=ws["authorize"], expected_revision=prepared["revision"],
        submission_id="approved-source-choose-" + ws["domain_scope"]["domain_id"],
        operation="choose", payload=selection("A", "100"),
    )
    ws.update(current=chosen, options=options, citation=None)
    return report


def _resolve(documents, ws, source):
    with ws["repo"].connection() as con:
        return documents.resolve_approved_source_reference(
            con, source_id=source["source_id"], canonical_id=source["canonical_id"],
            domain_id=ws["domain_scope"]["domain_id"],
            subject_id=ws["domain_scope"].get("subject_id"),
            brand_focus_id=ws["domain_scope"].get("brand_focus_id"),
            source_content_locator=source["entry"]["content_evidence_ref"],
            body_sha256=source["entry"]["body_sha256"],
        )


def _confirm_source_reference_import(ws, source, *, request_id, expected_resource=None):
    request = {
        "source_id": source["source_id"],
        "canonical_id": source["canonical_id"],
        "expected_body_sha256": source["entry"]["body_sha256"],
        "request_id": request_id,
    }
    pending = permission.prepare_approved_source_reference_confirmation(
        actor=ws["actor"], scope=ws["scope"], request=request, gate=ws["gate"],
    )
    assert pending["allowed"] is True
    assert pending["code"] == "APPROVED_SOURCE_REFERENCE_CONFIRMATION_PENDING"
    if expected_resource is not None:
        assert pending["resource"] == expected_resource

    confirmed = permission.confirm_approved_source_reference_confirmation(
        actor=ws["actor"], scope=ws["scope"],
        confirmation_id=pending["confirmation_id"], confirmed=True, gate=ws["gate"],
    )
    assert confirmed["allowed"] is True
    assert confirmed["code"] == "APPROVED_SOURCE_REFERENCE_READY_FOR_RETRY"
    assert "approval_token" not in confirmed
    return request


def test_approved_source_survives_domain_save_revision_reopen_and_recovery(
        business, monkeypatch):
    """Exercise one exact domain per case through Importer, C3 and Shared owners."""
    ws = business
    expected_domain = ws["domain_scope"]["domain_id"]
    assert ws["domain_scope"]["domain_id"] == expected_domain
    _install_test_source_scope_declaration(ws, monkeypatch)

    source = (_seed_cth_notes_parent(ws) if expected_domain == "cth"
              else _seed_bmp_evidence_parent(ws))
    entry = source["entry"]
    receipt, receipt_loads = _install_test_receipt(monkeypatch, entry)
    canonical_row = ws["repo"].query_one(
        "SELECT canonical_id,source_id,domain_id,product_id,subject_id,brand_focus_id,"
        "scope_status,url,content FROM canonical_data WHERE canonical_id=?",
        (source["canonical_id"],),
    )
    assert canonical_row is not None
    canonical_fields = dict(canonical_row)
    expected_focus = (ws["domain_scope"].get("subject_id") if expected_domain == "cth"
                      else ws["domain_scope"].get("brand_focus_id"))
    assert canonical_fields["source_id"] == source["source_id"], canonical_fields
    assert canonical_fields["domain_id"] == expected_domain, canonical_fields
    assert canonical_fields["product_id"] == ("CTH" if expected_domain == "cth" else "ZBMP"), canonical_fields
    assert canonical_fields["scope_status"] == "VERIFIED", canonical_fields
    assert canonical_fields["subject_id"] == (expected_focus or "" if expected_domain == "cth" else ""), canonical_fields
    assert canonical_fields["brand_focus_id"] == (expected_focus or "" if expected_domain == "zbmp" else ""), canonical_fields
    scope_row = ws["repo"].query_one(
        "SELECT domain_id,subject_id,brand_focus_id,result,status FROM app_evidence_records WHERE id=?",
        (source["scope_evidence_id"],),
    )
    assert scope_row is not None
    scope_fields = dict(scope_row)
    assert scope_fields["domain_id"] == expected_domain, scope_fields
    assert scope_fields["subject_id"] == (expected_focus if expected_domain == "cth" else None), scope_fields
    assert scope_fields["brand_focus_id"] == (expected_focus if expected_domain == "zbmp" else None), scope_fields
    assert scope_fields["result"] == "PASS" and scope_fields["status"] == "verified", scope_fields
    if source["content_evidence_id"] is not None:
        content_row = ws["repo"].query_one(
            "SELECT * FROM app_evidence_records WHERE id=?", (source["content_evidence_id"],),
        )
        assert content_row is not None
        from lumenis.shared.evidence.store import classify_evidence_integrity
        integrity = classify_evidence_integrity(dict(content_row))
        assert integrity.get("verified") is True, {"evidence": dict(content_row), "integrity": integrity}
    before_canonical = _source_snapshot(ws, source)
    before_rights = _source_rights(ws, source)
    if expected_domain == "cth":
        assert before_rights is None
    else:
        assert before_rights == "UNREVIEWED"

    from lumenis.importer import documents
    from lumenis.shared.evidence import store
    from lumenis.shared.reporting import saved_work

    import_resource = documents.prepare_approved_source_reference(
        source_id=source["source_id"], canonical_id=source["canonical_id"],
        expected_body_sha256=entry["body_sha256"],
        request_id="approved-source-reference-" + expected_domain,
        actor=ws["actor"], scope=ws["scope"],
    )["resource"]
    repeated_resource = documents.prepare_approved_source_reference(
        source_id=source["source_id"], canonical_id=source["canonical_id"],
        expected_body_sha256=entry["body_sha256"],
        request_id="approved-source-reference-" + expected_domain,
        actor=ws["actor"], scope=ws["scope"],
    )["resource"]
    assert repeated_resource == import_resource, "Same source request must retain its exact approval resource"
    source_reference_request = _confirm_source_reference_import(
        ws, source, request_id="approved-source-reference-" + expected_domain,
        expected_resource=import_resource,
    )
    created = documents.create_approved_source_reference(
        **source_reference_request,
        actor=ws["actor"], scope=ws["scope"],
    )
    resolved = _resolve(documents, ws, source)
    assert created["ok"] is True and created["replayed"] is False
    assert resolved["evidence_id"] == created["evidence_id"]
    assert resolved["body_sha256"] == entry["body_sha256"]
    assert resolved["source_content_locator"] == entry["content_evidence_ref"]
    assert resolved["source_reference_parent"]["scope_evidence_ref"] == entry["scope_evidence_ref"]
    assert _source_snapshot(ws, source) == before_canonical
    assert _source_rights(ws, source) == before_rights

    derived = ws["repo"].query_one(
        "SELECT collection_metadata FROM app_evidence_records WHERE id=?",
        (created["evidence_id"],),
    )
    derived_provenance = json.loads(derived[0])["provenance"]
    assert derived_provenance["rights"] == entry["rights_state"]
    derived_marker = derived_provenance["approved_internal_source_use"]
    assert derived_marker["rights_state"] == entry["rights_state"]
    assert derived_marker["commercial_state"] == "UNKNOWN"
    assert derived_marker["publication_state"] == "NOT_APPROVED"
    assert derived_marker["training_state"] == "NOT_APPROVED"

    # The receipt revocation is tested independently of source-rights withdrawal.
    receipt["sources"] = []
    with pytest.raises(SavedWorkError, match="SOURCE_USE_SOURCE_NOT_APPROVED"):
        _resolve(documents, ws, source)
    receipt["sources"] = [entry]

    quote_end = 160
    citation = documents.locate_quote(
        created["evidence_id"], actor=ws["actor"], scope=ws["scope"],
        start=0, end=quote_end,
    )["citation"]
    assert len(citation["quote"]) == 160
    report = _prepare_and_choose(ws, source)
    ws["citation"] = citation

    # Drop the first committed response to model a caller timeout; retry the exact
    # immutable request and require Shared's persisted receipt to replay it once.
    _ = save(ws, request_id="approved-source-save-" + expected_domain)
    replay = save(ws, request_id="approved-source-save-" + expected_domain)
    first = replay["saved_work"]
    assert first["replayed"] is True
    assert first["document"]["version"] == 1
    assert len(first["document"]["citations"][0]["quote"]) == 160
    first_binding = first["document"]["payload"]["business_work"]["source_bindings"][0]
    assert first_binding["source_id"] == source["source_id"]
    assert first_binding["source_content_locator"] == entry["content_evidence_ref"]
    assert first_binding["content_evidence_ref"] == f"app_evidence_records:{created['evidence_id']}"
    assert first["receipt"]["sources"][0]["rights"] == entry["rights_state"]

    options = copy.deepcopy(ws["options"])
    options[1]["proposal"] = "Revised source-bounded review with a separate follow-up check."
    ws["options"] = options
    ws["current"] = adopt(
        ws, report, options, selection("B", "300"),
        request_id="approved-source-adopt-" + expected_domain,
    )
    second = save(
        ws,
        request_id="approved-source-revise-" + expected_domain,
        parent=first["artifact"]["artifact_id"],
        digest=first["document"]["draft_digest"],
    )["saved_work"]
    assert second["document"]["version"] == 2
    assert second["document"]["parent_artifact_id"] == first["artifact"]["artifact_id"]
    assert second["document"]["payload"]["business_work"]["decision"]["option_id"] == "B"
    assert second["document"]["payload"]["business_work"]["source_bindings"] == [first_binding]

    reopened_first = saved_work.reopen_work(
        first["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"],
    )
    reopened_second = saved_work.reopen_work(
        second["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"],
    )
    assert reopened_first["document"] == first["document"]
    assert reopened_second["document"] == second["document"]
    assert reopened_second["receipt"]["constraint_observations"]["source_authorization"] == "fresh-per-source"
    assert ws["service"].reopen(
        ws["current"]["work_id"], actor_ref=ws["actor_ref"],
        scope=ws["domain_scope"], authorize=ws["authorize"],
    )["is_current_revision"] is True

    citation_161 = {
        **citation,
        "end": 161,
        "quote": source["body"][:161],
    }
    before_artifacts = ws["repo"].query_one(
        "SELECT COUNT(*) FROM lumenis_shared_artifacts WHERE kind='saved_document' AND source_execution_id=?",
        (second["document"]["work_id"],),
    )[0]
    with pytest.raises(SavedWorkError, match="SOURCE_USE_QUOTE_LIMIT_EXCEEDED"):
        save(
            ws, request_id="approved-source-overlimit-" + expected_domain,
            citations=[citation_161], parent=second["artifact"]["artifact_id"],
            digest=second["document"]["draft_digest"],
        )
    after_artifacts = ws["repo"].query_one(
        "SELECT COUNT(*) FROM lumenis_shared_artifacts WHERE kind='saved_document' AND source_execution_id=?",
        (second["document"]["work_id"],),
    )[0]
    assert after_artifacts == before_artifacts == 2

    # A current-source rights change invalidates both the C3 save adapter and
    # Shared reopen; the original signed result remains stored and immutable.
    _revoke_current_source_rights(ws, source)
    if expected_domain == "zbmp":
        evidence_row = ws["repo"].query_one(
            "SELECT * FROM app_evidence_records WHERE id=?", (source["content_evidence_id"],),
        )
        assert store.classify_evidence_integrity(dict(evidence_row))["verified"] is True
    with pytest.raises(SavedWorkError, match="SOURCE_USE_RIGHTS_STATE_CHANGED"):
        _resolve(documents, ws, source)
    with pytest.raises(SavedWorkError, match="SOURCE_USE_RIGHTS_STATE_CHANGED"):
        saved_work.reopen_work(
            second["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"],
        )
    # The new derived analysis refuses a revoked content reference before
    # the later Shared citation fence; the owner-specific denial above remains.
    with pytest.raises(PermissionError, match="BUSINESS_WORK_ANALYSIS_SOURCE_USE_UNAVAILABLE:BUSINESS_BRIEF_SOURCE_CONTENT_EVIDENCE_UNAVAILABLE"):
        ws["service"].save_result_request(
            ws["current"]["work_id"], actor_ref=ws["actor_ref"],
            scope=ws["domain_scope"], authorize=ws["authorize"],
            expected_revision=ws["current"]["revision"],
            request_id="approved-source-revoked-save-" + expected_domain,
            citations=[citation], previous_artifact_id=second["artifact"]["artifact_id"],
            expected_draft_digest=second["document"]["draft_digest"],
        )

    assert receipt_loads
