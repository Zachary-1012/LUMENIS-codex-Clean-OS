"""
account/skills.py — Skill/Agent 能力统一管理

所有能力在 设置→技能(Skills) 统一登记管理（启用/禁用/添加/配置/查看说明与运行状态）。
按需启用模式：用户主动添加启用才出现并运行，不选就不显示不加载不运行。
技能带 product/domain 归属，跨域需授权，禁用即彻底不加载。
"""
import json
from .models import get_db


def _builtin_status_identity(actor, connection):
    """Reopen only the existing owner or sealed local skills/write identity."""
    from lumenis.auth.service import get_current_user
    from lumenis.system.security.permission import (_is_server_local_workspace_principal,
        resolve_local_workspace_principal)
    if _is_server_local_workspace_principal(actor):
        if resolve_local_workspace_principal(module='skills', action='write') is None:
            raise PermissionError('SKILL_STATUS_WORKSPACE_UNAVAILABLE')
        return 'workspace:local'
    current = get_current_user(read_only=True)
    actor_id = actor.get('id') if isinstance(actor, dict) else None
    if (type(actor_id) is not int or not isinstance(current, dict) or current.get('id') != actor_id):
        raise PermissionError('SKILL_STATUS_OWNER_REQUIRED')
    row = connection.execute('SELECT role,status FROM v4_users WHERE id=?', (actor_id,)).fetchone()
    if not row or row['role'] != 'owner' or row['status'] != 'active':
        raise PermissionError('SKILL_STATUS_OWNER_REQUIRED')
    return 'actor:' + str(actor_id)


def _builtin_status_row(connection, skill_id):
    from lumenis.shared.agents.skills.execution import _BACKGROUND_INPUTS
    if type(skill_id) is not str or skill_id not in _BACKGROUND_INPUTS or not skill_id.startswith('shared.'):
        raise ValueError('SKILL_STATUS_BOUNDED_BUILTIN_REQUIRED')
    row = connection.execute('SELECT * FROM skills_registry WHERE skill_id=?', (skill_id,)).fetchone()
    if row is None:
        raise LookupError('SKILL_NOT_REGISTERED')
    value = dict(row)
    if (value.get('product') != 'SHARED' or value.get('status') not in {'enabled', 'disabled'}
            or str(value.get('runtime') or 'builtin').lower() != 'builtin'
            or str(value.get('source') or 'builtin').lower() != 'builtin'
            or str(value.get('source_type') or 'builtin').lower() != 'builtin'):
        raise PermissionError('SKILL_STATUS_BOUNDED_BUILTIN_REQUIRED')
    return value


def _builtin_status_hash(value):
    import hashlib
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _builtin_status_request(skill_id, status, *, operation_id, expected_binding=None):
    import re
    import uuid
    if status not in {'enabled', 'disabled'}:
        raise ValueError('SKILL_STATUS_INVALID')
    try:
        parsed = uuid.UUID(operation_id) if type(operation_id) is str else None
    except ValueError:
        parsed = None
    if parsed is None or str(parsed) != operation_id or parsed.variant != uuid.RFC_4122:
        raise ValueError('SKILL_STATUS_OPERATION_ID_INVALID')
    if expected_binding is not None and (type(expected_binding) is not str
            or re.fullmatch('[0-9a-f]{64}', expected_binding) is None):
        raise ValueError('SKILL_STATUS_BINDING_INVALID')
    return {'schema': 'builtin-skill-status/v1', 'skill_id': skill_id, 'status': status,
            'operation_id': operation_id, 'expected_binding': expected_binding}


def _builtin_status_event(connection, operation_id):
    rows = connection.execute("SELECT detail FROM v4_audit_logs WHERE action='builtin_skill_status_confirm' "
                              "AND resource='skill' AND resource_id=? ORDER BY id LIMIT 2", (operation_id,)).fetchall()
    if len(rows) > 1:
        raise RuntimeError('SKILL_STATUS_OPERATION_DUPLICATE')
    return json.loads(rows[0]['detail']) if rows else None


