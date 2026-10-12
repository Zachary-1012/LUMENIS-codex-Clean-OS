"""Allowlisted local engineering utilities; no production writes or arbitrary shell."""
from __future__ import annotations
import argparse
import ast
import configparser
import hashlib
from importlib import metadata as importlib_metadata
import importlib.util
import json
import os
import re
import shlex
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = ROOT / ".codex/hooks/lumenis_hooks.py"
OWNER = ROOT / "00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md"
VERIFICATION_POLICY_RELATIVE = Path("00-GOVERNANCE/LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json")
VERIFICATION_POLICY = ROOT / VERIFICATION_POLICY_RELATIVE

TEXT_SOURCE = {".py", ".dart", ".md", ".toml", ".yaml", ".yml", ".json", ".js", ".ts", ".txt", ".ps1", ".cmd", ".rules", ".ini", ".cfg"}
MAX_VERIFICATION_TIMEOUT_SECONDS = 300
MAX_VERIFICATION_DIAGNOSTIC_BYTES = 65536
PYTEST_CONFIG_NAMES = ("pytest.toml", ".pytest.toml", "pytest.ini", ".pytest.ini", "pyproject.toml", "tox.ini", "setup.cfg")
# Exact reviewed snapshots only; missing or changed source is never admitted.
PYTEST_SOURCE_REVIEW_RECEIPTS = {
    "tests/conftest.py": {
        "sha256": "274b8adfc3a6f54c2c4d6d74c6763612b5c2774873049ef3e571ce5419c782bf",
        "owners": {
            "C5": {
                "purpose": "Reviewed autouse guard blocks public TCP connections while allowing loopback and private targets.",
                "allowed_imports": ["socket"], "allowed_plugins": [],
            },
            "C3": {
                "purpose": "Reviewed isolated business fixtures use temporary DB state, hermetic seed access, and the outbound socket guard.",
                "allowed_imports": ["socket"], "allowed_plugins": [],
            },
            "C4": {
                "purpose": "Reviewed isolated contract fixtures use database-copy isolation, offline seed state, and the outbound socket guard.",
                "allowed_imports": ["socket"], "allowed_plugins": [],
            },
        },
    },
    "tests/test_saved_work_pptx_exports.py": {
        "sha256": "e9824de19c34802d771a818579122da49466d267333880c46b54007e6d798d31",
        "owners": {
            "C5": {
                "purpose": "Reviewed in-memory PPTX export tests patch socket.create_connection to fail and assert no network access.",
                "allowed_imports": ["socket"], "allowed_plugins": [],
            },
        },
    },
    "tests/test_business_approved_source_continuity.py": {
        "sha256": "a7a1d05a5ce2cd7c7b4efca8769042dad06feb26c87deb681ff4b29534b68467",
        "owners": {
            "C3": {
                "purpose": "Reviewed isolated approved-source continuity regression using only the named business-result and saved-document fixture plugins.",
                "allowed_imports": [],
                "allowed_plugins": [
                    "tests.test_business_result_continuity",
                    "tests.test_saved_document_workflow",
                ],
            },
        },
    },
    "tests/test_business_result_continuity.py": {
        "sha256": "e0ab0f0f4b8827c5380469ee8c7384f13ddd114b00280ddb1c5dccf0d0bc9264",
        "owners": {
            "C3": {
                "purpose": "Reviewed business-result fixture provider uses the temporary isolated workspace and its saved-document workspace fixture.",
                "allowed_imports": [],
                "allowed_plugins": ["tests.test_saved_document_workflow"],
            },
        },
    },
    "tests/test_saved_document_workflow.py": {
        "sha256": "f6527604cfcd050dcab2316430bd00a884de48f0627b1b3d61af9fddf5155ea2",
        "owners": {
            "C3": {
                "purpose": "Reviewed saved-document workspace fixture provider; this exact C3 node loads only the isolated workspace fixture, while unrelated process-interruption test functions are not collected.",
                "allowed_imports": ["subprocess"], "allowed_plugins": [],
            },
        },
    },
}
DENY_SOURCE = re.compile(r"(^|/)(\.git|\.env[^/]*|auth\.json|credentials[^/]*|[^/]*cookies?[^/]*|[^/]*profile[^/]*|[^/]*secrets?[^/]*)(/|$)", re.I)
ROUTES = [
    ("testing", r"test|bug|fix|测试|回归|修复", "approved isolated unit/integration regressions; actual user E2E remains separate"),
    ("current-docs", r"api|sdk|package|dependenc|library|framework|\u6587\u6863|\u4f9d\u8d56|\u7248\u672c", "Context7 / openaiDeveloperDocs / official docs"),
    ("source-navigation", r"refactor|implement|source|code|owner|\u4ee3\u7801|\u5b9e\u73b0|\u91cd\u6784|\u5f00\u53d1", "git / rg / engineering"),
    ("database-integrity", r"database|sqlite|migration|repository|\u6570\u636e\u5e93|\u8fc1\u79fb|\u6301\u4e45\u5316", "canonical database owner; safe data-consistency and recovery evidence"),
    ("python-contracts", r"python|flask|backend|endpoint|\u540e\u7aef|\u63a5\u53e3", "Python AST/compile and applicable static, security, and data checks"),
    ("flutter-runtime", r"flutter|dart|widget|app/|mobile|desktop|\u79fb\u52a8|\u684c\u9762|\u9875\u9762", "Dart/Flutter analysis and target build; actual promised surface acceptance"),
    ("browser-debug", r"browser|web|console|network|playwright|\u6d4f\u89c8\u5668|\u7f51\u9875|\u524d\u7aef", "verified browser/chrome/playwright tooling"),
    ("security-effects", r"permission|auth|cookie|secret|security|publish|\u6743\u9650|\u8ba4\u8bc1|\u5b89\u5168|\u53d1\u5e03", "Codex Security; Permission/effect owner"),
    ("release-completion", r"test|accept|e2e|bug|fix|\u6d4b\u8bd5|\u9a8c\u6536|\u4fee\u590d|\u62a5\u9519", "retained compile/static/security/data/recovery checks and real-user E2E; isolated unit/integration regressions follow current machine policy"),
    ("release-ci", r"release|deploy|ci\b|workflow|\u4e0a\u7ebf|\u90e8\u7f72|\u6d41\u6c34\u7ebf", "GitHub; approved deployment provider"),
    ("research-adoption", r"research|compare|oss|license|\u7814\u7a76|\u6bd4\u8f83|\u5f00\u6e90|\u9009\u578b", "current primary sources; licenses"),
    ("review-delegation", r"review|audit|agent|\u5ba1\u8ba1|\u5ba1\u67e5|\u5e76\u884c", "bounded native subagents/reviewer"),
    ("recovery-continuity", r"resume|continue|compact|handoff|\u7ee7\u7eed|\u63a5\u624b|\u6062\u590d", "checkpoint; fresh local/remote state"),
]


def current_verification_policy():
    try:
        contract = json.loads((ROOT / VERIFICATION_POLICY_RELATIVE).read_text("utf-8-sig"))
        policy = contract.get("verification_policy")
        return policy if isinstance(policy, dict) else None
    except (OSError, json.JSONDecodeError, AttributeError):
        return None


def module_suite_policy(policy=None):
    policy = current_verification_policy() if policy is None else policy
    if not isinstance(policy, dict):
        return {"status": "POLICY_UNAVAILABLE", "create_allowed": False, "run_allowed": False, "renamed_suites_allowed": False}
    return {
        "status": "PROHIBITED" if policy.get("run_unit_integration_allowed") is not True else "POLICY_CONTROLLED",
        "create_allowed": policy.get("create_unit_integration_allowed") is True,
        "run_allowed": policy.get("run_unit_integration_allowed") is True,
        "renamed_suites_allowed": policy.get("renamed_module_suites_allowed") is True,
    }


def applicable_retained_checks(paths, policy):
    retained = set(policy.get("retained_checks", [])) if isinstance(policy, dict) else set()
    joined = " ".join(paths).lower()
    suffixes = {Path(path).suffix.lower() for path in paths}
    checks = []
    if suffixes.intersection({".py", ".dart", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".rs"}):
        checks.extend(("compilation", "static_quality"))
    if re.search(r"security|permission|auth|effect|cookie", joined):
        checks.append("security_permission")
    if re.search(r"database|sqlite|migration|canonical|evidence|data", joined):
        checks.append("data_consistency")
    if re.search(r"runtime|recovery|backup|restore|supervisor|startup", joined):
        checks.append("recovery")
    if re.search(r"app/|experience|screen|route|view_model|api", joined):
        checks.append("real_user_e2e")
    if re.search(r"release|deploy|package|workflow|ci", joined):
        checks.append("release_verification")
    if not checks:
        checks.append("static_quality")
    return [check for check in dict.fromkeys(checks) if check in retained]
