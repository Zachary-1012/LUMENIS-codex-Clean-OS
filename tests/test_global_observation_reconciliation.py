"""GLOBAL unchanged collection preserves current lineage and Canonical annotations."""
from __future__ import annotations

import sqlite3

import pytest

from tests.test_collector_transaction_truth import collector_case


@pytest.mark.parametrize(
    ("domain_header", "product_id", "stored_domain"),
    [("CTH", "CTH", "cth"), ("BMP", "ZBMP", "zbmp")],
)
def test_global_unchanged_capture_reconciles_canonical_without_scope_or_history(
    collector_case, domain_header, product_id, stored_domain,
):
    from tests import test_collector_transaction_truth as collector_truth

    case = collector_case
    headers = {
        **collector_truth.GLOBAL_MODE,
        "X-Domain-Id": domain_header,
        "X-Product-Id": product_id,
    }
    first = collector_truth._approve_and_collect_once(
        case, headers=headers,
    )
    initial = collector_truth._global_snapshot(case)
    note = initial["note"]
    canonical = initial["canonical"]
    assert note is not None and canonical is not None
    assert note["product_id"] == canonical["product_id"] == product_id
    assert note["domain_id"] == canonical["domain_id"] == stored_domain
    source_id = note["note_id"]
    evidence_ref = str(first["evidence_ref"])
    original_publish_time = note["publish_datetime"]
    original_canonical_capture = canonical["captured_at"]
    original_canonical_publish = canonical["publish_datetime"]
    original_scope = (
        note["scope_status"], note["scope_evidence_ref"], note["subject_id"],
        note["brand_focus_id"],
    )
    original_canonical_scope = (
        canonical['scope_status'], canonical['scope_evidence_ref'],
        canonical['subject_id'], canonical['brand_focus_id'],
    )
    assert str(canonical["evidence_ref"]) == evidence_ref
    assert original_scope[0] == "UNASSIGNED"
    assert original_scope[1] in (None, "")
    assert original_scope[2] in (None, "")
    assert original_scope[3] in (None, "")

    with sqlite3.connect(str(case["db_path"])) as connection:
        connection.execute(
            "UPDATE canonical_data SET evidence_ref='',engagement_likes=17,"
            "sentiment='negative',ai_analysis='reviewed GLOBAL source analysis' "
            "WHERE source_id=? AND product_id=?", (source_id, product_id),
        )
    counts_before = collector_truth._pipeline_counts(case["db_path"])
    history_before = collector_truth._global_snapshot(case)

    repeated = collector_truth._post(
        case, headers=headers,
    ).get_json()

    assert repeated["ok"] is True, repeated
    assert repeated["refresh_verified"] is True, repeated
    assert repeated["scope_status"] == "UNASSIGNED"
    assert repeated["canonical_synced"] == 1
    assert str(repeated["evidence_ref"]) == evidence_ref
    after = collector_truth._global_snapshot(case)
    assert collector_truth._pipeline_counts(case["db_path"]) == counts_before
    assert after["evidence"] == history_before["evidence"]
    assert after["metrics"] == history_before["metrics"]
    assert len(after["evidence"]) == len(after["metrics"]) == 1
    assert after["note"] is not None and after["canonical"] is not None
    assert after["note"]["note_id"] == after["canonical"]["source_id"] == source_id
    assert str(after["canonical"]["evidence_ref"]) == evidence_ref
    assert after["note"]["publish_datetime"] == original_publish_time
    assert after["canonical"]["publish_datetime"] == original_canonical_publish
    assert after["canonical"]["captured_at"] == original_canonical_capture
    assert after["canonical"]["sentiment"] == "negative"
    assert after["canonical"]["ai_analysis"] == "reviewed GLOBAL source analysis"
    assert after["canonical"]["engagement_likes"] is None
    final_scope = (
        after["note"]["scope_status"], after["note"]["scope_evidence_ref"],
        after["note"]["subject_id"], after["note"]["brand_focus_id"],
    )
    canonical_scope = (
        after["canonical"]["scope_status"],
        after["canonical"]["scope_evidence_ref"],
        after["canonical"]["subject_id"], after["canonical"]["brand_focus_id"],
    )
    # notes uses nullable selectors; the existing CanonicalRecord contract uses
    # empty strings. Preserve each original representation without inventing IDs.
    assert final_scope == original_scope
    assert canonical_scope == original_canonical_scope
    assert tuple(value or None for value in final_scope) == tuple(value or None for value in canonical_scope)
    assert isinstance(after["note"]["captured_at"], str)
    assert after["note"]["captured_at"]