def _prepare_builtin_status(connection, skill_id, status, actor, operation_id, expected_binding=None):
    value = _builtin_status_request(skill_id, status, operation_id=operation_id, expected_binding=expected_binding)
    caller = _builtin_status_identity(actor, connection)
    row = _builtin_status_row(connection, skill_id)
    event = _builtin_status_event(connection, operation_id)
    if event:
        if (event.get('skill_id') != skill_id or event.get('status') != status
                or event.get('caller') != caller or (expected_binding is not None
                    and event.get('expected_binding') != expected_binding)):
            raise RuntimeError('SKILL_STATUS_OPERATION_CONFLICT')
        binding = event['expected_binding']
    else:
        binding = _builtin_status_hash(row)
        if expected_binding is not None and expected_binding != binding:
            raise RuntimeError('SKILL_STATUS_REGISTRY_CHANGED')
    value.update(expected_binding=binding, caller=caller)
    resource = 'builtin-skill-status:v1:' + _builtin_status_hash(value)
    if event and event.get('resource') != resource:
        raise RuntimeError('SKILL_STATUS_OPERATION_CONFLICT')
    return {**value, 'resource': resource, 'current_status': row['status'],
            'state': 'ALREADY_APPLIED' if event else 'PREPARED', 'effect_performed': False,
            'idempotent_hit': event is not None}


def prepare_builtin_skill_status(skill_id, status, *, actor, operation_id):
    """Read the exact registered builtin and owner; never enable, install or grant."""
    from lumenis.shared.database import get_repository
    from lumenis.system.security.permission import authorize_shared_workspace
    with get_repository().connection(read_only=True, wal=False) as connection:
        authorize_shared_workspace(actor, {'scope_kind': 'shared_workspace', 'version': 1},
                                   module='skills', action='write', connection=connection)
        return _prepare_builtin_status(connection, skill_id, status, actor, operation_id)


def validate_builtin_skill_status_resource(resource, *, actor, scope, connection=None):
    """Pure callback for the Gate's exact confirmed original status request."""
    from flask import request
    from lumenis.shared.database import get_repository
    try:
        if scope != {'scope_kind': 'shared_workspace', 'version': 1} or request.method != 'POST':
            return False
        status = {'account.api_enable_skill': 'enabled', 'account.api_disable_skill': 'disabled'}.get(request.endpoint)
        data = request.get_json(silent=True)
        skill_id = (request.view_args or {}).get('skill_id')
        if (status is None or type(data) is not dict or data.get('mode') != 'confirm'
                or set(data) != {'mode', 'operation_id', 'expected_binding', 'confirm', 'confirmed_resource'}
                or data.get('confirm') is not True or data.get('confirmed_resource') != resource):
            return False
        def valid(con):
            value = _prepare_builtin_status(con, skill_id, status, actor, data['operation_id'], data['expected_binding'])
            return value['resource'] == resource
        if connection is not None:
            return valid(connection)
        with get_repository().connection(read_only=True, wal=False) as con:
            return valid(con)
    except (ValueError, TypeError, LookupError, PermissionError, RuntimeError):
        return False


