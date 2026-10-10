import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "lumenis_hooks.py"
ENGINEERING = Path(__file__).resolve().parents[1] / "engineering.py"
spec = importlib.util.spec_from_file_location("lumenis_hooks", HOOK)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
eng_spec = importlib.util.spec_from_file_location("lumenis_engineering", ENGINEERING)
eng = importlib.util.module_from_spec(eng_spec)
eng_spec.loader.exec_module(eng)

class EngineeringTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lumenis-test-")
        self.root = Path(self.temp.name) / "序境"
        self.root.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "engineering-test@example.invalid")
        self.git("config", "user.name", "Engineering test")
        (self.root / "AGENTS.md").write_text("# LUMENIS test fixture", "utf-8")
        (self.root / "sample.py").write_text("value = 1\n", "utf-8")
        self.git("add", "AGENTS.md", "sample.py")
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
        self.temp.cleanup()

    def git(self, *args):
        p = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, encoding="utf-8")
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
        for data, expected in [({"exit_code": 1}, 1), ({"output": "Process exited with code 0"}, 0), ({"isError": True}, 1), ("all good", None), ({"exit_code": True}, None)]:
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
                re.compile(pattern, re.I)
        routes = eng.route_task("Flutter 页面 bug 阻塞，需要研究依赖和修复", ["app/lib/main.dart"])["routes"]
        self.assertTrue(any(item["skill"] == "lumenis-flutter-runtime" for item in routes))
        self.assertTrue(any(item["skill"] == "lumenis-testing" for item in routes))

    def test_engineering_mcp_has_no_hidden_workstation_helper(self):
        text = ENGINEERING.read_text("utf-8")
        self.assertNotIn(r"D:\\codex\\agent-skills", text)
        self.assertIn("def source_read(", text)
        self.assertIn("def route_task(", text)

    def test_utf8_hook_subprocess(self):
        event = {"hook_event_name": "PreToolUse", "cwd": str(self.root), "session_id": "unit-test", "tool_name": "Bash", "tool_input": {"command": "git reset --hard HEAD"}}
        proc = subprocess.run([sys.executable, "-X", "utf8", str(HOOK)], input=json.dumps(event, ensure_ascii=False).encode(), capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
        state = h.state_file(event, self.root)
        state.unlink(missing_ok=True)

if __name__ == "__main__":
    unittest.main()
