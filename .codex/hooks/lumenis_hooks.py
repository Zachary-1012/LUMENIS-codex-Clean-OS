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
import tomllib
from pathlib import Path

STATE_ROOT = Path.home() / ".codex" / "lumenis-engineering-state"
CODE = {".py", ".dart", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".rs", ".astro"}
TEXT = CODE | {".md", ".toml", ".json", ".yaml", ".yml", ".rules", ".txt", ".ps1", ".cmd", ".css", ".log", ".ini", ".cfg"}
SHELL = {"Bash", "exec_command", "command_execution", "shell_command"}
VERIFICATION_POLICY_PATH = Path("00-GOVERNANCE/LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json")
CONTINUITY_RULES = (
    "AGENTS.md", "README.md", str(VERIFICATION_POLICY_PATH),
    "00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md",
    "00-GOVERNANCE/AI-NATIVE-PRODUCT-CONSTITUTION.md",
    "00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md",
    "00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md",
    "00-GOVERNANCE/LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md",
    "00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md",
    "00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md",
    "00-GOVERNANCE/LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md",
    "00-GOVERNANCE/PRODUCT-POSITIONING-CURRENT.md",
    "00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md",
    "00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json",
    "00-GOVERNANCE/SECURITY-BOUNDARY-CURRENT.md",
)
CONTINUITY_FIELDS = {
    "owner", "objective", "po_source", "constraints", "completed", "remaining",
    "next_action", "pending_effects", "source_paths", "evidence_paths", "native_goal",
}


def load_verification_policy(root: Path) -> dict | None:
    try:
        contract = json.loads((root / VERIFICATION_POLICY_PATH).read_text("utf-8-sig"))
        policy = contract.get("verification_policy")
        return policy if isinstance(policy, dict) else None
    except (OSError, json.JSONDecodeError, AttributeError):
        return None


def model_policy_context(event: dict) -> str:
    current = str(event.get("model") or "SETTINGS_UNVERIFIED")
    return (
        f"Observed event model={current}; unreported effort/tier are SETTINGS_UNVERIFIED. "
        "Preserve the PO's current manual model/effort/speed; historical role defaults "
        "and summaries select nothing. Hooks never change settings or dispatch windows."
    )


def project_primary_model_override_reason(root: Path) -> str | None:
    cfg = root / ".codex" / "config.toml"
    if not cfg.is_file():
        return None
    data = tomllib.loads(cfg.read_text("utf-8-sig"))
    for key in ("model", "model_reasoning_effort", "plan_mode_reasoning_effort", "service_tier", "model_provider"):
        if key in data:
            return (
                f"Shared project config sets top-level {key}={data[key]!r}; "
                "preserve the Product Owner's manual selections; do not silently rewrite model, "
                "effort, speed, tier, or route. Record observed runtime metadata when reported."
            )
    return None

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
    raw = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=normal")
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
        for key in ("exit_code", "exitCode", "returncode"):
            value = response.get(key)
            if isinstance(value, int) and not isinstance(value, bool): return value
    # Tool output is user/process text and can contain arbitrary claims about
    # an exit status. Only a structured integer field is execution evidence.
    return None

def verification_kind(text: str) -> str | None:
    start = r"(?:^|[;\n]|&&)\s*(?:&\s*)?"
    py = r"(?:(?:[A-Za-z]:)?[^\s;&|\"']*[\\/])?(?:python(?:3|\.exe)?|py(?:\s+-3)?)(?:\s+-X\s+utf8)?"
    if re.search(start + r"(?:flutter(?:\.bat)?\s+build\b|dart\s+compile\b|" + py + r"\s+-m\s+(?:compileall|py_compile)\b)", text, re.I): return "compile"
    if re.search(start + r"git\s+diff\s+--check\b", text, re.I): return "diff"
    if re.search(start + r"(?:pytest(?:\.exe)?\b|" + py + r"\s+-m\s+(?:pytest|unittest)\b|flutter(?:\.bat)?\s+test\b)", text, re.I): return "test"
    if re.search(start + r"(?:(?:flutter|dart)(?:\.bat)?\s+analyze\b|ruff(?:\.exe|\.cmd)?\s+check\b|codex\s+doctor\b)", text, re.I): return "static"
    return None

