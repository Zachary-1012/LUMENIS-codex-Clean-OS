from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "contracts" / "experience" / "lumenis_app_binding_registry.json"
CONSTITUTION = ROOT / "00-GOVERNANCE" / "LUMENIS-EXPERIENCE-CONSTITUTION.md"
BLUEPRINT_HEADING = "## 36. The 44 screen-specific UX blueprints"
BLUEPRINT_TABLE_END = "### Blueprint implementation rules"
SCREEN_ID = re.compile(r"^(?:ACC|CTH|BMP|AI|SYS|SH)-\d{2}$")
BINDING_ID = re.compile(r"^BACKEND-GAP-\d{3}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SNAPSHOT_HEAD = re.compile(r"^[0-9a-f]{40}$")
SOURCE_FILES = {
    "contracts/experience/screen_meta.json",
    "contracts/experience/viewmodels/VIEWMODEL_REGISTRY.json",
    "contracts/experience/unknown-bindings.json",
    "contracts/experience/BINDING_MATRIX.json",
    "contracts/experience/BACKEND_GAP.json",
}


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)


def _load_json_bytes(contents: bytes, label: str) -> Any:
    try:
        return json.loads(contents.decode("utf-8"), object_pairs_hook=_unique_object)
    except Exception as exc:
        raise AssertionError(f"invalid source JSON {label}: {exc}") from exc


def _validate_source_snapshot(registry: dict[str, Any]) -> dict[str, Any]:
    entries = registry.get("source_files")
    if not isinstance(entries, list):
        raise AssertionError("registry source_files must be an array of SHA-256 snapshots")

    declared: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise AssertionError("registry source_files entries must be objects")
        path = entry.get("file")
        digest = entry.get("sha256")
        if path not in SOURCE_FILES or path in declared:
            raise AssertionError(f"unexpected or duplicate source snapshot path: {path!r}")
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            raise AssertionError(f"{path}: missing or malformed SHA-256")
        declared[path] = digest

    if set(declared) != SOURCE_FILES:
        raise AssertionError(
            f"source snapshot coverage mismatch; missing={sorted(SOURCE_FILES - set(declared))}, "
            f"extra={sorted(set(declared) - SOURCE_FILES)}"
        )

    loaded: dict[str, Any] = {}
    for relative_path in sorted(SOURCE_FILES):
        path = ROOT / relative_path
        try:
            contents = path.read_bytes()
        except OSError as exc:
            raise AssertionError(f"missing source contract {relative_path}: {exc}") from exc
        actual_digest = hashlib.sha256(contents).hexdigest()
        if actual_digest != declared[relative_path]:
            raise AssertionError(
                f"source snapshot drift: {relative_path} "
                f"expected={declared[relative_path]} actual={actual_digest}"
            )
        loaded[relative_path] = _load_json_bytes(contents, relative_path)

    snapshot_head = registry.get("generated_from_head")
    if not isinstance(snapshot_head, str) or not SNAPSHOT_HEAD.fullmatch(snapshot_head):
        raise AssertionError("registry generated_from_head must be a 40-character commit SHA")
    for binding in registry.get("bindings", []):
        if binding.get("source_snapshot_head") != snapshot_head:
            raise AssertionError(
                f"{binding.get('binding_id')}: source_snapshot_head does not match registry snapshot"
            )
    return loaded


def _unique_binding_sources(rows: Any, id_field: str, label: str) -> tuple[dict[str, dict[str, Any]], set[tuple[str, str]]]:
    if not isinstance(rows, list) or len(rows) != 54:
        raise AssertionError(f"{label} must contain exactly 54 binding rows")
    by_id: dict[str, dict[str, Any]] = {}
    keys: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise AssertionError(f"{label} binding rows must be objects")
        binding_id = row.get(id_field)
        key = (row.get("screen"), row.get("field"))
        if not isinstance(binding_id, str) or not BINDING_ID.fullmatch(binding_id):
            raise AssertionError(f"{label} has invalid {id_field}: {binding_id!r}")
        if binding_id in by_id:
            raise AssertionError(f"{label} duplicates binding ID {binding_id}")
        if not all(isinstance(part, str) and part for part in key) or key in keys:
            raise AssertionError(f"{label} has an invalid or duplicate (screen, field) key: {key!r}")
        by_id[binding_id] = row
        keys.add(key)
    return by_id, keys


