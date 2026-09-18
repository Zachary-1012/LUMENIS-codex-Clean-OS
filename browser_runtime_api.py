# -*- coding: utf-8 -*-
"""Zachary OS AI · Browser Runtime API（浏览器运行时只读接口）
对齐 CTR-BROWSER-RUNTIME-P0-01：对外暴露 Browser Runtime 统一能力（只读）。
端点：
  GET  /api/browser-runtime/status      → Provider 注册表 + 默认 Provider + 状态机序列
  POST /api/browser-runtime/probe       → Policy Gate + Router 探测指定 Provider（导航/健康）
设计原则：
  - 只读/探测，不改动现有 internal-browser API（保持向后兼容）
  - 不返回任何 Cookie/Token/密钥
  - 失败返回分类（transient/session/...），不无限重试
"""
from __future__ import annotations


def register_browser_runtime_api(app):
    """在 Flask app 上注册 Browser Runtime 只读 API。"""
    from flask import Blueprint, jsonify, request
    from lumenis.system.browser.runtime import browser_router, BrowserContract, BrowserState, FailureClass

    bp = Blueprint("browser_runtime_api", __name__)

    @bp.route("/api/browser-runtime/status", methods=["GET"])
    def browser_runtime_status():
        """Provider 注册表 + 默认 Provider + 状态机（只读）。"""
        try:
            return jsonify({
                "ok": True,
                "providers": browser_router.providers(),
                "default_provider": browser_router.default_provider(),
                "state_sequence": BrowserContract.state_sequence(),
                "failure_classes": [fc.value for fc in FailureClass],
            })
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)[:300]}), 500

    @bp.route("/api/browser-runtime/probe", methods=["POST"])
    def browser_runtime_probe():
        """探测指定 Provider：先过 Policy Gate，再执行导航/健康检查。"""
        try:
            data = request.get_json(silent=True) or {}
            provider = data.get("provider") or "cdp"
            url = data.get("url")  # 可选，仅 navigate 类需要
            action = data.get("action", "health")  # health | navigate

            # 1. Policy Gate（导航前必须检查）
            if action == "navigate":
                if not url:
                    return jsonify({"ok": False, "error": "navigate 需要 url"}), 400
                browser_router.policy_gate("navigate", url=url)

            # 2. 获取 Provider 实例
            adapter = browser_router.get(provider)

            # 3. 执行动作
            if action == "navigate":
                result = adapter.navigate(url)
            else:
                result = adapter.health()

            return jsonify({"ok": True, "provider": provider, "action": action, "result": result})
        except Exception as e:
            # 失败分类（供调用方决策）
            cls = BrowserContract.classify_failure(str(e)).value
            return jsonify({"ok": False, "error": str(e)[:300], "failure_class": cls}), 400

    app.register_blueprint(bp)
    return bp