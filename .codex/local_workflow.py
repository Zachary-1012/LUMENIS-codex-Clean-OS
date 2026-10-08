"""Guarded local engineering workflow helpers (stdlib only).

This is development tooling, not product truth. It never runs module tests,
models, providers, application runtimes, or arbitrary shell commands. Optional
local tool paths are read from the ignored
``work/m-governance-20261008/devtools/tools.local.json`` file. Example schema::

    {"version": 1, "tools": {"python": "C:/Python314/python.exe",
      "ruff": "C:/.../ruff.exe", "dart": "D:/.../dart.exe",
      "pwsh": "C:/.../pwsh.exe", "node": "C:/.../node.exe",
      "npm": "C:/.../npm-cli.js"},
     "flutter_tools_snapshot": "D:/.../flutter_tools.snapshot"}

Every executable setting is one absolute file path; arrays, flags and command
strings are rejected. Website and Flutter builds use fixed commands below.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import tomllib

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT = ROOT / "work/m-governance-20261008/devtools"
RESERVATION_REL = (
    "work/w6-integration-20261002/dispatch-20261008/SHARED-RESERVATIONS.json"
)
RESERVATION_KEY = "M_local_development_automation"
LOCALE_GENERATOR = "app/tool/generate_lumenis_copy.dart"
LOCALE_GENERATOR_SHA256 = (
    "732c88f5ca631102f0711e01687a89fa2c3301e958285027e448c19b4543a78c"
)
LOCALE_INPUTS = (
    "contracts/experience/i18n/zh-CN.delta.json",
    "contracts/experience/i18n/en.delta.json",
    "contracts/experience/i18n/ko.delta.json",
)
LOCALE_TARGET = "app/lib/l10n/lumenis_copy.g.dart"
MAX_FILES = 100
MAX_SOURCE_BYTES = 20 * 1024 * 1024
TOOL_KEYS = {"python", "ruff", "dart", "pwsh", "node", "npm"}
FORMATTABLE = {".py", ".dart"}
STATIC_SUFFIXES = {
    ".py",
    ".dart",
    ".ps1",
    ".json",
    ".toml",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".astro",
}
BLOCKED_PARTS = {
    ".git",
    "work",
    "data",
    "node_modules",
    "vendor",
    ".venv",
    "venv",
    "tests",
    "test",
    "__tests__",
    ".dart_tool",
    "build",
    "dist",
}
BLOCKED_BASENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "credentials",
    "credentials.json",
    "secrets",
    "secrets.json",
    "cookies.json",
    "session.json",
    "auth.json",
    "token.json",
    "tokens.json",
    "private_key",
    "private-key",
    "monitor.db",
}
SECRET_PATTERNS = (
    re.compile(r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{15,})\b"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(
        r"(?i)(\b(?:api[_-]?key|password|secret|token|cookie)\b\s*[:=]\s*)[^\s,;]+"
    ),
)
NODE_STATIC_CHECK = r"""
const fs=require('node:fs');
const path=require('node:path');
let bad=false;
function loc(file,pos){const lc=file.getLineAndCharacterOfPosition(pos||0);return {line:lc.line+1,column:lc.character+1};}
(async()=>{
  for(const file of process.argv.slice(1)){
    const ext=path.extname(file).toLowerCase();
    const source=fs.readFileSync(file,'utf8');
    if(ext==='.ts'||ext==='.tsx'){
      const ts=require('typescript');
      const kind=ext==='.tsx'?ts.ScriptKind.TSX:ts.ScriptKind.TS;
      const unit=ts.createSourceFile(file,source,ts.ScriptTarget.Latest,true,kind);
      if(unit.parseDiagnostics.length){bad=true; for(const d of unit.parseDiagnostics) console.error(JSON.stringify({path:path.basename(file),...loc(unit,d.start),code:d.code||null,message:ts.flattenDiagnosticMessageText(d.messageText,' ')}));}
    } else if(ext==='.astro'){
      const compiler=require('@astrojs/compiler');
      const result=await compiler.parse(source,{position:true});
      if(result.diagnostics&&result.diagnostics.length){bad=true; for(const d of result.diagnostics){const start=d.location&&d.location.start||{};console.error(JSON.stringify({path:path.basename(file),line:start.line||null,column:start.column||null,code:d.code||null,message:String(d.text||d.message||'Parse diagnostic')}));}}
    }
  }
  process.exitCode=bad?1:0;
})().catch(()=>{console.error('Existing TypeScript/Astro parser unavailable or failed');process.exitCode=2;});
"""
POWERSHELL_STATIC_CHECK = r"""
$ErrorActionPreference = 'Stop'
if (-not (Get-Module -ListAvailable -Name PSScriptAnalyzer)) {
  [Console]::Error.WriteLine('PSScriptAnalyzer unavailable')
  exit 2
}
Import-Module PSScriptAnalyzer -ErrorAction Stop
$failed = $false
foreach ($p in $args) {
  $tokens = $null; $parseErrors = $null
  [System.Management.Automation.Language.Parser]::ParseFile($p, [ref]$tokens, [ref]$parseErrors) | Out-Null
  if ($parseErrors.Count -gt 0) {
    $failed = $true
    foreach ($e in $parseErrors) {
      $item = [ordered]@{path=[System.IO.Path]::GetFileName($p);line=$e.Extent.StartLineNumber;column=$e.Extent.StartColumnNumber;rule=$e.ErrorId;message=$e.Message}
      [Console]::Error.WriteLine(($item | ConvertTo-Json -Compress))
    }
  }
  $findings = @(Invoke-ScriptAnalyzer -Path $p -Severity Error,Warning)
  if ($findings.Count -gt 0) {
    $failed = $true
    foreach ($f in $findings) {
      $item = [ordered]@{path=[System.IO.Path]::GetFileName($p);line=$f.Line;column=$f.Column;rule=$f.RuleName;message=$f.Message}
      [Console]::Error.WriteLine(($item | ConvertTo-Json -Compress))
    }
  }
}
if ($failed) { exit 1 }
exit 0
"""


class WorkflowError(Exception):
    def __init__(self, message: str, exit_code: int = 2):
        super().__init__(message)
        self.exit_code = exit_code


def now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_error(value: Any, limit: int = 1200) -> str:
    text = str(value or "")
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(
            lambda match: (match.group(1) if match.lastindex else "") + "[REDACTED]",
            text,
        )
    text = "".join(ch if ch in "\r\n\t" or ord(ch) >= 32 else " " for ch in text)
    return text[:limit]


def fixed_git(*args: str, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    command = ["git", "-C", str(ROOT), *args]
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkflowError("Read-only Git command unavailable or timed out") from exc


def git_output(*args: str, preserve_whitespace: bool = False) -> str:
    result = fixed_git(*args)
    if result.returncode != 0:
        raise WorkflowError("Read-only Git query failed")
    return (
        result.stdout.rstrip("\r\n") if preserve_whitespace else result.stdout.strip()
    )


def current_head() -> str:
    return git_output("rev-parse", "HEAD")


def is_ignored(relative: str) -> bool:
    result = fixed_git("check-ignore", "-q", "--", relative)
    return result.returncode == 0


def is_symlink_or_junction(path: Path) -> bool:
    junction_check = getattr(path, "is_junction", None)
    return path.is_symlink() or (callable(junction_check) and junction_check())


def has_symlink_component(path: Path) -> bool:
    try:
        relative = path.absolute().relative_to(ROOT.absolute())
    except ValueError:
        return True
    cursor = ROOT
    for part in relative.parts:
        cursor = cursor / part
        if is_symlink_or_junction(cursor):
            return True
    return False


def ensure_work_directory(path: Path, *, create: bool = True) -> Path:
    """Create/check one private ignored path, rejecting every linked component."""
    work_root = ROOT / "work"
    candidate = path.absolute()
    try:
        relative = candidate.relative_to(work_root.absolute())
    except ValueError as exc:
        raise WorkflowError(
            "Derived receipts, backups and caches must stay under repository work"
        ) from exc
    cursor = work_root
    if is_symlink_or_junction(cursor):
        raise WorkflowError("Repository work root may not be a symlink or junction")
    for part in relative.parts:
        if part in {"", ".", ".."}:
            raise WorkflowError("Invalid derived work path")
        cursor = cursor / part
        if is_symlink_or_junction(cursor):
            raise WorkflowError(
                "Derived work path may not contain symlinks or junctions"
            )
        if not cursor.exists():
            if not create:
                raise WorkflowError("Expected private work directory is unavailable")
            cursor.mkdir()
        if not cursor.is_dir():
            raise WorkflowError("Derived work path component is not a directory")
        resolved = cursor.resolve(strict=True)
        try:
            resolved.relative_to(work_root.resolve(strict=True))
        except ValueError as exc:
            raise WorkflowError(
                "Derived work directory resolves outside protected work"
            ) from exc
        if is_symlink_or_junction(cursor):
            raise WorkflowError("Derived work path changed to a symlink or junction")
        rel_to_root = resolved.relative_to(ROOT.resolve()).as_posix()
        if not is_ignored(rel_to_root):
            raise WorkflowError("Derived work directory must remain Git-ignored")
    return cursor.resolve(strict=True)


def ensure_private_subdir(receipt_dir: Path, *parts: str, create: bool = True) -> Path:
    if any(
        not part
        or Path(part).is_absolute()
        or part in {".", ".."}
        or len(Path(part).parts) != 1
        for part in parts
    ):
        raise WorkflowError(
            "Private work subdirectory requires exact single path components"
        )
    return ensure_work_directory(receipt_dir.joinpath(*parts), create=create)


def normalize_repo_path(
    raw: str, *, must_exist: bool = True, allowed_suffixes: set[str] | None = None
) -> tuple[str, Path]:
    if not isinstance(raw, str) or not raw or "\x00" in raw or len(raw) > 500:
        raise WorkflowError("Invalid repository-relative path")
    candidate = Path(raw)
    if (
        candidate.is_absolute()
        or candidate.drive
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise WorkflowError("Only exact repository-relative file paths are accepted")
    path = ROOT / candidate
    if has_symlink_component(path):
        raise WorkflowError("Symlink paths are not accepted")
    try:
        resolved = path.resolve(strict=must_exist)
        relative = resolved.relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError) as exc:
        raise WorkflowError("Path is missing or outside the repository") from exc
    parts = {part.lower() for part in Path(relative).parts}
    if parts & BLOCKED_PARTS or any(
        part.lower() in BLOCKED_BASENAMES or part.lower().startswith(".env.")
        for part in Path(relative).parts
    ):
        raise WorkflowError(
            "Protected, generated, test, or private path is not supported"
        )
    if allowed_suffixes is not None and path.suffix.lower() not in allowed_suffixes:
        raise WorkflowError("File type is outside this command's supported scope")
    if must_exist and (
        not resolved.is_file() or resolved.stat().st_size > MAX_SOURCE_BYTES
    ):
        raise WorkflowError("Expected a bounded regular file")
    if not must_exist and resolved.exists() and not resolved.is_dir():
        raise WorkflowError("Expected a directory path")
    return relative, resolved


def explicit_paths(
    raw_paths: list[str] | None, *, required: bool, suffixes: set[str] | None = None
) -> list[tuple[str, Path]]:
    if not raw_paths:
        if required:
            raise WorkflowError("This action requires exact --paths")
        return []
    if len(raw_paths) > MAX_FILES:
        raise WorkflowError(f"At most {MAX_FILES} exact paths are accepted")
    paths = [normalize_repo_path(raw, allowed_suffixes=suffixes) for raw in raw_paths]
    names = [name for name, _ in paths]
    if sum(len(name.encode("utf-8")) + 4 for name in names) > 10_000:
        raise WorkflowError(
            "Exact path set exceeds the bounded native-tool argument budget"
        )
    if len(set(names)) != len(names):
        raise WorkflowError("Duplicate paths are not accepted")
    return paths


def safe_receipt_dir(raw: str | None) -> Path:
    candidate = Path(raw) if raw else DEFAULT_RECEIPT
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    if has_symlink_component(candidate):
        raise WorkflowError("Receipt directory may not use symlinks")
    resolved = candidate.resolve(strict=False)
    try:
        relative = resolved.relative_to((ROOT / "work").resolve()).as_posix()
    except ValueError as exc:
        raise WorkflowError(
            "Receipt directory must stay under the protected repository work directory"
        ) from exc
    if not relative or any(
        part.lower() in {"vendor", "node_modules", ".git"}
        for part in Path(relative).parts
    ):
        raise WorkflowError(
            "Receipt directory is outside the approved private work path"
        )
    if not is_ignored(resolved.relative_to(ROOT.resolve()).as_posix()):
        raise WorkflowError("Receipt directory must be Git-ignored")
    return resolved


@contextmanager
def controlled_write_lock(receipt_dir: Path):
    """Coordinate only this helper's apply/rollback writers across processes."""
    lock_dir = ensure_private_subdir(receipt_dir, "locks")
    lock_path = lock_dir / "format-write.lock"
    if has_symlink_component(lock_path):
        raise WorkflowError("Controlled write lock may not be a symlink or junction")
    acquired = False
    deadline = time.monotonic() + 30
    stream = lock_path.open("a+b")
    try:
        if lock_path.stat().st_size == 0:
            stream.write(b"\0")
            stream.flush()
            os.fsync(stream.fileno())
        while time.monotonic() < deadline:
            stream.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except (OSError, BlockingIOError):
                time.sleep(0.1)
        if not acquired:
            raise WorkflowError(
                "Timed out waiting for another local helper write operation"
            )
        if (
            has_symlink_component(lock_path)
            or ensure_private_subdir(receipt_dir, "locks", create=False) != lock_dir
        ):
            raise WorkflowError("Controlled write lock path changed during acquisition")
        yield
    finally:
        if acquired:
            try:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        stream.close()


