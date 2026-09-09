# -*- coding: utf-8 -*-
"""Build an immutable LUMENIS release manifest from a clean Git tree.

The output is a build artifact and should not be committed back into the source
tree.  Runtime verification consumes it through LUMENIS_RELEASE_MANIFEST.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    return result.stdout.strip()


def build_manifest(release_id: str, product_mode: str, profile_id: str = "") -> dict:
    dirty = _git("status", "--porcelain", "--untracked-files=no")
    if dirty:
        raise RuntimeError("tracked working tree is dirty; commit or revert before building a release manifest")
    return {
        "schema_version": "lumenis.release-manifest.v1",
        "release_id": release_id,
        "core_commit": _git("rev-parse", "HEAD"),
        "source_tree_digest": _git("rev-parse", "HEAD^{tree}"),
        "product_mode": product_mode,
        "profile_id": profile_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-id", required=True)
    parser.add_argument(
        "--product-mode",
        required=True,
        choices=("CUSTOMER_RELEASE", "ZBRAND_PLATFORM"),
    )
    parser.add_argument("--profile-id", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output = Path(args.output).resolve()
    if ROOT == output or ROOT in output.parents:
        raise RuntimeError("release manifest must be written outside the source tree")
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build_manifest(args.release_id, args.product_mode, args.profile_id)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"written": True, "release_id": payload["release_id"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
