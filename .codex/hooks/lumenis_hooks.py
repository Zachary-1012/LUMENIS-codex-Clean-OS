"""LUMENIS engineering hooks: bounded checks, not an OS security boundary."""
from __future__ import annotations
import contextlib
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

STATE_ROOT = Path.home() / ".codex" / "lumenis-engineering-state"
CODE = {".py", ".dart", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".rs"}
TEXT = CODE | {".md", ".toml", ".json", ".yaml", ".yml", ".rules", ".txt", ".ps1", ".cmd"}
SHELL = {"Bash", "exec_command", "command_execution", "shell_command"}
PATTERNS = [
    (r"\bgit(?:\.exe)?\s+(?:-C\s+(?:\"[^\"]+\"|[^\s]+)\s+)?push\b[^\r\n]*(?:--force(?:-with-lease)?|\s-f(?:\s|$))", "Force-push is forbidden for LUMENIS."),
    (r"\bgit(?:\.exe)?\s+(?:-C\s+(?:\"[^\"]+\"|[^\s]+)\s+)?reset\b[^\r\n]*--hard\b", "Hard reset may destroy protected local work."),
    (r"\bgit(?:\.exe)?\s+clean\b[^\r\n]*(?:--force|\s-[a-z]*f[a-z]*\b)", "Forced cleanup may destroy unclassified local work."),
    (r"\bgit(?:\.exe)?\s+(?:-C\s+(?:\"[^\"]+\"|[^\s]+)\s+)?(?:checkout\s+(?:HEAD\s+)?--\s+\.|restore\s+(?:--worktree\s+)?\.)\s*(?:$|[;&])", "Broad checkout/restore may overwrite protected local work."),
    (r"\bgit(?:\.exe)?\s+(?:-C\s+(?:\"[^\"]+\"|[^\s]+)\s+)?add\s+(?:\.|-A|--all)\s*(?:$|[;&])", "Bulk staging may absorb another window's protected dirty work; stage exact paths only."),
    (r"\bgit(?:\.exe)?\s+(?:-C\s+(?:\"[^\"]+\"|[^\s]+)\s+)?commit\b[^\r\n]*(?:\s-a(?:\s|$)|\s--all(?:\s|$))", "git commit -a/--all may absorb unrelated dirty work; commit exact staged paths only."),
    (r"(?:Remove-Item|del|erase|rm)\b[^\r\n]*data[\\/]+monitor\.db\b", "Deletion of the production database is forbidden."),
]

def git(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                          timeout=10, encoding="utf-8", errors="strict")
    if proc.returncode:
        raise RuntimeError("Git inspection failed; repository state is UNKNOWN")
    return proc.stdout

def find_root(cwd: str | None) -> Path | None:
    base = Path(cwd or os.getcwd()).resolve()
    for path in (base, *base.parents):
        if (path / ".git").exists():
            authority = path / "AGENTS.md"
            if authority.is_file() and "LUMENIS" in authority.read_text("utf-8-sig")[:1000]:
                return path
            return None
    return None

def eligible(relative: str) -> bool:
    path = Path(relative)
    return (path.suffix.lower() in TEXT and not path.name.startswith(".env")
            and not any(p.lower() in {"data", ".git", "node_modules", ".playwright-cli"} for p in path.parts)
            and not any(word in path.name.lower() for word in ("cookie", "credential", "secret")))

def snapshot(root: Path) -> dict:
    raw = git(root, "status", "--porcelain=v1", "-z", "-uall")
    records, files, i = raw.split("\0"), {}, 0
    while i < len(records):
        entry = records[i]; i += 1
        if not entry: continue
        status, relative = entry[:2], entry[3:]
        if "R" in status or "C" in status: i += 1
        if not eligible(relative): continue
        path = root / relative
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()): continue
        if path.is_file():
            stat = path.stat()
            value = hashlib.sha256(path.read_bytes()).hexdigest() if stat.st_size < 2000000 else f"large:{stat.st_size}:{stat.st_mtime_ns}"
        else: value = "deleted"
        files[relative] = value
    head = git(root, "rev-parse", "HEAD").strip()
    digest = hashlib.sha256(json.dumps([head, files], sort_keys=True).encode()).hexdigest()
    return {"head": head, "files": files, "fingerprint": digest}

def emit(value: dict) -> None:
    sys.stdout.buffer.write((json.dumps(value, ensure_ascii=False) + "\n").encode("utf-8"))
    sys.stdout.buffer.flush()

