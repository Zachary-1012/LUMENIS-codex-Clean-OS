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

import tomllib

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
DELIVERY_FIELDS = {"schema_version", "status", "po_source", "scope_sources", "requirements"}
DELIVERY_OPTIONAL_FIELDS = {"exit"}
DELIVERY_STATUSES = {
    "RUNNING", "REPORT_ONLY", "PO_PAUSED", "APPROVAL_WAIT",
    "EXTERNAL_BLOCKED", "PO_DEFERRED", "JOB_CLOSED",
}
DELIVERY_REQUIREMENT_STATUSES = {
    "OPEN", "IMPLEMENTED", "INTEGRATED", "VERIFIED", "JOB_CLOSED", "DEFER", "PO_DEFERRED", "BLOCKED",
}
DELIVERY_OUTCOME_CLASSES = {"PRODUCT", "DEVELOPMENT_TOOL"}
DELIVERY_EVIDENCE_KINDS = {"REAL_USER_E2E", "TOOL_WORKFLOW", "RECOVERY", "EXTERNAL_BLOCKER"}
DELIVERY_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,119}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
MAX_EVIDENCE_PATHS = 220


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
                          timeout=10, encoding="utf-8", errors="strict", check=False)
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

def snapshot(root: Path, pinned_paths: set[str] | None = None) -> dict:
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
    for value in pinned_paths or set():
        path = continuity_path(root, value)
        relative = path.relative_to(root.resolve()).as_posix()
        if path.is_file():
            stat = path.stat()
            pinned_value = (
                hashlib.sha256(path.read_bytes()).hexdigest()
                if stat.st_size < 2000000 else f"large:{stat.st_size}:{stat.st_mtime_ns}"
            )
        else:
            pinned_value = "deleted"
        files[relative] = pinned_value
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
        if re.search(pattern, command(event), re.IGNORECASE): return reason
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
    if re.search(start + r"(?:flutter(?:\.bat)?\s+build\b|dart\s+compile\b|" + py + r"\s+-m\s+(?:compileall|py_compile)\b)", text, re.IGNORECASE): return "compile"
    if re.search(start + r"git\s+diff\s+--check\b", text, re.IGNORECASE): return "diff"
    if re.search(start + r"(?:pytest(?:\.exe)?\b|" + py + r"\s+-m\s+(?:pytest|unittest)\b|flutter(?:\.bat)?\s+test\b)", text, re.IGNORECASE): return "test"
    if re.search(start + r"(?:(?:flutter|dart)(?:\.bat)?\s+analyze\b|ruff(?:\.exe|\.cmd)?\s+check\b|codex\s+doctor\b)", text, re.IGNORECASE): return "static"
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
    return [value for pattern, value in rules if re.search(pattern, prompt, re.IGNORECASE)]

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
    if re.search(r"cookie|credential|secret|auth\.json", rel.name, re.IGNORECASE):
        raise ValueError("Sensitive continuity input rejected")
    path = (root / rel).resolve()
    if not path.is_relative_to(root.resolve()) or path.suffix.lower() not in TEXT:
        raise ValueError("Only repository text references are supported")
    if path.is_file() and path.stat().st_size > 2_000_000:
        raise ValueError("Reference exceeds bounded read limit")
    return path


def _delivery_source_manifest(root: Path, delivery: dict) -> dict[str, str]:
    values = delivery.get("scope_sources")
    if not isinstance(values, list) or not values or len(values) > 40:
        raise ValueError("Delivery scope_sources must enumerate the complete existing scope")
    result = {}
    for entry in values:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            raise ValueError("Invalid delivery scope source")
        value, digest = entry["path"], entry["sha256"]
        path = continuity_path(root, value)
        if not path.is_file() or path.is_symlink() or not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise ValueError("Delivery scope source must be a current repository text file with SHA-256")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Delivery scope source hash is stale; reconcile the current source before continuing")
        relative = path.relative_to(root.resolve()).as_posix()
        if relative in result:
            raise ValueError("Duplicate delivery scope source")
        result[relative] = digest
    return result


def _delivery_evidence_is_current(root: Path, item: dict, requirement_id: str,
                                  evidence: dict, expected_result: str) -> bool:
    """Check immutable receipt provenance and current source pins; HEAD is historical context."""
    required = {"path", "sha256", "kind", "result", "head", "source_pins"}
    if not isinstance(evidence, dict) or set(evidence) != required:
        return False
    if (evidence.get("kind") not in DELIVERY_EVIDENCE_KINDS
            or evidence.get("result") != expected_result
            or not isinstance(evidence.get("head"), str)
            or not re.fullmatch(r"[0-9a-f]{40,64}", evidence["head"])
            or not isinstance(evidence.get("sha256"), str)
            or not SHA256_RE.fullmatch(evidence["sha256"])):
        return False
    declared = set(item.get("evidence_paths", []))
    if evidence.get("path") not in declared:
        return False
    path = continuity_path(root, evidence["path"])
    raw_path = root / Path(evidence["path"])
    if not path.is_file() or raw_path.is_symlink() or path.stat().st_size > 2_000_000:
        return False
    body = path.read_bytes()
    if hashlib.sha256(body).hexdigest() != evidence["sha256"]:
        return False
    try:
        receipt = json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    if not isinstance(receipt, dict):
        return False
    encoded = json.dumps(receipt, ensure_ascii=False)
    if re.search(r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{15,}|Bearer\s+[A-Za-z0-9._~+/=-]{12,})", encoded, re.IGNORECASE):
        return False
    if (receipt.get("schema_version") != 1
            or receipt.get("requirement_id") != requirement_id
            or receipt.get("kind") != evidence["kind"]
            or receipt.get("result") != expected_result
            or receipt.get("head") != evidence["head"]
            or receipt.get("source_pins") != evidence["source_pins"]
            or not isinstance(receipt.get("observation"), str)
            or len(receipt["observation"].strip()) < 10):
        return False
    source_pins = evidence.get("source_pins")
    if not isinstance(source_pins, dict) or not source_pins or len(source_pins) > 80:
        return False
    allowed_sources = {
        continuity_path(root, value).relative_to(root.resolve()).as_posix()
        for value in item.get("source_paths", [])
    }
    allowed_sources.update(
        continuity_path(root, entry["path"]).relative_to(root.resolve()).as_posix()
        for entry in item.get("delivery", {}).get("scope_sources", [])
    )
    if set(source_pins) != allowed_sources:
        return False
    for value, digest in source_pins.items():
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            return False
        source = continuity_path(root, value)
        if (not source.is_file() or source.is_symlink()
                or hashlib.sha256(source.read_bytes()).hexdigest() != digest):
            return False
    return True