def _redact(text: str) -> str:
    text = re.sub(r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{15,})", "[REDACTED]", text)
    return re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[REDACTED]", text)

def _safe_source_path(value: str) -> Path:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError("Relative source path required")
    candidate = Path(value)
    if candidate.is_absolute() or candidate.drive or ".." in candidate.parts:
        raise ValueError("Path escape rejected")
    path = (ROOT / candidate).resolve()
    relative = path.relative_to(ROOT).as_posix()
    if DENY_SOURCE.search(relative) or path.suffix.lower() not in TEXT_SOURCE:
        raise ValueError("Protected/non-source path")
    return path

def source_read(path: str, start: int = 1, limit: int = 100):
    if not isinstance(start, int) or start < 1 or not isinstance(limit, int) or not 1 <= limit <= 250:
        raise ValueError("Invalid line bounds")
    source = _safe_source_path(path)
    if not source.is_file():
        raise ValueError("Source path is not a file")
    if source.stat().st_size > 2_000_000:
        raise ValueError("Use bounded native search for large files")
    lines = source.read_text("utf-8-sig", errors="replace").splitlines()
    body = "\n".join(f"{i+1}: {line}" for i, line in enumerate(lines[start-1:start-1+limit], start-1))
    return {"path": path, "start": start, "total_lines": len(lines), "text": _redact(body)[:28000]}

def route_task(task: str, paths=None):
    if not isinstance(task, str) or len(task) > 6000:
        raise ValueError("Task exceeds limit")
    if paths is not None and (not isinstance(paths, list) or len(paths) > 100 or any(not isinstance(x, str) for x in paths)):
        raise ValueError("Invalid paths")
    text = task + " " + " ".join(paths or [])
    hits = [{"skill": "lumenis-" + name, "tools": tools} for name, pattern, tools in ROUTES if re.search(pattern, text, re.I)]
    return {"routes": hits, "policy": "Load only matching skills; no automatic authorization; unavailable tools need verified native alternatives."}

def _source_fingerprint(paths):
    if not isinstance(paths, list) or len(paths) > 100:
        raise ValueError("Provide at most 100 explicit paths")
    values = {}
    for rel in sorted(set(paths)):
        path = _safe_source_path(rel)
        values[rel] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "ABSENT"
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()

def static_check(paths):
    before = _source_fingerprint(paths)
    checks = []
    for rel in paths:
        path = _safe_source_path(rel)
        if not path.is_file():
            checks.append({"path": rel, "status": "ABSENT"})
        elif path.suffix != ".py":
            checks.append({"path": rel, "status": "NOT_RUN", "reason": "Use native analyzer"})
        else:
            try:
                ast.parse(path.read_text("utf-8-sig"), filename=rel)
                checks.append({"path": rel, "status": "PASS"})
            except (SyntaxError, UnicodeError) as error:
                checks.append({"path": rel, "status": "FAIL", "error": str(error)})
    return {"fingerprint": before, "unchanged": before == _source_fingerprint(paths), "checks": checks, "acceptance": "STATIC_ONLY_NOT_PRODUCT_ACCEPTANCE"}

def validation_plan(paths):
    _source_fingerprint(paths)
    joined = " ".join(paths)
    plan = []
    if ".py" in joined:
        plan.append("Compile Python source and apply retained static-quality checks; run only bounded affected unit/integration regressions when the current machine policy permits, and keep real-user E2E separate.")
    if ".dart" in joined:
        plan.append("Run Dart/Flutter analysis and build the promised target; verify the actual user flow on the applicable product surface.")
    if re.search(r"database|migration|permission|evidence|runtime", joined, re.I):
        plan.append("Preserve production data; perform applicable permission, data-consistency, runtime, and recovery verification through existing owners.")
    if re.search(r"app/|experience|screen", joined, re.I):
        plan.append("Use the current screen specification and blocking Experience audits; complete the real-user E2E and recovery path.")
    plan.append("Complete the owning capability's real-user E2E with permitted real inputs, useful result, applicable save/reopen behavior, recovery, and evidence evaluation.")
    policy = current_verification_policy()
    return {
        "paths": paths,
        "plan": plan,
        "module_suite_policy": module_suite_policy(policy),
        "execution": "NOT_RUN; planning only. Retain exact compile/static/build, security, data, runtime, recovery, and real-E2E evidence as applicable.",
    }

def git(*args):
    p = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, encoding="utf-8", errors="strict", timeout=15)
    if p.returncode: raise RuntimeError("Git read failed")
    return p.stdout.strip()

def checked_path(value):
    path = ROOT / value
    if Path(value).is_absolute() or not path.resolve().is_relative_to(ROOT):
        raise ValueError("Path must stay in the authorized repository")
    if any(x.lower() in {".git", "data", "node_modules"} for x in path.relative_to(ROOT).parts) or path.name.startswith(".env"):
        raise ValueError("Sensitive/runtime path is not supported")
    return path


