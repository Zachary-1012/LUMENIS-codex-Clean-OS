"""Local document upload, parsing, explicit analysis state and import preview."""
import os
import uuid
import json
import re
import hashlib
import shutil
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict
from flask import Blueprint, request, jsonify
from ..auth import require_auth, get_current_user, log_audit
from ..config import IMPORTER_CONFIG
from .parser import parse_file
from .analyzer import (
    analyze_text, analyze_parsed, extract_source_rows, source_rows_fingerprint, AnalyzedNote,
)

importer_bp = Blueprint("v4_importer", __name__, url_prefix="/importer")  # 相对前缀，由父蓝图 /v4 拼成 /v4/importer

# 上传临时目录
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "imports")
os.makedirs(UPLOAD_DIR, exist_ok=True)

_UPLOAD_LIMIT_BYTES = 8 * 1024 * 1024


def _safe_upload_name(value: object) -> str:
    if (not isinstance(value, str) or not 1 <= len(value) <= 185 or value != value.strip()
            or os.path.basename(value) != value or any(char in '<>:"/\\|?*' for char in value)
            or any(unicodedata.category(char).startswith("C") for char in value)
            or value.endswith((".", " "))):
        raise ValueError("IMPORT_FILENAME_INVALID")
    reserved = {"CON", "PRN", "AUX", "NUL", *{f"COM{i}" for i in range(1, 10)},
                *{f"LPT{i}" for i in range(1, 10)}}
    if Path(value).stem.split(".", 1)[0].upper() in reserved:
        raise ValueError("IMPORT_FILENAME_INVALID")
    return value


def _task_directory(task_id: str) -> Path:
    if not isinstance(task_id, str) or re.fullmatch(r"[0-9a-f]{32}", task_id) is None:
        raise ValueError("IMPORT_TASK_ID_INVALID")
    root = Path(UPLOAD_DIR).resolve()
    task_dir = (root / task_id).resolve()
    if task_dir.parent != root:
        raise ValueError("IMPORT_TASK_PATH_INVALID")
    return task_dir


def _manifest_path(task_dir: Path) -> Path:
    return task_dir / "preview.json"


