# -*- coding: utf-8 -*-
"""LUMENIS Universal Skill source/compatibility boundary.

This module is a source adapter and preflight layer, not a second registry or
an arbitrary-code executor.  It extends the existing ``skills_registry``
owner through account APIs and leaves execution to canonical Shared Agent Skill execution.

Supported source families are explicit.  An unknown URL or package is never
executed.  Preview is read-only: it does not clone, install, import, spawn a
process, grant a permission, or persist a secret.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import unquote, urlparse


SUPPORTED_SOURCE_TYPES = {
    "github", "local", "zip", "skill_md", "mcp_stdio", "mcp_http",
    "python", "node", "http",
}
SUPPORTED_RUNTIMES = {"builtin", "python", "node", "mcp", "http", "unknown"}
PERMISSION_SCOPES = {
    "filesystem.read", "filesystem.write", "network", "specific_domains",
    "database.read", "database.write", "browser", "process", "shell",
    "ai.model", "connector", "export", "publish", "external_action",
}
_GITHUB_RE = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)
_GITHUB_PATH_RE = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)/"
    r"(?P<kind>tree|blob)/(?P<ref>[^/?#]+)/(?P<path>[^?#]+?)/?$",
    re.IGNORECASE,
)
_SKILL_ID_RE = re.compile(r"^[a-z][a-z0-9_.-]{2,63}$")
_AGENT_SKILL_NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
_REVISION_RE = re.compile(r"^[0-9a-f]{7,64}$", re.IGNORECASE)
_MAX_SOURCE_LENGTH = 2048
_MAX_MANIFEST_BYTES = 256 * 1024
_MANIFEST_NAMES = ("skill.json", ".lumenis/skill.json", "manifest.json")
_MARKDOWN_NAMES = ("SKILL.md", "skill.md")


@dataclass(frozen=True)
class SkillSource:
    source: str
    source_type: str
    protocol: str
    locator: str
    supported: bool
    reason: str = ""
    ref: Optional[str] = None
    subpath: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "source_type": self.source_type,
            "protocol": self.protocol,
            "locator": self.locator,
            "supported": self.supported,
            "reason": self.reason,
            "ref": self.ref,
            "subpath": self.subpath,
        }


def _json_value(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return fallback
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return fallback
    return value


def _list_value(value: Any, limit: int = 64) -> List[str]:
    value = _json_value(value, [])
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple, set)):
        return []
    result = []
    for item in list(value)[:limit]:
        if isinstance(item, str) and item.strip():
            result.append(item.strip()[:256])
    return list(dict.fromkeys(result))


def _tool_names(value: Any, limit: int = 64) -> List[str]:
    """Normalize a manifest's string or structured tool declarations."""
    if isinstance(value, (list, tuple)) and value and all(isinstance(item, dict) for item in value):
        return _list_value([item.get("name") for item in value], limit=limit)
    return _list_value(value, limit=limit)