def _load_hooks():
    spec = importlib.util.spec_from_file_location("lumenis_engineering_hooks", HOOK_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("LUMENIS continuity hooks are unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HOOKS = _load_hooks()


def _continuity_identity():
    thread_id = os.environ.get("CODEX_THREAD_ID", "").strip()
    session_id = os.environ.get("CODEX_SESSION_ID", "").strip()
    if thread_id and session_id and thread_id != session_id:
        raise ValueError("Conflicting Codex thread/session identity")
    identity = thread_id or session_id
    if not identity or identity.casefold() == "missing":
        raise ValueError("A verified Codex thread/session identity is required")
    return {
        "session_id": identity,
        "agent_id": os.environ.get("CODEX_AGENT_ID", "").strip(),
    }


def _continuity_record_path(value):
    if not isinstance(value, str) or not value or len(value) > 600:
        raise ValueError("An existing repository work JSON record is required")
    relative = Path(value)
    if (relative.is_absolute() or relative.drive or ".." in relative.parts
            or not relative.parts or relative.parts[0].casefold() != "work"):
        raise ValueError("Continuity records must be existing files under work/")
    if relative.suffix.lower() != ".json":
        raise ValueError("Continuity record must be a JSON file")
    path = checked_path(value)
    work_root = (ROOT / "work").resolve()
    resolved = path.resolve()
    if not resolved.is_relative_to(work_root) or not resolved.is_file():
        raise ValueError("Continuity record must be an existing file under work/")
    return resolved.relative_to(ROOT.resolve()).as_posix()


def continuity(params):
    if not isinstance(params, dict):
        raise ValueError("Continuity parameters must be an object")
    mode = params["mode"]
    if not isinstance(mode, str) or mode not in {"save", "read"}:
        raise ValueError("Continuity mode must be save or read")
    if mode == "save" and set(params) != {"mode", "record", "section"}:
        raise ValueError("Continuity save requires exactly mode, record, and section")
    if mode == "read" and set(params) not in ({"mode"}, {"mode", "record", "section"}):
        raise ValueError("Continuity read accepts mode, optionally with record and section together")
    record = section = None
    if "record" in params:
        record = _continuity_record_path(params["record"])
        section = params["section"]
        if not isinstance(section, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", section):
            raise ValueError("Continuity section must be a bounded top-level JSON field")

    event = _continuity_identity()
    state_path = HOOKS.state_file(event, ROOT)
    with HOOKS.locked(state_path):
        if state_path.is_file():
            state = json.loads(state_path.read_text("utf-8"))
            if not isinstance(state, dict):
                raise ValueError("Engineering continuity state is invalid")
        else:
            state = {}
        if mode == "save":
            result = HOOKS.continuity_save(ROOT, state, event, record, section)
            HOOKS.save(state_path, state)
        else:
            result = HOOKS.continuity_read(ROOT, state, event)
            if (record is not None and result.get("record") is not None and
                    (result.get("record") != record or result.get("section") != section)):
                raise ValueError("Requested record does not match this session's pinned owner record")
    return result

def repo_truth():
    fetch = ROOT / ".git/FETCH_HEAD"
    return {"root": str(ROOT), "head": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
            "origin_main_cached": git("rev-parse", "origin/main"),
            "fetch_record_mtime": fetch.stat().st_mtime if fetch.exists() else None,
            "remote_is_freshly_queried": False,
            "dirty_count": len(git("status", "--porcelain=v1", "-uall").splitlines()),
            "note": "Read-only inventory. Fetch origin before making remote-current claims; preserve existing local work."}

def verification_plan(paths):
    if not isinstance(paths, list) or len(paths) > 100: raise ValueError("At most 100 paths")
    for value in paths:
        if not isinstance(value, str): raise ValueError("Expected path strings")
        checked_path(value)
    policy = current_verification_policy()
    if policy is None:
        return {"input_paths": paths, "status": "VERIFICATION_POLICY_UNAVAILABLE", "required_checks": [],
                "module_suite_policy": module_suite_policy(policy), "executed": False}
    required = applicable_retained_checks(paths, policy)
    return {"input_paths": paths, "status": "PLANNED_NOT_EXECUTED", "required_checks": required,
            "module_suite_policy": module_suite_policy(policy),
            "acceptance": "Complete applicable real-user E2E with permitted real inputs and useful results; preserve save/reopen, recovery, and evidence evaluation.",
            "executed": False}

def source_owner(query):
    if not isinstance(query, str) or len(query) > 80: raise ValueError("Query exceeds limit")
    lines = OWNER.read_text("utf-8-sig").splitlines()
    selected = set()
    for i, line in enumerate(lines):
        if query.casefold() in line.casefold(): selected.update(range(max(0, i-1), min(len(lines), i+3)))
        if len(selected) >= 60: break
    return {"source": str(OWNER.relative_to(ROOT)), "query": query,
            "matches": [{"line": i+1, "text": lines[i]} for i in sorted(selected)[:60]],
            "note": "Current local owner document is routing evidence, not proof of implementation."}

def runtime_health():
    started = time.monotonic()
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs): return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open("http://127.0.0.1:8201/healthz", timeout=5) as response:
            status = response.status
        return {"http_status": status, "reachable": True, "elapsed_seconds": round(time.monotonic()-started, 3), "product_e2e_verified": False}
    except Exception as error:
        return {"reachable": False, "error_type": type(error).__name__, "status": "UNAVAILABLE", "product_e2e_verified": False}


def _python_command(token):
    return token in {"python", "python3", "python.exe", sys.executable, Path(sys.executable).name}


def _tool_command(token, tool):
    return isinstance(token, str) and token.casefold() in {tool, f"{tool}.bat", f"{tool}.cmd", f"{tool}.exe"}


def _resolve_tool_argv(tool, args):
    """Resolve an installed native executable without shell or PATH mutation."""
    if tool not in {"dart", "flutter"} or not isinstance(args, list):
        raise ValueError("Unsupported installed tool entry")
    candidates = (shutil.which(f"{tool}.exe"), shutil.which(f"{tool}.com"), shutil.which(tool))
    launcher = None
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if path.suffix.casefold() in {".exe", ".com"} and path.is_file():
            return [str(path.resolve()), *args]
        if path.suffix.casefold() in {".bat", ".cmd"} and path.is_file():
            launcher = path.resolve()
            sibling = launcher.with_name(f"{tool}.exe")
            if sibling.is_file():
                return [str(sibling.resolve()), *args]
            if tool == "dart":
                flutter_sdk_dart = launcher.parent / "cache" / "dart-sdk" / "bin" / "dart.exe"
                if flutter_sdk_dart.is_file():
                    return [str(flutter_sdk_dart.resolve()), *args]
            break

    if launcher is not None and tool == "flutter":
        flutter_bin = launcher.parent
        dart = flutter_bin / "cache" / "dart-sdk" / "bin" / "dart.exe"
        snapshot = flutter_bin / "cache" / "flutter_tools.snapshot"
        if dart.is_file() and snapshot.is_file():
            return [str(dart.resolve()), "--disable-dart-dev", str(snapshot.resolve()), *args]
    raise ValueError(
        f"{tool.title()} executable is UNAVAILABLE: no callable installed executable was resolved; "
        "install state and PATH were left unchanged"
    )


def _verification_source_args(values, scope_paths, suffixes):
    if not values or len(values) > 30:
        raise ValueError("A bounded list of explicit source paths is required")
    normalized = []
    scope = set(scope_paths)
    for value in values:
        if not isinstance(value, str) or not value or len(value) > 600:
            raise ValueError("Invalid verification source path")
        path = HOOKS.continuity_path(ROOT, value)
        relative = path.relative_to(ROOT.resolve()).as_posix()
        if relative not in scope:
            raise ValueError("Verification command path is outside the bound Owner scope")
        if path.suffix.lower() not in suffixes or not path.is_file():
            raise ValueError("Verification command path is missing or has an unsupported type")
        normalized.append(relative)
    if len(set(normalized)) != len(normalized):
        raise ValueError("Duplicate verification source path")
    return normalized


def _flutter_package_root(scope_paths):
    roots = set()
    for relative in scope_paths:
        source = HOOKS.continuity_path(ROOT, relative)
        if source.suffix.lower() != ".dart":
            continue
        current = source.parent
        while current != ROOT.resolve() and current.is_relative_to(ROOT.resolve()):
            if (current / "pubspec.yaml").is_file():
                roots.add(current)
                break
            current = current.parent
    if len(roots) != 1:
        raise ValueError("Flutter verification requires bound Dart sources in one existing pubspec package")
    return next(iter(roots))


def _package_relative(path, package_root):
    resolved = HOOKS.continuity_path(ROOT, path)
    if not resolved.is_relative_to(package_root) or resolved == package_root:
        raise ValueError("Flutter verification target must stay inside the bound package")
    return resolved.relative_to(package_root).as_posix()


def _unittest_target(path, test_name):
    if not re.fullmatch(r"test_[A-Za-z0-9_]+", test_name):
        raise ValueError("Targeted unittest must name one exact test method")
    source = path.read_text("utf-8-sig")
    tree = ast.parse(source, filename=str(path))
    names = [node.name for node in ast.walk(tree)
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")]
    if names.count(test_name) != 1 or sum(test_name in name for name in names) != 1:
        raise ValueError("Targeted unittest name must resolve to one exact test method")


def _pytest_version_tuple():
    try:
        match = re.match(r"^(\d+)\.(\d+)", importlib_metadata.version("pytest"))
    except importlib_metadata.PackageNotFoundError:
        return (0, 0)
    return (int(match.group(1)), int(match.group(2))) if match else (0, 0)


def _pytest_config_matches(path):
    """Recognize only configuration files supported by the installed pytest."""
    if path.name in {"pytest.ini", ".pytest.ini"}:
        return True
    if path.name in {"pytest.toml", ".pytest.toml"}:
        return _pytest_version_tuple() >= (9, 0)
    try:
        if path.name == "pyproject.toml":
            document = tomllib.loads(path.read_text("utf-8-sig"))
            pytest_config = document.get("tool", {}).get("pytest", {})
            if not isinstance(pytest_config, dict):
                return False
            return "ini_options" in pytest_config or (
                "pytest" in document.get("tool", {}) and _pytest_version_tuple() >= (9, 0)
            )
        parser = configparser.ConfigParser(interpolation=None, strict=False, allow_no_value=True)
        parser.read_string(path.read_text("utf-8-sig"))
        if path.name == "tox.ini":
            return parser.has_section("pytest")
        if path.name == "setup.cfg":
            return parser.has_section("tool:pytest")
    except (OSError, UnicodeError, configparser.Error, tomllib.TOMLDecodeError):
        raise ValueError("Pytest configuration is unreadable; review and rebind before execution")
    return False


def _pytest_config_addopts(path):
    """Read effective pytest addopts as tokens, failing closed on unknown forms."""
    try:
        if path.name in {"pytest.toml", ".pytest.toml"}:
            document = tomllib.loads(path.read_text("utf-8-sig"))
            pytest_config = document.get("pytest", {})
            value = pytest_config.get("addopts") if isinstance(pytest_config, dict) else None
        elif path.name == "pyproject.toml":
            document = tomllib.loads(path.read_text("utf-8-sig"))
            tool = document.get("tool", {})
            pytest_config = tool.get("pytest", {}) if isinstance(tool, dict) else {}
            if not isinstance(pytest_config, dict):
                raise ValueError("Pytest TOML configuration is malformed")
            ini_options = pytest_config.get("ini_options", {})
            if not isinstance(ini_options, dict):
                raise ValueError("Pytest TOML configuration is malformed")
            native_addopts = pytest_config.get("addopts") if _pytest_version_tuple() >= (9, 0) else None
            ini_addopts = ini_options.get("addopts")
            if native_addopts is not None and ini_addopts is not None:
                raise ValueError("Pytest addopts are ambiguous across TOML configuration tables")
            value = native_addopts if native_addopts is not None else ini_addopts
        else:
            parser = configparser.ConfigParser(interpolation=None, strict=False, allow_no_value=True)
            parser.read_string(path.read_text("utf-8-sig"))
            section = "tool:pytest" if path.name == "setup.cfg" else "pytest"
            value = parser.get(section, "addopts", fallback=None, raw=True)
    except ValueError:
        raise
    except (OSError, UnicodeError, configparser.Error, tomllib.TOMLDecodeError) as error:
        raise ValueError("Pytest addopts are unreadable; review and rebind before execution") from error

    if value is None:
        return []
    if isinstance(value, str):
        try:
            return shlex.split(value)
        except ValueError as error:
            raise ValueError("Pytest addopts tokenization failed; review and rebind before execution") from error
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        tokens = []
        for item in value:
            try:
                tokens.extend(shlex.split(item))
            except ValueError as error:
                raise ValueError("Pytest addopts tokenization failed; review and rebind before execution") from error
        return tokens
    raise ValueError("Pytest addopts must use a supported string or TOML string array")


def _review_pytest_addopts(path):
    """Reject unreviewed explicit plugin controls while retaining the root cache disable."""
    tokens = _pytest_config_addopts(path)
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "-p":
            if index + 1 >= len(tokens):
                raise ValueError("Pytest addopts has an incomplete explicit plugin option")
            plugin_name = tokens[index + 1]
            if plugin_name != "no:cacheprovider":
                raise ValueError("Pytest addopts explicit plugin control requires exact Owner review")
            index += 2
            continue
        if token.startswith("-p"):
            raise ValueError("Pytest addopts explicit plugin control requires exact Owner review")
        index += 1
    return tokens


def _pytest_source_review(source_path, root, owner, source_bytes):
    relative = source_path.relative_to(root).as_posix()
    entry = PYTEST_SOURCE_REVIEW_RECEIPTS.get(relative)
    owner_reviews = entry.get("owners") if isinstance(entry, dict) else None
    review = owner_reviews.get(owner) if isinstance(owner_reviews, dict) else None
    if not isinstance(review, dict):
        return None
    digest = hashlib.sha256(source_bytes).hexdigest()
    if digest != entry.get("sha256"):
        return None
    return {
        "path": relative,
        "sha256": digest,
        "owner": owner,
        "purpose": review["purpose"],
        "allowed_imports": list(review.get("allowed_imports", [])),
        "allowed_plugins": list(review.get("allowed_plugins", [])),
    }


def _pytest_target(path, node_parts, scope_paths, owner=None):
    """Require one literal AST test and pin pytest setup/config lookup inputs."""
    if not re.fullmatch(r"test_[A-Za-z0-9_]+\.py|[A-Za-z0-9_]+_test\.py", path.name):
        raise ValueError("Pytest target must be one conventionally named test file")
    if len(node_parts) not in {1, 2} or any(
        not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value) for value in node_parts
    ) or not node_parts[-1].startswith("test_"):
        raise ValueError("Pytest must name one exact function or class method without parameters")

    root = ROOT.resolve()
    path = path.resolve()
    if not path.is_relative_to(root):
        raise ValueError("Pytest target must remain inside the repository")
    scope = set(scope_paths)
    files = [path]
    conftest_paths = []
    active_conftest_paths = []
    config_paths = []
    selected_config = None
    current = path.parent
    while current.is_relative_to(root):
        conftest = current / "conftest.py"
        conftest_relative = conftest.relative_to(root).as_posix()
        if conftest.is_symlink():
            raise ValueError("Pytest conftest symlinks are not allowed")
        conftest_paths.append(conftest_relative)
        if conftest.is_file():
            if conftest_relative not in scope:
                raise ValueError("Every active pytest conftest must be in the bound Owner scope")
            files.append(conftest)
            active_conftest_paths.append(conftest_relative)
        for name in PYTEST_CONFIG_NAMES:
            candidate = current / name
            if candidate.is_symlink():
                raise ValueError("Pytest configuration symlinks are not allowed")
            relative = candidate.relative_to(root).as_posix()
            config_paths.append(relative)
            if candidate.is_file() and selected_config is None and _pytest_config_matches(candidate):
                selected_config = candidate
        if current == root:
            break
        current = current.parent

    if selected_config is None:
        raise ValueError("No effective repository-local pytest configuration is available")
    selected_config_relative = selected_config.relative_to(root).as_posix()
    if not selected_config.resolve().is_relative_to(root):
        raise ValueError("Pytest configuration must resolve inside the repository")
    if selected_config_relative not in scope:
        raise ValueError("The effective pytest configuration must be in the bound Owner scope")
    config_addopts = _review_pytest_addopts(selected_config)

    forbidden_imports = (
        "requests", "httpx", "aiohttp", "urllib.request", "socket", "websocket", "websockets",
        "playwright", "selenium", "subprocess", "multiprocessing", "torch", "tensorflow", "jax",
        "transformers", "accelerate", "datasets",
    )
    effectful_methods = {"fit", "train", "finetune", "backward", "cuda", "urlopen", "create_connection"}
    target_count = 0
    source_reviews = {}
    plugin_edges = []
    processed_sources = set()
    source_index = 0
    while source_index < len(files):
        source_path = files[source_index]
        source_index += 1
        if source_path in processed_sources:
            continue
        processed_sources.add(source_path)
        raw_source = source_path.read_bytes()
        source_text = raw_source.decode("utf-8-sig")
        tree = ast.parse(source_text, filename=str(source_path))
        relative = source_path.relative_to(root).as_posix()
        source_review = _pytest_source_review(source_path, root, owner, raw_source)
        if source_review and (source_review["allowed_imports"] or source_review["allowed_plugins"]):
            if relative in {"tests/test_business_approved_source_continuity.py",
                            "tests/test_business_result_continuity.py"}:
                source_reviews[relative] = source_review

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
                if node.module == "urllib" and any(alias.name == "request" for alias in node.names):
                    modules.append("urllib.request")
            else:
                modules = []
            denied_modules = [module for module in modules if any(
                module == blocked or module.startswith(blocked + ".") for blocked in forbidden_imports
            )]
            if denied_modules:
                if (source_review and all(
                    module in source_review["allowed_imports"] for module in denied_modules
                )):
                    source_reviews[relative] = source_review
                else:
                    raise ValueError("Pytest source imports a network, process, or model-training capability; owner review required")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr.casefold() in effectful_methods:
                raise ValueError("Pytest source calls a network or model-training operation; owner review required")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"__import__", "import_module"}:
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    module = node.args[0].value
                    if any(module == blocked or module.startswith(blocked + ".")
                           for blocked in forbidden_imports):
                        raise ValueError("Pytest source dynamically imports a network, process, or model-training capability")
        plugin_assignments = []
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
                targets = [node.target]
            if any(isinstance(target, ast.Name) and target.id == "pytest_plugins" for target in targets):
                plugin_assignments.append(node)
        if plugin_assignments:
            assignment = plugin_assignments[0]
            if (len(plugin_assignments) != 1 or assignment not in tree.body
                    or not isinstance(assignment, ast.Assign) or len(assignment.targets) != 1
                    or not isinstance(assignment.targets[0], ast.Name)
                    or assignment.targets[0].id != "pytest_plugins" or not source_review):
                raise ValueError("Pytest plugin loading requires an exact owner-reviewed fixture dependency")
            try:
                plugin_names = ast.literal_eval(assignment.value)
            except (ValueError, TypeError):
                raise ValueError("Pytest plugin list must be a literal reviewed dependency list") from None
            allowed_plugins = source_review["allowed_plugins"]
            if (not isinstance(plugin_names, (tuple, list))
                    or any(not isinstance(name, str) for name in plugin_names)
                    or list(plugin_names) != allowed_plugins):
                raise ValueError("Pytest plugin list differs from its exact owner-reviewed dependencies")
            source_reviews[relative] = source_review
            for module_name in plugin_names:
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*", module_name):
                    raise ValueError("Pytest plugin module name is not a bounded repository module")
                dependency = root.joinpath(*module_name.split(".")).with_suffix(".py")
                if dependency.is_symlink() or not dependency.is_file() or not dependency.resolve().is_relative_to(root):
                    raise ValueError("Reviewed pytest plugin dependency is missing or escapes the repository")
                dependency_relative = dependency.relative_to(root).as_posix()
                if dependency_relative not in scope:
                    raise ValueError("Every reviewed pytest plugin dependency must be in the bound Owner scope")
                dependency_bytes = dependency.read_bytes()
                dependency_review = _pytest_source_review(dependency, root, owner, dependency_bytes)
                if not dependency_review:
                    raise ValueError("Pytest plugin dependency hash or Owner review is missing; review and rebind")
                plugin_edges.append({
                    "declared_by": relative,
                    "module": module_name,
                    "path": dependency_relative,
                    "sha256": dependency_review["sha256"],
                    "owner": owner,
                    "purpose": dependency_review["purpose"],
                })
                if dependency not in files:
                    files.append(dependency)
        if source_path == path:
            if len(node_parts) == 1:
                matches = [node for node in tree.body
                           if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                           and node.name == node_parts[0]]
            else:
                classes = [node for node in tree.body
                           if isinstance(node, ast.ClassDef) and node.name == node_parts[0]]
                matches = [method for cls in classes for method in cls.body
                           if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
                           and method.name == node_parts[1]]
            if len(matches) != 1:
                raise ValueError("Pytest nodeid must resolve to exactly one existing test definition")
            target_count += 1
    if target_count != 1:
        raise ValueError("Pytest node target is ambiguous")
    pinned_paths = list(dict.fromkeys([
        *(file.relative_to(root).as_posix() for file in files),
        *conftest_paths,
        *config_paths,
    ]))
    config_pins = HOOKS.continuity_pins(root, config_paths)
    conftest_pins = HOOKS.continuity_pins(root, conftest_paths)
    pytest_review_receipt = {
        "schema_version": 1,
        "owner": owner,
        "selected_config": {
            "path": selected_config_relative,
            "sha256": config_pins[selected_config_relative],
        },
        "effective_addopts": config_addopts,
        "repository_root": str(root),
        "config_candidate_pins": config_pins,
        "conftest_candidate_pins": conftest_pins,
        "reviewed_sources": [source_reviews[key] for key in sorted(source_reviews)],
        "fixture_dependency_edges": plugin_edges,
    }
    owner_approved_paths = sorted({
        selected_config_relative,
        *active_conftest_paths,
        *source_reviews.keys(),
    })
    return {
        "additional_paths": pinned_paths,
        "pytest_conftest_paths": conftest_paths,
        "pytest_config_paths": config_paths,
        "pytest_active_conftest_paths": active_conftest_paths,
        "pytest_selected_config": selected_config_relative,
        "pytest_owner_approved_paths": owner_approved_paths,
        "pytest_review_receipt": pytest_review_receipt,
    }


def _allowlisted_verification(kind, argv, scope_paths, owner=None):
    if not isinstance(argv, list) or not 1 <= len(argv) <= 40 or any(
        not isinstance(value, str) or not value or len(value) > 600 or "\x00" in value for value in argv
    ) or sum(len(value) for value in argv) > 6000:
        raise ValueError("Provide a bounded argv list; shell command strings are not accepted")

    spec = {"argv": None, "cwd": ROOT, "additional_paths": [], "package_root": None,
            "pytest_conftest_paths": [], "pytest_config_paths": [],
            "pytest_active_conftest_paths": [], "pytest_selected_config": None,
            "pytest_owner_approved_paths": [], "pytest_review_receipt": None}

    if kind == "compile":
        if _python_command(argv[0]):
            if argv[1:5] == ["-X", "utf8", "-m", "py_compile"]:
                paths = _verification_source_args(argv[5:], scope_paths, {".py"})
                spec["argv"] = [sys.executable, "-X", "utf8", "-m", "py_compile", *paths]
                return spec
            if argv[1:5] == ["-X", "utf8", "-m", "compileall"]:
                if len(argv) < 7 or argv[5] != "-q":
                    raise ValueError("compileall requires -q and explicit source paths")
                paths = _verification_source_args(argv[6:], scope_paths, {".py"})
                spec["argv"] = [sys.executable, "-X", "utf8", "-m", "compileall", "-q", *paths]
                return spec
        if (_tool_command(argv[0], "flutter")
                and argv[1:6] == ["build", "web", "--release", "--no-web-resources-cdn", "--no-pub"] and len(argv) == 6):
            package_root = _flutter_package_root(scope_paths)
            spec.update({
                "argv": _resolve_tool_argv("flutter", ["build", "web", "--release", "--no-web-resources-cdn", "--no-pub"]),
                "cwd": package_root,
                "package_root": package_root.relative_to(ROOT.resolve()).as_posix(),
            })
            return spec
        raise ValueError("Compile command is outside the allowlist")

    if kind == "static":
        if _tool_command(argv[0], "ruff") and argv[1:5] == ["check", "--select", "F", "--no-cache"]:
            paths = _verification_source_args(argv[5:], scope_paths, {".py"})
            ruff = shutil.which("ruff.cmd") or shutil.which("ruff.exe") or shutil.which("ruff") or argv[0]
            spec["argv"] = [ruff, "check", "--select", "F", "--no-cache", *paths]
            return spec
        if (_python_command(argv[0]) and argv[1:8] == ["-X", "utf8", "-m", "ruff", "check", "--select", "F"]
                and len(argv) >= 10 and argv[8] == "--no-cache"):
            paths = _verification_source_args(argv[9:], scope_paths, {".py"})
            spec["argv"] = [sys.executable, "-X", "utf8", "-m", "ruff", "check", "--select", "F", "--no-cache", *paths]
            return spec

        if _tool_command(argv[0], "dart") and len(argv) >= 3 and argv[1] == "analyze":
            paths = _verification_source_args(argv[2:], scope_paths, {".dart"})
            package_root = _flutter_package_root(scope_paths)
            spec.update({
                "argv": _resolve_tool_argv("dart", ["analyze", *[_package_relative(path, package_root) for path in paths]]),
                "cwd": package_root,
                "package_root": package_root.relative_to(ROOT.resolve()).as_posix(),
            })
            return spec

        if (_tool_command(argv[0], "flutter") and len(argv) >= 3 and argv[1:3] == ["analyze", "--no-pub"]):
            package_root = _flutter_package_root(scope_paths)
            paths = _verification_source_args(argv[3:], scope_paths, {".dart"}) if len(argv) > 3 else []
            targets = [_package_relative(path, package_root) for path in paths]
            spec.update({
                "argv": _resolve_tool_argv("flutter", ["analyze", "--no-pub", *targets]),
                "cwd": package_root,
                "package_root": package_root.relative_to(ROOT.resolve()).as_posix(),
            })
            return spec

        raise ValueError("Static command is outside the allowlist")

    if kind == "test":
        pytest_prefix = ["-X", "utf8", "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider"]
        if _python_command(argv[0]) and argv[1:9] == pytest_prefix and len(argv) == 10:
            selection = argv[9]
            parts = selection.split("::")
            if len(parts) not in {2, 3} or not parts[0]:
                raise ValueError("Pytest requires exactly one file and one literal test function or class method")
            if (ROOT / parts[0]).is_symlink():
                raise ValueError("Pytest target symlinks are not allowed")
            test_paths = _verification_source_args([parts[0]], scope_paths, {".py"})
            test_path = HOOKS.continuity_path(ROOT, test_paths[0])
            setup_paths = _pytest_target(test_path, parts[1:], scope_paths, owner=owner)
            config_path = HOOKS.continuity_path(ROOT, setup_paths["pytest_selected_config"])
            spec["argv"] = [
                sys.executable, *pytest_prefix[:6], "--verbosity=1", *pytest_prefix[6:], "-c", str(config_path),
                "--rootdir", str(ROOT.resolve()), "::".join([test_paths[0], *parts[1:]]),
            ]
            spec.update(setup_paths)
            return spec

        expected = ["-X", "utf8", "-m", "unittest", "discover", "-s", ".codex/tests", "-p"]
        if _python_command(argv[0]) and argv[1:9] == expected and len(argv) == 13:
            filename, test_name = argv[9], argv[11]
            if (not re.fullmatch(r"test_[A-Za-z0-9_]+\.py", filename)
                    or argv[10] != "-k" or argv[12] != "-v"):
                raise ValueError("Only one exact .codex/tests unittest target is allowed")
            path = ROOT / ".codex" / "tests" / filename
            if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to((ROOT / ".codex" / "tests").resolve()):
                raise ValueError("Targeted unittest source must be an existing .codex/tests file")
            relative_path = path.relative_to(ROOT.resolve()).as_posix()
            if relative_path not in set(scope_paths):
                raise ValueError("Targeted unittest source must be in the bound Owner scope")
            _unittest_target(path, test_name)
            spec["argv"] = [sys.executable, *expected[:3], "unittest", "discover", "-s", ".codex/tests",
                            "-p", filename, "-k", test_name, "-v"]
            spec["additional_paths"] = [relative_path]
            return spec

        if (_tool_command(argv[0], "flutter") and len(argv) == 6 and argv[1:3] == ["test", "--no-pub"]
                and argv[4] == "--name"):
            package_root = _flutter_package_root(scope_paths)
            test_path = HOOKS.continuity_path(ROOT, argv[3])
            if (test_path.suffix.lower() != ".dart" or not test_path.is_file() or test_path.is_symlink()
                    or not test_path.is_relative_to(package_root)
                    or not test_path.relative_to(package_root).as_posix().startswith("test/")
                    or not re.fullmatch(r"[A-Za-z0-9_.-]+_test\.dart", test_path.name)):
                raise ValueError("Flutter regression must target one existing app/test/*_test.dart file")
            relative_test = test_path.relative_to(ROOT.resolve()).as_posix()
            if relative_test not in set(scope_paths):
                raise ValueError("Flutter regression source must be in the bound Owner scope")
            test_name = argv[5]
            if not test_name.strip() or len(test_name) > 200:
                raise ValueError("Flutter regression must name one bounded test")
            relative_test = test_path.relative_to(package_root).as_posix()
            spec.update({
                "argv": _resolve_tool_argv("flutter", ["test", "--no-pub", f"--name=^{re.escape(test_name)}$", relative_test]),
                "cwd": package_root,
                "package_root": package_root.relative_to(ROOT.resolve()).as_posix(),
                "additional_paths": [test_path.relative_to(ROOT.resolve()).as_posix()],
            })
            return spec

    raise ValueError("Verification command is outside the compile/static/policy-controlled test allowlist")


def _package_dirty_files(snapshot, package_root):
    if not package_root:
        return {}
    prefix = package_root.rstrip("/") + "/"
    return {path: value for path, value in snapshot.get("files", {}).items()
            if path == package_root or path.startswith(prefix)}


def _verification_policy_and_pin():
    path = ROOT / VERIFICATION_POLICY_RELATIVE
    try:
        raw = path.read_bytes()
        contract = json.loads(raw.decode("utf-8-sig"))
        policy = contract.get("verification_policy")
        return (policy if isinstance(policy, dict) else None), hashlib.sha256(raw).hexdigest()
    except (OSError, json.JSONDecodeError, AttributeError, UnicodeDecodeError):
        return None, "ABSENT"


def _verification_continuity_binding(state, event, scope_paths, additional_immutable_paths=None):
    """Check admitted task/evidence pins while allowing edits inside its declared source scope."""
    bound = state.get("continuity")
    identity = HOOKS.continuity_identity(event, ROOT)
    if not isinstance(bound, dict) or bound.get("identity") != identity:
        raise ValueError("Verification requires this session's bound Owner continuity scope")
    if not isinstance(bound.get("pins"), dict):
        raise ValueError("Owner continuity pins are unavailable; reread and rebind before verification")

    item = HOOKS.continuity_record(ROOT, bound.get("record"), bound.get("section"))
    normalized_scope = [HOOKS.continuity_path(ROOT, value).relative_to(ROOT.resolve()).as_posix()
                        for value in item["source_paths"]]
    bound_scope = [HOOKS.continuity_path(ROOT, value).relative_to(ROOT.resolve()).as_posix()
                   for value in bound.get("source_paths", [])]
    if not normalized_scope or normalized_scope != bound_scope or normalized_scope != scope_paths:
        raise ValueError("Owner source scope changed; reread and rebind before verification")

    additional_immutable = sorted({
        HOOKS.continuity_path(ROOT, value).relative_to(ROOT.resolve()).as_posix()
        for value in (additional_immutable_paths or [])
    })
    immutable_paths = {
        HOOKS.continuity_path(ROOT, value).relative_to(ROOT.resolve()).as_posix()
        for value in [*HOOKS.CONTINUITY_RULES, bound.get("record"), *item["evidence_paths"], *additional_immutable]
        if value
    }
    missing_additional_pins = set(additional_immutable) - set(bound["pins"])
    if missing_additional_pins:
        raise ValueError("Pytest setup/source inputs are not pinned by the Owner checkpoint; review and rebind first")

    readback = HOOKS.continuity_read(ROOT, state, event)
    reasons = list(readback.get("reasons", []))
    changed_paths = set(readback.get("changed_paths", []))
    source_set = set(normalized_scope)
    mutable_source_set = source_set - immutable_paths
    source_only_pin_change = bool(changed_paths) and changed_paths.issubset(mutable_source_set)
    disallowed = []
    for reason in reasons:
        if reason == "PENDING_EFFECTS_REQUIRE_RECEIPT_READBACK":
            # This runner has no product-effect operation. Preserve the pending
            # receipt context below and never replay it here.
            continue
        if reason == "PINNED_INPUT_CHANGED" and source_only_pin_change:
            # Source contents are expected to change during implementation;
            # task, authority, and evidence pins remain immutable for admission.
            continue
        disallowed.append(reason)
    if readback.get("status") == "READBACK_REQUIRED" or disallowed:
        if "NEW_MESSAGE_SINCE_CHECKPOINT" in disallowed:
            raise ValueError("A new prompt is not covered by this Owner checkpoint; reread and rebind before verification")
        raise ValueError(
            "Owner task, authority, evidence, HEAD, or prompt context changed; reread and rebind before verification"
        )

    current_head = HOOKS.git(ROOT, "rev-parse", "HEAD").strip()
    if bound.get("head") != current_head:
        raise ValueError("Owner checkpoint HEAD changed; reread and rebind before verification")
    if bound.get("prompt_hash") != state.get("last_prompt_hash"):
        raise ValueError("A new prompt is not covered by this Owner checkpoint; reread and rebind before verification")
    if bound.get("missing_authorities"):
        raise ValueError("Owner checkpoint authority pins are incomplete; reread and rebind before verification")

    saved_pins = bound["pins"]
    context_paths = sorted(set(saved_pins) - mutable_source_set)
    current_context_pins = HOOKS.continuity_pins(ROOT, context_paths)
    if current_context_pins != {path: saved_pins[path] for path in context_paths}:
        raise ValueError("Owner record or evidence pins changed; reread and rebind before verification")

    return {
        "fingerprint": HOOKS.continuity_context_fingerprint(
            ROOT, state, current_head, additional_immutable
        ),
        "record": bound.get("record"), "section": bound.get("section"),
        "owner": item["owner"], "head": current_head,
        "prompt_hash": bound.get("prompt_hash"),
        "current_prompt_hash": state.get("last_prompt_hash"),
        "pending_effects": list(item["pending_effects"]),
        "pending_effects_retained_only": True,
        "pending_effects_replayed": False,
        "additional_immutable_paths": additional_immutable,
    }


def _test_execution_counts(kind, command_argv, diagnostic):
    if kind != "test":
        return None, None
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", diagnostic.decode("utf-8", errors="replace"))
    if command_argv and command_argv[0] == sys.executable and command_argv[3:5] == ["-m", "pytest"]:
        outcomes = re.findall(r"\b(\d+)\s+(passed|failed|errors?|skipped|deselected|xfailed|xpassed)\b", text, re.I)
        if not outcomes:
            return None, None
        counts = {name.casefold(): int(count) for count, name in outcomes}
        test_count = sum(counts.values())
        return test_count, counts.get("passed", 0)
    flutter_snapshot = (
        len(command_argv) >= 4
        and command_argv[1] == "--disable-dart-dev"
        and Path(command_argv[2]).name.casefold() == "flutter_tools.snapshot"
    ) if command_argv else False
    if command_argv and (Path(command_argv[0]).name.casefold() == "flutter.exe" or flutter_snapshot):
        progress = re.findall(r"\+(\d+)(?:\s+-\d+)?(?:\s+~(\d+))?\s*:", text)
        if not progress:
            return None, None
        passed, skipped = progress[-1]
        return int(passed) + int(skipped or 0), int(passed)
    summaries = re.findall(r"Ran\s+(\d+)\s+tests?\b", text)
    if not summaries:
        return None, None
    ran = int(summaries[-1])
    skipped_values = re.findall(r"skipped=(\d+)", text)
    skipped = int(skipped_values[-1]) if skipped_values else 0
    return ran, max(0, ran - skipped)


def _verification_process_environment(kind, command_argv, cache_dir):
    run_env = os.environ.copy()
    run_env["PYTHONPYCACHEPREFIX"] = str(cache_dir)
    if kind == "test":
        run_env["ZBC_ALLOW_NETWORK"] = "0"
    if command_argv and command_argv[0] == sys.executable and command_argv[3:5] == ["-m", "pytest"]:
        run_env.pop("PYTEST_ADDOPTS", None)
        run_env.pop("PYTEST_PLUGINS", None)
        run_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    return run_env


def _execute_verification_process(kind, command_argv, cwd, timeout_seconds):
    with tempfile.TemporaryDirectory(prefix="lumenis-verification-cache-") as cache_dir:
        run_env = _verification_process_environment(kind, command_argv, cache_dir)
        process = subprocess.Popen(
            command_argv, cwd=cwd, env=run_env,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            shell=False,
        )
        diagnostic = bytearray()
        output_lock = threading.Lock()

        def collect_output():
            if process.stdout is None:
                return
            with process.stdout:
                while True:
                    chunk = process.stdout.read(8192)
                    if not chunk:
                        return
                    with output_lock:
                        diagnostic.extend(chunk)
                        if len(diagnostic) > MAX_VERIFICATION_DIAGNOSTIC_BYTES:
                            del diagnostic[:-MAX_VERIFICATION_DIAGNOSTIC_BYTES]

        reader = threading.Thread(target=collect_output, name="lumenis-verification-output", daemon=True)
        reader.start()
        timed_out = False
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            process.wait()
        reader.join(timeout=3)
        output_capture_complete = not reader.is_alive()
        with output_lock:
            output = bytes(diagnostic)
        if output:
            try:
                sys.stderr.buffer.write(output)
                if not output.endswith(b"\n"):
                    sys.stderr.buffer.write(b"\n")
                sys.stderr.buffer.flush()
            except (AttributeError, OSError):
                sys.stderr.write(output.decode("utf-8", errors="replace"))
                sys.stderr.flush()
        test_count, tests_passed = _test_execution_counts(kind, command_argv, output)
        return {
            "returncode": process.returncode,
            "timed_out": timed_out,
            "process_tree_exit_verified": False if timed_out else None,
            "timeout_recovery_state": (
                "DIRECT_TOOL_PROCESS_TERMINATED_DESCENDANTS_UNVERIFIED" if timed_out else None
            ),
            "output_capture_complete": output_capture_complete,
            "test_count": test_count,
            "tests_passed": tests_passed,
            "diagnostic_bytes": len(output),
        }


def run_selected_verification(params):
    if not isinstance(params, dict) or set(params) != {"kind", "argv", "timeout_seconds"}:
        raise ValueError("verification_run requires exactly kind, argv, and timeout_seconds")
    kind = params["kind"]
    timeout_seconds = params["timeout_seconds"]
    if not isinstance(kind, str) or kind not in {"compile", "static", "test"}:
        raise ValueError("Verification kind must be compile, static, or test")
    if (not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool)
            or not 1 <= timeout_seconds <= MAX_VERIFICATION_TIMEOUT_SECONDS):
        raise ValueError(f"timeout_seconds must be an integer from 1 to {MAX_VERIFICATION_TIMEOUT_SECONDS}")

    event = _continuity_identity()
    identity = HOOKS.continuity_identity(event, ROOT)
    state_path = HOOKS.state_file(event, ROOT)
    with HOOKS.locked(state_path):
        if state_path.is_file():
            state = json.loads(state_path.read_text("utf-8"))
            if not isinstance(state, dict):
                raise ValueError("Engineering verification state is invalid")
        else:
            raise ValueError("Save the current Owner continuity binding before running verification")
        bound = state.get("continuity")
        if not isinstance(bound, dict) or bound.get("identity") != identity:
            raise ValueError("Verification requires this session's bound Owner continuity scope")
        source_paths = bound.get("source_paths")
        if not isinstance(source_paths, list) or not source_paths or len(source_paths) > 30:
            raise ValueError("Verification requires explicit bound Owner source paths")
        normalized_scope = [HOOKS.continuity_path(ROOT, value).relative_to(ROOT.resolve()).as_posix()
                            for value in source_paths]
        owner_item = HOOKS.continuity_record(ROOT, bound.get("record"), bound.get("section"))
        command_spec = _allowlisted_verification(
            kind, params["argv"], normalized_scope, owner=owner_item["owner"]
        )
        command_argv = command_spec["argv"]
        additional_immutable_paths = command_spec["pytest_owner_approved_paths"]
        continuity_start = _verification_continuity_binding(
            state, event, normalized_scope, additional_immutable_paths
        )
        for path in source_paths:
            source = HOOKS.continuity_path(ROOT, path)
            if not source.is_file():
                raise ValueError("Every bound verification source must currently exist")
        verification_paths = sorted(set([*normalized_scope, *command_spec["additional_paths"]]))

        policy, policy_read_pin = _verification_policy_and_pin()
        if kind == "test":
            policy_allowed = isinstance(policy, dict) and policy.get("run_unit_integration_allowed") is True
        else:
            check_name = "compilation" if kind == "compile" else "static_quality"
            retained = policy.get("retained_checks") if isinstance(policy, dict) else None
            policy_allowed = isinstance(retained, list) and check_name in retained

        start_snapshot = HOOKS.snapshot(ROOT)
        source_pins_start = HOOKS.continuity_pins(ROOT, verification_paths)
        pytest_review_receipt = command_spec["pytest_review_receipt"]
        if isinstance(pytest_review_receipt, dict):
            admission_pins = {
                **pytest_review_receipt["config_candidate_pins"],
                **pytest_review_receipt["conftest_candidate_pins"],
            }
            if any(source_pins_start.get(path) != digest for path, digest in admission_pins.items()):
                raise ValueError("Pytest config/conftest changed after source review; rebind and retry")
            for reviewed in pytest_review_receipt["reviewed_sources"]:
                if source_pins_start.get(reviewed["path"]) != reviewed["sha256"]:
                    raise ValueError("Reviewed pytest source changed after admission; rebind and retry")
        policy_path = VERIFICATION_POLICY_RELATIVE.as_posix()
        policy_pins_start = HOOKS.continuity_pins(ROOT, [policy_path])
        policy_read_stable = policy_pins_start.get(policy_path) == policy_read_pin
        package_root = command_spec["package_root"]
        package_dirty_start = _package_dirty_files(start_snapshot, package_root)
        started_at = time.time()
        receipt_id = hashlib.sha256(
            f"{identity['session_id']}|{started_at:.9f}|{kind}|{json.dumps(command_argv)}".encode("utf-8")
        ).hexdigest()[:20]
        receipts = state.setdefault("receipts", [])
        if not isinstance(receipts, list):
            raise ValueError("Engineering verification receipt state is invalid")
        receipt = {
            "receipt_id": receipt_id, "runner": "engineering_cli", "kind": kind,
            "status": "RUNNING", "executed": False, "exit_code": None,
            "process_exit_code": None, "fingerprint": HOOKS.verification_fingerprint(ROOT, state, start_snapshot),
            "requested_argv": params["argv"], "command_argv": command_argv,
            "pytest_conftest_paths": command_spec["pytest_conftest_paths"],
            "pytest_config_paths": command_spec["pytest_config_paths"],
            "pytest_active_conftest_paths": command_spec["pytest_active_conftest_paths"],
            "pytest_selected_config": command_spec["pytest_selected_config"],
            "pytest_owner_approved_paths": additional_immutable_paths,
            "pytest_review_receipt": pytest_review_receipt,
            "source_paths": normalized_scope,
            "verification_paths": verification_paths, "package_root": package_root,
            "package_dirty_start": package_dirty_start, "package_dirty_end": None,
            "source_pins_start": source_pins_start, "source_pins_end": None,
            "policy_pins_start": policy_pins_start, "policy_pins_end": None,
            "head_start": start_snapshot["head"], "head_end": None,
            "continuity_binding_start": continuity_start,
            "continuity_binding_end": None,
            "continuity_binding_fingerprint_start": continuity_start["fingerprint"],
            "continuity_binding_fingerprint_end": None,
            "continuity_binding_stable": None,
            "source_stable": None, "policy_stable": None,
            "started_at": started_at, "finished_at": None,
            "timeout_seconds": timeout_seconds, "timed_out": False,
        }
        receipts.append(receipt)
        state["receipts"] = receipts[-20:]
        receipt = next(value for value in state["receipts"] if value.get("receipt_id") == receipt_id)
        HOOKS.save(state_path, state)

        process_exit_code = None
        error_type = None
        timed_out = False
        process_tree_exit_verified = None
        timeout_recovery_state = None
        output_capture_complete = None
        test_count = None
        tests_passed = None
        diagnostic_bytes = 0
        continuity_end = None
        continuity_stable = False
        if policy_allowed and policy_read_stable:
            receipt["executed"] = True
            HOOKS.save(state_path, state)
            try:
                completed = _execute_verification_process(kind, command_argv, command_spec["cwd"], timeout_seconds)
                process_exit_code = completed["returncode"]
                timed_out = completed["timed_out"]
                process_tree_exit_verified = completed["process_tree_exit_verified"]
                timeout_recovery_state = completed["timeout_recovery_state"]
                output_capture_complete = completed["output_capture_complete"]
                test_count = completed["test_count"]
                tests_passed = completed["tests_passed"]
                diagnostic_bytes = completed["diagnostic_bytes"]
            except OSError as error:
                error_type = type(error).__name__

        try:
            end_snapshot = HOOKS.snapshot(ROOT)
            source_pins_end = HOOKS.continuity_pins(ROOT, verification_paths)
            policy_pins_end = HOOKS.continuity_pins(ROOT, [policy_path])
            package_dirty_end = _package_dirty_files(end_snapshot, package_root)
            head_end = end_snapshot["head"]
            source_stable = (head_end == start_snapshot["head"] and source_pins_end == source_pins_start
                             and package_dirty_end == package_dirty_start)
            policy_stable = (policy_read_stable and policy_pins_end == policy_pins_start
                             and policy_pins_end.get(policy_path) == policy_read_pin)
            try:
                continuity_end = _verification_continuity_binding(
                    state, event, normalized_scope, additional_immutable_paths
                )
                continuity_stable = continuity_end["fingerprint"] == continuity_start["fingerprint"]
            except (OSError, ValueError, KeyError, TypeError, RuntimeError):
                continuity_end = {
                    "fingerprint": HOOKS.continuity_context_fingerprint(
                        ROOT, state, head_end, additional_immutable_paths
                    ),
                    "pending_effects_retained_only": True,
                    "pending_effects_replayed": False,
                }
                continuity_stable = False
            receipt["fingerprint"] = HOOKS.verification_fingerprint(ROOT, state, end_snapshot)
        except Exception as error:
            end_snapshot = None
            source_pins_end = None
            policy_pins_end = None
            package_dirty_end = None
            head_end = None
            source_stable = False
            policy_stable = False
            continuity_stable = False
            error_type = type(error).__name__

        if not policy_allowed:
            status = "PROHIBITED_BY_POLICY" if policy is not None else "VERIFICATION_POLICY_UNAVAILABLE"
        elif not policy_read_stable:
            status = "POLICY_CHANGED_BEFORE_RUN"
        elif error_type is not None:
            status = "READBACK_FAILED" if end_snapshot is None else "EXECUTION_ERROR"
        elif timed_out:
            status = "TIMED_OUT_PROCESS_TREE_UNVERIFIED"
        elif process_exit_code != 0:
            status = "FAILED"
        elif output_capture_complete is False:
            status = "OUTPUT_CAPTURE_INCOMPLETE"
        elif not source_stable:
            status = "SOURCE_CHANGED_DURING_RUN"
        elif not continuity_stable:
            status = "CONTINUITY_CHANGED_DURING_RUN"
        elif not policy_stable:
            status = "POLICY_CHANGED_DURING_RUN"
        elif kind == "test" and test_count is None:
            status = "TEST_COUNT_UNAVAILABLE"
        elif kind == "test" and (test_count != 1 or tests_passed != 1):
            status = "TEST_COUNT_MISMATCH"
        else:
            status = "SUCCEEDED"

        receipt.update({
            "source_pins_end": source_pins_end, "policy_pins_end": policy_pins_end,
            "package_dirty_end": package_dirty_end, "head_end": head_end,
            "source_stable": source_stable, "policy_stable": policy_stable,
            "continuity_binding_end": continuity_end,
            "continuity_binding_fingerprint_end": (
                continuity_end.get("fingerprint") if isinstance(continuity_end, dict) else None
            ),
            "continuity_binding_stable": continuity_stable,
        })

        finished_at = time.time()
        gate_exit_code = process_exit_code
        if process_exit_code == 0 and status != "SUCCEEDED":
            gate_exit_code = None
        receipt.update({
            "status": status, "process_exit_code": process_exit_code,
            "exit_code": gate_exit_code, "timed_out": timed_out,
            "process_tree_exit_verified": process_tree_exit_verified,
            "timeout_recovery_state": timeout_recovery_state,
            "output_capture_complete": output_capture_complete,
            "error_type": error_type, "finished_at": finished_at,
            "test_count": test_count, "tests_passed": tests_passed,
            "diagnostic_bytes": diagnostic_bytes,
        })
        HOOKS.save(state_path, state)
        return {
            "receipt_id": receipt_id, "kind": kind, "status": status,
            "executed": receipt["executed"], "exit_code": gate_exit_code,
            "process_exit_code": process_exit_code, "timed_out": timed_out,
            "process_tree_exit_verified": process_tree_exit_verified,
            "timeout_recovery_state": timeout_recovery_state,
            "output_capture_complete": output_capture_complete,
            "test_count": test_count, "tests_passed": tests_passed,
            "head_start": receipt["head_start"], "head_end": receipt["head_end"],
            "source_pins_start": source_pins_start, "source_pins_end": receipt["source_pins_end"],
            "source_stable": receipt["source_stable"], "policy_stable": receipt["policy_stable"],
            "continuity_binding_stable": receipt["continuity_binding_stable"],
            "acceptance": "ENGINEERING_CHECK_ONLY_NOT_PRODUCT_ACCEPTANCE",
        }

