"""
V4 升级模块蓝图总入口
注册所有V4新模块的路由，不修改现有app.py
用法（在app.py末尾添加）:
    from lumenis import create_v4_blueprint
    app.register_blueprint(create_v4_blueprint())
"""
from flask import Blueprint, jsonify, request, send_file, g
from .auth import (
    login, login_by_key, logout, get_current_user, require_auth, require_owner,
    create_user, list_users, ensure_initialized, log_audit
)
from .auth.workspace import (
    verify_workspace_key, issue_workspace_key, list_workspace_keys,
    revoke_workspace_key, grant_session, session_can_access,
)
from .settings import settings_bp
from .collect import collect_bp
from .importer import importer_bp
from .ai_hub import ai_bp
from .console import console_bp
from .version_center import version_bp, start_version_watcher
from .adapters import registry, register_default_adapters
from .adapters import collector_service
from .adapters import auth_recovery
from .adapters.risk_controller import risk_controller
from .config import AUTH_CONFIG


def create_v4_blueprint() -> Blueprint:
    """创建V4总蓝图"""
    # V4 只提供 Product Core/API 路由；用户界面由 Flutter App 承载。
    v4_bp = Blueprint("v4", __name__, url_prefix="/v4")

    # 注册子蓝图
    v4_bp.register_blueprint(settings_bp)
    v4_bp.register_blueprint(collect_bp)
    v4_bp.register_blueprint(importer_bp)
    v4_bp.register_blueprint(ai_bp)
    v4_bp.register_blueprint(console_bp)  # 含 /v4/ 与 /v4/console/ 统一控制台
    v4_bp.register_blueprint(version_bp)  # 版本中心 /v4/version-center/

    # ============ 认证API ============

    @v4_bp.route("/auth/login", methods=["POST"])
    def api_login():
        """登录接口"""
        data = request.get_json() or {}
        result = login(
            username=data.get("username", ""),
            password=data.get("password", ""),
            ip=request.remote_addr,
            user_agent=request.headers.get("User-Agent", ""),
        )
        if result["success"]:
            log_audit("login", "auth", None, f"用户 {data.get('username')} 登录成功")
        resp = jsonify(result)
        # 登录成功写会话 Cookie：浏览器地址栏直接打开/跳转设置页文档时也能带凭证
        # （get_current_user 本就支持 Header 或 Cookie 双通道，此处补齐登录侧 Set-Cookie）
        if result.get("success") and result.get("token"):
            resp.set_cookie(
                AUTH_CONFIG["session_cookie_name"], result["token"],
                max_age=AUTH_CONFIG["token_expire_hours"] * 3600,
                httponly=True, samesite="Lax", path="/",
            )
        return resp

    @v4_bp.route("/auth/login-by-key", methods=["POST"])
    def api_login_by_key():
        """密钥登录（第二登录方式，替代短信验证码）：密钥正确即以主账号身份登录"""
        data = request.get_json() or {}
        result = login_by_key(
            access_key=data.get("access_key", ""),
            ip=request.remote_addr,
            user_agent=request.headers.get("User-Agent", ""),
        )
        if result.get("success"):
            log_audit("login_by_key", "auth", None, "主账号通过密钥登录")
        resp = jsonify(result)
        if result.get("success") and result.get("token"):
            resp.set_cookie(
                AUTH_CONFIG["session_cookie_name"], result["token"],
                max_age=AUTH_CONFIG["token_expire_hours"] * 3600,
                httponly=True, samesite="Lax", path="/",
            )
        return resp

    @v4_bp.route("/auth/logout", methods=["POST"])
    @require_auth
    def api_logout():
        """登出接口"""
        user = get_current_user()
        token = user.get("token", "") if user else ""
        if token:
            logout(token)
            log_audit("logout", "auth", None, f"用户 {user['username']} 登出")
        resp = jsonify({"success": True})
        resp.delete_cookie(AUTH_CONFIG["session_cookie_name"], path="/")
        return resp

    @v4_bp.route("/auth/me", methods=["GET"])
    @require_auth
    def api_me():
        """获取当前用户信息"""
        user = get_current_user()
        return jsonify({"success": True, "user": user})

    # ---- 受限工作区（ZBMP）访问密钥 ----
    @v4_bp.route("/auth/workspace/unlock", methods=["POST"])
    def api_workspace_unlock():
        """Grant workspace access to an already logged-in session.

        A shared workspace key never creates or upgrades a login: without a
        session the request is refused, and failed key guesses are rate
        limited per IP with the same lockout as login.
        """
        from .config import WORKSPACE_CONFIG
        from .auth.security import (
            check_login_attempts, record_login_attempt, normalize_login_ip,
            WORKSPACE_KEY_ATTEMPT_USERNAME,
        )
        user = get_current_user()
        if not user:
            return jsonify({"success": False, "error": "请先登录，再输入工作区密钥"}), 401
        data = request.get_json(silent=True) or {}
        ws = (data.get("workspace") or "ZBMP").strip().upper()
        key = (data.get("key") or "").strip()
        bucket = WORKSPACE_KEY_ATTEMPT_USERNAME
        ip = normalize_login_ip(request.remote_addr)
        check = check_login_attempts(bucket, ip)
        if not check["allowed"]:
            return jsonify({"success": False, "error": "尝试过多已锁定，请稍后再试", "remaining": 0}), 429
        rec = verify_workspace_key(ws, key)
        if not rec:
            record_login_attempt(bucket, ip, False)
            log_audit("workspace_unlock_denied", "auth", ws, "workspace key invalid")
            return jsonify({"success": False, "error": "工作区密钥无效或已吊销/过期"}), 401
        record_login_attempt(bucket, ip, True)
        gres = grant_session(user["id"], ws, rec["id"], user["token"], WORKSPACE_CONFIG["grant_hours"])
        log_audit("workspace_unlock", "auth", ws, "unlock workspace " + ws)
        return jsonify({"success": True, "workspace": ws, "granted": True,
                        "expires_at": gres["expires_at"],
                        "user": {"username": user["username"], "role": user["role"]}})

    @v4_bp.route("/auth/workspace/status", methods=["GET"])
    def api_workspace_status():
        from .config import WORKSPACE_CONFIG
        user = get_current_user()
        workspaces = {w: True for w in WORKSPACE_CONFIG["default_workspaces"]}
        workspaces["ZBMP"] = bool(user and session_can_access(user.get("token", ""), "ZBMP"))
        return jsonify({"success": True, "workspaces": workspaces, "logged_in": bool(user),
                        "user": ({"username": user["username"], "role": user["role"]} if user else None)})

    @v4_bp.route("/auth/workspace/keys", methods=["GET"])
    @require_owner
    def api_workspace_keys_list():
        ws = (request.args.get("workspace") or "").strip().upper() or None
        return jsonify({"success": True, "keys": list_workspace_keys(ws)})

    @v4_bp.route("/auth/workspace/keys", methods=["POST"])
    @require_owner
    def api_workspace_keys_issue():
        data = request.get_json(silent=True) or {}
        ws = (data.get("workspace") or "ZBMP").strip().upper()
        out = issue_workspace_key(ws, data.get("label", ""), g.current_user["id"], data.get("expires_days"))
        if not out.get("success"):
            return jsonify(out), 400
        log_audit("workspace_key_issue", "auth", ws, "issue key #" + str(out["id"]))
        return jsonify(out)

    @v4_bp.route("/auth/workspace/keys/revoke", methods=["POST"])
    @require_owner
    def api_workspace_keys_revoke():
        data = request.get_json(silent=True) or {}
        kid = data.get("id")
        if not kid:
            return jsonify({"success": False, "error": "missing id"}), 400
        revoke_workspace_key(kid)
        log_audit("workspace_key_revoke", "auth", None, "revoke key #" + str(kid))
        return jsonify({"success": True})

    # ============ 采集适配器API ============

    @v4_bp.route("/adapters/platforms", methods=["GET"])
    @require_auth
    def api_list_platforms():
        """列出所有采集平台"""
        ensure_initialized()
        if not registry.list_platforms():
            register_default_adapters()
        return jsonify({
            "success": True,
            "platforms": registry.get_all_status(),
        })

    @v4_bp.route("/adapters/search", methods=["POST"])
    @require_auth
    def api_adapter_search():
        """多平台搜索采集"""
        data = request.get_json() or {}
        keyword = data.get("keyword", "")
        max_results = data.get("max_results", 20)
        platforms = data.get("platforms")  # None表示全部

        if not keyword:
            return jsonify({"success": False, "error": "关键词不能为空"}), 400

        if not registry.list_platforms():
            register_default_adapters()

        results = registry.search_all(keyword, max_results, platforms)
        # 转换为可序列化格式
        output = {}
        for platform, result in results.items():
            output[platform] = {
                "success": result.success,
                "error": result.error,
                "count": len(result.notes),
                "notes": [
                    {
                        "title": n.title, "content": n.content, "url": n.url,
                        "author": n.author, "publish_date": n.publish_date,
                        "likes": n.likes, "comments": n.comments,
                        "source_platform": n.source_platform,
                    }
                    for n in result.notes
                ],
            }
        log_audit("adapter_search", "collection", None, f"关键词: {keyword}, 平台: {platforms or '全部'}")
        return jsonify({"success": True, "keyword": keyword, "results": output})

    @v4_bp.route("/adapters/search-merged", methods=["POST"])
    @require_auth
    def api_adapter_search_merged():
        """多平台搜索合并去重"""
        data = request.get_json() or {}
        keyword = data.get("keyword", "")
        max_results = data.get("max_results", 20)
        platforms = data.get("platforms")

        if not keyword:
            return jsonify({"success": False, "error": "关键词不能为空"}), 400

        if not registry.list_platforms():
            register_default_adapters()

        notes, platform_status = registry.search_all_with_status(keyword, max_results, platforms)
        return jsonify({
            "success": True,
            "keyword": keyword,
            "total": len(notes),
            # 每平台 SUCCESS/EMPTY/FAIL 与错误如实回传，失败绝不被合并成“0条”
            "platforms": platform_status,
            "notes": [
                {"title": n.title, "content": n.content, "url": n.url,
                 "author": n.author, "source_platform": n.source_platform}
                for n in notes
            ],
        })

    # ============ 后台采集 + 全局健康（生产级流水线） ============

    @v4_bp.route("/adapters/collect", methods=["POST"])
    @require_auth
    def api_adapter_collect():
        """启动一次后台采集任务（立即返回 task_id，前端轮询进度，结果直接入库）。"""
        data = request.get_json(silent=True)
        if (not isinstance(data, dict) or set(data) - {"keyword", "platforms", "max_results", "confirm_read_only"}
                or data.get("confirm_read_only") is not True):
            return jsonify({"success": False, "error": "EXPLICIT_READ_ONLY_REQUEST_REQUIRED"}), 400
        try:
            from lumenis.system.security.permission import resolve_web_request_scope
            actor, scope, _, _ = resolve_web_request_scope("write", module="collector")
            # This authenticated compatibility route never serializes a local
            # principal or trusts an actor identifier supplied in request JSON.
            if not isinstance(actor, dict) or actor.get("id") != g.current_user.get("id"):
                raise PermissionError("AUTH_REQUIRED")
            task_id = collector_service.start_collect(
                data.get("keyword"), data.get("platforms"), data.get("max_results", 20),
                actor=actor, scope=scope)
        except collector_service.CollectorAdmissionError as exc:
            return jsonify({"success": False, **exc.result}), 403
        except PermissionError as exc:
            return jsonify({"success": False, "error": str(exc)}), 403
        except (TypeError, ValueError) as exc:
            return jsonify({"success": False, "error": str(exc)}), 400
        return jsonify({"success": True, "task_id": task_id})

    def _authorized_collector_task(task_id, action):
        from lumenis.system.security.permission import resolve_web_request_scope
        actor, scope, _, _ = resolve_web_request_scope(action, module="collector")
        if (not isinstance(actor, dict) or actor.get("id") != g.current_user.get("id")
                or collector_service.get_task_owner(task_id) != "actor:" + str(actor["id"])):
            raise PermissionError("TASK_NOT_FOUND")
        task = collector_service.get_task(task_id)
        if not task or task.get("scope") != scope:
            raise PermissionError("TASK_NOT_FOUND")
        return actor, scope, task

    @v4_bp.route("/adapters/task/<task_id>", methods=["GET"])
    @require_auth
    def api_adapter_task(task_id):
        """Read only the current actor's exact scoped durable task."""
        try:
            _, _, task = _authorized_collector_task(task_id, "read")
        except (PermissionError, ValueError):
            return jsonify({"success": False, "error": "TASK_NOT_FOUND"}), 404
        return jsonify({"success": True, "task": task})

    @v4_bp.route("/adapters/task/<task_id>/resume", methods=["POST"])
    @require_auth
    def api_adapter_task_resume(task_id):
        data = request.get_json(silent=True)
        if type(data) is not dict or set(data) != {"confirm_read_only"} or data.get("confirm_read_only") is not True:
            return jsonify({"success": False, "error": "EXPLICIT_READ_ONLY_REQUEST_REQUIRED"}), 400
        try:
            actor, scope, _ = _authorized_collector_task(task_id, "write")
            task = collector_service.resume_collect(task_id, actor=actor, scope=scope)
        except collector_service.CollectorAdmissionError as exc:
            return jsonify({"success": False, **exc.result}), 403
        except (PermissionError, ValueError):
            return jsonify({"success": False, "error": "TASK_NOT_FOUND"}), 404
        return jsonify({"success": True, "task": task})

    @v4_bp.route("/adapters/health", methods=["GET"])
    @require_auth
    def api_adapter_health():
        """全局采集健康状态中心：每平台最近六态/数量/时间/熔断态。"""
        return jsonify({"success": True, "health": collector_service.get_health()})

    @v4_bp.route("/adapters/recovery/start", methods=["POST"])
    @require_auth
    def api_recovery_start():
        """打开指定平台登录页并启动后台恢复探测（统一 Auth Recovery Center）。
        入参可带 source_state(六态)/detail，用于 A登录/B验证/C熔断 三类分清。"""
        body = request.get_json() or {}
        platform = body.get("platform", "")
        result = auth_recovery.request_recovery(
            platform, source_state=body.get("source_state", ""),
            detail=body.get("detail", ""))
        if not result.get("success"):
            return jsonify(result), 400
        log_audit("auth_recovery_start", "collection", None,
                  f"发起 {platform} 登录恢复 kind={result.get('kind')}")
        return jsonify(result)

    @v4_bp.route("/adapters/recovery/platforms", methods=["GET"])
    @require_auth
    def api_recovery_platforms():
        """可恢复真人平台清单（新增平台只改后端配置，前端自动列出）。"""
        return jsonify({"success": True, "platforms": auth_recovery.recovery_platforms()})

    @v4_bp.route("/adapters/recovery/health/<platform>", methods=["GET"])
    @require_auth
    def api_recovery_health(platform):
        """主动探测某平台登录态：AUTH_VALID/EXPIRED/UNKNOWN（不改风险状态）。"""
        return jsonify(auth_recovery.health_check(platform))

    @v4_bp.route("/adapters/recovery/check", methods=["POST"])
    @require_auth
    def api_recovery_check():
        """立即探测一次某平台登录态是否已恢复。"""
        platform = (request.get_json() or {}).get("platform", "")
        return jsonify(auth_recovery.check_recovery(platform))

    @v4_bp.route("/adapters/recovery/cancel", methods=["POST"])
    @require_auth
    def api_recovery_cancel():
        platform = (request.get_json() or {}).get("platform", "")
        auth_recovery.cancel_recovery(platform)
        return jsonify({"success": True})

    @v4_bp.route("/adapters/recovery/status", methods=["GET"])
    @require_auth
    def api_recovery_status():
        """当前所有登录恢复任务状态。"""
        return jsonify({"success": True, "tasks": auth_recovery.recovery_status()})

    @v4_bp.route("/adapters/recovery/shot/<platform>", methods=["GET"])
    @require_auth
    def api_recovery_shot(platform):
        """登录截图：优先返回裁剪二维码，无则回退整页登录截图。"""
        qr_only = request.args.get("qr") == "1"
        qr, full = auth_recovery.shot_paths(platform)
        p = qr if qr else ("" if qr_only else full)
        if not p:
            return jsonify({"success": False, "error": "截图尚未生成"}), 404
        return send_file(p, mimetype="image/png")

    @v4_bp.route("/adapters/risk", methods=["GET"])
    @require_auth
    def api_risk_snapshot():
        """动态风控状态机快照。"""
        return jsonify({"success": True, "risk": risk_controller.snapshot()})

    # ============ 数据清洗API ============

    @v4_bp.route("/data/fix-publish-date", methods=["POST"])
    @require_owner
    def api_fix_publish_date():
        """修复publish_date脏数据"""
        from .data_cleanup import fix_publish_dates
        data = request.get_json() or {}
        dry_run = data.get("dry_run", True)
        result = fix_publish_dates(dry_run=dry_run)
        log_audit("fix_publish_date", "data", None, f"dry_run={dry_run}, 修复{result['dirty_count']}条")
        return jsonify(result)

    @v4_bp.route("/data/empty-content", methods=["GET"])
    @require_auth
    def api_empty_content():
        """查询空正文笔记"""
        from .data_cleanup import find_empty_content_notes
        result = find_empty_content_notes()
        return jsonify(result)

    @v4_bp.route("/data/backfill-tasks", methods=["GET"])
    @require_auth
    def api_backfill_tasks():
        """生成补抓任务批次"""
        from .data_cleanup import generate_backfill_tasks
        batch_size = request.args.get("batch_size", 10, type=int)
        result = generate_backfill_tasks(batch_size)
        return jsonify(result)

    # ============ 健康检查 ============

    @v4_bp.route("/health", methods=["GET"])
    def api_health():
        """V4模块健康检查"""
        ensure_initialized()
        return jsonify({
            "success": True,
            "version": "4.0.0",
            "auth_db": "ok",
            "adapters": len(registry.list_platforms()),
        })

    return v4_bp


def init_v4_modules():
    """初始化所有V4模块（建表等）"""
    ensure_initialized()
    register_default_adapters()
    # 启动版本中心自动保存守护（检测源码变化→自动成版本→自动推送；内部已做异常隔离）
    try:
        start_version_watcher()
    except Exception as e:  # noqa: BLE001
        print(f"[v4] 版本守护未启动(不影响主系统): {e}")
