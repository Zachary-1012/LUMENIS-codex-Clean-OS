"""Actual signed source/event association, distinct from modeled attribution."""

import json
import pytest
from tests.test_saved_document_workflow import workspace
from tests.test_entity_profile_lifecycle import _register


def test_author_event_association_uses_explicit_mentions_and_excludes_foreign_scope(
    workspace, monkeypatch
):
    import database
    import kos_engine
    import subject_registry
    import kos_attribution
    from canonical_data import CanonicalRecord, persist_canonical
    from lumenis.shared.evidence import store

    ws = workspace
    scope = _register(ws)
    monkeypatch.setattr(database, "get_repository", lambda: ws["repo"])
    monkeypatch.setattr(kos_engine, "get_repository", lambda: ws["repo"])
    database.init_db()
    with ws["repo"].transaction() as con:
        from lumenis.shared.database.business_schema import (
            ensure_business_scope_storage,
        )

        ensure_business_scope_storage(con)
        database.insert_note(
            {
                "note_id": "owned-source",
                "author_id": "source-author",
                "author_nickname": "Synthetic source author",
                "title": "Reported event",
                "content": "An attributed source statement.",
                "source_platform": "x",
                "publish_date": "2026-10-17",
                "likes": 0,
                "comments": 0,
                "collects": 0,
                "shares": 0,
            },
            connection=con,
        )
        evidence_id = store.record_evidence(
            connection=con,
            source="public_http",
            project="LUMENIS",
            product="ZBMP",
            domain_id="zbmp",
            brand_focus_id=scope["brand_focus_id"],
            feature_id="ASSOCIATION_ENGINEERING",
            test_name="synthetic_source",
            result="PASS",
            status="verified",
            inputs={"source_ids": ["owned-source"]},
            outputs={"scope_admitted": True},
        )
        con.execute(
            "UPDATE notes SET subject_id=NULL,brand_focus_id=?,scope_status='VERIFIED',scope_evidence_ref=? WHERE note_id='owned-source'",
            (scope["brand_focus_id"], str(evidence_id)),
        )
        persist_canonical(
            con,
            CanonicalRecord(
                canonical_id="association-canonical",
                product_id="ZBMP",
                domain_id="zbmp",
                brand_focus_id=scope["brand_focus_id"],
                scope_status="VERIFIED",
                scope_evidence_ref=str(evidence_id),
                source_id="owned-source",
                external_id="owned-source",
                source_type="note",
                source_table="notes",
                source_platform="x",
                author_id="source-author",
                author_name="Synthetic source author",
                title="Reported event",
                content="An attributed source statement.",
                captured_at="2026-10-17T00:00:00Z",
                publish_datetime="2026-10-17",
                raw_ref=json.dumps({"table": "notes", "note_id": "owned-source"}),
            ),
        )
    event_id = database.upsert_event(
        {
            "event_key": database._event_scope_token({**scope, "product_id": "ZBMP"})
            + ".source-associated-event",
            "title": "Reported event",
            "event_date": "2026-10-17",
            "first_seen": "2026-10-17",
            "last_seen": "2026-10-17",
            "risk_level": "low",
            "status": "active",
        },
        scope=scope,
        mentions=[{"source_type": "note", "source_id": "owned-source"}],
    )
    result = kos_attribution.calculate_attribution(
        "source-author", "Synthetic profile entity", scope=scope, actor=ws["actor"]
    )
    assert result["association_state"] == "SOURCE_LINKED"
    assert result["event_associations"][0]["event_id"] == event_id
    assert (
        result["event_associations"][0]["linked_sources"][0]["source_id"]
        == "owned-source"
    )
    assert result["model_attribution"] == "NOT_RUN"
    assert result["verified_conversion"] == "NOT_ESTABLISHED"
    unknown = kos_attribution.calculate_attribution(
        "other-author", "Synthetic profile entity", scope=scope, actor=ws["actor"]
    )
    assert unknown["event_associations"] == []
    foreign, _ = subject_registry.add_subject(
        {
            "domain_id": "BMP",
            "subject_type": "brand",
            "name_en": "Other association brand",
            "name_zh": "另一关联品牌",
        }
    )
    other_scope = {**scope, "brand_focus_id": foreign["brand_focus_id"]}
    other = kos_attribution.calculate_attribution(
        "source-author", "Other association brand", scope=other_scope, actor=ws["actor"]
    )
    assert other["event_associations"] == [] and other["observed_source_count"] == 0
    with ws["repo"].transaction() as con:
        con.execute(
            "UPDATE notes SET scope_evidence_ref='invalid' WHERE note_id='owned-source'"
        )
    revoked = kos_attribution.calculate_attribution(
        "source-author", "Synthetic profile entity", scope=scope, actor=ws["actor"]
    )
    assert revoked["event_associations"] == [] and revoked["event_rejected_count"] == 1