def context(name: str, message: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": name, "additionalContext": message}}

def command(event: dict) -> str:
    value = event.get("tool_input", {})
    if isinstance(value, dict):
        for key in ("command", "cmd", "script"):
            if key in value: return str(value[key])
        return ""
    return str(value or "")

def policy_reason(event: dict) -> str | None:
    name = str(event.get("tool_name", ""))
    execution = name in SHELL or bool(re.search(r"(?:start_process|execute_command|run_command)$", name))
    if not execution: return None
    for pattern, reason in PATTERNS:
        if re.search(pattern, command(event), re.I): return reason
    return None

def exit_status(response) -> int | None:
    if isinstance(response, dict):
        if response.get("isError") is True: return 1
        for key in ("exit_code", "exitCode", "returncode"):
            value = response.get(key)
            if isinstance(value, int) and not isinstance(value, bool): return value
        for key in ("output", "stdout", "text", "result", "content"):
            if key in response:
                value = exit_status(response[key])
                if value is not None: return value
    elif isinstance(response, list):
        values = [exit_status(item) for item in response]
        if any(v not in (None, 0) for v in values): return 1
        if 0 in values: return 0
    elif isinstance(response, str):
        match = re.search(r"(?:Process exited with code|Process completed with exit code|Exit code:)\s*(-?\d+)", response, re.I)
        if match: return int(match.group(1))
    return None

def verification_kind(text: str) -> str | None:
    start = r"(?:^|[;\n]|&&)\s*(?:&\s*)?"
    py = r"(?:python(?:3|\.exe)?|py(?:\s+-3)?)(?:\s+-X\s+utf8)?"
    if re.search(start + r"(?:pytest\b|" + py + r"\s+-m\s+(?:pytest|unittest)\b|flutter(?:\.bat)?\s+test\b)", text, re.I): return "tests"
    if re.search(start + r"(?:git\s+diff\s+--check\b|(?:flutter|dart)(?:\.bat)?\s+analyze\b|" + py + r"\s+-m\s+py_compile\b|codex\s+doctor\b)", text, re.I): return "static"
    return None

def route_prompt(prompt: str) -> list[str]:
    rules = [
        (r"flutter|dart|sdk|package|playwright|openai|依赖|框架", "lumenis-current-docs: resolve installed versions, then Context7 or official docs."),
        (r"sqlite|migration|database|数据库|持久化", "lumenis-database-safety: isolated test DB; preserve production data."),
        (r"flutter|页面|界面|导航|accessibility|\bui\b|\bux\b", "lumenis-flutter-experience: current screen contract, real bindings and appropriate native/web acceptance."),
        (r"browser|playwright|e2e|浏览器|console|network", "lumenis-browser-e2e-debug: isolated browser profile; never personal work sessions."),
        (r"permission|security|auth|cookie|权限|安全|凭证", "lumenis-security: Codex Security and current Permission/Evidence boundaries."),
        (r"research|最新|研究|开源|方案", "lumenis-research-oss: current primary sources; verify license and actual source."),
        (r"bug|error|fail|failure|blocked|blocker|regression|报错|失败|阻塞|回归", "lumenis-self-resolve: reproduce once, locate the current Owner/caller/contract, research current official/standards docs plus maintained upstream GitHub/high-quality current implementations as needed, choose the strongest feasible complete solution, repair and verify in this owning window; escalate only genuine product/permission/paid-resource/security/external blockers."),
        (r"deploy|railway|hosting|部署|域名", "Deployment tools only for the explicitly scoped service; no silent production changes."),
    ]
    return [value for pattern, value in rules if re.search(pattern, prompt, re.I)]

def state_file(event: dict, root: Path) -> Path:
    identity = str(root) + str(event.get("session_id", "missing")) + str(event.get("agent_id", ""))
    key = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    return STATE_ROOT / (key + ".json")

@contextlib.contextmanager
def locked(path: Path):
    lock = path.with_suffix(".lock"); deadline = time.monotonic() + 1.0
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd); break
        except FileExistsError:
            if time.monotonic() >= deadline: raise RuntimeError("Concurrent state write; verification unavailable")
            time.sleep(0.025)
    try: yield
    finally: lock.unlink(missing_ok=True)

def save(path: Path, state: dict) -> None:
    temp = path.with_name(path.name + f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), "utf-8")
    os.replace(temp, path)

