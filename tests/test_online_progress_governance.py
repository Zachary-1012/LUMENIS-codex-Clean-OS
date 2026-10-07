from __future__ import annotations

import unittest
from pathlib import Path

from scripts.audit_tools.verify_codex_takeover_governance import (
    JOB_ASSERTIONS_HEADING,
    _assert_current_publication_truth,
    _assert_current_round_statuses,
    _assert_execution_boundaries,
    _assert_legacy_coverage_mapping,
    _assert_readme_routing_consistent,
    _assert_six_round_routing,
)


class GovernanceHistoryRegressionTests(unittest.TestCase):
    def _agents_matrix(self) -> str:
        return "\n".join(
            (
                "Root AGENTS.md is the only repository execution router.",
                "| C1 / W1 | mirror |",
                "| C2 / W2 | mirror |",
                "| C3 / W3 | mirror |",
                "| C4 / W4 | mirror |",
                "| C5 / W5 | mirror |",
                "| C6 / W6 | mirror |",
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

    def test_human_routing_mirror_keeps_c1_through_c6_exactly_once(self) -> None:
        matrix = self._agents_matrix()
        _assert_six_round_routing(matrix)

        without_c4 = "\n".join(line for line in matrix.splitlines() if "C4 / W4" not in line)
        with self.assertRaisesRegex(AssertionError, "C4"):
            _assert_six_round_routing(without_c4)

        remapped = matrix.replace("| C3 / W3 |", "| C3 / W4 |", 1)
        with self.assertRaisesRegex(AssertionError, "routing mismatch"):
            _assert_six_round_routing(remapped)

    def test_current_snapshot_must_report_all_six_rounds(self) -> None:
        current = self._agents_matrix() + "\nAGENTS.md\nLUMENIS-SOURCE-OWNER-INDEX-CURRENT.md"
        _assert_current_round_statuses(current)

        without_c4 = "\n".join(line for line in current.splitlines() if "C4 / W4" not in line)
        with self.assertRaisesRegex(AssertionError, "C4"):
            _assert_current_round_statuses(without_c4)

    def test_current_publication_truth_separates_local_candidate_from_published_source(self) -> None:
        local = """
## 1. Online reader's current-state snapshot
### Repair
Implementation publication state: `LOCAL_CANDIDATE_NOT_PUBLISHED`
Runtime load state: `NOT_LOADED_OR_NOT_VERIFIED`
The repair is not yet part of GitHub main and describes the current protected local candidate only.
It is not published Product Source. Promotion requires one coherent delivery.
### Approved D1–D5 convergence — 2026-10-06
"""
        _assert_current_publication_truth(local, changed_paths=set())

        false_published = local.replace(
            "LOCAL_CANDIDATE_NOT_PUBLISHED", "PUBLISHED_SOURCE_VERIFIED"
        )
        with self.assertRaisesRegex(
            AssertionError, "same-commit product behavior source|co-publication"
        ):
            _assert_current_publication_truth(
                false_published,
                changed_paths={
                    "00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md"
                },
            )

        _assert_current_publication_truth(
            false_published,
            changed_paths={
                "00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md",
                "collection_api.py",
            },
        )

    def test_current_publication_truth_requires_explicit_state_markers(self) -> None:
        with self.assertRaisesRegex(AssertionError, "publication state"):
            _assert_current_publication_truth(
                "## 1. Online reader's current-state snapshot\n"
                "### Approved D1–D5 convergence — 2026-10-06",
                changed_paths=set(),
            )

    def test_obsolete_execution_routes_are_blocking(self) -> None:
        _assert_execution_boundaries("current human explanation")
        for obsolete in (
            "Product Owner's parallelism target is ten",
            "ten is also the approved operating ceiling",
            "Use OpenCode with the configured Zhipu provider first",
            "Use Ollama first",
            "ROUND 02 starts only in a new Sol-controlled task",
        ):
            with self.subTest(obsolete=obsolete), self.assertRaisesRegex(AssertionError, "obsolete execution routes"):
                _assert_execution_boundaries("current human explanation " + obsolete)

    def test_readme_old_sequential_worker_route_is_blocking(self) -> None:
        readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
        _assert_readme_routing_consistent(readme)
        with self.assertRaisesRegex(AssertionError, "obsolete execution/provider routes"):
            _assert_readme_routing_consistent(readme + "\n15 个顺序 Codex 任务")

    def test_missing_or_remapped_legacy_coverage_is_blocking(self) -> None:
        matrix = self._coverage_matrix()
        _assert_legacy_coverage_mapping(matrix)

        without_r15 = "\n".join(line for line in matrix.splitlines() if "R15" not in line)
        with self.assertRaisesRegex(AssertionError, "R15"):
            _assert_legacy_coverage_mapping(without_r15)

        remapped_j7 = matrix.replace("| J7 | C2 |", "| J7 | C3 |", 1)
        with self.assertRaisesRegex(AssertionError, "J7 coverage omits"):
            _assert_legacy_coverage_mapping(remapped_j7)

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


def test_publication_paths_keep_staged_and_committed_evidence_separate(monkeypatch):
    from types import SimpleNamespace
    from scripts.audit_tools import verify_codex_takeover_governance as gate

    seen = []
    def git_result(command, **kwargs):
        seen.append(command)
        if command[1] == 'diff':
            return SimpleNamespace(returncode=0, stdout='collection_api.py\n00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md\n', stderr='')
        return SimpleNamespace(returncode=0, stdout='README.md\n', stderr='')
    monkeypatch.setattr(gate.subprocess, 'run', git_result)
    assert gate._publication_changed_paths() == {'README.md'}
    assert gate._publication_changed_paths(staged=True) == {
        'collection_api.py', '00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md'}
    assert '--cached' not in seen[0]
    assert '--cached' in seen[1]
