"""Import the reviewed Subject/BrandFocus seed through the existing registry path.

Seeds live in ``scripts/data_candidates/`` with a manifest that pins their
SHA-256 (``--seed 20261013`` is the online-verified universe seed; ``--seed tkh``
is the PO-provided Guangzhou Taikoo Hui directory brands). Every row is written
only through ``subject_registry.add_subject`` so identity, normalization,
deduplication and the ``configured`` status remain owned by the canonical
registry. Re-running is idempotent: existing identities are reported, never
duplicated or rewritten. A row whose English *or* Chinese name already belongs
to a different registered identity in the same domain is held as an identity
conflict instead of creating a near-duplicate.
Default mode is a dry run; pass ``--apply`` to write. ``--apply`` is a HIGH
risk ``CONFIG_MODIFY`` on the same resource as ``POST /api/settings/subjects``
and is refused unless the existing PermissionGate allows it with an exact human
approval; the CLI never grants or fakes an approval itself.

Accepted row provenance classes: ``VERIFIED_ONLINE`` (http source URL) and
``PO_PROVIDED_AUTHORITATIVE`` (the manifest pins the PO-provided file sha256,
its ``po-provided://`` URI and the PO approval reference).

Venue/tenant relations are intentionally not imported here: TENANT_OF claims
require captured, verified Evidence (see
``lumenis/shared/database/entity_relations.py`` and
``scripts/import_tkh_directory_relations.py``).
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
SEEDS = {
    "20261013": (SEED_PATH, MANIFEST_PATH),
    "tkh": (
        SEED_DIR / "subject_registry_seed_tkh_20261013.jsonl",
        SEED_DIR / "subject_registry_seed_tkh_20261013.manifest.json",
    ),
}
REGISTRY_FIELDS = ("domain_id", "subject_type", "name_en", "name_zh", "industry", "keywords")
PO_PROVIDED = "PO_PROVIDED_AUTHORITATIVE"


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


def _row_provenance_ok(row: Dict[str, Any], manifest: Dict[str, Any]) -> bool:
    status = row.get("verification_status")
    if status == "VERIFIED_ONLINE":
        return str(row.get("source_url") or "").startswith("http")
    if status == PO_PROVIDED:
        return (
            manifest.get("source_class") == PO_PROVIDED
            and bool(manifest.get("approval_ref")) and bool(manifest.get("source_sha256"))
            and row.get("source_url") == manifest.get("source_uri")
            and str(manifest.get("source_uri") or "").endswith("sha256=" + manifest["source_sha256"])
        )
    return False


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
        if not row.get("verified_at") or not _row_provenance_ok(row, manifest):
            raise SeedIntegrityError(f"unverified row in seed: {row.get('name_zh')}")
    return rows


def registry_payload(row: Dict[str, Any]) -> Dict[str, Any]:
    return {field: row[field] for field in REGISTRY_FIELDS}


def _identity_conflict(registry: Any, payload: Dict[str, Any]) -> Dict[str, Any] | None:
    """Return an existing identity sharing exactly one of name_en/name_zh."""
    try:
        existing = registry.list_subjects(payload["domain_id"])
    except Exception:  # registry not created yet: nothing can conflict
        return None
    en = registry._canonical_name(payload["name_en"])
    zh = registry._canonical_name(payload["name_zh"])
    for row in existing:
        same_en = registry._canonical_name(row.get("name_en") or "") == en
        same_zh = registry._canonical_name(row.get("name_zh") or "") == zh
        if same_en != same_zh:
            return {"subject_id": row.get("subject_id"), "name_en": row.get("name_en"),
                    "name_zh": row.get("name_zh")}
    return None


def import_seed(rows: Iterable[Dict[str, Any]], *, apply: bool = False) -> Dict[str, Any]:
    """Validate every row with the registry rules; write only when ``apply``."""
    import subject_registry as registry

    if apply:
        require_apply_approval()
    report = {"total": 0, "created": 0, "existing": 0, "would_import": 0,
              "identity_conflicts": [], "subject_ids": []}
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
        conflict = _identity_conflict(registry, payload)
        if conflict is not None:
            report["identity_conflicts"].append(
                {"seed": {"name_en": payload["name_en"], "name_zh": payload["name_zh"]},
                 "existing": conflict})
            continue
        subject, created = registry.add_subject(payload)
        report["created" if created else "existing"] += 1
        report["subject_ids"].append(subject["subject_id"])
    return report


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="write through subject_registry.add_subject")
    parser.add_argument("--seed", choices=sorted(SEEDS), default="20261013")
    args = parser.parse_args(argv)
    try:
        report = import_seed(load_seed(*SEEDS[args.seed]), apply=args.apply)
    except SeedApprovalRequired as exc:
        print(json.dumps({"ok": False, "code": "PERMISSION_DENIED", "error": str(exc)}, ensure_ascii=False))
        return 2
    report.pop("subject_ids")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