def handle(event: dict, root: Path, state: dict) -> dict:
    name = str(event.get("hook_event_name", ""))
    state["updated_at"] = time.time()
    if name in {"SessionEnd", "Interrupt"}:
        state["last_event"] = name; return {}
    if name == "PreToolUse":
        reason = policy_reason(event)
        return {"hookSpecificOutput": {"hookEventName": name, "permissionDecision": "deny", "permissionDecisionReason": reason}} if reason else {}
    if name == "SubagentStart":
        return context(name, "Use the current local AGENTS.md concurrency and owner contract, not a historical round/window limit. Own ordinary bugs/blockers inside the assigned Owner end-to-end: reproduce once, research current official docs plus maintained upstream GitHub/high-quality current implementations when needed, choose the strongest feasible complete solution, implement, verify recovery and continue toward the full outcome. Escalate only genuine product/permission/paid-resource/security/external blockers. Return scoped diff, exit statuses and runtime evidence; never overlap unknown work.")
    if name in {"PreCompact", "PostCompact", "SubagentStop"}:
        state["last_event"] = name; return {}
    if name == "UserPromptSubmit":
        state["routes"] = route_prompt(str(event.get("prompt", "")))
        return context(name, "\n".join(state["routes"])) if state["routes"] else {}
    if name == "SessionStart":
        if "baseline" not in state or event.get("source") == "clear":
            state["baseline"] = snapshot(root); state["receipts"] = []; state["mutation_observed"] = False
        try: origin = git(root, "rev-parse", "origin/main").strip()
        except RuntimeError: origin = "UNAVAILABLE"
        current_rel = "00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md"
        current_note = ""
        if current_rel in state["baseline"].get("files", {}):
            current_note = (
                " CURRENT has local uncommitted modifications. Treat only the published HEAD copy as GitHub-main truth; "
                "the local delta is LOCAL_CANDIDATE_ONLY until its owning source/tests/evidence are validated and published. "
            )
        return context(name, f"Local HEAD={state['baseline']['head']}; cached origin/main={origin} (not a fresh network read). Before editing, git fetch origin and reconcile protected local work.{current_note}State is preserved across compact/resume. Root AGENTS.md and current source owners control execution. " + "\n".join(state.get("routes", [])))
    if name == "PostToolUse":
        now = snapshot(root)
        state.setdefault("baseline", now)
        previous = state.get("last_snapshot", state["baseline"])
        if now["fingerprint"] != previous["fingerprint"]: state["mutation_observed"] = True
        tool = str(event.get("tool_name", ""))
        if tool == "apply_patch" and exit_status(event.get("tool_response")) != 1:
            state["mutation_observed"] = True
        kind = verification_kind(command(event)) if tool in SHELL else None
        if kind:
            receipt = {"kind": kind, "exit_code": exit_status(event.get("tool_response")), "fingerprint": now["fingerprint"], "at": time.time()}
            state.setdefault("receipts", []).append(receipt)
            state["receipts"] = state["receipts"][-20:]
        state["last_snapshot"] = now
        return {}
    if name == "Stop":
        if not state.get("mutation_observed"): return {}
        now = snapshot(root); baseline = state.get("baseline", {}).get("files", {})
        changed = {p for p in set(baseline) | set(now["files"]) if baseline.get(p) != now["files"].get(p)}
        required = "tests" if any(Path(p).suffix in CODE for p in changed) else "static"
        current = [r for r in state.get("receipts", []) if r["fingerprint"] == now["fingerprint"] and (r["kind"] == required or r["kind"] == "tests")]
        good = bool(current) and current[-1]["exit_code"] == 0
        state["verification_status"] = "SCOPED_CHECK_OBSERVED" if good else "BLOCKED_MISSING_SUCCESSFUL_CHECK"
        if good: return {}
        reason = "No successful current-snapshot " + required + " result was recorded. Failed/unknown exit codes and checks before newer edits are not PASS. Run proportional verification; if genuinely blocked, report BLOCKED and the concrete reason, never claim completion. Real user E2E remains separately required by AGENTS.md."
        if event.get("stop_hook_active"):
            return {"continue": False, "stopReason": reason, "systemMessage": "LUMENIS verification is BLOCKED; stopped without an unbounded retry loop."}
        return {"decision": "block", "reason": reason}
    return {}

def main() -> int:
    try:
        raw = sys.stdin.buffer.read(1000001)
        if len(raw) > 1000000: raise ValueError("Hook input too large")
        event = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(event, dict): raise ValueError("Hook input is not an object")
        root = find_root(event.get("cwd"))
        if root is None: emit({}); return 0
        path = state_file(event, root)
        with locked(path):
            state = json.loads(path.read_text("utf-8")) if path.exists() else {}
            output = handle(event, root, state)
            save(path, state)
        emit(output); return 0
    except Exception as error:
        emit({"systemMessage": "LUMENIS hook error: " + type(error).__name__ + ". Verification is unavailable, not PASS."})
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
