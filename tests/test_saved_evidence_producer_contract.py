"""SavedWork must not upgrade a re-signed generic row to an Importer source.

These tests deliberately use the isolated test signing owner. They model an
incorrect trusted producer, not possession of a production signing credential.
"""
from __future__ import annotations

import pytest

from tests.test_saved_document_workflow import workspace, _source, _save


@pytest.mark.parametrize("field,value", [
    ("source", "generic_manual_evidence"),
    ("feature_id", "UNRELATED_FEATURE"),
    ("provider", "generic_writer"),
    ("version", "document-import/999"),
])
def test_resigned_wrong_producer_cannot_save_or_reopen(workspace, field, value):
    from lumenis.shared.evidence import store

    _, _, source = _source(workspace)
    citation = workspace["documents"].locate_quote(
        source["evidence_id"], actor=workspace["actor"],
        scope=workspace["scope"], start=0, end=20,
    )["citation"]
    saved = _save(workspace, citations=[citation])
    with workspace["repo"].transaction() as con:
        # The field names come only from the fixed parametrization above.
        con.execute(f"UPDATE app_evidence_records SET {field}=? WHERE id=?",
                    (value, source["evidence_id"]))
        store._sign_evidence_record(con, source["evidence_id"])
        cursor = con.execute("SELECT * FROM app_evidence_records WHERE id=?",
                             (source["evidence_id"],))
        row = dict(zip((column[0] for column in cursor.description), cursor.fetchone()))
        assert store.classify_evidence_integrity(row)["verified"] is True

    with pytest.raises(ValueError, match="DOCUMENT_SOURCE_PRODUCER_INVALID"):
        _save(workspace, request_id="wrong-producer-save", citations=[citation])
    with pytest.raises(ValueError, match="DOCUMENT_SOURCE_PRODUCER_INVALID"):
        workspace["work"].reopen_work(
            saved["artifact"]["artifact_id"], actor=workspace["actor"],
            scope=workspace["scope"],
        )
