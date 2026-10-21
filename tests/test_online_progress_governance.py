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
    _assert_engineering_owner_routing,
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

    def test_retired_root_rules_are_removed_not_banners_or_copies(self) -> None:
        import tempfile
        from unittest.mock import patch
        from scripts.audit_tools import verify_codex_takeover_governance as gate
        gate._assert_unique_current_rule_sources()
        current_agents = (gate.ROOT / "AGENTS.md").read_text("utf-8-sig")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "AGENTS.md").write_text(current_agents, encoding="utf8")
            (root / 'lumenis_shared_skills.py').write_text(
                '_LOCAL_RESEARCH = ["00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md"]',
                encoding='utf8')
            with patch.object(gate, 'ROOT', root):
                gate._assert_unique_current_rule_sources()
                for rel in gate.RETIRED_RULE_PATHS:
                    for suffix in ('', '.bak', '.old'):
                        path = root / (rel + suffix)
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text('HISTORICAL / NOT CURRENT. Old instructions still here.', encoding='utf8')
                        try:
                            with self.subTest(path=path.name), self.assertRaisesRegex(AssertionError, 'retired instruction files remain'):
                                gate._assert_unique_current_rule_sources()
                        finally:
                            path.unlink()
                (root / 'lumenis_shared_skills.py').write_text(
                    '_LOCAL_RESEARCH = ["ARCHITECTURE.md"]', encoding='utf8')
                with self.assertRaisesRegex(AssertionError, 'retired rule source'):
                    gate._assert_unique_current_rule_sources()

    def test_nested_execution_authorities_are_blocked_not_only_known_names(self) -> None:
        import tempfile
        from unittest.mock import patch
        from scripts.audit_tools import verify_codex_takeover_governance as gate
        current_agents = (gate.ROOT / "AGENTS.md").read_text("utf-8-sig")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "AGENTS.md").write_text(current_agents, encoding="utf8")
            (root / "lumenis_shared_skills.py").write_text(
                '_LOCAL_RESEARCH = ["00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md"]',
                encoding="utf8",
            )
            with patch.object(gate, "ROOT", root):
                cases = (
                    ("docs/ARCHITECTURE_DECISION_RECORD_20260830.md", "当前有效关系以：\n- CURRENT_BASELINE.md"),
                    ("intelligence_library/09_Research-Hub/docs/MASTER/FINAL_EXECUTION_COMMAND.md", "# FINAL EXECUTION COMMAND\nThis is current"),
                    ("intelligence_library/05_Runtime/architecture/lumenis_AI_PROGRAMMING_BASELINE_V1.md", "状态：正式施工基线"),
                    ("docs/MASTER/FINAL_EXECUTION_COMMAND.md", "# FINAL EXECUTION COMMAND\nSTATUS: P0 / FINAL EXECUTION AUTHORITY"),
                    ("docs/unlisted-later-master.md", "本文件是所有UI业务的统一执行母指令"),
                )
                for rel, bad in cases:
                    path = root / rel
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(bad, encoding="utf8")
                    try:
                        with self.subTest(path=rel), self.assertRaisesRegex(
                            AssertionError, "uncontrolled nested execution authority"
                        ):
                            gate._assert_unique_current_rule_sources()
                    finally:
                        path.unlink()
                hist = root / "docs/ARCHITECTURE_DECISION_RECORD_20260830.md"
                hist.write_text("# History only\nHISTORICAL / NOT EXECUTION", encoding="utf8")
                gate._assert_unique_current_rule_sources()

    def test_retiring_release_copy_preserves_real_safety_requirements(self) -> None:
        import tempfile
        from unittest.mock import patch
        from scripts.audit_tools import verify_codex_takeover_governance as gate
        source = (gate.ROOT / "AGENTS.md").read_text("utf-8-sig")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "lumenis_shared_skills.py").write_text(
                '_LOCAL_RESEARCH = ["00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md"]', encoding="utf8")
            with patch.object(gate, "ROOT", root):
                for requirement in (
                    "verify a restorable data backup and rollback path",
                    "Collector replacement requires isolated comparison",
                    "On session expiry, expose the platform, failure cause, affected task and cooldown",
                    "Each release records changed source, database migrations, actual verification",
                    "keep one product across its approved surfaces",
                ):
                    with self.subTest(requirement=requirement):
                        (root / "AGENTS.md").write_text(source.replace(requirement, "removed"), encoding="utf8")
                        with self.assertRaises(AssertionError):
                            gate._assert_unique_current_rule_sources()

    def test_nested_screen_template_cannot_restore_old_surface_or_visual_policy(self) -> None:
        import tempfile
        from unittest.mock import patch
        from scripts.audit_tools import verify_codex_takeover_governance as gate
        source = (gate.ROOT / "AGENTS.md").read_text("utf-8-sig")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "AGENTS.md").write_text(source, encoding="utf8")
            (root / "lumenis_shared_skills.py").write_text(
                '_LOCAL_RESEARCH = ["00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md"]', encoding="utf8")
            p = root / "contracts/experience/screen-specifications/SCREEN_SPEC_TEMPLATE.md"
            p.parent.mkdir(parents=True)
            with patch.object(gate, "ROOT", root):
                for obsolete in ("Website/Web closes first", "Website/Web first; native", "二维手绘水彩/版画视觉",
                                 "二维手绘水彩/版画色彩语言", "只借鉴手绘平面笔触与色彩", "不用3D质感"):
                    p.write_text(obsolete, encoding="utf8")
                    with self.subTest(phrase=obsolete), self.assertRaisesRegex(AssertionError, "obsolete surface instruction"):
                        gate._assert_unique_current_rule_sources()
                p.write_text("parallel construction, independent acceptance", encoding="utf8")
                gate._assert_unique_current_rule_sources()
                reference = root / "contracts/experience/README.md"
                reference.write_text("[old entry](../../RELEASE_POLICY.md)", encoding="utf8")
                with self.assertRaisesRegex(AssertionError, "active reference to retired instruction"):
                    gate._assert_unique_current_rule_sources()
                reference.write_text("[current entry](../../AGENTS.md)", encoding="utf8")
                gate._assert_unique_current_rule_sources()

    def test_decision_binding_inventory_does_not_erase_existing_owner(self) -> None:
        import json
        root = Path(__file__).resolve().parents[1]
        contracts = root / "contracts/experience"
        gap = next(row for row in json.loads((contracts / "BACKEND_GAP.json").read_text("utf8"))["gaps"] if row["gap_id"] == "BACKEND-GAP-016")
        unknown = next(row for row in json.loads((contracts / "unknown-bindings.json").read_text("utf8"))["bindings"] if row["binding_id"] == gap["gap_id"])
        matrix = next(row for row in json.loads((contracts / "BINDING_MATRIX.json").read_text("utf8"))["matrix"] if (row["screen"], row["field"]) == (gap["screen"], gap["field"]))
        registry = next(row for row in json.loads((contracts / "lumenis_app_binding_registry.json").read_text("utf8"))["bindings"] if row["binding_id"] == gap["gap_id"])
        self.assertEqual(gap["current_api"], unknown["current_api"])
        self.assertEqual(gap["current_api"], matrix["current_source"])
        self.assertEqual(gap["current_api"], registry["api_callable"])
        self.assertIn("BusinessDecisionWorkflow", gap["current_api"])
        self.assertNotEqual(gap["source_status"], "ABSENT")
        self.assertNotEqual(gap["app_status"], "NO_FLUTTER_SCREEN")
        self.assertEqual(gap["source_status"], unknown["source_status"])
        self.assertEqual(gap["source_status"], matrix["status"])
        # Source presence must not silently promote the separate live result.
        if registry["truth_status"] == "UNVERIFIED_ACCEPTANCE_PENDING":
            self.assertEqual(gap["acceptance_status"], "PENDING")
        self.assertIn("EXISTS_BUT_UNSCOPED", json.loads((contracts / "BACKEND_GAP.json").read_text("utf8"))["field_semantics"]["source_status"])

    def test_current_binding_summary_and_mirrors_reject_drift(self) -> None:
        import copy
        import json
        from scripts.audit_tools import verify_experience_screen_blueprints as screen_gate
        root = Path(__file__).resolve().parents[1]
        registry = json.loads((root / "contracts/experience/lumenis_app_binding_registry.json").read_text("utf8"))
        sources = {p: json.loads((root / p).read_text("utf8")) for p in screen_gate.SOURCE_FILES}
        screen_gate._validate_source_ids(registry, sources)
        for key in ("total", "bound", "absent", "local_only", "status_counts", "bound_screens"):
            changed = copy.deepcopy(sources)
            summary = changed["contracts/experience/unknown-bindings.json"]["ledger_summary"]
            summary[key] = {} if key == "status_counts" else [] if key == "bound_screens" else -1
            with self.subTest(field=key), self.assertRaisesRegex(AssertionError, "binding summary"):
                screen_gate._validate_source_ids(registry, changed)
        changed = copy.deepcopy(sources)
        changed["contracts/experience/BACKEND_GAP.json"]["gaps"][0]["app_status"] = "NO_FLUTTER_SCREEN"
        with self.assertRaisesRegex(AssertionError, "Flutter presence claims disagree"):
            screen_gate._validate_source_ids(registry, changed)

    def test_existing_flutter_widgets_are_not_declared_absent(self) -> None:
        import json
        import re
        root = Path(__file__).resolve().parents[1]
        shell = (root / "app/lib/shell/lumenis_workspace_shell.dart").read_text("utf8")
        rows = json.loads((root / "contracts/experience/BACKEND_GAP.json").read_text("utf8"))["gaps"]
        for row in rows:
            sid = row["screen"].replace("-", "").lower()
            for path in (root / "app/lib/features").rglob(sid + "_screen.dart"):
                for widget in re.findall(r"class\s+(\w+)\s+extends\s+(?:StatefulWidget|StatelessWidget)", path.read_text("utf8")):
                    if not widget.startswith("_") and re.search(r"\b" + re.escape(widget) + r"\s*\(", shell):
                        with self.subTest(binding=row["gap_id"], widget=widget):
                            self.assertNotEqual(row["app_status"], "NO_FLUTTER_SCREEN")

    def test_shared_rule_references_are_not_executable_module_bindings(self) -> None:
        import lumenis_shared_skills as shared
        card = shared.get_shared_skill('shared.social_card')
        self.assertIn('00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md', card['research_basis'])
        result = shared._binding_state(card)
        self.assertTrue(result['available'])
        self.assertEqual([row['module'] for row in result['bindings']], ['lumenis_shared_skills.py'])
        for spec in shared.SHARED_SKILL_CATALOG:
            for binding in spec['bindings']:
                with self.subTest(skill=spec['metadata']['skill_id'], binding=binding['module']):
                    self.assertTrue(binding['module'].endswith('.py'))

    def test_human_routing_mirror_keeps_c1_through_c6_exactly_once(self) -> None:
        matrix = self._agents_matrix()
        _assert_engineering_owner_routing(matrix)

        without_c4 = "\n".join(line for line in matrix.splitlines() if "C4 / W4" not in line)
        with self.assertRaisesRegex(AssertionError, "C4"):
            _assert_engineering_owner_routing(without_c4)

        remapped = matrix.replace("| C3 / W3 |", "| C3 / W4 |", 1)
        with self.assertRaisesRegex(AssertionError, "routing mismatch"):
            _assert_engineering_owner_routing(remapped)

    def test_current_snapshot_must_report_all_six_source_owners(self) -> None:
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

    def test_rules_only_publication_requires_governance_changes_and_unverified_runtime(self) -> None:
        rules_only = """
## 1. Online reader's current-state snapshot
### Repair
Implementation publication state: `RULES_ONLY_PUBLICATION`
Runtime load state: `NOT_LOADED_OR_NOT_VERIFIED`
### Approved D1–D5 convergence — 2026-10-06
"""
        current_path = "00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md"
        rules_paths = {
            current_path,
            "AGENTS.md",
            "00-GOVERNANCE/evidence/round-15/NEW-RULES-REPORT.md",
            "scripts/audit_tools/verify_codex_takeover_governance.py",
            "scripts/audit_tools/verify_lumenis_single_product.py",
            "tests/test_online_progress_governance.py",
            "tests/test_audit_inventory_boundaries.py",
            ".codex/model-routing.toml",
            ".codex/tests/test_engineering.py",
            "website/DEVELOPMENT-BRIEF.md",
            "contracts/experience/BACKEND_GAP.json",
            "contracts/experience/BINDING_MATRIX.json",
            "contracts/experience/lumenis_app_binding_registry.json",
            "contracts/experience/unknown-bindings.json",
            "scripts/audit_tools/verify_experience_screen_blueprints.py",
            "docs/ARCHITECTURE_DECISION_RECORD_20260830.md",
            "docs/MASTER/FINAL_EXECUTION_COMMAND.md",
            "intelligence_library/05_Runtime/architecture/lumenis_AI_PROGRAMMING_BASELINE_V1.md",
            "intelligence_library/09_Research-Hub/docs/MASTER/FINAL_EXECUTION_COMMAND.md",
        }
        _assert_current_publication_truth(rules_only, changed_paths=rules_paths)

        _assert_current_publication_truth(
            rules_only,
            changed_paths=rules_paths | {
                "00-GOVERNANCE/evidence/round-15/full-product-audit-20261003/MATERIAL-OWNER-MANIFEST.json",
                "contracts/experience/source-target-contract-v1.json",
            },
        )
        for runtime_path in (
            "data/runtime/governance/live_dispatch.json",
            "lumenis/system/browser/config.json",
            "contracts/experience/unreviewed-runtime.json",
            "docs/unreviewed-rule-file.md",
            ".codex/config.toml",
            ".codex/tests/unreviewed_test.py",
            "website/src/components/UnreviewedBehavior.astro",
            "tests/test_unrelated_product.py",
            "scripts/audit_tools/verify_unreviewed_runtime.py",
            "scripts/audit_tools/verify_lumenis_single_product.py.backup",
        ):
            with self.subTest(runtime_path=runtime_path):
                with self.assertRaisesRegex(AssertionError, "governance/documentation paths only"):
                    _assert_current_publication_truth(
                        rules_only, changed_paths=rules_paths | {runtime_path}
                    )

        with self.assertRaisesRegex(AssertionError, "CURRENT co-publication"):
            _assert_current_publication_truth(
                rules_only,
                changed_paths={"AGENTS.md"},
            )

        with self.assertRaisesRegex(AssertionError, "governance/documentation paths only"):
            _assert_current_publication_truth(
                rules_only,
                changed_paths=rules_paths | {"app.py"},
            )

        with self.assertRaisesRegex(AssertionError, "runtime state"):
            _assert_current_publication_truth(
                rules_only.replace(
                    "NOT_LOADED_OR_NOT_VERIFIED", "LOADED_AND_VERIFIED"
                ),
                changed_paths=rules_paths,
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
        positioning = (Path(__file__).resolve().parents[1] / "00-GOVERNANCE" /
                       "PRODUCT-POSITIONING-CURRENT.md").read_text(encoding="utf-8")
        for stale in ("Website/Web优先及原生Windows/macOS/iOS顺序不变",
                      "Public Website and Web Workspace close first.",
                      "Later native application targets", "Exact seven-domain coverage"):
            with self.subTest(stale=stale):
                self.assertNotIn(stale, positioning)
        for current in ("built in parallel", "accepted independently", "Independently usable"):
            with self.subTest(current=current):
                self.assertIn(current, positioning)

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


# T04 (阿康（bot）): historical PO prohibitions are structured machine red lines,
# validated by the blocking governance validator rather than frozen English prose.
class HistoricalProhibitionRedLinesTest(unittest.TestCase):
    def test_machine_contract_keeps_every_historical_prohibition(self) -> None:
        from scripts.audit_tools.verify_governance_machine_contract import (
            CONTRACT_PATH, HISTORICAL_PROHIBITION_RED_LINES, load_json, validate_contract,
        )
        red = load_json(CONTRACT_PATH)["red_lines"]
        self.assertEqual(len(HISTORICAL_PROHIBITION_RED_LINES), 6)
        for key in HISTORICAL_PROHIBITION_RED_LINES:
            self.assertIs(red.get(key), False, key)
        validate_contract()

    def test_dropping_or_allowing_a_historical_prohibition_fails_validation(self) -> None:
        import copy
        from unittest.mock import patch
        from scripts.audit_tools import verify_governance_machine_contract as gov
        base = gov.load_json(gov.CONTRACT_PATH)
        for key in gov.HISTORICAL_PROHIBITION_RED_LINES:
            for mutate in ("drop", "allow"):
                c = copy.deepcopy(base)
                if mutate == "drop":
                    del c["red_lines"][key]
                else:
                    c["red_lines"][key] = True
                with patch.object(gov, "load_json", return_value=c):
                    with self.assertRaises(AssertionError, msg=f"{mutate}:{key}"):
                        gov.validate_contract()


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
    assert any('--cached' not in cmd for cmd in seen)
    assert any('--cached' in cmd for cmd in seen)

def test_pr_publication_uses_full_branch_history_not_last_commit(monkeypatch):
    from types import SimpleNamespace
    from scripts.audit_tools import verify_codex_takeover_governance as gate
    calls = []
    def fake_run(command, **kwargs):
        calls.append(command)
        if "symbolic-ref" in command:
            return SimpleNamespace(returncode=0, stdout="fix/my-pr\n", stderr="")
        if "merge-base" in command:
            return SimpleNamespace(returncode=0, stdout=("a" * 40) + "\n", stderr="")
        if "diff" in command:
            return SimpleNamespace(returncode=0, stdout="lumenis_shared_skills.py\n00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="README.md\n", stderr="")
    monkeypatch.setattr(gate.subprocess, "run", fake_run)
    observed = gate._publication_changed_paths()
    assert observed == {"lumenis_shared_skills.py", "00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md"}
    assert any("merge-base" in cmd for cmd in calls)
    assert any("diff" in cmd and "a"*40 in cmd for cmd in calls)
    import pytest
    marker = chr(96)
    rules = "\n## 1. Online reader's current-state snapshot\nImplementation publication state: " + marker + "RULES_ONLY_PUBLICATION" + marker + "\nRuntime load state: " + marker + "NOT_LOADED_OR_NOT_VERIFIED" + marker + "\n### Approved D1"
    with pytest.raises(AssertionError, match="governance/documentation paths only"):
        gate._assert_current_publication_truth(rules, changed_paths=observed)


def test_recovered_archive_is_finite_evidence_not_product_behavior():
    from scripts.audit_tools import verify_codex_takeover_governance as gate
    inventory = gate._recovered_evidence_inventory()
    assert len(inventory) == 275
    gate._assert_recovered_evidence_integrity()
    for path in inventory:
        assert gate._is_rules_only_publication_path(path), path
        assert not gate._is_product_behavior_source(path), path
    assert gate._is_rules_only_publication_path(gate.RECOVERED_EVIDENCE_RECEIPT)
    assert gate._is_rules_only_publication_path(gate.RECOVERED_EVIDENCE_REPORT)
    for path in (
        'research/arbitrary.py', 'research/arbitrary.json',
        'app/lib/recovered.dart', 'lumenis/runtime/recovered.py',
        gate.RECOVERED_EVIDENCE_REPORT + '.py',
        next(iter(inventory)) + '.unlisted.py',
    ):
        assert not gate._is_rules_only_publication_path(path), path
    import pytest
    current = """
## 1. Online reader's current-state snapshot
Implementation publication state: `RULES_ONLY_PUBLICATION`
Runtime load state: `NOT_LOADED_OR_NOT_VERIFIED`
### Approved D1
"""
    changes = set(inventory) | {
        '00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md',
        gate.RECOVERED_EVIDENCE_RECEIPT, gate.RECOVERED_EVIDENCE_REPORT,
    }
    gate._assert_current_publication_truth(current, changed_paths=changes)
    with pytest.raises(AssertionError, match='same-commit product behavior source'):
        gate._assert_current_publication_truth(
            current.replace('RULES_ONLY_PUBLICATION', 'PUBLISHED_SOURCE_VERIFIED'),
            changed_paths=changes,
        )
    code_path = next(path for path in inventory if path.endswith('.py'))
    assert not gate._is_rules_only_publication_path(code_path.replace('/', '\\'))
    assert not gate._is_rules_only_publication_path(code_path.replace('/reports/', '/reports/../reports/'))
    assert gate._is_product_behavior_source('research/arbitrary.py')


def test_recovery_receipt_cannot_self_authorize_paths(tmp_path, monkeypatch):
    import copy
    import json
    from scripts.audit_tools import verify_codex_takeover_governance as gate
    original = json.loads((gate.ROOT / gate.RECOVERED_EVIDENCE_RECEIPT).read_text())
    receipt = tmp_path / gate.RECOVERED_EVIDENCE_RECEIPT
    receipt.parent.mkdir(parents=True)
    monkeypatch.setattr(gate, 'ROOT', tmp_path)
    mutations = []
    extra = copy.deepcopy(original)
    extra['files'].append(copy.deepcopy(extra['files'][0]))
    mutations.append(extra)
    duplicate = copy.deepcopy(original)
    duplicate['files'][0] = copy.deepcopy(duplicate['files'][1])
    mutations.append(duplicate)
    for replacement in ('research/arbitrary.py', 'app/lib/runtime.dart',
                        '../outside.py', '/absolute.py', 'research/../outside.py',
                        'research\\outside.py', 'research//outside.py'):
        changed = copy.deepcopy(original)
        changed['files'][0]['repository_relative_path'] = replacement
        mutations.append(changed)
    for bad in (None, [], {}, {'files': {}}, *mutations):
        receipt.write_text(json.dumps(bad))
        assert not gate._is_rules_only_publication_path(gate.RECOVERED_EVIDENCE_RECEIPT)
        assert not gate._is_rules_only_publication_path(original['files'][0]['repository_relative_path'])
    receipt.write_text('{broken')
    assert not gate._is_rules_only_publication_path(gate.RECOVERED_EVIDENCE_RECEIPT)
    receipt.unlink()
    assert not gate._is_rules_only_publication_path(gate.RECOVERED_EVIDENCE_RECEIPT)


def test_recovered_archive_requires_actual_bytes_not_receipt_claim(tmp_path, monkeypatch):
    import json
    from scripts.audit_tools import verify_codex_takeover_governance as gate
    original_root = gate.ROOT
    original = json.loads((original_root / gate.RECOVERED_EVIDENCE_RECEIPT).read_text())
    entry = next(item for item in original['files'] if item['repository_relative_path'].endswith('.py'))
    path = entry['repository_relative_path']
    content = (original_root / path).read_bytes()
    receipt = tmp_path / gate.RECOVERED_EVIDENCE_RECEIPT
    receipt.parent.mkdir(parents=True)
    receipt.write_text(json.dumps(original))
    target = tmp_path / path
    target.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(gate, 'ROOT', tmp_path)
    assert not gate._is_rules_only_publication_path(path)
    target.write_bytes(content)
    assert gate._is_rules_only_publication_path(path)
    target.write_bytes(content + b'\n')
    assert not gate._is_rules_only_publication_path(path)
    target.write_bytes(bytes([content[0] ^ 1]) + content[1:])
    assert not gate._is_rules_only_publication_path(path)
    target.unlink()
    outside = tmp_path / 'outside.py'
    outside.write_bytes(content)
    target.symlink_to(outside)
    assert not gate._is_rules_only_publication_path(path)


def test_receipt_only_publication_checks_unchanged_archive_members(tmp_path, monkeypatch):
    import pytest
    from scripts.audit_tools import verify_codex_takeover_governance as gate
    receipt_content = (gate.ROOT / gate.RECOVERED_EVIDENCE_RECEIPT).read_bytes()
    receipt = tmp_path / gate.RECOVERED_EVIDENCE_RECEIPT
    receipt.parent.mkdir(parents=True)
    receipt.write_bytes(receipt_content)
    # Receipt is intact but its unchanged members are absent from this checkout.
    monkeypatch.setattr(gate, 'ROOT', tmp_path)
    current_path = '00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md'
    monkeypatch.setitem(gate.PATHS, 'takeover', tmp_path / current_path)
    current = """
## 1. Online reader's current-state snapshot
Implementation publication state: `RULES_ONLY_PUBLICATION`
Runtime load state: `NOT_LOADED_OR_NOT_VERIFIED`
### Approved D1
"""
    with pytest.raises(FileNotFoundError):
        gate._assert_current_publication_truth(current, changed_paths={
            current_path, gate.RECOVERED_EVIDENCE_RECEIPT,
        })


def test_governance_production_cli_smoke():
    import subprocess
    import sys
    from scripts.audit_tools import verify_codex_takeover_governance as gate
    result = subprocess.run(
        [sys.executable, str(Path(gate.__file__))], cwd=gate.ROOT,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'CODEX TAKEOVER GOVERNANCE OK' in result.stdout


def test_governance_validate_staged_reads_index_snapshot(monkeypatch):
    import subprocess
    from scripts.audit_tools import verify_codex_takeover_governance as gate
    run = gate.subprocess.run
    current_path = '00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md'
    staged_current = """
## 1. Online reader's current-state snapshot
Implementation publication state: `RULES_ONLY_PUBLICATION`
Runtime load state: `NOT_LOADED_OR_NOT_VERIFIED`
### Approved D1
"""
    calls = []

    def staged_run(command, **kwargs):
        if command == ['git', 'show', ':' + current_path]:
            calls.append('index-current')
            return subprocess.CompletedProcess(command, 0, staged_current, '')
        return run(command, **kwargs)

    def changed_paths(*, staged=False):
        assert staged
        calls.append('index-paths')
        return {current_path, 'AGENTS.md'}

    monkeypatch.setattr(gate.subprocess, 'run', staged_run)
    monkeypatch.setattr(gate, '_publication_changed_paths', changed_paths)
    gate.validate(staged=True)
    assert calls == ['index-current', 'index-paths']
