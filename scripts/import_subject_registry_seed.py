"""Import the reviewed Subject/BrandFocus seed through the existing registry path.

The seed lives in ``scripts/data_candidates/subject_registry_seed_20261013.jsonl``
with a manifest that pins its SHA-256. Every row is written only through
``subject_registry.add_subject`` so identity, normalization, deduplication and
the ``configured`` status remain owned by the canonical registry. Re-running is
idempotent: existing identities are reported, never duplicated or rewritten.
Default mode is a dry run; pass ``--apply`` to write. ``--apply`` is a HIGH
risk ``CONFIG_MODIFY`` on the same resource as ``POST /api/settings/subjects``
and is refused unless the existing PermissionGate allows it with an exact human
approval; the CLI never grants or fakes an approval itself.

Venue/tenant relations are intentionally not imported here: TENANT_OF claims
require captured, verified Evidence (see
``lumenis/shared/database/entity_relations.py``).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SEED_DIR = ROOT / "scripts" / "data_candidates"
SEED_PATH = SEED_DIR / "subject_registry_seed_20261013.jsonl"
MANIFEST_PATH = SEED_DIR / "subject_registry_seed_20261013.manifest.json"
REGISTRY_FIELDS = ("domain_id", "subject_type", "name_en", "name_zh", "industry", "keywords")


APPROVAL_RESOURCE = "/api/settings/subjects"
APPROVAL_CALLER = "scripts/import_subject_registry_seed.py"


class SeedIntegrityError(ValueError):
    """Seed file does not match its pinned manifest."""


class SeedApprovalRequired(PermissionError):
    """--apply was requested without an exact CONFIG_MODIFY approval."""


def require_apply_approval(gate: Any = None) -> None:
    """Reuse the registry write route's Permission/Approval boundary."""
    from lumenis.system.security import OperationType, RiskLevel
    from lumenis.system.security.permission import get_permission_gate

    gate = gate if gate is not None else get_permission_gate()
    result = gate.check(
        OperationType.CONFIG_MODIFY,
        resource=APPROVAL_RESOURCE,
        risk_level=RiskLevel.HIGH,
        caller=APPROVAL_CALLER,
        exact_approval_required=True,
    )
    if not getattr(result, "allowed", False):
        raise SeedApprovalRequired(
            "主体登记属于系统配置变更，需要人工审批 (CONFIG_MODIFY HIGH, "
            f"{APPROVAL_RESOURCE}): {getattr(result, 'reason', '')}"
        )


def load_seed(seed_path: Path = SEED_PATH, manifest_path: Path = MANIFEST_PATH) -> List[Dict[str, Any]]:
    raw = seed_path.read_bytes()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(raw).hexdigest()
    if digest != manifest.get("sha256_jsonl"):
        raise SeedIntegrityError(f"seed sha256 {digest} != manifest {manifest.get('sha256_jsonl')}")
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    if len(rows) != manifest.get("record_count"):
        raise SeedIntegrityError("seed record_count does not match manifest")
    for row in rows:
        if row.get("verification_status") != "VERIFIED_ONLINE" or not row.get("source_url"):
            raise SeedIntegrityError(f"unverified row in seed: {row.get('name_zh')}")
    return rows


def registry_payload(row: Dict[str, Any]) -> Dict[str, Any]:
    return {field: row[field] for field in REGISTRY_FIELDS}


def import_seed(rows: Iterable[Dict[str, Any]], *, apply: bool = False) -> Dict[str, Any]:
    """Validate every row with the registry rules; write only when ``apply``."""
    import subject_registry as registry

    if apply:
        require_apply_approval()
    report = {"total": 0, "created": 0, "existing": 0, "would_import": 0, "subject_ids": []}
    for row in rows:
        payload = registry_payload(row)
        report["total"] += 1
        if not apply:
            # Same validators add_subject uses, without touching the database.
            domain = registry.normalize_domain(payload["domain_id"])
            stype = registry.normalize_subject_type(payload["subject_type"])
            if (domain == "CTH") != (stype == "company"):
                raise registry.SubjectValidationError("domain/subject_type mismatch")
            registry._text(payload["name_en"], field="name_en")
            registry._text(payload["name_zh"], field="name_zh")
            registry._keywords(payload["keywords"])
            report["would_import"] += 1
            continue
        subject, created = registry.add_subject(payload)
        report["created" if created else "existing"] += 1
        report["subject_ids"].append(subject["subject_id"])
    return report


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="write through subject_registry.add_subject")
    args = parser.parse_args(argv)
    try:
        report = import_seed(load_seed(), apply=args.apply)
    except SeedApprovalRequired as exc:
        print(json.dumps({"ok": False, "code": "PERMISSION_DENIED", "error": str(exc)}, ensure_ascii=False))
        return 2
    report.pop("subject_ids")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
