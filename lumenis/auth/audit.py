"""
操作审计日志
记录谁、什么时间、做了什么操作
"""
import sqlite3
from flask import request, g
from .models import get_db


def log_audit(action: str, resource: str = None, resource_id: str = None, detail: str = None):
    """
    记录审计日志
    自动从请求中获取当前用户和IP
    """
    user = getattr(g, "current_user", None)
    user_id = user["id"] if user else None
    username = user["username"] if user else "anonymous"
    ip = request.remote_addr if request else "unknown"

    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO v4_audit_logs (user_id, username, action, resource, resource_id, detail, ip)
               VALUES (?,?,?,?,?,?,?)""",
            (user_id, username, action, resource, resource_id, detail, ip)
        )
        conn.commit()
    finally:
        conn.close()


def query_audit_logs(page: int = 1, page_size: int = 50,
                     username: str = None, action: str = None,
                     start_date: str = None, end_date: str = None) -> dict:
    """查询审计日志（分页+筛选）"""
    conn = get_db()
    try:
        conditions = []
        params = []
        if username:
            conditions.append("username LIKE ?")
            params.append(f"%{username}%")
        if action:
            conditions.append("action LIKE ?")
            params.append(f"%{action}%")
        if start_date:
            conditions.append("created_at >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("created_at <= ?")
            params.append(end_date)

        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        # 总数
        cur = conn.execute(f"SELECT COUNT(*) as cnt FROM v4_audit_logs{where}", params)
        total = cur.fetchone()["cnt"]
        # 分页数据
        offset = (page - 1) * page_size
        cur = conn.execute(
            f"SELECT * FROM v4_audit_logs{where} ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        )
        logs = [dict(row) for row in cur.fetchall()]
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "logs": logs,
        }
    finally:
        conn.close()


def get_audit_stats() -> dict:
    """审计统计"""
    conn = get_db()
    try:
        cur = conn.execute("SELECT COUNT(*) as cnt FROM v4_audit_logs")
        total = cur.fetchone()["cnt"]
        cur = conn.execute("SELECT COUNT(DISTINCT username) as cnt FROM v4_audit_logs")
        users = cur.fetchone()["cnt"]
        cur = conn.execute("""
            SELECT action, COUNT(*) as cnt FROM v4_audit_logs
            GROUP BY action ORDER BY cnt DESC LIMIT 10
        """)
        action_stats = [dict(row) for row in cur.fetchall()]
        return {"total_logs": total, "active_users": users, "top_actions": action_stats}
    finally:
        conn.close()