def route_prompt(prompt: str) -> list[str]:
    rules = [
        (r"openai|codex|chatgpt|plugin|responses api|agents sdk", "lumenis-openai-current-docs: use the project-configured openaiDeveloperDocs MCP first, then current official OpenAI domains and maintained openai/codex GitHub as needed."),
        (r"flutter|dart|sdk|package|playwright|依赖|框架", "lumenis-current-docs: resolve installed versions, then Context7, authoritative vendor docs, and maintained upstream GitHub."),
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
    session = event.get("session_id")
    if not isinstance(session, str) or not session.strip() or session == "missing":
        raise ValueError("Stable session identity required; never share missing-session state")
    identity = str(root) + session + str(event.get("agent_id", ""))
    key = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    return STATE_ROOT / (key + ".json")

@contextlib.contextmanager
def locked(path: Path):
    lock = path.with_suffix(".lock")
    marker = b"LUMENIS_OS_LOCK_V1\n"
    try:
        stream = lock.open("x+b", buffering=0)
        stream.write(marker)
        stream.flush()
    except FileExistsError:
        stream = lock.open("r+b", buffering=0)
        if stream.read(len(marker)) != marker:
            stream.close()
            raise RuntimeError("Legacy lock requires process-owner readback; never remove an unknown active lock")
    # A stable inode/file handle avoids unlink races. The OS releases this lock
    # on crash/termination; no PID reuse guess or stale-lock age heuristic.
    if os.name == "nt":
        import msvcrt
        def acquire():
            stream.seek(len(marker))
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        def release():
            stream.seek(len(marker))
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        def acquire():
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        def release():
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    acquired = False
    deadline = time.monotonic() + 5.0
    try:
        while not acquired:
            try:
                acquire()
                acquired = True
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Concurrent state write; verification unavailable") from None
                time.sleep(0.025)
        yield
    finally:
        if acquired:
            release()
        stream.close()

def save(path: Path, state: dict) -> None:
    temp = path.with_name(path.name + f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), "utf-8")
    os.replace(temp, path)


def continuity_identity(event: dict, root: Path) -> dict:
    session = event.get("session_id")
    if not isinstance(session, str) or not session.strip() or session == "missing":
        raise ValueError("Stable session identity required")
    return {"root": str(root.resolve()), "session_id": session,
            "agent_id": str(event.get("agent_id") or "")}


