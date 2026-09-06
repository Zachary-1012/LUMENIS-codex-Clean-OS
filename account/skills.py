"""
account/skills.py — Skill/Agent 能力统一管理

所有能力在 设置→技能(Skills) 统一登记管理（启用/禁用/添加/配置/查看说明与运行状态）。
按需启用模式：用户主动添加启用才出现并运行，不选就不显示不加载不运行。
技能带 product/domain 归属，跨域需授权，禁用即彻底不加载。
"""
import json
from .models import get_db

# 内置技能清单（从现有模块提取的能力）
BUILTIN_SKILLS = [
    {"skill_id": "ai_analyzer", "name": "AI分析", "description": "舆情AI分析与摘要", "product": "SYSTEM", "domain": "global", "version": "1.0"},
    {"skill_id": "risk_engine", "name": "风险引擎", "description": "舆情风险评估与预警", "product": "CTH", "domain": "risk", "version": "1.0"},
    {"skill_id": "report_generator", "name": "报告生成", "description": "自动生成舆情/品牌报告", "product": "SYSTEM", "domain": "report", "version": "1.0"},
    {"skill_id": "kos_engine", "name": "KOS引擎", "description": "KOL/KOS兴趣图谱与分析", "product": "ZBMP", "domain": "kos", "version": "1.0"},
    {"skill_id": "collector_xhs", "name": "小红书采集", "description": "小红书数据采集适配器", "product": "CTH", "domain": "collector", "version": "1.0"},
    {"skill_id": "collector_weibo", "name": "微博采集", "description": "微博数据采集适配器", "product": "CTH", "domain": "collector", "version": "1.0"},
    {"skill_id": "collector_bilibili", "name": "B站采集", "description": "B站数据采集适配器", "product": "CTH", "domain": "collector", "version": "1.0"},
    {"skill_id": "brand_analysis", "name": "品牌分析", "description": "品牌传播与声量分析", "product": "ZBMP", "domain": "brand", "version": "1.0"},
    {"skill_id": "internal_browser", "name": "内部浏览器", "description": "CDP浏览器自动化通道", "product": "SYSTEM", "domain": "developer", "version": "1.0"},
    {"skill_id": "data_visualization", "name": "数据可视化", "description": "函数驱动图表与仪表盘", "product": "SYSTEM", "domain": "viz", "version": "1.0"},
    {"skill_id": "intelligence_library", "name": "智能资料库", "description": "案例与知识检索库", "product": "SYSTEM", "domain": "library", "version": "1.0"},
    {"skill_id": "alert_engine", "name": "告警引擎", "description": "舆情告警与通知", "product": "CTH", "domain": "alert", "version": "1.0"},
]


def ensure_builtin_skills():
    """确保内置技能已登记到 DB（幂等）"""
    conn = get_db()
    try:
        for skill in BUILTIN_SKILLS:
            cur = conn.execute("SELECT id FROM skills_registry WHERE skill_id=?", (skill["skill_id"],))
            if not cur.fetchone():
                conn.execute(
                    """INSERT INTO skills_registry (skill_id, name, description, product, domain, status, version)
                       VALUES (?,?,?,?,?,'disabled',?)""",
                    (skill["skill_id"], skill["name"], skill["description"],
                     skill["product"], skill["domain"], skill["version"])
                )
        conn.commit()
    finally:
        conn.close()


def list_skills(product: str = None, status: str = None) -> list:
    """列出技能（可按 product/status 筛选）"""
    ensure_builtin_skills()
    conn = get_db()
    try:
        sql = "SELECT * FROM skills_registry"
        conditions = []
        params = []
        if product:
            conditions.append("product=?")
            params.append(product.upper())
        if status:
            conditions.append("status=?")
            params.append(status)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY product, name"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def set_skill_status(skill_id: str, status: str) -> dict:
    """启用/禁用技能"""
    if status not in ("enabled", "disabled"):
        return {"success": False, "error": "status 必须是 enabled 或 disabled"}
    conn = get_db()
    try:
        cur = conn.execute("SELECT name, product FROM skills_registry WHERE skill_id=?", (skill_id,))
        row = cur.fetchone()
        if not row:
            return {"success": False, "error": "技能不存在"}
        conn.execute(
            "UPDATE skills_registry SET status=?, updated_at=datetime('now','localtime') WHERE skill_id=?",
            (status, skill_id)
        )
        conn.commit()
        from .audit import log_audit
        log_audit("skill_status_change", "skill", skill_id,
                  f"技能 {row['name']} {status}")
        return {"success": True, "skill_id": skill_id, "status": status}
    finally:
        conn.close()


def configure_skill(skill_id: str, config: dict) -> dict:
    """配置技能参数"""
    conn = get_db()
    try:
        cur = conn.execute("SELECT id FROM skills_registry WHERE skill_id=?", (skill_id,))
        if not cur.fetchone():
            return {"success": False, "error": "技能不存在"}
        config_json = json.dumps(config, ensure_ascii=False)
        conn.execute(
            "UPDATE skills_registry SET config_json=?, updated_at=datetime('now','localtime') WHERE skill_id=?",
            (config_json, skill_id)
        )
        conn.commit()
        return {"success": True, "skill_id": skill_id, "config": config}
    finally:
        conn.close()


def add_custom_skill(skill_id: str, name: str, description: str = "",
                     product: str = "SYSTEM", domain: str = "global") -> dict:
    """添加自定义技能"""
    conn = get_db()
    try:
        cur = conn.execute("SELECT id FROM skills_registry WHERE skill_id=?", (skill_id,))
        if cur.fetchone():
            return {"success": False, "error": "skill_id 已存在"}
        conn.execute(
            """INSERT INTO skills_registry (skill_id, name, description, product, domain, status)
               VALUES (?,?,?,?,?,'disabled')""",
            (skill_id, name, description, product.upper(), domain)
        )
        conn.commit()
        return {"success": True, "skill_id": skill_id, "name": name}
    finally:
        conn.close()


def get_enabled_skills(product: str = None) -> list:
    """获取已启用的技能（用于前端判断是否显示入口）"""
    skills = list_skills(product=product, status="enabled")
    return [{"skill_id": s["skill_id"], "name": s["name"], "product": s["product"],
             "domain": s["domain"]} for s in skills]
