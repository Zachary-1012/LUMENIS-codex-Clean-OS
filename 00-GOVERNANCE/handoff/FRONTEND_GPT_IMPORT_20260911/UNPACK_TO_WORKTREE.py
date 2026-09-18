#!/usr/bin/env python3
"""Expand the curated LUMENIS Experience V2 + ChatGPT handoff into normal repo paths.

Safety: verifies payload SHA-256, rejects path traversal, refuses conflicting overwrites,
and performs JSON/Python parse validation after extraction. No DB/runtime writes.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile

EXPECTED_SHA256 = "1f916070e27e5e9a230cca69e4f6ce3901118ddf53be106afde1afe9d6dfc6ff"
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PARTS = sorted((HERE / "payload").glob("payload.part*.b64"))


def die(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def safe_target(name: str) -> Path:
    target = (REPO / name).resolve()
    repo = REPO.resolve()
    if target != repo and repo not in target.parents:
        die(f"path traversal rejected: {name}")
    return target


def load_payload() -> bytes:
    if not PARTS:
        die("payload parts not found")
    encoded = "".join(p.read_text(encoding="ascii").strip() for p in PARTS)
    raw = base64.b64decode(encoded, validate=True)
    actual = hashlib.sha256(raw).hexdigest()
    if actual != EXPECTED_SHA256:
        die(f"payload sha256 mismatch: {actual}")
    return raw


def extract(raw: bytes, force: bool) -> list[Path]:
    written: list[Path] = []
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tf:
        members = [m for m in tf.getmembers() if m.isfile()]
        for m in members:
            target = safe_target(m.name)
            src = tf.extractfile(m)
            if src is None:
                die(f"cannot read payload member: {m.name}")
            data = src.read()
            if target.exists():
                old = target.read_bytes()
                if old == data:
                    continue
                if not force:
                    die(f"conflicting existing file (use --force only after audit): {target.relative_to(REPO)}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            written.append(target)
    return written


def validate() -> None:
    errors: list[str] = []
    json_count = py_count = 0
    for p in REPO.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(REPO).as_posix()
        if not (rel.startswith("experience_v2/") or rel.startswith("00-GOVERNANCE/handoff/CHATGPT_COMPLIANCE_20260911/") or rel.startswith("08-AUDIT/LEGACY-DELIVERY-EVIDENCE/2026-09-11/")):
            continue
        if p.suffix.lower() == ".json":
            json_count += 1
            try:
                json.loads(p.read_text(encoding="utf-8-sig"))
            except Exception as exc:
                errors.append(f"JSON {rel}: {exc}")
        elif p.suffix.lower() == ".py":
            py_count += 1
            try:
                compile(p.read_text(encoding="utf-8"), rel, "exec")
            except Exception as exc:
                errors.append(f"PY {rel}: {exc}")
    if errors:
        die("validation failed:\n" + "\n".join(errors[:30]))
    print(f"VALIDATION PASS: json={json_count}, python={py_count}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="replace audited conflicting files; default is fail-closed")
    args = ap.parse_args()
    raw = load_payload()
    print(f"PAYLOAD VERIFIED: sha256={EXPECTED_SHA256} bytes={len(raw)} parts={len(PARTS)}")
    written = extract(raw, args.force)
    validate()
    print(f"EXTRACTED/UPDATED: {len(written)} files")
    print("NEXT: read 00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-READ-FIRST-20260911.md")
    print("THEN: calibrate AI-01 + CTH-01 before broad 44-screen propagation")


if __name__ == "__main__":
    main()
