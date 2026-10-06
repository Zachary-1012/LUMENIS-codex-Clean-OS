#!/usr/bin/env python3
"""Check the current LUMENIS origin/main and emit a local sync task.

This helper never chooses a coding model, development agent, product scope or
platform priority. The configured Git origin is the repository authority;
AGENTS.md and CURRENT route all follow-up engineering work.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_BRANCH = "main"
TASK_FILE = Path(".runtime") / "github_upgrade_task.md"
STATE_FILE = Path(".runtime") / "github_upgrade_state.json"


def run_git(repo_dir: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return result.stdout.strip()


def remote_head(repo_dir: Path) -> tuple[str, str]:
    remote_url = run_git(repo_dir, "remote", "get-url", "origin")
    result = subprocess.run(
        ["git", "ls-remote", "--heads", "origin", f"refs/heads/{DEFAULT_BRANCH}"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    fields = result.stdout.strip().split()
    if len(fields) != 2 or fields[1] != f"refs/heads/{DEFAULT_BRANCH}":
        raise RuntimeError("origin/main remote head unavailable")
    return fields[0], remote_url


def task_text(now: str, remote_url: str, local_head: str, remote: str) -> str:
    if local_head == remote:
        return (
            "# LUMENIS main sync check\n\n"
            f"Time: {now}\n"
            f"Repository: origin ({remote_url})\n"
            f"Local HEAD: {local_head}\n"
            f"origin/main: {remote}\n\n"
            "Status: synchronized. Do not modify source merely to create work.\n"
        )
    return (
        "# LUMENIS main sync task\n\n"
        f"Time: {now}\n"
        f"Repository: origin ({remote_url})\n"
        f"Local HEAD: {local_head}\n"
        f"origin/main: {remote}\n\n"
        "Execution rules:\n"
        "1. Resolve fresh origin/main and preserve the complete local working tree.\n"
        "2. Root AGENTS.md is the sole execution router; Product Architecture is the sole product blueprint.\n"
        "3. Do not reset, clean, bulk overwrite, or infer current truth from historical documents.\n"
        "4. Current source/runtime/DB/Permission/Evidence truth has precedence.\n"
        "5. Product context defaults to GLOBAL / ALL; Subject or BrandFocus requires explicit focus.\n"
        "6. CTH/BMP/Shared/SYSTEM and platform work follow their current Owner/Permission contracts; this helper assigns no priority.\n"
        "7. Run affected tests and blocking gates before delivery.\n"
        "8. Push main in the same delivery cycle and fetch again to prove local/online equality.\n\n"
        "Completion requires the active objective, data safety, verification, and Git state to agree with current LUMENIS governance.\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-dir", default=".")
    args = parser.parse_args()

    repo_dir = Path(args.repo_dir).resolve()
    local_head = run_git(repo_dir, "rev-parse", "HEAD")
    remote, remote_url = remote_head(repo_dir)
    now = datetime.now(timezone.utc).isoformat()
    status = "synced" if local_head == remote else "remote_differs"

    task_file = repo_dir / TASK_FILE
    state_file = repo_dir / STATE_FILE
    task_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        task_text(now, remote_url, local_head, remote),
        encoding="utf-8",
    )
    state_file.write_text(
        json.dumps(
            {
                "checked_at": now,
                "local_head": local_head,
                "remote_head": remote,
                "remote_url": remote_url,
                "status": status,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"status={status} local={local_head} remote={remote}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