def durable_private_write(path: Path, data: bytes) -> None:
    ensure_work_directory(path.parent)
    if has_symlink_component(path) or path.exists():
        raise WorkflowError("Private backup path is linked or already exists")
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def load_tools_config(receipt_dir: Path) -> dict[str, Any]:
    config_path = receipt_dir / "tools.local.json"
    if has_symlink_component(config_path):
        raise WorkflowError("Local tool configuration may not use symlinks")
    if not config_path.exists():
        return {"tools": {}}
    relative = config_path.resolve().relative_to(ROOT.resolve()).as_posix()
    if not is_ignored(relative):
        raise WorkflowError("tools.local.json must be Git-ignored")
    if not config_path.is_file() or config_path.stat().st_size > 64 * 1024:
        raise WorkflowError("Local tool configuration is not a bounded file")
    try:
        config = json.loads(config_path.read_text("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WorkflowError(
            "Local tool configuration is unreadable or invalid JSON"
        ) from exc
    if (
        not isinstance(config, dict)
        or config.get("version") not in {None, 1}
        or set(config) - {"version", "tools", "flutter_tools_snapshot"}
    ):
        raise WorkflowError("Unsupported local tool configuration")
    tools = config.get("tools", {})
    if not isinstance(tools, dict) or set(tools) - TOOL_KEYS - {"build"}:
        raise WorkflowError("Local tool configuration contains a non-allowlisted entry")
    for name, value in tools.items():
        if name == "build":
            if value not in {"website:astro", "flutter:web"}:
                raise WorkflowError("Build selector must use a fixed supported value")
            continue
        if (
            not isinstance(value, str)
            or not Path(value).is_absolute()
            or "\x00" in value
        ):
            raise WorkflowError("Tool entries must be single absolute executable paths")
    snapshot = config.get("flutter_tools_snapshot")
    if snapshot is not None:
        p = Path(snapshot)
        if (
            not isinstance(snapshot, str)
            or not p.is_absolute()
            or p.name.lower() != "flutter_tools.snapshot"
        ):
            raise WorkflowError(
                "Flutter tool snapshot must be one absolute flutter_tools.snapshot path"
            )
    return config


def executable(
    name: str, config: dict[str, Any], *, optional: bool = False
) -> Path | None:
    configured = config.get("tools", {}).get(name)
    if configured:
        path = Path(configured)
        if not path.is_file():
            if optional:
                return None
            raise WorkflowError(f"Configured {name} tool is unavailable")
        return path.resolve()
    if name == "python":
        return Path(sys.executable).resolve()
    found = shutil.which(name)
    if found:
        return Path(found).resolve()
    if optional:
        return None
    raise WorkflowError(f"Required {name} tool is unavailable")


def npm_cli_path(config: dict[str, Any]) -> Path:
    configured = config.get("tools", {}).get("npm")
    candidates: list[Path] = []
    if configured:
        npm_path = Path(configured).resolve()
        if npm_path.suffix.lower() == ".js" and npm_path.name.lower() == "npm-cli.js":
            candidates.append(npm_path)
        elif npm_path.suffix.lower() in {".cmd", ".bat", ".exe"}:
            candidates.extend(
                (
                    npm_path.parent / "node_modules/npm/bin/npm-cli.js",
                    npm_path.parent.parent / "node_modules/npm/bin/npm-cli.js",
                )
            )
        else:
            raise WorkflowError(
                "npm must resolve to npm-cli.js or a standard npm launcher"
            )
    else:
        found = shutil.which("npm")
        if found:
            npm_path = Path(found).resolve()
            candidates.extend(
                (
                    npm_path.parent / "node_modules/npm/bin/npm-cli.js",
                    npm_path.parent.parent / "node_modules/npm/bin/npm-cli.js",
                )
            )
    for path in candidates:
        if path.is_file() and path.name.lower() == "npm-cli.js":
            resolved = path.resolve()
            parts = [part.lower() for part in resolved.parts]
            for index in range(max(0, len(parts) - 3)):
                if parts[index : index + 4] == [
                    "node_modules",
                    "npm",
                    "bin",
                    "npm-cli.js",
                ]:
                    return resolved
    raise WorkflowError(
        "Allowlisted npm CLI JavaScript entry was not found; no shell shim will be invoked"
    )


def flutter_tools_snapshot(dart: Path, config: dict[str, Any]) -> Path:
    configured = config.get("flutter_tools_snapshot")
    if not configured:
        raise WorkflowError(
            "Flutter build requires configured flutter_tools.snapshot; no SDK install/pub get is allowed"
        )
    dart = dart.resolve()
    flutter_root = None
    for parent in dart.parents:
        if (
            parent.name.lower() == "dart-sdk"
            and parent.parent.name.lower() == "cache"
            and parent.parent.parent.name.lower() == "bin"
        ):
            flutter_root = parent.parent.parent.parent
            break
    if flutter_root is None:
        raise WorkflowError(
            "Configured Dart executable is not under a verifiable Flutter SDK"
        )
    expected = (flutter_root / "bin/cache/flutter_tools.snapshot").resolve()
    actual = Path(configured).resolve()
    if actual != expected or not actual.is_file() or is_symlink_or_junction(actual):
        raise WorkflowError(
            "Flutter build snapshot must be the exact configured Dart SDK's flutter_tools.snapshot"
        )
    return actual


def run_process(argv: list[str], *, cwd: Path, timeout: int) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
            check=False,
        )
        return {
            "exit_code": result.returncode,
            "duration_seconds": round(time.monotonic() - started, 3),
            "stdout": safe_error(result.stdout, 2400),
            "stderr": safe_error(result.stderr, 2400),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "exit_code": 124,
            "duration_seconds": round(time.monotonic() - started, 3),
            "stdout": safe_error(exc.stdout or "", 1200),
            "stderr": safe_error(exc.stderr or "", 1200),
            "timed_out": True,
        }
    except OSError as exc:
        return {
            "exit_code": 127,
            "duration_seconds": round(time.monotonic() - started, 3),
            "stdout": "",
            "stderr": safe_error(type(exc).__name__ + ": executable unavailable", 400),
            "timed_out": False,
        }


def file_hashes(paths: list[tuple[str, Path]]) -> dict[str, str]:
    return {relative: sha256_file(path) for relative, path in paths}


