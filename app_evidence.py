# -*- coding: utf-8 -*-
"""
XHS App Evidence Adapter - 最小可运行版（V3.0 P1）

定位：App端数据证据采集（Shadow模式，不碰App自动化）
- 用户主动打开App → 截图/分享 → 上传 → OCR/手动字段识别 → 证据记录 → 人工确认 → Shadow
- 禁止：自动登录、自动浏览、私有API、逆向签名、抓包、绕风控
- 数据只做Shadow记录，不进入生产高频采集链路

最小对象：
AppEvidence
├── id
├── source              来源平台（xhs_app / douyin_app / weibo_app）
├── capture_mode        采集方式（screenshot / share_link / manual_input）
├── captured_at         截图/采集时间
├── topic               关联话题
├── metric_name         指标名（browse_count / discussion_count / note_count等）
├── metric_value        指标值
├── evidence_hash       证据文件哈希（去重用）
├── evidence_path       证据文件本地路径
├── parse_confidence    解析置信度（0-1，OCR或手动输入）
├── verified_by         人工确认人
├── verified_at         确认时间
├── status              状态（pending / confirmed / rejected / shadow）
├── notes               备注
├── created_at
├── updated_at
"""
import os
import logging
import json
import hashlib
import sqlite3
from datetime import datetime
from flask import jsonify, request

# ========== 配置 ==========
MODULE_VERSION = '1.0.0-shadow'
EVIDENCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'app_evidence')
# 上传安全限制（对齐 INGESTION_AND_TERMINOLOGY_STANDARD）
EVIDENCE_ALLOWED_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp',  # 图片
    '.pdf', '.txt', '.csv',                              # 文档
    '.mp4', '.mov', '.webm',                             # 视频
}
EVIDENCE_MAX_FILE_SIZE_MB = 500
EVIDENCE_MAX_FILE_SIZE_BYTES = EVIDENCE_MAX_FILE_SIZE_MB * 1024 * 1024

from db_paths import main_db_path  # P0-DBISO-01 隔离重定向，call-time
DB_PATH = main_db_path()

# 支持的来源平台
SUPPORTED_SOURCES = ['xhs_app', 'douyin_app', 'weibo_app', 'other']
# 支持的采集方式
SUPPORTED_CAPTURE_MODES = ['screenshot', 'share_link', 'manual_input']
# 支持的指标名
SUPPORTED_METRICS = ['browse_count', 'discussion_count', 'note_count', 'like_count', 'comment_count', 'collect_count', 'other']
# 状态
STATUS_PENDING = 'pending'
STATUS_CONFIRMED = 'confirmed'
STATUS_REJECTED = 'rejected'
STATUS_SHADOW = 'shadow'

# 确保目录存在
os.makedirs(EVIDENCE_DIR, exist_ok=True)


# ========== 数据库 Schema ==========
SCHEMA = """
CREATE TABLE IF NOT EXISTS app_evidence_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL DEFAULT 'xhs_app',
    capture_mode TEXT NOT NULL DEFAULT 'screenshot',
    captured_at TEXT,
    topic TEXT,
    metric_name TEXT NOT NULL,
    metric_value TEXT NOT NULL,
    evidence_hash TEXT,
    evidence_path TEXT,
    parse_confidence REAL DEFAULT 1.0,
    verified_by TEXT,
    verified_at TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_app_evidence_topic ON app_evidence_records(topic);
CREATE INDEX IF NOT EXISTS idx_app_evidence_status ON app_evidence_records(status);
CREATE INDEX IF NOT EXISTS idx_app_evidence_hash ON app_evidence_records(evidence_hash);
"""


logger = logging.getLogger(__name__)

def _get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(main_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """初始化数据库表"""
    with _get_db() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def _now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _row_to_dict(row):
    if row is None:
        return None
    return dict(row)


# ========== CRUD 操作 ==========
def create_evidence(source='xhs_app', capture_mode='screenshot', captured_at=None,
                    topic=None, metric_name=None, metric_value=None,
                    evidence_path=None, parse_confidence=1.0, notes=None):
    """创建一条证据记录"""
    if not metric_name or metric_value is None:
        return None, 'metric_name 和 metric_value 不能为空'

    if source not in SUPPORTED_SOURCES:
        return None, f'不支持的来源平台: {source}'

    if capture_mode not in SUPPORTED_CAPTURE_MODES:
        return None, f'不支持的采集方式: {capture_mode}'

    # 计算证据文件哈希（用于去重）
    evidence_hash = None
    if evidence_path and os.path.exists(evidence_path):
        with open(evidence_path, 'rb') as f:
            evidence_hash = hashlib.md5(f.read()).hexdigest()
        # 检查是否已存在相同哈希的记录
        with _get_db() as conn:
            existing = conn.execute(
                "SELECT id FROM app_evidence_records WHERE evidence_hash=? AND status != 'rejected'",
                (evidence_hash,)
            ).fetchone()
            if existing:
                return None, f'证据文件已存在（ID: {existing["id"]}），请勿重复上传'

    now = _now()
    with _get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO app_evidence_records
            (source, capture_mode, captured_at, topic, metric_name, metric_value,
             evidence_hash, evidence_path, parse_confidence, status, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            source, capture_mode, captured_at or now, topic, metric_name, str(metric_value),
            evidence_hash, evidence_path, parse_confidence, STATUS_PENDING, notes, now, now
        ))
        conn.commit()
        record_id = cursor.lastrowid

    return get_evidence(record_id), None