def _manifest_digest(manifest: Dict[str, Any]) -> str:
    payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def detect_source(source: str) -> SkillSource:
    """Classify a source without fetching or executing it."""
    raw = str(source or "").strip()
    if not raw:
        return SkillSource(raw, "unknown", "", "", False, "source is required")
    if len(raw) > _MAX_SOURCE_LENGTH or any(ord(ch) < 32 for ch in raw):
        return SkillSource(raw[:_MAX_SOURCE_LENGTH], "unknown", "", "", False, "source is invalid")

    github = _GITHUB_RE.match(raw)
    if github:
        owner = github.group("owner")
        repo = github.group("repo")
        locator = f"github.com/{owner}/{repo}"
        return SkillSource(raw, "github", "git", locator, True, "remote source requires pinned ref")

    github_path = _GITHUB_PATH_RE.match(raw)
    if github_path:
        owner = github_path.group("owner")
        repo = github_path.group("repo")
        ref = unquote(github_path.group("ref"))
        subpath = unquote(github_path.group("path")).strip("/")
        segments = subpath.split("/") if subpath else []
        if not subpath or any(part in ("", ".", "..") for part in segments):
            return SkillSource(raw, "unknown", "git", raw, False,
                               "GitHub Skill path is invalid")
        if github_path.group("kind").lower() == "blob" and segments[-1].lower() not in {
            "skill.md", "skill.json", "manifest.json",
        }:
            return SkillSource(raw, "unknown", "git", raw, False,
                               "GitHub file source must point to a Skill manifest")
        locator = f"github.com/{owner}/{repo}"
        return SkillSource(raw, "github", "git", locator, True,
                           "remote Skill path requires pinned ref and manifest fetch",
                           ref=ref, subpath=subpath)

    parsed = urlparse(raw)
    if parsed.scheme in ("mcp+stdio", "mcp-stdio"):
        return SkillSource(raw, "mcp_stdio", "mcp", parsed.path or parsed.netloc, True,
                           "process remains blocked until permission and isolation gates")
    if parsed.scheme in ("mcp", "mcp+http", "mcp-http"):
        return SkillSource(raw, "mcp_http", "mcp", parsed.geturl(), True,
                           "network transport remains blocked until domain approval")
    if parsed.scheme in ("http", "https"):
        return SkillSource(raw, "http", "http", parsed.geturl(), True,
                           "HTTP adapter requires allowlisted domain and permission")
    if parsed.scheme and len(parsed.scheme) > 1:
        return SkillSource(raw, "unknown", parsed.scheme, raw, False, "unsupported source protocol")

    path = Path(raw)
    try:
        if path.is_dir():
            return SkillSource(raw, "local", "filesystem", str(path), True,
                               "local package is untrusted until manifest/security checks")
        if path.is_file() and path.suffix.lower() == ".zip":
            return SkillSource(raw, "zip", "filesystem", str(path), True,
                               "zip package is inspected without extraction")
        if path.is_file() and path.name.lower() == "skill.md":
            return SkillSource(raw, "skill_md", "filesystem", str(path), True,
                               "SKILL.md is validated without execution")
    except OSError as exc:
        return SkillSource(raw, "unknown", "filesystem", raw, False, f"source cannot be inspected: {exc}")
    return SkillSource(raw, "unknown", "filesystem", raw, False, "source path does not exist")


def _parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if value.startswith(("[", "{")):
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    if value.lower() in ("null", "none"):
        return None
    return value.strip("\"'")


