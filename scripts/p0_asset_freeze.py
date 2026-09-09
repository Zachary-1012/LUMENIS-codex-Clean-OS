"""Create a read-only LUMENIS P0-A asset manifest and recoverable DB backups.

The output directory must live outside the repository. Source SQLite databases
are opened in read-only mode and copied with SQLite's online backup API.
No credential values or file contents are written to the manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
ENV_KEY = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def iter_files(root: Path) -> Iterable[Path]:
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS)
        current_path = Path(current)
        for name in sorted(files):
            yield current_path / name


def env_key_names(root: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for path in iter_files(root):
        if not (path.name == ".env" or path.name.startswith(".env.")):
            continue
        keys: set[str] = set()
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                match = ENV_KEY.match(line)
                if match:
                    keys.add(match.group(1))
        except OSError:
            continue
        result[path.relative_to(root).as_posix()] = sorted(keys)
    return result


def file_inventory(root: Path) -> tuple[list[dict[str, Any]], str]:
    records: list[dict[str, Any]] = []
    aggregate = hashlib.sha256()
    for path in iter_files(root):
        try:
            stat = path.stat()
            digest = sha256_file(path)
        except OSError as exc:
            records.append(
                {"path": path.relative_to(root).as_posix(), "error": type(exc).__name__}
            )
            continue
        record = {
            "path": path.relative_to(root).as_posix(),
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": digest,
        }
        records.append(record)
        aggregate.update(
            f"{record['path']}\0{record['size']}\0{record['sha256']}\n".encode("utf-8")
        )
    return records, aggregate.hexdigest()


def source_manifest(asset: dict[str, str]) -> dict[str, Any]:
    root = Path(asset["path"]).resolve()
    if not root.is_dir():
        return {**asset, "exists": False}
    files, filesystem_digest = file_inventory(root)
    is_git = (root / ".git").exists()
    status = run_git(root, "status", "--porcelain=v1", "--untracked-files=all") if is_git else None
    return {
        **asset,
        "exists": True,
        "resolved_path": str(root),
        "is_git": is_git,
        "git_head": run_git(root, "rev-parse", "HEAD") if is_git else None,
        "git_tree": run_git(root, "rev-parse", "HEAD^{tree}") if is_git else None,
        "git_remote": run_git(root, "remote", "get-url", "origin") if is_git else None,
        "git_status_lines": status.splitlines() if status else [],
        "file_count": len(files),
        "filesystem_digest": filesystem_digest,
        "config_key_names": env_key_names(root),
        "files": files,
    }


def sqlite_summary(path: Path) -> dict[str, Any]:
    uri = f"file:{path.as_posix()}?mode=ro"
    result: dict[str, Any] = {
        "source": str(path.resolve()),
        "size": path.stat().st_size,
        "sha256": sha256_file(path),
    }
    connection = sqlite3.connect(uri, uri=True, timeout=15)
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchall()
        fk_rows = connection.execute("PRAGMA foreign_key_check").fetchall()
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        counts: dict[str, int | str] = {}
        schemas: dict[str, str] = {}
        for table in tables:
            escaped = table.replace('"', '""')
            try:
                counts[table] = int(
                    connection.execute(f'SELECT COUNT(*) FROM "{escaped}"').fetchone()[0]
                )
            except sqlite3.DatabaseError as exc:
                counts[table] = f"ERROR:{type(exc).__name__}"
            row = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            schemas[table] = row[0] if row and row[0] else ""
        result.update(
            {
                "integrity": [row[0] for row in integrity],
                "foreign_key_violation_count": len(fk_rows),
                "foreign_key_violation_sample": [list(row) for row in fk_rows[:20]],
                "table_count": len(tables),
                "table_counts": counts,
                "schema": schemas,
            }
        )
    finally:
        connection.close()
    return result


def backup_sqlite(source: Path, destination: Path) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_uri = f"file:{source.as_posix()}?mode=ro"
    src = sqlite3.connect(source_uri, uri=True, timeout=30)
    dst = sqlite3.connect(destination)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    verify = sqlite3.connect(f"file:{destination.as_posix()}?mode=ro", uri=True)
    try:
        integrity = verify.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        verify.close()
    for suffix in ("-shm", "-wal"):
        sidecar = Path(f"{destination}{suffix}")
        if sidecar.exists():
            sidecar.unlink()
    return {
        "destination": str(destination.resolve()),
        "size": destination.stat().st_size,
        "sha256": sha256_file(destination),
        "integrity": integrity,
    }


def runtime_snapshot() -> dict[str, Any]:
    if os.name != "nt":
        return {"supported": False, "reason": "Windows-only snapshot"}
    ps = (
        "$p=Get-CimInstance Win32_Process | Where-Object {"
        "$_.CommandLine -match 'Z-Brand-Core|Taikoo-monitor-new|8201|8202|ollama|opencode'};"
        "$p | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine,CreationDate | ConvertTo-Json -Depth 4"
    )
    ports = (
        "$c=Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | "
        "Where-Object {$_.LocalPort -in 8201,8202,9222,11434};"
        "$c | Select-Object LocalAddress,LocalPort,OwningProcess,State | ConvertTo-Json -Depth 3"
    )
    return {
        "supported": True,
        "processes": json.loads(subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps], capture_output=True,
            text=True, encoding="utf-8", errors="replace"
        ).stdout or "[]"),
        "listeners": json.loads(subprocess.run(
            ["powershell", "-NoProfile", "-Command", ports], capture_output=True,
            text=True, encoding="utf-8", errors="replace"
        ).stdout or "[]"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    output = args.output.resolve()
    repo = Path(__file__).resolve().parents[1]
    if output == repo or repo in output.parents:
        parser.error("--output must be outside the repository")
    if output.exists() and any(output.iterdir()):
        parser.error("--output must be a new or empty directory")
    output.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "generator": str(Path(__file__).resolve()),
        "sources": [],
        "databases": [],
        "runtime": runtime_snapshot(),
    }
    for asset in config["assets"]:
        manifest["sources"].append(source_manifest(asset))
    for index, value in enumerate(config["database_candidates"], start=1):
        source = Path(value).resolve()
        if not source.is_file():
            manifest["databases"].append({"source": str(source), "exists": False})
            continue
        summary = sqlite_summary(source)
        backup_name = f"{index:02d}-{source.parent.parent.name}-{source.name}"
        summary["backup"] = backup_sqlite(source, output / "database_backups" / backup_name)
        summary["exists"] = True
        manifest["databases"].append(summary)

    manifest_path = output / "P0A_FULL_ASSET_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    checksum_path = output / "SHA256SUMS.txt"
    backup_files = sorted((output / "database_backups").glob("*"))
    lines = [f"{sha256_file(path)}  {path.relative_to(output).as_posix()}" for path in backup_files]
    lines.append(f"{sha256_file(manifest_path)}  {manifest_path.name}")
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "manifest": str(manifest_path),
        "checksums": str(checksum_path),
        "sources": len(manifest["sources"]),
        "databases": len(manifest["databases"]),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