def run_static_check(
    paths: list[tuple[str, Path]], config: dict[str, Any]
) -> tuple[list[dict[str, Any]], int]:
    results: list[dict[str, Any]] = []
    failed = False
    groups: dict[str, list[tuple[str, Path]]] = {}
    for relative, path in paths:
        ext = path.suffix.lower()
        try:
            data = path.read_bytes()
            text = data.decode("utf-8-sig")
        except (OSError, UnicodeError):
            results.append({"check": "source_read", "status": "FAIL", "path": relative})
            failed = True
            continue
        try:
            if ext == ".py":
                ast.parse(text, filename=relative)
                results.append(
                    {"check": "python_ast", "status": "PASS", "path": relative}
                )
                groups.setdefault("ruff", []).append((relative, path))
            elif ext == ".json":
                json.loads(text)
                results.append(
                    {"check": "json_parse", "status": "PASS", "path": relative}
                )
            elif ext == ".toml":
                tomllib.loads(text)
                results.append(
                    {"check": "toml_parse", "status": "PASS", "path": relative}
                )
            elif ext == ".dart":
                groups.setdefault("dart", []).append((relative, path))
            elif ext == ".ps1":
                groups.setdefault("powershell", []).append((relative, path))
            elif ext in {".js", ".mjs", ".cjs"}:
                groups.setdefault("node_js", []).append((relative, path))
            elif ext in {".ts", ".tsx", ".astro"}:
                if not relative.startswith("website/"):
                    results.append(
                        {
                            "check": "web_static_parse",
                            "status": "FAIL",
                            "path": relative,
                            "detail": "TypeScript/Astro parser is scoped to the existing Website toolchain",
                        }
                    )
                    failed = True
                else:
                    groups.setdefault("web_static_parse", []).append((relative, path))
        except (SyntaxError, ValueError, tomllib.TOMLDecodeError) as exc:
            results.append(
                {
                    "check": f"{ext[1:]}_parse",
                    "status": "FAIL",
                    "path": relative,
                    "detail": safe_error(type(exc).__name__ + ": parse error", 250),
                }
            )
            failed = True

    if groups.get("ruff"):
        try:
            ruff = executable("ruff", config)
            result = run_process(
                [
                    str(ruff),
                    "check",
                    "--no-cache",
                    *[str(p) for _, p in groups["ruff"]],
                ],
                cwd=ROOT,
                timeout=180,
            )
            results.append(
                {
                    "check": "ruff",
                    "status": "PASS" if result["exit_code"] == 0 else "FAIL",
                    "paths": [p for p, _ in groups["ruff"]],
                    **result,
                }
            )
            failed |= result["exit_code"] != 0
        except WorkflowError as exc:
            results.append(
                {
                    "check": "ruff",
                    "status": "UNAVAILABLE",
                    "paths": [p for p, _ in groups["ruff"]],
                    "detail": str(exc),
                }
            )
            failed = True

    if groups.get("dart"):
        try:
            dart = executable("dart", config)
            for relative, path in groups["dart"]:
                analyze = run_process(
                    [str(dart), "analyze", str(path)], cwd=ROOT, timeout=300
                )
                results.append(
                    {
                        "check": "dart_analyze",
                        "status": "PASS" if analyze["exit_code"] == 0 else "FAIL",
                        "path": relative,
                        **analyze,
                    }
                )
                format_result = run_process(
                    [
                        str(dart),
                        "format",
                        "--output=none",
                        "--set-exit-if-changed",
                        str(path),
                    ],
                    cwd=ROOT,
                    timeout=300,
                )
                results.append(
                    {
                        "check": "dart_format_check",
                        "status": "PASS" if format_result["exit_code"] == 0 else "FAIL",
                        "path": relative,
                        **format_result,
                    }
                )
                failed |= analyze["exit_code"] != 0 or format_result["exit_code"] != 0
        except WorkflowError as exc:
            results.append(
                {
                    "check": "dart",
                    "status": "UNAVAILABLE",
                    "paths": [p for p, _ in groups["dart"]],
                    "detail": str(exc),
                }
            )
            failed = True

    if groups.get("powershell"):
        try:
            pwsh = executable("pwsh", config)
            selected = [str(p) for _, p in groups["powershell"]]
            result = run_process(
                [
                    str(pwsh),
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-CommandWithArgs",
                    POWERSHELL_STATIC_CHECK,
                    *selected,
                ],
                cwd=ROOT,
                timeout=180,
            )
            results.append(
                {
                    "check": "powershell_parser_and_script_analyzer",
                    "status": "PASS" if result["exit_code"] == 0 else "FAIL",
                    "paths": [p for p, _ in groups["powershell"]],
                    **result,
                }
            )
            failed |= result["exit_code"] != 0
        except WorkflowError as exc:
            results.append(
                {
                    "check": "powershell_parser_and_script_analyzer",
                    "status": "UNAVAILABLE",
                    "paths": [p for p, _ in groups["powershell"]],
                    "detail": str(exc),
                }
            )
            failed = True

    if groups.get("node_js"):
        try:
            node = executable("node", config)
            for relative, path in groups["node_js"]:
                result = run_process(
                    [str(node), "--check", str(path)], cwd=ROOT, timeout=120
                )
                results.append(
                    {
                        "check": "node_syntax",
                        "status": "PASS" if result["exit_code"] == 0 else "FAIL",
                        "paths": [relative],
                        **result,
                    }
                )
                failed |= result["exit_code"] != 0
        except WorkflowError as exc:
            results.append(
                {
                    "check": "node_syntax",
                    "status": "UNAVAILABLE",
                    "paths": [p for p, _ in groups["node_js"]],
                    "detail": str(exc),
                }
            )
            failed = True

    if groups.get("web_static_parse"):
        try:
            node = executable("node", config)
            result = run_process(
                [
                    str(node),
                    "-e",
                    NODE_STATIC_CHECK,
                    *[str(p) for _, p in groups["web_static_parse"]],
                ],
                cwd=ROOT / "website",
                timeout=180,
            )
            results.append(
                {
                    "check": "existing_typescript_astro_syntax_parsers",
                    "status": "PASS" if result["exit_code"] == 0 else "FAIL",
                    "paths": [p for p, _ in groups["web_static_parse"]],
                    **result,
                    "scope_note": "syntax parse only; not typecheck or product acceptance",
                }
            )
            failed |= result["exit_code"] != 0
        except WorkflowError as exc:
            results.append(
                {
                    "check": "existing_typescript_astro_syntax_parsers",
                    "status": "UNAVAILABLE",
                    "paths": [p for p, _ in groups["web_static_parse"]],
                    "detail": str(exc),
                }
            )
            failed = True

    results.extend(run_git_diff_checks(paths))
    if any(
        item.get("status") == "FAIL"
        for item in results
        if item.get("check", "").startswith("git_diff")
    ):
        failed = True
    return results, 1 if failed else 0


def run_git_diff_checks(paths: list[tuple[str, Path]]) -> list[dict[str, Any]]:
    if not paths:
        return []
    names = [relative for relative, _ in paths]
    result: list[dict[str, Any]] = []
    for args, label in (
        (["diff", "--check", "--", *names], "git_diff_check"),
        (["diff", "--cached", "--check", "--", *names], "git_diff_cached_check"),
    ):
        proc = fixed_git(*args)
        result.append(
            {
                "check": label,
                "status": "PASS" if proc.returncode == 0 else "FAIL",
                "paths": names,
                "exit_code": proc.returncode,
                "detail": safe_error(proc.stdout + proc.stderr, 1200),
            }
        )
    untracked = []
    for relative, _ in paths:
        listed = fixed_git("ls-files", "--error-unmatch", "--", relative)
        if listed.returncode != 0:
            untracked.append((relative, ROOT / relative))
    if untracked:
        findings = []
        with tempfile.TemporaryDirectory(prefix="lumenis-diff-check-") as temp_dir:
            empty = Path(temp_dir) / "empty"
            empty.write_bytes(b"")
            for relative, path in untracked:
                proc = fixed_git(
                    "diff", "--no-index", "--check", "--", str(empty), str(path)
                )
                diagnostic = proc.stdout + proc.stderr
                whitespace = bool(
                    re.search(
                        r"(?i)(trailing whitespace|new blank line at eof|space before tab in indent)",
                        diagnostic,
                    )
                )
                unexpected = proc.returncode not in {0, 1}
                if whitespace or unexpected:
                    findings.append(
                        {
                            "path": relative,
                            "detail": safe_error(
                                diagnostic or "Git no-index diff check failed", 500
                            ),
                            "exit_code": proc.returncode,
                        }
                    )
        result.append(
            {
                "check": "git_diff_untracked_whitespace",
                "status": "FAIL" if findings else "PASS",
                "paths": [p for p, _ in untracked],
                "findings": findings,
            }
        )
    return result


def read_only_diff(paths: list[tuple[str, Path]]) -> tuple[dict[str, Any], int]:
    names = [relative for relative, _ in paths]
    before = file_hashes(paths)
    proc = fixed_git("diff", "--no-ext-diff", "--no-color", "HEAD", "--", *names)
    if proc.returncode != 0:
        raise WorkflowError("Selected-path Git diff against HEAD failed")
    untracked_diffs: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="lumenis-readonly-diff-") as temp_dir:
        empty = Path(temp_dir) / "empty"
        empty.write_bytes(b"")
        for relative, path in paths:
            tracked = fixed_git("ls-files", "--error-unmatch", "--", relative)
            if tracked.returncode == 0:
                continue
            untracked = fixed_git(
                "diff",
                "--no-index",
                "--no-ext-diff",
                "--no-color",
                "--",
                str(empty),
                str(path),
            )
            if untracked.returncode not in {0, 1}:
                raise WorkflowError("Selected untracked-file diff failed")
            untracked_diffs.append(
                {
                    "path": relative,
                    "diff": safe_error(untracked.stdout + untracked.stderr, 16000),
                }
            )
    unchanged = file_hashes(paths) == before
    return {
        "base": "HEAD",
        "head": current_head(),
        "paths": names,
        "path_sha256": before,
        "tracked_diff": safe_error(proc.stdout, 40000),
        "untracked_diffs": untracked_diffs,
        "source_unchanged": unchanged,
    }, 0 if unchanged else 1


def find_ruff_config(source: Path) -> Path | None:
    for parent in (source.parent, *source.parent.parents):
        if not parent.is_relative_to(ROOT):
            break
        for name in ("ruff.toml", ".ruff.toml", "pyproject.toml"):
            candidate = parent / name
            if candidate.is_file():
                return candidate
    return None


def format_one(
    relative: str,
    source: Path,
    config: dict[str, Any],
    *,
    config_anchor: Path | None = None,
) -> bytes:
    suffix = source.suffix.lower()
    if suffix not in FORMATTABLE:
        raise WorkflowError(
            "Only Python and Dart have approved preview/apply formatter paths"
        )
    with tempfile.TemporaryDirectory(prefix="lumenis-format-preview-") as temp_dir:
        temp_path = Path(temp_dir) / source.name
        original = source.read_bytes()
        temp_path.write_bytes(original)
        if suffix == ".py":
            ruff = executable("ruff", config)
            ruff_args = [str(ruff), "format"]
            ruff_config = find_ruff_config(config_anchor or source)
            ruff_args.extend(
                ["--config", str(ruff_config)] if ruff_config else ["--isolated"]
            )
            ruff_args.append(str(temp_path))
            result = run_process(ruff_args, cwd=ROOT, timeout=180)
        else:
            dart = executable("dart", config)
            result = run_process(
                [str(dart), "format", str(temp_path)], cwd=ROOT, timeout=180
            )
        if result["exit_code"] != 0:
            raise WorkflowError(
                f"Formatter failed for {relative}: {safe_error(result.get('stderr') or result.get('stdout'), 300)}",
                1,
            )
        return temp_path.read_bytes()


def format_preview(
    paths: list[tuple[str, Path]], config: dict[str, Any]
) -> tuple[dict[str, Any], int]:
    diffs: list[dict[str, Any]] = []
    before = file_hashes(paths)
    for relative, path in paths:
        output = format_one(relative, path, config)
        original = path.read_bytes()
        try:
            old_text = original.decode("utf-8-sig").splitlines(keepends=True)
            new_text = output.decode("utf-8-sig").splitlines(keepends=True)
        except UnicodeError as exc:
            raise WorkflowError(
                f"Formatter returned non-UTF-8 output for {relative}"
            ) from exc
        diff = "".join(
            difflib.unified_diff(
                old_text,
                new_text,
                fromfile=relative + " (current)",
                tofile=relative + " (formatted)",
            )
        )
        diffs.append(
            {
                "path": relative,
                "before_sha256": before[relative],
                "formatted_sha256": sha256_bytes(output),
                "changed": output != original,
                "diff": safe_error(diff, 24000),
            }
        )
        if sha256_file(path) != before[relative]:
            raise WorkflowError("Original source changed during format preview")
    return {"files": diffs, "source_unchanged": file_hashes(paths) == before}, 0


def load_actual_reservation() -> tuple[dict[str, Any], str]:
    path = ROOT / RESERVATION_REL
    if has_symlink_component(path) or not path.is_file():
        raise WorkflowError("Current shared reservation is unavailable")
    raw = path.read_bytes()
    try:
        document = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise WorkflowError("Current shared reservation is invalid JSON") from exc
    record = document.get(RESERVATION_KEY) if isinstance(document, dict) else None
    if not isinstance(record, dict):
        raise WorkflowError("Exact M development-tools reservation is absent")
    return {
        "document": document,
        "record": record,
        "raw": raw,
        "path": path,
    }, sha256_bytes(raw)