def confirm_builtin_skill_status(skill_id, status, *, actor, operation_id, expected_binding,
                                 confirmed_resource, confirm, same_origin):
    """Apply one explicit builtin opt-in through the current Gate and atomic audit."""
    from flask import request
    from lumenis.shared.database import get_repository
    from lumenis.system.security import permission
    if confirm is not True or same_origin is not True:
        raise PermissionError('SKILL_STATUS_EXACT_CONFIRMATION_REQUIRED')
    gate = permission.get_permission_gate()
    if (not gate.fail_closed or permission.is_testing_bypass_enabled()
            or not gate.has_permission(permission.PermissionLevel.HUMAN_APPROVAL)
            or not gate.has_permission(permission.PermissionLevel.COMMIT)):
        raise PermissionError('SKILL_STATUS_MANUAL_AUTHORITY_REQUIRED')
    scope = {'scope_kind': 'shared_workspace', 'version': 1}
    token, issued = None, False
    try:
        with get_repository().transaction(timeout=10) as connection:
            connection.execute('BEGIN IMMEDIATE')
            permission.authorize_shared_workspace(actor, scope, module='skills', action='write', connection=connection)
            prepared = _prepare_builtin_status(connection, skill_id, status, actor, operation_id, expected_binding)
            resource = prepared['resource']
            if confirmed_resource != resource:
                raise PermissionError('SKILL_STATUS_EXACT_RESOURCE_REQUIRED')
            token = gate.get_valid_approval_token(permission.OperationType.CONFIG_MODIFY.value, resource, exact=True)
            issued = token is None
            if issued:
                token = gate.grant_approval(permission.OperationType.CONFIG_MODIFY.value,
                    resource=resource, duration_minutes=5, granted_by=prepared['caller'])
            decision = permission.check_shared_workspace_effect(actor, scope, operation=permission.OperationType.CONFIG_MODIFY,
                resource=resource, module='skills', action='write', connection=connection, gate=gate)
            if not decision.allowed or not decision.audit_id:
                raise PermissionError('SKILL_STATUS_EFFECT_PERMISSION_DENIED')
            if not prepared['idempotent_hit']:
                connection.execute("UPDATE skills_registry SET status=?,updated_at=datetime('now','localtime') WHERE skill_id=?",
                                   (status, skill_id))
                event = {key: prepared[key] for key in ('schema', 'skill_id', 'status', 'operation_id',
                                                        'expected_binding', 'caller', 'resource')}
                connection.execute("INSERT INTO v4_audit_logs (user_id,username,action,resource,resource_id,detail,ip) "
                    "VALUES(?,?,'builtin_skill_status_confirm','skill',?,?,?)",
                    (actor.get('id') if isinstance(actor, dict) else None, prepared['caller'], operation_id,
                     json.dumps(event, ensure_ascii=False, sort_keys=True), request.remote_addr))
            _builtin_status_identity(actor, connection)
            permission.authorize_shared_workspace(actor, scope, module='skills', action='write', connection=connection)
            with gate.builtin_skill_status_commit_lease(token, resource=resource, caller=prepared['caller']):
                connection.commit()
            current = _builtin_status_row(connection, skill_id)
        return {**prepared, 'state': 'ALREADY_APPLIED' if prepared['idempotent_hit'] else 'APPLIED',
                'effect_performed': not prepared['idempotent_hit'], 'current_status': current['status']}
    except Exception:
        if issued and token is not None:
            gate.revoke_approval(token)
        raise

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
    # The bounded local execution lane is already implemented by these exact
    # Registry handlers. Discover them here as disabled account projections;
    # listing metadata never enables a Skill or runs an optional adapter.
    from lumenis.shared.agents.skills.registry import get_skill_registry
    from lumenis.shared.agents.skills.execution import _BACKGROUND_INPUTS, registered_background_contract
    projections = []
    registry = get_skill_registry()
    for skill_id in sorted(_BACKGROUND_INPUTS):
        metadata = registry.get(skill_id)
        if metadata is None:
            continue
        contract = registered_background_contract({'skill_id': skill_id,
            'input_schema_json': '{}', 'output_schema_json': json.dumps(metadata.output_schema)})
        projections.append((metadata, contract))
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
        for metadata, contract in projections:
            conn.execute('''INSERT OR IGNORE INTO skills_registry
                (skill_id,name,description,product,domain,status,version,source,source_type,runtime,
                 input_schema_json,output_schema_json)
                VALUES(?,?,?,?,?,'disabled',?,'builtin','builtin','builtin',?,?)''',
                (metadata.skill_id, metadata.skill_id, metadata.description, metadata.product, metadata.domain,
                 metadata.version, json.dumps(contract['input_schema'], ensure_ascii=False),
                 json.dumps(contract['output_schema'], ensure_ascii=False)))
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
        from lumenis.shared.agents.skills.lifecycle import _hash as registry_hash
        info["registry_sha256"] = registry_hash(info)
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
                      user_role: str = "user", product: str = None, *,
                      _execution_id=None, _background=False, _agent_task_id=None, _workspace_principal=None, scope=None, _local_only=False,
                      _execution_control=None) -> dict:
    """执行 Skill（走完整执行链：Permission→Firewall→Effect Fence→Execute→Evidence→Evaluation→Trace）"""
    from lumenis.shared.agents.skills.execution import (
        run_execution_chain, ActionType, SkillRuntimeInfo, registered_background_handler,
    )
    if _execution_control is not None:
        from agent_runtime.loop import StepExecutionControl
        if type(_execution_control) is not StepExecutionControl:
            raise PermissionError('TOOL_EXECUTION_CONTROL_INVALID')
        _execution_control.check()
    if _workspace_principal is not None:
        return _execute_local_agent_skill(skill_id, task, input_payload or {}, action_type,
            _execution_id, _agent_task_id, _workspace_principal, local_only=_local_only, execution_control=_execution_control)
    # 获取 Skill 信息用于权限检查
    info = get_skill_info(skill_id)
    if not info:
        return {"success": False, "error": f"skill '{skill_id}' not found", "code": "NOT_FOUND"}

    # Derive identity from the active account record and check the requested
    # product lens against the member authorization matrix. The request body
    # and a caller-supplied role are never authorization sources.
    if not isinstance(user_id, int) or user_id <= 0:
        return {"success": False, "error": "authenticated actor required", "code": "ACTOR_REQUIRED"}
    try:
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT role, status FROM v4_users WHERE id=?", (user_id,)
            ).fetchone()
        finally:
            conn.close()
    except Exception:
        row = None
    if not row or row["status"] != "active" or row["role"] not in ("owner", "admin", "user"):
        return {"success": False, "error": "active authenticated actor required", "code": "ACTOR_INVALID"}
    actual_role = row["role"]
    agent_context = None
    if _agent_task_id is not None:
        try:
            from ai_task_engine import get_task_engine
            from agent_runtime.task_binding import authorized_context
            original = get_task_engine().get_task(_agent_task_id)
            if not isinstance(original, dict):
                raise PermissionError('AGENT_TASK_UNAVAILABLE')
            agent_context = authorized_context(original, {'id': user_id})
            if (agent_context['actor_id'] != user_id or _background
                    or (scope is not None and scope != agent_context['scope'])
                    or task != original['user_input']):
                raise PermissionError('AGENT_SKILL_BINDING_INVALID')
            scope = dict(agent_context['scope'])
        except (PermissionError, ValueError, KeyError, TypeError):
            return {'success': False, 'error': 'Agent task binding denied', 'code': 'AGENT_SKILL_SCOPE_DENIED'}

    requested_product = str(product or info.get("product") or "").strip().upper()
    if requested_product == 'SHARED':
        from lumenis.shared.agents.skills.execution import _BACKGROUND_INPUTS
        if (skill_id in _BACKGROUND_INPUTS and str(info.get('runtime') or 'builtin').lower() == 'builtin'
                and str(info.get('source') or 'builtin').lower() == 'builtin'):
            # A local Shared helper needs its own SYSTEM Skill permission, not
            # an invented business Subject or a borrowed CTH/BMP context.
            requested_product = 'SYSTEM'
    product_map = {
        "CTH": ("CTH", "cth"),
        "BMP": ("ZBMP", "zbmp"),
        "ZBMP": ("ZBMP", "zbmp"),
        "SYSTEM": ("SYSTEM", "system"),
    }
    selected_scope = product_map.get(requested_product)
    if not selected_scope or requested_product == "SHARED":
        return {"success": False, "error": "select an authorized CTH, BMP or SYSTEM context", "code": "PRODUCT_CONTEXT_REQUIRED"}
    product_id, domain_id = selected_scope
    if agent_context is not None and (product_id != agent_context['product'] or domain_id != agent_context['domain_id']):
        return {'success': False, 'error': 'Agent task product mismatch', 'code': 'AGENT_SKILL_SCOPE_DENIED'}

    at_name = str(action_type or "ANALYZE").upper()
    if actual_role == "user" and at_name in {"COMMIT", "PUSH"}:
        return {
            "success": False,
            "error": "explicit product admin role required for commit or push",
            "code": "DOMAIN_ROLE_REQUIRED",
        }

    try:
        from account.authorization import check_dual_domain_permission
        access_action = "write" if at_name in {"WRITE", "COMMIT", "PUSH"} else "read"
        if not check_dual_domain_permission(
            user_id, product_id, module=skill_id, action=access_action
        ):
            return {"success": False, "error": "product scope permission denied", "code": "PRODUCT_SCOPE_DENIED"}
    except Exception:
        return {"success": False, "error": "product scope permission unavailable", "code": "PRODUCT_SCOPE_UNAVAILABLE"}

    if _local_only:
        from lumenis.shared.agents.skills.execution import _BACKGROUND_INPUTS, validate_source_free_input
        if (skill_id not in _BACKGROUND_INPUTS or (input_payload is not None and not isinstance(input_payload, dict))
                or set(input_payload or {}) - _BACKGROUND_INPUTS[skill_id]
                or at_name not in {"READ", "ANALYZE"}
                or str(info.get("runtime") or "builtin").lower() != "builtin"
                or str(info.get("source") or "builtin").lower() != "builtin"):
            return {"success": False, "code": "SOURCE_READER_UNBOUND", "error": "Source reader is not bound"}
        try:
            validate_source_free_input(skill_id, input_payload or {})
        except PermissionError:
            return {"success": False, "code": "SOURCE_READER_UNBOUND", "error": "Source reader is not bound"}
    from lumenis.shared.agents.skills.execution import _background_binding, _BACKGROUND_INPUTS
    local_binding = _background_binding(info)
    bounded_builtin = (skill_id in _BACKGROUND_INPUTS
        and str(info.get('runtime') or 'builtin').lower() == 'builtin'
        and str(info.get('source') or 'builtin').lower() == 'builtin')
    trusted_cross_domain = []
    if bounded_builtin:
        from lumenis.shared.agents.skills.registry import get_skill_registry
        metadata = get_skill_registry().get(skill_id)
        if metadata is not None:
            trusted_cross_domain = list(metadata.cross_domain_allowed)
    runtime_config = dict(info.get("config") or {})
    if "registry_sha256" in info:
        runtime_config["registry_sha256"] = info["registry_sha256"]
    for key in (
        "runtime", "source", "source_type", "entrypoint", "install_path",
        "active_version", "version", "tools_json", "permissions_granted_json",
        "input_schema_json", "output_schema_json", "compatibility_json",
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
        cross_domain_allowed=trusted_cross_domain,
    )

    # 映射 action_type
    try:
        at = ActionType(action_type.upper())
    except ValueError:
        return {"success": False, "error": "unknown action type", "code": "ACTION_TYPE_INVALID"}

    # Domain permission roles are derived only from active server-side account
    # state and the exact module/action matrix checked above. A module WRITE
    # grant maps to a narrow writer role, never to a domain-wide admin role.
    if product_id == "CTH":
        permission_role = (
            "cth_admin" if actual_role in ("owner", "admin") else
            "cth_operator" if access_action == "write" else "cth_analyst"
        )
    elif product_id == "ZBMP":
        permission_role = (
            "zbmp_admin" if actual_role in ("owner", "admin") else
            "zbmp_operator" if access_action == "write" else "zbmp_analyst"
        )
    else:
        permission_role = (
            "system_admin" if actual_role in ("owner", "admin") else
            "system_writer" if access_action == "write" else "system_operator"
        )

    if _background:
        from lumenis.shared.agents.skills.execution import enqueue_registered_skill
        return enqueue_registered_skill(skill_id=skill_id, task=task,
            input_payload=input_payload or {}, action_type=at, user_id=user_id,
            product=product_id, domain=domain_id, skill_info=info, scope=scope)

    try:
        ctx = run_execution_chain(
            skill_id=skill_id,
            task=task,
            input_payload=input_payload or {},
            action_type=at,
            user_id=user_id,
            user_role=actual_role,
            product=product_id,
            domain=domain_id,
            permission_role=permission_role,
            skill_info=skill_runtime,
            execution_id=_execution_id,
            request_context=({"skill_scope": scope, "agent_task_id": _agent_task_id} if agent_context is not None
                             else {"skill_scope": scope} if scope is not None else None),
            handler=registered_background_handler(skill_id) if _execution_id is not None or _local_only or bounded_builtin else None,
            execution_control=_execution_control,
        )
    except Exception:
        if scope is None:
            raise
        # Exception text can contain handler-derived data just as a failed
        # return value can. Do not publish it outside the execution owner.
        return {"success": False, "execution_id": _execution_id, "status": "failed",
                "skill_id": skill_id, "result": None, "evidence": None,
                "evaluation": None, "error": "SKILL_RESULT_NOT_AUTHORIZED"}

    if _local_only and ctx.status.value == "completed":
        from lumenis.shared.agents.skills.execution import _record_source_free_execution, read_source_free_execution, query_executions
        try:
            if _background_binding(get_skill_info(skill_id)) != local_binding:
                raise PermissionError("SKILL_PRODUCER_CHANGED")
            _record_source_free_execution(ctx, registry_binding=local_binding)
            rows = query_executions(execution_id=ctx.execution_id, limit=1, strict=True)
            if not rows or read_source_free_execution(rows[0], {"id": user_id}) is None:
                raise PermissionError("SKILL_PRODUCER_READ_DENIED")
            # SYSTEM has no domain scope receipt. It still returns exactly the
            # sanitized, producer-signed durable projection, never raw memory.
            ctx.execute_result = json.loads(rows[0]['output_json'])
            ctx.evidence = json.loads(rows[0]['evidence_json'] or 'null')
            ctx.evaluation = json.loads(rows[0]['evaluation_json'] or 'null')
        except Exception:
            return {"success": False, "execution_id": ctx.execution_id, "status": "failed",
                    "result": None, "error": "SOURCE_READER_UNBOUND"}

    # Scoped outputs cross this API boundary only after durable signed proof and
    # live read authorization. A failed receipt must not leak handler data through
    # an error response, evidence summary, or an Agent's failed checkpoint.
    if scope is not None and ctx.execute_result is not None:
        from lumenis.shared.agents.skills.execution import query_executions, verified_execution_scope, _trace_json
        try:
            rows = query_executions(execution_id=ctx.execution_id, limit=1, strict=True)
            readable = (ctx.status.value == "completed" and rows
                        and verified_execution_scope(rows[0], {"id": user_id})
                        and json.loads(rows[0]['output_json']) == json.loads(_trace_json(ctx.execute_result)))
        except Exception:
            readable = False
        if not readable:
            return {"success": False, "execution_id": ctx.execution_id,
                    "status": "failed", "skill_id": skill_id, "result": None,
                    "evidence": None, "evaluation": None,
                    "error": (ctx.error if ctx.error in {
                        "SKILL_EXECUTION_TRACE_FINALIZATION_FAILED", "EVIDENCE_RECORD_FAILED"}
                        else "SKILL_RESULT_NOT_AUTHORIZED")}
        # The durable owner already sanitized these fields before signing. Return
        # that exact projection, never the unsanitized in-memory handler value.
        ctx.execute_result = json.loads(rows[0]['output_json'])
        ctx.evidence = json.loads(rows[0]['evidence_json'] or 'null')
        ctx.evaluation = json.loads(rows[0]['evaluation_json'] or 'null')

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