def get_evidence(record_id):
    """获取单条证据记录"""
    with _get_db() as conn:
        row = conn.execute("SELECT * FROM app_evidence_records WHERE id=?", (record_id,)).fetchone()
        return _row_to_dict(row)


def list_evidence(status=None, topic=None, source=None, limit=50, offset=0):
    """列出证据记录"""
    query = "SELECT * FROM app_evidence_records WHERE 1=1"
    params = []
    if status:
        query += " AND status=?"
        params.append(status)
    if topic:
        query += " AND topic LIKE ?"
        params.append(f'%{topic}%')
    if source:
        query += " AND source=?"
        params.append(source)
    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with _get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        total = conn.execute("SELECT COUNT(*) as cnt FROM app_evidence_records WHERE 1=1" +
                              (" AND status=?" if status else "") +
                              (" AND topic LIKE ?" if topic else "") +
                              (" AND source=?" if source else ""),
                              params[:-2] if params else []).fetchone()
        return {
            'records': [_row_to_dict(r) for r in rows],
            'total': total['cnt'] if total else 0,
            'limit': limit,
            'offset': offset
        }


def update_evidence_status(record_id, status, verified_by=None, notes=None):
    """更新证据状态（确认/拒绝/Shadow）"""
    if status not in [STATUS_CONFIRMED, STATUS_REJECTED, STATUS_SHADOW, STATUS_PENDING]:
        return None, f'不支持的状态: {status}'

    record = get_evidence(record_id)
    if not record:
        return None, f'记录不存在: {record_id}'

    now = _now()
    with _get_db() as conn:
        conn.execute("""
            UPDATE app_evidence_records
            SET status=?, verified_by=?, verified_at=?, notes=COALESCE(?, notes), updated_at=?
            WHERE id=?
        """, (status, verified_by, now if status in [STATUS_CONFIRMED, STATUS_SHADOW] else None,
              notes, now, record_id))
        conn.commit()

    return get_evidence(record_id), None


def delete_evidence(record_id):
    """删除证据记录（同时删除证据文件）"""
    record = get_evidence(record_id)
    if not record:
        return False, f'记录不存在: {record_id}'

    # 删除证据文件
    if record.get('evidence_path') and os.path.exists(record['evidence_path']):
        try:
            os.remove(record['evidence_path'])
        except Exception:
            pass

    with _get_db() as conn:
        conn.execute("DELETE FROM app_evidence_records WHERE id=?", (record_id,))
        conn.commit()

    return True, None


def get_stats():
    """获取统计信息"""
    with _get_db() as conn:
        total = conn.execute("SELECT COUNT(*) as cnt FROM app_evidence_records").fetchone()['cnt']
        pending = conn.execute("SELECT COUNT(*) as cnt FROM app_evidence_records WHERE status='pending'").fetchone()['cnt']
        confirmed = conn.execute("SELECT COUNT(*) as cnt FROM app_evidence_records WHERE status='confirmed'").fetchone()['cnt']
        rejected = conn.execute("SELECT COUNT(*) as cnt FROM app_evidence_records WHERE status='rejected'").fetchone()['cnt']
        shadow = conn.execute("SELECT COUNT(*) as cnt FROM app_evidence_records WHERE status='shadow'").fetchone()['cnt']
        by_source = conn.execute("SELECT source, COUNT(*) as cnt FROM app_evidence_records GROUP BY source").fetchall()
        by_metric = conn.execute("SELECT metric_name, COUNT(*) as cnt FROM app_evidence_records GROUP BY metric_name").fetchall()

    return {
        'total': total,
        'pending': pending,
        'confirmed': confirmed,
        'rejected': rejected,
        'shadow': shadow,
        'by_source': {r['source']: r['cnt'] for r in by_source},
        'by_metric': {r['metric_name']: r['cnt'] for r in by_metric},
        'module_version': MODULE_VERSION,
        'mode': 'shadow_only'
    }


# ========== OCR 辅助（最小版：先做手动输入，后续接入真正OCR） ==========
def parse_screenshot_manual(evidence_path, topic=None, metric_name=None, metric_value=None, notes=None):
    """手动解析截图（最小版：用户手动填写字段，系统只做记录）

    后续可接入：pytesseract / paddleocr / 云端OCR API
    当前版本：parse_confidence=1.0（用户手动输入，完全可信）
    """
    return create_evidence(
        source='xhs_app',
        capture_mode='screenshot',
        topic=topic,
        metric_name=metric_name,
        metric_value=metric_value,
        evidence_path=evidence_path,
        parse_confidence=1.0,
        notes=notes or '手动输入解析（OCR待接入）'
    )


