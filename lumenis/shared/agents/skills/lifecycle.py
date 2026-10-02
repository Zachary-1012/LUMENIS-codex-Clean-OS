"""Skill metadata candidates and signed history over the existing registry.

Preparation and history reads are read-only. A candidate is never an approval,
installation or permission grant. Metadata application belongs to this owner
after the canonical Permission/EffectFence manual-admission contract is bound.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
import uuid
from urllib.parse import urlparse

from lumenis.shared.database import get_repository
from lumenis.shared.evidence import store
from .package_runtime import preview_skill_source

SCHEMA_VERSION = "skill-metadata-change:v1"
HISTORY_SOURCE = "shared_skills"
HISTORY_FEATURE = "SKILL_METADATA_CHANGE"
_ISSUER = object()
_SKILL_ID = re.compile(r"^[a-z][a-z0-9_.-]{2,63}$")
_REF = re.compile(r"^app_evidence_records:([1-9][0-9]*)$")
_METADATA_FIELDS = (
    "skill_id", "name", "description", "product", "domain", "status", "version",
    "source", "source_type", "revision", "digest", "runtime", "entrypoint",
    "capabilities_json", "tools_json", "input_schema_json", "output_schema_json",
    "permissions_requested_json", "permissions_granted_json", "secrets_required_json",
    "dependencies_json", "compatibility_json", "trust_level", "health_state",
    "install_state", "lifecycle_state", "install_path", "active_version", "previous_version",
)
_REQUIRED_COLUMNS = frozenset((*_METADATA_FIELDS, "id", "config_json", "created_at", "updated_at",
                               "last_error", "last_health_at"))


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _hash(value) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _safe_metadata(metadata: dict) -> dict:
    """Reject embedded credentials rather than retaining them in version history."""
    from agent_runtime.durable_adapter import _sanitize_checkpoint_value

    def inspect(value):
        if isinstance(value, dict):
            for item in value.values():
                inspect(item)
        elif isinstance(value, list):
            for item in value:
                inspect(item)
        elif isinstance(value, str):
            if _sanitize_checkpoint_value(value)[1]:
                raise ValueError("SKILL_METADATA_CONTAINS_CREDENTIAL")
            for link in re.findall(r"[a-zA-Z][a-zA-Z0-9+.-]*://[^\s\"']+", value):
                parsed = urlparse(link)
                if parsed.username is not None or parsed.password is not None:
                    raise ValueError("SKILL_METADATA_CONTAINS_CREDENTIAL")
                if parsed.query and re.search(r"(?i)(?:[?&])(?:token|key|secret|password|signature)=", link):
                    raise ValueError("SKILL_METADATA_CONTAINS_CREDENTIAL")

    if set(metadata) != set(_METADATA_FIELDS):
        raise ValueError("SKILL_METADATA_SCHEMA_INVALID")
    inspect(metadata)
    entrypoint = metadata.get("entrypoint")
    if isinstance(entrypoint, str) and entrypoint.startswith("{"):
        try:
            parsed = json.loads(entrypoint)
        except ValueError:
            raise ValueError("SKILL_METADATA_ENTRYPOINT_INVALID") from None
        if _sanitize_checkpoint_value(parsed)[1]:
            raise ValueError("SKILL_METADATA_CONTAINS_CREDENTIAL")
    return metadata


def _registry_row(connection, skill_id: str) -> dict:
    if not isinstance(skill_id, str) or not _SKILL_ID.fullmatch(skill_id):
        raise ValueError("SKILL_ID_INVALID")
    columns = {row[1] for row in connection.execute("PRAGMA table_info(skills_registry)")}
    if not _REQUIRED_COLUMNS <= columns:
        raise RuntimeError("SKILL_LIFECYCLE_SCHEMA_NOT_READY")
    row = connection.execute("SELECT * FROM skills_registry WHERE skill_id=?", (skill_id,)).fetchone()
    if row is None:
        raise LookupError("SKILL_NOT_REGISTERED")
    return dict(row)


def _snapshot(row: dict) -> dict:
    return _safe_metadata({name: row[name] for name in _METADATA_FIELDS})


def _operation_id(value: str) -> str:
    try:
        parsed = uuid.UUID(value) if isinstance(value, str) else None
    except ValueError:
        parsed = None
    if parsed is None or str(parsed) != value or parsed.variant != uuid.RFC_4122:
        raise ValueError("SKILL_OPERATION_ID_INVALID")
    return value


@dataclass(frozen=True)
class SkillMetadataChange:
    """An immutable server-prepared change; it conveys no authority to apply."""
    skill_id: str
    action: str
    operation_id: str
    before_sha256: str
    after_sha256: str
    candidate_sha256: str
    config_sha256: str
    restore_evidence_ref: str | None
    _before_json: str = field(repr=False)
    _after_json: str = field(repr=False)
    _issuer: object = field(repr=False, compare=False)

    @property
    def resource(self) -> str:
        """Material fingerprint only; Permission binds the final identity/scope resource."""
        return "skills_registry_change:v1:" + self.candidate_sha256

    def to_dict(self) -> dict:
        _validate_candidate(self)
        return {
            "schema_version": SCHEMA_VERSION, "state": "PREPARED_NOT_APPROVED",
            "skill_id": self.skill_id, "action": self.action, "operation_id": self.operation_id,
            "before_sha256": self.before_sha256, "after_sha256": self.after_sha256,
            "candidate_sha256": self.candidate_sha256, "config_sha256": self.config_sha256,
            "material_resource": self.resource, "restore_evidence_ref": self.restore_evidence_ref,
            "before_metadata": json.loads(self._before_json), "after_metadata": json.loads(self._after_json),
            "permissions_granted": [], "installed": False, "files_deleted": False,
        }


def _candidate_material(candidate: SkillMetadataChange) -> dict:
    return {"schema_version": SCHEMA_VERSION, "skill_id": candidate.skill_id, "action": candidate.action,
            "operation_id": candidate.operation_id, "before_sha256": candidate.before_sha256,
            "after_sha256": candidate.after_sha256, "config_sha256": candidate.config_sha256,
            "restore_evidence_ref": candidate.restore_evidence_ref,
            "before_metadata": json.loads(candidate._before_json), "after_metadata": json.loads(candidate._after_json)}


def _validate_candidate(candidate: SkillMetadataChange) -> None:
    if type(candidate) is not SkillMetadataChange or candidate._issuer is not _ISSUER:
        raise ValueError("SKILL_CANDIDATE_NOT_SERVER_PREPARED")
    material = _candidate_material(candidate)
    if candidate.candidate_sha256 != _hash(material) or candidate.after_sha256 != _hash(material["after_metadata"]):
        raise ValueError("SKILL_CANDIDATE_CHANGED")


def _history_row(connection, evidence_ref: str, skill_id: str) -> tuple[dict, dict, dict]:
    match = _REF.fullmatch(evidence_ref) if isinstance(evidence_ref, str) else None
    if not match:
        raise ValueError("SKILL_HISTORY_REFERENCE_INVALID")
    row = connection.execute("SELECT * FROM app_evidence_records WHERE id=?", (int(match[1]),)).fetchone()
    if row is None:
        raise LookupError("SKILL_HISTORY_NOT_FOUND")
    row = dict(row)
    if not store.verify_evidence_record_integrity(row):
        raise RuntimeError("SKILL_HISTORY_SIGNATURE_INVALID")
    if (row.get("source"), row.get("feature_id"), row.get("product"), row.get("asset_id"),
            row.get("result"), row.get("status")) != (
            HISTORY_SOURCE, HISTORY_FEATURE, "SYSTEM", skill_id, "PASS", "derived"):
        raise ValueError("SKILL_HISTORY_OWNER_MISMATCH")
    try:
        inputs, outputs = json.loads(row["inputs_json"]), json.loads(row["outputs_json"])
    except (TypeError, ValueError):
        raise ValueError("SKILL_HISTORY_SCHEMA_INVALID") from None
    if not isinstance(inputs, dict) or not isinstance(outputs, dict):
        raise ValueError("SKILL_HISTORY_SCHEMA_INVALID")
    if inputs.get("schema_version") != SCHEMA_VERSION or inputs.get("skill_id") != skill_id:
        raise ValueError("SKILL_HISTORY_SCHEMA_INVALID")
    before, after = outputs.get("before_metadata"), outputs.get("after_metadata")
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise ValueError("SKILL_HISTORY_SCHEMA_INVALID")
    _safe_metadata(before)
    _safe_metadata(after)
    if before.get("skill_id") != skill_id or after.get("skill_id") != skill_id \
            or inputs.get("after_sha256") != _hash(after):
        raise ValueError("SKILL_HISTORY_METADATA_MISMATCH")
    material = {key: inputs.get(key) for key in (
        "schema_version", "skill_id", "action", "operation_id", "before_sha256", "after_sha256",
        "config_sha256", "restore_evidence_ref")}
    material.update(before_metadata=before, after_metadata=after)
    _operation_id(material["operation_id"])
    if material["action"] not in {"update", "uninstall", "restore"} \
            or inputs.get("candidate_sha256") != _hash(material) \
            or row.get("version") != SCHEMA_VERSION + ":" + inputs["candidate_sha256"] \
            or row.get("test_name") != material["operation_id"]:
        raise ValueError("SKILL_HISTORY_CANDIDATE_MISMATCH")
    return row, inputs, outputs


def read_skill_version_history(skill_id: str, *, limit: int = 50) -> list[dict]:
    """Read verified existing Evidence only; never initializes or migrates tables."""
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("SKILL_HISTORY_LIMIT_INVALID")
    with get_repository().connection(read_only=True, wal=False) as connection:
        _registry_row(connection, skill_id)
        refs = connection.execute(
            "SELECT id FROM app_evidence_records WHERE source=? AND feature_id=? AND asset_id=? "
            "ORDER BY id DESC LIMIT ?", (HISTORY_SOURCE, HISTORY_FEATURE, skill_id, limit)).fetchall()
        history = []
        for ref in refs:
            evidence_ref = f"app_evidence_records:{ref['id']}"
            row, inputs, outputs = _history_row(connection, evidence_ref, skill_id)
            history.append({"evidence_ref": evidence_ref, "operation_id": inputs.get("operation_id"),
                            "action": inputs.get("action"), "candidate_sha256": inputs.get("candidate_sha256"),
                            "created_at": row["created_at"], "before_version": outputs["before_metadata"]["version"],
                            "after_version": outputs["after_metadata"]["version"],
                            "restored_enabled": False, "signature_verified": True})
    return history


def prepare_skill_metadata_change(skill_id: str, action: str, *, operation_id: str,
                                  source: str | None = None, restore_evidence_ref: str | None = None,
                                  resolve_remote: bool = False) -> SkillMetadataChange:
    """Prepare one update/uninstall/restore without changing registry or package files."""
    _operation_id(operation_id)
    if action not in {"update", "uninstall", "restore"}:
        raise ValueError("SKILL_METADATA_ACTION_INVALID")
    if (action == "update") != (source is not None) or (action == "restore") != (restore_evidence_ref is not None):
        raise ValueError("SKILL_METADATA_INPUT_INVALID")
    with get_repository().connection(read_only=True, wal=False) as connection:
        row = _registry_row(connection, skill_id)
        before = _snapshot(row)
        if str(row["source_type"] or "builtin").lower() == "builtin":
            raise ValueError("BUILTIN_SKILL_METADATA_CHANGE_NOT_SUPPORTED")
        after = dict(before)
        if action == "restore":
            _event, _inputs, outputs = _history_row(connection, restore_evidence_ref, skill_id)
            after = dict(outputs["before_metadata"])
            if (after["product"], after["domain"]) != (before["product"], before["domain"]) \
                    or str(after["source_type"] or "builtin").lower() == "builtin":
                raise ValueError("SKILL_RESTORE_OWNER_MISMATCH")
    if action == "update":
        preview = preview_skill_source(source, resolve_remote=resolve_remote, fetch_remote_manifest=resolve_remote)
        source_info = preview.get("source") or {}
        source_type = source_info.get("source_type")
        expected_state = "REMOTE_VALIDATED" if source_type == "github" else "VALIDATED"
        if source_type not in {"local", "zip", "skill_md", "github"} or preview.get("state") != expected_state:
            raise ValueError("SKILL_UPDATE_SOURCE_NOT_VALIDATED")
        normalized = (preview.get("validation") or {}).get("normalized") or {}
        if normalized.get("skill_id") != skill_id:
            raise ValueError("SKILL_UPDATE_ID_MISMATCH")
        if not re.fullmatch(r"[0-9a-f]{64}", str(preview.get("digest") or "")):
            raise ValueError("SKILL_UPDATE_DIGEST_MISSING")
        if source_type == "github" and not re.fullmatch(r"[0-9a-f]{40}", str(preview.get("revision") or "")):
            raise ValueError("SKILL_UPDATE_REVISION_MISSING")
        after.update({"name": normalized["name"], "description": normalized["description"],
                      "version": normalized["version"], "runtime": normalized["runtime"],
                      "entrypoint": normalized["entrypoint"] or None, "source": source_info["source"],
                      "source_type": source_type, "revision": preview.get("revision"), "digest": preview["digest"]})
        for name in ("capabilities", "tools", "input_schema", "output_schema", "permissions_requested", "secrets_required", "dependencies"):
            after[name + "_json"] = _json(normalized[name])
        after["compatibility_json"] = _json(preview.get("compatibility") or {})
        if (after["version"], after["revision"], after["digest"]) == (before["version"], before["revision"], before["digest"]):
            raise ValueError("SKILL_UPDATE_UNCHANGED")
    after.update({"status": "disabled", "permissions_granted_json": "[]", "trust_level": "unverified",
                  "health_state": "unknown", "install_state": "not_installed", "install_path": None,
                  "active_version": None, "previous_version": before["version"],
                  "lifecycle_state": "uninstalled" if action == "uninstall" else "validated"})
    if action == "uninstall":
        after["entrypoint"] = None
    _safe_metadata(after)
    values = dict(skill_id=skill_id, action=action, operation_id=operation_id, before_sha256=_hash(row),
                  after_sha256=_hash(after), candidate_sha256="", config_sha256=_hash(row["config_json"]),
                  restore_evidence_ref=restore_evidence_ref, _before_json=_json(before), _after_json=_json(after), _issuer=_ISSUER)
    candidate = SkillMetadataChange(**values)
    values["candidate_sha256"] = _hash(_candidate_material(candidate))
    return SkillMetadataChange(**values)


def recover_skill_metadata_candidate(skill_id: str, evidence_ref: str) -> SkillMetadataChange:
    """Recover a signed candidate after restart; fresh Fence approval is still required."""
    with get_repository().connection(read_only=True, wal=False) as connection:
        _registry_row(connection, skill_id)
        _event, inputs, outputs = _history_row(connection, evidence_ref, skill_id)
    candidate = SkillMetadataChange(
        skill_id=skill_id, action=inputs["action"], operation_id=inputs["operation_id"],
        before_sha256=inputs["before_sha256"], after_sha256=inputs["after_sha256"],
        candidate_sha256=inputs["candidate_sha256"], config_sha256=inputs["config_sha256"],
        restore_evidence_ref=inputs["restore_evidence_ref"],
        _before_json=_json(outputs["before_metadata"]), _after_json=_json(outputs["after_metadata"]), _issuer=_ISSUER,
    )
    _validate_candidate(candidate)
    return candidate


def apply_skill_metadata_change(candidate: SkillMetadataChange, *, gate,
                                actor_id: int | None = None, principal=None, domain_id: str,
                                subject_id: str | None = None, brand_focus_id: str | None = None,
                                global_scope: bool = False) -> dict:
    """Apply only an exact approved metadata change in the canonical transaction.

    The caller cannot provide a receipt or choose a Fence phase. The existing
    Fence issues/rechecks authority; this owner writes registry and signed
    history together, preserving configuration, files and execution history.
    """
    from lumenis.system.security import effect_fence, permission

    _validate_candidate(candidate)
    if type(gate) is not permission.PermissionGate:
        raise PermissionError("SKILL_METADATA_CANONICAL_PERMISSION_REQUIRED")
    fence = effect_fence.get_effect_fence()
    if not callable(getattr(fence, "check_skill_metadata_change", None)):
        raise RuntimeError("SKILL_METADATA_MANUAL_ADMISSION_NOT_BOUND")
    decision_type = getattr(effect_fence, "SkillMetadataFenceDecision", None)
    if decision_type is None:
        raise RuntimeError("SKILL_METADATA_MANUAL_ADMISSION_NOT_BOUND")
    scope = dict(domain_id=domain_id, subject_id=subject_id, brand_focus_id=brand_focus_id, global_scope=global_scope)

    def check(connection, phase, replay_ref=None):
        payload = permission._skill_metadata_payload(
            candidate, actor_id=actor_id, principal=principal, **scope,
        )
        expected_resource = permission.skill_metadata_approval_resource(
            candidate, actor_id=actor_id, principal=principal, **scope,
        )
        decision = fence.check_skill_metadata_change(
            candidate, connection=connection, gate=gate, actor_id=actor_id, principal=principal,
            **scope, phase=phase, replay_evidence_ref=replay_ref,
        )
        if type(decision) is not decision_type or decision.allowed is not True:
            code = decision.code if type(decision) is decision_type else "SKILL_METADATA_FENCE_UNVERIFIED"
            raise PermissionError(code)
        expected = {"before_write": "admitted", "before_commit": "commit_verified", "replay": "already_applied"}[phase]
        if decision.state != expected or (decision.operation_id, decision.candidate_sha256) != (
                candidate.operation_id, candidate.candidate_sha256):
            raise PermissionError("SKILL_METADATA_FENCE_BINDING_MISMATCH")
        expected_fields = {**payload["identity"], **payload["scope"], "resource": expected_resource}
        if any(getattr(decision, name) != value for name, value in expected_fields.items()) \
                or decision.idempotent_hit is not (phase == "replay") \
                or any(type(getattr(decision, name)) is not str or not getattr(decision, name)
                       for name in ("permission_audit_id", "scope_audit_id", "fence_audit_id")) \
                or not re.fullmatch(r"[0-9a-f]{64}", str(decision.approval_token_sha256)):
            raise PermissionError("SKILL_METADATA_FENCE_BINDING_MISMATCH")
        return decision

    with get_repository().transaction(timeout=10) as connection:
        connection.execute("BEGIN IMMEDIATE")
        _registry_row(connection, candidate.skill_id)
        rows = connection.execute(
            "SELECT id FROM app_evidence_records WHERE source=? AND feature_id=? AND test_name=? LIMIT 2",
            (HISTORY_SOURCE, HISTORY_FEATURE, candidate.operation_id),
        ).fetchall()
        if len(rows) > 1:
            raise RuntimeError("SKILL_METADATA_OPERATION_DUPLICATE")
        if rows:
            evidence_ref = f"app_evidence_records:{rows[0]['id']}"
            _event, inputs, _outputs = _history_row(connection, evidence_ref, candidate.skill_id)
            if inputs["candidate_sha256"] != candidate.candidate_sha256:
                raise ValueError("SKILL_METADATA_OPERATION_CONFLICT")
            decision = check(connection, "replay", evidence_ref)
            return {"state": "already_applied", "skill_id": candidate.skill_id, "action": candidate.action,
                    "operation_id": candidate.operation_id, "candidate_sha256": candidate.candidate_sha256,
                    "evidence_ref": evidence_ref, "resource": decision.resource,
                    "metadata": _snapshot(_registry_row(connection, candidate.skill_id)),
                    "files_deleted": False, "configuration_changed": False, "execution_cancelled": False}

        running = connection.execute(
            "SELECT 1 FROM skill_executions WHERE skill_id=? AND status IN ('pending','running') LIMIT 1",
            (candidate.skill_id,),
        ).fetchone()
        if running is not None:
            raise RuntimeError("SKILL_EXECUTION_IN_PROGRESS")
        decision = check(connection, "before_write")
        before, after = json.loads(candidate._before_json), json.loads(candidate._after_json)
        assignments = ",".join(f"{name}=?" for name in _METADATA_FIELDS)
        connection.execute(
            f"UPDATE skills_registry SET {assignments},"
            "updated_at=datetime('now','localtime') WHERE skill_id=?",
            (*[after[name] for name in _METADATA_FIELDS], candidate.skill_id),
        )
        commit_verification = check(connection, "before_commit")
        identity = {name: getattr(decision, name) for name in ("actor_id", "caller", "principal_kind", "principal_ref")}
        verified_scope = {name: getattr(decision, name) for name in ("domain_id", "subject_id", "brand_focus_id", "global_scope")}
        inputs = {key: value for key, value in _candidate_material(candidate).items()
                  if key not in {"before_metadata", "after_metadata"}}
        inputs.update(candidate_sha256=candidate.candidate_sha256, identity=identity, scope=verified_scope,
                      resource=decision.resource, permission_audit_id=decision.permission_audit_id,
                      scope_audit_id=decision.scope_audit_id, fence_audit_id=decision.fence_audit_id,
                      approval_token_sha256=decision.approval_token_sha256)
        inputs["commit_verification"] = {name: getattr(commit_verification, name) for name in (
            "permission_audit_id", "scope_audit_id", "fence_audit_id", "approval_token_sha256")}
        record_id = store.record_evidence(
            connection=connection, source=HISTORY_SOURCE, product="SYSTEM", subject_scope="SYSTEM",
            feature_id=HISTORY_FEATURE, asset_id=candidate.skill_id, test_name=candidate.operation_id,
            version=SCHEMA_VERSION + ":" + candidate.candidate_sha256, capture_mode="manual_metadata_admission",
            result="PASS", status="derived", inputs=inputs,
            outputs={"before_metadata": before, "after_metadata": after, "config_sha256": candidate.config_sha256},
            notes="Admission and first post-write commit verification recorded; fresh approval rechecked after signing. "
                  "Configuration, package files and execution history retained."
        )
        if type(record_id) is not int or record_id < 1:
            raise RuntimeError("SKILL_METADATA_HISTORY_WRITE_FAILED")
        evidence_ref = f"app_evidence_records:{record_id}"
        _history_row(connection, evidence_ref, candidate.skill_id)
        result = {"state": "applied", "skill_id": candidate.skill_id, "action": candidate.action,
                  "operation_id": candidate.operation_id, "candidate_sha256": candidate.candidate_sha256,
                  "evidence_ref": evidence_ref, "resource": decision.resource,
                  "metadata": _snapshot(_registry_row(connection, candidate.skill_id)),
                  "files_deleted": False, "configuration_changed": False, "execution_cancelled": False}
        final_decision = check(connection, "before_commit")
        with gate.skill_metadata_commit_lease(
                candidate, connection=connection, decision=final_decision,
                actor_id=actor_id, principal=principal, **scope):
            connection.commit()
    return result