def validate_delivery(root: Path, item: dict) -> dict | None:
    delivery = item.get("delivery")
    if delivery is None:
        return None
    if (not isinstance(delivery, dict)
            or not DELIVERY_FIELDS.issubset(delivery)
            or set(delivery) - DELIVERY_FIELDS - DELIVERY_OPTIONAL_FIELDS
            or delivery.get("schema_version") != 1
            or delivery.get("status") not in DELIVERY_STATUSES
            or not isinstance(delivery.get("po_source"), str)
            or not delivery["po_source"].strip()
            or len(delivery["po_source"]) > 6000):
        raise ValueError("Invalid structured delivery contract")
    scope = _delivery_source_manifest(root, delivery)
    if delivery.get("status") == "JOB_CLOSED" and item.get("pending_effects"):
        raise ValueError("JOB_CLOSED is forbidden while any pending effect lacks a resolved receipt")
    requirements = delivery.get("requirements")
    if not isinstance(requirements, list) or not requirements or len(requirements) > 100:
        raise ValueError("Delivery requirements must enumerate the complete admitted outcome")
    seen = set()
    for requirement in requirements:
        if not isinstance(requirement, dict):
            raise TypeError("Invalid delivery requirement")
        required = {"id", "outcome_class", "acceptance", "coverage_refs", "status", "evidence"}
        if (not required.issubset(requirement)
                or set(requirement) - required - {"po_source"}
                or not isinstance(requirement.get("id"), str)
                or not DELIVERY_ID_RE.fullmatch(requirement["id"])
                or requirement["id"] in seen
                or requirement.get("outcome_class") not in DELIVERY_OUTCOME_CLASSES
                or not isinstance(requirement.get("acceptance"), str)
                or not requirement["acceptance"].strip()
                or len(requirement["acceptance"]) > 4000
                or requirement.get("status") not in DELIVERY_REQUIREMENT_STATUSES):
            raise ValueError("Invalid or duplicate delivery requirement")
        seen.add(requirement["id"])
        refs = requirement.get("coverage_refs")
        if (not isinstance(refs, list) or not refs or len(refs) > 100
                or any(not isinstance(value, str) or not value.strip() or len(value) > 180 for value in refs)
                or len(set(refs)) != len(refs)):
            raise ValueError("Every outcome must retain its full existing coverage references")
        if requirement["status"] == "PO_DEFERRED" and (
                not isinstance(requirement.get("po_source"), str)
                or not requirement["po_source"].strip()
                or len(requirement["po_source"]) > 6000):
            raise ValueError("PO_DEFERRED must preserve its direct Product Owner source")
        required_source_pins = {
            continuity_path(root, value).relative_to(root.resolve()).as_posix()
            for value in item.get("source_paths", [])
        }
        required_source_pins.update(scope)
        evidence_values = requirement.get("evidence")
        if not isinstance(evidence_values, list) or len(evidence_values) > 40:
            raise ValueError("Invalid delivery evidence list")
        for evidence in evidence_values:
            if (not isinstance(evidence, dict)
                    or set(evidence) != {"path", "sha256", "kind", "result", "head", "source_pins"}
                    or evidence.get("kind") not in DELIVERY_EVIDENCE_KINDS
                    or evidence.get("result") not in {"ACCEPTED", "BLOCKED"}
                    or evidence.get("path") not in item.get("evidence_paths", [])
                    or not isinstance(evidence.get("sha256"), str)
                    or not SHA256_RE.fullmatch(evidence["sha256"])
                    or not isinstance(evidence.get("head"), str)
                    or not re.fullmatch(r"[0-9a-f]{40,64}", evidence["head"])
                    or not isinstance(evidence.get("source_pins"), dict)
                    or not evidence["source_pins"]
                    or len(evidence["source_pins"]) > 80
                    or set(evidence["source_pins"]) != required_source_pins
                    or any(not isinstance(value, str) or not SHA256_RE.fullmatch(value)
                           for value in evidence["source_pins"].values())):
                raise ValueError("Invalid delivery evidence reference")
            if evidence["kind"] == "EXTERNAL_BLOCKER" and evidence["result"] != "BLOCKED":
                raise ValueError("External blocker evidence cannot claim acceptance")
            if evidence["kind"] != "EXTERNAL_BLOCKER" and evidence["result"] != "ACCEPTED":
                raise ValueError("Outcome evidence must be an accepted real operation or recovery")
        if requirement["status"] == "JOB_CLOSED":
            kinds = {value.get("kind") for value in evidence_values
                     if _delivery_evidence_is_current(root, item, requirement["id"], value, "ACCEPTED")}
            required_outcome_kind = (
                "REAL_USER_E2E" if requirement["outcome_class"] == "PRODUCT" else "TOOL_WORKFLOW"
            )
            if required_outcome_kind not in kinds or "RECOVERY" not in kinds:
                raise ValueError(
                    f"JOB_CLOSED requires current-version {required_outcome_kind} and recovery receipts"
                )
    if delivery["status"] == "JOB_CLOSED":
        if item.get("remaining"):
            raise ValueError("JOB_CLOSED requires the continuity record's remaining list to be empty")
        if any(value["status"] != "JOB_CLOSED" for value in requirements):
            raise ValueError("Delivery cannot close while any required outcome remains open, deferred, or blocked")
    exit_record = delivery.get("exit")
    if exit_record is not None:
        if (not isinstance(exit_record, dict)
                or set(exit_record) != {"reason", "evidence_path", "resume_condition"}
                or any(not isinstance(exit_record.get(key), str) or not exit_record[key].strip()
                       for key in ("reason", "evidence_path", "resume_condition"))):
            raise ValueError("Non-closure exit must preserve its reason, evidence, and resume condition")
        if exit_record["evidence_path"] not in item.get("evidence_paths", []):
            raise ValueError("Exit evidence must be declared in the existing continuity record")
    if delivery["status"] == "EXTERNAL_BLOCKED":
        unfinished = [value for value in requirements if value["status"] != "JOB_CLOSED"]
        if not unfinished or exit_record is None:
            raise ValueError("EXTERNAL_BLOCKED requires a concrete blocker receipt and resume condition")
        if any(value["status"] != "BLOCKED" for value in unfinished):
            raise ValueError("A blocked outcome cannot stop independent work that remains executable")
        blocker_paths = set()
        for value in unfinished:
            valid_paths = {
                evidence.get("path") for evidence in value["evidence"]
                if evidence.get("kind") == "EXTERNAL_BLOCKER"
                and _delivery_evidence_is_current(root, item, value["id"], evidence, "BLOCKED")
            }
            if not valid_paths:
                raise ValueError("Every remaining blocked outcome requires its own current, source-pinned blocker evidence")
            blocker_paths.update(valid_paths)
        if exit_record["evidence_path"] not in blocker_paths:
            raise ValueError("EXTERNAL_BLOCKED exit must point to one of its verified blocker receipts")
    if delivery["status"] == "PO_DEFERRED":
        unfinished = [value for value in requirements if value["status"] != "JOB_CLOSED"]
        if not unfinished or any(value["status"] != "PO_DEFERRED" for value in unfinished):
            raise ValueError("PO_DEFERRED may exit only when every remaining requirement is explicitly deferred")
        if exit_record is None:
            raise ValueError("PO_DEFERRED requires a preserved source receipt and resume condition")
        deferred_ids = {value["id"] for value in unfinished}
        if ("PO_DEFERRED" not in exit_record["reason"].upper()
                or any(identifier not in exit_record["reason"] for identifier in deferred_ids)):
            raise ValueError("PO_DEFERRED exit reason must name the non-closed requirements")
        source_path = continuity_path(root, exit_record["evidence_path"])
        raw_source_path = root / Path(exit_record["evidence_path"])
        if (not source_path.is_file() or raw_source_path.is_symlink()
                or source_path.stat().st_size > 2_000_000):
            raise ValueError("PO_DEFERRED requires a readable, repository-local Product Owner source receipt")
        source_key = source_path.relative_to(root.resolve()).as_posix()
        if source_key not in scope:
            raise ValueError("PO_DEFERRED source receipt must be included in the frozen source manifest")
        source_text = source_path.read_text("utf-8-sig")
        if not re.search(r"\b(?:product owner|direct\s+po|po\s+(?:instruction|approval|decision))\b",
                         source_text, re.IGNORECASE):
            raise ValueError("PO_DEFERRED source receipt must identify a direct Product Owner instruction")
        normalized_source = " ".join(source_text.split())
        for requirement in unfinished:
            normalized_requirement_source = " ".join(requirement["po_source"].split())
            if (requirement["id"] not in source_text
                    or normalized_requirement_source not in normalized_source):
                raise ValueError("PO_DEFERRED source receipt must name each deferred requirement and its PO source")
    return {"scope_sources": scope, "requirements": requirements}


