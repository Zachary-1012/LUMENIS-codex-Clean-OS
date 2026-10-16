import importlib.util
import io
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "lumenis_hooks.py"
ENGINEERING = Path(__file__).resolve().parents[1] / "engineering.py"
spec = importlib.util.spec_from_file_location("lumenis_hooks", HOOK)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
eng_spec = importlib.util.spec_from_file_location("lumenis_engineering", ENGINEERING)
eng = importlib.util.module_from_spec(eng_spec)
eng_spec.loader.exec_module(eng)
logger = logging.getLogger(__name__)

class EngineeringTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lumenis-test-")
        self.root = Path(self.temp.name) / "序境"
        self.root.mkdir()
        self.previous_eng_root = eng.ROOT
        self.previous_state_root = eng.HOOKS.STATE_ROOT
        self.previous_test_hook_state_root = h.STATE_ROOT
        eng.ROOT = self.root
        isolated_state_root = Path(self.temp.name) / "engineering-state"
        eng.HOOKS.STATE_ROOT = isolated_state_root
        h.STATE_ROOT = isolated_state_root
        self.git("init", "-q")
        # Disposable fixtures must not spawn background Git maintenance or
        # inherit a workstation fsmonitor. Cleanup remains strict; no retry or
        # ignore_errors hides a live writer racing TemporaryDirectory removal.
        for key, value in (
            ("core.fsmonitor", "false"), ("gc.auto", "0"),
            ("maintenance.auto", "false"), ("gc.autoDetach", "false"),
            ("maintenance.autoDetach", "false"),
        ):
            self.git("config", "--local", key, value)
        self.git("config", "user.email", "engineering-test@example.invalid")
        self.git("config", "user.name", "Engineering test")
        (self.root / "AGENTS.md").write_text("# LUMENIS test fixture", "utf-8")
        (self.root / "README.md").write_text("# Fixture README", "utf-8")
        (self.root / "pytest.ini").write_text("[pytest]\n", "utf-8")
        (self.root / "sample.py").write_text("value = 1\n", "utf-8")
        governance = self.root / "00-GOVERNANCE"
        governance.mkdir()
        machine_contract = h.VERIFICATION_POLICY_PATH.as_posix()
        for relative in h.CONTINUITY_RULES:
            if relative in {"AGENTS.md", "README.md", machine_contract}:
                continue
            authority = self.root / relative
            authority.parent.mkdir(parents=True, exist_ok=True)
            authority.write_text("{}\n" if authority.suffix == ".json" else f"# Fixture {authority.stem}\n", "utf-8")
        authority_paths = [value for value in h.CONTINUITY_RULES if value != machine_contract]
        self.git("add", "--", "sample.py", "pytest.ini", *authority_paths)
        self.git("commit", "-qm", "isolated fixture")
        policy_path = self.root / h.VERIFICATION_POLICY_PATH
        policy_path.parent.mkdir(parents=True, exist_ok=True)
        policy_path.write_text(json.dumps({"verification_policy": {
            "unit_integration_required": False, "create_unit_integration_allowed": True,
            "run_unit_integration_allowed": True, "renamed_module_suites_allowed": True,
            "affected_regressions_required": True, "retained_checks": ["compilation", "static_quality"]}}), "utf-8")
        self.git("add", str(h.VERIFICATION_POLICY_PATH))
        self.git("commit", "-qm", "isolated approved policy fixture")
        self.state = {}
        self.handle("SessionStart", source="startup")

    def tearDown(self):
        eng.ROOT = self.previous_eng_root
        eng.HOOKS.STATE_ROOT = self.previous_state_root
        h.STATE_ROOT = self.previous_test_hook_state_root
        self.temp.cleanup()

    def git(self, *args):
        p = subprocess.run(["git", "-c", "core.fsmonitor=false", "-c", "gc.auto=0", "-c", "maintenance.auto=false", "-C", str(self.root), *args], capture_output=True, encoding="utf-8", timeout=20, check=False)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout

    def handle(self, name, **fields):
        return h.handle({"hook_event_name": name, "cwd": str(self.root), **fields}, self.root, self.state)

    def edit(self, value=2):
        (self.root / "sample.py").write_text(f"value = {value}\n", "utf-8")
        self.handle("PostToolUse", tool_name="apply_patch", tool_input={"command": "patch"}, tool_response={"exit_code": 0})

    def verify(self, code=0, command="python -m unittest discover", **extra):
        if command == "python -m unittest discover":
            self.handle("PostToolUse", tool_name="Bash", tool_input={"command": "python -m py_compile sample.py"}, tool_response={"exit_code": 0})
            self.handle("PostToolUse", tool_name="Bash", tool_input={"command": "ruff check --select F sample.py"}, tool_response={"exit_code": 0})
        self.handle("PostToolUse", tool_name="Bash", tool_input={"command": command}, tool_response={"exit_code": code, **extra})

    def test_unicode_root(self):
        self.assertEqual(h.find_root(str(self.root)), self.root)
        self.assertEqual(h.find_root(str(self.root / "subfolder")), self.root)

    def test_safe_read_is_not_blocked(self):
        self.assertIsNone(h.policy_reason({"tool_name": "Bash", "tool_input": {"command": "git status --short"}}))

    def test_dangerous_git_variants(self):
        commands = [
            "git reset --hard HEAD",
            "git push origin main --force",
            "git push -f",
            "git clean -xdf",
            'git -C "D:/repo" reset --hard HEAD',
            "git checkout -- .",
            "git checkout HEAD -- .",
            "git restore .",
            "git add .",
            "git add -A",
            "git add --all",
            'git commit -a -m "unsafe"',
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assertIsNotNone(h.policy_reason({"tool_name": "Bash", "tool_input": {"command": command}}))

    def test_patch_can_contain_policy_test_text(self):
        self.assertIsNone(h.policy_reason({"tool_name": "apply_patch", "tool_input": {"command": "test string: git reset --hard HEAD"}}))

    def test_mcp_exec_is_checked(self):
        self.assertIsNotNone(h.policy_reason({"tool_name": "mcp__desktop__start_process", "tool_input": {"command": "git reset --hard HEAD"}}))

    def test_missing_check_blocks(self):
        self.edit()
        self.assertEqual(self.handle("Stop").get("decision"), "block")

    def test_compile_alone_does_not_satisfy_code_change(self):
        self.edit()
        self.verify(0, "python -m compileall -q sample.py")
        self.assertEqual(self.handle("Stop").get("decision"), "block")

    def test_static_alone_does_not_satisfy_code_change(self):
        self.edit()
        self.verify(0, "ruff check --select F sample.py")
        self.assertEqual(self.handle("Stop").get("decision"), "block")

    def test_failed_test_blocks(self):
        self.edit(); self.verify(1)
        self.assertEqual(self.handle("Stop").get("decision"), "block")

    def test_unknown_exit_blocks(self):
        self.edit(); self.verify(None)
        self.assertEqual(self.handle("Stop").get("decision"), "block")

    def test_successful_current_test_is_recorded(self):
        self.edit(); self.verify(0)
        self.assertEqual(self.handle("Stop"), {})
        self.assertEqual(self.state["verification_status"], "SCOPED_CHECK_OBSERVED")

    def test_static_check_is_not_code_test(self):
        self.edit(); self.verify(0, "git diff --check")
        self.assertEqual(self.handle("Stop").get("decision"), "block")

    def test_echo_is_not_test(self):
        self.edit(); self.verify(0, "echo pytest")
        self.assertEqual(self.handle("Stop").get("decision"), "block")

    def test_same_status_new_content_invalidates_result(self):
        self.edit(); self.verify(0)
        (self.root / "sample.py").write_text("value = 3\n", "utf-8")
        self.assertEqual(self.handle("Stop").get("decision"), "block")

    def test_compact_does_not_reset_baseline(self):
        before = self.state["baseline"]["fingerprint"]
        self.edit()
        self.handle("PreCompact")
        self.handle("PostCompact")
        self.handle("SessionStart", source="compact")
        self.assertEqual(self.state["baseline"]["fingerprint"], before)
        self.assertTrue(self.state["mutation_observed"])

    def test_session_start_reports_current_head_not_old_baseline(self):
        old_head = self.state["baseline"]["head"]
        (self.root / "sample.py").write_text("value = 4\n", "utf-8")
        self.git("add", "sample.py")
        self.git("commit", "-qm", "advance fixture head")
        current_head = self.git("rev-parse", "HEAD").strip()
        output = self.handle("SessionStart", source="resume")
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn(f"Current local HEAD={current_head}", context)
        self.assertNotIn(f"Current local HEAD={old_head}", context)
        self.assertEqual(self.state["baseline"]["head"], old_head)

    def test_model_context_does_not_inject_historical_model_defaults(self):
        context = h.model_policy_context({"model": "manually-selected-model"})
        self.assertIn("Observed event model=manually-selected-model", context)
        for historical in ("GPT-6 Luna", "GPT-6.1 Sol", "GPT-6 Astra"):
            self.assertNotIn(historical, context)

    def test_continuity_rejects_missing_session_identity(self):
        with self.assertRaises(ValueError):
            h.state_file({}, self.root)
        with mock.patch.dict(os.environ, {"CODEX_THREAD_ID": "", "CODEX_SESSION_ID": "", "CODEX_AGENT_ID": ""}), self.assertRaises(ValueError):
            eng.dispatch("continuity", {"mode": "read", "record": "work/checkpoint.json", "section": "continuity"})

    def test_continuity_rejects_conflicting_thread_and_session_identity(self):
        self.make_continuity_record()
        with mock.patch.dict(os.environ, {"CODEX_THREAD_ID": "thread-a", "CODEX_SESSION_ID": "session-b"}), self.assertRaises(ValueError):
            eng.dispatch("continuity", {"mode": "save", "record": "work/checkpoint.json", "section": "continuity"})

    def test_continuity_state_isolated_by_session(self):
        first = h.state_file({"session_id": "session-a"}, self.root)
        second = h.state_file({"session_id": "session-b"}, self.root)
        self.assertNotEqual(first, second)

    def continuity_item(self, pending_effects=None):
        return {
            "owner": "C4",
            "objective": "Complete the existing video deliverable outcome with save, reopen, recovery, and acceptance evidence.",
            "po_source": "Direct PO instruction dated 2026-10-11; source declaration only, not dispatch authorization.",
            "constraints": ["Keep this checkpoint in the existing C4 owner record."],
            "completed": ["Engineering continuity wrapper is being validated; this does not prove product E2E."],
            "remaining": ["Complete real user operation, save/reopen/recovery, and acceptance."],
            "next_action": "Read the pinned owner record and reconcile current source and receipts before writing.",
            "pending_effects": list(pending_effects or []),
            "source_paths": ["sample.py"],
            "evidence_paths": ["work/evidence.json"],
            "native_goal": "NOT_VERIFIED",
        }

    def make_continuity_record(self, pending_effects=None):
        work = self.root / "work"
        work.mkdir(exist_ok=True)
        (work / "evidence.json").write_text(json.dumps({"status": "NOT_VERIFIED"}), "utf-8")
        record = work / "checkpoint.json"
        record.write_text(json.dumps({"continuity": self.continuity_item(pending_effects), "keep": "existing"}), "utf-8")
        return record

    def bind_continuity_scope(self):
        self.make_continuity_record()
        event = {"session_id": "engineering-test-thread", "agent_id": "bounded-test-agent"}
        h.continuity_save(self.root, self.state, event, "work/checkpoint.json", "continuity")

    def observe_patch_mutation(self):
        self.handle("PostToolUse", tool_name="apply_patch", tool_input={"command": "patch"}, tool_response={"exit_code": 0})

    def continuity_dispatch(self, mode, session="engineering-test-thread", include_record=True):
        params = {"mode": mode}
        if mode == "save" or include_record:
            params.update({"record": "work/checkpoint.json", "section": "continuity"})
        with mock.patch.dict(os.environ, {
            "CODEX_THREAD_ID": session,
            "CODEX_SESSION_ID": "",
            "CODEX_AGENT_ID": "bounded-test-agent",
        }):
            return eng.dispatch("continuity", params)

    def continuity_cli(self, mode, include_record=True):
        capture = type("StdoutCapture", (), {"buffer": io.BytesIO()})()
        params = {"mode": mode}
        if mode == "save" or include_record:
            params.update({"record": "work/checkpoint.json", "section": "continuity"})
        arguments = [str(ENGINEERING), "continuity", "--params", json.dumps(params)]
        with mock.patch.dict(os.environ, {
            "CODEX_THREAD_ID": "engineering-cli-thread",
            "CODEX_SESSION_ID": "",
            "CODEX_AGENT_ID": "cli-test-agent",
        }), mock.patch.object(sys, "argv", arguments), mock.patch.object(sys, "stdout", capture):
            self.assertEqual(eng.main(), 0)
        return json.loads(capture.buffer.getvalue().decode("utf-8"))

    def bind_verification_scope(self, source_paths=None, owner="C4", pending_effects=None):
        record = self.make_continuity_record(pending_effects)
        payload = json.loads(record.read_text("utf-8"))
        payload["continuity"]["owner"] = owner
        if source_paths is not None:
            payload["continuity"]["source_paths"] = list(source_paths)
        record.write_text(json.dumps(payload), "utf-8")
        self.continuity_dispatch("save")

    def run_verification(self, kind, argv, timeout_seconds=10):
        with mock.patch.dict(os.environ, {
            "CODEX_THREAD_ID": "engineering-test-thread",
            "CODEX_SESSION_ID": "",
            "CODEX_AGENT_ID": "bounded-test-agent",
        }):
            return eng.dispatch("verification_run", {
                "kind": kind, "argv": argv, "timeout_seconds": timeout_seconds,
            })

    def engineering_state(self):
        event = {"session_id": "engineering-test-thread", "agent_id": "bounded-test-agent"}
        path = eng.HOOKS.state_file(event, self.root)
        return path, json.loads(path.read_text("utf-8"))

    def pytest_receipt_is_current(self, accepted, scope):
        event = {"session_id": "engineering-test-thread", "agent_id": "bounded-test-agent"}
        _, state = self.engineering_state()
        try:
            binding = eng._verification_continuity_binding(
                state, event, scope, accepted["pytest_owner_approved_paths"]
            )
        except (OSError, ValueError, KeyError, TypeError, RuntimeError):
            return False
        paths = sorted({*scope, *accepted["additional_paths"]})
        current = h.snapshot(self.root)
        policy_path = str(h.VERIFICATION_POLICY_PATH)
        receipt = {
            "runner": "engineering_cli", "kind": "test", "status": "SUCCEEDED",
            "continuity_binding_stable": True,
            "continuity_binding_start": binding,
            "continuity_binding_fingerprint_end": binding["fingerprint"],
            "head_end": current["head"], "verification_paths": paths,
            "source_pins_end": h.continuity_pins(self.root, paths),
            "policy_pins_end": h.continuity_pins(self.root, [policy_path]),
            "package_root": None, "pytest_review_receipt": accepted["pytest_review_receipt"],
            "pytest_active_conftest_paths": accepted["pytest_active_conftest_paths"],
            "pytest_selected_config": accepted["pytest_selected_config"],
            "pytest_owner_approved_paths": accepted["pytest_owner_approved_paths"],
            "command_argv": accepted["argv"],
            "fingerprint": h.verification_fingerprint(self.root, state, current),
        }
        return h.verification_receipt_current(self.root, state, receipt, current)

    def make_verification_probe(self):
        tests = self.root / ".codex" / "tests"
        tests.mkdir(parents=True, exist_ok=True)
        path = tests / "test_verification_probe.py"
        path.write_text(
            "import time\nimport unittest\n\n"
            "class VerificationProbe(unittest.TestCase):\n"
            "    def test_runner_probe(self):\n"
            "        time.sleep(2)\n",
            "utf-8",
        )
        return path

    def make_flutter_verification_fixture(self):
        app = self.root / "app"
        (app / "lib").mkdir(parents=True)
        (app / "test").mkdir(parents=True)
        (app / "pubspec.yaml").write_text("name: runner_fixture\n", "utf-8")
        source = app / "lib" / "main.dart"
        source.write_text("void main() {}\n", "utf-8")
        test_file = app / "test" / "widget_test.dart"
        test_file.write_text("void main() {}\n", "utf-8")
        return source, test_file

    def test_continuity_save_read_pins_existing_record(self):
        self.make_continuity_record()
        self.continuity_dispatch("save")
        result = self.continuity_dispatch("read")
        self.assertEqual(result["status"], "PINNED_CONTEXT")
        self.assertEqual(result["context"]["owner"], "C4")
        self.assertFalse(result["dispatch_authorized"])
        self.assertFalse(result["product_accepted"])

    def test_continuity_narrative_retains_24000_unicode_character_budget(self):
        record = self.make_continuity_record()
        payload = json.loads(record.read_text("utf-8"))
        payload["continuity"]["objective"] = "任务" * 3000
        payload["continuity"]["native_goal"] = "结果" * 3000
        record.write_text(json.dumps(payload, ensure_ascii=False), "utf-8")
        item = h.continuity_record(self.root, "work/checkpoint.json", "continuity")
        self.assertGreater(len(json.dumps(item, ensure_ascii=False).encode("utf-8")), 24_000)

    def test_continuity_save_and_lookup_normalize_record_path_spellings(self):
        record, payload = self.delivery_fixture()
        event = self.delivery_event
        fresh_state = {
            "last_prompt_hash": self.state["last_prompt_hash"],
            "turn_id": self.state["turn_id"],
        }
        h.continuity_save(self.root, fresh_state, event, "./work/checkpoint.json", "continuity")
        self.assertEqual(fresh_state["continuity"]["record"], "work/checkpoint.json")
        fresh_state["continuity"]["record"] = r".\work\checkpoint.json"
        fresh_state["delivery_guard"]["record"] = r".\work\checkpoint.json"
        h.continuity_read(self.root, fresh_state, event)
        self.assertEqual(fresh_state["continuity"]["record"], "work/checkpoint.json")

        self.close_delivery_fixture(record, payload)
        self.state["continuity"]["record"] = r".\work\checkpoint.json"
        self.state["delivery_guard"]["record"] = r".\work\checkpoint.json"
        self.assertEqual(self.delivery_stop(), {})

    def test_continuity_paths_reject_windows_escapes_and_private_segments(self):
        for value in (
            r"C:\work\checkpoint.json", r"C:work\checkpoint.json",
            r"\\server\share\checkpoint.json", r"\work\checkpoint.json",
            r"work\..\checkpoint.json", r"work\data\checkpoint.json",
            r"work\profiles\checkpoint.json", r"work\.env\checkpoint.json",
            r"work\secret.json", r"work\report.txt:stream.txt",
        ):
            with self.subTest(path=value), self.assertRaises(ValueError):
                h.continuity_path(self.root, value)

    def test_continuity_authority_change_requires_rebind_before_runner(self):
        self.bind_verification_scope(["sample.py"])
        architecture = self.root / "00-GOVERNANCE" / "LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md"
        architecture.write_text("# Changed current architecture\n", "utf-8")
        with mock.patch.object(eng, "_execute_verification_process") as execute, self.assertRaisesRegex(ValueError, "authority"):
            self.run_verification("compile", ["python", "-X", "utf8", "-m", "py_compile", "sample.py"])
        execute.assert_not_called()

    def test_continuity_save_pins_astro_css_and_log_then_reconciles_changes(self):
        sources = {
            "website/continuity-sample.astro": "---\nconst title = 'F';\n---\n<h1>{title}</h1>\n",
            "website/continuity-sample.css": ".page { color: #243; }\n",
            "work/frontend-build.log": "frontend build result: NOT_VERIFIED\n",
        }
        for relative, content in sources.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, "utf-8")

        record = self.make_continuity_record()
        payload = json.loads(record.read_text("utf-8"))
        payload["continuity"]["owner"] = "F"
        payload["continuity"]["objective"] = "Complete the existing frontend outcome with saved, responsive artifacts and verification."
        payload["continuity"]["source_paths"] = list(sources)
        record.write_text(json.dumps(payload), "utf-8")

        saved = self.continuity_dispatch("save")
        self.assertEqual(saved["status"], "PINNED_CONTEXT")
        event = {"session_id": "engineering-test-thread", "agent_id": "bounded-test-agent"}
        state_path = eng.HOOKS.state_file(event, self.root)
        state = json.loads(state_path.read_text("utf-8"))
        self.assertTrue(set(sources).issubset(state["continuity"]["pins"]))

        for relative, content in sources.items():
            (self.root / relative).write_text(content + "updated\n", "utf-8")
        result = self.continuity_dispatch("read")
        self.assertEqual(result["status"], "RECONCILE_REQUIRED")
        self.assertEqual(set(result["changed_paths"]), set(sources))

    def test_continuity_cli_saves_and_reads_existing_record(self):
        self.make_continuity_record()
        self.continuity_cli("save")
        result = self.continuity_cli("read", include_record=False)
        self.assertEqual(result["status"], "PINNED_CONTEXT")
        self.assertEqual(result["context"]["owner"], "C4")

    def test_continuity_mode_only_read_does_not_rewrite_engineering_state(self):
        self.make_continuity_record()
        self.continuity_dispatch("save")
        event = {"session_id": "engineering-test-thread", "agent_id": "bounded-test-agent"}
        state_path = eng.HOOKS.state_file(event, self.root)
        before = state_path.read_bytes()
        result = self.continuity_dispatch("read", include_record=False)
        self.assertEqual(result["status"], "PINNED_CONTEXT")
        self.assertEqual(state_path.read_bytes(), before)

    def test_continuity_new_session_cannot_reuse_another_session_checkpoint(self):
        self.make_continuity_record()
        self.continuity_dispatch("save", session="session-original")
        result = self.continuity_dispatch("read", session="session-new", include_record=False)
        self.assertEqual(result["status"], "READBACK_REQUIRED")
        self.assertNotIn("context", result)

    def test_continuity_new_prompt_hash_requires_reconciliation(self):
        self.make_continuity_record()
        self.continuity_dispatch("save")
        event = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "engineering-test-thread",
            "agent_id": "bounded-test-agent",
            "prompt": "A new user request arrived after this checkpoint.",
        }
        state_path = eng.HOOKS.state_file(event, self.root)
        state = json.loads(state_path.read_text("utf-8"))
        eng.HOOKS.handle(event, self.root, state)
        eng.HOOKS.save(state_path, state)
        result = self.continuity_dispatch("read", include_record=False)
        self.assertEqual(result["status"], "RECONCILE_REQUIRED")
        self.assertIn("NEW_MESSAGE_SINCE_CHECKPOINT", result["reasons"])

    def test_continuity_cached_origin_main_change_requires_reconciliation(self):
        self.make_continuity_record()
        head = self.git("rev-parse", "HEAD").strip()
        self.git("update-ref", "refs/remotes/origin/main", head)
        self.continuity_dispatch("save")
        tree = self.git("rev-parse", "HEAD^{tree}").strip()
        alternate = self.git("commit-tree", tree, "-m", "alternate remote ref fixture").strip()
        self.git("update-ref", "refs/remotes/origin/main", alternate)
        result = self.continuity_dispatch("read", include_record=False)
        self.assertEqual(result["status"], "RECONCILE_REQUIRED")
        self.assertIn("CACHED_ORIGIN_CHANGED", result["reasons"])

    def test_continuity_optional_read_record_and_section_must_match_binding(self):
        self.make_continuity_record()
        self.continuity_dispatch("save")
        other = self.root / "work" / "other.json"
        other.write_text("{}", "utf-8")
        with mock.patch.dict(os.environ, {
            "CODEX_THREAD_ID": "engineering-test-thread",
            "CODEX_SESSION_ID": "",
            "CODEX_AGENT_ID": "bounded-test-agent",
        }):
            with self.assertRaises(ValueError):
                eng.dispatch("continuity", {"mode": "read", "record": "work/checkpoint.json"})
            with self.assertRaises(ValueError):
                eng.dispatch("continuity", {"mode": "read", "record": "work/other.json", "section": "continuity"})

    def test_continuity_reconciles_scope_source_change(self):
        self.make_continuity_record()
        self.continuity_dispatch("save")
        (self.root / "sample.py").write_text("value = 99\n", "utf-8")
        result = self.continuity_dispatch("read")
        self.assertEqual(result["status"], "RECONCILE_REQUIRED")
        self.assertIn("sample.py", result["changed_paths"])

    def test_continuity_stop_ignores_other_owner_dirty_mutation(self):
        self.assertEqual(self.git("status", "--porcelain").strip(), "")
        self.assertEqual(self.state["baseline"]["files"], {})
        self.bind_continuity_scope()
        (self.root / "other_owner.py").write_text("other_owner_value = 1\n", "utf-8")
        self.observe_patch_mutation()
        self.assertTrue(self.state["mutation_observed"])
        self.assertEqual(self.handle("Stop"), {})

    def test_continuity_stop_requires_checks_for_bound_source_dirty_change(self):
        self.bind_continuity_scope()
        (self.root / "sample.py").write_text("value = 99\n", "utf-8")
        self.observe_patch_mutation()
        result = self.handle("Stop")
        self.assertEqual(result.get("decision"), "block")
        self.assertEqual(self.state["verification_status"], "BLOCKED_MISSING_SUCCESSFUL_CHECK")

    def test_continuity_stop_detects_committed_bound_source_with_clean_tree(self):
        baseline_head = self.state["baseline"]["head"]
        self.bind_continuity_scope()
        (self.root / "sample.py").write_text("value = 99\n", "utf-8")
        self.git("add", "sample.py", "work/checkpoint.json", "work/evidence.json")
        self.git("commit", "-qm", "change bound source")
        self.assertEqual(self.git("status", "--porcelain").strip(), "")
        self.handle("PostToolUse", tool_name="Bash", tool_input={"command": "git commit"}, tool_response={"exit_code": 0})
        self.assertTrue(self.state["mutation_observed"])
        self.assertNotEqual(self.git("rev-parse", "HEAD").strip(), baseline_head)
        self.assertIn("sample.py", h.changed_scope_paths(self.root, self.state, h.snapshot(self.root)))
        result = self.handle("Stop")
        self.assertEqual(result.get("decision"), "block")
        self.assertEqual(self.state["verification_status"], "BLOCKED_MISSING_SUCCESSFUL_CHECK")

    def test_continuity_stop_ignores_commit_outside_bound_scope(self):
        baseline_head = self.state["baseline"]["head"]
        self.bind_continuity_scope()
        (self.root / "other_owner.py").write_text("other_owner_value = 1\n", "utf-8")
        self.git("add", "other_owner.py", "work/checkpoint.json", "work/evidence.json")
        self.git("commit", "-qm", "change another owner source")
        self.assertEqual(self.git("status", "--porcelain").strip(), "")
        self.handle("PostToolUse", tool_name="Bash", tool_input={"command": "git commit"}, tool_response={"exit_code": 0})
        self.assertTrue(self.state["mutation_observed"])
        self.assertNotEqual(self.git("rev-parse", "HEAD").strip(), baseline_head)
        self.assertEqual(h.changed_scope_paths(self.root, self.state, h.snapshot(self.root)), set())
        self.assertEqual(self.handle("Stop"), {})

    def test_continuity_reconciles_record_change(self):
        record = self.make_continuity_record()
        self.continuity_dispatch("save")
        payload = json.loads(record.read_text("utf-8"))
        payload["continuity"]["next_action"] = "Changed after the saved checkpoint."
        record.write_text(json.dumps(payload), "utf-8")
        result = self.continuity_dispatch("read")
        self.assertEqual(result["status"], "RECONCILE_REQUIRED")
        self.assertIn("work/checkpoint.json", result["changed_paths"])

    def bind_scope_and_record_targeted_check(self):
        self.make_continuity_record()
        event = {"session_id": "engineering-test-thread", "agent_id": "bounded-test-agent"}
        h.continuity_save(self.root, self.state, event, "work/checkpoint.json", "continuity")
        check_event = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "python -m py_compile sample.py"},
            "tool_response": {"exit_code": 0},
        }
        h.handle(check_event, self.root, self.state)
        return self.state["receipts"][-1]["fingerprint"]

    def test_continuity_bound_targeted_check_ignores_other_owner_but_tracks_scope_source(self):
        original_fingerprint = self.bind_scope_and_record_targeted_check()
        (self.root / "other_owner.py").write_text("other_owner_value = 1\n", "utf-8")
        after_other_owner = h.verification_fingerprint(self.root, self.state, h.snapshot(self.root))
        self.assertEqual(after_other_owner, original_fingerprint)
        self.assertTrue(any(receipt["fingerprint"] == after_other_owner for receipt in self.state["receipts"]))

        (self.root / "sample.py").write_text("value = 100\n", "utf-8")
        after_bound_source = h.verification_fingerprint(self.root, self.state, h.snapshot(self.root))
        self.assertNotEqual(after_bound_source, original_fingerprint)
        self.assertFalse(any(receipt["fingerprint"] == after_bound_source for receipt in self.state["receipts"]))

    def test_continuity_bound_targeted_check_is_invalidated_by_policy_change(self):
        original_fingerprint = self.bind_scope_and_record_targeted_check()
        policy_path = self.root / h.VERIFICATION_POLICY_PATH
        policy = json.loads(policy_path.read_text("utf-8"))
        policy["verification_policy"]["fixture_revision"] = 2
        policy_path.write_text(json.dumps(policy), "utf-8")
        after_policy_change = h.verification_fingerprint(self.root, self.state, h.snapshot(self.root))
        self.assertNotEqual(after_policy_change, original_fingerprint)
        self.assertFalse(any(receipt["fingerprint"] == after_policy_change for receipt in self.state["receipts"]))

    def test_unknown_pending_effect_is_retained_without_dispatch(self):
        pending = ["operation-unknown-7 | UNKNOWN | work/receipts/op-7.json | NOT_VERIFIED"]
        self.make_continuity_record(pending)
        self.continuity_dispatch("save")
        original_run = eng.HOOKS.subprocess.run
        commands = []

        def track_run(args, *positional, **keywords):
            commands.append(args)
            return original_run(args, *positional, **keywords)

        with mock.patch.object(eng.HOOKS.subprocess, "run", side_effect=track_run):
            result = self.continuity_dispatch("read")
        self.assertEqual(result["status"], "RECONCILE_REQUIRED")
        self.assertEqual(result["context"]["pending_effects"], pending)
        self.assertFalse(result["automatic_effect_replay"])
        self.assertFalse(result["dispatch_authorized"])
        self.assertTrue(commands)
        self.assertTrue(all(args[0] == "git" for args in commands))

    def test_continuity_rejects_non_work_or_unknown_params(self):
        self.make_continuity_record()
        with mock.patch.dict(os.environ, {"CODEX_THREAD_ID": "engineering-test-thread", "CODEX_SESSION_ID": ""}):
            with self.assertRaises(ValueError):
                eng.dispatch("continuity", {"mode": "read", "record": "AGENTS.md", "section": "continuity"})
            with self.assertRaises(ValueError):
                eng.dispatch("continuity", {"mode": "read", "record": "work/checkpoint.json", "section": "continuity", "extra": True})

    def test_verification_runner_records_real_zero_exit_and_native_unknown_cannot_overwrite(self):
        self.bind_verification_scope()
        result = self.run_verification("compile", ["python", "-X", "utf8", "-m", "py_compile", "sample.py"])
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(result["process_exit_code"], 0)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["head_start"], result["head_end"])
        self.assertEqual(result["source_pins_start"], result["source_pins_end"])

        state_path, state = self.engineering_state()
        receipt = state["receipts"][-1]
        self.assertEqual(receipt["runner"], "engineering_cli")
        self.assertTrue(h.verification_receipt_current(self.root, state, receipt, h.snapshot(self.root)))
        receipt_ids = [item.get("receipt_id") for item in state["receipts"]]
        state["compile_envelope_probe"] = "temporary diagnostic value"
        state["compile_event_probe"] = {"temporary": "event data"}
        runner_command = "python .codex/engineering.py verification_run --params '{}'"
        h.handle({
            "hook_event_name": "PostToolUse", "tool_name": "Bash",
            "tool_input": {"command": runner_command}, "tool_response": "",
        }, self.root, state)
        self.assertEqual([item.get("receipt_id") for item in state["receipts"]], receipt_ids)
        self.assertNotIn("compile_envelope_probe", state)
        self.assertNotIn("compile_event_probe", state)
        self.assertFalse(state["last_shell_response_shape"]["exit_status_available"])

        state_path.write_text(json.dumps(state), "utf-8")
        (self.root / "sample.py").write_text("value = 2\n", "utf-8")
        state = json.loads(state_path.read_text("utf-8"))
        self.assertFalse(h.verification_receipt_current(self.root, state, state["receipts"][-1], h.snapshot(self.root)))

    def test_verification_runner_records_nonzero_process_exit(self):
        self.bind_verification_scope()
        (self.root / "sample.py").write_text("if :\n", "utf-8")
        result = self.run_verification("compile", ["python", "-X", "utf8", "-m", "py_compile", "sample.py"])
        self.assertEqual(result["status"], "FAILED")
        self.assertNotEqual(result["process_exit_code"], 0)
        self.assertNotEqual(result["exit_code"], 0)
        _, state = self.engineering_state()
        self.assertEqual(state["receipts"][-1]["process_exit_code"], result["process_exit_code"])

    def test_verification_runner_rejects_owner_record_drift_before_execution(self):
        self.bind_verification_scope()
        record = self.root / "work" / "checkpoint.json"
        payload = json.loads(record.read_text("utf-8"))
        payload["continuity"]["objective"] = "A new task objective that was not reviewed in the binding."
        payload["continuity"]["remaining"] = ["New unreviewed work item."]
        payload["continuity"]["pending_effects"] = ["C6 publication receipt remains unresolved."]
        record.write_text(json.dumps(payload), "utf-8")
        with mock.patch.object(eng, "_execute_verification_process") as execute, self.assertRaisesRegex(ValueError, "reread and rebind"):
            self.run_verification("compile", ["python", "-X", "utf8", "-m", "py_compile", "sample.py"])
        execute.assert_not_called()

    def test_verification_runner_rejects_new_prompt_before_execution(self):
        self.bind_verification_scope()
        state_path, state = self.engineering_state()
        state["last_prompt_hash"] = "new-unreviewed-prompt-hash"
        h.save(state_path, state)
        with mock.patch.object(eng, "_execute_verification_process") as execute, self.assertRaisesRegex(ValueError, "new prompt"):
            self.run_verification("compile", ["python", "-X", "utf8", "-m", "py_compile", "sample.py"])
        execute.assert_not_called()

    def test_verification_runner_retains_pending_effect_without_replay(self):
        pending = ["C6 publication receipt: work/product-closure-20261011/context-continuity/status.json; UNKNOWN"]
        self.bind_verification_scope(pending_effects=pending)
        result = self.run_verification("compile", ["python", "-X", "utf8", "-m", "py_compile", "sample.py"])
        self.assertEqual(result["status"], "SUCCEEDED")
        _, state = self.engineering_state()
        receipt = state["receipts"][-1]
        self.assertEqual(receipt["continuity_binding_start"]["pending_effects"], pending)
        self.assertEqual(receipt["continuity_binding_end"]["pending_effects"], pending)
        self.assertTrue(receipt["continuity_binding_start"]["pending_effects_retained_only"])
        self.assertFalse(receipt["continuity_binding_start"]["pending_effects_replayed"])
        self.assertTrue(receipt["continuity_binding_stable"])

    def test_verification_runner_timeout_is_not_a_pass(self):
        probe = self.make_verification_probe()
        probe_rel = probe.relative_to(self.root).as_posix()
        self.bind_verification_scope(["sample.py", probe_rel])
        command = ["python", "-X", "utf8", "-m", "unittest", "discover", "-s", ".codex/tests",
                   "-p", "test_verification_probe.py", "-k", "test_runner_probe", "-v"]
        result = self.run_verification("test", command, timeout_seconds=1)
        self.assertEqual(result["status"], "TIMED_OUT_PROCESS_TREE_UNVERIFIED")
        self.assertTrue(result["timed_out"])
        self.assertFalse(result["process_tree_exit_verified"])
        self.assertEqual(result["timeout_recovery_state"], "DIRECT_TOOL_PROCESS_TERMINATED_DESCENDANTS_UNVERIFIED")
        self.assertNotEqual(result["exit_code"], 0)
        _, state = self.engineering_state()
        self.assertTrue(state["receipts"][-1]["executed"])
        self.assertIsNotNone(state["receipts"][-1]["head_end"])
        self.assertIsNotNone(state["receipts"][-1]["source_pins_end"])

    def test_verification_runner_source_drift_blocks_zero_process_exit(self):
        probe = self.make_verification_probe()
        probe_rel = probe.relative_to(self.root).as_posix()
        self.bind_verification_scope(["sample.py", probe_rel])
        command = ["python", "-X", "utf8", "-m", "unittest", "discover", "-s", ".codex/tests",
                   "-p", "test_verification_probe.py", "-k", "test_runner_probe", "-v"]
        started = threading.Event()
        results = []
        errors = []
        execute = eng._execute_verification_process

        def tracked_execute(*args, **kwargs):
            started.set()
            return execute(*args, **kwargs)

        def run_check():
            try:
                results.append(self.run_verification("test", command, timeout_seconds=10))
            except Exception as error:
                logger.exception("Isolated verification thread failed")
                errors.append(error)

        with mock.patch.object(eng, "_execute_verification_process", side_effect=tracked_execute):
            worker = threading.Thread(target=run_check)
            worker.start()
            self.assertTrue(started.wait(5))
            time.sleep(0.2)
            (self.root / "sample.py").write_text("value = 88\n", "utf-8")
            worker.join(10)
        self.assertFalse(worker.is_alive())
        self.assertFalse(errors, errors)
        self.assertEqual(results[0]["process_exit_code"], 0)
        self.assertEqual(results[0]["status"], "SOURCE_CHANGED_DURING_RUN")
        self.assertIsNone(results[0]["exit_code"])
        self.assertFalse(results[0]["source_stable"])

    def test_verification_runner_skipped_target_is_not_a_pass(self):
        tests = self.root / ".codex" / "tests"
        tests.mkdir(parents=True, exist_ok=True)
        probe = tests / "test_verification_skipped.py"
        probe.write_text(
            "import unittest\n\n"
            "class SkippedProbe(unittest.TestCase):\n"
            "    @unittest.skip('not an executed check')\n"
            "    def test_skipped_probe(self):\n"
            "        self.fail('must not run')\n",
            "utf-8",
        )
        probe_rel = probe.relative_to(self.root).as_posix()
        self.bind_verification_scope(["sample.py", probe_rel])
        command = ["python", "-X", "utf8", "-m", "unittest", "discover", "-s", ".codex/tests",
                   "-p", "test_verification_skipped.py", "-k", "test_skipped_probe", "-v"]
        result = self.run_verification("test", command)
        self.assertEqual(result["process_exit_code"], 0)
        self.assertEqual(result["test_count"], 1)
        self.assertEqual(result["tests_passed"], 0)
        self.assertEqual(result["status"], "TEST_COUNT_MISMATCH")
        self.assertIsNone(result["exit_code"])

    def test_verification_runner_rejects_arbitrary_commands_before_execution(self):
        probe = self.make_verification_probe()
        self.bind_verification_scope(["sample.py"])
        with mock.patch.object(eng, "_execute_verification_process") as execute:
            with self.assertRaises(ValueError):
                self.run_verification("compile", ["python", "-c", "print('not allowed')"])
            with self.assertRaises(ValueError):
                self.run_verification("compile", ["python", "-X", "utf8", "-m", "py_compile", "other.py"])
            with self.assertRaisesRegex(ValueError, "bound Owner scope"):
                self.run_verification("test", ["python", "-X", "utf8", "-m", "unittest", "discover", "-s", ".codex/tests",
                                                 "-p", probe.name, "-k", "test_runner_probe", "-v"])
            with self.assertRaisesRegex(ValueError, "bound Owner scope"):
                self.run_verification("test", ["python", "-X", "utf8", "-m", "pytest", "-q", "--no-header",
                                                 "-p", "no:cacheprovider",
                                                 ".codex/tests/test_verification_probe.py::VerificationProbe::test_runner_probe"])
        execute.assert_not_called()

    def make_pytest_probe(self, contents="def test_runner_probe():\n    assert 2 + 2 == 4\n"):
        path = self.root / ".codex" / "tests" / "test_pytest_runner_probe.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, "utf-8")
        return path

    def make_reviewed_admission_sources(self, relative_paths):
        """Build isolated AST admission specimens, never business-success fixtures."""
        specimens = {
            "tests/conftest.py": "import socket\n",
            "tests/test_saved_work_pptx_exports.py": (
                "import socket\n"
                "def test_saved_work_pptx_is_editable_and_preserves_every_section_in_memory():\n"
                "    raise AssertionError('Admission specimen must never execute as a product test')\n"
            ),
            "tests/test_business_approved_source_continuity.py": (
                "pytest_plugins = (\n"
                '    "tests.test_business_result_continuity",\n'
                '    "tests.test_saved_document_workflow",\n'
                ")\n"
                "def test_approved_source_survives_domain_save_revision_reopen_and_recovery():\n"
                "    raise AssertionError('Admission specimen must never execute as a product test')\n"
            ),
            "tests/test_business_result_continuity.py": (
                'pytest_plugins = ("tests.test_saved_document_workflow",)\n'
            ),
            "tests/test_saved_document_workflow.py": "import subprocess\n",
        }
        copied, registry = {}, {}
        for relative in relative_paths:
            raw = specimens[relative].encode("utf-8")
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
            copied[relative] = destination
            # Copy metadata for the intended dependency graph, but scope the test
            # hashes to the isolated bytes. Production review entries are untouched.
            review = json.loads(json.dumps(eng.PYTEST_SOURCE_REVIEW_RECEIPTS[relative]))
            review["sha256"] = eng.hashlib.sha256(raw).hexdigest()
            registry[relative] = review
        patcher = mock.patch.dict(eng.PYTEST_SOURCE_REVIEW_RECEIPTS, registry)
        patcher.start()
        self.addCleanup(patcher.stop)
        return copied

    def pytest_argv(self, path, node="test_runner_probe"):
        relative = path.relative_to(self.root).as_posix()
        return ["python", "-X", "utf8", "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider",
                f"{relative}::{node}"]

    def test_pytest_runner_executes_one_bound_literal_node(self):
        probe = self.make_pytest_probe()
        probe_rel = probe.relative_to(self.root).as_posix()
        self.bind_verification_scope(["sample.py", "pytest.ini", probe_rel])
        if importlib.util.find_spec("pytest") is None:
            self.skipTest("pytest is unavailable in this workspace runtime")
        result = self.run_verification("test", self.pytest_argv(probe), timeout_seconds=30)
        self.assertEqual(result["process_exit_code"], 0)
        self.assertEqual(result["test_count"], 1)
        self.assertEqual(result["tests_passed"], 1)
        self.assertEqual(result["status"], "SUCCEEDED")
        _state_path, state = self.engineering_state()
        receipt = state["receipts"][-1]
        self.assertIn("pytest.ini", receipt["verification_paths"])
        self.assertEqual(receipt["pytest_selected_config"], "pytest.ini")
        self.assertEqual(receipt["command_argv"][receipt["command_argv"].index("-c") + 1],
                         str((self.root / "pytest.ini").resolve()))
        self.assertEqual(receipt["command_argv"][receipt["command_argv"].index("--rootdir") + 1],
                         str(self.root.resolve()))
        self.assertEqual(receipt["requested_argv"], self.pytest_argv(probe))

    def test_pytest_root_quiet_addopts_keep_real_test_count_available(self):
        probe = self.make_pytest_probe()
        probe_rel = probe.relative_to(self.root).as_posix()
        (self.root / "pytest.ini").write_text(
            "[pytest]\naddopts = -q -p no:cacheprovider --strict-markers\n", "utf-8"
        )
        self.bind_verification_scope(["sample.py", "pytest.ini", probe_rel])
        if importlib.util.find_spec("pytest") is None:
            self.skipTest("pytest is unavailable in this workspace runtime")
        result = self.run_verification("test", self.pytest_argv(probe), timeout_seconds=30)
        self.assertEqual(result["process_exit_code"], 0)
        self.assertTrue(result["output_capture_complete"])
        self.assertEqual(result["test_count"], 1)
        self.assertEqual(result["tests_passed"], 1)
        self.assertEqual(result["status"], "SUCCEEDED")
        _, state = self.engineering_state()
        command = state["receipts"][-1]["command_argv"]
        self.assertIn("--verbosity=1", command)
        self.assertEqual(command[command.index("--rootdir") + 1], str(self.root.resolve()))

    def test_pytest_addopts_rejects_explicit_plugin_load_spellings(self):
        probe = self.make_pytest_probe()
        probe_rel = probe.relative_to(self.root).as_posix()
        scope = ["sample.py", "pytest.ini", probe_rel]
        configs = [
            "[pytest]\naddopts = -q -p unreviewed_plugin\n",
            "[pytest]\naddopts = -q -p=unreviewed_plugin\n",
            "[pytest]\naddopts = -q -punreviewed_plugin\n",
        ]
        for contents in configs:
            with self.subTest(contents=contents):
                (self.root / "pytest.ini").write_text(contents, "utf-8")
                self.bind_verification_scope(scope)
                with mock.patch.object(eng, "_execute_verification_process") as execute, self.assertRaisesRegex(ValueError, "explicit plugin control"):
                    self.run_verification("test", self.pytest_argv(probe))
                execute.assert_not_called()

    def test_pyproject_pytest_addopts_plugin_load_is_rejected(self):
        probe = self.make_pytest_probe()
        probe_rel = probe.relative_to(self.root).as_posix()
        pytest_ini = self.root / "pytest.ini"
        pytest_ini.unlink()
        pyproject = self.root / "pyproject.toml"
        pyproject.write_text(
            "[tool.pytest.ini_options]\naddopts = \"-q -p unreviewed_plugin\"\n", "utf-8"
        )
        scope = ["sample.py", "pyproject.toml", probe_rel]
        self.bind_verification_scope(scope)
        with mock.patch.object(eng, "_execute_verification_process") as execute, self.assertRaisesRegex(ValueError, "explicit plugin control"):
            self.run_verification("test", self.pytest_argv(probe))
        execute.assert_not_called()

    def test_pytest_native_toml_addopts_plugin_load_is_rejected(self):
        probe = self.make_pytest_probe()
        probe_rel = probe.relative_to(self.root).as_posix()
        pytest_ini = self.root / "pytest.ini"
        pytest_ini.unlink()
        pyproject = self.root / "pyproject.toml"
        pyproject.write_text(
            "[tool.pytest]\naddopts = [\"-q\", \"-p\", \"unreviewed_plugin\"]\n", "utf-8"
        )
        scope = ["sample.py", "pyproject.toml", probe_rel]
        self.bind_verification_scope(scope)
        with mock.patch.object(eng, "_pytest_version_tuple", return_value=(9, 0)), mock.patch.object(eng, "_execute_verification_process") as execute, self.assertRaisesRegex(ValueError, "explicit plugin control"):
            self.run_verification("test", self.pytest_argv(probe))
        execute.assert_not_called()

    def test_pytest_native_toml_config_addopts_parser(self):
        config = self.root / "pytest.toml"
        config.write_text("[pytest]\naddopts = [\"-q\", \"-p\", \"no:cacheprovider\"]\n", "utf-8")
        with mock.patch.object(eng, "_pytest_version_tuple", return_value=(9, 0)):
            self.assertEqual(eng._review_pytest_addopts(config), ["-q", "-p", "no:cacheprovider"])

    def test_pytest_stdout_claim_cannot_override_nonzero_process_exit(self):
        probe = self.make_pytest_probe(
            "def test_runner_probe():\n    print('9 passed')\n    assert False, 'controlled failure'\n"
        )
        probe_rel = probe.relative_to(self.root).as_posix()
        self.bind_verification_scope(["sample.py", "pytest.ini", probe_rel])
        if importlib.util.find_spec("pytest") is None:
            self.skipTest("pytest is unavailable in this workspace runtime")
        result = self.run_verification("test", self.pytest_argv(probe), timeout_seconds=30)
        self.assertEqual(result["process_exit_code"], 1)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["exit_code"], 1)

    def test_pytest_config_change_invalidates_receipt(self):
        probe = self.make_pytest_probe()
        probe_rel = probe.relative_to(self.root).as_posix()
        self.bind_verification_scope(["sample.py", "pytest.ini", probe_rel])
        if importlib.util.find_spec("pytest") is None:
            self.skipTest("pytest is unavailable in this workspace runtime")
        result = self.run_verification("test", self.pytest_argv(probe), timeout_seconds=30)
        self.assertEqual(result["status"], "SUCCEEDED")
        _, state = self.engineering_state()
        receipt = state["receipts"][-1]
        pytest_config = self.root / "pytest.ini"
        self.assertIn(pytest_config.relative_to(self.root).as_posix(), receipt["pytest_config_paths"])
        pytest_config.write_text("[pytest]\naddopts = -ra\n", "utf-8")
        self.assertFalse(h.verification_receipt_current(self.root, state, receipt, h.snapshot(self.root)))

    def test_pytest_higher_precedence_config_appearance_invalidates_receipt(self):
        probe = self.make_pytest_probe()
        probe_rel = probe.relative_to(self.root).as_posix()
        self.bind_verification_scope(["sample.py", "pytest.ini", probe_rel])
        if importlib.util.find_spec("pytest") is None:
            self.skipTest("pytest is unavailable in this workspace runtime")
        result = self.run_verification("test", self.pytest_argv(probe), timeout_seconds=30)
        self.assertEqual(result["status"], "SUCCEEDED")
        _, state = self.engineering_state()
        receipt = state["receipts"][-1]
        pytest_config = self.root / ".codex" / "tests" / "pytest.ini"
        pytest_config.parent.mkdir(parents=True, exist_ok=True)
        self.assertIn(pytest_config.relative_to(self.root).as_posix(), receipt["pytest_config_paths"])
        pytest_config.write_text("[pytest]\n", "utf-8")
        self.assertFalse(h.verification_receipt_current(self.root, state, receipt, h.snapshot(self.root)))

    def test_pytest_conftest_appearance_invalidates_receipt(self):
        probe = self.make_pytest_probe()
        probe_rel = probe.relative_to(self.root).as_posix()
        self.bind_verification_scope(["sample.py", "pytest.ini", probe_rel])
        if importlib.util.find_spec("pytest") is None:
            self.skipTest("pytest is unavailable in this workspace runtime")
        result = self.run_verification("test", self.pytest_argv(probe), timeout_seconds=30)
        self.assertEqual(result["status"], "SUCCEEDED")
        _, state = self.engineering_state()
        receipt = state["receipts"][-1]
        conftest = self.root / ".codex" / "tests" / "conftest.py"
        self.assertIn(conftest.relative_to(self.root).as_posix(), receipt["verification_paths"])
        conftest.write_text("# Newly appeared pytest setup\n", "utf-8")
        self.assertFalse(h.verification_receipt_current(self.root, state, receipt, h.snapshot(self.root)))

    def test_pytest_empty_or_skipped_selection_cannot_pass(self):
        command = [sys.executable, "-X", "utf8", "-m", "pytest", "-q", "--no-header",
                   "-p", "no:cacheprovider", ".codex/tests/test_probe.py::test_probe"]
        self.assertEqual(eng._test_execution_counts("test", command, b"no tests ran in 0.01s\n"), (None, None))
        self.assertEqual(eng._test_execution_counts("test", command, b"s [100%]\n1 skipped in 0.01s\n"), (1, 0))
        self.assertEqual(eng._test_execution_counts("test", command, b"x [100%]\n1 xfailed in 0.01s\n"), (1, 0))

    def test_pytest_network_and_training_source_requires_owner_review(self):
        samples = [
            "import requests\ndef test_runner_probe():\n    assert True\n",
            "import torch\ndef test_runner_probe():\n    model.train()\n",
        ]
        for contents in samples:
            with self.subTest(contents=contents):
                probe = self.make_pytest_probe(contents)
                probe_rel = probe.relative_to(self.root).as_posix()
                self.bind_verification_scope(["sample.py", "pytest.ini", probe_rel])
                with mock.patch.object(eng, "_execute_verification_process") as execute, self.assertRaisesRegex(ValueError, "owner review required"):
                    self.run_verification("test", self.pytest_argv(probe))
                execute.assert_not_called()

    def test_pytest_target_allowlist_requires_exact_source_scope(self):
        probe = self.make_pytest_probe()
        probe_rel = probe.relative_to(self.root).as_posix()
        self.bind_verification_scope(["sample.py", "pytest.ini", probe_rel])
        scope = ["sample.py", "pytest.ini", probe_rel]
        accepted = eng._allowlisted_verification("test", self.pytest_argv(probe), scope)
        self.assertIn(probe_rel, accepted["additional_paths"])
        self.assertIn("pytest.ini", accepted["pytest_config_paths"])
        self.assertIn("-c", accepted["argv"])
        self.assertEqual(accepted["argv"][accepted["argv"].index("--rootdir") + 1], str(self.root.resolve()))
        self.assertEqual(accepted["pytest_selected_config"], "pytest.ini")
        self.assertEqual(accepted["argv"][-1], f"{probe_rel}::test_runner_probe")
        with self.assertRaisesRegex(ValueError, "exact function"):
            eng._allowlisted_verification("test", self.pytest_argv(probe, "test_runner_probe[case]"),
                                          scope)

    def test_pytest_uses_effective_scoped_config_and_pins_non_pytest_candidates(self):
        probe = self.make_pytest_probe()
        probe_rel = probe.relative_to(self.root).as_posix()
        nested_pyproject = self.root / ".codex" / "tests" / "pyproject.toml"
        nested_pyproject.write_text("[project]\nname = 'not-pytest-config'\n", "utf-8")
        scope = ["sample.py", "pytest.ini", probe_rel]
        self.bind_verification_scope(scope)

        accepted = eng._allowlisted_verification("test", self.pytest_argv(probe), scope)
        receipt = accepted["pytest_review_receipt"]
        self.assertEqual(receipt["selected_config"]["path"], "pytest.ini")
        self.assertEqual(receipt["config_candidate_pins"][".codex/tests/pyproject.toml"],
                         eng.hashlib.sha256(nested_pyproject.read_bytes()).hexdigest())
        self.assertEqual(receipt["config_candidate_pins"][".codex/tests/pytest.ini"], "ABSENT")
        self.assertEqual(accepted["argv"][accepted["argv"].index("-c") + 1], str((self.root / "pytest.ini").resolve()))
        self.assertEqual(accepted["argv"][accepted["argv"].index("--rootdir") + 1], str(self.root.resolve()))
        with self.assertRaisesRegex(ValueError, "effective pytest configuration must be in the bound Owner scope"):
            eng._allowlisted_verification("test", self.pytest_argv(probe), ["sample.py", probe_rel])

    def test_pytest_source_authority_task_record_and_evidence_cannot_change_as_source(self):
        protected_paths = ["AGENTS.md", "work/checkpoint.json", "work/evidence.json"]
        for protected in protected_paths:
            with self.subTest(protected=protected):
                probe = self.make_pytest_probe()
                probe_rel = probe.relative_to(self.root).as_posix()
                scope = ["sample.py", "pytest.ini", probe_rel, protected]
                self.bind_verification_scope(scope)
                path = self.root / protected
                if protected == "work/checkpoint.json":
                    payload = json.loads(path.read_text("utf-8"))
                    payload["keep"] = "changed after Owner checkpoint"
                    path.write_text(json.dumps(payload), "utf-8")
                elif protected == "work/evidence.json":
                    payload = json.loads(path.read_text("utf-8"))
                    payload["status"] = "changed after Owner checkpoint"
                    path.write_text(json.dumps(payload), "utf-8")
                else:
                    path.write_bytes(path.read_bytes() + b"\nchanged after Owner checkpoint\n")
                with mock.patch.object(eng, "_execute_verification_process") as execute, self.assertRaisesRegex(ValueError, "Owner task, authority, evidence"):
                    self.run_verification("test", self.pytest_argv(probe))
                execute.assert_not_called()

    def test_c5_reviewed_admission_fixture_is_owner_and_hash_bound(self):
        target_rel = "tests/test_saved_work_pptx_exports.py"
        conftest_rel = "tests/conftest.py"
        copied = self.make_reviewed_admission_sources([target_rel, conftest_rel])
        scope = ["pytest.ini", conftest_rel, target_rel]
        self.bind_verification_scope(scope, owner="C5")
        selection = f"{target_rel}::test_saved_work_pptx_is_editable_and_preserves_every_section_in_memory"
        approved = eng._allowlisted_verification("test", self.pytest_argv(copied[target_rel], selection.split("::", 1)[1]),
                                                  scope, owner="C5")
        receipt = approved["pytest_review_receipt"]
        reviews = {value["path"]: value for value in receipt["reviewed_sources"]}
        self.assertEqual(reviews[conftest_rel]["sha256"], eng.hashlib.sha256(copied[conftest_rel].read_bytes()).hexdigest())
        self.assertEqual(reviews[conftest_rel]["purpose"],
                         "Reviewed autouse guard blocks public TCP connections while allowing loopback and private targets.")
        self.assertEqual(reviews[target_rel]["purpose"],
                         "Reviewed in-memory PPTX export tests patch socket.create_connection to fail and assert no network access.")
        self.assertEqual(receipt["fixture_dependency_edges"], [])
        self.assertTrue(self.pytest_receipt_is_current(approved, scope))
        self.assertIn("ZBC_ALLOW_NETWORK", eng._verification_process_environment(
            "test", approved["argv"], Path(self.temp.name) / "cache"
        ))

        wrong_owner_scope = scope
        with self.assertRaisesRegex(ValueError, "owner review required"):
            eng._allowlisted_verification("test", self.pytest_argv(copied[target_rel], selection.split("::", 1)[1]),
                                          wrong_owner_scope, owner="C4")

        copied[target_rel].write_text(copied[target_rel].read_text("utf-8") + "\n# changed hash\n", "utf-8")
        self.assertFalse(self.pytest_receipt_is_current(approved, scope))
        with self.assertRaisesRegex(ValueError, "owner review required"):
            eng._allowlisted_verification("test", self.pytest_argv(copied[target_rel], selection.split("::", 1)[1]),
                                          scope, owner="C5")

    def test_c4_socket_guard_review_is_owner_and_hash_specific(self):
        conftest_rel = "tests/conftest.py"
        copied = self.make_reviewed_admission_sources([conftest_rel])[conftest_rel]
        raw = copied.read_bytes()
        review = eng._pytest_source_review(copied, self.root, "C4", raw)
        self.assertEqual(review["sha256"], eng.hashlib.sha256(raw).hexdigest())
        self.assertEqual(review["allowed_imports"], ["socket"])
        self.assertIn("database-copy isolation", review["purpose"])
        self.assertIsNone(eng._pytest_source_review(copied, self.root, "C4", raw + b"\n# changed\n"))

    def test_c3_reviewed_pytest_plugins_pin_recursive_fixture_dependency_chain(self):
        paths = [
            "tests/conftest.py",
            "tests/test_business_approved_source_continuity.py",
            "tests/test_business_result_continuity.py",
            "tests/test_saved_document_workflow.py",
        ]
        copied = self.make_reviewed_admission_sources(paths)
        scope = ["pytest.ini", *paths]
        self.bind_verification_scope(scope, owner="C3")
        target_rel = "tests/test_business_approved_source_continuity.py"
        target = copied[target_rel]
        accepted = eng._allowlisted_verification(
            "test",
            self.pytest_argv(target, "test_approved_source_survives_domain_save_revision_reopen_and_recovery"),
            scope,
            owner="C3",
        )
        receipt = accepted["pytest_review_receipt"]
        reviews = {value["path"]: value for value in receipt["reviewed_sources"]}
        self.assertEqual(set(reviews), set(paths))
        edges = {(edge["declared_by"], edge["module"], edge["path"]) for edge in receipt["fixture_dependency_edges"]}
        self.assertEqual(edges, {
            (target_rel, "tests.test_business_result_continuity", "tests/test_business_result_continuity.py"),
            (target_rel, "tests.test_saved_document_workflow", "tests/test_saved_document_workflow.py"),
            ("tests/test_business_result_continuity.py", "tests.test_saved_document_workflow",
             "tests/test_saved_document_workflow.py"),
        })
        for path in paths:
            self.assertEqual(reviews[path]["sha256"], eng.hashlib.sha256(copied[path].read_bytes()).hexdigest())
            self.assertTrue(reviews[path]["purpose"])
        self.assertIn("pytest.ini", accepted["pytest_owner_approved_paths"])
        self.assertIn("tests/conftest.py", accepted["pytest_owner_approved_paths"])
        self.assertTrue(self.pytest_receipt_is_current(accepted, scope))

        copied[target_rel].write_text(copied[target_rel].read_text("utf-8").replace(
            '"tests.test_saved_document_workflow",', '"tests.unknown_fixture_plugin",', 1), "utf-8")
        self.assertFalse(self.pytest_receipt_is_current(accepted, scope))
        with self.assertRaisesRegex(ValueError, "exact owner-reviewed fixture dependency"):
            eng._allowlisted_verification(
                "test", self.pytest_argv(target, "test_approved_source_survives_domain_save_revision_reopen_and_recovery"),
                scope, owner="C3",
            )

    def test_pytest_runner_clears_inherited_plugin_and_network_overrides(self):
        for key, expected in (
            ("core.fsmonitor", "false"), ("gc.auto", "0"),
            ("maintenance.auto", "false"), ("gc.autoDetach", "false"),
            ("maintenance.autoDetach", "false"),
        ):
            self.assertEqual(self.git("config", "--local", "--get", key).strip(), expected)
        command = [sys.executable, "-X", "utf8", "-m", "pytest", "-q"]
        with mock.patch.dict(os.environ, {
            "PYTEST_ADDOPTS": "-k unsafe",
            "PYTEST_PLUGINS": "unreviewed.plugin",
            "ZBC_ALLOW_NETWORK": "1",
        }, clear=False):
            env = eng._verification_process_environment("test", command, Path(self.temp.name) / "cache")
        self.assertEqual(env["ZBC_ALLOW_NETWORK"], "0")
        self.assertNotIn("PYTEST_ADDOPTS", env)
        self.assertNotIn("PYTEST_PLUGINS", env)
        self.assertEqual(env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"], "1")

    def test_verification_runner_accepts_scoped_f_static_and_existing_flutter_commands(self):
        source, widget_test = self.make_flutter_verification_fixture()
        source_rel = source.relative_to(self.root).as_posix()
        test_rel = widget_test.relative_to(self.root).as_posix()
        self.bind_verification_scope([source_rel, test_rel], owner="F")

        dart_prefix = ["D:/installed/dart.exe"]
        flutter_prefix = ["D:/installed/dart.exe", "--disable-dart-dev", "D:/installed/flutter_tools.snapshot"]
        with mock.patch.object(eng, "_resolve_tool_argv", side_effect=lambda tool, args: [*(dart_prefix if tool == "dart" else flutter_prefix), *args]):
            dart = eng._allowlisted_verification("static", ["dart", "analyze", source_rel], [source_rel])
            self.assertEqual(dart["argv"], [*dart_prefix, "analyze", "lib/main.dart"])
            self.assertEqual(dart["cwd"], source.parents[1])
            flutter_analyze = eng._allowlisted_verification("static", ["flutter", "analyze", "--no-pub"], [source_rel])
            self.assertEqual(flutter_analyze["argv"], [*flutter_prefix, "analyze", "--no-pub"])
            self.assertEqual(flutter_analyze["package_root"], "app")
            build = eng._allowlisted_verification(
                "compile", ["flutter", "build", "web", "--release", "--no-web-resources-cdn", "--no-pub"], [source_rel]
            )
            self.assertEqual(build["argv"], [*flutter_prefix, "build", "web", "--release", "--no-web-resources-cdn", "--no-pub"])
            widget = eng._allowlisted_verification(
                "test", ["flutter", "test", "--no-pub", test_rel, "--name", "Widget route handles F"], [source_rel, test_rel]
            )
            self.assertTrue(any(value.startswith("--name=^") and value.endswith("$") for value in widget["argv"]))
            self.assertEqual(widget["additional_paths"], [test_rel])
        with self.assertRaisesRegex(ValueError, "bound Owner scope"):
            eng._allowlisted_verification(
                "test", ["flutter", "test", "--no-pub", test_rel, "--name", "Widget route handles F"], [source_rel]
            )

    def test_windows_dart_and_flutter_batch_launchers_resolve_native_executables(self):
        tool_root = Path(self.temp.name) / "flutter-sdk"
        flutter_bin = tool_root / "bin"
        dart_bin = flutter_bin / "cache" / "dart-sdk" / "bin"
        dart_bin.mkdir(parents=True)
        flutter_launcher = flutter_bin / "flutter.bat"
        flutter_launcher.parent.mkdir(parents=True, exist_ok=True)
        flutter_launcher.write_text("@echo off\n", "utf-8")
        flutter_tools = flutter_bin / "cache" / "flutter_tools.snapshot"
        flutter_tools.write_bytes(b"fixture snapshot")
        dart_launcher = dart_bin / "dart.bat"
        dart_launcher.write_text("@echo off\n", "utf-8")
        flutter_bin_dart_launcher = flutter_bin / "dart.bat"
        flutter_bin_dart_launcher.write_text("@echo off\n", "utf-8")
        dart_exe = dart_bin / "dart.exe"
        dart_exe.write_bytes(b"fixture executable")

        def which(name):
            if name == "flutter":
                return str(flutter_launcher)
            if name == "dart":
                return str(dart_launcher)
            return None

        with mock.patch.object(eng.shutil, "which", side_effect=which):
            self.assertEqual(eng._resolve_tool_argv("dart", ["analyze", "lib/main.dart"]),
                             [str(dart_exe.resolve()), "analyze", "lib/main.dart"])
            self.assertEqual(eng._resolve_tool_argv("flutter", ["analyze", "--no-pub"]),
                             [str(dart_exe.resolve()), "--disable-dart-dev", str(flutter_tools.resolve()),
                              "analyze", "--no-pub"])

        with mock.patch.object(eng.shutil, "which", side_effect=lambda name: (
                str(flutter_bin_dart_launcher) if name == "dart" else None)):
            self.assertEqual(eng._resolve_tool_argv("dart", ["--version"]),
                             [str(dart_exe.resolve()), "--version"])

        flutter_tools.unlink()
        with mock.patch.object(eng.shutil, "which", side_effect=which), self.assertRaisesRegex(ValueError, "Flutter executable is UNAVAILABLE"):
            eng._resolve_tool_argv("flutter", ["build", "web"])

        with mock.patch.object(eng.shutil, "which", return_value=None), self.assertRaisesRegex(ValueError, "Dart executable is UNAVAILABLE"):
            eng._resolve_tool_argv("dart", ["analyze", "lib/main.dart"])
        ruff = eng._allowlisted_verification(
            "static", ["ruff.cmd", "check", "--select", "F", "--no-cache", "sample.py"], ["sample.py"]
        )
        self.assertEqual(ruff["argv"][1:5], ["check", "--select", "F", "--no-cache"])
        if shutil.which("ruff.cmd"):
            actual = eng._execute_verification_process("static", ruff["argv"], self.root, 20)
            self.assertEqual(actual["returncode"], 0)

    def test_dirty_current_is_local_candidate_only(self):
        current = self.root / "00-GOVERNANCE" / "LUMENIS-CODEX-TAKEOVER-CURRENT.md"
        current.parent.mkdir(parents=True, exist_ok=True)
        current.write_text("published current\n", "utf-8")
        self.git("add", "00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md")
        self.git("commit", "-qm", "add current fixture")
        current.write_text("local candidate current\n", "utf-8")
        output = self.handle("SessionStart", source="clear")
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("LOCAL_CANDIDATE_ONLY", context)
        self.assertIn("published HEAD copy", context)

    def test_subagent_owns_ordinary_blockers(self):
        output = self.handle("SubagentStart")
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("maintained upstream GitHub", context)
        self.assertIn("strongest feasible complete solution", context)
        self.assertIn("Escalate only genuine", context)

    def test_failed_latest_test_wins(self):
        self.edit(); self.verify(0); self.verify(1)
        self.assertEqual(self.handle("Stop").get("decision"), "block")

    def test_repeat_stop_terminates_without_success(self):
        self.edit()
        output = self.handle("Stop", stop_hook_active=True)
        self.assertFalse(output["continue"])
        self.assertIn("BLOCKED", output["systemMessage"])

    def test_non_code_static(self):
        (self.root / "notes.md").write_text("notes", "utf-8")
        self.handle("PostToolUse", tool_name="apply_patch", tool_input={}, tool_response={"exit_code": 0})
        self.verify(0, "git diff --check")
        self.assertEqual(self.handle("Stop"), {})

    def test_exit_decoding(self):
        cases = [
            ({"exit_code": 1}, 1),
            ({"exitCode": 0}, 0),
            ({"returncode": -2}, -2),
            ({"output": "Process exited with code 0"}, None),
            ({"stdout": "Exit code: 0"}, None),
            ({"content": [{"text": "Process completed with exit code 0"}]}, None),
            ({"stdout": {"exit_code": 0}}, None),
            ([{"exit_code": 0}], None),
            ({"isError": True}, None),
            ("Process exited with code 0", None),
            ("all good", None),
            ({"exit_code": "0"}, None),
            ({"exit_code": True}, None),
        ]
        for data, expected in cases:
            self.assertEqual(h.exit_status(data), expected)

    def test_sensitive_paths_are_excluded(self):
        for path in [".env", "data/monitor.db", "data/private/item.json", "credentials.json", "node_modules/a.py"]:
            self.assertFalse(h.eligible(path))

    def test_routes_include_relevant_tools(self):
        text = " ".join(h.route_prompt("Flutter 数据库 API Playwright E2E 权限 bug 阻塞"))
        self.assertIn("Context7", text)
        self.assertIn("database-safety", text)
        self.assertIn("browser-e2e", text)
        self.assertIn("lumenis-self-resolve", text)
        self.assertIn("maintained upstream GitHub", text)

    def test_openai_route_uses_official_docs_mcp_first(self):
        text = " ".join(h.route_prompt("Codex OpenAI plugin API bug"))
        self.assertIn("openaiDeveloperDocs MCP first", text)
        self.assertIn("openai/codex GitHub", text)

    def test_engineering_routes_compile_and_support_chinese(self):
        import re
        for name, pattern, _ in eng.ROUTES:
            with self.subTest(route=name):
                re.compile(pattern, re.IGNORECASE)
        routes = eng.route_task("Flutter 页面 bug 阻塞，需要研究依赖和修复", ["app/lib/main.dart"])["routes"]
        self.assertTrue(any(item["skill"] == "lumenis-flutter-runtime" for item in routes))
        self.assertTrue(any(item["skill"] == "lumenis-testing" for item in routes))

    def test_engineering_mcp_has_no_hidden_workstation_helper(self):
        text = ENGINEERING.read_text("utf-8")
        self.assertNotIn(r"D:\\codex\\agent-skills", text)
        self.assertIn("def source_read(", text)
        self.assertIn("def route_task(", text)

    def test_validation_plan_uses_current_policy_and_separates_e2e(self):
        plan = eng.validation_plan(["sample.py"])
        text = " ".join(plan["plan"])
        self.assertIn("current machine policy permits", text)
        self.assertIn("real-user E2E separate", text)
        self.assertNotIn("do not create or run module suites", text)

    def test_utf8_hook_subprocess(self):
        event = {"hook_event_name": "PreToolUse", "cwd": str(self.root), "session_id": "unit-test", "tool_name": "Bash", "tool_input": {"command": "git reset --hard HEAD"}}
        isolated_home = Path(self.temp.name) / "subprocess-home"
        isolated_home.mkdir()
        environment = os.environ.copy()
        environment["USERPROFILE"] = str(isolated_home)
        environment["HOME"] = str(isolated_home)
        proc = subprocess.run([sys.executable, "-X", "utf8", str(HOOK)], input=json.dumps(event, ensure_ascii=False).encode(), capture_output=True, env=environment, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
        state = h.state_file(event, self.root)
        state.unlink(missing_ok=True)

    def lock_child(self, code, *arguments):
        return [sys.executable, "-X", "utf8", "-c", code, str(HOOK), *map(str, arguments)]

    def test_kernel_lock_is_released_after_process_crash(self):
        state_path = Path(self.temp.name) / "crash-state.json"
        lock_path = state_path.with_suffix(".lock")
        code = """
import importlib.util, os, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('lock_test_hooks', sys.argv[1])
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)
with hook.locked(Path(sys.argv[2])):
    os._exit(7)
"""
        child = subprocess.run(self.lock_child(code, state_path), capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(child.returncode, 7, child.stderr)
        self.assertTrue(lock_path.exists(), "Kernel lock marker should survive process exit")
        with h.locked(state_path):
            self.assertTrue(lock_path.exists(), "Lock acquisition must not depend on deleting the marker")
        self.assertTrue(lock_path.exists(), "Marker file should persist after releasing the kernel lock")

    def test_kernel_lock_cannot_be_bypassed_while_another_process_holds_it(self):
        state_path = Path(self.temp.name) / "active-state.json"
        ready_path = Path(self.temp.name) / "lock-ready.txt"
        code = """
import importlib.util, sys, time
from pathlib import Path
spec = importlib.util.spec_from_file_location('lock_test_hooks', sys.argv[1])
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)
with hook.locked(Path(sys.argv[2])):
    Path(sys.argv[3]).write_text('locked', encoding='utf-8')
    time.sleep(15)
"""
        child = subprocess.Popen(self.lock_child(code, state_path, ready_path), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 8
            while not ready_path.exists() and child.poll() is None and time.monotonic() < deadline:
                time.sleep(0.025)
            self.assertTrue(ready_path.exists(), "Lock holder subprocess did not report acquisition")
            with self.assertRaisesRegex(RuntimeError, "Concurrent state write"), h.locked(state_path):
                self.fail("An active process lock was bypassed")
            self.assertIsNone(child.poll(), "The competing process must still hold its lock")
        finally:
            if child.poll() is None:
                child.terminate()
            child.communicate(timeout=5)

    def test_empty_legacy_lock_is_rejected_for_manual_verification(self):
        state_path = Path(self.temp.name) / "legacy-state.json"
        lock_path = state_path.with_suffix(".lock")
        lock_path.write_bytes(b"")
        with self.assertRaisesRegex(RuntimeError, r"(?i)(legacy|verify|verification|核实)"), h.locked(state_path):
            self.fail("An empty legacy lock must not be taken over")
        self.assertEqual(lock_path.read_bytes(), b"", "Legacy marker must remain untouched")

    def delivery_fixture(self, pending_effects=None):
        """An isolated tool outcome; never a product acceptance receipt."""
        record = self.make_continuity_record(pending_effects)
        payload = json.loads(record.read_text("utf-8"))
        payload["continuity"]["delivery"] = {
            "schema_version": 1,
            "status": "RUNNING",
            "po_source": "Direct PO: finish both admitted tooling outcomes",
            "scope_sources": [{"path": "AGENTS.md", "sha256": h.hashlib.sha256((self.root / "AGENTS.md").read_bytes()).hexdigest()}],
            "effect_ledger": [
                {"pending_effect_sha256": h._pending_effect_id(value), "status": "PENDING"}
                for value in (pending_effects or [])
            ],
            "requirements": [
                {"id": "TOOL-1", "outcome_class": "DEVELOPMENT_TOOL", "acceptance": "Actual tool workflow completes and can recover", "coverage_refs": ["tool-input", "tool-output", "tool-recovery"], "status": "OPEN", "evidence": []},
                {"id": "TOOL-2", "outcome_class": "DEVELOPMENT_TOOL", "acceptance": "Published source and activated tool match", "coverage_refs": ["source", "loaded-version"], "status": "OPEN", "evidence": []},
            ],
        }
        record.write_text(json.dumps(payload), "utf-8")
        self.delivery_event = {"session_id": "engineering-test-thread", "agent_id": "bounded-test-agent"}
        self.handle("UserPromptSubmit", **self.delivery_event,
                    prompt="Complete the admitted tooling outcomes", turn_id="tooling-initial")
        h.continuity_save(self.root, self.state, self.delivery_event, "work/checkpoint.json", "continuity")
        return record, payload

    def save_delivery_fixture(self, record, payload):
        record.write_text(json.dumps(payload), "utf-8")
        return h.continuity_save(self.root, self.state, self.delivery_event, "work/checkpoint.json", "continuity")

    def delivery_stop(self, **extra):
        return self.handle("Stop", **self.delivery_event, **extra)

    def test_delivery_open_outcomes_block_even_without_source_changes(self):
        self.delivery_fixture()
        self.assertEqual(self.delivery_stop().get("decision"), "block")

    def test_delivery_cannot_remove_required_item_by_rebinding(self):
        record, payload = self.delivery_fixture()
        payload["continuity"]["delivery"]["requirements"].pop()
        with self.assertRaises(ValueError):
            self.save_delivery_fixture(record, payload)

    def test_delivery_cannot_narrow_acceptance_by_rebinding(self):
        record, payload = self.delivery_fixture()
        payload["continuity"]["delivery"]["requirements"][0]["acceptance"] = "Code exists"
        with self.assertRaises(ValueError):
            self.save_delivery_fixture(record, payload)

    def test_delivery_cannot_drop_coverage_by_rebinding(self):
        record, payload = self.delivery_fixture()
        payload["continuity"]["delivery"]["requirements"][0]["coverage_refs"].pop()
        with self.assertRaises(ValueError):
            self.save_delivery_fixture(record, payload)

    def test_delivery_rebinding_legacy_record_cannot_remove_guard(self):
        record, payload = self.delivery_fixture()
        del payload["continuity"]["delivery"]
        with self.assertRaises(ValueError):
            self.save_delivery_fixture(record, payload)

    def test_delivery_defer_is_not_completion(self):
        record, payload = self.delivery_fixture()
        payload["continuity"]["delivery"]["requirements"][0]["status"] = "DEFER"
        self.save_delivery_fixture(record, payload)
        self.assertEqual(self.delivery_stop().get("decision"), "block")

    def test_delivery_ci_and_implementation_cannot_close_outcomes(self):
        record, payload = self.delivery_fixture()
        for requirement in payload["continuity"]["delivery"]["requirements"]:
            requirement["status"] = "INTEGRATED"
        self.save_delivery_fixture(record, payload)
        self.verify()
        self.assertEqual(self.delivery_stop().get("decision"), "block")

    def test_delivery_unverified_claimed_evidence_never_closes_task(self):
        record, payload = self.delivery_fixture()
        delivery = payload["continuity"]["delivery"]
        delivery["status"] = "JOB_CLOSED"
        for requirement in delivery["requirements"]:
            requirement["status"] = "JOB_CLOSED"
        try:
            self.save_delivery_fixture(record, payload)
        except ValueError:
            return
        self.assertEqual(self.delivery_stop().get("decision"), "block")

    def test_delivery_stop_retry_is_bounded(self):
        self.delivery_fixture()
        self.assertEqual(self.delivery_stop().get("decision"), "block")
        self.assertFalse(self.delivery_stop(stop_hook_active=True).get("continue", True))

    def test_delivery_clarification_keeps_full_outcome_open(self):
        self.delivery_fixture()
        self.handle("UserPromptSubmit", **self.delivery_event, prompt="#17和Slack也全部包括，对的", turn_id="clarification")
        self.assertEqual(self.delivery_stop().get("decision"), "block")

    def test_delivery_blocked_without_reason_and_evidence_is_not_an_exit(self):
        record, payload = self.delivery_fixture()
        payload["continuity"]["delivery"]["status"] = "EXTERNAL_BLOCKED"
        try:
            self.save_delivery_fixture(record, payload)
        except ValueError:
            return
        self.assertEqual(self.delivery_stop().get("decision"), "block")

    def close_delivery_fixture(self, record, payload):
        item = payload["continuity"]
        item["remaining"] = []
        item["delivery"]["status"] = "JOB_CLOSED"
        head = self.git("rev-parse", "HEAD").strip()
        required_sources = [*item["source_paths"], *(source["path"] for source in item["delivery"]["scope_sources"])]
        pins = {name: h.hashlib.sha256((self.root / name).read_bytes()).hexdigest() for name in required_sources}
        for requirement in item["delivery"]["requirements"]:
            requirement["status"] = "JOB_CLOSED"
            for kind in ("TOOL_WORKFLOW", "RECOVERY"):
                name = f"work/{requirement['id']}-{kind}.json"
                receipt = {
                    "schema_version": 1, "requirement_id": requirement["id"],
                    "kind": kind, "result": "ACCEPTED", "head": head,
                    "source_pins": pins,
                    "observation": "Isolated hook fixture, not real product acceptance",
                }
                (self.root / name).write_text(json.dumps(receipt), "utf-8")
                item["evidence_paths"].append(name)
                requirement["evidence"].append({
                    "path": name, "sha256": h.hashlib.sha256((self.root / name).read_bytes()).hexdigest(),
                    "kind": kind, "result": "ACCEPTED", "head": head, "source_pins": pins,
                })
        self.save_delivery_fixture(record, payload)

    def add_delivery_receipts(self, item, requirement):
        head = self.git("rev-parse", "HEAD").strip()
        required_sources = [*item["source_paths"],
                            *(source["path"] for source in item["delivery"]["scope_sources"])]
        pins = {name: h.hashlib.sha256((self.root / name).read_bytes()).hexdigest()
                for name in required_sources}
        for kind in ("TOOL_WORKFLOW", "RECOVERY"):
            name = f"work/{requirement['id']}-{kind}-current.json"
            receipt = {
                "schema_version": 1, "requirement_id": requirement["id"],
                "kind": kind, "result": "ACCEPTED", "head": head,
                "source_pins": pins,
                "observation": "Isolated receipt pins the complete declared source scope",
            }
            (self.root / name).write_text(json.dumps(receipt), "utf-8")
            item["evidence_paths"].append(name)
            requirement["evidence"].append({
                "path": name, "sha256": h.hashlib.sha256((self.root / name).read_bytes()).hexdigest(),
                "kind": kind, "result": "ACCEPTED", "head": head, "source_pins": pins,
            })
        requirement["status"] = "JOB_CLOSED"
        return pins

    def block_delivery_fixture(self, record, payload):
        item = payload["continuity"]
        delivery = item["delivery"]
        delivery["status"] = "EXTERNAL_BLOCKED"
        receipt_paths = []
        head = self.git("rev-parse", "HEAD").strip()
        pins = {name: h.hashlib.sha256((self.root / name).read_bytes()).hexdigest()
                for name in [*item["source_paths"], *(source["path"] for source in delivery["scope_sources"])]}
        for requirement in delivery["requirements"]:
            requirement["status"] = "BLOCKED"
            name = f"work/{requirement['id']}-EXTERNAL-BLOCKER.json"
            receipt = {
                "schema_version": 1, "requirement_id": requirement["id"],
                "kind": "EXTERNAL_BLOCKER", "result": "BLOCKED", "head": head,
                "source_pins": pins,
                "observation": "Isolated fixture records a concrete external dependency blocker",
            }
            (self.root / name).write_text(json.dumps(receipt), "utf-8")
            item["evidence_paths"].append(name)
            requirement["evidence"].append({
                "path": name, "sha256": h.hashlib.sha256((self.root / name).read_bytes()).hexdigest(),
                "kind": "EXTERNAL_BLOCKER", "result": "BLOCKED", "head": head, "source_pins": pins,
            })
            receipt_paths.append(name)
        item["remaining"] = ["The two admitted tool outcomes remain blocked by the documented external dependency."]
        delivery["exit"] = {
            "reason": "EXTERNAL_BLOCKED: both outcomes need the named external dependency.",
            "evidence_path": receipt_paths[0],
            "resume_condition": "Resume after the external dependency is available and read back.",
        }
        self.save_delivery_fixture(record, payload)

    def resolve_effect_fixture(self, payload, effect):
        item = payload["continuity"]
        delivery = item["delivery"]
        effect_id = h._pending_effect_id(effect)
        head = self.git("rev-parse", "HEAD").strip()
        sources = [*item["source_paths"], *(value["path"] for value in delivery["scope_sources"])]
        pins = {name: h.hashlib.sha256((self.root / name).read_bytes()).hexdigest() for name in sources}
        receipt = {
            "schema_version": 1,
            "pending_effect_sha256": effect_id,
            "resolution": "RECONCILED",
            "head": head,
            "source_pins": pins,
            "observation": "Isolated fixture has an exact terminal readback for this operation",
        }
        name = f"work/effect-resolution-{effect_id[:16]}.json"
        receipt_path = self.root / name
        receipt_path.write_text(json.dumps(receipt), "utf-8")
        item["evidence_paths"].append(name)
        ledger_entry = next(value for value in delivery["effect_ledger"]
                            if value["pending_effect_sha256"] == effect_id)
        ledger_entry.update({
            "status": "RESOLVED",
            "path": name,
            "sha256": h.hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        })
        item["pending_effects"].remove(effect)
        return receipt_path

    def test_delivery_complete_current_outcomes_and_recovery_allow_stop(self):
        record, payload = self.delivery_fixture()
        self.close_delivery_fixture(record, payload)
        self.assertEqual(self.delivery_stop(), {})

    def test_delivery_supports_100_complete_outcomes_with_real_and_recovery_receipts(self):
        record, payload = self.delivery_fixture()
        requirements = payload["continuity"]["delivery"]["requirements"]
        for index in range(3, 101):
            requirements.append({
                "id": f"TOOL-{index}",
                "outcome_class": "DEVELOPMENT_TOOL",
                "acceptance": f"Complete the admitted tool operation {index} with a useful readback and recoverable saved result. "
                              + "Confirm the actual workflow outcome and restored state. " * 18,
                "coverage_refs": [f"tool-{index}-operation", f"tool-{index}-recovery"],
                "status": "OPEN",
                "evidence": [],
            })
        self.save_delivery_fixture(record, payload)
        self.close_delivery_fixture(record, payload)
        self.assertEqual(len(payload["continuity"]["delivery"]["requirements"]), 100)
        self.assertEqual(self.delivery_stop(), {})

    def test_delivery_switch_rechecks_prior_record_and_new_requirement(self):
        record, payload = self.delivery_fixture()
        self.close_delivery_fixture(record, payload)
        next_record = self.root / "work/next.json"
        next_record.write_text(json.dumps(payload), "utf-8")
        payload["continuity"]["delivery"]["status"] = "RUNNING"
        payload["continuity"]["delivery"]["requirements"].append({
            "id": "TOOL-3", "outcome_class": "DEVELOPMENT_TOOL",
            "acceptance": "Newly admitted full recovery outcome",
            "coverage_refs": ["recovery"], "status": "OPEN", "evidence": [],
        })
        record.write_text(json.dumps(payload), "utf-8")
        with self.assertRaisesRegex(ValueError, "unfinished delivery"):
            h.continuity_save(self.root, self.state, self.delivery_event, "work/next.json", "continuity")
        self.assertEqual(self.state["delivery_guard"]["record"], "work/checkpoint.json")

    def test_delivery_switch_rechecks_current_source_receipts(self):
        record, payload = self.delivery_fixture()
        self.close_delivery_fixture(record, payload)
        next_payload = {"continuity": self.continuity_item()}
        (self.root / "work/next.json").write_text(json.dumps(next_payload), "utf-8")
        self.edit(99)
        with self.assertRaises(ValueError):
            h.continuity_save(self.root, self.state, self.delivery_event, "work/next.json", "continuity")
        self.assertEqual(self.state["delivery_guard"]["record"], "work/checkpoint.json")

    def test_delivery_current_closed_record_can_switch(self):
        record, payload = self.delivery_fixture()
        self.close_delivery_fixture(record, payload)
        (self.root / "work/next.json").write_text(json.dumps({"continuity": self.continuity_item()}), "utf-8")
        h.continuity_save(self.root, self.state, self.delivery_event, "work/next.json", "continuity")
        self.assertEqual(self.state["continuity"]["record"], "work/next.json")
        self.assertNotIn("delivery_guard", self.state)

    def test_new_execution_prompt_cannot_switch_to_legacy_or_old_closed_record(self):
        record, payload = self.delivery_fixture()
        self.close_delivery_fixture(record, payload)
        self.handle("UserPromptSubmit", **self.delivery_event,
                    prompt="Implement the new reporting outcome", turn_id="new-reporting-outcome")
        for next_item in (self.continuity_item(), payload["continuity"]):
            (self.root / "work/next.json").write_text(json.dumps({"continuity": next_item}), "utf-8")
            with self.assertRaisesRegex(ValueError, "admit its required outcome"):
                h.continuity_save(self.root, self.state, self.delivery_event, "work/next.json", "continuity")
            self.assertEqual(self.state["delivery_guard"]["record"], "work/checkpoint.json")
        payload["continuity"]["delivery"]["status"] = "RUNNING"
        payload["continuity"]["delivery"]["requirements"].append({
            "id": "TOOL-3", "outcome_class": "DEVELOPMENT_TOOL",
            "acceptance": "New reporting operation saves and reopens its real result",
            "coverage_refs": ["reporting", "save", "reopen"], "status": "OPEN", "evidence": [],
        })
        payload["continuity"]["remaining"] = ["TOOL-3 reporting outcome remains open"]
        (self.root / "work/next.json").write_text(json.dumps(payload), "utf-8")
        h.continuity_save(self.root, self.state, self.delivery_event, "work/next.json", "continuity")
        self.assertEqual(self.state["delivery_guard"]["record"], "work/next.json")
        self.assertEqual(self.delivery_stop().get("decision"), "block")

    def test_delivery_clear_keeps_scope_and_requires_rebind(self):
        record, payload = self.delivery_fixture()
        self.handle("SessionStart", source="clear", **self.delivery_event)
        self.assertNotIn("continuity", self.state)
        self.assertEqual(self.delivery_stop().get("decision"), "block")
        self.assertEqual(set(self.state["delivery_guard"]["requirements"]), {"TOOL-1", "TOOL-2"})
        self.save_delivery_fixture(record, payload)
        self.assertEqual(self.state["continuity"]["record"], "work/checkpoint.json")

    def test_delivery_old_closure_requires_current_prompt_reconciliation(self):
        record, payload = self.delivery_fixture()
        self.close_delivery_fixture(record, payload)
        self.handle("UserPromptSubmit", **self.delivery_event, prompt="继续实现新增的产品要求", turn_id="new-outcome")
        self.assertEqual(self.delivery_stop().get("decision"), "block")
        self.assertIn("new Product Owner message", self.state["last_delivery_reason"] if "last_delivery_reason" in self.state else h.delivery_stop_check(self.root, self.state, self.delivery_event)[1])

    def test_delivery_old_closure_cannot_refresh_only_prompt_hash(self):
        record, payload = self.delivery_fixture()
        self.close_delivery_fixture(record, payload)
        self.handle("UserPromptSubmit", **self.delivery_event, prompt="继续实现新产品能力", turn_id="new-required-outcome")
        with self.assertRaisesRegex(ValueError, "closed outcomes unchanged"):
            self.save_delivery_fixture(record, payload)
        payload["continuity"]["delivery"]["status"] = "RUNNING"
        payload["continuity"]["delivery"]["requirements"].append({
            "id": "TOOL-3", "outcome_class": "DEVELOPMENT_TOOL",
            "acceptance": "New direct PO outcome with actual recovery",
            "coverage_refs": ["new-task"], "status": "OPEN", "evidence": [],
        })
        self.save_delivery_fixture(record, payload)
        self.assertEqual(self.delivery_stop().get("decision"), "block")

    def test_external_blocker_exit_cannot_be_rebound_to_a_new_prompt(self):
        record, payload = self.delivery_fixture()
        self.block_delivery_fixture(record, payload)
        self.assertEqual(self.delivery_stop(), {})
        self.handle("UserPromptSubmit", **self.delivery_event,
                    prompt="Continue the full outcome after the new instruction", turn_id="blocker-new-prompt")
        payload["continuity"]["delivery"]["exit"]["reason"] += "."
        self.save_delivery_fixture(record, payload)
        self.assertEqual(self.delivery_stop().get("decision"), "block")

        delivery = payload["continuity"]["delivery"]
        old_receipt = self.root / delivery["exit"]["evidence_path"]
        receipt = json.loads(old_receipt.read_text("utf-8"))
        receipt["observation"] = "Fresh isolated readback still proves the same external dependency is unavailable"
        old_receipt.write_text(json.dumps(receipt), "utf-8")
        for requirement in delivery["requirements"]:
            evidence = requirement["evidence"][0]
            evidence_path = self.root / evidence["path"]
            evidence_body = json.loads(evidence_path.read_text("utf-8"))
            evidence_body["observation"] = (
                "Fresh isolated readback still proves the named external dependency is unavailable for "
                + requirement["id"]
            )
            evidence_path.write_text(json.dumps(evidence_body), "utf-8")
            evidence["sha256"] = h.hashlib.sha256(evidence_path.read_bytes()).hexdigest()
        self.save_delivery_fixture(record, payload)
        self.assertEqual(self.delivery_stop(), {})

    def test_po_deferred_cannot_be_laundered_through_running_or_clear(self):
        record, payload = self.delivery_fixture()
        item = payload["continuity"]
        delivery = item["delivery"]
        deferred = delivery["requirements"][1]
        deferred["po_source"] = "Direct PO instruction: defer TOOL-2 pending its named approval."
        source_path = "work/po-deferred.md"
        source_text = (
            "Product Owner direct instruction receipt\n"
            "PO_DEFERRED TOOL-2\n"
            f"{deferred['po_source']}\n"
        )
        (self.root / source_path).write_text(source_text, "utf-8")
        item["evidence_paths"].append(source_path)
        delivery["scope_sources"].append({
            "path": source_path,
            "sha256": h.hashlib.sha256((self.root / source_path).read_bytes()).hexdigest(),
        })
        self.save_delivery_fixture(record, payload)
        self.close_delivery_fixture(record, payload)
        deferred["status"] = "PO_DEFERRED"
        delivery["status"] = "PO_DEFERRED"
        item["remaining"] = ["TOOL-2 remains deferred until the named approval is received."]
        delivery["exit"] = {
            "reason": "PO_DEFERRED: TOOL-2 remains open under the direct PO instruction.",
            "evidence_path": source_path,
            "resume_condition": "Resume TOOL-2 only when its named Product Owner approval is received.",
        }
        self.save_delivery_fixture(record, payload)
        self.assertEqual(self.delivery_stop(), {})

        self.handle("UserPromptSubmit", **self.delivery_event,
                    prompt="Resume TOOL-2 and continue the authorized work", turn_id="deferred-resume")
        delivery["status"] = "RUNNING"
        deferred["status"] = "OPEN"
        self.save_delivery_fixture(record, payload)
        self.handle("SessionStart", source="clear", **self.delivery_event)
        delivery["status"] = "PO_DEFERRED"
        deferred["status"] = "PO_DEFERRED"
        self.save_delivery_fixture(record, payload)
        self.assertEqual(self.delivery_stop().get("decision"), "block")
        delivery["exit"]["reason"] += "."
        self.save_delivery_fixture(record, payload)
        result = self.delivery_stop()
        self.assertTrue(result.get("decision") == "block" or result.get("continue") is False, result)

        current_prompt = "PO_DEFERRED TOOL-2 again under the newly issued direct instruction"
        self.handle("UserPromptSubmit", **self.delivery_event,
                    prompt=current_prompt, turn_id="deferred-new-authorization")
        new_po_source = deferred["po_source"] + " Direct PO instruction: defer TOOL-2 again per the current message."
        deferred["po_source"] = new_po_source
        renewed_source_path = "work/po-deferred-renewed.md"
        refreshed_text = (
            "Product Owner direct instruction receipt\nPO_DEFERRED TOOL-2\n"
            f"{new_po_source}\n"
            f"Current direct instruction: {current_prompt}\n"
        )
        (self.root / renewed_source_path).write_text(refreshed_text, "utf-8")
        item["evidence_paths"].append(renewed_source_path)
        delivery["scope_sources"].append({
            "path": renewed_source_path,
            "sha256": h.hashlib.sha256((self.root / renewed_source_path).read_bytes()).hexdigest(),
        })
        original_receipts = {
            requirement["id"]: json.loads(json.dumps(requirement["evidence"]))
            for requirement in delivery["requirements"]
        }
        deferred["status"] = "PO_DEFERRED"
        delivery["status"] = "PO_DEFERRED"
        item["remaining"] = ["TOOL-2 remains deferred under the renewed direct PO instruction."]
        delivery["exit"] = {
            "reason": "PO_DEFERRED: TOOL-2 remains open under the renewed direct PO instruction.",
            "evidence_path": renewed_source_path,
            "resume_condition": "Resume TOOL-2 only after the renewed named approval is received.",
        }
        self.save_delivery_fixture(record, payload)
        self.assertEqual(self.delivery_stop(), {})
        for requirement in delivery["requirements"]:
            self.assertEqual(requirement["evidence"], original_receipts[requirement["id"]])
        self.assertEqual(delivery["status"], "PO_DEFERRED")

    def test_delivery_clear_preserves_unverified_mutations(self):
        self.delivery_fixture()
        before = self.state["baseline"]["fingerprint"]
        self.edit()
        self.handle("SessionStart", source="clear", **self.delivery_event)
        self.assertEqual(self.state["baseline"]["fingerprint"], before)
        self.assertTrue(self.state["mutation_observed"])
        self.handle("UserPromptSubmit", **self.delivery_event, prompt="只汇报，不要修改", turn_id="status-after-clear")
        self.delivery_stop()
        self.assertTrue(self.state["mutation_observed"])

    def test_delivery_implementation_paths_are_append_only_and_normalized(self):
        record, payload = self.delivery_fixture()
        payload["continuity"]["source_paths"] = ["./sample.py"]
        self.save_delivery_fixture(record, payload)
        self.assertEqual(self.state["delivery_guard"]["source_paths"], ["sample.py"])
        payload["continuity"]["source_paths"] = []
        with self.assertRaisesRegex(ValueError, "implementation source path"):
            self.save_delivery_fixture(record, payload)
        self.assertEqual(self.state["delivery_guard"]["source_paths"], ["sample.py"])

    def test_delivery_closure_rejects_remaining_continuity_work(self):
        record, payload = self.delivery_fixture()
        self.close_delivery_fixture(record, payload)
        payload["continuity"]["remaining"].append("A required user outcome remains open")
        with self.assertRaisesRegex(ValueError, "remaining list to be empty"):
            self.save_delivery_fixture(record, payload)

    def test_delivery_receipts_survive_unrelated_head_advance(self):
        record, payload = self.delivery_fixture()
        self.close_delivery_fixture(record, payload)
        (self.root / "unrelated.md").write_text("An unrelated commit.\n", "utf-8")
        self.git("add", "unrelated.md")
        self.git("commit", "-qm", "unrelated source change")
        self.assertEqual(self.delivery_stop(), {})
        evidence = payload["continuity"]["delivery"]["requirements"][0]["evidence"][0]
        self.assertNotEqual(evidence["head"], self.git("rev-parse", "HEAD").strip())

    def test_delivery_scope_addition_preserves_closed_receipt_and_pins_open_work(self):
        record, payload = self.delivery_fixture()
        item = payload["continuity"]
        delivery = item["delivery"]
        first, second = delivery["requirements"]
        item["remaining"] = ["TOOL-2 remains open under its existing acceptance."]
        self.add_delivery_receipts(item, first)
        self.save_delivery_fixture(record, payload)
        frozen_first_evidence = list(first["evidence"])
        legacy_requirement_guard = self.state["delivery_guard"]["requirements"]["TOOL-1"]
        legacy_requirement_guard.pop("closed_evidence")
        legacy_requirement_guard.pop("needs_current_evidence")
        legacy_requirement_guard.pop("closure_source_pins")

        added_source = "work/scope-for-tool-2.md"
        (self.root / added_source).write_text("Approved scope source for the remaining TOOL-2 outcome.\n", "utf-8")
        added_hash = h.hashlib.sha256((self.root / added_source).read_bytes()).hexdigest()
        delivery["scope_sources"].append({"path": added_source, "sha256": added_hash})
        self.save_delivery_fixture(record, payload)
        self.assertEqual(first["evidence"], frozen_first_evidence)
        self.assertTrue(all(added_source not in evidence["source_pins"] for evidence in first["evidence"]))
        self.assertNotIn(
            added_source,
            self.state["delivery_guard"]["requirements"]["TOOL-1"]["closure_source_pins"],
        )
        self.assertIn(added_source, self.state["delivery_guard"]["scope_sources"])

        added_ref = next(value for value in delivery["scope_sources"] if value["path"] == added_source)
        delivery["scope_sources"].remove(added_ref)
        with self.assertRaisesRegex(ValueError, "remove a frozen scope source"):
            self.save_delivery_fixture(record, payload)
        delivery["scope_sources"].append(added_ref)
        self.save_delivery_fixture(record, payload)

        current_pins = self.add_delivery_receipts(item, second)
        self.assertIn(added_source, current_pins)
        item["remaining"] = []
        delivery["status"] = "JOB_CLOSED"
        self.save_delivery_fixture(record, payload)
        self.assertEqual(self.delivery_stop(), {})

    def test_delivery_scope_addition_rejects_replaced_historical_receipt(self):
        record, payload = self.delivery_fixture()
        item = payload["continuity"]
        delivery = item["delivery"]
        first = delivery["requirements"][0]
        item["remaining"] = ["TOOL-2 remains open under its existing acceptance."]
        self.add_delivery_receipts(item, first)
        self.save_delivery_fixture(record, payload)

        added_source = "work/scope-for-tool-2.md"
        (self.root / added_source).write_text("Approved scope source for the remaining TOOL-2 outcome.\n", "utf-8")
        delivery["scope_sources"].append({
            "path": added_source,
            "sha256": h.hashlib.sha256((self.root / added_source).read_bytes()).hexdigest(),
        })
        self.save_delivery_fixture(record, payload)

        frozen_ref = first["evidence"][0]
        receipt_path = self.root / frozen_ref["path"]
        receipt = json.loads(receipt_path.read_text("utf-8"))
        receipt["observation"] = "A replacement observation attempts to reuse the historical scope pins"
        receipt_path.write_text(json.dumps(receipt), "utf-8")
        frozen_ref["sha256"] = h.hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, "cannot be removed or replaced"):
            self.save_delivery_fixture(record, payload)

    def test_delivery_old_scope_receipt_cannot_be_claimed_without_original_session_guard(self):
        record, payload = self.delivery_fixture()
        item = payload["continuity"]
        delivery = item["delivery"]
        first = delivery["requirements"][0]
        item["remaining"] = ["TOOL-2 remains open under its existing acceptance."]
        self.add_delivery_receipts(item, first)
        self.save_delivery_fixture(record, payload)

        added_source = "work/scope-for-tool-2.md"
        (self.root / added_source).write_text("Approved scope source for the remaining TOOL-2 outcome.\n", "utf-8")
        delivery["scope_sources"].append({
            "path": added_source,
            "sha256": h.hashlib.sha256((self.root / added_source).read_bytes()).hexdigest(),
        })
        record.write_text(json.dumps(payload), "utf-8")
        new_event = {"session_id": "different-engineering-session", "agent_id": "bounded-test-agent"}
        with self.assertRaisesRegex(ValueError, "complete current source scope"):
            h.continuity_save(self.root, self.state, new_event,
                              "work/checkpoint.json", "continuity")

    def test_delivery_scope_addition_still_rejects_changed_old_pinned_source(self):
        record, payload = self.delivery_fixture()
        item = payload["continuity"]
        delivery = item["delivery"]
        first = delivery["requirements"][0]
        item["remaining"] = ["TOOL-2 remains open under its existing acceptance."]
        self.add_delivery_receipts(item, first)
        self.save_delivery_fixture(record, payload)

        added_source = "work/scope-for-tool-2.md"
        (self.root / added_source).write_text("Approved scope source for the remaining TOOL-2 outcome.\n", "utf-8")
        delivery["scope_sources"].append({
            "path": added_source,
            "sha256": h.hashlib.sha256((self.root / added_source).read_bytes()).hexdigest(),
        })
        self.save_delivery_fixture(record, payload)

        (self.root / "AGENTS.md").write_text("Changed original frozen source.\n", "utf-8")
        with self.assertRaisesRegex(ValueError, "stale"):
            self.save_delivery_fixture(record, payload)

    def test_delivery_changed_source_invalidates_previous_closure(self):
        record, payload = self.delivery_fixture()
        self.close_delivery_fixture(record, payload)
        (self.root / "sample.py").write_text("value = 43\n", "utf-8")
        with self.assertRaisesRegex(ValueError, "source pins are stale"):
            self.save_delivery_fixture(record, payload)
        self.assertEqual(self.delivery_stop().get("decision"), "block")

    def test_delivery_reopen_changed_source_requires_current_receipts_and_preserves_history(self):
        record, payload = self.delivery_fixture()
        self.close_delivery_fixture(record, payload)
        item = payload["continuity"]
        delivery = item["delivery"]
        historical_refs = {
            requirement["id"]: json.loads(json.dumps(requirement["evidence"]))
            for requirement in delivery["requirements"]
        }
        historical_bytes = {
            evidence["path"]: (self.root / evidence["path"]).read_bytes()
            for requirement in delivery["requirements"]
            for evidence in requirement["evidence"]
        }

        self.handle("UserPromptSubmit", **self.delivery_event,
                    prompt="Reopen the existing outcome after its implementation source changed",
                    turn_id="reopen-changed-source")
        delivery["status"] = "RUNNING"
        item["remaining"] = ["Revalidate the changed implementation source and recover the outcome."]
        for requirement in delivery["requirements"]:
            requirement["status"] = "OPEN"
        self.save_delivery_fixture(record, payload)

        (self.root / "sample.py").write_text("value = 43\n", "utf-8")
        self.save_delivery_fixture(record, payload)
        self.assertEqual(self.delivery_stop().get("decision"), "block")

        delivery["status"] = "JOB_CLOSED"
        item["remaining"] = []
        for requirement in delivery["requirements"]:
            requirement["status"] = "JOB_CLOSED"
        with self.assertRaisesRegex(ValueError, "fresh receipts for the complete current source scope"):
            self.save_delivery_fixture(record, payload)

        delivery["status"] = "RUNNING"
        item["remaining"] = ["Revalidate the changed implementation source and recover the outcome."]
        for requirement in delivery["requirements"]:
            requirement["status"] = "OPEN"
        self.save_delivery_fixture(record, payload)
        for requirement in delivery["requirements"]:
            self.add_delivery_receipts(item, requirement)
        delivery["status"] = "JOB_CLOSED"
        item["remaining"] = []
        self.save_delivery_fixture(record, payload)

        self.assertEqual(self.delivery_stop(), {})
        for requirement in delivery["requirements"]:
            self.assertEqual(requirement["evidence"][:2], historical_refs[requirement["id"]])
            self.assertNotEqual(
                requirement["evidence"][-1]["source_pins"]["sample.py"],
                historical_refs[requirement["id"]][0]["source_pins"]["sample.py"],
            )
        for path, body in historical_bytes.items():
            self.assertEqual((self.root / path).read_bytes(), body)

    def test_delivery_changed_authority_outside_source_scope_blocks_closure(self):
        record, payload = self.delivery_fixture()
        self.close_delivery_fixture(record, payload)
        authority = self.root / h.VERIFICATION_POLICY_PATH
        authority.write_text(authority.read_text("utf-8") + "\n", "utf-8")
        self.assertIn("PINNED_INPUT_CHANGED", h.continuity_read(
            self.root, self.state, self.delivery_event)["reasons"])
        self.assertEqual(self.delivery_stop().get("decision"), "block")

    def test_delivery_changed_receipt_cannot_reuse_previous_closure(self):
        record, payload = self.delivery_fixture()
        self.close_delivery_fixture(record, payload)
        receipt = self.root / payload["continuity"]["delivery"]["requirements"][0]["evidence"][0]["path"]
        body = json.loads(receipt.read_text("utf-8"))
        body["result"] = "NOT_VERIFIED"
        receipt.write_text(json.dumps(body), "utf-8")
        self.assertEqual(self.delivery_stop().get("decision"), "block")

    def test_delivery_new_prompt_does_not_erase_unverified_source_edits(self):
        self.delivery_fixture()
        self.edit()
        self.handle("UserPromptSubmit", **self.delivery_event, prompt="继续完成全部任务", turn_id="continue")
        self.assertEqual(self.delivery_stop().get("decision"), "block")

    def test_readonly_turn_can_answer_without_revalidating_historical_edits(self):
        self.edit()
        self.handle("UserPromptSubmit", prompt="只回答当前进度，不要修改或执行任务。", turn_id="report-only")
        self.assertEqual(self.handle("Stop"), {})
        self.assertTrue(self.state["mutation_observed"], "Historical verification debt must remain")

    def test_legacy_continuity_can_reconcile_without_new_delivery_opt_in(self):
        self.bind_continuity_scope()
        path = self.root / "work/checkpoint.json"
        payload = json.loads(path.read_text("utf-8"))
        payload["continuity"]["next_action"] = "Continue the unchanged full outcome after a new PO clarification"
        path.write_text(json.dumps(payload), "utf-8")
        event = {"session_id": "engineering-test-thread", "agent_id": "bounded-test-agent"}
        result = h.continuity_save(self.root, self.state, event, "work/checkpoint.json", "continuity")
        self.assertEqual(result["status"], "PINNED_CONTEXT")

    def test_delivery_newly_added_requirement_is_also_frozen(self):
        record, payload = self.delivery_fixture()
        requirements = payload["continuity"]["delivery"]["requirements"]
        extra = dict(requirements[0], id="TOOL-3", acceptance="Newly authorized complete tool operation")
        requirements.append(extra)
        self.save_delivery_fixture(record, payload)
        requirements.pop()
        with self.assertRaises(ValueError):
            self.save_delivery_fixture(record, payload)

    def test_delivery_outcome_class_cannot_be_changed_to_evade_e2e(self):
        record, payload = self.delivery_fixture()
        payload["continuity"]["delivery"]["requirements"][0]["outcome_class"] = "PRODUCT"
        with self.assertRaises(ValueError):
            self.save_delivery_fixture(record, payload)

    def test_product_delivery_rejects_tool_workflow_receipts(self):
        record, payload = self.delivery_fixture()
        # Fresh isolated task admission as a product requirement, no earlier guard.
        self.state.pop("delivery_guard")
        for requirement in payload["continuity"]["delivery"]["requirements"]:
            requirement["outcome_class"] = "PRODUCT"
        self.save_delivery_fixture(record, payload)
        with self.assertRaises(ValueError):
            self.close_delivery_fixture(record, payload)

    def test_readonly_instruction_does_not_exempt_new_source_mutation(self):
        self.handle("UserPromptSubmit", prompt="只回答当前进度，不要修改或执行任务。", turn_id="report-only")
        self.edit()
        self.assertEqual(self.handle("Stop").get("decision"), "block")

    def test_quoted_pause_policy_is_not_current_pause(self):
        prompts = [
            "请修复规则中‘暂停所有窗口’的错误描述并继续完成任务",
            "文档示例：等我审核完。请把它作为历史引用保留并继续实现",
            "先给我报告，然后继续完成全部修复",
            "#17和Slack全部包括，对的",
        ]
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                self.assertEqual(h.classify_turn_exit(prompt), "RUNNING")

    def test_readonly_turn_detects_explicit_ignored_source_change(self):
        record, payload = self.delivery_fixture()
        (self.root / ".gitignore").write_text("local-source/\n", "utf-8")
        source = self.root / "local-source/owned.py"
        source.parent.mkdir()
        source.write_text("value = 1\n", "utf-8")
        payload["continuity"]["source_paths"].append("local-source/owned.py")
        self.save_delivery_fixture(record, payload)
        self.handle("UserPromptSubmit", **self.delivery_event,
                    prompt="只回答当前进度，不要修改或执行任务。", turn_id="report-only")
        source.write_text("value = 2\n", "utf-8")
        self.assertEqual(self.delivery_stop().get("decision"), "block")

    def test_clear_then_readonly_turn_retains_frozen_implementation_scope(self):
        self.delivery_fixture()
        self.handle("SessionStart", source="clear", **self.delivery_event)
        self.assertNotIn("continuity", self.state)
        self.handle("UserPromptSubmit", **self.delivery_event,
                    prompt="只回答当前进度，不要修改或执行任务。", turn_id="cleared-report")
        self.edit()
        self.assertEqual(self.delivery_stop().get("decision"), "block")
        self.assertIn("sample.py", self.state["report_turn_changed_paths"])

    def test_report_only_scope_normalizes_dot_paths_before_intersection(self):
        record, payload = self.delivery_fixture()
        payload["continuity"]["source_paths"] = ["./sample.py"]
        self.save_delivery_fixture(record, payload)
        self.handle("UserPromptSubmit", **self.delivery_event,
                    prompt="只回答当前进度，不要修改或执行任务。", turn_id="dot-path-report")
        self.edit()
        output = self.delivery_stop()
        self.assertEqual(output.get("decision"), "block")
        self.assertEqual(self.state["report_turn_changed_paths"], ["sample.py"])

    def test_continuity_supports_more_than_twenty_evidence_paths(self):
        record, payload = self.delivery_fixture()
        item = payload["continuity"]
        for index in range(21):
            name = f"work/evidence-{index:02}.json"
            (self.root / name).write_text("{}\n", "utf-8")
            item["evidence_paths"].append(name)
        self.save_delivery_fixture(record, payload)
        self.assertEqual(len(item["evidence_paths"]), 22)

    def test_direct_english_pause_and_approval_wait_are_recognized(self):
        self.assertEqual(h.classify_turn_exit("Pause all tasks and wait for my review"), "PO_PAUSED")
        self.assertEqual(h.classify_turn_exit("Wait for my approval before continuing."), "APPROVAL_WAIT")
        self.delivery_fixture()
        self.handle("UserPromptSubmit", **self.delivery_event,
                    prompt="Pause all tasks and wait for my review", turn_id="english-pause")
        self.assertEqual(self.delivery_stop(), {})
        self.assertFalse(self.state["delivery_exit"]["closed"])
        self.assertEqual(self.state["delivery_exit"]["remaining_ids"], ["TOOL-1", "TOOL-2"])
        self.handle("UserPromptSubmit", **self.delivery_event,
                    prompt="Wait for my approval before continuing.", turn_id="english-approval")
        self.assertEqual(self.delivery_stop(), {})
        self.assertEqual(self.state["delivery_exit"]["mode"], "APPROVAL_WAIT")
        self.assertEqual(self.state["delivery_exit"]["remaining_ids"], ["TOOL-1", "TOOL-2"])
        self.assertEqual(
            h.classify_turn_exit("The note says ‘Pause all tasks and wait for my review’; continue with the fix"),
            "RUNNING",
        )
        self.assertEqual(
            h.classify_turn_exit("Pause all tasks and wait for my review, then continue the code fix"),
            "RUNNING",
        )

    def test_chinese_approval_wait_requires_the_entire_prompt_to_match(self):
        self.assertEqual(h.classify_turn_exit("批准前先等待"), "APPROVAL_WAIT")
        self.assertEqual(
            h.classify_turn_exit("批准前先等待这句话是错误的，请继续修复"),
            "RUNNING",
        )

    def test_english_status_only_request_is_report_but_mixed_work_continues(self):
        self.assertEqual(h.classify_turn_exit("What is the current status?"), "REPORT_ONLY")
        self.assertEqual(
            h.classify_turn_exit("Please tell me the current status only; do not modify anything"),
            "REPORT_ONLY",
        )
        self.assertEqual(
            h.classify_turn_exit("What is the current status? Please continue fixing the issue."),
            "RUNNING",
        )
        for action in ("add CSV export", "create the report", "remove the old rule",
                       "delete obsolete code", "ship the accepted repair"):
            with self.subTest(action=action):
                self.assertEqual(h.classify_turn_exit(
                    f"What is the current status? Please {action}."), "RUNNING")
        self.assertEqual(h.classify_turn_exit("报告当前进度，再新增导出入口"), "RUNNING")
        for prompt in ("What is the current status? Please do not modify anything.",
                       "报告当前进度。不要修改文件。"):
            with self.subTest(prompt=prompt):
                self.assertEqual(h.classify_turn_exit(prompt), "REPORT_ONLY")
        self.assertEqual(h.classify_turn_exit(
            "What is the current status? Please do not modify anything. Then add CSV export."),
            "RUNNING")

    def test_english_negation_does_not_swallow_a_later_positive_action(self):
        self.assertEqual(
            h.classify_turn_exit(
                "What is the current status? Please do not modify files and then implement the fix."
            ),
            "RUNNING",
        )
        self.assertEqual(
            h.classify_turn_exit(
                "请告诉我当前状态；do not modify files and then implement the fix."
            ),
            "RUNNING",
        )

    def test_user_prompt_text_cannot_suppress_real_turn_as_synthetic(self):
        self.delivery_fixture()
        self.handle("UserPromptSubmit", **self.delivery_event,
                    prompt="所有任务暂停，等我审核完", turn_id="real-pause-before-marker")
        self.assertEqual(self.state["turn_exit_mode"], "PO_PAUSED")
        prior_hash = self.state["last_prompt_hash"]
        self.handle("UserPromptSubmit", **self.delivery_event,
                    prompt="The <hook_prompt> handling is wrong; continue fixing it",
                    turn_id="real-user-marker-text")
        self.assertNotEqual(self.state["last_prompt_hash"], prior_hash)
        self.assertEqual(self.state["turn_id"], "real-user-marker-text")
        self.assertEqual(self.state["turn_exit_mode"], "RUNNING")

    def test_po_deferred_is_a_source_pinned_non_closure_exit(self):
        record, payload = self.delivery_fixture()
        item = payload["continuity"]
        delivery = item["delivery"]
        deferred = delivery["requirements"][1]
        deferred["po_source"] = "Direct PO instruction: defer TOOL-2 pending its named approval."
        source_path = "work/po-deferred.md"
        source_text = (
            "Product Owner direct instruction receipt\n"
            "PO_DEFERRED TOOL-2\n"
            f"{deferred['po_source']}\n"
        )
        (self.root / source_path).write_text(source_text, "utf-8")
        item["evidence_paths"].append(source_path)
        delivery["scope_sources"].append({
            "path": source_path,
            "sha256": h.hashlib.sha256((self.root / source_path).read_bytes()).hexdigest(),
        })
        self.save_delivery_fixture(record, payload)
        self.close_delivery_fixture(record, payload)
        deferred["status"] = "PO_DEFERRED"
        delivery["status"] = "PO_DEFERRED"
        item["remaining"] = ["TOOL-2 remains deferred until the named approval is received."]
        delivery["exit"] = {
            "reason": "PO_DEFERRED: TOOL-2 remains open under the direct PO instruction.",
            "evidence_path": source_path,
            "resume_condition": "Resume TOOL-2 only when its named Product Owner approval is received.",
        }
        self.save_delivery_fixture(record, payload)
        self.assertEqual(self.delivery_stop(), {})
        self.assertFalse(self.state["delivery_exit"]["closed"])
        self.assertEqual(self.state["delivery_exit"]["remaining_ids"], ["TOOL-2"])
        self.assertEqual(self.state["delivery_exit"]["mode"], "PO_DEFERRED")
        self.handle("UserPromptSubmit", **self.delivery_event,
                    prompt="Resume TOOL-2 and continue the approved work", turn_id="resume-deferred")
        self.assertEqual(self.delivery_stop().get("decision"), "block")
        self.save_delivery_fixture(record, payload)
        (self.root / source_path).write_text(source_text + "changed after admission\n", "utf-8")
        repeated_failure = self.delivery_stop()
        self.assertIs(repeated_failure.get("continue"), False)
        self.assertIn("Structured delivery could not be verified", repeated_failure["stopReason"])

    def test_po_deferred_requires_complete_ids_in_reason_and_source(self):
        record, payload = self.delivery_fixture()
        item = payload["continuity"]
        delivery = item["delivery"]
        delivery["requirements"] = [delivery["requirements"][0]]
        requirement = delivery["requirements"][0]
        requirement["status"] = "PO_DEFERRED"
        requirement["po_source"] = "Direct PO instruction: defer the named work until approval."
        delivery["status"] = "PO_DEFERRED"
        source_path = "work/po-deferred.md"
        item["evidence_paths"].append(source_path)
        delivery["exit"] = {
            "reason": "PO_DEFERRED: (TOOL-1)", "evidence_path": source_path,
            "resume_condition": "Wait for the named Product Owner approval.",
        }
        for reason_id, source_id, accepted in (
            ("TOOL-10", "TOOL-1", False),
            ("TOOL-1", "TOOL-10", False),
            ("TOOL-1", "TOOL-1.child", False),
            ("TOOL-1", "TOOL-1:other", False),
            ("TOOL-1", "TOOL-1/other", False),
            ("TOOL-1", "TOOL-1", True),
        ):
            with self.subTest(reason_id=reason_id, source_id=source_id):
                delivery["exit"]["reason"] = f"PO_DEFERRED: ({reason_id})"
                source = self.root / source_path
                source.write_text(f"Product Owner receipt: `{source_id}`\n{requirement['po_source']}\n", "utf-8")
                delivery["scope_sources"] = [
                    value for value in delivery["scope_sources"] if value["path"] != source_path
                ] + [{"path": source_path, "sha256": h.hashlib.sha256(source.read_bytes()).hexdigest()}]
                record.write_text(json.dumps(payload), "utf-8")
                if accepted:
                    h.continuity_record(self.root, "work/checkpoint.json", "continuity")
                else:
                    with self.assertRaisesRegex(ValueError, "must name"):
                        h.continuity_record(self.root, "work/checkpoint.json", "continuity")

    def test_po_deferred_cannot_hide_open_independent_work(self):
        record, payload = self.delivery_fixture()
        delivery = payload["continuity"]["delivery"]
        delivery["status"] = "PO_DEFERRED"
        delivery["requirements"][0]["status"] = "PO_DEFERRED"
        delivery["requirements"][0]["po_source"] = "Direct PO instruction: defer TOOL-1."
        source_path = "work/po-deferred.md"
        (self.root / source_path).write_text(
            "Product Owner direct instruction\nPO_DEFERRED TOOL-1\n"
            "Direct PO instruction: defer TOOL-1.\n", "utf-8"
        )
        payload["continuity"]["evidence_paths"].append(source_path)
        delivery["exit"] = {
            "reason": "PO_DEFERRED: TOOL-1 remains open.",
            "evidence_path": source_path,
            "resume_condition": "Resume after the named approval.",
        }
        with self.assertRaisesRegex(ValueError, "every remaining requirement"):
            self.save_delivery_fixture(record, payload)

    def test_chinese_direct_po_receipt_can_authorize_exact_deferred_ids(self):
        record, payload = self.delivery_fixture()
        item = payload["continuity"]
        delivery = item["delivery"]
        source_path = "work/po-chinese.md"
        source_text = "产品负责人直接指示延期 TOOL-1、TOOL-2，等待审核。"
        (self.root / source_path).write_text(source_text, "utf-8")
        item["evidence_paths"].append(source_path)
        delivery["scope_sources"].append({
            "path": source_path, "sha256": h.hashlib.sha256((self.root / source_path).read_bytes()).hexdigest(),
        })
        for requirement in delivery["requirements"]:
            requirement.update(status="PO_DEFERRED", po_source=source_text)
        delivery["status"] = "PO_DEFERRED"
        delivery["exit"] = {"reason": "PO_DEFERRED：TOOL-1、TOOL-2", "evidence_path": source_path,
                            "resume_condition": "收到产品负责人明确恢复指令后继续。"}
        self.save_delivery_fixture(record, payload)
        self.assertEqual(self.delivery_stop(), {})
        self.assertFalse(self.state["delivery_exit"]["closed"])

    def test_direct_pause_preserves_remaining_without_closure(self):
        self.delivery_fixture()
        self.handle("UserPromptSubmit", **self.delivery_event, prompt="所有任务暂停，等我审核完", turn_id="pause")
        self.assertEqual(self.delivery_stop(), {})
        self.assertFalse(self.state["delivery_exit"]["closed"])
        self.assertEqual(self.state["delivery_exit"]["remaining_ids"], ["TOOL-1", "TOOL-2"])

    def test_delivery_pending_effect_prevents_closure(self):
        effect = "operation-cth-publish-17 remains unresolved pending durable readback"
        record, payload = self.delivery_fixture([effect])
        payload["continuity"]["pending_effects"] = []
        with self.assertRaisesRegex(ValueError, "ledger"):
            self.close_delivery_fixture(record, payload)

    def test_effect_ledger_rejects_non_object_entries_with_type_error(self):
        effect = "operation-cth-publish-24 rejects malformed ledger entries"
        record, payload = self.delivery_fixture([effect])
        payload["continuity"]["delivery"]["effect_ledger"][0] = "not-an-object"
        with self.assertRaisesRegex(TypeError, "Invalid external-effect ledger entry"):
            self.save_delivery_fixture(record, payload)

    def test_effect_receipt_rejects_non_object_json_with_type_error(self):
        effect = "operation-cth-publish-25 rejects non-object terminal receipts"
        record, payload = self.delivery_fixture([effect])
        receipt_path = self.resolve_effect_fixture(payload, effect)
        receipt_path.write_text(json.dumps(["not-an-object"]), "utf-8")
        payload["continuity"]["delivery"]["effect_ledger"][0]["sha256"] = (
            h.hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        )
        with self.assertRaisesRegex(TypeError, "receipt must be a JSON object"):
            self.save_delivery_fixture(record, payload)

    def test_nonclosure_history_rejects_non_object_with_type_error(self):
        record, payload = self.delivery_fixture()
        self.block_delivery_fixture(record, payload)
        self.state["delivery_guard"]["nonclosure_exits"] = []
        with self.assertRaisesRegex(TypeError, "non-closure exit history is invalid"):
            self.save_delivery_fixture(record, payload)

    def test_pending_effect_can_close_only_with_its_frozen_resolution_receipt(self):
        effect = "operation-cth-publish-18 remains unresolved pending durable readback"
        record, payload = self.delivery_fixture([effect])
        receipt_path = self.resolve_effect_fixture(payload, effect)
        self.close_delivery_fixture(record, payload)
        self.assertEqual(self.delivery_stop(), {})
        reopened_state = {}
        reopened_event = {"session_id": "engineering-reopen-thread", "agent_id": "bounded-test-agent"}
        original_receipt = receipt_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "first be frozen as PENDING"):
            h.continuity_save(
                self.root, reopened_state, reopened_event, "work/checkpoint.json", "continuity"
            )
        self.assertEqual(receipt_path.read_bytes(), original_receipt)
        receipt_path.write_text(receipt_path.read_text("utf-8") + "\n", "utf-8")
        self.assertEqual(self.delivery_stop().get("decision"), "block")

    def test_long_running_delivery_can_append_and_freeze_a_new_pending_effect(self):
        first = "operation-cth-publish-19 remains unresolved pending durable readback"
        second = "operation-cth-publish-20 is newly pending in the same task"
        record, payload = self.delivery_fixture([first])
        item = payload["continuity"]
        ledger = item["delivery"]["effect_ledger"]
        item["pending_effects"].append(second)
        ledger.append({"pending_effect_sha256": h._pending_effect_id(second), "status": "PENDING"})
        self.save_delivery_fixture(record, payload)
        self.assertEqual(
            self.state["delivery_guard"]["pending_effects"][h._pending_effect_id(second)],
            {"status": "PENDING"},
        )

        item["pending_effects"].remove(second)
        ledger.pop()
        with self.assertRaisesRegex(ValueError, "cannot remove"):
            self.save_delivery_fixture(record, payload)

    def test_effect_admission_reserves_capacity_for_resolution_and_outcomes(self):
        effect = "First bounded publication pending readback"
        record, payload = self.delivery_fixture([effect])
        self.resolve_effect_fixture(payload, effect)
        self.save_delivery_fixture(record, payload)
        item = payload["continuity"]
        required_capacity = len(item["evidence_paths"]) + 2 * len(item["delivery"]["requirements"])
        with mock.patch.object(h, "MAX_EVIDENCE_PATHS", required_capacity):
            self.save_delivery_fixture(record, payload)
            second = "Another publication must reserve a future receipt slot"
            item["pending_effects"].append(second)
            item["delivery"]["effect_ledger"].append({
                "pending_effect_sha256": h._pending_effect_id(second), "status": "PENDING",
            })
            with self.assertRaisesRegex(ValueError, "Evidence capacity"):
                self.save_delivery_fixture(record, payload)
            item["pending_effects"].pop()
            item["delivery"]["effect_ledger"].pop()
            self.close_delivery_fixture(record, payload)
            self.assertEqual(self.delivery_stop(), {})

    def test_new_effect_cannot_enter_the_ledger_already_resolved(self):
        first = "operation-cth-publish-21 remains unresolved pending durable readback"
        second = "operation-cth-publish-22 may not bypass initial pending admission"
        record, payload = self.delivery_fixture([first])
        item = payload["continuity"]
        item["pending_effects"].append(second)
        item["delivery"]["effect_ledger"].append({
            "pending_effect_sha256": h._pending_effect_id(second), "status": "PENDING",
        })
        self.resolve_effect_fixture(payload, second)
        with self.assertRaisesRegex(ValueError, "first be frozen as PENDING"):
            self.save_delivery_fixture(record, payload)

    def test_empty_frozen_effect_ledger_cannot_admit_already_resolved_effect(self):
        record, payload = self.delivery_fixture()
        self.assertEqual(self.state["delivery_guard"]["pending_effects"], {})
        effect = "A new remote publication needs pending admission before its resolution"
        item = payload["continuity"]
        item["pending_effects"].append(effect)
        item["delivery"]["effect_ledger"].append({
            "pending_effect_sha256": h._pending_effect_id(effect), "status": "PENDING",
        })
        self.resolve_effect_fixture(payload, effect)
        with self.assertRaisesRegex(ValueError, "first be frozen as PENDING"):
            self.save_delivery_fixture(record, payload)

    def test_resolved_effect_receipt_survives_a_later_source_edit(self):
        effect = "operation-cth-publish-23 terminal readback must not be replayed"
        record, payload = self.delivery_fixture([effect])
        receipt_path = self.resolve_effect_fixture(payload, effect)
        self.save_delivery_fixture(record, payload)
        original_receipt = receipt_path.read_bytes()

        source = self.root / "sample.py"
        source.write_text(source.read_text("utf-8") + "\n# later authorized source revision\n", "utf-8")
        self.save_delivery_fixture(record, payload)

        validation = h.validate_delivery(self.root, payload["continuity"])
        self.assertEqual(
            validation["effect_ledger"][h._pending_effect_id(effect)]["status"], "RESOLVED"
        )
        self.assertEqual(
            self.state["delivery_guard"]["pending_effects"][h._pending_effect_id(effect)]["status"],
            "RESOLVED",
        )
        self.assertEqual(receipt_path.read_bytes(), original_receipt)

    def test_delivery_receipt_cannot_omit_other_in_scope_source(self):
        record, payload = self.delivery_fixture()
        self.close_delivery_fixture(record, payload)
        for requirement in payload["continuity"]["delivery"]["requirements"]:
            for evidence in requirement["evidence"]:
                evidence["source_pins"].pop("AGENTS.md", None)
                path = self.root / evidence["path"]
                receipt = json.loads(path.read_text("utf-8"))
                receipt["source_pins"] = evidence["source_pins"]
                path.write_text(json.dumps(receipt), "utf-8")
                evidence["sha256"] = h.hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):
            self.save_delivery_fixture(record, payload)

if __name__ == "__main__":
    unittest.main()
