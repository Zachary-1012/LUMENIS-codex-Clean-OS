"""FIX-026: bound scoped legacy-note source scans and report incompleteness."""
import json
import unittest
from unittest.mock import patch


class DataQuerySourceLimitTests(unittest.TestCase):
    def setUp(self):
        import data_query_api

        self.api = data_query_api
        self.scope = {"product_id": "CTH", "domain_id": "cth", "subject_id": None}
        self.source_ids = [f"note-{index}" for index in range(5)]
        self.candidate_calls = []
        self.signed_batches = []

        def canonical_row(source_id):
            return {
                "canonical_id": f"canonical-{source_id}",
                "product_id": "CTH",
                "domain_id": "cth",
                "subject_id": None,
                "scope_status": "VERIFIED",
                "scope_evidence_ref": "evidence-test",
                "source_id": source_id,
                "external_id": source_id,
                "source_type": "note",
                "source_table": "notes",
                "captured_at": "2026-10-20T00:00:00",
                "raw_ref": json.dumps({"table": "notes", "note_id": source_id}),
            }

        def read_canonical(*, source_ids=None, **_kwargs):
            if source_ids is None:
                return {
                    "scope": self.scope,
                    "canonical": {"page": {
                        "candidate_source_count": len(self.source_ids),
                    }},
                    "permission_audit_id": "audit-test",
                }
            self.signed_batches.append(list(source_ids))
            return {
                "scope": self.scope,
                "canonical": {
                    "records": [canonical_row(source_id) for source_id in source_ids],
                    "rejected_count": 0,
                },
                "permission_audit_id": "audit-test",
            }

        def candidate_page(_scope, _filters=None, *, limit=100, offset=0):
            self.candidate_calls.append((limit, offset))
            return self.source_ids[offset:offset + limit]

        self._patch(data_query_api, "_read_cth_canonical_page", read_canonical)
        self._patch(data_query_api.db, "get_canonical_note_projection_count",
                    lambda *_args, **_kwargs: len(self.source_ids))
        self._patch(data_query_api.db, "get_canonical_note_projection_candidate_page",
                    candidate_page)
        self._patch(
            data_query_api.db, "get_notes_for_canonical_source_ids",
            lambda ids, *_args, **_kwargs: [{"note_id": source_id} for source_id in ids],
        )

    def _patch(self, target, name, value):
        patcher = patch.object(target, name, value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_limit_marks_partial_and_leaves_total_unknown(self):
        result = self.api.read_scoped_legacy_note_rows(
            module="content", limit=5, scan_all=True, max_sources=2,
        )

        self.assertEqual(self.candidate_calls, [(2, 0)])
        self.assertEqual(self.signed_batches, [self.source_ids[:2]])
        self.assertEqual([note["note_id"] for note in result["notes"]], self.source_ids[:2])
        self.assertEqual(result["candidate_count"], len(self.source_ids))
        self.assertEqual(result["verified_source_count"], 2)
        self.assertFalse(result["verified_source_count_complete"])
        self.assertTrue(result["truncated"])
        self.assertEqual(result["data_state"], "PARTIAL")
        self.assertIsNone(result["total"])

    def test_complete_scan_succeeds_when_limit_covers_scope(self):
        result = self.api.read_scoped_legacy_note_rows(
            module="content", limit=5, require_complete=True,
            scan_all=True, max_sources=len(self.source_ids),
        )

        self.assertEqual(self.candidate_calls, [(len(self.source_ids), 0)])
        self.assertEqual(self.signed_batches, [self.source_ids])
        self.assertEqual(len(result["notes"]), len(self.source_ids))
        self.assertTrue(result["verified_source_count_complete"])
        self.assertFalse(result["truncated"])
        self.assertEqual(result["data_state"], "READY")
        self.assertEqual(result["total"], len(self.source_ids))

    def test_require_complete_fails_when_limit_hides_sources(self):
        with self.assertRaises(self.api.LegacyScopeReadError) as raised:
            self.api.read_scoped_legacy_note_rows(
                module="content", limit=5, require_complete=True,
                scan_all=True, max_sources=2,
            )

        self.assertEqual(raised.exception.code, "CTH_CANONICAL_SCAN_INCOMPLETE")
        self.assertEqual(self.candidate_calls, [(2, 0)])
        self.assertEqual(self.signed_batches, [self.source_ids[:2]])

    def test_invalid_limits_are_rejected_before_source_reads(self):
        for invalid_limit in (0, -1, True, 1.5):
            with self.subTest(max_sources=invalid_limit):
                with self.assertRaises(self.api.LegacyScopeReadError) as raised:
                    self.api.read_scoped_legacy_note_rows(max_sources=invalid_limit)
                self.assertEqual(raised.exception.code, "INVALID_CTH_SOURCE_SCAN_LIMIT")
        self.assertEqual(self.candidate_calls, [])
        self.assertEqual(self.signed_batches, [])


if __name__ == "__main__":
    unittest.main()