def run_engineering_checks():
    policy = current_verification_policy()
    if policy is None:
        return {"status": "VERIFICATION_POLICY_UNAVAILABLE", "exit_code": None, "scope": "engineering-layer-only",
                "product_tests_run": False, "executed": False, "reason": "Machine verification_policy could not be read; no suite was invoked."}
    if policy.get("run_unit_integration_allowed") is not True:
        return {"status": "PROHIBITED_BY_POLICY", "exit_code": None, "scope": "engineering-layer-only",
                "product_tests_run": False, "executed": False,
                "policy_path": VERIFICATION_POLICY.relative_to(ROOT).as_posix(),
                "reason": "Current machine verification_policy prohibits unit/integration suite execution; no subprocess was started."}
    p = subprocess.run([sys.executable, "-X", "utf8", "-m", "unittest", "discover", "-s", str(ROOT/".codex/tests"), "-v"],
                       cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace", timeout=90)
    return {"exit_code": p.returncode, "scope": "engineering-layer-only", "product_tests_run": False, "output": (p.stdout+p.stderr)[-14000:]}

def config_inventory():
    config = tomllib.loads((Path.home()/".codex/config.toml").read_text("utf-8-sig"))
    return {"configured_mcp_names": sorted(config.get("mcp_servers", {})), "sandbox_mode": config.get("sandbox_mode"),
            "approval_policy": config.get("approval_policy"), "hooks_require_native_trust": True,
            "repo_skill_names": sorted(p.parent.name for p in (ROOT/".agents/skills").glob("*/SKILL.md")),
            "status": "CONFIGURATION_INVENTORY_NOT_LIVE_VERIFICATION"}

def shared_source_tool(action, params):
    allowed = {
        "source_read": source_read,
        "route_task": route_task,
        "static_check": static_check,
        "validation_plan": validation_plan,
    }
    if action not in allowed:
        raise ValueError("Unknown source tool")
    return allowed[action](**params)

def dispatch(action, params):
    if action in {"source_read", "route_task", "static_check", "validation_plan"}: return shared_source_tool(action, params)
    if action == "continuity": return continuity(params)
    if action == "verification_run": return run_selected_verification(params)
    if action == "capabilities": return config_inventory()
    functions = {"repo_truth": repo_truth, "runtime_health": runtime_health, "run_engineering_checks": run_engineering_checks, "config_inventory": config_inventory}
    if action in functions: return functions[action]()
    if action == "verification_plan": return verification_plan(params.get("paths", []))
    if action == "source_owner": return source_owner(params.get("query", ""))
    raise ValueError("Unknown engineering action")

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["repo_truth", "runtime_health", "run_engineering_checks", "config_inventory", "verification_plan", "source_owner", "source_read", "route_task", "static_check", "validation_plan", "continuity", "verification_run", "capabilities"])
    parser.add_argument("--params", default="{}")
    args = parser.parse_args(argv)
    try:
        result = dispatch(args.action, json.loads(args.params))
        sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False)+"\n").encode("utf-8"))
        return 1 if args.action == "verification_run" and result.get("status") != "SUCCEEDED" else 0
    except Exception as error:
        print(json.dumps({"status": "ERROR", "error_type": type(error).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