def prepare_skill_metadata_change(skill_id: str, action: str, **kwargs):
    """Compatibility delegate; a prepared candidate is not an approved change."""
    from lumenis.shared.agents.skills.lifecycle import prepare_skill_metadata_change as prepare
    return prepare(skill_id, action, **kwargs)


def read_skill_version_history(skill_id: str, *, limit: int = 50) -> list:
    """Read the existing signed history through the canonical Shared owner."""
    from lumenis.shared.agents.skills.lifecycle import read_skill_version_history as read_history
    return read_history(skill_id, limit=limit)


def apply_skill_metadata_change(candidate, **kwargs) -> dict:
    """Delegate actual admission and mutation to the existing Shared owner."""
    from lumenis.shared.agents.skills.lifecycle import apply_skill_metadata_change as apply_change
    return apply_change(candidate, **kwargs)


def recover_skill_metadata_candidate(skill_id: str, evidence_ref: str):
    """Recover a signed candidate; this delegate grants no execution permission."""
    from lumenis.shared.agents.skills.lifecycle import recover_skill_metadata_candidate as recover
    return recover(skill_id, evidence_ref)


def _execute_local_agent_skill(skill_id, task, inputs, action_type, execution_id, task_id, principal, *, local_only=False, execution_control=None):
    """Only the original server Agent task may invoke five bounded local tools."""
    from agent_runtime.task_binding import authorized_context, _current_binding, _digest
    from ai_task_engine import get_task_engine
    from lumenis.shared.agents.skills.execution import (run_execution_chain, ActionType,
        registered_background_handler, _BACKGROUND_INPUTS)
    original = get_task_engine().get_task(task_id)
    context = authorized_context(original, principal)
    _current_binding(task_id, skill_id)
    expected = 'agentstep_' + _digest({'task': task_id, 'skill': skill_id, 'inputs': inputs})[:32]
    if (context['actor_id'] is not None or skill_id not in _BACKGROUND_INPUTS
            or set(inputs) - _BACKGROUND_INPUTS[skill_id] or action_type != 'READ'
            or execution_id != expected or original['status'] == 'cancelled'):
        raise PermissionError('LOCAL_AGENT_SKILL_BINDING_INVALID')
    from lumenis.shared.agents.skills.execution import (_background_binding, _record_source_free_execution,
                                                        validate_source_free_input)
    local_info = get_skill_info(skill_id)
    if local_only:
        validate_source_free_input(skill_id, inputs)
        if (str(local_info.get('runtime') or 'builtin').lower() != 'builtin'
                or str(local_info.get('source') or 'builtin').lower() != 'builtin'):
            raise PermissionError('SOURCE_READER_UNBOUND')
    local_binding = _background_binding(local_info)
    ctx = run_execution_chain(skill_id=skill_id, task=original['user_input'], input_payload=inputs,
        action_type=ActionType.READ, user_id=None, user_role='user', product=context['product'],
        domain=context['domain_id'], permission_role=context['role'],
        request_context={'agent_task_id': task_id}, workspace_principal=principal,
        execution_id=execution_id, handler=registered_background_handler(skill_id), execution_control=execution_control)
    if local_only and ctx.status.value == 'completed':
        _current_binding(task_id, skill_id)
        if _background_binding(get_skill_info(skill_id)) != local_binding:
            raise PermissionError('SKILL_PRODUCER_CHANGED')
        _record_source_free_execution(ctx, registry_binding=local_binding)
        from lumenis.shared.agents.skills.execution import query_executions, read_source_free_execution
        rows = query_executions(execution_id=ctx.execution_id, limit=1, strict=True)
        if not rows or read_source_free_execution(rows[0], principal) is None:
            raise PermissionError('SKILL_PRODUCER_READ_DENIED')
        ctx.execute_result = json.loads(rows[0]['output_json'])
        ctx.evidence = json.loads(rows[0]['evidence_json'] or 'null')
        ctx.evaluation = json.loads(rows[0]['evaluation_json'] or 'null')
    return {'success': ctx.status.value == 'completed', 'execution_id': ctx.execution_id,
            'status': ctx.status.value, 'result': ctx.execute_result, 'error': ctx.error}