def verify_apply_grant(
    manifest_path: Path, paths: list[tuple[str, Path]], owner: str
) -> dict[str, Any]:
    if has_symlink_component(manifest_path) or not manifest_path.is_file():
        raise WorkflowError("Authorization manifest must be a regular non-symlink file")
    try:
        manifest_rel = (
            manifest_path.resolve().relative_to(DEFAULT_RECEIPT.resolve()).as_posix()
        )
    except ValueError as exc:
        raise WorkflowError(
            "Authorization manifest must be stored under the protected default receipt directory"
        ) from exc
    if not is_ignored(
        (ROOT / "work/m-governance-20261008/devtools" / manifest_rel)
        .relative_to(ROOT)
        .as_posix()
    ):
        raise WorkflowError("Authorization manifest must be Git-ignored")
    if manifest_path.stat().st_size > 64 * 1024:
        raise WorkflowError("Authorization manifest is oversized")
    try:
        grant = json.loads(manifest_path.read_text("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WorkflowError(
            "Authorization manifest is unreadable or invalid JSON"
        ) from exc
    if not isinstance(grant, dict):
        raise WorkflowError("Authorization manifest must be a JSON object")
    head = current_head()
    if grant.get("head") != head or grant.get("owner") != owner:
        raise WorkflowError(
            "Authorization manifest HEAD or owner does not match current execution"
        )
    if (
        grant.get("reservation_path", RESERVATION_REL).replace("\\", "/")
        != RESERVATION_REL
    ):
        raise WorkflowError(
            "Authorization manifest references a noncanonical reservation"
        )
    reservation, reservation_sha = load_actual_reservation()
    record = reservation["record"]
    if grant.get("reservation_sha256") != reservation_sha:
        raise WorkflowError(
            "Authorization manifest does not pin the current reservation bytes"
        )
    if (
        record.get("owner") != owner
        or record.get("state") != "RESERVED"
        or record.get("head") != head
    ):
        raise WorkflowError(
            "Current reservation owner/state/HEAD does not authorize writes"
        )
    allowed = record.get("allowed_paths")
    if not isinstance(allowed, list) or any(
        not isinstance(item, str) for item in allowed
    ):
        raise WorkflowError("Current reservation lacks exact allowed paths")
    manifest_paths = grant.get("paths", grant.get("allowed_paths"))
    if not isinstance(manifest_paths, list):
        raise WorkflowError(
            "Authorization manifest requires exact path/preimage entries"
        )
    expected_names = [name for name, _ in paths]
    if len(manifest_paths) != len(expected_names):
        raise WorkflowError("Manifest path set must exactly match --paths")
    entries: dict[str, str] = {}
    for entry in manifest_paths:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise WorkflowError("Manifest path entry is malformed")
        relative, _ = normalize_repo_path(
            entry["path"], allowed_suffixes=STATIC_SUFFIXES
        )
        preimage = entry.get("preimage_sha256", entry.get("sha256"))
        if not isinstance(preimage, str) or not re.fullmatch(r"[0-9a-f]{64}", preimage):
            raise WorkflowError("Manifest path entry requires a SHA-256 preimage")
        entries[relative] = preimage
    if set(entries) != set(expected_names) or len(entries) != len(expected_names):
        raise WorkflowError(
            "Manifest paths must exactly match --paths with no duplicates"
        )
    for relative, path in paths:
        if relative not in allowed:
            raise WorkflowError(
                "Exact source path is not listed in the current M reservation"
            )
        if sha256_file(path) != entries[relative]:
            raise WorkflowError("Source preimage does not match the authorized SHA-256")
    return {
        "head": head,
        "owner": owner,
        "reservation_sha256": reservation_sha,
        "reservation_revision": reservation["document"].get("revision"),
        "paths": entries,
        "manifest_path": manifest_path,
        "manifest_sha256": sha256_file(manifest_path),
    }


def recheck_apply_grant(grant: dict[str, Any], relative: str, path: Path) -> None:
    if has_symlink_component(path):
        raise WorkflowError("Source path became a symlink during authorized write")
    if current_head() != grant["head"]:
        raise WorkflowError("HEAD changed during authorized write; stop and re-admit")
    reservation, reservation_sha = load_actual_reservation()
    record = reservation["record"]
    if (
        reservation_sha != grant["reservation_sha256"]
        or record.get("head") != grant["head"]
        or record.get("owner") != grant["owner"]
        or record.get("state") != "RESERVED"
    ):
        raise WorkflowError("Shared reservation changed during authorized write")
    manifest_path = grant["manifest_path"]
    if (
        has_symlink_component(manifest_path)
        or sha256_file(manifest_path) != grant["manifest_sha256"]
    ):
        raise WorkflowError("Authorization manifest changed during authorized write")
    if relative not in record.get("allowed_paths", []):
        raise WorkflowError("Exact path reservation changed during authorized write")
    if sha256_file(path) != grant["paths"][relative]:
        raise WorkflowError(
            "Source file changed after authorization; no overwrite performed"
        )


def atomic_write(path: Path, data: bytes) -> None:
    if has_symlink_component(path):
        raise WorkflowError("Source path may not be a symlink or junction during write")
    original_mode = stat.S_IMODE(path.stat().st_mode)
    fd, temp_name = tempfile.mkstemp(
        prefix=".local-workflow-", suffix=path.suffix, dir=str(path.parent)
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp_path, original_mode)
        if has_symlink_component(path):
            raise WorkflowError(
                "Source path changed to a symlink or junction before atomic replace"
            )
        os.replace(temp_path, path)
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def restore_apply_from_index(
    rollback: dict[str, Any], paths: list[tuple[str, Path]], receipt_dir: Path
) -> str:
    """Restore preimages only when the durable index names an exact formatter postimage."""
    if (
        current_head() != rollback.get("head")
        or rollback.get("reservation_path") != RESERVATION_REL
    ):
        return "NOT_RESTORED_HEAD_OR_RESERVATION_MISMATCH"
    reservation, reservation_sha = load_actual_reservation()
    record = reservation["record"]
    if (
        reservation_sha != rollback.get("reservation_sha256")
        or record.get("owner") != rollback.get("owner")
        or record.get("state") != "RESERVED"
        or record.get("head") != rollback.get("head")
    ):
        return "NOT_RESTORED_HEAD_OR_RESERVATION_MISMATCH"
    indexed_paths = rollback.get("paths")
    if not isinstance(indexed_paths, list) or not indexed_paths:
        return "NOT_RESTORED_INCOMPLETE_RECOVERY_INDEX"
    entries: dict[str, dict[str, Any]] = {}
    for entry in indexed_paths:
        if not isinstance(entry, dict):
            return "NOT_RESTORED_INCOMPLETE_RECOVERY_INDEX"
        relative = entry.get("path")
        if not isinstance(relative, str) or relative in entries:
            return "NOT_RESTORED_INCOMPLETE_RECOVERY_INDEX"
        entries[relative] = entry
    requested_paths: dict[str, Path] = {}
    for relative, path in paths:
        if not isinstance(relative, str) or relative in requested_paths:
            return "NOT_RESTORED_INCOMPLETE_RECOVERY_INDEX"
        requested_paths[relative] = path
    if not set(entries).issubset(requested_paths):
        return "NOT_RESTORED_INCOMPLETE_RECOVERY_INDEX"
    # The durable rollback index contains only files whose formatting changed.
    # Unchanged requested files have no backup and must never make recovery fail.
    paths = [(relative, path) for relative, path in paths if relative in entries]
    if len(paths) != len(entries):
        return "NOT_RESTORED_INCOMPLETE_RECOVERY_INDEX"
    prepared: list[tuple[str, Path, Path, dict[str, Any]]] = []
    private_root = ensure_private_subdir(receipt_dir, "private-backups", create=False)
    for relative, path in paths:
        if has_symlink_component(path):
            return "NOT_RESTORED_SOURCE_PATH_BECAME_LINKED"
        entry = entries[relative]
        backup_rel = entry.get("backup_path")
        if (
            not isinstance(backup_rel, str)
            or Path(backup_rel).is_absolute()
            or ".." in Path(backup_rel).parts
        ):
            return "NOT_RESTORED_UNSAFE_BACKUP_LOCATOR"
        backup = ROOT / backup_rel
        if has_symlink_component(backup):
            return "NOT_RESTORED_LINKED_BACKUP"
        try:
            backup = backup.resolve(strict=True)
            backup.relative_to(private_root.resolve(strict=True))
        except (OSError, ValueError):
            return "NOT_RESTORED_BACKUP_UNAVAILABLE"
        if (
            not backup.is_file()
            or sha256_file(backup) != entry.get("backup_sha256")
            or sha256_file(backup) != entry.get("preimage_sha256")
        ):
            return "NOT_RESTORED_BACKUP_HASH_MISMATCH"
        current = sha256_file(path)
        if current not in {entry.get("preimage_sha256"), entry.get("postimage_sha256")}:
            return "NOT_RESTORED_CONCURRENT_SOURCE_CHANGE"
        prepared.append((relative, path, backup, entry))
    for relative, path, backup, entry in prepared:
        reservation_now, reservation_sha_now = load_actual_reservation()
        record_now = reservation_now["record"]
        if (
            current_head() != rollback["head"]
            or reservation_sha_now != rollback["reservation_sha256"]
            or record_now.get("owner") != rollback["owner"]
            or record_now.get("state") != "RESERVED"
            or record_now.get("head") != rollback["head"]
            or relative not in record_now.get("allowed_paths", [])
        ):
            return "PARTIAL_RESTORATION_STOPPED_AUTHORITY_CHANGED"
        if sha256_file(path) == entry["postimage_sha256"]:
            atomic_write(path, backup.read_bytes())
    return "ROLLED_BACK_EXACT_POSTIMAGES_TO_PREIMAGES"


def format_apply(
    paths: list[tuple[str, Path]],
    owner: str,
    manifest: Path,
    config: dict[str, Any],
    receipt_dir: Path,
    receipt_path: Path,
) -> tuple[dict[str, Any], int]:
    grant = verify_apply_grant(manifest, paths, owner)
    prepared: list[tuple[str, Path, bytes, bytes]] = []
    for relative, path in paths:
        original = path.read_bytes()
        formatted = format_one(relative, path, config)
        prepared.append((relative, path, original, formatted))
    changed = [item for item in prepared if item[2] != item[3]]
    if not changed:
        return {
            "authorization": "VERIFIED_EXACT_HEAD_OWNER_RESERVATION_PREIMAGES",
            "manifest_sha256": grant["manifest_sha256"],
            "reservation_sha256": grant["reservation_sha256"],
            "reservation_revision": grant["reservation_revision"],
            "files": [
                {
                    "path": rel,
                    "before_sha256": sha256_bytes(old),
                    "after_sha256": sha256_bytes(new),
                    "written": False,
                }
                for rel, _, old, new in prepared
            ],
            "private_backup_directory": None,
            "recovery": "NOT_NEEDED",
            "rollback_record": None,
        }, 0

    backup_root = ensure_private_subdir(
        receipt_dir,
        "private-backups",
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        + "-"
        + uuid.uuid4().hex[:8],
    )
    backup_entries = []
    for relative, path, original, formatted in changed:
        recheck_apply_grant(grant, relative, path)
        backup = backup_root / relative
        ensure_work_directory(backup.parent)
        durable_private_write(backup, original)
        backup_entries.append(
            {
                "path": relative,
                "preimage_sha256": sha256_bytes(original),
                "postimage_sha256": sha256_bytes(formatted),
                "backup_path": backup.relative_to(ROOT).as_posix(),
                "backup_sha256": sha256_file(backup),
            }
        )
    rollback_record = {
        "schema": "lumenis.local-format-rollback.v1",
        "created_by_action": "format-apply",
        "owner": owner,
        "head": grant["head"],
        "reservation_path": RESERVATION_REL,
        "reservation_sha256": grant["reservation_sha256"],
        "reservation_revision": grant["reservation_revision"],
        "paths": backup_entries,
    }
    intent = {
        "schema": "lumenis.local-workflow-receipt.v1",
        "action": "format-apply",
        "owner": owner,
        "started_at": now_utc(),
        "head": grant["head"],
        "paths": [rel for rel, _ in paths],
        "path_sha256": {rel: sha256_file(path) for rel, path in paths},
        "exit_code": 2,
        "model_calls": 0,
        "repair_authorization": "VERIFIED_EXACT_HEAD_OWNER_RESERVATION_PREIMAGES",
        "write_coordination": "SHARED_LOCAL_PROCESS_LOCK_FOR_THIS_HELPER_ONLY_EXTERNAL_EDITORS_NOT_LOCKED",
        "recovery": "DURABLE_APPLY_INTENT_PREPARED",
        "intent_status": "APPLYING",
        "errors": [],
        "result": {
            "authorization": "VERIFIED_EXACT_HEAD_OWNER_RESERVATION_PREIMAGES",
            "manifest_sha256": grant["manifest_sha256"],
            "reservation_sha256": grant["reservation_sha256"],
            "reservation_revision": grant["reservation_revision"],
            "private_backup_directory": backup_root.relative_to(ROOT).as_posix(),
            "recovery": "DURABLE_APPLY_INTENT_PREPARED",
            "write_coordination": "SHARED_LOCAL_PROCESS_LOCK_FOR_THIS_HELPER_ONLY_EXTERNAL_EDITORS_NOT_LOCKED",
            "rollback_record": rollback_record,
        },
    }
    for relative, path in paths:
        recheck_apply_grant(grant, relative, path)
    atomic_receipt(receipt_path, intent)
    try:
        for relative, path, original, formatted in changed:
            recheck_apply_grant(grant, relative, path)
            atomic_write(path, formatted)
        intent["exit_code"] = 0
        intent["intent_status"] = "APPLIED"
        intent["recovery"] = "BACKUPS_AND_ROLLBACK_INDEX_DURABLE"
        intent["result"]["recovery"] = intent["recovery"]
        intent["path_sha256_after"] = {rel: sha256_file(path) for rel, path in paths}
        intent["result"]["files"] = [
            {
                "path": rel,
                "before_sha256": sha256_bytes(old),
                "after_sha256": sha256_bytes(new),
                "written": old != new,
            }
            for rel, _, old, new in prepared
        ]
        atomic_receipt(receipt_path, intent)
    except (
        Exception
    ) as exc:  # exact-index recovery is required for any failed write/receipt.
        recovery = restore_apply_from_index(rollback_record, paths, receipt_dir)
        intent["exit_code"] = 1
        intent["intent_status"] = "APPLY_FAILED"
        intent["recovery"] = recovery
        receipt_update_failure = None
        try:
            atomic_receipt(receipt_path, intent)
        except (OSError, TypeError, ValueError) as receipt_exc:
            receipt_update_failure = type(receipt_exc).__name__
        failure_message = (
            "Authorized format apply failed; durable recovery status: " + recovery
        )
        if receipt_update_failure is not None:
            failure_message += (
                "; failure receipt update failed (" + receipt_update_failure + ")"
            )
        raise WorkflowError(
            failure_message, 1
        ) from exc
    return intent["result"], 0


def receipt_file(path_arg: str, receipt_dir: Path) -> tuple[Path, str]:
    candidate = Path(path_arg)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    if has_symlink_component(candidate) or not candidate.is_file():
        raise WorkflowError("Prior format-apply receipt is unavailable")
    resolved = candidate.resolve()
    try:
        receipts_root = ensure_private_subdir(receipt_dir, "receipts", create=False)
        relative_to_receipts = resolved.relative_to(
            receipts_root.resolve(strict=True)
        ).as_posix()
    except ValueError as exc:
        raise WorkflowError(
            "Rollback source must be a receipt written under this protected receipt directory"
        ) from exc
    if (
        not is_ignored(resolved.relative_to(ROOT.resolve()).as_posix())
        or candidate.stat().st_size > 1024 * 1024
    ):
        raise WorkflowError("Rollback source must be a bounded ignored receipt")
    return resolved, relative_to_receipts


def validate_rollback_record(
    apply_receipt_path: Path,
    paths: list[tuple[str, Path]],
    owner: str,
    receipt_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        apply_receipt = json.loads(apply_receipt_path.read_text("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WorkflowError("Prior format-apply receipt is invalid") from exc
    if (
        not isinstance(apply_receipt, dict)
        or apply_receipt.get("schema") != "lumenis.local-workflow-receipt.v1"
        or apply_receipt.get("action") != "format-apply"
        or apply_receipt.get("exit_code") != 0
        or apply_receipt.get("owner") != owner
    ):
        raise WorkflowError(
            "Rollback requires a successful format-apply receipt for the same owner"
        )
    result = apply_receipt.get("result")
    rollback = result.get("rollback_record") if isinstance(result, dict) else None
    if (
        not isinstance(rollback, dict)
        or rollback.get("schema") != "lumenis.local-format-rollback.v1"
        or rollback.get("created_by_action") != "format-apply"
    ):
        raise WorkflowError("Receipt has no tool-created format backup record")
    head = current_head()
    if (
        rollback.get("head") != head
        or apply_receipt.get("head") != head
        or rollback.get("owner") != owner
    ):
        raise WorkflowError("Rollback receipt HEAD or owner no longer matches")
    if rollback.get("reservation_path") != RESERVATION_REL:
        raise WorkflowError(
            "Rollback receipt does not reference the canonical shared reservation"
        )
    reservation, reservation_sha = load_actual_reservation()
    record = reservation["record"]
    if (
        reservation_sha != rollback.get("reservation_sha256")
        or record.get("owner") != owner
        or record.get("state") != "RESERVED"
        or record.get("head") != head
    ):
        raise WorkflowError(
            "Current same-owner shared reservation/HEAD does not authorize rollback"
        )
    allowed = record.get("allowed_paths")
    if not isinstance(allowed, list):
        raise WorkflowError("Current reservation has no exact path list")
    entries = rollback.get("paths")
    if not isinstance(entries, list) or not entries:
        raise WorkflowError("No tool-created changed paths are available to roll back")
    expected = [relative for relative, _ in paths]
    entry_paths = [entry.get("path") for entry in entries if isinstance(entry, dict)]
    if (
        len(entry_paths) != len(entries)
        or set(entry_paths) != set(expected)
        or len(entry_paths) != len(expected)
    ):
        raise WorkflowError(
            "Rollback --paths must exactly match the format-apply backup"
        )
    for relative, path in paths:
        if relative not in allowed:
            raise WorkflowError(
                "Rollback path is not present in the current exact reservation"
            )
        entry = next(item for item in entries if item["path"] == relative)
        backup_raw = entry.get("backup_path")
        if not isinstance(backup_raw, str):
            raise WorkflowError("Rollback backup locator is malformed")
        backup_candidate = ROOT / backup_raw
        if (
            Path(backup_raw).is_absolute()
            or ".." in Path(backup_raw).parts
            or has_symlink_component(backup_candidate)
        ):
            raise WorkflowError("Rollback backup locator is unsafe")
        try:
            private_root = ensure_private_subdir(
                receipt_dir, "private-backups", create=False
            )
            backup = backup_candidate.resolve(strict=True)
            backup.relative_to(private_root.resolve(strict=True))
        except (OSError, ValueError) as exc:
            raise WorkflowError(
                "Rollback backup is outside the private backup directory"
            ) from exc
        if not backup.is_file() or backup.suffix.lower() not in FORMATTABLE:
            raise WorkflowError("Tool-created private backup is unavailable")
        if sha256_file(backup) != entry.get("backup_sha256") or entry.get(
            "preimage_sha256"
        ) != sha256_file(backup):
            raise WorkflowError(
                "Private backup hash does not match the original preimage"
            )
        if (
            not re.fullmatch(r"[0-9a-f]{64}", str(entry.get("postimage_sha256", "")))
            or sha256_file(path) != entry["postimage_sha256"]
        ):
            raise WorkflowError(
                "Current source no longer matches the exact format-apply postimage"
            )
        if not re.fullmatch(r"[0-9a-f]{64}", str(entry.get("preimage_sha256", ""))):
            raise WorkflowError("Rollback preimage SHA-256 is malformed")
    return rollback, {item["path"]: item for item in entries}


def recheck_rollback(
    rollback: dict[str, Any], relative: str, path: Path, entry: dict[str, Any]
) -> None:
    if has_symlink_component(path):
        raise WorkflowError("Rollback source path became a symlink")
    if current_head() != rollback["head"]:
        raise WorkflowError("HEAD changed during rollback; stop without overwriting")
    reservation, reservation_sha = load_actual_reservation()
    record = reservation["record"]
    if (
        reservation_sha != rollback["reservation_sha256"]
        or record.get("owner") != rollback["owner"]
        or record.get("state") != "RESERVED"
        or record.get("head") != rollback["head"]
        or relative not in record.get("allowed_paths", [])
    ):
        raise WorkflowError("Same-owner reservation changed during rollback")
    if sha256_file(path) != entry["postimage_sha256"]:
        raise WorkflowError(
            "Source changed after rollback authorization; no overwrite performed"
        )


def restore_rollback_forward(
    index: dict[str, Any], paths: list[tuple[str, Path]], receipt_dir: Path
) -> str:
    if (
        current_head() != index.get("head")
        or index.get("reservation_path") != RESERVATION_REL
    ):
        return "NOT_RESTORED_HEAD_OR_RESERVATION_MISMATCH"
    reservation, reservation_sha = load_actual_reservation()
    record = reservation["record"]
    if (
        reservation_sha != index.get("reservation_sha256")
        or record.get("owner") != index.get("owner")
        or record.get("state") != "RESERVED"
        or record.get("head") != index.get("head")
    ):
        return "NOT_RESTORED_HEAD_OR_RESERVATION_MISMATCH"
    entries = {
        entry.get("path"): entry
        for entry in index.get("paths", [])
        if isinstance(entry, dict)
    }
    if len(entries) != len(paths) or set(entries) != {
        relative for relative, _ in paths
    }:
        return "NOT_RESTORED_INCOMPLETE_RECOVERY_INDEX"
    private_root = ensure_private_subdir(receipt_dir, "private-backups", create=False)
    prepared: list[tuple[str, Path, Path, dict[str, Any]]] = []
    for relative, path in paths:
        if has_symlink_component(path):
            return "NOT_RESTORED_SOURCE_PATH_BECAME_LINKED"
        entry = entries[relative]
        backup_raw = entry.get("backup_path")
        if (
            not isinstance(backup_raw, str)
            or Path(backup_raw).is_absolute()
            or ".." in Path(backup_raw).parts
        ):
            return "NOT_RESTORED_UNSAFE_BACKUP_LOCATOR"
        backup = ROOT / backup_raw
        if has_symlink_component(backup):
            return "NOT_RESTORED_LINKED_BACKUP"
        try:
            backup = backup.resolve(strict=True)
            backup.relative_to(private_root.resolve(strict=True))
        except (OSError, ValueError):
            return "NOT_RESTORED_BACKUP_UNAVAILABLE"
        if (
            not backup.is_file()
            or sha256_file(backup) != entry.get("backup_sha256")
            or sha256_file(backup) != entry.get("forward_target_sha256")
        ):
            return "NOT_RESTORED_BACKUP_HASH_MISMATCH"
        if sha256_file(path) not in {
            entry.get("rollback_target_sha256"),
            entry.get("forward_target_sha256"),
        }:
            return "NOT_RESTORED_CONCURRENT_SOURCE_CHANGE"
        prepared.append((relative, path, backup, entry))
    for relative, path, backup, entry in prepared:
        reservation_now, reservation_sha_now = load_actual_reservation()
        record_now = reservation_now["record"]
        if (
            current_head() != index["head"]
            or reservation_sha_now != index["reservation_sha256"]
            or record_now.get("owner") != index["owner"]
            or record_now.get("state") != "RESERVED"
            or record_now.get("head") != index["head"]
            or relative not in record_now.get("allowed_paths", [])
        ):
            return "PARTIAL_RESTORATION_STOPPED_AUTHORITY_CHANGED"
        if sha256_file(path) == entry["rollback_target_sha256"]:
            atomic_write(path, backup.read_bytes())
    return "ROLLED_FORWARD_TO_EXACT_FORMAT_POSTIMAGES_FROM_DURABLE_INTENT"


def rollback_apply(
    paths: list[tuple[str, Path]],
    owner: str,
    apply_receipt_path: Path,
    config: dict[str, Any],
    receipt_dir: Path,
    receipt_path: Path,
) -> tuple[dict[str, Any], int]:
    rollback, entries = validate_rollback_record(
        apply_receipt_path, paths, owner, receipt_dir
    )
    prepared: list[tuple[str, Path, bytes, bytes, dict[str, Any]]] = []
    private_root = ensure_private_subdir(receipt_dir, "private-backups", create=False)
    for relative, path in paths:
        entry = entries[relative]
        backup_candidate = ROOT / entry["backup_path"]
        if (
            Path(entry["backup_path"]).is_absolute()
            or ".." in Path(entry["backup_path"]).parts
            or has_symlink_component(backup_candidate)
        ):
            raise WorkflowError("Rollback backup locator is unsafe")
        backup = backup_candidate.resolve(strict=True)
        backup.relative_to(private_root.resolve(strict=True))
        original = path.read_bytes()
        restore = backup.read_bytes()
        formatted = format_one(relative, backup, config, config_anchor=ROOT / relative)
        if sha256_bytes(formatted) != entry["postimage_sha256"]:
            raise WorkflowError(
                "Backup is not the formatter source for the recorded postimage"
            )
        prepared.append((relative, path, original, restore, entry))
    recovery_root = ensure_private_subdir(
        receipt_dir,
        "private-backups",
        "rollback-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        + "-"
        + uuid.uuid4().hex[:8],
    )
    recovery_entries = []
    for relative, path, postimage, preimage, entry in prepared:
        recheck_rollback(rollback, relative, path, entry)
        backup_path = recovery_root / relative
        ensure_work_directory(backup_path.parent)
        durable_private_write(backup_path, postimage)
        recovery_entries.append(
            {
                "path": relative,
                "rollback_target_sha256": entry["preimage_sha256"],
                "forward_target_sha256": entry["postimage_sha256"],
                "backup_path": backup_path.relative_to(ROOT).as_posix(),
                "backup_sha256": sha256_file(backup_path),
            }
        )
    recovery_index = {
        "head": rollback["head"],
        "owner": owner,
        "reservation_path": RESERVATION_REL,
        "reservation_sha256": rollback["reservation_sha256"],
        "paths": recovery_entries,
    }
    intent = {
        "schema": "lumenis.local-workflow-receipt.v1",
        "action": "rollback",
        "owner": owner,
        "started_at": now_utc(),
        "head": rollback["head"],
        "paths": [rel for rel, _ in paths],
        "path_sha256": {rel: sha256_file(path) for rel, path in paths},
        "exit_code": 2,
        "model_calls": 0,
        "repair_authorization": "VERIFIED_SAME_OWNER_HEAD_RESERVATION_AND_EXACT_FORMAT_POSTIMAGES",
        "write_coordination": "SHARED_LOCAL_PROCESS_LOCK_FOR_THIS_HELPER_ONLY_EXTERNAL_EDITORS_NOT_LOCKED",
        "recovery": "DURABLE_ROLLBACK_INTENT_PREPARED",
        "intent_status": "ROLLING_BACK",
        "errors": [],
        "result": {"recovery_index": recovery_index},
    }
    atomic_receipt(receipt_path, intent)
    try:
        for relative, path, postimage, preimage, entry in prepared:
            recheck_rollback(rollback, relative, path, entry)
            atomic_write(path, preimage)
        result = {
            "authorization": "VERIFIED_SAME_OWNER_HEAD_RESERVATION_AND_EXACT_FORMAT_POSTIMAGES",
            "source_format_apply_receipt": apply_receipt_path.relative_to(
                ROOT
            ).as_posix(),
            "reservation_sha256": rollback["reservation_sha256"],
            "reservation_revision": rollback.get("reservation_revision"),
            "files": [
                {
                    "path": relative,
                    "before_postimage_sha256": sha256_bytes(postimage),
                    "restored_preimage_sha256": sha256_bytes(preimage),
                    "restored": True,
                }
                for relative, _, postimage, preimage, _ in prepared
            ],
            "private_recovery_backup_directory": recovery_root.relative_to(
                ROOT
            ).as_posix(),
            "recovery": "ROLLED_BACK_WITH_POSTIMAGES_BACKED_UP",
            "recovery_index": recovery_index,
        }
        intent["exit_code"] = 0
        intent["intent_status"] = "ROLLED_BACK"
        intent["recovery"] = result["recovery"]
        intent["result"] = result
        intent["path_sha256_after"] = {rel: sha256_file(path) for rel, path in paths}
        atomic_receipt(receipt_path, intent)
    except Exception as exc:  # roll forward only the exact durable source image.
        recovery = restore_rollback_forward(recovery_index, paths, receipt_dir)
        intent["exit_code"] = 1
        intent["intent_status"] = "ROLLBACK_FAILED"
        intent["recovery"] = recovery
        try:
            atomic_receipt(receipt_path, intent)
        except (OSError, WorkflowError):
            pass
        raise WorkflowError(
            "Rollback failed; durable recovery status: " + recovery, 1
        ) from exc
    return result, 0


def locale_generator_preview(config: dict[str, Any]) -> tuple[dict[str, Any], int]:
    exact_relatives = [LOCALE_GENERATOR, *LOCALE_INPUTS, LOCALE_TARGET]
    source_paths = [
        normalize_repo_path(relative, allowed_suffixes=STATIC_SUFFIXES)
        for relative in exact_relatives
    ]
    before = file_hashes(source_paths)
    if before[LOCALE_GENERATOR] != LOCALE_GENERATOR_SHA256:
        raise WorkflowError(
            "Existing locale generator changed from the reviewed fixed implementation; preview refused"
        )
    dart = executable("dart", config)
    with tempfile.TemporaryDirectory(
        prefix="lumenis-locale-generator-preview-"
    ) as temp_dir:
        mirror = Path(temp_dir)
        for relative, source in source_paths:
            destination = mirror / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        copied_target = mirror / LOCALE_TARGET
        generated_target = run_process(
            [str(dart), str(mirror / LOCALE_GENERATOR)], cwd=mirror / "app", timeout=180
        )
        if generated_target["exit_code"] != 0:
            return {
                "status": "PREVIEW_FAILED",
                "fixed_generator_sha256": LOCALE_GENERATOR_SHA256,
                "input_hashes": before,
                "process": generated_target,
                "source_files_unchanged": file_hashes(source_paths) == before,
                "persisted_candidate": False,
            }, 1
        generated = copied_target.read_bytes()
        original = (ROOT / LOCALE_TARGET).read_bytes()
        try:
            diff = "".join(
                difflib.unified_diff(
                    original.decode("utf-8-sig").splitlines(keepends=True),
                    generated.decode("utf-8-sig").splitlines(keepends=True),
                    fromfile=LOCALE_TARGET + " (current)",
                    tofile=LOCALE_TARGET + " (preview)",
                )
            )
        except UnicodeError as exc:
            raise WorkflowError("Locale generator produced non-UTF-8 output") from exc
        unchanged = file_hashes(source_paths) == before
        return {
            "status": "PREVIEW_ONLY",
            "generator": LOCALE_GENERATOR,
            "generator_sha256": before[LOCALE_GENERATOR],
            "source_input_hashes": {
                key: value for key, value in before.items() if key != LOCALE_TARGET
            },
            "target_before_sha256": before[LOCALE_TARGET],
            "target_preview_sha256": sha256_bytes(generated),
            "target_changed": generated != original,
            "diff": safe_error(diff, 30000),
            "source_files_unchanged": unchanged,
            "temporary_mirror_removed": True,
            "persisted_candidate": False,
            "model_calls": 0,
            "process": generated_target,
            "acceptance": "GENERATOR_PREVIEW_ONLY_NOT_PRODUCT_INTEGRATION",
        }, 0 if unchanged else 1


def walk_inputs(root: Path, *, target: str) -> list[tuple[str, Path]]:
    selected: list[tuple[str, Path]] = []
    if target == "website":
        base = ROOT / "website"
        if not base.is_dir():
            raise WorkflowError("Website source root is unavailable")
        exclude = {
            "node_modules",
            ".git",
            ".astro",
            "dist",
            "build",
            "work",
            "vendor",
            "test",
            "tests",
            "__tests__",
            ".cache",
        }
        for current, dirs, files in os.walk(base, followlinks=False):
            current_path = Path(current)
            dirs[:] = [
                name
                for name in dirs
                if name.lower() not in exclude
                and not is_symlink_or_junction(current_path / name)
            ]
            for name in files:
                path = current_path / name
                if (
                    is_symlink_or_junction(path)
                    or name.lower() in BLOCKED_BASENAMES
                    or name.lower().startswith(".env.")
                ):
                    continue
                if (
                    path.suffix.lower()
                    in {
                        ".lock",
                        ".json",
                        ".mjs",
                        ".js",
                        ".ts",
                        ".tsx",
                        ".astro",
                        ".css",
                        ".scss",
                        ".html",
                        ".svg",
                        ".md",
                        ".txt",
                        ".yaml",
                        ".yml",
                        ".toml",
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".webp",
                        ".woff",
                        ".woff2",
                        ".ttf",
                        ".ico",
                    }
                    or name
                    in {
                        "package.json",
                        "package-lock.json",
                        "astro.config.mjs",
                        "astro.config.ts",
                        "tsconfig.json",
                    }
                ) and path.stat().st_size <= MAX_SOURCE_BYTES:
                    selected.append((path.relative_to(ROOT).as_posix(), path))
    elif target == "flutter-web":
        base = ROOT / "app"
        if not base.is_dir():
            raise WorkflowError("Flutter source root is unavailable")
        for exact in (
            "pubspec.yaml",
            "pubspec.lock",
            "analysis_options.yaml",
            ".dart_tool/package_config.json",
        ):
            path = base / exact
            if path.is_file() and not is_symlink_or_junction(path):
                selected.append((path.relative_to(ROOT).as_posix(), path))
        roots = [base / "lib", base / "web", base / "assets"]
        for tree in roots:
            if not tree.is_dir():
                continue
            for current, dirs, files in os.walk(tree, followlinks=False):
                current_path = Path(current)
                dirs[:] = [
                    name
                    for name in dirs
                    if name.lower() not in BLOCKED_PARTS
                    and not is_symlink_or_junction(current_path / name)
                ]
                for name in files:
                    path = current_path / name
                    if (
                        is_symlink_or_junction(path)
                        or name.lower() in BLOCKED_BASENAMES
                        or name.lower().startswith(".env.")
                    ):
                        continue
                    if path.stat().st_size <= MAX_SOURCE_BYTES:
                        selected.append((path.relative_to(ROOT).as_posix(), path))
    else:
        raise WorkflowError("Build target must be website or flutter-web")
    selected.sort(key=lambda item: item[0])
    if not selected:
        raise WorkflowError("No exact build inputs were found")
    return selected


def tree_hash(paths: list[tuple[str, Path]]) -> tuple[str, dict[str, str]]:
    hashes = file_hashes(paths)
    digest = hashlib.sha256()
    for relative in sorted(hashes):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashes[relative].encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest(), hashes


def output_tree_hash(output_dir: Path) -> tuple[str, int]:
    if not output_dir.is_dir():
        raise WorkflowError(
            "Build command completed without the expected output directory"
        )
    digest = hashlib.sha256()
    count = 0
    total_bytes = 0
    for current, dirs, files in os.walk(output_dir, followlinks=False):
        current_path = Path(current)
        dirs[:] = [
            name for name in dirs if not is_symlink_or_junction(current_path / name)
        ]
        for name in sorted(files):
            path = current_path / name
            if is_symlink_or_junction(path):
                continue
            rel = path.relative_to(output_dir).as_posix()
            total_bytes += path.stat().st_size
            if total_bytes > 2 * 1024 * 1024 * 1024 or count >= 100_000:
                raise WorkflowError(
                    "Build output exceeds bounded receipt hashing limits"
                )
            digest.update(rel.encode("utf-8"))
            digest.update(b"\0")
            digest.update(bytes.fromhex(sha256_file(path)))
            digest.update(b"\n")
            count += 1
    return digest.hexdigest(), count


def build_target(
    target: str, config: dict[str, Any], paths: list[tuple[str, Path]]
) -> tuple[dict[str, Any], int]:
    selector = config.get("tools", {}).get("build")
    expected_selector = "website:astro" if target == "website" else "flutter:web"
    if selector is not None and selector != expected_selector:
        raise WorkflowError(
            "Configured build selector does not match the requested target"
        )
    inputs = walk_inputs(ROOT, target=target)
    explicit = {name: sha256_file(path) for name, path in paths}
    target_prefix = "website/" if target == "website" else "app/"
    if any(not name.startswith(target_prefix) for name in explicit):
        raise WorkflowError("Explicit build paths must belong to the selected target")
    for name in explicit:
        if name not in {rel for rel, _ in inputs}:
            inputs.append((name, ROOT / name))
    inputs.sort(key=lambda item: item[0])
    source_hash, input_hashes = tree_hash(inputs)
    head = current_head()
    if target == "website":
        package_path = ROOT / "website/package.json"
        package = json.loads(package_path.read_text("utf-8-sig"))
        scripts = package.get("scripts", {}) if isinstance(package, dict) else {}
        if scripts.get("build") != "astro build" or any(
            key in scripts for key in ("prebuild", "postbuild")
        ):
            raise WorkflowError(
                "Website build must be the existing fixed `astro build` script without lifecycle hooks"
            )
        node = executable("node", config)
        npm_cli = npm_cli_path(config)
        command = [str(node), str(npm_cli), "run", "build"]
        cwd = ROOT / "website"
        output_dir = ROOT / "website/dist"
        tool_inputs = {
            "node_sha256": sha256_file(node),
            "npm_cli_sha256": sha256_file(npm_cli),
        }
    else:
        app = ROOT / "app"
        if (
            not (app / ".dart_tool/package_config.json").is_file()
            or not (app / "pubspec.lock").is_file()
        ):
            raise WorkflowError(
                "Flutter Web build requires existing locked dependencies; pub get is never run here"
            )
        dart = executable("dart", config)
        snapshot = flutter_tools_snapshot(dart, config)
        command = [str(dart), str(snapshot), "build", "web", "--release", "--no-pub"]
        cwd = app
        output_dir = app / "build/web"
        tool_inputs = {
            "dart_sha256": sha256_file(dart),
            "flutter_tools_snapshot_sha256": sha256_file(snapshot),
        }
    command_template_hash = sha256_bytes(
        json.dumps(
            {
                "target": target,
                "template": [
                    Path(x).name if index == 0 else x
                    for index, x in enumerate(command[1:])
                ],
            },
            sort_keys=True,
        ).encode()
    )
    cache_key = sha256_bytes(
        json.dumps(
            {
                "target": target,
                "head": head,
                "source_hash": source_hash,
                "tool_inputs": tool_inputs,
                "command_template_hash": command_template_hash,
            },
            sort_keys=True,
        ).encode()
    )
    cache_dir = ensure_private_subdir(DEFAULT_RECEIPT, "build-cache")
    cache_path = cache_dir / f"{target}-{cache_key}.json"
    if cache_path.is_file() and not has_symlink_component(cache_path):
        try:
            cached = json.loads(cache_path.read_text("utf-8-sig"))
            current_output, output_count = output_tree_hash(output_dir)
            if (
                cached.get("cache_key") == cache_key
                and cached.get("exit_code") == 0
                and cached.get("output_tree_sha256") == current_output
            ):
                return {
                    "status": "CACHED_SUCCESS",
                    "cache_key": cache_key,
                    "cache_receipt": cache_path.relative_to(ROOT).as_posix(),
                    "source_tree_sha256": source_hash,
                    "input_count": len(input_hashes),
                    "input_hashes": input_hashes,
                    "tool_inputs": tool_inputs,
                    "command_template_sha256": command_template_hash,
                    "output_tree_sha256": current_output,
                    "output_file_count": output_count,
                    "command_executed": False,
                }, 0
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    result = run_process(
        command, cwd=cwd, timeout=1800 if target == "flutter-web" else 900
    )
    if result["exit_code"] != 0:
        return {
            "status": "FAILED",
            "cache_key": cache_key,
            "source_tree_sha256": source_hash,
            "input_count": len(input_hashes),
            "input_hashes": input_hashes,
            "tool_inputs": tool_inputs,
            "command_template_sha256": command_template_hash,
            "command_executed": True,
            "process": result,
            "output_tree_sha256": None,
        }, 1
    if tree_hash(inputs)[0] != source_hash:
        raise WorkflowError(
            "Build inputs changed while the build was running; result is not cacheable"
        )
    output_hash, output_count = output_tree_hash(output_dir)
    cache_record = {
        "cache_key": cache_key,
        "target": target,
        "head": head,
        "source_tree_sha256": source_hash,
        "input_hashes": input_hashes,
        "tool_inputs": tool_inputs,
        "command_template_sha256": command_template_hash,
        "exit_code": 0,
        "output_tree_sha256": output_hash,
        "output_file_count": output_count,
        "recorded_at": now_utc(),
    }
    atomic_receipt(cache_path, cache_record)
    return {
        "status": "PASS_BUILD_ONLY",
        "cache_key": cache_key,
        "source_tree_sha256": source_hash,
        "input_count": len(input_hashes),
        "input_hashes": input_hashes,
        "tool_inputs": tool_inputs,
        "command_template_sha256": command_template_hash,
        "command_executed": True,
        "process": result,
        "output_tree_sha256": output_hash,
        "output_file_count": output_count,
        "runtime_user_acceptance": "NOT_PROVEN_BY_BUILD",
    }, 0


def snapshot(config: dict[str, Any], paths: list[tuple[str, Path]]) -> dict[str, Any]:
    head = current_head()
    origin = git_output("rev-parse", "origin/main")
    branch = git_output("branch", "--show-current")
    status = git_output("status", "--porcelain=v1", "-uall", preserve_whitespace=True)
    lines = [line for line in status.splitlines() if line]
    counts = {"tracked_modified": 0, "untracked": 0, "staged": 0, "other": 0}
    for line in lines:
        code = line[:2]
        if code == "??":
            counts["untracked"] += 1
        elif "?" not in code:
            counts["tracked_modified"] += 1
            if code.strip() and code[0] not in {" ", "?"}:
                counts["staged"] += 1
        else:
            counts["other"] += 1
    live_summary: dict[str, Any] = {"status": "UNAVAILABLE"}
    live = ROOT / "data/runtime/governance/live_dispatch.json"
    if live.is_file() and not is_symlink_or_junction(live):
        try:
            doc = json.loads(live.read_text("utf-8-sig"))
            roles = doc.get("roles", {}) if isinstance(doc, dict) else {}
            states: dict[str, int] = {}
            if isinstance(roles, dict):
                for item in roles.values():
                    if isinstance(item, dict):
                        state = str(item.get("state", "UNKNOWN"))
                        states[state] = states.get(state, 0) + 1
            live_summary = {
                "status": "READ_ONLY_SUMMARY",
                "state_counts": states,
                "current_business_role_set": bool(doc.get("current_business_role")),
                "independent_frontend_set": bool(doc.get("independent_frontend")),
            }
        except (OSError, UnicodeError, json.JSONDecodeError):
            live_summary = {"status": "INVALID_OR_UNREADABLE"}
    tools = {}
    for name in sorted(TOOL_KEYS):
        try:
            tool = executable(name, config, optional=True)
            tools[name] = "AVAILABLE" if tool and tool.is_file() else "MISSING"
        except WorkflowError:
            tools[name] = "INVALID_LOCAL_CONFIGURATION"
    if config.get("flutter_tools_snapshot"):
        tools["flutter_tools_snapshot"] = (
            "AVAILABLE"
            if Path(config["flutter_tools_snapshot"]).is_file()
            else "MISSING"
        )
    return {
        "local_head": head,
        "cached_origin_main": origin,
        "branch": branch,
        "dirty_counts": counts,
        "live_dispatch": live_summary,
        "tools": tools,
        "selected_path_sha256": file_hashes(paths),
        "remote_current": "NOT_QUERIED",
        "runtime": "NOT_INSPECTED",
        "production_database": "NOT_INSPECTED",
    }


def atomic_receipt(path: Path, value: dict[str, Any]) -> None:
    ensure_work_directory(path.parent)
    if has_symlink_component(path):
        raise WorkflowError("Receipt path may not be a symlink or junction")
    fd, name = tempfile.mkstemp(prefix=".receipt-", suffix=".tmp", dir=str(path.parent))
    temp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        ensure_work_directory(path.parent, create=False)
        if has_symlink_component(path):
            raise WorkflowError(
                "Receipt path changed to a symlink or junction before atomic replace"
            )
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def parser() -> argparse.ArgumentParser:
    class WorkflowParser(argparse.ArgumentParser):
        def error(self, message: str) -> None:
            raise WorkflowError(
                "Invalid command arguments; use --help for the fixed CLI syntax"
            )

    p = WorkflowParser(
        description="Guarded local LUMENIS engineering workflow; no tests, runtime, model or arbitrary shell."
    )
    sub = p.add_subparsers(dest="action", required=True)
    for action in (
        "snapshot",
        "check",
        "diff",
        "format-preview",
        "format-apply",
        "rollback",
        "locale-preview",
        "build",
    ):
        child = sub.add_parser(action)
        child.add_argument("--owner", required=True)
        child.add_argument(
            "--paths",
            nargs="+",
            required=action
            in {"check", "diff", "format-preview", "format-apply", "rollback"},
        )
        child.add_argument("--receipt-dir", default=str(DEFAULT_RECEIPT))
        if action == "format-apply":
            child.add_argument("--manifest", required=True)
        if action == "rollback":
            child.add_argument(
                "--receipt",
                required=True,
                help="Prior successful local format-apply receipt",
            )
        if action == "build":
            child.add_argument(
                "--target", choices=("website", "flutter-web"), required=True
            )
    return p


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
    except WorkflowError as exc:
        args = SimpleNamespace(
            action="cli", owner="UNKNOWN", receipt_dir=str(DEFAULT_RECEIPT)
        )
        started_at = now_utc()
        record = {
            "schema": "lumenis.local-workflow-receipt.v1",
            "action": "cli",
            "owner": "UNKNOWN",
            "started_at": started_at,
            "ended_at": now_utc(),
            "duration_seconds": 0,
            "head": None,
            "paths": [],
            "path_sha256": {},
            "exit_code": 2,
            "model_calls": 0,
            "repair_authorization": "NOT_RUN",
            "recovery": "NOT_APPLICABLE",
            "next_step": "Correct the fixed CLI arguments.",
            "errors": [safe_error(str(exc))],
            "result": "FAILED_CLOSED",
        }
        try:
            record["head"] = current_head()
            receipt_dir = safe_receipt_dir(str(DEFAULT_RECEIPT))
            receipt_path = (
                receipt_dir
                / "receipts"
                / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')}-cli-{uuid.uuid4().hex[:8]}.json"
            )
            atomic_receipt(receipt_path, record)
            print(
                json.dumps(
                    {
                        "receipt": receipt_path.relative_to(ROOT).as_posix(),
                        "action": "cli",
                        "exit_code": 2,
                    },
                    ensure_ascii=False,
                )
            )
        except Exception:  # noqa: BLE001 -- preserve a receipt if an unexpected error occurs.
            print(
                json.dumps(
                    {"action": "cli", "exit_code": 2, "receipt": "NOT_WRITTEN"},
                    ensure_ascii=False,
                )
            )
        return 2
    start = time.monotonic()
    started_at = now_utc()
    exit_code = 2
    receipt_dir = DEFAULT_RECEIPT
    receipt_path: Path | None = None
    paths: list[tuple[str, Path]] = []
    record: dict[str, Any] = {
        "schema": "lumenis.local-workflow-receipt.v1",
        "action": args.action,
        "owner": args.owner,
        "started_at": started_at,
        "head": None,
        "paths": [],
        "path_sha256": {},
        "exit_code": 2,
        "model_calls": 0,
        "repair_authorization": "NOT_REQUIRED_READ_ONLY",
        "recovery": "NOT_APPLICABLE",
        "next_step": "Review the bounded receipt; do not infer product acceptance from static/build output.",
        "errors": [],
    }
    try:
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", args.owner):
            raise WorkflowError("Owner must be a short identifier")
        receipt_dir = safe_receipt_dir(args.receipt_dir)
        receipt_store = ensure_private_subdir(receipt_dir, "receipts")
        receipt_path = (
            receipt_store
            / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')}-{args.action}-{uuid.uuid4().hex[:8]}.json"
        )
        config = load_tools_config(receipt_dir)
        paths = explicit_paths(
            getattr(args, "paths", None),
            required=args.action
            in {"check", "diff", "format-preview", "format-apply", "rollback"},
            suffixes=STATIC_SUFFIXES,
        )
        record["paths"] = [name for name, _ in paths]
        record["head"] = current_head()
        record["path_sha256"] = file_hashes(paths)
        if args.action == "snapshot":
            record["result"] = snapshot(config, paths)
            exit_code = 0
        elif args.action == "check":
            checks, exit_code = run_static_check(paths, config)
            record["checks"] = checks
            record["source_unchanged"] = file_hashes(paths) == record["path_sha256"]
            if not record["source_unchanged"]:
                exit_code = 1
                record["errors"].append("Selected source changed during static check")
            record["result"] = (
                "STATIC_CHECKS_ONLY_NOT_PRODUCT_ACCEPTANCE"
                if exit_code == 0
                else "STATIC_CHECK_FAILED_OR_UNAVAILABLE"
            )
        elif args.action == "diff":
            record["result"], exit_code = read_only_diff(paths)
        elif args.action == "format-preview":
            paths = explicit_paths(args.paths, required=True, suffixes=FORMATTABLE)
            record["paths"] = [name for name, _ in paths]
            record["path_sha256"] = file_hashes(paths)
            record["result"], exit_code = format_preview(paths, config)
            if not record["result"]["source_unchanged"]:
                exit_code = 1
                record["errors"].append("Source changed during preview")
        elif args.action == "format-apply":
            paths = explicit_paths(args.paths, required=True, suffixes=FORMATTABLE)
            record["paths"] = [name for name, _ in paths]
            record["path_sha256"] = file_hashes(paths)
            record["repair_authorization"] = (
                "REQUIRES_EXACT_MANIFEST_AND_CURRENT_SHARED_RESERVATION"
            )
            manifest = Path(args.manifest)
            if not manifest.is_absolute():
                manifest = ROOT / manifest
            with controlled_write_lock(receipt_dir):
                record["result"], exit_code = format_apply(
                    paths, args.owner, manifest, config, receipt_dir, receipt_path
                )
            record["repair_authorization"] = record["result"]["authorization"]
            record["recovery"] = record["result"]["recovery"]
            record["path_sha256_after"] = file_hashes(paths)
        elif args.action == "rollback":
            prior_receipt, prior_rel = receipt_file(args.receipt, receipt_dir)
            record["repair_authorization"] = (
                "REQUIRES_SAME_OWNER_HEAD_RESERVATION_AND_EXACT_FORMAT_POSTIMAGES"
            )
            record["source_format_apply_receipt"] = prior_rel
            with controlled_write_lock(receipt_dir):
                record["result"], exit_code = rollback_apply(
                    paths, args.owner, prior_receipt, config, receipt_dir, receipt_path
                )
            record["repair_authorization"] = record["result"]["authorization"]
            record["recovery"] = record["result"]["recovery"]
            record["path_sha256_after"] = file_hashes(paths)
        elif args.action == "locale-preview":
            fixed_paths = [
                normalize_repo_path(relative, allowed_suffixes=STATIC_SUFFIXES)
                for relative in [LOCALE_GENERATOR, *LOCALE_INPUTS, LOCALE_TARGET]
            ]
            record["paths"] = [name for name, _ in fixed_paths]
            record["path_sha256"] = file_hashes(fixed_paths)
            record["result"], exit_code = locale_generator_preview(config)
        elif args.action == "build":
            if config.get("tools", {}).get("build") not in {
                None,
                "website:astro",
                "flutter:web",
            }:
                raise WorkflowError(
                    "Build tool configuration must be a fixed allowlisted selector"
                )
            record["result"], exit_code = build_target(args.target, config, paths)
            record["target"] = args.target
            record["repair_authorization"] = "EXISTING_LOCAL_BUILD_ONLY"
        else:
            raise WorkflowError("Unknown action")
    except WorkflowError as exc:
        exit_code = exc.exit_code
        record["errors"].append(safe_error(str(exc)))
        record["result"] = "FAILED_CLOSED"
        if args.action == "format-apply":
            record["repair_authorization"] = "DENIED_OR_ABORTED"
            record["recovery"] = (
                "DURABLE_INTENT_PRESENT_CHECK_HASHES"
                if receipt_path and receipt_path.is_file()
                else "NO_SOURCE_WRITE_BEFORE_DURABLE_INTENT"
            )
    except Exception as exc:  # noqa: BLE001 -- a bounded receipt is required for unexpected failures.
        exit_code = 2
        record["errors"].append(
            safe_error(type(exc).__name__ + ": unexpected bounded workflow failure")
        )
        record["result"] = "FAILED_CLOSED"
        if args.action == "format-apply":
            record["repair_authorization"] = "DENIED_OR_ABORTED"
            record["recovery"] = (
                "DURABLE_INTENT_PRESENT_CHECK_HASHES"
                if receipt_path and receipt_path.is_file()
                else "NO_SOURCE_WRITE_BEFORE_DURABLE_INTENT"
            )
    finally:
        record["ended_at"] = now_utc()
        record["duration_seconds"] = round(time.monotonic() - start, 3)
        record["exit_code"] = exit_code
        try:
            if record.get("head") is None:
                record["head"] = current_head()
            receipt_dir = safe_receipt_dir(str(receipt_dir))
            if receipt_path is None:
                receipt_store = ensure_private_subdir(receipt_dir, "receipts")
                receipt_path = (
                    receipt_store
                    / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')}-{args.action}-{uuid.uuid4().hex[:8]}.json"
                )
            atomic_receipt(receipt_path, record)
            print(
                json.dumps(
                    {
                        "receipt": receipt_path.relative_to(ROOT).as_posix(),
                        "action": args.action,
                        "exit_code": exit_code,
                    },
                    ensure_ascii=False,
                )
            )
        except Exception as receipt_write_exc:  # noqa: BLE001 -- report receipt failure without leaking paths/config.
            # Do not print configuration, paths, source text or tool output on receipt failure.
            recovery_status = "NOT_APPLICABLE"
            try:
                if (
                    receipt_path is not None
                    and paths
                    and args.action in {"format-apply", "rollback"}
                ):
                    with controlled_write_lock(receipt_dir):
                        intent = (
                            json.loads(receipt_path.read_text("utf-8-sig"))
                            if receipt_path.is_file()
                            and not has_symlink_component(receipt_path)
                            else {}
                        )
                        intent_result = (
                            intent.get("result", {}) if isinstance(intent, dict) else {}
                        )
                        valid_intent = (
                            isinstance(intent, dict)
                            and intent.get("action") == args.action
                            and intent.get("owner") == args.owner
                            and intent.get("head") == current_head()
                            and intent.get("paths")
                            == [relative for relative, _ in paths]
                        )
                        if args.action == "format-apply":
                            rollback_record = (
                                intent_result.get("rollback_record")
                                if isinstance(intent_result, dict)
                                else None
                            )
                            recovery_status = (
                                restore_apply_from_index(
                                    rollback_record, paths, receipt_dir
                                )
                                if valid_intent and isinstance(rollback_record, dict)
                                else "NOT_RESTORED_NO_VALID_DURABLE_INTENT"
                            )
                        else:
                            recovery_index = (
                                intent_result.get("recovery_index")
                                if isinstance(intent_result, dict)
                                else None
                            )
                            recovery_status = (
                                restore_rollback_forward(
                                    recovery_index, paths, receipt_dir
                                )
                                if valid_intent and isinstance(recovery_index, dict)
                                else "NOT_RESTORED_NO_VALID_DURABLE_INTENT"
                            )
            except Exception as recovery_exc:  # noqa: BLE001 -- report uncertainty without risking a broad write.
                recovery_status = (
                    "RECOVERY_NOT_VERIFIED_" + type(recovery_exc).__name__
                )
            if exit_code == 0:
                exit_code = 2
            print(
                json.dumps(
                    {
                        "action": args.action,
                        "exit_code": exit_code,
                        "receipt": "NOT_WRITTEN",
                        "receipt_error": type(receipt_write_exc).__name__,
                        "source_recovery": recovery_status,
                    },
                    ensure_ascii=False,
                )
            )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
