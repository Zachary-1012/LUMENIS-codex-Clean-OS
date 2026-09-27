# -*- coding: utf-8 -*-
"""
ZBC AI Browser Runtime API — REST Contract
=============================================
新增路由（兼容已有 browser-surface / browser-runtime 路由，不冲突）：

  POST   /api/browser/sessions                              创建 Session
  GET    /api/browser/sessions/<session_id>                 Session 状态
  POST   /api/browser/sessions/<session_id>/navigate        导航
  POST   /api/browser/sessions/<session_id>/observe         观察页面（脱敏）
  POST   /api/browser/sessions/<session_id>/action          执行 Action（带 Verification）
  POST   /api/browser/sessions/<session_id>/verify          验证状态
  POST   /api/browser/sessions/<session_id>/stop            关闭 Session
  GET    /api/browser/sessions/<session_id>/evidence        Evidence 列表
  GET    /api/browser/sessions                                 列出所有 Session
  GET    /api/browser/security/status                         安全状态（Firewall/Injection/CB）
  GET    /api/browser/evidence/stats                          Evidence 统计

设计原则：
  - 所有响应中的页面内容经过敏感信息脱敏
  - 所有写操作经过 Action Firewall + Permission Gate
  - 失败不静默，返回分类错误和 Recovery 状态
  - 不返回 Cookie/Token/Session 明文
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def register_ai_browser_api(app):
    """在 Flask app 上注册 AI Browser Runtime API 蓝图。"""
    from flask import Blueprint, g, jsonify, request

    bp = Blueprint("ai_browser_runtime", __name__)

    @bp.before_request
    def _require_browser_actor():
        """Bind every AI Browser request to an active account and SYSTEM grant."""
        try:
            from account.service import get_current_user
            from account.authorization import check_dual_domain_permission

            actor = get_current_user()
            if not actor or type(actor.get("id")) is not int or type(actor.get("session_id")) is not int:
                return jsonify({"ok": False, "error_code": "BROWSER_ACTOR_REQUIRED"}), 401
            action = "read" if request.method == "GET" else "write"
            if not check_dual_domain_permission(actor["id"], "SYSTEM", module="browser", action=action):
                return jsonify({"ok": False, "error_code": "BROWSER_PERMISSION_DENIED"}), 403
            g.browser_actor_id = actor["id"]
            g.browser_account_session_id = actor["session_id"]
        except Exception:
            logger.exception("AI Browser actor authorization unavailable")
            return jsonify({"ok": False, "error_code": "BROWSER_PERMISSION_UNAVAILABLE"}), 503

    # 延迟导入（避免循环依赖）
    from ai_browser_runtime import (
        get_session_manager,
        get_evidence_store,
        get_action_firewall,
        get_injection_guard,
        BrowserActionType,
        ExpectedState,
        SessionStatus,
        sanitize_sensitive,
        sanitize_dict,
    )

    # ──────────────────────────────────────────────────────────
    # 辅助函数
    # ──────────────────────────────────────────────────────────

    def _get_session_or_404(session_id: str):
        """获取 Session，不存在返回 404。"""
        mgr = get_session_manager()
        session = mgr.get_session(session_id)
        if session is None:
            return None, (jsonify({
                "ok": False,
                "error": f"Session not found or expired: {session_id}",
                "error_code": "SESSION_NOT_FOUND",
            }), 404)
        if (session.owner_actor_id != g.browser_actor_id or
                session.owner_account_session_id != g.browser_account_session_id):
            return None, (jsonify({"ok": False, "error_code": "SESSION_NOT_FOUND"}), 404)
        return session, None

    def _parse_expected_state(data: Dict[str, Any]) -> Optional[ExpectedState]:
        """从请求 JSON 解析 ExpectedState。"""
        exp_data = data.get("expected") or data.get("expected_state")
        if not exp_data:
            return None
        element_text = None
        if "element_text" in exp_data and isinstance(exp_data["element_text"], (list, tuple)):
            element_text = tuple(exp_data["element_text"])
        input_value = None
        if "input_value" in exp_data and isinstance(exp_data["input_value"], (list, tuple)):
            input_value = tuple(exp_data["input_value"])
        element_count_gte = None
        if "element_count_gte" in exp_data and isinstance(exp_data["element_count_gte"], (list, tuple)):
            element_count_gte = tuple(exp_data["element_count_gte"])
        return ExpectedState(
            url_contains=exp_data.get("url_contains"),
            url_equals=exp_data.get("url_equals"),
            title_contains=exp_data.get("title_contains"),
            element_visible=exp_data.get("element_visible"),
            element_text=element_text,
            input_value=input_value,
            element_count_gte=element_count_gte,
            text_present=exp_data.get("text_present"),
            text_absent=exp_data.get("text_absent"),
            status_code=exp_data.get("status_code"),
            loading_complete=exp_data.get("loading_complete", True),
            custom_check=exp_data.get("custom_check"),
        )

    def _action_result_to_dict(result) -> Dict[str, Any]:
        """将 ActionExecutionResult 转为可序列化 dict（脱敏）。"""
        d = result.to_dict()
        if result.before_state:
            d["before_state"] = sanitize_dict(result.before_state.to_dict())
        if result.after_state:
            d["after_state"] = sanitize_dict(result.after_state.to_dict())
        return d

    # ──────────────────────────────────────────────────────────
    # 1. Session 管理
    # ──────────────────────────────────────────────────────────

    @bp.route("/api/browser/sessions", methods=["POST"])
    def create_session():
        """创建 Browser Session。

        Request JSON:
          - cdp_port: int (默认 9224，产品内置浏览器通用实例)
          - headless: bool (默认 True)
          - user_data_dir: str (可选，独立 profile 路径)
          - idle_timeout: int (秒，默认 600)
          - max_lifetime: int (秒，默认 3600)
          - auto_start: bool (是否自动启动浏览器，默认 True)
        """
        try:
            data = request.get_json(silent=True) or {}
            if (data.get("cdp_port", 9224) != 9224 or
                    data.get("headless", True) is not True or
                    data.get("user_data_dir") not in (None, "")):
                return jsonify({"ok": False, "error_code": "BROWSER_SESSION_BLOCKED",
                                "error": "AI Browser must use the isolated LUMENIS browser"}), 400
            mgr = get_session_manager()

            session = mgr.create_session(
                cdp_port=9224,
                headless=True,
                user_data_dir=None,
                owner_actor_id=g.browser_actor_id,
                owner_account_session_id=g.browser_account_session_id,
                idle_timeout=int(data.get("idle_timeout", 600)),
                max_lifetime=int(data.get("max_lifetime", 3600)),
            )

            started = False
            start_error = None
            if data.get("auto_start", True):
                try:
                    started = session.start()
                except Exception as e:
                    start_error = sanitize_sensitive(str(e)[:300])
                    logger.warning(f"[AI Browser API] Session 启动失败: {start_error}")

            if data.get("auto_start", True) and not started:
                failed_status = session.status.value
                mgr.close_session(session.session_id)
                return jsonify({
                    "ok": False,
                    "error_code": "BROWSER_START_UNAVAILABLE",
                    "status": failed_status,
                    "started": False,
                }), 503

            return jsonify({
                "ok": True,
                "session_id": session.session_id,
                "status": session.status.value,
                "started": started,
                "start_error": start_error,
                "cdp_port": session.cdp_port,
                "headless": session.headless,
                "idle_timeout": session.idle_timeout,
                "max_lifetime": session.max_lifetime,
                "message": "Session created. AI Browser Session与用户日常浏览Session隔离（独立profile）。"
                           if not start_error else f"Session created but start failed: {start_error}",
            })
        except Exception as e:
            logger.error(f"[AI Browser API] create_session error: {e}")
            return jsonify({"ok": False, "error": sanitize_sensitive(str(e)[:300])}), 500

    @bp.route("/api/browser/sessions", methods=["GET"])
    def list_sessions():
        """列出所有活跃 Session。"""
        try:
            mgr = get_session_manager()
            sessions = mgr.list_sessions_for_actor(
                g.browser_actor_id, g.browser_account_session_id)
            return jsonify({
                "ok": True,
                "count": len(sessions),
                "sessions": sessions,
            })
        except Exception as e:
            return jsonify({"ok": False, "error": sanitize_sensitive(str(e)[:300])}), 500

    @bp.route("/api/browser/sessions/<session_id>", methods=["GET"])
    def get_session_status(session_id: str):
        """获取 Session 状态。"""
        session, err = _get_session_or_404(session_id)
        if err:
            return err
        try:
            status = session.get_status()
            return jsonify({"ok": True, **status})
        except Exception as e:
            return jsonify({"ok": False, "error": sanitize_sensitive(str(e)[:300])}), 500

    @bp.route("/api/browser/sessions/<session_id>/stop", methods=["POST"])
    def stop_session(session_id: str):
        """关闭 Session。"""
        session, err = _get_session_or_404(session_id)
        if err:
            return err
        try:
            mgr = get_session_manager()
            closed = mgr.close_session(session_id)
            return jsonify({
                "ok": closed,
                "session_id": session_id,
                "closed": closed,
                "message": "Session closed" if closed else "Session not found",
            })
        except Exception as e:
            return jsonify({"ok": False, "error": sanitize_sensitive(str(e)[:300])}), 500

    # ──────────────────────────────────────────────────────────
    # 2. 导航
    # ──────────────────────────────────────────────────────────

    @bp.route("/api/browser/sessions/<session_id>/navigate", methods=["POST"])
    def navigate(session_id: str):
        """导航到 URL（带 Verification）。

        Request JSON:
          - url: str (必填)
          - expected: ExpectedState (可选)
          - task_id/run_id/step_id/agent_id/skill_id: 追踪字段
        """
        session, err = _get_session_or_404(session_id)
        if err:
            return err
        try:
            data = request.get_json(silent=True) or {}
            url = (data.get("url") or "").strip()
            if not url:
                return jsonify({"ok": False, "error": "url is required"}), 400

            expected = _parse_expected_state(data)
            result = session.navigate(
                url=url,
                expected=expected,
                task_id=data.get("task_id"),
                run_id=data.get("run_id"),
                step_id=data.get("step_id"),
                agent_id=data.get("agent_id"),
                skill_id=data.get("skill_id"),
            )
            return jsonify({"ok": result.success, **_action_result_to_dict(result)})
        except Exception as e:
            logger.error(f"[AI Browser API] navigate error: {e}")
            return jsonify({"ok": False, "error": sanitize_sensitive(str(e)[:300])}), 500

    # ──────────────────────────────────────────────────────────
    # 3. Observe（观察页面）
    # ──────────────────────────────────────────────────────────

    @bp.route("/api/browser/sessions/<session_id>/observe", methods=["POST"])
    def observe(session_id: str):
        """观察当前页面（返回脱敏后的 DOM 摘要/Accessibility Tree/screenshot）。

        Request JSON:
          - include_dom: bool (默认 False)
          - include_accessibility: bool (默认 False)
          - max_text_length: int (默认 2000)
          - screenshot: bool (是否返回 base64 截图，默认 False)
        """
        session, err = _get_session_or_404(session_id)
        if err:
            return err
        try:
            data = request.get_json(silent=True) or {}
            state = session.observe(
                include_dom=bool(data.get("include_dom", False)),
                include_accessibility=bool(data.get("include_accessibility", False)),
                max_text_length=int(data.get("max_text_length", 2000)),
            )

            response = {
                "ok": True,
                "session_id": session_id,
                "state": sanitize_dict(state.to_dict()),
                "state_hash": state.state_hash(),
                "untrusted_content": True,  # 网页内容标记为不可信
                "injection_scan": session.injection_guard.scan(
                    state.body_text, source="api_observe"
                ).to_dict() if state.body_text else None,
            }

            # 可选截图（base64，不存 Evidence）
            if data.get("screenshot", False):
                try:
                    import base64
                    screenshot_bytes = session.screenshot(full_page=False)
                    response["screenshot_base64"] = base64.b64encode(screenshot_bytes).decode("ascii")
                except Exception as e:
                    response["screenshot_error"] = sanitize_sensitive(str(e)[:200])

            return jsonify(response)
        except Exception as e:
            logger.error(f"[AI Browser API] observe error: {e}")
            return jsonify({"ok": False, "error": sanitize_sensitive(str(e)[:300])}), 500

    # ──────────────────────────────────────────────────────────
    # 4. Action（执行 Action，带 Verification 闭环）
    # ──────────────────────────────────────────────────────────

    @bp.route("/api/browser/sessions/<session_id>/action", methods=["POST"])
    def execute_action(session_id: str):
        """执行 Browser Action（核心接口，带完整 Verification 闭环）。

        Request JSON:
          - action: str (click/input/select/scroll/keyboard/wait/back/forward/reload/tab_new/...)
          - selector: str (CSS/XPath 选择器)
          - target: str (目标描述)
          - text: str (输入文本/键盘输入)
          - value: str (值/滚动距离/等待毫秒)
          - url: str (导航 URL)
          - expected: ExpectedState (期望状态，用于 Verification)
          - task_id/run_id/step_id/agent_id/skill_id: 追踪字段
          - risk_level: str (low/medium/high/critical，默认 medium)
        """
        session, err = _get_session_or_404(session_id)
        if err:
            return err
        try:
            data = request.get_json(silent=True) or {}
            action_str = (data.get("action") or "").lower().strip()
            if not action_str:
                return jsonify({"ok": False, "error": "action is required"}), 400

            # 解析 action 类型
            try:
                action_type = BrowserActionType(action_str)
            except ValueError:
                return jsonify({
                    "ok": False,
                    "error": f"Unsupported action: {action_str}. "
                             f"Supported: {[a.value for a in BrowserActionType]}",
                }), 400

            expected = _parse_expected_state(data)
            result = session.execute_action(
                action_type=action_type,
                target=data.get("target", ""),
                selector=data.get("selector", ""),
                text=data.get("text", ""),
                value=data.get("value", ""),
                url=data.get("url", ""),
                expected=expected,
                task_id=data.get("task_id"),
                run_id=data.get("run_id"),
                step_id=data.get("step_id"),
                agent_id=data.get("agent_id"),
                skill_id=data.get("skill_id"),
                risk_level=data.get("risk_level", "medium"),
            )

            response = {"ok": result.success, **_action_result_to_dict(result)}

            # 如果需要人工升级，返回 400 + escalation 信息
            if result.human_escalation_required:
                response["needs_human_approval"] = True
                response["escalation_reason"] = result.escalation_reason
                return jsonify(response), 200  # 200 但包含 escalation 标记

            return jsonify(response)
        except Exception as e:
            logger.error(f"[AI Browser API] execute_action error: {e}")
            return jsonify({"ok": False, "error": sanitize_sensitive(str(e)[:300])}), 500

    # ──────────────────────────────────────────────────────────
    # 5. Verify（独立验证接口）
    # ──────────────────────────────────────────────────────────

    @bp.route("/api/browser/sessions/<session_id>/verify", methods=["POST"])
    def verify_state(session_id: str):
        """独立验证当前页面状态是否符合期望。

        Request JSON:
          - expected: ExpectedState (必填)
        """
        session, err = _get_session_or_404(session_id)
        if err:
            return err
        try:
            data = request.get_json(silent=True) or {}
            expected = _parse_expected_state(data)
            if not expected:
                return jsonify({"ok": False, "error": "expected state is required"}), 400

            current_state = session.observe()
            verification = session.verifier.verify(expected, current_state.to_dict())

            return jsonify({
                "ok": True,
                "verification": verification.to_dict(),
                "passed": verification.passed,
                "current_state_hash": current_state.state_hash(),
            })
        except Exception as e:
            return jsonify({"ok": False, "error": sanitize_sensitive(str(e)[:300])}), 500

    # ──────────────────────────────────────────────────────────
    # 6. Evidence 查询
    # ──────────────────────────────────────────────────────────

    @bp.route("/api/browser/sessions/<session_id>/evidence", methods=["GET"])
    def get_evidence(session_id: str):
        """获取 Session 的 Evidence 列表。

        Query params:
          - result: PASS/FAIL/RETRY/HUMAN_ESCALATION (可选筛选)
          - action: action 类型 (可选筛选)
          - limit: int (默认 50，最大 200)
          - offset: int (默认 0)
        """
        try:
            store = get_evidence_store()
            result_filter = request.args.get("result", "")
            action_filter = request.args.get("action", "")
            limit = min(int(request.args.get("limit", "50")), 200)
            offset = int(request.args.get("offset", "0"))

            records = store.query(
                session_id=session_id,
                result=result_filter or None,
                action=action_filter or None,
                limit=limit,
                offset=offset,
            )
            stats = store.get_stats(session_id=session_id)

            return jsonify({
                "ok": True,
                "session_id": session_id,
                "count": len(records),
                "records": records,
                "stats": stats,
            })
        except Exception as e:
            return jsonify({"ok": False, "error": sanitize_sensitive(str(e)[:300])}), 500

    # ──────────────────────────────────────────────────────────
    # 7. 安全状态
    # ──────────────────────────────────────────────────────────

    @bp.route("/api/browser/security/status", methods=["GET"])
    def security_status():
        """获取 Browser Runtime 安全状态（Firewall/Injection/Circuit Breaker）。"""
        try:
            firewall = get_action_firewall()
            injection_guard = get_injection_guard()
            mgr = get_session_manager()

            return jsonify({
                "ok": True,
                "action_firewall": firewall.get_blocked_stats(),
                "prompt_injection_guard": injection_guard.get_detection_stats(),
                "session_manager": mgr.get_stats(),
                "security_policies": {
                    "readonly_mode": firewall.readonly_mode,
                    "credential_sanitization": True,
                    "session_isolation": True,
                    "session_idle_timeout": 600,
                    "session_max_lifetime": 3600,
                    "circuit_breaker_threshold": 5,
                    "circuit_breaker_cooldown": 30,
                    "upload_requires_l3_approval": True,
                    "xhs_official_account_readonly": True,
                },
            })
        except Exception as e:
            return jsonify({"ok": False, "error": sanitize_sensitive(str(e)[:300])}), 500

    @bp.route("/api/browser/evidence/stats", methods=["GET"])
    def evidence_stats():
        """获取全局 Evidence 统计。"""
        try:
            store = get_evidence_store()
            session_id = request.args.get("session_id", "")
            if not session_id:
                return jsonify({"ok": False, "error_code": "SESSION_ID_REQUIRED"}), 400
            session, err = _get_session_or_404(session_id)
            if err:
                return err
            stats = store.get_stats(session_id=session_id or None)
            return jsonify({"ok": True, **stats})
        except Exception as e:
            return jsonify({"ok": False, "error": sanitize_sensitive(str(e)[:300])}), 500

    # ──────────────────────────────────────────────────────────
    # 8. 人工审批确认（Human Escalation 处理）
    # ──────────────────────────────────────────────────────────

    @bp.route("/api/browser/sessions/<session_id>/human-approval", methods=["POST"])
    def human_approval(session_id: str):
        """人工审批确认接口（用于 Human Escalation 后恢复操作）。

        Request JSON:
          - approved: bool
          - action: str (要执行的 action)
          - selector/target/text/value/url: action 参数
          - reason: str (审批理由)
        """
        session, err = _get_session_or_404(session_id)
        if err:
            return err
        try:
            data = request.get_json(silent=True) or {}
            approved = bool(data.get("approved", False))

            if not approved:
                # 人工拒绝：重置 Circuit Breaker，记录拒绝
                session.recovery.circuit_breaker.reset()
                return jsonify({
                    "ok": True,
                    "approved": False,
                    "message": "Action rejected by human. Circuit breaker reset.",
                })

            # 人工批准：重置 Circuit Breaker，然后执行 action
            session.recovery.circuit_breaker.reset()

            action_str = (data.get("action") or "").lower().strip()
            if not action_str:
                return jsonify({"ok": False, "error": "action is required for approved execution"}), 400

            try:
                action_type = BrowserActionType(action_str)
            except ValueError:
                return jsonify({"ok": False, "error": f"Unsupported action: {action_str}"}), 400

            expected = _parse_expected_state(data)
            result = session.execute_action(
                action_type=action_type,
                target=data.get("target", ""),
                selector=data.get("selector", ""),
                text=data.get("text", ""),
                value=data.get("value", ""),
                url=data.get("url", ""),
                expected=expected,
                task_id=data.get("task_id"),
                run_id=data.get("run_id"),
                agent_id="human_approved",
                risk_level="high",
            )

            return jsonify({
                "ok": result.success,
                "human_approved": True,
                **_action_result_to_dict(result),
            })
        except Exception as e:
            return jsonify({"ok": False, "error": sanitize_sensitive(str(e)[:300])}), 500

    # 注册蓝图
    app.register_blueprint(bp)
    logger.info("[AI Browser API] Blueprint registered: /api/browser/*")
    return bp
