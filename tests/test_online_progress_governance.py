from __future__ import annotations

import unittest

from scripts.audit_tools.verify_codex_takeover_governance import (
    ONLINE_STATUS_PATH,
    _assert_online_progress_for_paths,
    _requires_online_progress,
)


class OnlineProgressGovernanceTests(unittest.TestCase):
    def test_product_and_round_changes_require_progress(self) -> None:
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
                self.assertTrue(_requires_online_progress(path))
                with self.assertRaisesRegex(AssertionError, "CURRENT online progress"):
                    _assert_online_progress_for_paths({path})

    def test_same_commit_progress_closes_the_gate(self) -> None:
        _assert_online_progress_for_paths(
            {"lumenis/shared/database/migrations.py", ONLINE_STATUS_PATH}
        )

    def test_historical_document_alone_does_not_claim_a_batch(self) -> None:
        self.assertFalse(_requires_online_progress("docs/archive/old-note.md"))
        _assert_online_progress_for_paths({"docs/archive/old-note.md"})


if __name__ == "__main__":
    unittest.main()
