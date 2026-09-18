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
    # A non-builtin Skill cannot become visible as enabled before its
    # verified runtime has passed install/self-test/health gates.
    from .models import init_account_db
    init_account_db()
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM skills_registry WHERE skill_id=?", (skill_id,))
        row = cur.fetchone()
        if not row:
            return {"success": False, "error": "技能不存在"}
        columns = set(row.keys())
        runtime = str(row["runtime"] if "runtime" in columns and row["runtime"] else "builtin").lower()
        install_state = str(row["install_state"] if "install_state" in columns and row["install_state"] else "not_installed").lower()
        health_state = str(row["health_state"] if "health_state" in columns and row["health_state"] else "unknown").lower()
        if status == "enabled" and runtime != "builtin" and (install_state != "installed" or health_state != "healthy"):
            return {"success": False, "error": "技能运行时尚未通过安装、自测与健康门禁", "code": "RUNTIME_NOT_READY"}
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


def register_validated_skill(preview: dict) -> dict:
    """登记已通过来源预检的 Skill 元数据，但保持禁用/未安装状态。

    这是生命周期中的 ``VALIDATED -> REGISTERED`` 节点，不是安装器：
    不下载、不解压、不导入、不启动进程、不授予权限。端点调用者必须
    先通过 owner 权限门，注册时再次读取并校验预检结果，避免信任浏览器
    回传的字段。元数据写入现有 ``skills_registry``，不创建第二注册表。
    """
    if not isinstance(preview, dict):
        return {"success": False, "error": "only VALIDATED Skill sources can be registered",
                "code": "SOURCE_NOT_VALIDATED"}
    validation = preview.get("validation") or {}
    normalized = validation.get("normalized") if isinstance(validation, dict) else None
    source = preview.get("source") if isinstance(preview.get("source"), dict) else {}
    source_type = str(source.get("source_type") or "unknown")
    if source_type in ("mcp_stdio", "mcp_http"):
        return {
            "success": False,
            "error": "MCP registration requires capability discovery and human approval",
            "code": "MCP_DISCOVERY_AND_APPROVAL_REQUIRED",
        }
    if source_type not in ("local", "zip", "skill_md", "github"):
        return {
            "success": False,
            "error": "only validated local, ZIP, SKILL.md, or pinned GitHub metadata can be registered at this stage",
            "code": "SOURCE_REGISTRATION_NOT_SUPPORTED",
        }
    valid_states = {"VALIDATED"}
    if source_type == "github":
        valid_states = {"REMOTE_VALIDATED"}
        revision = str(preview.get("revision") or "")
        remote_manifest = preview.get("remote_manifest") or {}
        if not revision or len(revision) != 40 or remote_manifest.get("path") is None:
            return {"success": False, "error": "pinned GitHub manifest evidence is incomplete",
                    "code": "REMOTE_MANIFEST_INCOMPLETE"}
    if preview.get("state") not in valid_states:
        return {"success": False, "error": "only VALIDATED Skill sources can be registered",
                "code": "SOURCE_NOT_VALIDATED"}
    if not isinstance(normalized, dict) or not normalized.get("skill_id"):
        return {"success": False, "error": "validated manifest is incomplete",
                "code": "MANIFEST_INCOMPLETE"}

    # Ensure an older production database receives the additive columns before
    # the single canonical insert. This never replaces or recreates tables.
    from .models import init_account_db
    init_account_db()
    skill_id = str(normalized["skill_id"])
    conn = get_db()
    try:
        if conn.execute("SELECT id FROM skills_registry WHERE skill_id=?", (skill_id,)).fetchone():
            return {"success": False, "error": "skill_id 已存在", "code": "SKILL_EXISTS",
                    "skill_id": skill_id}
        payload = (
            skill_id,
            str(normalized.get("name") or skill_id),
            str(normalized.get("description") or ""),
            "SYSTEM",
            "global",
            "disabled",
            str(normalized.get("version") or ""),
            str(source.get("source") or ""),
            str(source.get("source_type") or "unknown"),
            preview.get("revision"),
            preview.get("digest") or None,
            str(normalized.get("runtime") or "unknown"),
            str(normalized.get("entrypoint") or "") or None,
            json.dumps(normalized.get("capabilities") or [], ensure_ascii=False),
            json.dumps(normalized.get("tools") or [], ensure_ascii=False),
            json.dumps(normalized.get("input_schema") or {}, ensure_ascii=False),
            json.dumps(normalized.get("output_schema") or {}, ensure_ascii=False),
            json.dumps(normalized.get("permissions_requested") or [], ensure_ascii=False),
            "[]",
            json.dumps(normalized.get("secrets_required") or [], ensure_ascii=False),
            json.dumps(normalized.get("dependencies") or [], ensure_ascii=False),
            json.dumps(preview.get("compatibility") or {}, ensure_ascii=False),
            "unverified",
            "unknown",
            "not_installed",
            "validated",
        )
        conn.execute(
            """INSERT INTO skills_registry (
                skill_id, name, description, product, domain, status, version,
                source, source_type, revision, digest, runtime, entrypoint,
                capabilities_json, tools_json, input_schema_json, output_schema_json,
                permissions_requested_json, permissions_granted_json, secrets_required_json,
                dependencies_json, compatibility_json, trust_level, health_state,
                install_state, lifecycle_state
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            payload,
        )
        conn.commit()
        return {"success": True, "skill_id": skill_id, "status": "disabled",
                "install_state": "not_installed", "lifecycle_state": "validated",
                "permissions_granted": []}
    finally:
        conn.close()


def activate_installed_mcp_skill(skill_id: str, install_path: str, *,
                                 revision: str = "", digest: str = "") -> dict:
    """Activate a locally built MCP package in the existing Skill registry.

    The package must already have passed the remote-source preview and local
    build/smoke gate.  This function only records the verified runtime in the
    canonical registry; it never downloads, executes, enables, or grants a
    write permission.  Enabling remains a separate owner action.
    """
    from .models import init_account_db
    from mcp_skill_runtime import READ_ONLY_PERMISSIONS, build_entrypoint, validate_installation

    init_account_db()
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM skills_registry WHERE skill_id=?", (skill_id,)).fetchone()
        if not row:
            return {"success": False, "error": "Skill must be registered before activation", "code": "SKILL_NOT_REGISTERED"}
        if str(row["runtime"] or "").lower() != "mcp":
            return {"success": False, "error": "only MCP runtime Skills can use this activation path", "code": "RUNTIME_NOT_MCP"}
        if revision and str(row["revision"] or "") != revision:
            return {"success": False, "error": "installed revision does not match registered revision", "code": "REVISION_MISMATCH"}
        if digest and str(row["digest"] or "") != digest:
            return {"success": False, "error": "installed manifest digest does not match registered digest", "code": "DIGEST_MISMATCH"}
        check = validate_installation(
            install_path,
            expected_skill_id=skill_id,
            expected_version=str(row["version"] or ""),
        )
        if not check.get("ok"):
            return {"success": False, "error": "MCP package self-check failed", "code": "SELFTEST_FAILED", "health": check}
        entrypoint = build_entrypoint(install_path)
        conn.execute(
            """UPDATE skills_registry SET entrypoint=?, permissions_granted_json=?,
               trust_level='verified', health_state='healthy', install_state='installed',
               lifecycle_state='available', install_path=?, active_version=?,
               last_error=NULL, last_health_at=datetime('now','localtime'),
               updated_at=datetime('now','localtime') WHERE skill_id=?""",
            (
                json.dumps(entrypoint, ensure_ascii=False, sort_keys=True),
                json.dumps(list(READ_ONLY_PERMISSIONS), ensure_ascii=False),
                str(check["install_path"]),
                str(check["version"]),
                skill_id,
            ),
        )
        conn.commit()
        return {
            "success": True,
            "skill_id": skill_id,
            "status": str(row["status"] or "disabled"),
            "install_state": "installed",
            "lifecycle_state": "available",
            "health_state": "healthy",
            "permissions_granted": list(READ_ONLY_PERMISSIONS),
            "health": check,
        }
    finally:
        conn.close()


def get_enabled_skills(product: str = None) -> list:
    """获取已启用的技能（用于前端判断是否显示入口）"""
    skills = list_skills(product=product, status="enabled")
    return [{"skill_id": s["skill_id"], "name": s["name"], "product": s["product"],
             "domain": s["domain"]} for s in skills]


# ═══════════════════════════════════════════════════════════════
# Skill 执行链适配层（桥接 skill_execution_chain）
# ═══════════════════════════════════════════════════════════════

def get_skill_info(skill_id: str) -> dict:
    """获取单个 Skill 完整信息（含运行时状态）"""
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM skills_registry WHERE skill_id=?", (skill_id,))
        row = cur.fetchone()
        if not row:
            return {}
        info = dict(row)
        # 解析 config_json
        if info.get("config_json"):
            try:
                info["config"] = json.loads(info["config_json"])
            except Exception:
                info["config"] = {}
        else:
            info["config"] = {}
        # 最近执行状态
        try:
            from lumenis.shared.agents.skills.execution import query_executions
            execs = query_executions(skill_id=skill_id, limit=1)
            info["last_execution"] = execs[0] if execs else None
        except Exception:
            info["last_execution"] = None
        return info
    finally:
        conn.close()


def execute_skill_api(skill_id: str, task: str = "", input_payload: dict = None,
                      action_type: str = "ANALYZE", user_id: int = None,
                      user_role: str = "user", product: str = "SYSTEM") -> dict:
    """执行 Skill（走完整执行链：Permission→Firewall→Effect Fence→Execute→Evidence→Evaluation→Trace）"""
    from lumenis.shared.agents.skills.execution import (
        run_execution_chain, ActionType, SkillRuntimeInfo,
    )
    # 获取 Skill 信息用于权限检查
    info = get_skill_info(skill_id)
    if not info:
        return {"success": False, "error": f"skill '{skill_id}' not found", "code": "NOT_FOUND"}

    runtime_config = dict(info.get("config") or {})
    for key in (
        "runtime", "source", "source_type", "entrypoint", "install_path",
        "active_version", "version", "tools_json", "permissions_granted_json",
        "install_state", "lifecycle_state", "health_state",
    ):
        if info.get(key) is not None:
            runtime_config[key] = info.get(key)
    skill_runtime = SkillRuntimeInfo(
        skill_id=skill_id,
        name=info.get("name", skill_id),
        product=info.get("product", "SYSTEM"),
        domain=info.get("domain", "global"),
        enabled=info.get("status") == "enabled",
        config=runtime_config,
        source=info.get("source") or "builtin",
        version=info.get("version") or "1.0.0",
    )

    # 映射 action_type
    try:
        at = ActionType(action_type.upper())
    except ValueError:
        at = ActionType.ANALYZE

    ctx = run_execution_chain(
        skill_id=skill_id,
        task=task,
        input_payload=input_payload or {},
        action_type=at,
        user_id=user_id,
        user_role=user_role,
        product=product,
        domain=info.get("domain", "global"),
        skill_info=skill_runtime,
    )

    return {
        "success": ctx.status.value == "completed",
        "execution_id": ctx.execution_id,
        "status": ctx.status.value,
        "skill_id": skill_id,
        "result": ctx.execute_result,
        "evidence": ctx.evidence,
        "evaluation": ctx.evaluation,
        "permission": ctx.permission_result,
        "firewall": ctx.firewall_result,
        "effect_fence": ctx.effect_fence_result,
        "error": ctx.error,
    }


def get_skill_executions(skill_id: str = None, limit: int = 50, status: str = None) -> list:
    """获取 Skill 执行历史"""
    from lumenis.shared.agents.skills.execution import query_executions
    return query_executions(skill_id=skill_id, limit=limit, status=status)


def get_skills_status_light(product: str = None) -> dict:
    """轻量状态（主界面卡片用，只返回已启用+已注册）"""
    from lumenis.shared.agents.skills.execution import get_skills_light_status
    skills = get_skills_light_status(product=product)
    # 按类别分组
    categories = {}
    for s in skills:
        cat = _categorize_skill(s)
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(s)
    return {
        "total": len(skills),
        "enabled_count": sum(1 for s in skills if s["status"] == "enabled"),
        "categories": categories,
        "skills": skills,
    }


def _categorize_skill(skill: dict) -> str:
    """按 Skill 特征分类（采集类/分析类/报告类/运营类/开发者工具/系统）"""
    sid = skill.get("skill_id", "").lower()
    domain = skill.get("domain", "").lower()
    name = skill.get("name", "").lower()

    if any(k in sid or k in domain or k in name for k in ("collect", "crawl", "采集", "xhs", "weibo", "bilibili")):
        return "采集类"
    if any(k in sid or k in domain or k in name for k in ("analyze", "analysis", "分析", "risk", "ai", "kos", "brand")):
        return "分析类"
    if any(k in sid or k in domain or k in name for k in ("report", "报告", "viz", "visual", "可视化")):
        return "报告类"
    if any(k in sid or k in domain or k in name for k in ("alert", "告警", "operate", "运营", "library", "智能")):
        return "运营类"
    if any(k in sid or k in domain or k in name for k in ("browser", "developer", "开发", "registry", "agent", "boundary")):
        return "开发者工具"
    return "系统"
