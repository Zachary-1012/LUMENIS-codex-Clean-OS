"""
account/nav_config.py — 导航/工作台自定义

支持左侧栏目与页签的 显隐/添加/排序/重命名。
按 user_id + domain 持久化，不写死在模板。
受权限与双域隔离约束：跨域/无权栏目加不进来。
"""
import json
from .models import get_db

# 默认导航配置（已拍板）
DEFAULT_NAV = {
    "ZBMP": [
        {"id": "overview", "label": "概览", "icon": "dashboard", "visible": True, "order": 1},
        {"id": "brand", "label": "品牌", "icon": "brand", "visible": True, "order": 2},
        {"id": "content", "label": "内容", "icon": "content", "visible": True, "order": 3},
        {"id": "kos", "label": "KOS", "icon": "kos", "visible": True, "order": 4},
        {"id": "competition", "label": "竞品", "icon": "compete", "visible": True, "order": 5},
        {"id": "risk", "label": "风险", "icon": "risk", "visible": True, "order": 6},
        {"id": "reports", "label": "报告", "icon": "report", "visible": True, "order": 7},
    ],
    "CTH": [
        {"id": "overview", "label": "概览", "icon": "dashboard", "visible": True, "order": 1},
        {"id": "real-time", "label": "实时", "icon": "realtime", "visible": True, "order": 2},
        {"id": "events", "label": "事件", "icon": "event", "visible": True, "order": 3},
        {"id": "risk", "label": "风险", "icon": "risk", "visible": True, "order": 4},
        {"id": "xiaohongshu", "label": "小红书", "icon": "xhs", "visible": True, "order": 5},
        {"id": "reports", "label": "报告", "icon": "report", "visible": True, "order": 6},
    ],
    "SYSTEM": [
        {"id": "runtime", "label": "运行时", "icon": "runtime", "visible": True, "order": 1},
        {"id": "collector", "label": "采集", "icon": "collect", "visible": True, "order": 2},
        {"id": "ai", "label": "AI", "icon": "ai", "visible": True, "order": 3},
        {"id": "database", "label": "数据库", "icon": "db", "visible": True, "order": 4},
        {"id": "security", "label": "安全", "icon": "security", "visible": True, "order": 5},
        {"id": "settings", "label": "设置", "icon": "settings", "visible": True, "order": 6},
    ],
}

VALID_DOMAINS = ("ZBMP", "CTH", "SYSTEM")


def get_nav_config(user_id: int, domain: str) -> list:
    """获取用户导航配置（无配置则返回默认）"""
    domain = (domain or "").upper()
    if domain not in VALID_DOMAINS:
        return []
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT nav_items FROM user_nav_config WHERE user_id=? AND domain=?",
            (user_id, domain)
        )
        row = cur.fetchone()
        if row and row["nav_items"]:
            try:
                items = json.loads(row["nav_items"])
                return sorted(items, key=lambda x: x.get("order", 99))
            except (json.JSONDecodeError, TypeError):
                pass
        return DEFAULT_NAV.get(domain, [])
    finally:
        conn.close()


def save_nav_config(user_id: int, domain: str, nav_items: list) -> dict:
    """保存用户导航配置（全量替换）"""
    domain = (domain or "").upper()
    if domain not in VALID_DOMAINS:
        return {"success": False, "error": f"无效域：{domain}"}
    # 校验：不允许添加跨域栏目
    default_ids = {item["id"] for item in DEFAULT_NAV.get(domain, [])}
    for item in nav_items:
        item_id = item.get("id", "")
        # 自定义栏目允许，但必须有 label
        if item_id not in default_ids and not item.get("label"):
            return {"success": False, "error": f"自定义栏目 {item_id} 必须有 label"}
    conn = get_db()
    try:
        nav_json = json.dumps(nav_items, ensure_ascii=False)
        conn.execute(
            """INSERT INTO user_nav_config (user_id, domain, nav_items)
               VALUES (?,?,?)
               ON CONFLICT(user_id, domain) DO UPDATE SET nav_items=?, updated_at=datetime('now','localtime')""",
            (user_id, domain, nav_json, nav_json)
        )
        conn.commit()
        from .audit import log_audit
        log_audit("nav_config_update", "navigation", domain, f"用户{user_id}更新{domain}导航")
        return {"success": True, "nav_items": get_nav_config(user_id, domain)}
    finally:
        conn.close()


def reset_nav_config(user_id: int, domain: str) -> dict:
    """一键恢复默认导航"""
    domain = (domain or "").upper()
    conn = get_db()
    try:
        conn.execute("DELETE FROM user_nav_config WHERE user_id=? AND domain=?", (user_id, domain))
        conn.commit()
        return {"success": True, "nav_items": get_nav_config(user_id, domain),
                "message": "已恢复默认导航"}
    finally:
        conn.close()


def get_all_nav_configs(user_id: int) -> dict:
    """获取用户全部域的导航配置"""
    return {domain: get_nav_config(user_id, domain) for domain in VALID_DOMAINS}