def _write_manifest(path: Path, manifest: dict) -> None:
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as output:
            json.dump(manifest, output, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            output.write("\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _current_import_actor_scope():
    from experience_runtime import _source_brief_context, _parse_shared_workspace_scope_header
    if "X-Lumenis-Workspace-Scope" in request.headers:
        from lumenis.shared.reporting.saved_work import authorize_saved_work
        scope = _parse_shared_workspace_scope_header()
        actor = get_current_user(read_only=True)
        if actor is None:
            raise PermissionError("AUTH_REQUIRED")
        context = authorize_saved_work(actor, scope, action="write")
        return "user:" + str(context["actor_id"]), scope, actor

    actor_ref, _audit_ref, material, actor = _source_brief_context("write", include_actor=True)
    scope = {
        "domain_id": "cth" if material["product_id"] == "CTH" else "zbmp",
        "subject_id": material["subject_id"],
        "brand_focus_id": material["brand_focus_id"],
        "global_scope": material["global_scope"],
    }
    return actor_ref, scope, actor


def _normalized_import_provenance(provenance: object, manifest: dict) -> dict:
    if not isinstance(provenance, dict):
        raise ValueError("DOCUMENT_PROVENANCE_REQUIRED")
    if "source_origin" in provenance:
        raise ValueError("DOCUMENT_SOURCE_ORIGIN_SERVER_OWNED")
    value = dict(provenance)
    value.setdefault("source_url", None)
    value.setdefault("published_at", None)
    value.setdefault("title", manifest["original_filename"])
    captured_at = manifest["uploaded_at"]
    if "captured_at" in value and value["captured_at"] != captured_at:
        raise ValueError("DOCUMENT_CAPTURE_TIME_MISMATCH")
    value["captured_at"] = captured_at
    if not isinstance(value.get("rights"), str) or value["rights"] not in {
        "public-reference-only", "owner-approved",
    }:
        raise ValueError("DOCUMENT_RIGHTS_REQUIRED")
    if not isinstance(value.get("content_origin"), dict):
        raise ValueError("DOCUMENT_CONTENT_ORIGIN_REQUIRED")
    if value["source_url"] is None:
        value["source_origin"] = {
            "kind": "approved-file", "ref": "file-upload-" + manifest["source_sha256"],
        }
    return value


def _provenance_digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _source_import_receipt(manifest: dict, receipt: dict, *, replayed: bool) -> dict:
    selected_indices = receipt.get("selected_row_indices") or []
    canonical_rows = receipt.get("canonical_row_records") or []
    source_replayed = bool(receipt.get("source_replayed", replayed))
    return {
        "success": True, "status": "SOURCE_IMPORTED",
        "inserted": 0 if replayed or source_replayed else 1,
        "inserted_kind": "source_document", "note_rows_inserted": 0,
        "canonical_rows_inserted": 0 if replayed else int(receipt.get("canonical_rows_inserted") or 0),
        "selected_preview_indices": list(selected_indices),
        "preview_selection_applied": bool(selected_indices),
        "canonical_rows": list(canonical_rows),
        "total": manifest["total_note_count"],
        "preview_count": manifest["preview_note_count"],
        "analysis_status": manifest["preview_analysis"]["analysis_status"],
        "source_content_scope": "WHOLE_DOCUMENT",
        "document": {**receipt, "replayed": replayed},
    }


def _confirm_source_document(data: dict, *, actor_ref: str, scope: dict, actor) -> dict:
    task_id = data.get("task_id")
    task_dir = _task_directory(task_id)
    manifest_path = _manifest_path(task_dir)
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise LookupError("IMPORT_PREVIEW_NOT_FOUND")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("IMPORT_PREVIEW_INVALID") from exc
    if (not isinstance(manifest, dict) or manifest.get("schema") != "import-preview/v1"
            or manifest.get("task_id") != task_id):
        raise ValueError("IMPORT_PREVIEW_INVALID")
    if (manifest.get("actor_ref") != actor_ref or manifest.get("scope") != scope):
        raise PermissionError("IMPORT_PREVIEW_ACTOR_OR_SCOPE_CHANGED")
    if data.get("confirm_whole_source") is not True:
        raise ValueError("WHOLE_SOURCE_CONFIRMATION_REQUIRED")
    target_table = data.get("target_table", "notes")
    if target_table != "notes":
        raise ValueError("IMPORT_TARGET_UNSUPPORTED")
    indices = data.get("note_indices")
    selected_row_indices = None
    preview_selection_fingerprint = None
    if indices is not None:
        if (not isinstance(indices, list)
                or any(type(index) is not int or index < 0 for index in indices)
                or len(set(indices)) != len(indices)):
            raise ValueError("IMPORT_PREVIEW_SELECTION_INVALID")
        preview_count = manifest.get("preview_note_count")
        if type(preview_count) is not int or any(index >= preview_count for index in indices):
            raise ValueError("IMPORT_PREVIEW_SELECTION_INVALID")
        if not indices:
            raise ValueError("IMPORT_PREVIEW_SELECTION_EMPTY")
        if sorted(indices) != list(range(preview_count)):
            selected_row_indices = sorted(indices)
            preview_selection_fingerprint = manifest.get("preview_selection_fingerprint")
            if (not isinstance(preview_selection_fingerprint, str)
                    or re.fullmatch(r"[0-9a-f]{64}", preview_selection_fingerprint) is None):
                raise ValueError("IMPORT_PREVIEW_SELECTION_BINDING_UNAVAILABLE")

    provenance = _normalized_import_provenance(data.get("provenance"), manifest)
    provenance_sha256 = _provenance_digest(provenance)
    selection_sha256 = _provenance_digest({
        "selected_row_indices": selected_row_indices,
        "preview_selection_fingerprint": preview_selection_fingerprint,
    })
    if manifest.get("state") == "IMPORTED":
        prior_selection = manifest.get("selection_sha256")
        if (manifest.get("provenance_sha256") != provenance_sha256
                or prior_selection is not None and prior_selection != selection_sha256
                or prior_selection is None and selected_row_indices is not None):
            raise ValueError("IMPORT_REPLAY_CONFLICT")
        receipt = manifest.get("receipt")
        if not isinstance(receipt, dict):
            raise ValueError("IMPORT_RECEIPT_INVALID")
        return _source_import_receipt(manifest, receipt, replayed=True)

    original_filename = _safe_upload_name(manifest.get("original_filename"))
    source_path = task_dir / original_filename
    if (source_path.parent.resolve() != task_dir.resolve()
            or source_path.is_symlink() or not source_path.is_file()):
        raise LookupError("IMPORT_PREVIEW_SOURCE_MISSING")
    raw = source_path.read_bytes()
    if (len(raw) != manifest.get("source_size_bytes")
            or hashlib.sha256(raw).hexdigest() != manifest.get("source_sha256")):
        raise ValueError("IMPORT_PREVIEW_SOURCE_CHANGED")

    from lumenis.importer.documents import import_document

    imported = import_document(
        str(source_path), actor=actor, scope=scope, provenance=provenance,
        selected_row_indices=selected_row_indices,
        preview_row_count=manifest["preview_note_count"] if selected_row_indices is not None else None,
        expected_preview_rows_sha256=preview_selection_fingerprint,
    )
    if (not isinstance(imported, dict)
            or not all(imported.get(key) for key in ("source_id", "evidence_id", "canonical_id"))):
        raise RuntimeError("DOCUMENT_IMPORT_RECEIPT_INVALID")
    receipt = {key: imported[key] for key in (
        "source_id", "evidence_id", "canonical_id", "source_artifact_ref", "scope", "replayed",
        "source_replayed",
        "selected_row_indices", "canonical_rows_inserted", "canonical_row_records",
    ) if key in imported}
    manifest.update({
        "state": "IMPORTED", "provenance_sha256": provenance_sha256,
        "selection_sha256": selection_sha256, "receipt": receipt,
    })
    _write_manifest(manifest_path, manifest)
    source_path.unlink(missing_ok=True)
    return _source_import_receipt(manifest, receipt, replayed=bool(imported.get("replayed")))


@importer_bp.route("/upload", methods=["POST"])
@require_auth
def upload_file():
    """
    上传文件并解析预览
    返回: 解析后的笔记列表（预览，不入库）
    """
    if "file" not in request.files:
        return jsonify({"success": False, "error": "未选择文件"}), 400

    if set(request.files) != {"file"} or len(request.files.getlist("file")) != 1:
        return jsonify({"success": False, "error": "上传文件无效"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"success": False, "error": "文件名为空"}), 400
    try:
        original_filename = _safe_upload_name(file.filename)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    ext = os.path.splitext(original_filename)[1].lower()
    if ext not in IMPORTER_CONFIG["allowed_extensions"]:
        return jsonify({"success": False, "error": f"不支持的格式: {ext}"}), 400

    limit = min(_UPLOAD_LIMIT_BYTES, IMPORTER_CONFIG["max_file_size_mb"] * 1024 * 1024)
    raw = file.stream.read(limit + 1)
    if not 0 < len(raw) <= limit:
        return jsonify({"success": False, "error": "文件大小无效或超过导入上限"}), 413

    try:
        actor_ref, scope, _actor = _current_import_actor_scope()
        task_id = uuid.uuid4().hex
        task_dir = _task_directory(task_id)
        task_dir.mkdir(parents=True, exist_ok=False)
        file_path = task_dir / original_filename
        file_path.write_bytes(raw)
        if scope.get("scope_kind") == "shared_workspace":
            from lumenis.importer.documents import save_private_document
            saved = save_private_document(
                str(file_path), actor=_actor, scope=scope,
                request_id=request.form.get("request_id") or "upload-" + task_id,
                context_keywords=[term.strip() for term in request.form.get("keywords", "").split(",") if term.strip()],
            )
            # The immutable SavedWork registry now owns original bytes and analysis.
            shutil.rmtree(task_dir)
            response = jsonify({"success": True, "status": "PRIVATE_SOURCE_SAVED",
                "analysis_status": "COMPLETED", "analysis_method": "deterministic-source-basics:v1",
                "ai_state": "NOT_RUN", "canonical_admitted": False, "rights": "UNKNOWN",
                "result": saved})
            response.headers["Cache-Control"] = "no-store"
            return response
        # Deterministic parsing; model enhancement is a separate explicit action.
        parsed = parse_file(str(file_path))
        # AI分析
        context_keywords = request.form.get("keywords", "").split(",")
        context_keywords = [k.strip() for k in context_keywords if k.strip()]
        notes = analyze_parsed(parsed, context_keywords)

        # 限制预览数量
        preview_notes = notes[:IMPORTER_CONFIG["preview_limit"]]
        preview_selection_fingerprint = None
        preview_selection_error = None
        try:
            source_rows = extract_source_rows(parsed)
            if len(source_rows) != len(notes):
                preview_selection_error = "IMPORT_PREVIEW_SELECTION_BINDING_UNAVAILABLE"
            else:
                preview_selection_fingerprint = source_rows_fingerprint(
                    parsed, source_rows, count=len(preview_notes),
                )
        except (TypeError, ValueError, AttributeError):
            preview_selection_error = "IMPORT_PREVIEW_SELECTION_BINDING_UNAVAILABLE"
        uploaded_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        preview_analysis = _analysis_summary_payload(notes)
        manifest = {
            "schema": "import-preview/v1", "task_id": task_id, "state": "PREVIEWED",
            "actor_ref": actor_ref, "scope": scope, "original_filename": original_filename,
            "source_sha256": hashlib.sha256(raw).hexdigest(), "source_size_bytes": len(raw),
            "uploaded_at": uploaded_at, "preview_note_count": len(preview_notes),
            "total_note_count": len(notes),
            "preview_analysis": preview_analysis,
            "preview_selection_fingerprint": preview_selection_fingerprint,
            "preview_selection_error": preview_selection_error,
        }
        _write_manifest(_manifest_path(task_dir), manifest)

        log_audit("import_upload", "file", original_filename,
                  f"上传文件解析，得到{len(notes)}条笔记")

        return jsonify({
            "success": True,
            **_analysis_summary_payload(notes),
            "task_id": task_id,
            "source_sha256": manifest["source_sha256"],
            "filename": original_filename,
            "format": parsed.metadata.get("format", ""),
            "preview_selection_available": preview_selection_fingerprint is not None,
            "preview_selection_error": preview_selection_error,
            "total_notes": len(notes),
            "preview_count": len(preview_notes),
            "notes": [_note_to_dict(n) for n in preview_notes],
            "tables_count": len(parsed.tables),
        })
    except (ValueError, PermissionError) as exc:
        if "task_dir" in locals() and task_dir.is_dir():
            shutil.rmtree(task_dir)
        code = str(exc)
        if re.fullmatch(r"[A-Z_0-9]{1,100}", code) is None:
            code = "IMPORT_INPUT_INVALID"
        return jsonify({"success": False, "status": "ERROR", "code": code}), (403 if isinstance(exc, PermissionError) or "PERMISSION" in code else 400)
    except Exception:
        try:
            if "task_dir" in locals() and task_dir.is_dir():
                shutil.rmtree(task_dir)
        except OSError:
            pass
        return jsonify({"success": False, "status": "ERROR", "code": "IMPORT_PREVIEW_FAILED"}), 500


@importer_bp.route("/confirm", methods=["POST"])
@require_auth
def confirm_import():
    """
    Confirm a whole uploaded document through the canonical Source/Evidence/Canonical owner.
    Selected preview rows are projected to Canonical children under the source
    document's existing Evidence and exact scope; they are never written to notes.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "请求格式无效"}), 400
    try:
        actor_ref, scope, actor = _current_import_actor_scope()
        result = _confirm_source_document(data, actor_ref=actor_ref, scope=scope, actor=actor)
        log_audit("import_confirm", "source_document", data.get("task_id", ""),
                  f"导入 Source/Evidence/Canonical 文档 source_id={result['document']['source_id']}")
        return jsonify(result)
    except ValueError as exc:
        code = str(exc)
        if code in {
            "IMPORT_REPLAY_CONFLICT", "IMPORT_PREVIEW_SOURCE_CHANGED",
            "DOCUMENT_PREVIEW_SELECTION_CHANGED",
        }:
            return jsonify({"success": False, "status": "CONFLICT", "code": code,
                            "publish_status": "not_performed"}), 409
        from experience_runtime import _source_brief_job_error
        return _source_brief_job_error(exc)
    except (LookupError, PermissionError, RuntimeError) as exc:
        from experience_runtime import _source_brief_job_error
        return _source_brief_job_error(exc)
    except Exception as exc:
        return jsonify({"success": False, "code": "DOCUMENT_IMPORT_UNAVAILABLE"}), 503


def _note_to_dict(note: AnalyzedNote) -> dict:
    return {
        "title": note.title,
        "content": note.content,
        "author": note.author,
        "publish_date": note.publish_date,
        "source_platform": note.source_platform,
        "sentiment": note.sentiment,
        "sentiment_score": note.sentiment_score,
        "risk_level": note.risk_level,
        "risk_score": note.risk_score,
        "topics": note.topics,
        "category": note.category,
        "keywords": note.keywords,
        "summary": note.summary,
        "ai_provider": note.ai_provider,
        "analysis_status": note.analysis_status,
        "analysis_code": note.analysis_code,
        "keyword_method": note.keyword_method,
        "source_locator": note.source_locator,
        "source_row_sha256": note.source_row_sha256,
        "source_record": getattr(note, "source_record", None),
        "source_fields": getattr(note, "source_fields", []),
    }


def _analysis_summary_payload(notes: List[AnalyzedNote]) -> dict:
    """Keep parsing success separate from model analysis state and counts."""
    statuses = [str(note.analysis_status or "UNKNOWN") for note in notes]
    if not statuses:
        status = "NO_NOTES"
    elif all(item == "COMPLETED" for item in statuses):
        status = "COMPLETED"
    elif len(set(statuses)) == 1:
        status = statuses[0]
    else:
        status = "PARTIAL"
    return {
        "analysis_status": status,
        "analysis_completed_count": sum(item == "COMPLETED" for item in statuses),
        "analysis_unavailable_count": sum(
            item in {"UNAVAILABLE", "ERROR", "INVALID_INPUT"} for item in statuses
        ),
        "analysis_not_run_count": sum(item == "NOT_RUN" for item in statuses),
    }


def _insert_notes(notes: List[AnalyzedNote], table: str = "notes") -> int:
    """Retired compatibility helper; raw notes bypass Source/Evidence/Canonical."""
    raise RuntimeError("DIRECT_NOTES_IMPORT_RETIRED_USE_CANONICAL_DOCUMENT_IMPORT")
