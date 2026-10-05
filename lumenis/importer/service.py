"""Local document upload, parsing, explicit analysis state and import preview."""
import os
import uuid
import sqlite3
from datetime import datetime
from typing import List, Dict
from flask import Blueprint, request, jsonify
from ..auth import require_auth, get_current_user, log_audit
from ..config import IMPORTER_CONFIG
from lumenis.shared.database import get_repository
from .parser import parse_file
from .analyzer import analyze_text, analyze_parsed, AnalyzedNote

importer_bp = Blueprint("v4_importer", __name__, url_prefix="/importer")  # 相对前缀，由父蓝图 /v4 拼成 /v4/importer

# 上传临时目录
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "imports")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@importer_bp.route("/upload", methods=["POST"])
@require_auth
def upload_file():
    """
    上传文件并解析预览
    返回: 解析后的笔记列表（预览，不入库）
    """
    if "file" not in request.files:
        return jsonify({"success": False, "error": "未选择文件"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"success": False, "error": "文件名为空"}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in IMPORTER_CONFIG["allowed_extensions"]:
        return jsonify({"success": False, "error": f"不支持的格式: {ext}"}), 400

    # 保存临时文件
    task_id = str(uuid.uuid4())[:8]
    filename = f"{task_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    file.save(file_path)

    # 检查文件大小
    if os.path.getsize(file_path) > IMPORTER_CONFIG["max_file_size_mb"] * 1024 * 1024:
        os.remove(file_path)
        return jsonify({"success": False, "error": f"文件超过{IMPORTER_CONFIG['max_file_size_mb']}MB"}), 400

    try:
        # 解析
        parsed = parse_file(file_path)
        # AI分析
        context_keywords = request.form.get("keywords", "").split(",")
        context_keywords = [k.strip() for k in context_keywords if k.strip()]
        notes = analyze_parsed(parsed, context_keywords)

        # 限制预览数量
        preview_notes = notes[:IMPORTER_CONFIG["preview_limit"]]

        log_audit("import_upload", "file", file.filename,
                  f"上传文件解析，得到{len(notes)}条笔记")

        return jsonify({
            "success": True,
            **_analysis_summary_payload(notes),
            "task_id": task_id,
            "filename": file.filename,
            "format": parsed.metadata.get("format", ""),
            "total_notes": len(notes),
            "preview_count": len(preview_notes),
            "notes": [_note_to_dict(n) for n in preview_notes],
            "tables_count": len(parsed.tables),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@importer_bp.route("/confirm", methods=["POST"])
@require_auth
def confirm_import():
    """
    确认导入，将选中的笔记入库
    请求体: {task_id, note_indices: [0,1,2], target_table: "notes"}
    """
    data = request.get_json()
    task_id = data.get("task_id")
    indices = data.get("note_indices", [])
    target_table = data.get("target_table", "notes")

    if not task_id:
        return jsonify({"success": False, "error": "缺少task_id"}), 400

    # 查找上传的文件
    import glob
    pattern = os.path.join(UPLOAD_DIR, f"{task_id}_*")
    files = glob.glob(pattern)
    if not files:
        return jsonify({"success": False, "error": "任务不存在或已过期"}), 404

    try:
        parsed = parse_file(files[0])
        notes = analyze_parsed(parsed)
        selected = [notes[i] for i in indices if i < len(notes)]

        inserted = _insert_notes(selected, target_table)

        log_audit("import_confirm", target_table, task_id,
                  f"导入{inserted}条笔记到{target_table}")

        # 清理临时文件
        for f in files:
            os.remove(f)

        return jsonify({
            "success": True, "inserted": inserted, "total": len(selected),
            **_analysis_summary_payload(selected),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


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
    """将笔记插入数据库。
    真实 notes 表 note_id 为 NOT NULL 非自增主键（24位hex，ObjectId风格），必须由本处生成；
    topics 列存 JSON 数组字符串；INSERT OR IGNORE 兜底唯一约束，rowcount 统计真实插入。"""
    import json
    import uuid
    if table != "notes":
        raise ValueError(f"外部导入当前仅支持 notes 表，收到: {table}")
    conn = get_repository().connect()
    inserted = 0
    try:
        for note in notes:
            cur = conn.execute(
                """INSERT OR IGNORE INTO notes
                   (note_id, title, content, author_nickname, publish_date, source_platform,
                    sentiment, sentiment_score, risk_level, risk_score, ai_provider, ai_analyzed_at,
                    topics, category, summary, collected_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now','localtime'))""",
                (uuid.uuid4().hex[:24], note.title, note.content, note.author or "外部导入",
                 note.publish_date, note.source_platform or "import",
                 note.sentiment, note.sentiment_score, note.risk_level, note.risk_score,
                 note.ai_provider,
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                 if note.analysis_status == "COMPLETED" else "",
                 json.dumps(note.topics, ensure_ascii=False),
                 note.category or "unknown", note.summary)
            )
            inserted += (cur.rowcount or 0)
        conn.commit()
    finally:
        conn.close()
    return inserted