# ========== Flask 路由注册 ==========
def register_app_evidence(app):
    """注册 App Evidence 路由（Shadow模式，只读+手动上传，不碰App自动化）"""
    init_db()

    @app.route('/api/app_evidence/stats', methods=['GET'])
    def api_evidence_stats():
        return jsonify({'ok': True, 'data': get_stats()})

    @app.route('/api/app_evidence/list', methods=['GET'])
    def api_evidence_list():
        status = request.args.get('status')
        topic = request.args.get('topic')
        source = request.args.get('source')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        result = list_evidence(status=status, topic=topic, source=source, limit=limit, offset=offset)
        return jsonify({'ok': True, 'data': result})

    @app.route('/api/app_evidence/<int:record_id>', methods=['GET'])
    def api_evidence_get(record_id):
        record = get_evidence(record_id)
        if not record:
            return jsonify({'ok': False, 'error': '记录不存在'}), 404
        return jsonify({'ok': True, 'data': record})

    @app.route('/api/app_evidence/upload', methods=['POST'])
    def api_evidence_upload():
        """上传证据（截图+手动填写字段）

        Shadow模式：只记录，不进入生产采集
        禁止：自动登录、自动浏览、私有API、逆向签名、抓包、绕风控
        """
        try:
            source = request.form.get('source', 'xhs_app')
            capture_mode = request.form.get('capture_mode', 'screenshot')
            captured_at = request.form.get('captured_at')
            topic = request.form.get('topic')
            metric_name = request.form.get('metric_name')
            metric_value = request.form.get('metric_value')
            notes = request.form.get('notes')

            if not metric_name or metric_value is None:
                return jsonify({'ok': False, 'error': 'metric_name 和 metric_value 不能为空'}), 400

            # 处理文件上传
            evidence_path = None
            if 'file' in request.files:
                file = request.files['file']
                if file.filename:
                    # 扩展名白名单校验
                    ext = os.path.splitext(file.filename)[1].lower() or '.png'
                    if ext not in EVIDENCE_ALLOWED_EXTENSIONS:
                        return jsonify({'ok': False, 'error': f'不支持的文件格式: {ext}，允许: {sorted(EVIDENCE_ALLOWED_EXTENSIONS)}'}), 400
                    # 先保存再检查大小（Flask MAX_CONTENT_LENGTH 已在全局拦截，这里二次校验）
                    filename = f"evidence_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}{ext}"
                    evidence_path = os.path.join(EVIDENCE_DIR, filename)
                    file.save(evidence_path)
                    actual_size = os.path.getsize(evidence_path)
                    if actual_size > EVIDENCE_MAX_FILE_SIZE_BYTES:
                        os.remove(evidence_path)
                        return jsonify({'ok': False, 'error': f'文件超过 {EVIDENCE_MAX_FILE_SIZE_MB}MB 限制'}), 400

            record, err = create_evidence(
                source=source, capture_mode=capture_mode, captured_at=captured_at,
                topic=topic, metric_name=metric_name, metric_value=metric_value,
                evidence_path=evidence_path, parse_confidence=1.0, notes=notes
            )
            if err:
                return jsonify({'ok': False, 'error': err}), 400
            return jsonify({'ok': True, 'data': record, 'message': '证据已上传（Shadow模式，待人工确认）'})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500

    @app.route('/api/app_evidence/<int:record_id>/confirm', methods=['POST'])
    def api_evidence_confirm(record_id):
        """确认证据（人工确认后进入Shadow）"""
        verified_by = request.form.get('verified_by', 'manual')
        notes = request.form.get('notes')
        record, err = update_evidence_status(record_id, STATUS_CONFIRMED, verified_by=verified_by, notes=notes)
        if err:
            return jsonify({'ok': False, 'error': err}), 400
        return jsonify({'ok': True, 'data': record, 'message': '证据已确认（Shadow模式）'})

    @app.route('/api/app_evidence/<int:record_id>/reject', methods=['POST'])
    def api_evidence_reject(record_id):
        """拒绝证据"""
        notes = request.form.get('notes')
        record, err = update_evidence_status(record_id, STATUS_REJECTED, notes=notes)
        if err:
            return jsonify({'ok': False, 'error': err}), 400
        return jsonify({'ok': True, 'data': record, 'message': '证据已拒绝'})

    @app.route('/api/app_evidence/<int:record_id>/shadow', methods=['POST'])
    def api_evidence_shadow(record_id):
        """标记为Shadow（已确认但仅作影子数据，不进入生产）"""
        verified_by = request.form.get('verified_by', 'manual')
        record, err = update_evidence_status(record_id, STATUS_SHADOW, verified_by=verified_by)
        if err:
            return jsonify({'ok': False, 'error': err}), 400
        return jsonify({'ok': True, 'data': record, 'message': '证据已标记为Shadow'})

    @app.route('/api/app_evidence/<int:record_id>', methods=['DELETE'])
    def api_evidence_delete(record_id):
        """删除证据"""
        success, err = delete_evidence(record_id)
        if not success:
            return jsonify({'ok': False, 'error': err}), 400
        return jsonify({'ok': True, 'message': '证据已删除'})

    print(f'[AppEvidence] 模块已注册（v{MODULE_VERSION}，Shadow模式，不碰App自动化）')
    return True
