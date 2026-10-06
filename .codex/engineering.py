"""Allowlisted local engineering utilities; no production writes or arbitrary shell."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys
import time
import tomllib
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OWNER = ROOT / "00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md"

TEXT_SOURCE = {".py", ".dart", ".md", ".toml", ".yaml", ".yml", ".json", ".js", ".ts", ".txt", ".ps1", ".cmd", ".rules"}
DENY_SOURCE = re.compile(r"(^|/)(\.git|\.env[^/]*|auth\.json|credentials[^/]*|[^/]*cookies?[^/]*|[^/]*profile[^/]*|[^/]*secrets?[^/]*)(/|$)", re.I)
ROUTES = [
    ("current-docs", r"api|sdk|package|dependenc|library|framework|\u6587\u6863|\u4f9d\u8d56|\u7248\u672c", "Context7 / openaiDeveloperDocs / official docs"),
    ("source-navigation", r"refactor|implement|source|code|owner|\u4ee3\u7801|\u5b9e\u73b0|\u91cd\u6784|\u5f00\u53d1", "git / rg / engineering"),
    ("database-integrity", r"database|sqlite|migration|repository|\u6570\u636e\u5e93|\u8fc1\u79fb|\u6301\u4e45\u5316", "canonical database owner; read-only inspection"),
    ("python-contracts", r"python|flask|backend|endpoint|\u540e\u7aef|\u63a5\u53e3", "Python AST; pytest in native sandbox"),
    ("flutter-runtime", r"flutter|dart|widget|app/|mobile|desktop|\u79fb\u52a8|\u684c\u9762|\u9875\u9762", "dart MCP; existing Flutter skills"),
    ("browser-debug", r"browser|web|console|network|playwright|\u6d4f\u89c8\u5668|\u7f51\u9875|\u524d\u7aef", "verified browser/chrome/playwright tooling"),
    ("security-effects", r"permission|auth|cookie|secret|security|publish|\u6743\u9650|\u8ba4\u8bc1|\u5b89\u5168|\u53d1\u5e03", "Codex Security; Permission/effect owner"),
    ("testing-evidence", r"test|accept|e2e|bug|fix|\u6d4b\u8bd5|\u9a8c\u6536|\u4fee\u590d|\u62a5\u9519", "scoped tests; runtime/E2E evidence"),
    ("release-ci", r"release|deploy|ci\b|workflow|\u4e0a\u7ebf|\u90e8\u7f72|\u6d41\u6c34\u7ebf", "GitHub; approved deployment provider"),
    ("research-adoption", r"research|compare|oss|license|\u7814\u7a76|\u6bd4\u8f83|\u5f00\u6e90|\u9009\u578b", "current primary sources; licenses"),
    ("review-delegation", r"review|audit|agent|\u5ba1\u8ba1|\u5ba1\u67e5|\u5e76\u884c", "bounded native subagents/reviewer"),
    ("recovery-continuity", r"resume|continue|compact|handoff|\u7ee7\u7eed|\u63a5\u624b|\u6062\u590d", "checkpoint; fresh local/remote state"),
]
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
        plan.append("AST then owner-matched pytest in an isolated test DB, through native sandbox.")
    if ".dart" in joined:
        plan.append("Dart MCP diagnostics, scoped unit/widget tests, actual promised target surfaces.")
    if re.search(r"database|migration|permission|evidence|runtime", joined, re.I):
        plan.append("Shared primitive: widen integration/regression and preserve protected production DB.")
    if re.search(r"app/|experience|screen", joined, re.I):
        plan.append("Current screen specification, Experience/anti-template gates, real-user E2E and failure recovery.")
    return {"paths": paths, "plan": plan or ["Resolve current Owner and proportional acceptance checks."], "execution": "Not run. Use native sandbox; retain exact command, exit status, output and source fingerprint."}

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
    inventory = git("ls-files", "--cached", "--others", "--exclude-standard", "-z").split("\0")
    candidates = sorted({p for p in inventory if (p.startswith("tests/") or p.startswith("app/test/")) and (p.endswith(".py") or p.endswith(".dart"))})
    relevant = [p for p in candidates if (p.startswith("app/test/") and any(x.endswith(".dart") for x in paths)) or (p.startswith("tests/") and any(x.endswith(".py") for x in paths))]
    stems = {Path(p).stem for p in paths}
    entrypoint = bool(stems & {"main", "app", "__init__"})
    matched = [p for p in relevant if entrypoint or any(Path(p).stem in {"test_"+s, s+"_test"} or Path(p).stem.startswith("test_"+s+"_") for s in stems)][:100]
    broad = any(any(s in p.lower() for s in ["database", "permission", "evidence", "gateway", "runtime"]) for p in paths)
    return {"input_paths": paths, "suggested_existing_tests": matched, "widen_regression": broad or entrypoint,
            "selection_is_heuristic": True, "executed": False,
            "requirements": ["Read current source owner and caller contracts.", "Use isolated DBs and current CI test tiers.", "Native Flutter tests are not replaced by browser tests.", "User-visible completion requires real runtime/E2E evidence."]}

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

def run_engineering_checks():
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
    if action == "capabilities": return config_inventory()
    functions = {"repo_truth": repo_truth, "runtime_health": runtime_health, "run_engineering_checks": run_engineering_checks, "config_inventory": config_inventory}
    if action in functions: return functions[action]()
    if action == "verification_plan": return verification_plan(params.get("paths", []))
    if action == "source_owner": return source_owner(params.get("query", ""))
    raise ValueError("Unknown engineering action")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["repo_truth", "runtime_health", "run_engineering_checks", "config_inventory", "verification_plan", "source_owner", "source_read", "route_task", "static_check", "validation_plan", "capabilities"])
    parser.add_argument("--params", default="{}")
    args = parser.parse_args()
    try:
        result = dispatch(args.action, json.loads(args.params))
        sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False)+"\n").encode("utf-8"))
    except Exception as error:
        print(json.dumps({"status": "ERROR", "error_type": type(error).__name__}))
        raise SystemExit(1)