def continuity_path(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or len(value) > 600:
        raise ValueError("Bounded relative evidence/source path required")
    rel = Path(value)
    if rel.is_absolute() or rel.drive or ".." in rel.parts:
        raise ValueError("Path escape rejected")
    if any(part.lower() in {".git", "data", "node_modules", "sessions", "profiles"}
           or part.lower().startswith(".env") for part in rel.parts):
        raise ValueError("Private/runtime data paths are not continuity inputs")
    if re.search(r"cookie|credential|secret|auth\.json", rel.name, re.I):
        raise ValueError("Sensitive continuity input rejected")
    path = (root / rel).resolve()
    if not path.is_relative_to(root.resolve()) or path.suffix.lower() not in TEXT:
        raise ValueError("Only repository text references are supported")
    if path.is_file() and path.stat().st_size > 2_000_000:
        raise ValueError("Reference exceeds bounded read limit")
    return path


def continuity_record(root: Path, record: str, section: str) -> dict:
    path = continuity_path(root, record)
    if path.suffix != ".json" or Path(record).parts[0] != "work":
        raise ValueError("Use a section in the existing local work JSON record")
    if not isinstance(section, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", section):
        raise ValueError("Exact top-level section required")
    item = json.loads(path.read_text("utf-8-sig"))[section]
    if not isinstance(item, dict) or set(item) != CONTINUITY_FIELDS:
        raise ValueError("Incomplete or unexpected continuity fields")
    if item["owner"] not in {"M", "F", "C1", "C2", "C3", "C4", "C5", "C6"}:
        raise ValueError("Unknown existing owner")
    for key in ("objective", "po_source", "next_action", "native_goal"):
        if not isinstance(item[key], str) or not item[key].strip() or len(item[key]) > 6000:
            raise ValueError("Required bounded task context missing")
    for key in ("constraints", "completed", "remaining", "pending_effects", "source_paths", "evidence_paths"):
        values = item[key]
        maximum = 30 if key == "source_paths" else 20
        if not isinstance(values, list) or len(values) > maximum or any(
            not isinstance(value, str) or not value.strip() or len(value) > 1800 for value in values
        ):
            raise ValueError("Invalid bounded task context list")
    encoded = json.dumps(item, ensure_ascii=False)
    if len(encoded) > 24000 or re.search(r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{15,}|Bearer\s+[A-Za-z0-9._~+/=-]{12,})", encoded, re.I):
        raise ValueError("Oversized or potentially sensitive context; keep pointers instead")
    return item


def continuity_pins(root: Path, paths: list[str]) -> dict:
    pins = {}
    for value in sorted(set(paths)):
        path = continuity_path(root, value)
        pins[path.relative_to(root.resolve()).as_posix()] = (
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "ABSENT")
    return pins


def continuity_save(root: Path, state: dict, event: dict, record: str, section: str) -> dict:
    """Bind an existing owner record, never create a task or grant authorization."""
    item = continuity_record(root, record, section)
    identity = continuity_identity(event, root)
    paths = [*CONTINUITY_RULES, record, *item["source_paths"], *item["evidence_paths"]]
    pins = continuity_pins(root, paths)
    missing = [path for path, value in pins.items() if value == "ABSENT"]
    # Optional authority files in a portable checkout may be absent; claimed evidence may not.
    for value in [record, *item["source_paths"], *item["evidence_paths"]]:
        if pins[continuity_path(root, value).relative_to(root.resolve()).as_posix()] == "ABSENT":
            raise ValueError("Declared current source/evidence is missing")
    state["continuity"] = {
        "schema_version": 1, "identity": identity, "record": record, "section": section,
        "head": git(root, "rev-parse", "HEAD").strip(), "pins": pins,
        "source_paths": item["source_paths"],
        "prompt_hash": state.get("last_prompt_hash"), "saved_at": time.time(),
        "missing_authorities": missing,
    }
    try:
        state["continuity"]["cached_origin_main"] = git(root, "rev-parse", "origin/main").strip()
    except RuntimeError:
        state["continuity"]["cached_origin_main"] = "UNAVAILABLE"
    return continuity_read(root, state, event)


def continuity_read(root: Path, state: dict, event: dict) -> dict:
    identity = continuity_identity(event, root)
    bound = state.get("continuity")
    result = {"status": "READBACK_REQUIRED", "dispatch_authorized": False,
              "product_accepted": False, "automatic_effect_replay": False,
              "note": "Checkpoint is context evidence, never PO authorization. Reconcile only changed scope; continue independent authorized work."}
    if not bound:
        result["reasons"] = ["NO_BOUND_OWNER_RECORD"]
        return result
    if bound.get("schema_version") != 1 or bound.get("identity") != identity:
        result["reasons"] = ["IDENTITY_OR_SCHEMA_MISMATCH"]
        return result
    result.update({"record": bound["record"], "section": bound["section"],
                   "saved_head": bound["head"], "saved_at": bound["saved_at"]})
    reasons = []
    try:
        pins = continuity_pins(root, list(bound["pins"]))
        changed = [path for path, value in pins.items() if value != bound["pins"][path]]
        result["changed_paths"] = changed
        current_head = git(root, "rev-parse", "HEAD").strip()
        result["current_head"] = current_head
        if current_head != bound["head"]:
            reasons.append("HEAD_CHANGED")
        try:
            cached_origin = git(root, "rev-parse", "origin/main").strip()
        except RuntimeError:
            cached_origin = "UNAVAILABLE"
        result["cached_origin_main"] = cached_origin
        result["remote_is_freshly_queried"] = False
        if cached_origin != bound.get("cached_origin_main"):
            reasons.append("CACHED_ORIGIN_CHANGED")
        if changed:
            reasons.append("PINNED_INPUT_CHANGED")
        if state.get("last_prompt_hash") != bound.get("prompt_hash"):
            reasons.append("NEW_MESSAGE_SINCE_CHECKPOINT")
        if bound.get("missing_authorities"):
            reasons.append("AUTHORITY_UNAVAILABLE")
        result["context"] = continuity_record(root, bound["record"], bound["section"])
        if result["context"]["pending_effects"]:
            reasons.append("PENDING_EFFECTS_REQUIRE_RECEIPT_READBACK")
    except (OSError, ValueError, KeyError, TypeError):
        reasons.append("OWNER_RECORD_UNREADABLE_OR_INVALID")
    result["status"] = "RECONCILE_REQUIRED" if reasons else "PINNED_CONTEXT"
    result["reasons"] = reasons
    return result


def continuity_context(root: Path, state: dict, event: dict) -> str:
    if not event.get("session_id"):
        return " Continuity identity NOT_VERIFIED; do not borrow another window's checkpoint."
    result = continuity_read(root, state, event)
    pointer = (f" {result['record']}#{result['section']}." if result.get("record") else " No owner record bound.")
    return (
        f" Continuity={result['status']}.{pointer} "
        "Read python .codex/engineering.py continuity --params '{\"mode\":\"read\"}' before resuming writes. "
        "Compare latest direct PO instructions, full outcome/open requirements, current owner/reservations "
        "and receipts; reconcile changed scope, not a whole-repo restart. Historical Goal PAUSED/RUNNING "
        "and summaries do not dispatch or stop windows. Never replay uncertain writes/collection/paid effects: "
        "read their existing receipt/process first. Checkpoint is not authorization or acceptance."
    )


def continuity_context_fingerprint(
    root: Path,
    state: dict,
    current_head: str | None = None,
    additional_immutable_paths: list[str] | None = None,
) -> str:
    """Fingerprint the admitted Owner/task/evidence context, excluding mutable source bytes."""
    bound = state.get("continuity")
    if not isinstance(bound, dict):
        payload = {"binding": "MISSING"}
    else:
        try:
            source_paths = sorted({
                continuity_path(root, value).relative_to(root.resolve()).as_posix()
                for value in bound.get("source_paths", [])
            })
            saved_pins = bound.get("pins")
            if not isinstance(saved_pins, dict):
                raise ValueError("continuity pins unavailable")
            item = continuity_record(root, bound.get("record"), bound.get("section"))
            immutable_paths = {
                continuity_path(root, value).relative_to(root.resolve()).as_posix()
                for value in [
                    *CONTINUITY_RULES,
                    bound.get("record"),
                    *item["evidence_paths"],
                    *(additional_immutable_paths or []),
                ]
                if value
            }
            mutable_source_paths = set(source_paths) - immutable_paths
            context_paths = sorted(set(saved_pins) - mutable_source_paths)
            current_pins = continuity_pins(root, context_paths)
            if current_head is None:
                current_head = git(root, "rev-parse", "HEAD").strip()
            try:
                current_origin = git(root, "rev-parse", "origin/main").strip()
            except RuntimeError:
                current_origin = "UNAVAILABLE"
            record_hash = hashlib.sha256(
                json.dumps(item, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()
            payload = {
                "schema_version": bound.get("schema_version"),
                "identity": bound.get("identity"),
                "record": bound.get("record"),
                "section": bound.get("section"),
                "owner_record_hash": record_hash,
                "source_paths": source_paths,
                "immutable_source_paths": sorted(set(source_paths) & immutable_paths),
                "saved_head": bound.get("head"),
                "current_head": current_head,
                "saved_prompt_hash": bound.get("prompt_hash"),
                "current_prompt_hash": state.get("last_prompt_hash"),
                "saved_cached_origin_main": bound.get("cached_origin_main"),
                "current_cached_origin_main": current_origin,
                "missing_authorities": sorted(bound.get("missing_authorities", [])),
                "saved_context_pins": {path: saved_pins[path] for path in context_paths},
                "current_context_pins": current_pins,
            }
        except (OSError, ValueError, KeyError, TypeError, RuntimeError):
            payload = {
                "binding": "UNREADABLE",
                "identity": bound.get("identity"),
                "record": bound.get("record"),
                "section": bound.get("section"),
                "saved_head": bound.get("head"),
                "saved_prompt_hash": bound.get("prompt_hash"),
                "current_prompt_hash": state.get("last_prompt_hash"),
            }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def verification_fingerprint(root: Path, state: dict, now: dict) -> str:
    """Other Owners' edits must not invalidate this bound outcome's checks."""
    bound = state.get("continuity")
    paths = bound.get("source_paths") if isinstance(bound, dict) else None
    if not paths:
        return now["fingerprint"]
    pins = continuity_pins(root, [*paths, str(VERIFICATION_POLICY_PATH)])
    context = continuity_context_fingerprint(root, state, now.get("head"))
    return hashlib.sha256(json.dumps([now["head"], pins, context], sort_keys=True).encode()).hexdigest()


def verification_receipt_current(root: Path, state: dict, receipt: dict, now: dict) -> bool:
    if receipt.get("fingerprint") != verification_fingerprint(root, state, now):
        return False
    if receipt.get("runner") != "engineering_cli":
        return True
    if receipt.get("continuity_binding_stable") is not True:
        return False
    binding_start = receipt.get("continuity_binding_start")
    immutable_paths = binding_start.get("additional_immutable_paths", []) if isinstance(binding_start, dict) else []
    if not isinstance(immutable_paths, list) or any(not isinstance(value, str) for value in immutable_paths):
        return False
    if receipt.get("continuity_binding_fingerprint_end") != continuity_context_fingerprint(
        root, state, now.get("head"), immutable_paths
    ):
        return False
    running = receipt.get("status") == "RUNNING"
    head_key = "head_start" if running else "head_end"
    source_pin_key = "source_pins_start" if running else "source_pins_end"
    policy_pin_key = "policy_pins_start" if running else "policy_pins_end"
    package_dirty_key = "package_dirty_start" if running else "package_dirty_end"
    if receipt.get(head_key) != now.get("head"):
        return False
    paths = receipt.get("verification_paths")
    source_pins = receipt.get(source_pin_key)
    policy_pins = receipt.get(policy_pin_key)
    if not isinstance(paths, list) or not paths or not isinstance(source_pins, dict) or not isinstance(policy_pins, dict):
        return False
    try:
        if continuity_pins(root, paths) != source_pins:
            return False
        if continuity_pins(root, [str(VERIFICATION_POLICY_PATH)]) != policy_pins:
            return False
        package = receipt.get("package_root")
        if package:
            package_rel = Path(package)
            if package_rel.is_absolute() or package_rel.drive or ".." in package_rel.parts:
                return False
            package_path = (root / package_rel).resolve()
            if not package_path.is_relative_to(root.resolve()):
                return False
            if not package_path.is_dir():
                return False
            prefix = package.rstrip("/") + "/"
            package_dirty = {path: value for path, value in now.get("files", {}).items()
                             if path == package or path.startswith(prefix)}
            if package_dirty != receipt.get(package_dirty_key):
                return False
    except (OSError, ValueError, TypeError):
        return False
    command = receipt.get("command_argv")
    is_pytest = (
        receipt.get("kind") == "test"
        and isinstance(command, list)
        and len(command) >= 5
        and command[1:5] == ["-X", "utf8", "-m", "pytest"]
    )
    if is_pytest:
        review = receipt.get("pytest_review_receipt")
        binding_owner = binding_start.get("owner") if isinstance(binding_start, dict) else None
        if not isinstance(review, dict) or review.get("schema_version") != 1 or review.get("owner") != binding_owner:
            return False
        if review.get("repository_root") != str(root.resolve()):
            return False
        config_path = review.get("selected_config", {}).get("path") if isinstance(review.get("selected_config"), dict) else None
        config_hash = review.get("selected_config", {}).get("sha256") if isinstance(review.get("selected_config"), dict) else None
        config_pins = review.get("config_candidate_pins")
        conftest_pins = review.get("conftest_candidate_pins")
        approved_sources = review.get("reviewed_sources")
        if (not isinstance(config_path, str) or not isinstance(config_hash, str)
                or not isinstance(config_pins, dict) or not isinstance(conftest_pins, dict)
                or not isinstance(approved_sources, list)):
            return False
        if config_pins.get(config_path) != config_hash or config_path not in paths:
            return False
        if receipt.get("pytest_selected_config") != config_path:
            return False
        if any(not isinstance(path, str) or path not in paths or not isinstance(digest, str)
               or source_pins.get(path) != digest for path, digest in config_pins.items()):
            return False
        if any(not isinstance(path, str) or path not in paths or not isinstance(digest, str)
               or source_pins.get(path) != digest for path, digest in conftest_pins.items()):
            return False
        for approved in approved_sources:
            if (not isinstance(approved, dict) or approved.get("owner") != binding_owner
                    or not isinstance(approved.get("path"), str)
                    or approved["path"] not in paths
                    or source_pins.get(approved["path"]) != approved.get("sha256")
                    or not isinstance(approved.get("purpose"), str)
                    or not approved["purpose"].strip()
                    or not isinstance(approved.get("allowed_imports"), list)
                    or any(not isinstance(value, str) for value in approved["allowed_imports"])
                    or not isinstance(approved.get("allowed_plugins"), list)
                    or any(not isinstance(value, str) for value in approved["allowed_plugins"])):
                return False
        active_conftests = receipt.get("pytest_active_conftest_paths")
        if not isinstance(active_conftests, list) or any(not isinstance(path, str) for path in active_conftests):
            return False
        expected_immutable = {config_path, *active_conftests, *(value["path"] for value in approved_sources)}
        if (any(path not in paths for path in expected_immutable)
                or set(immutable_paths) != expected_immutable
                or receipt.get("pytest_owner_approved_paths") != sorted(expected_immutable)):
            return False
        if any(path not in conftest_pins or conftest_pins[path] == "ABSENT" for path in active_conftests):
            return False
        edges = review.get("fixture_dependency_edges")
        if not isinstance(edges, list):
            return False
        reviewed_by_path = {value["path"]: value for value in approved_sources}
        for edge in edges:
            if (not isinstance(edge, dict) or edge.get("owner") != binding_owner
                    or not isinstance(edge.get("declared_by"), str)
                    or not isinstance(edge.get("module"), str)
                    or not isinstance(edge.get("path"), str)
                    or edge["declared_by"] not in reviewed_by_path
                    or edge["path"] not in paths):
                return False
            reviewed_dependency = reviewed_by_path.get(edge["path"])
            declared_review = reviewed_by_path[edge["declared_by"]]
            expected_module_path = Path(*edge["module"].split(".")).with_suffix(".py").as_posix()
            if (not isinstance(reviewed_dependency, dict)
                    or edge["path"] != expected_module_path
                    or edge["module"] not in declared_review.get("allowed_plugins", [])
                    or edge.get("sha256") != reviewed_dependency.get("sha256")
                    or edge.get("purpose") != reviewed_dependency.get("purpose")):
                return False
    return True


def changed_scope_paths(root: Path, state: dict, now: dict) -> set[str]:
    """Compare tracked clean files via Git history, not absent dirty-map entries."""
    baseline = state.get("baseline", {})
    before, after = baseline.get("files", {}), now["files"]
    changed = {path for path in before.keys() | after.keys()
               if before.get(path) != after.get(path)}
    paths = state.get("continuity", {}).get("source_paths")
    if paths:
        scope = {continuity_path(root, path).relative_to(root.resolve()).as_posix()
                 for path in paths}
        changed.intersection_update(scope)
        # A committed edit disappears from porcelain but is still an owned change.
        if baseline.get("head") and baseline["head"] != now["head"]:
            committed = git(root, "diff", "--name-only", "-z", baseline["head"],
                            now["head"], "--", *sorted(scope))
            changed.update(path for path in committed.split("\0") if path)
    return changed


def handle(event: dict, root: Path, state: dict) -> dict:
    name = str(event.get("hook_event_name", ""))
    state["updated_at"] = time.time()
    if name in {"SessionEnd", "Interrupt"}:
        state["last_event"] = name; return {}
    if name == "PreToolUse":
        reason = policy_reason(event)
        return {"hookSpecificOutput": {"hookEventName": name, "permissionDecision": "deny", "permissionDecisionReason": reason}} if reason else {}
    if name in {"SessionStart", "UserPromptSubmit"}:
        reason = project_primary_model_override_reason(root)
        if reason:
            return {"continue": False, "stopReason": reason,
                    "systemMessage": "LUMENIS manual-selection guard blocked this turn: " + reason}
    if name == "SubagentStart":
        return context(name, model_policy_context(event) + " Use the current local AGENTS.md concurrency and owner contract, not a historical round/window limit. Own ordinary bugs/blockers inside the assigned Owner end-to-end: reproduce once, research current official docs plus maintained upstream GitHub/high-quality current implementations when needed, choose the strongest feasible complete solution, implement, verify recovery and continue toward the full outcome. Escalate only genuine product/permission/paid-resource/security/external blockers. Return scoped diff, exit statuses and runtime evidence; never overlap unknown work.")
    if name == "PreCompact":
        state["last_event"] = name
        state["pre_compact"] = {"at": time.time(), "snapshot": snapshot(root),
                                "continuity": continuity_read(root, state, event) if event.get("session_id") else {"status": "READBACK_REQUIRED"}}
        # Do not copy task text into global state or silently refresh stale pins.
        state["pre_compact"]["continuity"].pop("context", None)
        return {}
    if name in {"PostCompact", "SubagentStop"}:
        state["last_event"] = name
        return {}  # Native SessionStart(source=compact) supplies context next request.
    if name == "UserPromptSubmit":
        # Never persist the raw user prompt, credentials or agent-relayed instructions.
        state["last_prompt_hash"] = hashlib.sha256(str(event.get("prompt", "")).encode("utf-8")).hexdigest()
        state["last_prompt_at"] = time.time()
        state["routes"] = route_prompt(str(event.get("prompt", "")))
        routed = "\n".join(state["routes"])
        message = model_policy_context(event)
        if routed:
            message += "\n" + routed
        return context(name, message)
    if name == "SessionStart":
        now = snapshot(root)
        if "baseline" not in state or event.get("source") == "clear":
            state["baseline"] = now; state["receipts"] = []; state["mutation_observed"] = False
        if event.get("source") == "clear":
            state.pop("continuity", None)
        try: origin = git(root, "rev-parse", "origin/main").strip()
        except RuntimeError: origin = "UNAVAILABLE"
        current_rel = "00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md"
        current_note = ""
        if current_rel in now.get("files", {}):
            current_note = (
                " CURRENT has local uncommitted modifications. Treat only the published HEAD copy as GitHub-main truth; "
                "the local delta is LOCAL_CANDIDATE_ONLY until its owning source/tests/evidence are validated and published. "
            )
        message = (model_policy_context(event) + " " + f"Current local HEAD={now['head']}; cached origin/main={origin} (not a fresh network read). Before integration fetch/reconcile protected work.{current_note} "
                   + continuity_context(root, state, event))
        return context(name, message[:2400])
    if name == "PostToolUse":
        state.pop("compile_envelope_probe", None)
        state.pop("compile_event_probe", None)
        now = snapshot(root)
        state.setdefault("baseline", now)
        previous = state.get("last_snapshot", state["baseline"])
        if now["fingerprint"] != previous["fingerprint"]: state["mutation_observed"] = True
        tool = str(event.get("tool_name", ""))
        if tool in SHELL or tool == "write_stdin":
            response = event.get("tool_response")
            state["last_shell_response_shape"] = {
                "tool": tool, "type": type(response).__name__,
                "keys": [key for key in ("exit_code", "exitCode", "returncode", "isError", "content", "output", "result", "stdout", "text")
                         if isinstance(response, dict) and key in response],
                "members": {key: type(response[key]).__name__ for key in
                            ("content", "output", "result", "stdout", "text")
                            if isinstance(response, dict) and key in response},
                "exit_status_available": exit_status(response) is not None,
            }
        if tool == "apply_patch" and exit_status(event.get("tool_response")) != 1:
            state["mutation_observed"] = True
        native_exit_code = exit_status(event.get("tool_response"))
        native_command = command(event)
        engineering_runner = bool(re.search(r"\.codex[\\/]engineering\.py\s+verification_run\b", native_command, re.I))
        kind = verification_kind(native_command) if tool in SHELL and not engineering_runner else None
        if kind and native_exit_code is not None:
            receipt = {"kind": kind, "exit_code": native_exit_code, "fingerprint": verification_fingerprint(root, state, now), "at": time.time()}
            state.setdefault("receipts", []).append(receipt)
            state["receipts"] = state["receipts"][-20:]
        state["last_snapshot"] = now
        return {}
    if name == "Stop":
        if not state.get("mutation_observed"): return {}
        now = snapshot(root)
        scoped_changes = changed_scope_paths(root, state, now)
        if state.get("continuity", {}).get("source_paths") and not scoped_changes:
            return {}  # Another Owner's edits cannot impose this task's checks.
        code_changed = any(Path(path).suffix.lower() in CODE for path in scoped_changes)
        policy = load_verification_policy(root)
        policy_known = isinstance(policy, dict) and all(
            type(policy.get(key)) is bool for key in (
                "unit_integration_required", "create_unit_integration_allowed",
                "run_unit_integration_allowed", "renamed_module_suites_allowed"))
        if not policy_known:
            state["verification_status"] = "BLOCKED_VERIFICATION_POLICY_UNAVAILABLE"
            reason = "The machine verification_policy is missing or invalid; reconcile its approved values before claiming completion. Hooks never start a test suite."
            if event.get("stop_hook_active"):
                return {"continue": False, "stopReason": reason, "systemMessage": "LUMENIS verification policy is unavailable; no suite was started."}
            return {"decision": "block", "reason": reason}
        retained = set(policy.get("retained_checks", []))
        required_retained = {"compilation", "static_quality"} if code_changed else set()
        if ((required_retained and not required_retained.issubset(retained))
                or (not required_retained and not retained.intersection({"compilation", "static_quality"}))):
            state["verification_status"] = "BLOCKED_RETAINED_CHECK_MISSING"
            reason = "The current machine verification_policy does not retain every applicable compilation/static-quality check; reconcile the policy before claiming completion."
            if event.get("stop_hook_active"):
                return {"continue": False, "stopReason": reason, "systemMessage": "LUMENIS verification policy is incomplete; stopped without running a suite."}
            return {"decision": "block", "reason": reason}
        current = [r for r in state.get("receipts", []) if verification_receipt_current(root, state, r, now)]
        quality_kinds = {"compile", "static"} if code_changed else {"compile", "static", "diff"}
        quality = [r for r in current if r["kind"] in quality_kinds]
        tests = [r for r in current if r["kind"] == "test"]
        tests_required = code_changed and policy.get("affected_regressions_required") is True
        tests_allowed = policy.get("run_unit_integration_allowed") is True
        if code_changed:
            latest_quality = {
                kind: next((r for r in reversed(quality) if r["kind"] == kind), None)
                for kind in ("compile", "static")
            }
            good = all(item is not None and item.get("exit_code") == 0 for item in latest_quality.values())
        else:
            good = bool(quality) and quality[-1].get("exit_code") == 0
        if tests_allowed and tests:
            good = good and tests[-1]["exit_code"] == 0
        if tests_required:
            good = good and tests_allowed and bool(tests) and tests[-1]["exit_code"] == 0
        state["verification_status"] = "SCOPED_CHECK_OBSERVED" if good else "BLOCKED_MISSING_SUCCESSFUL_CHECK"
        if good: return {}
        reason = "Current-snapshot compilation/static quality and applicable authorized regression evidence are missing or failed. A diff check alone cannot verify code. Hooks never start suites. Security, source rights, data consistency, recovery and real user E2E remain separate acceptance requirements."
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