def continuity_record(root: Path, record: str, section: str) -> dict:
    path = continuity_path(root, record)
    if path.suffix != ".json" or Path(record).parts[0] != "work":
        raise ValueError("Use a section in the existing local work JSON record")
    if not isinstance(section, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", section):
        raise ValueError("Exact top-level section required")
    item = json.loads(path.read_text("utf-8-sig"))[section]
    if (not isinstance(item, dict) or not CONTINUITY_FIELDS.issubset(item)
            or set(item) - CONTINUITY_FIELDS - {"delivery"}):
        raise ValueError("Incomplete or unexpected continuity fields")
    if item["owner"] not in {"M", "F", "C1", "C2", "C3", "C4", "C5", "C6"}:
        raise ValueError("Unknown existing owner")
    for key in ("objective", "po_source", "next_action", "native_goal"):
        if not isinstance(item[key], str) or not item[key].strip() or len(item[key]) > 6000:
            raise ValueError("Required bounded task context missing")
    for key in ("constraints", "completed", "remaining", "pending_effects", "source_paths", "evidence_paths"):
        values = item[key]
        maximum = {"source_paths": 30, "evidence_paths": MAX_EVIDENCE_PATHS}.get(key, 20)
        if not isinstance(values, list) or len(values) > maximum or any(
            not isinstance(value, str) or not value.strip() or len(value) > 1800 for value in values
        ):
            raise ValueError("Invalid bounded task context list")
    validate_delivery(root, item)
    encoded = json.dumps(item, ensure_ascii=False)
    if len(encoded) > 24000 or re.search(r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{15,}|Bearer\s+[A-Za-z0-9._~+/=-]{12,})", encoded, re.IGNORECASE):
        raise ValueError("Oversized or potentially sensitive context; keep pointers instead")
    return item


def continuity_pins(root: Path, paths: list[str]) -> dict:
    pins = {}
    for value in sorted(set(paths)):
        path = continuity_path(root, value)
        pins[path.relative_to(root.resolve()).as_posix()] = (
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "ABSENT")
    return pins


def _delivery_guard_snapshot(delivery: dict) -> dict:
    requirements = {
        value["id"]: {
            "outcome_class": value["outcome_class"],
            "acceptance": value["acceptance"],
            "coverage_refs": list(value["coverage_refs"]),
            "po_source": value.get("po_source"),
        }
        for value in delivery["requirements"]
    }
    return {
        "schema_version": 1,
        "delivery_status": delivery["status"],
        "record_po_source": delivery["po_source"],
        "requirements": requirements,
        "scope_sources": {value["path"]: [value["sha256"]] for value in delivery["scope_sources"]},
    }


def _check_delivery_rebind(root: Path, state: dict, identity: dict,
                           record: str, section: str, item: dict) -> dict | None:
    guard = state.get("delivery_guard")
    if isinstance(guard, dict):
        if guard.get("identity") != identity:
            raise ValueError("Delivery guard belongs to another session identity")
        prior_record = guard.get("record")
        prior_section = guard.get("section")
        if prior_record != record or prior_section != section:
            old_requirements = guard.get("requirements", {})
            if (guard.get("delivery_status") != "JOB_CLOSED" or not old_requirements
                    or set(guard.get("closed_ids", [])) != set(old_requirements)):
                raise ValueError("Cannot rebind away from an unfinished delivery; preserve its remaining IDs")
            state.pop("delivery_guard", None)
            guard = None
    delivery = item.get("delivery")
    if delivery is None:
        if isinstance(guard, dict) and guard.get("record") == record and guard.get("section") == section:
            raise ValueError("A bound delivery cannot be removed while rebinding continuity")
        return None
    if isinstance(guard, dict) and guard.get("record") == record and guard.get("section") == section:
        prior = guard.get("requirements")
        current = {value["id"]: value for value in delivery["requirements"]}
        if not isinstance(prior, dict) or not set(prior).issubset(current):
            raise ValueError("Rebinding cannot remove any frozen required outcome ID")
        for identifier, frozen in prior.items():
            value = current[identifier]
            if value["outcome_class"] != frozen["outcome_class"]:
                raise ValueError("Rebinding cannot change the frozen product/tool outcome class")
            if value["acceptance"] != frozen["acceptance"]:
                raise ValueError("Rebinding cannot narrow or rewrite frozen acceptance")
            if not set(frozen["coverage_refs"]).issubset(value["coverage_refs"]):
                raise ValueError("Rebinding cannot remove existing coverage references")
            old_po = frozen.get("po_source")
            if old_po and old_po not in str(value.get("po_source", "")):
                raise ValueError("Rebinding must preserve the prior Product Owner deferral source")
        if guard.get("record_po_source") not in delivery["po_source"]:
            raise ValueError("Rebinding must retain the original Product Owner task source")
        scope = {value["path"]: value["sha256"] for value in delivery["scope_sources"]}
        prior_scope = guard.get("scope_sources", {})
        if not isinstance(prior_scope, dict) or not set(prior_scope).issubset(scope):
            raise ValueError("Rebinding cannot remove a frozen scope source reference")
        for path, digest in scope.items():
            history = guard.setdefault("scope_sources", {}).setdefault(path, [])
            if not isinstance(history, list):
                raise TypeError("Delivery source-version history is invalid")
            if digest not in history:
                history.append(digest)
        guard["requirements"] = {
            identifier: {
                "outcome_class": value["outcome_class"],
                "acceptance": value["acceptance"],
                "coverage_refs": list(value["coverage_refs"]),
                "po_source": (
                    prior.get(identifier, {}).get("po_source")
                    or value.get("po_source")
                ),
            }
            for identifier, value in current.items()
        }
        return guard
    delivery_state = _delivery_guard_snapshot(delivery)
    delivery_state.update({
        "identity": identity, "record": record, "section": section,
        "scope_sources": {value["path"]: [value["sha256"]] for value in delivery["scope_sources"]},
        "closed_ids": [],
    })
    state["delivery_guard"] = delivery_state
    return delivery_state


def continuity_save(root: Path, state: dict, event: dict, record: str, section: str) -> dict:
    """Bind an existing owner record, never create a task or grant authorization."""
    item = continuity_record(root, record, section)
    identity = continuity_identity(event, root)
    guard = _check_delivery_rebind(root, state, identity, record, section, item)
    scope_paths = [value["path"] for value in item.get("delivery", {}).get("scope_sources", [])]
    paths = [*CONTINUITY_RULES, record, *item["source_paths"], *item["evidence_paths"], *scope_paths]
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
    if guard is not None:
        guard["delivery_status"] = item["delivery"]["status"]
        guard["closed_ids"] = [value["id"] for value in item["delivery"]["requirements"]
                                if value["status"] == "JOB_CLOSED"]
        state["delivery_guard"] = guard
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
        guard_reasons = delivery_guard_reasons(state, bound, result["context"])
        reasons.extend(guard_reasons)
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
    delivery = result.get("context", {}).get("delivery") if isinstance(result.get("context"), dict) else None
    if isinstance(delivery, dict):
        remaining = [value["id"] for value in delivery.get("requirements", [])
                     if value.get("status") != "JOB_CLOSED"]
        delivery_note = (
            f" Structured delivery={delivery.get('status')}; frozen required IDs are append-only; "
            f"remaining={','.join(remaining[:40]) or 'none'}. OPEN/DEFER/IMPLEMENTED/INTEGRATED/VERIFIED "
            "are not job completion. Scope-source hashes prove only the cited bytes, not that the required list is semantically complete."
        )
    else:
        delivery_note = (
            " Structured delivery guard is not bound for this checkpoint; this is prompt guidance only, "
            "not machine enforcement. Bind the complete existing owner/outcome and mapped coverage before claiming completion; "
            "a list of source-file hashes alone does not prove scope completeness."
        )
    return (
        f" Continuity={result['status']}.{pointer} "
        + delivery_note + " "
        "Read python .codex/engineering.py continuity --params '{\"mode\":\"read\"}' before resuming writes. "
        "Compare latest direct PO instructions, full outcome/open requirements, current owner/reservations "
        "and receipts; reconcile changed scope, not a whole-repo restart. Historical Goal PAUSED/RUNNING "
        "and summaries do not dispatch or stop windows. Never replay uncertain writes/collection/paid effects: "
        "read their existing receipt/process first. Checkpoint is not authorization or acceptance."
    )


def delivery_guard_reasons(state: dict, bound: dict, item: dict) -> list[str]:
    guard = state.get("delivery_guard")
    delivery = item.get("delivery")
    if not isinstance(guard, dict):
        return ["DELIVERY_SCOPE_NOT_FROZEN"] if isinstance(delivery, dict) else []
    if (guard.get("identity") != bound.get("identity")
            or guard.get("record") != bound.get("record")
            or guard.get("section") != bound.get("section")
            or not isinstance(delivery, dict)):
        return ["DELIVERY_GUARD_MISMATCH"]
    frozen = guard.get("requirements")
    current = {value.get("id"): value for value in delivery.get("requirements", [])
               if isinstance(value, dict)}
    reasons = []
    if not isinstance(frozen, dict) or not set(frozen).issubset(current):
        reasons.append("FROZEN_REQUIRED_OUTCOME_REMOVED")
    else:
        for identifier, prior in frozen.items():
            value = current[identifier]
            if value.get("outcome_class") != prior.get("outcome_class"):
                reasons.append("FROZEN_OUTCOME_CLASS_CHANGED")
            if value.get("acceptance") != prior.get("acceptance"):
                reasons.append("FROZEN_ACCEPTANCE_CHANGED")
            if not set(prior.get("coverage_refs", [])).issubset(set(value.get("coverage_refs", []))):
                reasons.append("FROZEN_COVERAGE_REMOVED")
            old_po = prior.get("po_source")
            if old_po and old_po not in str(value.get("po_source", "")):
                reasons.append("PO_DEFERRAL_PROVENANCE_REMOVED")
    old_scope = guard.get("scope_sources", {})
    current_scope = {value.get("path") for value in delivery.get("scope_sources", [])
                     if isinstance(value, dict)}
    if not isinstance(old_scope, dict) or not set(old_scope).issubset(current_scope):
        reasons.append("FROZEN_SCOPE_REFERENCE_REMOVED")
    if guard.get("record_po_source") not in delivery.get("po_source", ""):
        reasons.append("ORIGINAL_PO_TASK_SOURCE_REMOVED")
    return reasons


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
                raise TypeError("continuity pins unavailable")
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
    paths = delivery_scope_paths(root, state)
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


def delivery_scope_paths(root: Path, state: dict) -> set[str]:
    """Return the frozen owner's source scope without changing its session baseline."""
    bound = state.get("continuity")
    paths = bound.get("source_paths", []) if isinstance(bound, dict) else []
    values = {value for value in paths if isinstance(value, str)}
    guard = state.get("delivery_guard")
    if isinstance(guard, dict) and isinstance(guard.get("scope_sources"), dict):
        values.update(value for value in guard["scope_sources"] if isinstance(value, str))
    return {
        continuity_path(root, value).relative_to(root.resolve()).as_posix()
        for value in values
    }


def changed_paths_since(root: Path, before: dict, after: dict, scope: set[str]) -> set[str]:
    """Find only this turn's changes, including committed changes absent from status."""
    normalized_scope = {
        continuity_path(root, value).relative_to(root.resolve()).as_posix()
        for value in scope
    }
    before_files = before.get("files", {})
    after_files = after.get("files", {})
    changed = {path for path in before_files.keys() | after_files.keys()
               if before_files.get(path) != after_files.get(path)}
    if normalized_scope:
        changed.intersection_update(normalized_scope)
    if before.get("head") and before.get("head") != after.get("head"):
        args = ["diff", "--name-only", "-z", before["head"], after["head"]]
        if normalized_scope:
            args.extend(["--", *sorted(normalized_scope)])
        committed = git(root, *args)
        committed_paths = {path for path in committed.split("\0") if path}
        if normalized_scope:
            committed_paths.intersection_update(normalized_scope)
        changed.update(committed_paths)
    return changed


def classify_turn_exit(prompt: str) -> str:
    """Recognize brief, direct exits; quoted, long, or mixed instructions keep running."""
    text = str(prompt or "").strip()
    if (not text or len(text) > 240 or text.count("\n") > 1
            or "<hook_prompt" in text.lower()
            or "```" in text
            or re.search(r"[>『』「」“”‘’]", text)):
        return "RUNNING"
    if re.match(r"^(?:等我|等待我|待我)(?:的)?(?:批准|授权|确认|审批)(?:后|前)?(?:再执行|再继续|之前先停)?[。.!！]?$|^(?:批准|授权|审批)(?:前|之前)(?:先)?(?:等待|不要执行|先停)[。.!！]?", text, re.IGNORECASE):
        return "APPROVAL_WAIT"
    if re.fullmatch(
        r"(?:please\s+)?(?:wait for (?:my|the product owner(?:'s)?) "
        r"(?:approval|review|authorization|confirmation) before "
        r"(?:continuing|proceeding|resuming)|"
        r"(?:do not|don't) (?:continue|proceed|resume) until "
        r"(?:i|the product owner) (?:approve|review|authorize|confirm))\s*[.!]?",
        text,
        re.IGNORECASE,
    ):
        return "APPROVAL_WAIT"
    if re.match(r"^(?:(?:所有|全部|当前)?(?:任务|工作|研发|窗口)?\s*(?:先)?(?:暂停|停工|停止执行)|先别(?:继续|推进|开工)|等我(?:的)?(?:指令|审核|确认)|等我审核完)(?:吧|一下)?(?:[，,]\s*等我(?:的)?(?:审核完|指令|审核|确认))?[。.!！]?\s*$", text, re.IGNORECASE):
        return "PO_PAUSED"
    if re.fullmatch(
        r"(?:please\s+)?(?:pause|stop)\s+(?:(?:all|the current|current)\s+)?"
        r"(?:tasks?|work|windows?)(?:\s+and\s+wait for "
        r"(?:my|the product owner(?:'s)?) (?:review|approval|authorization|confirmation))?\s*[.!]?",
        text,
        re.IGNORECASE,
    ):
        return "PO_PAUSED"
    negative_action = re.compile(
        r"(?:不要|先不|别)(?:再)?(?:修改|执行|继续|实现|更新|开工|推进)"
        r"(?:\s*(?:或|和|并|以及)\s*(?:修改|执行|继续|实现|更新|开工|推进))*",
        re.IGNORECASE,
    )
    report_request = re.match(
        r"^(?:(?:请|给我|向我|先)\s*){0,2}(?:只)?(?:直接)?"
        r"(?:回答|报告|汇报|告诉我)(?:一下)?(?:当前|最新|全部|整体|各窗口|产品)?"
        r"(?:进度|状态|待完成项|完成情况|已经完成什么|还差什么)?"
        r"(?:即可|就行)?(?:[，,。.!！?？].*)?$|"
        r"^(?:当前|最新|各窗口|整体)(?:的)?(?:进度|状态)(?:是什么|如何|怎样)?[。.!！?？]?$|"
        r"^(?:我想|我要|请让我)(?:看|了解|知道)?(?:当前|最新|各窗口|整体)?(?:进度|状态)(?:如何|怎么样|是什么)?[。.!！?？]?$|"
        r"^summary(?:\s+only)?[.!?]?$|^status report[.!?]?$",
        text,
        re.IGNORECASE,
    )
    if report_request and not re.search(
        r"继续|修复|实现|更新|开工|推进|同步落实|接着做", negative_action.sub("", text), re.IGNORECASE
    ):
        return "REPORT_ONLY"
    if re.search(r"继续|执行|修复|实现|更新|开工|推进|同步落实|继续做|接着做", negative_action.sub("", text), re.IGNORECASE):
        return "RUNNING"
    # Only a direct report request exits this turn; clarifications and task
    # prompts that merely mention status continue through the full outcome.
    return "REPORT_ONLY" if report_request else "RUNNING"


def delivery_stop_check(root: Path, state: dict, event: dict) -> tuple[bool, str | None]:
    mode = state.get("turn_exit_mode", "RUNNING")
    if mode == "REPORT_ONLY":
        now = snapshot(root, delivery_scope_paths(root, state))
        before = state.get("report_turn_snapshot")
        if isinstance(before, dict) and isinstance(before.get("files"), dict):
            changed = changed_paths_since(root, before, now, delivery_scope_paths(root, state))
            state["report_turn_snapshot_missing"] = False
        else:
            # Older state files have no prompt-time snapshot. Preserve historical
            # debt and conservatively compare with the existing session baseline.
            changed = changed_scope_paths(root, state, now)
            state["report_turn_snapshot_missing"] = True
        state["report_turn_changed_paths"] = sorted(changed)
        state["report_turn_requires_verification"] = bool(changed) or (
            state.get("report_turn_snapshot_missing") is True
            and state.get("mutation_observed") is True
        )
        if state.get("mutation_observed"):
            state["verification_status"] = "REPORT_ONLY_UNVERIFIED_RETAINED"
        guard = state.get("delivery_guard")
        if isinstance(guard, dict) and isinstance(guard.get("requirements"), dict):
            closed = set(guard.get("closed_ids", []))
            remaining = sorted(set(guard["requirements"]) - closed)
            scope_state = "FROZEN"
        else:
            remaining = None
            scope_state = "UNBOUND_OR_LEGACY"
        state["delivery_exit"] = {
            "mode": mode,
            "at": time.time(),
            "closed": False,
            "remaining_ids": remaining,
            "scope_state": scope_state,
            "resume_condition": "A new direct Product Owner execution instruction; no requirement is closed by this exit.",
            "prompt_hash": state.get("turn_prompt_hash"),
        }
        return True, None
    if mode in {"PO_PAUSED", "APPROVAL_WAIT"}:
        # A direct current-turn pause/approval wait is a non-closure exit. Keep
        # the required IDs and all unverified evidence intact for resumption.
        if state.get("mutation_observed"):
            state["verification_status"] = f"{mode}_UNVERIFIED_RETAINED"
        guard = state.get("delivery_guard")
        if isinstance(guard, dict) and isinstance(guard.get("requirements"), dict):
            closed = set(guard.get("closed_ids", []))
            remaining = sorted(set(guard["requirements"]) - closed)
            scope_state = "FROZEN"
        else:
            remaining = None
            scope_state = "UNBOUND_OR_LEGACY"
        state["delivery_exit"] = {
            "mode": mode,
            "at": time.time(),
            "closed": False,
            "remaining_ids": remaining,
            "scope_state": scope_state,
            "resume_condition": "A new direct Product Owner execution instruction; no requirement is closed by this exit.",
            "prompt_hash": state.get("turn_prompt_hash"),
        }
        return True, None
    bound = state.get("continuity")
    if not isinstance(bound, dict):
        return True, None  # Legacy/unbound continuity remains compatible; prompt context warns.
    try:
        record_path = continuity_path(root, bound.get("record"))
        current_record_hash = hashlib.sha256(record_path.read_bytes()).hexdigest()
        if bound.get("pins", {}).get(bound.get("record")) != current_record_hash:
            return False, "The bound continuity record changed after readback; reconcile and rebind it before any completion claim."
        item = continuity_record(root, bound.get("record"), bound.get("section"))
        reasons = delivery_guard_reasons(state, bound, item)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        return False, f"Structured delivery could not be verified ({type(error).__name__}); preserve every remaining requirement and reconcile its current evidence."
    delivery = item.get("delivery")
    if not isinstance(delivery, dict):
        if state.get("delivery_guard"):
            return False, "A previously bound full delivery scope is missing; restore its required IDs and remaining work before stopping."
        return True, None
    if reasons:
        return False, "Structured delivery scope changed or could not be reconciled: " + ", ".join(sorted(set(reasons))) + ". Keep all frozen requirements and continue the existing outcome."
    status = delivery.get("status")
    requirements = delivery.get("requirements", [])
    unfinished = [value for value in requirements if value.get("status") != "JOB_CLOSED"]
    if status == "JOB_CLOSED" and not unfinished:
        return True, None
    if status == "EXTERNAL_BLOCKED":
        # validate_delivery already proves every unfinished item is blocked by
        # current source-pinned evidence and includes a concrete resume condition.
        if not unfinished:
            return False, "EXTERNAL_BLOCKED has no remaining blocked requirement; reconcile the outcome status."
        return True, None
    if status == "PO_DEFERRED":
        if bound.get("prompt_hash") != state.get("last_prompt_hash"):
            return False, "A new Product Owner message requires reconciling the prior deferral; historical deferral cannot stop newly authorized work."
        exit_record = delivery["exit"]
        remaining_ids = sorted(value["id"] for value in unfinished)
        state["delivery_exit"] = {
            "mode": "PO_DEFERRED",
            "at": time.time(),
            "closed": False,
            "remaining_ids": remaining_ids,
            "scope_state": "FROZEN",
            "reason": exit_record["reason"],
            "evidence_path": exit_record["evidence_path"],
            "resume_condition": exit_record["resume_condition"],
        }
        return True, None
    if status in {"REPORT_ONLY", "PO_PAUSED", "APPROVAL_WAIT"}:
        return False, f"Stored status {status} is not current Product Owner authorization to stop; continue unless the current direct instruction explicitly pauses or requests a report-only reply."
    if not unfinished:
        return False, "All items have outcome evidence but the delivery has not been recorded JOB_CLOSED; reconcile the current closure receipt."
    remaining = ", ".join(f"{value['id']}={value['status']}" for value in unfinished[:40])
    return False, f"Full user outcome remains open: {remaining}. OPEN/DEFER/IMPLEMENTED/INTEGRATED/VERIFIED are not JOB_CLOSED; continue implementation and real outcome verification."


def stop_block(state: dict, event: dict, reason: str, status: str) -> dict:
    state["verification_status"] = status
    if event.get("stop_hook_active") or state.get("stop_continuation_used"):
        return {"continue": False, "stopReason": reason,
                "systemMessage": f"LUMENIS completion guard BLOCKED ({status}) after its single bounded continuation; no tests, models, or tasks were started."}
    state["stop_continuation_used"] = True
    return {"decision": "block", "reason": reason}


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
        prompt = str(event.get("prompt", ""))
        synthetic_hook_prompt = "<hook_prompt" in prompt.lower()
        incoming_turn_id = event.get("turn_id")
        same_turn = (isinstance(incoming_turn_id, str)
                     and incoming_turn_id == state.get("turn_id"))
        if not synthetic_hook_prompt and not same_turn:
            state["last_prompt_hash"] = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            state["last_prompt_at"] = time.time()
            state["turn_exit_mode"] = classify_turn_exit(prompt)
            state["turn_prompt_hash"] = state["last_prompt_hash"]
            state["turn_id"] = incoming_turn_id
            state["stop_continuation_used"] = False
            if state["turn_exit_mode"] == "REPORT_ONLY":
                # This snapshot is a turn-local comparison point only. Keep the
                # original session baseline and historical verification debt.
                state["report_turn_snapshot"] = snapshot(root, delivery_scope_paths(root, state))
                state["report_turn_snapshot_missing"] = False
                state["report_turn_requires_verification"] = False
                state["report_turn_changed_paths"] = []
            else:
                state.pop("report_turn_snapshot", None)
                state.pop("report_turn_snapshot_missing", None)
                state.pop("report_turn_requires_verification", None)
                state.pop("report_turn_changed_paths", None)
        state["routes"] = route_prompt(prompt)
        routed = "\n".join(state["routes"])
        message = model_policy_context(event)
        if routed:
            message += "\n" + routed
        if state["turn_exit_mode"] == "RUNNING":
            message += (
                "\nContinue the full currently authorized user outcome. A clarification or added research source "
                "does not reset or reduce prior requirements. Preserve existing IDs and remaining work; append new scope only."
            )
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
        engineering_runner = bool(re.search(r"\.codex[\\/]engineering\.py\s+verification_run\b", native_command, re.IGNORECASE))
        kind = verification_kind(native_command) if tool in SHELL and not engineering_runner else None
        if kind and native_exit_code is not None:
            receipt = {"kind": kind, "exit_code": native_exit_code, "fingerprint": verification_fingerprint(root, state, now), "at": time.time()}
            state.setdefault("receipts", []).append(receipt)
            state["receipts"] = state["receipts"][-20:]
        state["last_snapshot"] = now
        return {}
    if name == "Stop":
        allowed, delivery_reason = delivery_stop_check(root, state, event)
        if not allowed:
            return stop_block(state, event, delivery_reason or "Structured delivery remains open.", "BLOCKED_DELIVERY_OUTCOME_OPEN")
        if state.get("turn_exit_mode") in {"PO_PAUSED", "APPROVAL_WAIT"}:
            return {}
        report_only = state.get("turn_exit_mode") == "REPORT_ONLY"
        if not report_only and not state.get("mutation_observed"):
            return {}
        now = snapshot(root, delivery_scope_paths(root, state) if report_only else None)
        if report_only and isinstance(state.get("report_turn_snapshot"), dict):
            scoped_changes = changed_paths_since(
                root, state["report_turn_snapshot"], now, delivery_scope_paths(root, state)
            )
            state["report_turn_snapshot_missing"] = False
        else:
            scoped_changes = changed_scope_paths(root, state, now)
            if report_only:
                state["report_turn_snapshot_missing"] = True
        if report_only:
            state["report_turn_changed_paths"] = sorted(scoped_changes)
            state["report_turn_requires_verification"] = bool(scoped_changes) or (
                state.get("report_turn_snapshot_missing") is True
                and state.get("mutation_observed") is True
            )
            if not state["report_turn_requires_verification"]:
                return {}
        if delivery_scope_paths(root, state) and not scoped_changes:
            return {}  # Another Owner's edits cannot impose this task's checks.
        code_changed = any(Path(path).suffix.lower() in CODE for path in scoped_changes)
        policy = load_verification_policy(root)
        policy_known = isinstance(policy, dict) and all(
            type(policy.get(key)) is bool for key in (
                "unit_integration_required", "create_unit_integration_allowed",
                "run_unit_integration_allowed", "renamed_module_suites_allowed"))
        if not policy_known:
            reason = "The machine verification_policy is missing or invalid; reconcile its approved values before claiming completion. Hooks never start a test suite."
            return stop_block(state, event, reason, "BLOCKED_VERIFICATION_POLICY_UNAVAILABLE")
        retained = set(policy.get("retained_checks", []))
        required_retained = {"compilation", "static_quality"} if code_changed else set()
        if ((required_retained and not required_retained.issubset(retained))
                or (not required_retained and not retained.intersection({"compilation", "static_quality"}))):
            reason = "The current machine verification_policy does not retain every applicable compilation/static-quality check; reconcile the policy before claiming completion."
            return stop_block(state, event, reason, "BLOCKED_RETAINED_CHECK_MISSING")
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
        if good:
            state["stop_continuation_used"] = False
            return {}
        reason = "Current-snapshot compilation/static quality and applicable authorized regression evidence are missing or failed. A diff check alone cannot verify code. Hooks never start suites. Security, source rights, data consistency, recovery and real user E2E remain separate acceptance requirements."
        return stop_block(state, event, reason, "BLOCKED_MISSING_SUCCESSFUL_CHECK")
    return {}

def main() -> int:
    try:
        raw = sys.stdin.buffer.read(1000001)
        if len(raw) > 1000000: raise ValueError("Hook input too large")
        event = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(event, dict): raise TypeError("Hook input is not an object")
        root = find_root(event.get("cwd"))
        if root is None: emit({}); return 0
        path = state_file(event, root)
        with locked(path):
            state = json.loads(path.read_text("utf-8")) if path.exists() else {}
            output = handle(event, root, state)
            save(path, state)
        emit(output); return 0
    # Deliberate outer fail-closed boundary: hook failures must report unavailable.
    except Exception as error:  # noqa: BLE001
        emit({"systemMessage": "LUMENIS hook error: " + type(error).__name__ + ". Verification is unavailable, not PASS."})
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
