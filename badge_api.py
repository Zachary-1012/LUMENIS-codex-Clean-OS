"""
badge_api.py — 轻量红点提醒 API（ZBC V1.1 前端回补）
查询 alert_records 未读数 + notes/events 负面待审数，30s 轮询。
不修改任何核心模块，只读数据库 + 写 alert_records.state。
"""
import sqlite3
from datetime import datetime
from flask import Blueprint, jsonify, request
from db_paths import main_db_path

badge_bp = Blueprint('badge', __name__)

def _get_db():
    conn = sqlite3.connect(main_db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn, table_name):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    ).fetchone()
    return row is not None


@badge_bp.route('/api/badge/counts', methods=['GET'])
def badge_counts():
    """返回未读告警数 + 负面待审数。"""
    unread_alerts = 0
    negative_pending = 0

    try:
        with _get_db() as conn:
            # 1. 未读告警：alert_records.state 非 'read'/'acknowledged'
            if _table_exists(conn, 'alert_records'):
                row = conn.execute(
                    "SELECT COUNT(*) as cnt FROM alert_records "
                    "WHERE state NOT IN ('read','acknowledged','resolved')"
                ).fetchone()
                unread_alerts = row['cnt'] if row else 0

            # 2. 负面待审：notes 中 sentiment=negative 且 negative_confirmed != 1
            if _table_exists(conn, 'notes'):
                row = conn.execute(
                    "SELECT COUNT(*) as cnt FROM notes "
                    "WHERE sentiment = 'negative' "
                    "AND (negative_confirmed = 0 OR negative_confirmed IS NULL)"
                ).fetchone()
                negative_pending = row['cnt'] if row else 0

            # 3. 事件层面的负面待审（补充）
            if _table_exists(conn, 'events') and negative_pending == 0:
                row = conn.execute(
                    "SELECT COUNT(*) as cnt FROM events "
                    "WHERE risk_level IN ('high','critical') "
                    "AND (negative_confirmed = 0 OR negative_confirmed IS NULL) "
                    "AND status != 'resolved'"
                ).fetchone()
                if row and row['cnt'] > 0:
                    negative_pending = row['cnt']

    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e),
            'unread_alerts': 0,
            'negative_pending': 0
        }), 200  # 返回200但ok=false，前端静默降级

    return jsonify({
        'ok': True,
        'unread_alerts': unread_alerts,
        'negative_pending': negative_pending,
        'total': unread_alerts + negative_pending,
        'ts': datetime.utcnow().isoformat() + 'Z'
    })


@badge_bp.route('/api/badge/notifications', methods=['GET'])
def badge_notifications():
    """返回最近的通知列表（告警 + 负面待审）。"""
    limit = min(int(request.args.get('limit', 20)), 50)
    notifications = []

    try:
        with _get_db() as conn:
            # 告警记录
            if _table_exists(conn, 'alert_records'):
                rows = conn.execute(
                    "SELECT id, alert_key, alert_type, severity, message, state, created_at "
                    "FROM alert_records ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
                for r in rows:
                    notifications.append({
                        'id': 'alert_' + str(r['id']),
                        'type': 'alert',
                        'title': r['message'] or r['alert_key'] or '系统告警',
                        'severity': r['severity'],
                        'state': r['state'],
                        'time': r['created_at'] or ''
                    })

            # 负面待审笔记
            if _table_exists(conn, 'notes'):
                rows = conn.execute(
                    "SELECT id, title, author_nickname, sentiment, risk_level, collected_at "
                    "FROM notes WHERE sentiment = 'negative' "
                    "AND (negative_confirmed = 0 OR negative_confirmed IS NULL) "
                    "ORDER BY collected_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
                for r in rows:
                    notifications.append({
                        'id': 'note_' + str(r['id']),
                        'type': 'negative',
                        'title': r['title'] or '负面笔记待审',
                        'author': r['author_nickname'] or '',
                        'risk_level': r['risk_level'],
                        'time': r['collected_at'] or ''
                    })

            # 按时间排序
            notifications.sort(key=lambda x: x.get('time', ''), reverse=True)
            notifications = notifications[:limit]

    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'notifications': []}), 200

    return jsonify({
        'ok': True,
        'notifications': notifications,
        'count': len(notifications)
    })


@badge_bp.route('/api/badge/mark-all-read', methods=['POST'])
def badge_mark_all_read():
    """将所有告警标记为已读。"""
    try:
        with _get_db() as conn:
            if _table_exists(conn, 'alert_records'):
                conn.execute(
                    "UPDATE alert_records SET state = 'read', updated_at = ? "
                    "WHERE state NOT IN ('read','acknowledged','resolved')",
                    (datetime.utcnow().isoformat() + 'Z',)
                )
                conn.commit()
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 200

    return jsonify({'ok': True})


@badge_bp.route('/api/badge/mark-read/<notif_id>', methods=['POST'])
def badge_mark_read(notif_id):
    """标记单条通知为已读。"""
    try:
        with _get_db() as conn:
            if notif_id.startswith('alert_'):
                alert_id = notif_id.replace('alert_', '')
                if _table_exists(conn, 'alert_records'):
                    conn.execute(
                        "UPDATE alert_records SET state = 'read', updated_at = ? WHERE id = ?",
                        (datetime.utcnow().isoformat() + 'Z', alert_id)
                    )
                    conn.commit()
            elif notif_id.startswith('note_'):
                note_id = notif_id.replace('note_', '')
                if _table_exists(conn, 'notes'):
                    conn.execute(
                        "UPDATE notes SET negative_confirmed = 1, last_reviewed_at = ? WHERE id = ?",
                        (datetime.utcnow().isoformat() + 'Z', note_id)
                    )
                    conn.commit()
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 200

    return jsonify({'ok': True})