def _validate_source_ids(registry: dict[str, Any], sources: dict[str, Any]) -> None:
    screen_meta = sources["contracts/experience/screen_meta.json"]
    viewmodel_registry = sources["contracts/experience/viewmodels/VIEWMODEL_REGISTRY.json"]
    if not isinstance(screen_meta, dict):
        raise AssertionError("screen_meta.json must map screen IDs to metadata")
    vm_screens = viewmodel_registry.get("screens") if isinstance(viewmodel_registry, dict) else None
    if not isinstance(vm_screens, dict):
        raise AssertionError("VIEWMODEL_REGISTRY.json must contain a screens object")

    source_screen_ids = set(screen_meta)
    vm_screen_ids = set(vm_screens)
    registry_screen_ids = {
        screen.get("screen_id") for screen in registry.get("screens", [])
        if isinstance(screen, dict)
    }
    if len(source_screen_ids) != 44:
        raise AssertionError(f"screen_meta.json must contain 44 screens, got {len(source_screen_ids)}")
    if source_screen_ids != vm_screen_ids:
        raise AssertionError(
            f"screen source drift between screen_meta and ViewModels; "
            f"meta_only={sorted(source_screen_ids - vm_screen_ids)}, "
            f"viewmodel_only={sorted(vm_screen_ids - source_screen_ids)}"
        )
    if registry_screen_ids != source_screen_ids:
        raise AssertionError(
            f"registry screen IDs differ from source contracts; "
            f"registry_only={sorted(registry_screen_ids - source_screen_ids)}, "
            f"source_only={sorted(source_screen_ids - registry_screen_ids)}"
        )

    expected_ids = {f"BACKEND-GAP-{number:03d}" for number in range(1, 55)}
    registry_bindings, registry_keys = _unique_binding_sources(
        registry.get("bindings"), "binding_id", "binding registry"
    )
    unknown_data = sources["contracts/experience/unknown-bindings.json"]
    matrix_data = sources["contracts/experience/BINDING_MATRIX.json"]
    gap_data = sources["contracts/experience/BACKEND_GAP.json"]
    if not all(isinstance(item, dict) for item in (unknown_data, matrix_data, gap_data)):
        raise AssertionError("binding source contracts must be JSON objects")

    unknown_bindings, unknown_keys = _unique_binding_sources(
        unknown_data.get("bindings"), "binding_id", "unknown-bindings.json"
    )
    matrix_rows = matrix_data.get("matrix")
    if not isinstance(matrix_rows, list) or len(matrix_rows) != 54:
        raise AssertionError("BINDING_MATRIX.json must contain exactly 54 matrix rows")
    matrix_keys: set[tuple[str, str]] = set()
    for row in matrix_rows:
        if not isinstance(row, dict):
            raise AssertionError("BINDING_MATRIX.json matrix rows must be objects")
        key = (row.get("screen"), row.get("field"))
        if not all(isinstance(part, str) and part for part in key) or key in matrix_keys:
            raise AssertionError(f"BINDING_MATRIX.json has an invalid or duplicate key: {key!r}")
        matrix_keys.add(key)
    gaps, gap_keys = _unique_binding_sources(gap_data.get("gaps"), "gap_id", "BACKEND_GAP.json")

    for label, source_ids in (
        ("binding registry", set(registry_bindings)),
        ("unknown-bindings.json", set(unknown_bindings)),
        ("BACKEND_GAP.json", set(gaps)),
    ):
        if source_ids != expected_ids:
            raise AssertionError(
                f"{label} IDs must be BACKEND-GAP-001..054; "
                f"missing={sorted(expected_ids - source_ids)}, extra={sorted(source_ids - expected_ids)}"
            )

    for label, source_keys in (
        ("unknown-bindings.json", unknown_keys),
        ("BINDING_MATRIX.json", matrix_keys),
        ("BACKEND_GAP.json", gap_keys),
    ):
        if source_keys != registry_keys:
            raise AssertionError(
                f"(screen, field) drift in {label}; "
                f"registry_only={sorted(registry_keys - source_keys)}, "
                f"source_only={sorted(source_keys - registry_keys)}"
            )

    source_id_field_by_id = {
        binding_id: (row.get("screen"), row.get("field"))
        for binding_id, row in unknown_bindings.items()
    }
    for label, source_rows in (("BACKEND_GAP.json", gaps),):
        for binding_id, row in source_rows.items():
            if (row.get("screen"), row.get("field")) != source_id_field_by_id[binding_id]:
                raise AssertionError(f"{label} ID/key mismatch for {binding_id}")
    for binding_id, row in registry_bindings.items():
        if (row.get("screen"), row.get("field")) != source_id_field_by_id[binding_id]:
            raise AssertionError(f"binding registry ID/key mismatch for {binding_id}")


