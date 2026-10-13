"""Import the PO-provided Guangzhou Taikoo Hui directory as Evidence-backed tenant claims.

Source class ``PO_PROVIDED_AUTHORITATIVE`` (approval ref
``PO-20261013-TKH-DIRECTORY-INGEST``): the Product Owner supplied the current
floor directory (xlsx, pinned by sha256 in the manifest) and declared it more
current than the official website. The directory is stored once as one source
note through the existing collector persistence owner, signed by the existing
Evidence owner, bound to the exact CTH venue scope through
``persist_existing_note_scope`` and only then written as ``TENANT_OF`` claims
through ``EntityRelationRepository.record_venue_tenant_claim``. Every claim
starts ``UNREVIEWED``. Default mode is a dry run; ``--apply`` is a HIGH risk
``CONFIG_MODIFY`` refused unless the existing PermissionGate holds an exact
human approval. This CLI never grants or fakes an approval itself.

Mandarin Oriental Guangzhou outlets and ``MOH`` units are not Taikoo Hui mall
units; they are excluded by the manifest and never written as tenant claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SEED_DIR = ROOT / "scripts" / "data_candidates"
DIRECTORY_PATH = SEED_DIR / "tkh_directory_20261013.jsonl"
MANIFEST_PATH = SEED_DIR / "tkh_directory_20261013.manifest.json"
SOURCE_CLASS = "PO_PROVIDED_AUTHORITATIVE"
APPROVAL_RESOURCE = "/api/settings/subjects/tenant-relations"
APPROVAL_CALLER = "scripts/import_tkh_directory_relations.py"
SOURCE_LOCALE = "mul"
VENUE_NAMES_EN = ("taikoo hui guangzhou", "guangzhou taikoo hui")
VENUE_NAME_ZH = "广州太古汇"


class DirectoryIntegrityError(ValueError):
    """Directory file does not match its pinned manifest or source class."""


class DirectoryApprovalRequired(PermissionError):
    """--apply was requested without an exact CONFIG_MODIFY approval."""


def require_apply_approval(gate: Any = None) -> None:
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
        raise DirectoryApprovalRequired(
            "场内关系写入属于系统配置变更，需要人工审批 (CONFIG_MODIFY HIGH, "
            f"{APPROVAL_RESOURCE}): {getattr(result, 'reason', '')}"
        )


def load_directory(path: Path = DIRECTORY_PATH, manifest_path: Path = MANIFEST_PATH):
    raw = path.read_bytes()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if hashlib.sha256(raw).hexdigest() != manifest.get("sha256_jsonl"):
        raise DirectoryIntegrityError("directory sha256 does not match manifest")
    if manifest.get("source_class") != SOURCE_CLASS:
        raise DirectoryIntegrityError("directory is not a PO_PROVIDED_AUTHORITATIVE source")
    for key in ("approval_ref", "source_sha256", "source_uri", "provided_at", "provided_by"):
        if not manifest.get(key):
            raise DirectoryIntegrityError(f"manifest provenance field missing: {key}")
    if manifest["source_uri"] != (
        f"po-provided://{manifest['source_file']}#sha256={manifest['source_sha256']}"
    ):
        raise DirectoryIntegrityError("source_uri does not pin the provided file sha256")
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    if len(rows) != manifest.get("store_count"):
        raise DirectoryIntegrityError("store_count does not match manifest")
    for row in rows:
        if any(u.upper().startswith("MOH") for u in row["units"]):
            raise DirectoryIntegrityError("MOH units are Mandarin Oriental, not mall units")
        for target in row["target_brands"]:
            if target["tenant_literal"].casefold() not in row["store_name"].casefold():
                raise DirectoryIntegrityError("tenant literal is not part of the source store name")
    return rows, manifest


def source_note_content(rows: List[Dict[str, Any]]) -> str:
    lines = ["广州太古汇场内分布 / Taikoo Hui Guangzhou floor directory (PO-provided)"]
    for row in rows:
        lines.append(" | ".join([
            row["store_name"], row.get("store_name_zh") or "-",
            "&".join(row["units"]) or "-", ";".join(row["floors"]) or "-", row["category"],
        ]))
    return "\n".join(lines)


def tenant_claims(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    claims = []
    for row in rows:
        for unit in row["units"]:
            for target in row["target_brands"]:
                claims.append({
                    "tenant_name": target["tenant_literal"], "floor": unit,
                    "category": row["category"], "brand_en": target["name_en"],
                    "brand_zh": target["name_zh"],
                })
    return claims


def _norm(value: str) -> str:
    import subject_registry as registry
    return registry._canonical_name(value or "")


def resolve_venue(conn: sqlite3.Connection) -> str:
    rows = conn.execute(
        "SELECT subject_id, name_en, name_zh FROM lumenis_subject_registry "
        "WHERE domain_id='CTH' AND lower(status) NOT IN ('archived','disabled','deleted')"
    ).fetchall()
    hits = [r[0] for r in rows if _norm(r[2]) == _norm(VENUE_NAME_ZH)
            or _norm(r[1]) in VENUE_NAMES_EN]
    if len(set(hits)) != 1:
        raise DirectoryIntegrityError(f"expected exactly one Taikoo Hui CTH identity, found {len(set(hits))}")
    return hits[0]


def resolve_brand(conn: sqlite3.Connection, name_en: str, name_zh: str) -> Optional[str]:
    rows = conn.execute(
        "SELECT brand_focus_id, name_en, name_zh FROM lumenis_subject_registry "
        "WHERE domain_id='BMP' AND brand_focus_id IS NOT NULL "
        "AND lower(status) NOT IN ('archived','disabled','deleted')"
    ).fetchall()
    en, zh = _norm(name_en), _norm(name_zh)
    exact = [r[0] for r in rows if _norm(r[1]) == en and _norm(r[2]) == zh]
    if len(exact) == 1:
        return exact[0]
    loose = {r[0] for r in rows if _norm(r[1]) == en}
    return next(iter(loose)) if len(loose) == 1 else None


def _existing_scope_ref(conn, note_id: str, venue: str) -> Optional[int]:
    row = conn.execute(
        "SELECT scope_status, scope_evidence_ref, subject_id FROM notes WHERE note_id=?", (note_id,)
    ).fetchone()
    if row and row[0] == "VERIFIED" and row[2] == venue and str(row[1] or "").isdigit():
        return int(row[1])
    return None


def import_directory(rows, manifest, *, apply: bool = False, conn: sqlite3.Connection = None) -> Dict[str, Any]:
    claims = tenant_claims(rows)
    report = {"stores": len(rows), "claims": len(claims), "written": 0, "existing": 0,
              "brand_unresolved": [], "approval_ref": manifest["approval_ref"]}
    if not apply:
        report["would_write"] = len(claims)
        return report
    require_apply_approval()
    from lumenis.adapters.base import CollectedNote
    from lumenis.adapters.persist import persist_existing_note_scope, persist_social_note
    from lumenis.shared.database.entity_relations import EntityRelationRepository
    from lumenis.shared.evidence import store as evidence_store

    owns = conn is None
    if owns:
        from lumenis.shared.database import get_repository
        conn = get_repository().connect()
    conn.row_factory = sqlite3.Row
    try:
        venue = resolve_venue(conn)
        uri = manifest["source_uri"]
        note = CollectedNote(
            title="广州太古汇场内分布（PO 提供 2026-10-13）", content=source_note_content(rows),
            url=uri, source_platform="po_provided",
            raw_data={"note_id": "tkh-directory-" + manifest["source_sha256"][:16]},
        )
        persist_social_note(conn, note, uri)
        note_id = "po_provided_tkh-directory-" + manifest["source_sha256"][:16]
        conn.commit()
        ref = _existing_scope_ref(conn, note_id, venue)
        if ref is None:
            ref = evidence_store.record_evidence(
                source="po_provided", project="LUMENIS", product="CTH",
                feature_id="CTH_PO_PROVIDED_DIRECTORY", test_name="po_provided_tkh_directory",
                capture_mode="po_provided", result="PASS", status="verified",
                inputs={"source_ids": [note_id], "source_uri": uri,
                        "source_sha256": manifest["source_sha256"],
                        "source_class": SOURCE_CLASS, "approval_ref": manifest["approval_ref"]},
                outputs={"store_count": len(rows), "claim_count": len(claims)},
                domain_id="cth", subject_id=venue,
            )
            persist_existing_note_scope(
                conn, [note_id], product_id="CTH", domain_id="cth",
                subject_id=venue, scope_evidence_ref=ref,
            )
            conn.commit()
        repo = EntityRelationRepository(conn)
        before = conn.execute(
            "SELECT COUNT(*) FROM lumenis_entity_relation_assertions WHERE source_evidence_ref=?", (ref,)
        ).fetchone()[0]
        for claim in claims:
            focus = resolve_brand(conn, claim["brand_en"], claim["brand_zh"])
            if focus is None:
                report["brand_unresolved"].append(claim["brand_en"])
            repo.record_venue_tenant_claim(
                venue_subject_id=venue, source_evidence_ref=ref, source_note_id=note_id,
                tenant_name=claim["tenant_name"], floor=claim["floor"], category=claim["category"],
                detail_url=None, listing_url=uri, source_locale=SOURCE_LOCALE,
                target_brand_focus_id=focus,
            )
        conn.commit()
        after = conn.execute(
            "SELECT COUNT(*) FROM lumenis_entity_relation_assertions WHERE source_evidence_ref=?", (ref,)
        ).fetchone()[0]
        report.update(written=after - before, existing=len(claims) - (after - before),
                      venue_subject_id=venue, evidence_ref=ref, note_id=note_id, total_for_source=after)
        report["brand_unresolved"] = sorted(set(report["brand_unresolved"]))
        return report
    finally:
        if owns:
            conn.close()


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    rows, manifest = load_directory()
    try:
        report = import_directory(rows, manifest, apply=args.apply)
    except DirectoryApprovalRequired as exc:
        print(json.dumps({"ok": False, "code": "PERMISSION_DENIED", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
