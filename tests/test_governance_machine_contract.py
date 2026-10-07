from __future__ import annotations

import copy
import unittest

from scripts.audit_tools.verify_governance_machine_contract import (
    CONTRACT_PATH,
    load_json,
    path_requires_current,
    validate_approval_receipts,
    validate_contract,
    validate_model_routing,
    validate_publication_policy,
    validate_semantic_change_receipt,
)


class GovernanceMachineSemanticTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_json(CONTRACT_PATH)

    def test_current_machine_contract_and_structured_model_routing_validate(self) -> None:
        contract = validate_contract()
        self.assertEqual(contract["contract_version"], "1.1.0")
        validate_model_routing(contract)
        validate_approval_receipts(contract)

    def test_c1_through_c6_window_environment_semantics_are_structured(self) -> None:
        for number in range(1, 7):
            role = f"C{number}"
            row = self.contract["roles"][role]
            self.assertEqual(row["window"], f"W{number}")
            self.assertEqual(row["environment"], "Local Codex")
            self.assertTrue(row["responsibilities"])

    def test_published_state_is_not_live_dispatch(self) -> None:
        dispatch = self.contract["dispatch"]
        self.assertFalse(dispatch["published_state_is_live_scheduler"])
        self.assertFalse(dispatch["runtime_state_tracked"])
        self.assertTrue(dispatch["wait_resume_condition_is_binding"])
        self.assertTrue(dispatch["resume_after_condition_without_second_approval"])

    def test_execution_semantics_are_not_markdown_dependent(self) -> None:
        policy = self.contract["semantic_change_policy"]
        self.assertTrue(policy["machine_contract_is_semantic_source"])
        self.assertFalse(policy["markdown_only_change_may_change_machine_semantics"])
        self.assertTrue(policy["semantic_machine_change_requires_po_receipt"])

    def test_delivery_paths_require_current_by_machine_policy(self) -> None:
        publication = self.contract["publication_policy"]
        for path in (
            "app/lib/main.dart",
            "website/src/pages/index.astro",
            "lumenis/shared/database/migrations.py",
            "canonical_data.py",
            "tests/test_database.py",
            "00-GOVERNANCE/evidence/round-03/RESULT.md",
            "00-GOVERNANCE/LUMENIS-ROUND-03-CHARTER-CURRENT.md",
        ):
            with self.subTest(path=path):
                self.assertTrue(path_requires_current(path, publication))
                with self.assertRaisesRegex(AssertionError, "CURRENT co-publication"):
                    validate_publication_policy(self.contract, {path})

    def test_same_commit_current_closes_machine_publication_gate(self) -> None:
        publication = self.contract["publication_policy"]
        validate_publication_policy(
            self.contract,
            {
                "lumenis/shared/database/migrations.py",
                publication["current_status_path"],
            },
        )

    def test_historical_doc_alone_does_not_require_current(self) -> None:
        publication = self.contract["publication_policy"]
        path = "docs/archive/old-note.md"
        self.assertFalse(path_requires_current(path, publication))
        validate_publication_policy(self.contract, {path})

    def test_semantic_machine_change_requires_same_commit_approval_receipt(self) -> None:
        machine_path = self.contract["semantic_change_policy"]["semantic_machine_paths"][0]
        with self.assertRaisesRegex(AssertionError, "PO approval receipt"):
            validate_semantic_change_receipt(self.contract, {machine_path})

        receipt_path = (
            self.contract["approval"]["receipt_directory"].rstrip("/")
            + "/PO-TEST.json"
        )
        validate_semantic_change_receipt(self.contract, {machine_path, receipt_path})

    def test_model_routing_semantics_are_read_from_structured_toml(self) -> None:
        validate_model_routing(self.contract)
        changed = copy.deepcopy(self.contract)
        changed["model_routing"]["role_defaults"]["C2"]["model"] = "invalid-model"
        with self.assertRaisesRegex(AssertionError, "C2"):
            validate_model_routing(changed)


if __name__ == "__main__":
    unittest.main()