def _blueprint_rows() -> dict[str, list[str]]:
    text = CONSTITUTION.read_text(encoding="utf-8")
    try:
        start = text.index(BLUEPRINT_HEADING) + len(BLUEPRINT_HEADING)
    except ValueError as exc:
        raise AssertionError(f"missing required section: {BLUEPRINT_HEADING}") from exc
    try:
        end = text.index(BLUEPRINT_TABLE_END, start)
    except ValueError as exc:
        raise AssertionError(f"missing required section end: {BLUEPRINT_TABLE_END}") from exc

    rows: dict[str, list[str]] = {}
    for line in text[start:end].splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells:
            continue
        if cells[0] == "Screen" or re.fullmatch(r"-+", cells[0]):
            continue
        identity = cells[0].split(maxsplit=1)
        if len(identity) != 2 or not SCREEN_ID.fullmatch(identity[0]) or not identity[1].strip():
            raise AssertionError(f"invalid screen blueprint ID/title cell: {cells[0]!r}")
        rows.setdefault(identity[0], []).append(cells)
    return rows


def validate() -> tuple[int, int]:
    registry = _load_registry()
    sources = _validate_source_snapshot(registry)
    _validate_source_ids(registry, sources)
    screens = registry.get("screens")
    bindings = registry.get("bindings")
    if not isinstance(screens, list) or not isinstance(bindings, list):
        raise AssertionError("registry must contain screens and bindings arrays")

    screen_ids = [screen.get("screen_id") for screen in screens]
    if len(screen_ids) != 44 or len(set(screen_ids)) != len(screen_ids):
        raise AssertionError(f"expected 44 unique screen IDs, got {len(screen_ids)}")

    rows = _blueprint_rows()
    if set(rows) != set(screen_ids):
        missing = sorted(set(screen_ids) - set(rows))
        extra = sorted(set(rows) - set(screen_ids))
        raise AssertionError(f"screen blueprint coverage mismatch; missing={missing}, extra={extra}")
    compositions: set[str] = set()
    for screen_id, occurrences in rows.items():
        if len(occurrences) != 1:
            raise AssertionError(f"screen {screen_id} has {len(occurrences)} blueprint rows")
        cells = occurrences[0]
        if len(cells) != 4 or any(not value for value in cells[1:]):
            raise AssertionError(f"screen {screen_id} needs a purpose-built composition, primary action, and PC→mobile plan")
        composition = " ".join(cells[1].split())
        if composition in compositions:
            raise AssertionError(f"screen {screen_id} reuses an identical screen composition")
        compositions.add(composition)

    binding_ids = [row.get("binding_id") for row in bindings]
    binding_keys = [(row.get("screen"), row.get("field")) for row in bindings]
    expected_bindings = {f"BACKEND-GAP-{number:03d}" for number in range(1, 55)}
    if len(bindings) != 54 or set(binding_ids) != expected_bindings:
        raise AssertionError("binding registry must contain BACKEND-GAP-001..054 exactly once")
    if len(set(binding_keys)) != len(binding_keys):
        raise AssertionError("binding registry contains duplicate (screen, field) keys")
    if any(screen not in set(screen_ids) or not field for screen, field in binding_keys):
        raise AssertionError("every binding must reference an inventoried screen and non-empty field")

    for row in bindings:
        for field in ("canonical_owner", "source_contract", "actor_scope", "api_callable",
                      "viewmodel", "permission", "evidence_lineage", "read_write_effect",
                      "truth_status", "acceptance_reference", "next_action"):
            if field not in row:
                raise AssertionError(f"{row.get('binding_id')}: missing required binding field {field}")

    return len(screen_ids), len(bindings)


if __name__ == "__main__":
    screen_count, binding_count = validate()
    print(
        "Experience blueprint/source contract: PASS "
        f"screens={screen_count} bindings={binding_count} sha256=verified ids=verified"
    )
