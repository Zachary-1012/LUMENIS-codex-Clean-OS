from __future__ import annotations

import unittest
from pathlib import Path

from scripts.audit_tools.verify_codex_takeover_governance import (
    ONLINE_STATUS_PATH,
    JOB_ASSERTIONS_HEADING,
    _assert_current_round_statuses,
    _assert_execution_boundaries,
    _assert_legacy_coverage_mapping,
    _assert_online_progress_for_paths,
    _assert_readme_routing_consistent,
    _assert_six_round_routing,
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


class SixRoundGovernanceTests(unittest.TestCase):
    def _agents_matrix(self) -> str:
        return "\n".join(
            (
                "Root AGENTS.md is the only repository execution router.",
                "| C1 / W1 | Local Codex | Data and Collection |",
                "| C2 / W2 | Local Codex | Owned AI and Agent |",
                "| C3 / W3 | Local Codex | CTH and BMP business workflows |",
                "| C4 / W4 | Local Codex | Original Pitch, Video, Podcast |",
                "| C5 / W5 | Local Codex | Importer, Research, Reporting, Artifact and notifications |",
                "| C6 / W6 | Local Codex | Integration, Runtime and Release |",
                "The separate front-end window F joins all six deliveries.",
                "The root controller M owns review and acceptance.",
                "M/controller = `gpt-6-astra`",
                "F/frontend = `gpt-6-astra`",
                "C1-C6 = `gpt-6.1-sol`",
                "Spawned task agents default to `gpt-6-luna` + `max`",
                "A choice made manually by the Product Owner overrides the role default.",
                "Hooks must never mutate model/effort/service tier.",
                "When no work remains, M stops and waits.",
                "The 49 audit dispositions are D01-D49, distinct from acceptance requirements R01-R15.",
            )
        )

    def _cloud_and_human_boundaries(self) -> str:
        return " ".join(
            (
                "fixed base SHA",
                "approved bounded/public sample inputs",
                "never upload secrets credentials Cookies private sessions complete production database",
                "must not create a branch open a PR directly push main or deploy",
                "W6 applies that exact patch",
                "local runtime/E2E validation",
                "do not call, auto-discover, probe, fall back to, or reactivate them",
                "legacy Ollama/local-model-provider, Zhipu or Jev",
                "interfaces and historical artifacts",
                "The Product Owner performs the repeated core-job acceptance only after engineering is fully operable",
                "development window E2E does not mark USER_VERIFIED, RELEASED or OPERATING",
            )
        )

    def _coverage_matrix(self) -> str:
        rows = (
            "R01 | M W6",
            "R02 | M W6 all windows",
            "R03 | C1 C6",
            "R04 | C1 C2 C5 C6",
            "R05 | C1 C2 C6",
            "R06 | C1 F C6",
            "R07 | C2 C4 C5",
            "R08 | C6 F",
            "R09 | C1 C2 C3 C5 C6 F",
            "R10 | C1 C3",
            "R11 | C2 C3 C4 C5",
            "R12 | C1 C2 C3",
            "R13 | C2 C3 C4 C5",
            "R14 | C1 C2 C5 C6 F",
            "R15 | C6 M Product Owner",
            "J1 | C1 C6",
            "J2 | C3",
            "J3 | C3",
            "J4 | C4",
            "J5 | C4",
            "J6 | C4",
            "J7 | C2",
            "J8 | C6 F",
        )
        return "\n".join(f"| {row} |" for row in rows)

    def test_unapproved_cloud_reactivation_is_blocking(self) -> None:
        matrix = self._agents_matrix()
        _assert_six_round_routing(matrix)

        swapped = matrix.replace(
            "| C3 / W3 | Local Codex |", "| C3 / W3 | Codex Cloud |", 1
        )
        with self.assertRaisesRegex(AssertionError, "C3 must use Local Codex"):
            _assert_six_round_routing(swapped)

    def test_current_snapshot_must_report_all_six_rounds(self) -> None:
        current = self._agents_matrix() + "\nLUMENIS-SOURCE-OWNER-INDEX-CURRENT.md"
        _assert_current_round_statuses(current)

        without_c4 = "\n".join(line for line in current.splitlines() if "C4 / W4" not in line)
        with self.assertRaisesRegex(AssertionError, "C4"):
            _assert_current_round_statuses(without_c4)

    def test_missing_or_remapped_legacy_coverage_is_blocking(self) -> None:
        matrix = self._coverage_matrix()
        _assert_legacy_coverage_mapping(matrix)

        without_r15 = "\n".join(line for line in matrix.splitlines() if "R15" not in line)
        with self.assertRaisesRegex(AssertionError, "R15"):
            _assert_legacy_coverage_mapping(without_r15)

        remapped_j7 = matrix.replace("| J7 | C2 |", "| J7 | C3 |", 1)
        with self.assertRaisesRegex(AssertionError, "J7 coverage omits"):
            _assert_legacy_coverage_mapping(remapped_j7)

    def test_cloud_isolation_retired_providers_and_final_human_gate_are_required(self) -> None:
        controls = self._cloud_and_human_boundaries()
        _assert_execution_boundaries(controls)

        with self.assertRaisesRegex(AssertionError, "fixed base SHA"):
            _assert_execution_boundaries(controls.replace("fixed base SHA ", "", 1))
        with self.assertRaisesRegex(AssertionError, "repeated core-job acceptance"):
            _assert_execution_boundaries(
                controls.replace(
                    "The Product Owner performs the repeated core-job acceptance only after engineering is fully operable",
                    "",
                    1,
                )
            )
        with self.assertRaisesRegex(AssertionError, "obsolete active execution routes"):
            _assert_execution_boundaries(controls + " Use Ollama first.")

    def test_readme_old_sequential_worker_route_is_blocking(self) -> None:
        readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
        _assert_readme_routing_consistent(readme)
        with self.assertRaisesRegex(AssertionError, "obsolete execution/provider routes"):
            _assert_readme_routing_consistent(readme + "\n15 个顺序 Codex 任务")

    def _assertion_section(self) -> str:
        path = Path(__file__).resolve().parents[1] / "00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md"
        source = path.read_text(encoding="utf-8")
        return JOB_ASSERTIONS_HEADING + source.split(JOB_ASSERTIONS_HEADING, 1)[1].split("\n## ", 1)[0]

    def _two_ledgers(self, section: str | None = None) -> str:
        return self._coverage_matrix() + "\n" + (self._assertion_section() if section is None else section)

    def test_both_coverage_ledgers_are_required_and_validated(self) -> None:
        _assert_legacy_coverage_mapping(self._two_ledgers(), require_assertions=True)
        with self.assertRaisesRegex(AssertionError, "exactly one"):
            _assert_legacy_coverage_mapping(self._coverage_matrix(), require_assertions=True)
        with self.assertRaisesRegex(AssertionError, "Missing current"):
            _assert_legacy_coverage_mapping(self._two_ledgers(JOB_ASSERTIONS_HEADING))

    def test_primary_duplicates_outside_assertion_section_still_fail(self) -> None:
        for heading in ("# Other", "## Other", "### Other"):
            with self.subTest(heading=heading), self.assertRaisesRegex(AssertionError, "duplicates coverage mapping J1"):
                _assert_legacy_coverage_mapping(self._two_ledgers() + f"\n{heading}\n| J1 | C1 C6 |")

    def test_assertion_ids_must_be_complete_unique_and_known(self) -> None:
        section = self._assertion_section()
        row = next(line for line in section.splitlines() if line.startswith("| U15 |"))
        mutations = {
            "missing": section.replace(row, ""),
            "duplicate_u": section + "\n" + row,
            "duplicate_j": section + "\n" + next(line for line in section.splitlines() if line.startswith("| J1 |")),
            "extra_u": section + "\n" + row.replace("U15", "U26"),
            "extra_r": section + "\n" + row.replace("U15", "R03"),
            "duplicate_heading": section + "\n" + JOB_ASSERTIONS_HEADING,
        }
        for mutation, changed in mutations.items():
            with self.subTest(mutation=mutation), self.assertRaises(AssertionError):
                _assert_legacy_coverage_mapping(self._two_ledgers(changed), require_assertions=True)

    def test_assertion_labels_outcomes_and_owner_cells_are_validated(self) -> None:
        section = self._assertion_section()
        row = next(line for line in section.splitlines() if line.startswith("| U15 |"))
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        for column in (1, 3):
            for placeholder in ("", "UNKNOWN", "NA", "PENDING"):
                changed = cells.copy()
                changed[column] = placeholder
                bad_row = "| " + " | ".join(changed) + " |"
                with self.subTest(column=column, placeholder=placeholder), self.assertRaisesRegex(AssertionError, "placeholder"):
                    _assert_legacy_coverage_mapping(self._two_ledgers(section.replace(row, bad_row)))
        for owner in ("C3 / C2 C5 F", "C4 / C2 C5 F C7", "C4 / C2 C5 F W7", ""):
            changed = cells.copy()
            changed[2] = owner
            with self.subTest(owner=owner), self.assertRaisesRegex(AssertionError, "owners"):
                _assert_legacy_coverage_mapping(self._two_ledgers(section.replace(row, "| " + " | ".join(changed) + " |")))
        with self.assertRaisesRegex(AssertionError, "four fields"):
            _assert_legacy_coverage_mapping(self._two_ledgers(section.replace(row, "| U15 | Podcast | C4 C2 C5 F |")))

    def test_assertion_cannot_drop_an_observed_primary_job_owner(self) -> None:
        changed = self._two_ledgers().replace("| J1 | C1 C6 |", "| J1 | C1 C2 C6 |", 1)
        with self.assertRaisesRegex(AssertionError, "J1 omits owners.*C2"):
            _assert_legacy_coverage_mapping(changed, require_assertions=True)


if __name__ == "__main__":
    unittest.main()