def _parse_skill_markdown(text: str) -> Dict[str, Any]:
    """Read optional front matter and safe headings; never interpret prose."""
    text = text[:_MAX_MANIFEST_BYTES]
    manifest: Dict[str, Any] = {}
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        end = next((i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"), None)
        if end is not None:
            for line in lines[1:end]:
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                key = key.strip().lower().replace("-", "_")
                if re.match(r"^[a-z_][a-z0-9_]{0,63}$", key):
                    manifest[key] = _parse_scalar(value)
            lines = lines[end + 1:]
    if not manifest:
        for line in lines[:80]:
            match = re.match(
                r"^\s*(?:skill_id|id|name|description|version|runtime|entrypoint)\s*:\s*(.+)$",
                line, re.I,
            )
            if match:
                key = line.split(":", 1)[0].strip().lower().replace("-", "_")
                manifest[key] = _parse_scalar(match.group(1))
    if "name" not in manifest:
        for line in lines:
            heading = re.match(r"^#\s+(.+?)\s*$", line)
            if heading:
                manifest["name"] = heading.group(1)[:256]
                break
    return manifest


def _read_local_manifest(source: SkillSource) -> Tuple[Optional[Dict[str, Any]], str]:
    path = Path(source.locator)
    if source.source_type == "skill_md":
        try:
            if not path.is_file():
                return None, "SKILL.md not found"
            if path.stat().st_size > _MAX_MANIFEST_BYTES:
                return None, "manifest exceeds size limit"
            return _parse_skill_markdown(path.read_text(encoding="utf-8", errors="replace")), path.name
        except OSError:
            return None, "SKILL.md unreadable"
    if source.source_type == "zip":
        try:
            with zipfile.ZipFile(path) as archive:
                names = {}
                for raw_name in archive.namelist():
                    normalized = raw_name.replace("\\", "/")
                    while normalized.startswith("./"):
                        normalized = normalized[2:]
                    parts = normalized.split("/")
                    if not normalized or "\x00" in normalized or any(part == ".." for part in parts):
                        # A manifest inside a traversal path is never a valid
                        # package root, even though this preflight never extracts it.
                        continue
                    names[normalized] = raw_name

                def _find_entry(candidates: Tuple[str, ...]) -> Optional[str]:
                    for candidate in candidates:
                        if candidate in names:
                            return candidate
                    # Common distribution shape: package-name/<manifest>.  Only
                    # one directory level is accepted; nothing is extracted.
                    for name in names:
                        if name.count("/") == 1 and name.split("/", 1)[1] in candidates:
                            return name
                    return None

                manifest_entry = _find_entry(_MANIFEST_NAMES)
                if manifest_entry:
                    data = archive.read(names[manifest_entry])
                    if len(data) > _MAX_MANIFEST_BYTES:
                        return None, "manifest exceeds size limit"
                    return json.loads(data.decode("utf-8")), manifest_entry
                markdown_entry = _find_entry(_MARKDOWN_NAMES)
                if markdown_entry:
                    data = archive.read(names[markdown_entry])
                    if len(data) > _MAX_MANIFEST_BYTES:
                        return None, "manifest exceeds size limit"
                    return _parse_skill_markdown(data.decode("utf-8", "replace")), markdown_entry
        except (OSError, zipfile.BadZipFile, KeyError, UnicodeError, json.JSONDecodeError) as exc:
            return None, f"package manifest unreadable: {type(exc).__name__}"
        return None, "manifest not found"

    candidates = [path / name for name in _MANIFEST_NAMES]
    for candidate in candidates:
        try:
            if candidate.is_file():
                if candidate.stat().st_size > _MAX_MANIFEST_BYTES:
                    return None, "manifest exceeds size limit"
                return json.loads(candidate.read_text(encoding="utf-8")), str(candidate.relative_to(path))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None, "manifest unreadable"
    for candidate in [path / name for name in _MARKDOWN_NAMES]:
        try:
            if candidate.is_file():
                return _parse_skill_markdown(candidate.read_text(encoding="utf-8", errors="replace")), candidate.name
        except OSError:
            return None, "SKILL.md unreadable"
    return None, "manifest not found"


def validate_manifest(manifest: Dict[str, Any], *, standard_skill_md: bool = False) -> Dict[str, Any]:
    if not isinstance(manifest, dict):
        return {"valid": False, "errors": ["manifest must be an object"], "warnings": []}
    errors: List[str] = []
    warnings: List[str] = []
    skill_id = str(manifest.get("skill_id") or manifest.get("id") or "").strip()
    name = str(manifest.get("name") or "").strip()
    version = str(manifest.get("version") or "").strip()
    if standard_skill_md:
        if not name or not _AGENT_SKILL_NAME_RE.match(name) or "--" in name:
            errors.append("SKILL.md name must be lowercase hyphenated and 1-64 characters")
        if not skill_id:
            skill_id = name
        if skill_id and not _AGENT_SKILL_NAME_RE.match(skill_id):
            errors.append("SKILL.md skill_id must match its lowercase hyphenated name")
        if not str(manifest.get("description") or "").strip():
            errors.append("SKILL.md description is required")
    elif not skill_id:
        # The authored TrendHub manifest uses the standard package ``name``
        # without a second LUMENIS-specific id field.  Derive only when the
        # name is already a valid stable id; never slugify or guess from prose.
        derived_id = name.lower()
        if _SKILL_ID_RE.match(derived_id):
            skill_id = derived_id
            warnings.append("skill_id is absent; derived from manifest name")
        else:
            errors.append("skill_id must match ^[a-z][a-z0-9_.-]{2,63}$")
    elif not _SKILL_ID_RE.match(skill_id):
        errors.append("skill_id must match ^[a-z][a-z0-9_.-]{2,63}$")
    if not name:
        errors.append("name is required")
    if not version and standard_skill_md:
        version = "0.0.0"
        warnings.append("SKILL.md does not declare a version; source revision/digest is the pin")
    elif not re.match(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$", version):
        errors.append("version must be semver-like")
    runtime_descriptor = manifest.get("runtime") if isinstance(manifest.get("runtime"), dict) else {}
    runtime_value = runtime_descriptor.get("type") if runtime_descriptor else manifest.get("runtime")
    runtime = str(runtime_value or "unknown").strip().lower()
    if runtime == "local-mcp-plugin":
        runtime = "mcp"
    if runtime not in SUPPORTED_RUNTIMES:
        warnings.append(f"runtime '{runtime}' needs an explicit adapter")
    permissions = _list_value(
        manifest.get("permissions_requested", manifest.get("permissions", [])), limit=32
    )
    unsupported = sorted(set(permissions) - PERMISSION_SCOPES)
    if unsupported:
        errors.append(f"unsupported permission scopes: {unsupported}")
    entrypoint = str(manifest.get("entrypoint") or "").strip()
    if not entrypoint and runtime == "mcp":
        transports = runtime_descriptor.get("transports") if runtime_descriptor else None
        transport = next(
            (
                item for item in (transports if isinstance(transports, list) else [])
                if isinstance(item, dict) and item.get("id") == "stdio"
                and item.get("default", True) is True
            ),
            None,
        )
        install_mcp = (manifest.get("aiInstall") or {}).get("mcpStdio")
        declared = transport or (install_mcp if isinstance(install_mcp, dict) else None)
        if isinstance(declared, dict) and declared.get("command"):
            entrypoint = json.dumps(
                {"command": str(declared["command"]), "args": _list_value(declared.get("args", []), 16)},
                ensure_ascii=False,
                sort_keys=True,
            )
            warnings.append("entrypoint derived from declared MCP stdio transport")
    if not entrypoint and runtime not in ("builtin", "unknown"):
        warnings.append("entrypoint is not declared; install/invoke remains blocked")
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "normalized": {
            "skill_id": skill_id,
            "name": name,
            "description": str(manifest.get("description") or "")[:2000],
            "version": version,
            "runtime": runtime,
            "entrypoint": entrypoint[:512],
            "capabilities": _list_value(manifest.get("capabilities", [])),
            "tools": _tool_names(manifest.get("tools", [])),
            "permissions_requested": permissions,
            "secrets_required": _list_value(manifest.get("secrets_required", []), limit=32),
            "dependencies": _list_value(manifest.get("dependencies", []), limit=64),
            "input_schema": _json_value(manifest.get("input_schema"), {}),
            "output_schema": _json_value(manifest.get("output_schema"), {}),
        },
    }


def preview_skill_source(source: str, *, resolve_remote: bool = False,
                         fetch_remote_manifest: bool = False,
                         git_executable: str = "git",
                         timeout: float = 30.0) -> Dict[str, Any]:
    """Return a non-mutating, non-executing installation preflight."""
    detected = detect_source(source)
    result: Dict[str, Any] = {
        "ok": detected.supported,
        "state": "DETECTED" if detected.supported else "BLOCKED",
        "source": detected.to_dict(),
        "manifest_state": "NOT_FETCHED",
        "manifest": None,
        "validation": {"valid": False, "errors": [], "warnings": []},
        "compatibility": {
            "supported_source_type": detected.source_type in SUPPORTED_SOURCE_TYPES,
            "supported_runtime": False,
            "adapter": detected.protocol or detected.source_type,
        },
        "security": {
            "trust": "UNVERIFIED",
            "policy": "DENY_BY_DEFAULT",
            "permissions_requested": [],
            "permissions_granted": [],
            "secrets_injected": False,
            "execution": "BLOCKED_UNTIL_INSTALL_PERMISSION_AND_SELFTEST",
        },
        "ownership": {
            "registry": "account.models.skills_registry",
            "execution": "lumenis.shared.agents.skills.execution",
            "evidence": "lumenis.shared.evidence",
            "permission": "lumenis.system.security",
        },
        "registration": {
            "allowed": False,
            "status": "VALIDATION_REQUIRED",
            "reason": "registration never grants permissions or installs code",
        },
        "lifecycle": [
            "SOURCE", "DISCOVER", "DETECT", "PARSE", "VALIDATE", "COMPATIBILITY",
            "SECURITY", "PERMISSION_PREVIEW", "DEPENDENCY_RESOLUTION", "INSTALL",
            "BUILD", "SELFTEST", "HEALTHCHECK", "REGISTER", "ENABLE", "AVAILABLE",
        ],
        "digest": "",
        "revision": None,
        "errors": [],
    }
    if not detected.supported:
        result["errors"].append(detected.reason)
        return result

    if detected.source_type in ("mcp_stdio", "mcp_http"):
        result["state"] = "MCP_DISCOVERY_REQUIRED"
        result["manifest_state"] = "DISCOVERY_REQUIRED"
        result["registration"] = {
            "allowed": False,
            "status": "REQUIRES_DISCOVERY_AND_APPROVAL",
            "reason": "MCP registration requires server capability discovery, allowlist, permission approval and self-test",
        }
        result["errors"].append(
            "MCP is a transport; no server is registered until discovery and human approval complete"
        )
        return result

    if detected.source_type in ("local", "zip", "skill_md"):
        manifest, manifest_name = _read_local_manifest(detected)
        if manifest is None:
            result["manifest_state"] = "MISSING"
            result["state"] = "BLOCKED"
            result["registration"] = {
                "allowed": False,
                "status": "MANIFEST_REQUIRED",
                "reason": "a valid Skill manifest is required before registration",
            }
            result["errors"].append(manifest_name)
            return result
        result["manifest_state"] = "PARSED"
        standard_skill_md = manifest_name.lower().endswith("skill.md")
        result["manifest"] = {
            "name": manifest_name,
            "format": "agentskills" if standard_skill_md else "lumenis-json",
        }
        validation = validate_manifest(manifest, standard_skill_md=standard_skill_md)
        result["validation"] = validation
        normalized = validation.get("normalized") or {}
        result["security"]["permissions_requested"] = normalized.get("permissions_requested", [])
        result["compatibility"]["supported_runtime"] = normalized.get("runtime") in SUPPORTED_RUNTIMES
        result["digest"] = _manifest_digest(manifest)
        if validation["valid"] and result["compatibility"]["supported_runtime"]:
            result["state"] = "VALIDATED"
            result["registration"] = {
                "allowed": True,
                "status": "VALIDATED_METADATA_ONLY",
                "reason": "can be registered disabled; install/execute still require separate gates",
            }
        else:
            result["state"] = "BLOCKED"
        return result

    if detected.source_type == "github" and resolve_remote:
        try:
            result["revision"] = resolve_github_revision(detected.source, git_executable=git_executable)
            result["state"] = "REMOTE_RESOLVED"
            if fetch_remote_manifest:
                remote = fetch_github_manifest(
                    detected,
                    revision=result["revision"],
                    git_executable=git_executable,
                    timeout=timeout,
                )
                result["remote_manifest"] = remote
                if remote["state"] != "VALIDATED":
                    result["state"] = "BLOCKED"
                    result["manifest_state"] = remote["state"]
                    result["errors"].append(remote.get("reason", "remote manifest unavailable"))
                else:
                    result["manifest_state"] = "PARSED"
                    result["manifest"] = {
                        "name": remote["path"],
                        "path": remote["path"],
                        "format": remote["format"],
                    }
                    result["validation"] = remote["validation"]
                    normalized = remote["validation"].get("normalized") or {}
                    result["security"]["permissions_requested"] = normalized.get(
                        "permissions_requested", []
                    )
                    result["compatibility"]["supported_runtime"] = (
                        normalized.get("runtime") in SUPPORTED_RUNTIMES
                    )
                    result["digest"] = remote["digest"]
                    if remote["validation"].get("valid") and result["compatibility"]["supported_runtime"]:
                        result["state"] = "REMOTE_VALIDATED"
                        result["registration"] = {
                            "allowed": True,
                            "status": "VALIDATED_METADATA_ONLY",
                            "reason": "remote manifest is pinned and validated; install/execute still require separate gates",
                        }
                    else:
                        result["state"] = "BLOCKED"
        except SkillSourceError as exc:
            result["errors"].append(str(exc))
            result["state"] = "BLOCKED"
    return result


class SkillSourceError(RuntimeError):
    pass


def _run_remote_git(git_executable: str, args: List[str], cwd: Path,
                    timeout: float) -> str:
    """Run a read-only Git inspection command in a disposable directory.

    The command is deliberately constrained to repository initialization,
    remote fetch of one already-resolved commit, tree listing and blob read.
    It never checks out files, runs hooks, installs dependencies or executes
    repository content.  Credentials are not read from the LUMENIS database.
    """
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    try:
        completed = subprocess.run(
            [git_executable, *args],
            cwd=str(cwd),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SkillSourceError(f"remote manifest inspection unavailable: {type(exc).__name__}") from exc
    if completed.returncode != 0:
        raise SkillSourceError("remote manifest inspection failed")
    return completed.stdout


def _remote_manifest_candidates(tree: str, subpath: Optional[str]) -> List[str]:
    names = [line.strip().replace("\\", "/") for line in tree.splitlines() if line.strip()]
    if len(names) > 20000:
        raise SkillSourceError("remote repository tree exceeds inspection limit")
    names = [name for name in names if "\x00" not in name and not any(
        part in ("", ".", "..") for part in name.split("/")
    )]
    json_names = {name.lower() for name in _MANIFEST_NAMES}
    markdown_names = {name.lower() for name in _MARKDOWN_NAMES}
    prefix = (subpath or "").strip("/")
    if prefix:
        scoped = [
            name for name in names
            if name.lower().startswith(f"{prefix.lower()}/")
            and name[len(prefix) + 1:].lower() in json_names | markdown_names
        ]
    else:
        # A repository root can contain several independent Skills.  Only an
        # exact root manifest is auto-selectable; nested candidates are shown
        # to the caller instead of guessing which product to register.
        scoped = [
            name for name in names
            if "/" not in name and name.lower() in json_names | markdown_names
        ]
    # Match the local manifest reader: an explicit JSON manifest wins over a
    # co-located SKILL.md.  This avoids treating a package's documentation as
    # a second Skill when both files are intentionally present.
    json_candidates = [
        name for name in scoped
        if (name[len(prefix) + 1:] if prefix else name).lower() in json_names
    ]
    candidates = json_candidates or [
        name for name in scoped
        if (name[len(prefix) + 1:] if prefix else name).lower() in markdown_names
    ]
    return sorted(dict.fromkeys(candidates))


def fetch_github_manifest(detected: SkillSource, *, revision: str,
                          git_executable: str = "git",
                          timeout: float = 30.0) -> Dict[str, Any]:
    """Fetch and validate one GitHub manifest at an exact commit.

    This is a metadata-only operation used by source preview.  It is not an
    installer: repository files stay in a temporary directory and are never
    imported, built, or executed.  A repository with multiple nested Skills
    must provide a GitHub ``tree/<ref>/<skill-path>`` source so selection is
    explicit.
    """
    if detected.source_type != "github" or not _REVISION_RE.fullmatch(str(revision or "")):
        raise SkillSourceError("remote manifest inspection requires an exact Git revision")
    remote = f"https://{detected.locator}"
    with tempfile.TemporaryDirectory(prefix="lumenis-skill-preview-") as temp_dir:
        worktree = Path(temp_dir)
        _run_remote_git(git_executable, ["init", "--quiet"], worktree, timeout)
        _run_remote_git(git_executable, ["remote", "add", "origin", remote], worktree, timeout)
        _run_remote_git(
            git_executable,
            ["fetch", "--quiet", "--depth=1", "--no-tags", "origin", revision],
            worktree,
            timeout,
        )
        tree = _run_remote_git(
            git_executable,
            ["ls-tree", "-r", "--name-only", "FETCH_HEAD"],
            worktree,
            timeout,
        )
        candidates = _remote_manifest_candidates(tree, detected.subpath)
        if len(candidates) != 1:
            reason = "remote manifest not found" if not candidates else "remote manifest selection is ambiguous"
            return {
                "state": "MISSING" if not candidates else "AMBIGUOUS",
                "reason": reason,
                "path": None,
                "candidates": candidates[:32],
                "format": None,
                "validation": {"valid": False, "errors": [reason], "warnings": []},
                "digest": "",
            }
        manifest_path = candidates[0]
        raw = _run_remote_git(
            git_executable,
            ["show", f"FETCH_HEAD:{manifest_path}"],
            worktree,
            timeout,
        )
        raw = raw or ""
        if len(raw.encode("utf-8", errors="replace")) > _MAX_MANIFEST_BYTES:
            reason = "remote manifest exceeds size limit"
            return {
                "state": "BLOCKED", "reason": reason, "path": manifest_path,
                "candidates": candidates, "format": None,
                "validation": {"valid": False, "errors": [reason], "warnings": []},
                "digest": "",
            }
        standard_skill_md = manifest_path.lower().endswith("skill.md")
        try:
            manifest = (_parse_skill_markdown(raw) if standard_skill_md else json.loads(raw))
        except (TypeError, ValueError, json.JSONDecodeError):
            reason = "remote manifest is not valid JSON or SKILL.md front matter"
            return {
                "state": "BLOCKED", "reason": reason, "path": manifest_path,
                "candidates": candidates, "format": "agentskills" if standard_skill_md else "lumenis-json",
                "validation": {"valid": False, "errors": [reason], "warnings": []},
                "digest": "",
            }
        validation = validate_manifest(manifest, standard_skill_md=standard_skill_md)
        return {
            "state": "VALIDATED" if validation.get("valid") else "BLOCKED",
            "reason": "" if validation.get("valid") else "remote manifest validation failed",
            "path": manifest_path,
            "candidates": candidates,
            "format": "agentskills" if standard_skill_md else "lumenis-json",
            "validation": validation,
            "digest": _manifest_digest(manifest),
        }


def resolve_github_revision(source: str, *, git_executable: str = "git", timeout: float = 15.0) -> str:
    """Resolve an exact GitHub ref without cloning or changing the repo."""
    detected = detect_source(source)
    if detected.source_type != "github":
        raise SkillSourceError("source is not a GitHub repository URL")
    # A tree/blob URL may already carry an exact commit SHA.  ``git
    # ls-remote <remote> <sha>`` is not a reliable existence query because
    # ls-remote advertises refs, not arbitrary object IDs.  Preserve the
    # pinned revision here; fetch_github_manifest() performs the authoritative
    # object and manifest validation at that exact revision.
    if detected.ref and _REVISION_RE.fullmatch(detected.ref):
        return detected.ref.lower()
    try:
        # Do not pass --refs here: Git documents that --refs hides symbolic
        # refs, while the remote default HEAD is commonly advertised as one.
        remote = detected.source
        ref = "HEAD"
        if detected.ref:
            remote = f"https://{detected.locator}"
            ref = detected.ref
        completed = None
        for attempt in range(2):
            completed = subprocess.run(
                [git_executable, "ls-remote", remote, ref],
                check=False, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=timeout,
            )
            if completed.returncode == 0:
                break
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SkillSourceError(f"GitHub ref resolution unavailable: {type(exc).__name__}") from exc
    if completed is None or completed.returncode != 0:
        raise SkillSourceError("GitHub ref resolution failed")
    for line in completed.stdout.splitlines():
        fields = line.split()
        if fields and _REVISION_RE.match(fields[0]):
            return fields[0].lower()
    raise SkillSourceError("GitHub HEAD did not return a commit revision")
