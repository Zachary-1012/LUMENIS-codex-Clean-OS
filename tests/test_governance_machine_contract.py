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
        branch = contract["branch_policy"]
        self.assertTrue(branch["platform_branch_protection_required_now"])
        self.assertEqual(branch["harden_at"], "EXPLICIT_PO_APPROVAL")
        from unittest.mock import patch
        from pathlib import Path
        from scripts.audit_tools import verify_governance_machine_contract as validator
        for field, bad in (("platform_branch_protection_required_now", False),
                           ("harden_at", "INTERNAL_BETA_ENTRY")):
            altered = copy.deepcopy(contract)
            altered["branch_policy"][field] = bad
            with patch.object(validator, "load_json", side_effect=lambda path:
                    altered if Path(path) == CONTRACT_PATH else load_json(path)):
                with self.assertRaisesRegex(AssertionError, "branch protection|hardening trigger"):
                    validate_contract()
        receipt_path = validator.ROOT / branch["approval_receipt"]
        original_receipt = load_json(receipt_path)
        missing_amendment = {key: value for key, value in original_receipt.items() if key != "amendments"}
        with patch.object(validator, "load_json", side_effect=lambda path:
                missing_amendment if Path(path) == receipt_path else load_json(path)):
            with self.assertRaisesRegex(AssertionError, "dated PO amendment"):
                validate_contract()
        from scripts.audit_tools.verify_codex_takeover_governance import (
            _assert_current_publication_truth, _is_rules_only_publication_path,
        )
        self.assertTrue(_is_rules_only_publication_path("tests/test_governance_machine_contract.py"))
        snapshot = ("## 1. Online reader's current-state snapshot\n"
                    "Implementation publication state: `RULES_ONLY_PUBLICATION`\n"
                    "Runtime load state: `NOT_LOADED_OR_NOT_VERIFIED`\n")
        policy_paths = {"00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md",
                        "tests/test_governance_machine_contract.py",
                        "scripts/audit_tools/verify_governance_machine_contract.py"}
        _assert_current_publication_truth(snapshot, changed_paths=policy_paths)
        for forbidden in ("tests/test_unrelated_business.py", "app.py", "lumenis/runtime.py"):
            self.assertFalse(_is_rules_only_publication_path(forbidden))
            with self.assertRaisesRegex(AssertionError, "governance/documentation paths only"):
                _assert_current_publication_truth(snapshot, changed_paths=policy_paths | {forbidden})

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


class PublicationMergeDiffTests(unittest.TestCase):
    """Exercise actual divergent Git merges, not fabricated changed-path lists."""

    def _exercise(self, include_current):
        from pathlib import Path
        import subprocess
        import tempfile
        from unittest.mock import patch
        import scripts.audit_tools.verify_governance_machine_contract as machine
        import scripts.audit_tools.verify_codex_takeover_governance as takeover
        current = "00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md"
        with tempfile.TemporaryDirectory(prefix="lumenis-merge-regression-") as folder:
            root = Path(folder)
            def git(*args):
                result = subprocess.run(["git", "-C", str(root), *args],
                    capture_output=True, text=True, encoding="utf-8", timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
                return result.stdout
            git("init", "-q", "--initial-branch=main")
            git("config", "user.name", "Isolated merge regression")
            git("config", "user.email", "test@example.invalid")
            git("config", "commit.gpgsign", "false")
            (root/"seed.txt").write_text("base", encoding="utf-8")
            git("add", "seed.txt")
            git("commit", "-qm", "initial")
            git("switch", "-qc", "repair")
            (root/"business.py").write_text("value = 1\n", encoding="utf-8")
            git("add", "business.py")
            if include_current:
                (root/current).parent.mkdir(parents=True, exist_ok=True)
                (root/current).write_text("current evidence", encoding="utf-8")
                git("add", current)
            git("commit", "-qm", "repair")
            git("switch", "-q", "main")
            (root/"unrelated.txt").write_text("main-only", encoding="utf-8")
            git("add", "unrelated.txt")
            git("commit", "-qm", "main advances independently")
            git("merge", "--no-ff", "-qm", "reviewed merge", "repair")
            with patch.object(machine, "ROOT", root), patch.object(takeover, "ROOT", root):
                paths = machine.changed_paths()
                self.assertEqual(paths, takeover._publication_changed_paths())
            expected = {"business.py", current} if include_current else {"business.py"}
            self.assertEqual(paths, expected)
            return paths

    def test_complete_merge_is_checked_against_first_parent(self):
        paths = self._exercise(True)
        validate_publication_policy(load_json(CONTRACT_PATH), paths)

    def test_merge_without_current_is_still_rejected(self):
        paths = self._exercise(False)
        with self.assertRaisesRegex(AssertionError, "CURRENT co-publication"):
            validate_publication_policy(load_json(CONTRACT_PATH), paths)


if __name__ == "__main__":
    unittest.main()
