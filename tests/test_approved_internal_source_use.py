"""Focused guardrails for the receipt-bound source-reference admission."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask

import experience_runtime
from lumenis.importer.documents import _approved_source_use_entry
from lumenis.system.security.permission import (
    SourceUseApprovalError,
    _load_source_use_receipt,
    _source_use_authenticated_scope_matches,
    _source_use_current_evidence,
    _source_use_rights_state,
    validate_current_source_use,
)

RECEIPT_ID = "PO-20261011-APPROVED-INTERNAL-SOURCE-USE"


class ApprovedInternalSourceUseTests(unittest.TestCase):
    _TEST_EVIDENCE_KEY_ID = "source-use-regression"
    _TEST_EVIDENCE_KEY = b"isolated-source-use-regression-key"

    @classmethod
    def _test_evidence_key_environment(cls):
        return {
            "LUMENIS_EVIDENCE_HMAC_KEY_RING": json.dumps({
                cls._TEST_EVIDENCE_KEY_ID: cls._TEST_EVIDENCE_KEY.decode("ascii"),
            }),
            "LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID": cls._TEST_EVIDENCE_KEY_ID,
        }

    @classmethod
    def _signed_evidence_record(cls, record_id, *, domain_id, product_id, inputs):
        from lumenis.shared.evidence import store as evidence_store

        record = {name: None for name in evidence_store._EVIDENCE_V2_MATERIAL_FIELDS}
        record.update({
            "id": record_id,
            "source": "test",
            "product": product_id,
            "asset_id": "test-source",
            "result": "PASS",
            "status": "verified",
            "inputs_json": json.dumps(inputs, sort_keys=True, separators=(",", ":")),
            "collection_metadata": "{}",
            "domain_id": domain_id,
            "product_id": product_id,
            "integrity_version": evidence_store.EVIDENCE_INTEGRITY_VERSION,
            "integrity_algorithm": evidence_store.EVIDENCE_INTEGRITY_ALGORITHM,
            "integrity_key_id": cls._TEST_EVIDENCE_KEY_ID,
            "integrity_digest": "",
        })
        record["integrity_digest"] = hmac.new(
            cls._TEST_EVIDENCE_KEY, evidence_store._integrity_payload(record), hashlib.sha256,
        ).hexdigest()
        return record

    @staticmethod
    def _read_authenticated_evidence(record):
        columns = tuple(record)
        quoted_columns = ", ".join(f'"{column}"' for column in columns)
        placeholders = ", ".join("?" for _ in columns)
        connection = sqlite3.connect(":memory:")
        try:
            connection.execute(f"CREATE TABLE app_evidence_records ({quoted_columns})")
            connection.execute(
                f"INSERT INTO app_evidence_records ({quoted_columns}) VALUES ({placeholders})",
                tuple(record.values()),
            )
            return _source_use_current_evidence(
                connection, f"app_evidence_records:{record['id']}",
            )
        finally:
            connection.close()

    def test_receipt_is_machine_shaped_and_contains_only_the_two_exact_sources(self):
        receipt = _load_source_use_receipt(RECEIPT_ID)
        self.assertEqual(receipt["approval_id"], RECEIPT_ID)
        self.assertEqual(receipt["approval_source_type"], "direct_product_owner_instruction")
        self.assertEqual(receipt["approved_by"], "Product Owner")
        self.assertTrue(receipt["constraints"])
        self.assertTrue(receipt["scope_manifest"])
        by_source = {item["source_id"]: item for item in receipt["sources"]}
        self.assertEqual(set(by_source), {
            "public-http:f23bf6b5247f75b692bfbe317ebb37af",
            "2108916710510088619",
        })
        taikoo = by_source["public-http:f23bf6b5247f75b692bfbe317ebb37af"]
        nike = by_source["2108916710510088619"]
        self.assertEqual(taikoo["content_evidence_ref"], "notes:109")
        self.assertEqual(taikoo["snapshot_kind"], "existing_canonical_content_snapshot_not_native_capture")
        self.assertEqual(nike["scope_evidence_ref"], "app_evidence_records:7915")
        self.assertEqual(nike["content_evidence_ref"], "app_evidence_records:7916")
        self.assertEqual(nike["rights_state"], "UNREVIEWED")
        self.assertEqual(taikoo["rights_state"], "UNKNOWN")
        self.assertEqual(set(taikoo["allowed_purposes"]), {"internal_research", "short_quote", "cth_brief"})
        self.assertEqual(set(nike["allowed_purposes"]), {"internal_research", "short_quote", "bmp_brief"})
        for item in by_source.values():
            self.assertEqual(item["allowed_operations"], ["derive_reference", "read", "save", "revise", "reopen"])
            self.assertEqual(item["commercial_state"], "UNKNOWN")
            self.assertEqual(item["publication_state"], "NOT_APPROVED")
            self.assertEqual(item["training_state"], "NOT_APPROVED")

    def test_source_lookup_fails_closed_for_unlisted_source(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_USE_SOURCE_NOT_APPROVED"):
            _approved_source_use_entry("unlisted-source")

    def test_rights_state_is_preserved_and_positive_or_restricted_rights_are_not_inferred(self):
        self.assertEqual(_source_use_rights_state(None), "UNKNOWN")
        self.assertEqual(_source_use_rights_state("UNKNOWN"), "UNKNOWN")
        self.assertEqual(_source_use_rights_state("UNREVIEWED"), "UNREVIEWED")
        with self.assertRaisesRegex(SourceUseApprovalError, "SOURCE_USE_RIGHTS_STATE_CHANGED"):
            _source_use_rights_state("APPROVED")
        with self.assertRaisesRegex(SourceUseApprovalError, "SOURCE_USE_SOURCE_RESTRICTED"):
            _source_use_rights_state({"private": True})

    def test_current_use_rejects_noncanonical_connection_before_considering_grant(self):
        with self.assertRaisesRegex(SourceUseApprovalError, "SOURCE_USE_SCOPE_CONNECTION_INVALID"):
            validate_current_source_use(
                object(),
                source_id="2108916710510088619",
                source_url="https://x.com/nikestore/status/2108916710510088619",
                domain_id="zbmp", subject_id=None,
                brand_focus_id="BRAND-8b9f5ffaeea603d31bf0d7e8",
                scope_evidence_ref="app_evidence_records:7915",
                content_evidence_ref="app_evidence_records:7916",
                body_sha256="208f0de7dae51afaed9e66adbbad583c2a81d723af6902ac39f0a44c42779a08",
                purpose="bmp_brief", operation="save", receipt_id=RECEIPT_ID,
            )

    def test_authenticated_scope_marker_accepts_normal_cth_and_bmp_focus_rows(self):
        from lumenis.shared.evidence import store as evidence_store

        cases = (
            ("cth", "CTH", "SUBJ-89269ecd7273fb3c4b6d3fbe", None),
            ("zbmp", "ZBMP", None, "BRAND-8b9f5ffaeea603d31bf0d7e8"),
        )
        with patch.dict(os.environ, self._test_evidence_key_environment()):
            for index, (domain_id, product_id, subject_id, brand_focus_id) in enumerate(cases, 1):
                with self.subTest(domain_id=domain_id):
                    scope = evidence_store._normalize_record_evidence_scope(
                        product=product_id, domain_id=domain_id, subject_id=subject_id,
                        brand_focus_id=brand_focus_id, global_scope=False,
                    )
                    record = self._signed_evidence_record(
                        index, domain_id=domain_id, product_id=product_id,
                        inputs={"_lumenis_scope": scope},
                    )
                    authenticated = self._read_authenticated_evidence(record)
                    self.assertTrue(_source_use_authenticated_scope_matches(
                        authenticated, domain_id=domain_id, subject_id=subject_id,
                        brand_focus_id=brand_focus_id,
                    ))

    def test_authenticated_scope_marker_rejects_missing_mismatch_and_tampering(self):
        from lumenis.shared.evidence import store as evidence_store

        domain_id = "zbmp"
        product_id = "ZBMP"
        brand_focus_id = "BRAND-8b9f5ffaeea603d31bf0d7e8"
        expected = evidence_store._normalize_record_evidence_scope(
            product=product_id, domain_id=domain_id, subject_id=None,
            brand_focus_id=brand_focus_id, global_scope=False,
        )
        mismatched = evidence_store._normalize_record_evidence_scope(
            product=product_id, domain_id=domain_id, subject_id=None,
            brand_focus_id="BRAND-OTHER", global_scope=False,
        )
        with patch.dict(os.environ, self._test_evidence_key_environment()):
            for record_id, inputs in (
                (1, {"source": "test-source"}),
                (2, {"_lumenis_scope": mismatched}),
            ):
                with self.subTest(record_id=record_id):
                    authenticated = self._read_authenticated_evidence(self._signed_evidence_record(
                        record_id, domain_id=domain_id, product_id=product_id, inputs=inputs,
                    ))
                    self.assertFalse(_source_use_authenticated_scope_matches(
                        authenticated, domain_id=domain_id, subject_id=None,
                        brand_focus_id=brand_focus_id,
                    ))

            record = self._signed_evidence_record(
                3, domain_id=domain_id, product_id=product_id,
                inputs={"_lumenis_scope": expected},
            )
            altered_inputs = json.dumps({"_lumenis_scope": mismatched}, sort_keys=True, separators=(",", ":"))
            columns = tuple(record)
            quoted_columns = ", ".join(f'"{column}"' for column in columns)
            placeholders = ", ".join("?" for _ in columns)
            connection = sqlite3.connect(":memory:")
            try:
                connection.execute(f"CREATE TABLE app_evidence_records ({quoted_columns})")
                connection.execute(
                    f"INSERT INTO app_evidence_records ({quoted_columns}) VALUES ({placeholders})",
                    tuple(record.values()),
                )
                connection.execute(
                    "UPDATE app_evidence_records SET inputs_json=? WHERE id=?",
                    (altered_inputs, record["id"]),
                )
                with self.assertRaisesRegex(SourceUseApprovalError, "SOURCE_USE_SOURCE_EVIDENCE_INVALID"):
                    _source_use_current_evidence(connection, f"app_evidence_records:{record['id']}")
            finally:
                connection.close()

    def test_route_derives_actor_and_scope_server_side_and_rejects_extra_fields(self):
        app = Flask(__name__)
        scope = {"domain_id": "cth", "subject_id": "SUBJ-89269ecd7273fb3c4b6d3fbe",
                 "brand_focus_id": None, "global_scope": False}
        actor = object()
        payload = {
            "source_id": "public-http:f23bf6b5247f75b692bfbe317ebb37af",
            "canonical_id": "can_note_public-http:f23bf6b5247f75b692bfbe317ebb37af",
            "expected_body_sha256": "14df1c3f1713dddfa3ab19f9daaa2af54570658dade44e77959b236f86d69ec6",
            "request_id": "source-ref-cth-01",
        }
        prepared = {
            "prepared": True,
            "resource": "approved-internal-source-reference:v2:" + "a" * 64,
        }
        with (
            app.test_request_context("/api/experience/materials/source-references", method="POST", json=payload),
            patch.object(experience_runtime, "_shared_work_actor_scope", return_value=(actor, scope)) as actor_scope,
            patch("lumenis.importer.documents.prepare_approved_source_reference",
                  return_value=prepared) as prepare,
            patch("lumenis.system.security.permission.check_approved_source_reference_import",
                  return_value=SimpleNamespace(allowed=True, requires_approval=False)) as check,
            patch("lumenis.system.security.permission.prepare_approved_source_reference_confirmation",
                  side_effect=AssertionError("allowed import must not prepare confirmation")) as confirmation,
            patch("lumenis.importer.documents.create_approved_source_reference",
                  return_value={"ok": True, "source_id": payload["source_id"]}) as create,
        ):
            response = experience_runtime.import_approved_source_reference()
            self.assertEqual(response.status_code, 200)
            actor_scope.assert_called_once_with("write")
            prepare.assert_called_once_with(actor=actor, scope=scope, **payload)
            check.assert_called_once_with(actor=actor, scope=scope, prepared=prepared)
            confirmation.assert_not_called()
            args, kwargs = create.call_args
            self.assertEqual(args, ())
            self.assertIs(kwargs.pop("actor"), actor)
            self.assertEqual(kwargs.pop("scope"), scope)
            self.assertEqual(kwargs, payload)

        bad_payload = {**payload, "actor_id": "client-controlled"}
        with (
            app.test_request_context("/api/experience/materials/source-references", method="POST", json=bad_payload),
            patch.object(experience_runtime, "_shared_work_actor_scope") as actor_scope,
        ):
            response = experience_runtime.import_approved_source_reference()
            if isinstance(response, tuple):
                response, status = response
            else:
                status = response.status_code
            self.assertEqual(status, 400)
            body = json.loads(response.get_data(as_text=True))
            self.assertEqual(body["code"], "SOURCE_USE_REQUEST_INVALID")
            actor_scope.assert_not_called()

    def test_source_reference_attachment_requires_export_use(self):
        app = Flask(__name__)
        actor, scope = object(), {"domain_id": "zbmp", "brand_focus_id": "BRAND-test"}
        with (
            app.test_request_context("/api/experience/materials/documents/7916/file"),
            patch.object(experience_runtime, "_shared_work_actor_scope", return_value=(actor, scope)),
            patch("lumenis.importer.documents.reopen_imported_source", side_effect=SourceUseApprovalError(
                "SOURCE_USE_PURPOSE_NOT_ALLOWED")) as reopen,
        ):
            response, status = experience_runtime.download_shared_document(7916)
            self.assertGreaterEqual(status, 400)
            self.assertEqual(json.loads(response.get_data(as_text=True))["code"], "SOURCE_USE_PURPOSE_NOT_ALLOWED")
            reopen.assert_called_once_with(7916, actor=actor, scope=scope, _source_use_operation="export")

    def test_ordinary_approved_file_attachment_keeps_owner_result(self):
        app = Flask(__name__)
        actor, scope = object(), {"domain_id": "cth", "subject_id": "SUBJ-test"}
        result = {"content": b"owner-approved-file", "filename": "author.txt",
                  "artifact_ref": "existing-owner-artifact", "sha256": "a" * 64}
        with (
            app.test_request_context("/api/experience/materials/documents/23/file"),
            patch.object(experience_runtime, "_shared_work_actor_scope", return_value=(actor, scope)),
            patch("lumenis.importer.documents.reopen_imported_source", return_value=result) as reopen,
        ):
            response = experience_runtime.download_shared_document(23)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b"".join(response.response), result["content"])
            self.assertEqual(response.headers["X-Source-Artifact-ID"], result["artifact_ref"])
            self.assertEqual(response.headers["X-Content-SHA256"], result["sha256"])
            reopen.assert_called_once_with(23, actor=actor, scope=scope, _source_use_operation="export")


if __name__ == "__main__":
    unittest.main()
