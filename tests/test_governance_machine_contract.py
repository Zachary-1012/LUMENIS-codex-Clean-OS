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
        self.assertEqual(contract["contract_version"], "1.3.0")
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


class ConstitutionTestAuthorizationTests(unittest.TestCase):
    """Run the real validator against an isolated copy of its declared inputs."""

    def _check(self, allowed):
        import json
        from pathlib import Path
        import shutil
        import subprocess
        import sys
        import tempfile
        root = CONTRACT_PATH.parents[1]
        paths = [
            "AGENTS.md", "README.md",
            "00-GOVERNANCE/AI-NATIVE-PRODUCT-CONSTITUTION.md",
            "00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md",
            "00-GOVERNANCE/LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json",
            ".github/workflows/platform-verify.yml", ".github/workflows/app-verify.yml",
            "tests/test_report_audit.py", "tests/CI_TEST_TIERS.md",
            "scripts/audit_tools/verify_ai_native_constitution.py",
        ]
        with tempfile.TemporaryDirectory(prefix="lumenis-policy-regression-") as directory:
            target = Path(directory)
            for relative in paths:
                dest = target / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root / relative, dest)
            machine_path = target / "00-GOVERNANCE/LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json"
            machine = json.loads(machine_path.read_text(encoding="utf-8"))
            machine["verification_policy"]["run_unit_integration_allowed"] = allowed
            machine_path.write_text(json.dumps(machine), encoding="utf-8")
            workflow = target / ".github/workflows/platform-verify.yml"
            with workflow.open("a", encoding="utf-8") as out:
                out.write("\n      - name: isolated test command fixture\n        run: python -m pytest tests/example.py\n")
            return subprocess.run(
                [sys.executable, "-I", "-X", "utf8", str(target / paths[-1])],
                cwd=target, capture_output=True, text=True, encoding="utf-8", timeout=20,
            )

    def test_restored_authorization_allows_explicit_unit_command(self):
        result = self._check(True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_explicitly_revoked_authorization_blocks_unit_command(self):
        result = self._check(False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("suite execution violates", result.stdout)

    def test_malformed_machine_authorization_is_not_treated_as_grant(self):
        result = self._check("true")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing or invalid machine contract", result.stdout)


if __name__ == "__main__":
    unittest.main()
