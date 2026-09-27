# -*- coding: utf-8 -*-
"""序境 Xujing · 平台内置浏览器统一 API（Browser Surface API）

对标 Safari/Chrome 原生浏览能力，全部在平台内完成、不跳系统外部浏览器。
能力层见 browser_surface.py；本文件只做 HTTP 入参校验与响应封装，不含业务算法。

路由前缀：/api/browser-surface/*
"""
from __future__ import annotations


def register_browser_surface_api(app):
    from flask import Blueprint, jsonify, request
    import browser_surface as bs
    import browser_discovery as bd

    bp = Blueprint("browser_surface", __name__)

    @bp.before_request
    def _require_product_browser_actor():
        """Keep the legacy surface on the same account/Permission boundary."""
        try:
            from account.service import get_current_user
            from account.authorization import check_dual_domain_permission

            actor = get_current_user()
            if not actor or type(actor.get("id")) is not int or type(actor.get("session_id")) is not int:
                return jsonify({"ok": False, "code": "BROWSER_ACTOR_REQUIRED"}), 401
            action = "read" if request.method == "GET" else "write"
            if not check_dual_domain_permission(actor["id"], "SYSTEM", module="browser", action=action):
                return jsonify({"ok": False, "code": "BROWSER_PERMISSION_DENIED"}), 403
        except Exception:
            return jsonify({"ok": False, "code": "BROWSER_PERMISSION_UNAVAILABLE"}), 503

        data = request.get_json(silent=True) or {}
        if ("account" in request.args or "port" in request.args or
                (isinstance(data, dict) and ("account" in data or "port" in data))):
            return jsonify({"ok": False, "code": "CLIENT_BROWSER_SELECTOR_FORBIDDEN"}), 400

    @bp.after_request
    def _hide_browser_transport(response):
        """Never return CDP transport/profile fields to the product client."""
        private_keys = {"cdp_port", "port", "profile", "ws_url", "websocketdebuggerurl", "account"}

        def public(value):
            if isinstance(value, dict):
                return {key: public(item) for key, item in value.items()
                        if str(key).casefold() not in private_keys}
            if isinstance(value, list):
                return [public(item) for item in value]
            return value

        payload = response.get_json(silent=True)
        if payload is not None:
            response.set_data(app.json.dumps(public(payload)))
        return response

    @bp.errorhandler(PermissionError)
    def _blocked_browser_session(_error):
        return jsonify({"ok": False, "code": "BROWSER_SESSION_BLOCKED",
                        "error": "当前浏览器会话未经序境验证"}), 403

    def _acct():
        """Product requests never select an acquisition identity."""
        return ""

    def _port():
        return bs.GENERAL_CDP_PORT

    def _target_id():
        data = request.get_json(silent=True) or {}
        return request.args.get("target_id") or data.get("target_id") or None

    # ── 能力与策略 ─────────────────────────────────────────────
    @bp.route("/api/browser-surface/capabilities", methods=["GET"])
    def api_capabilities():
        return jsonify(bs.capability_report())

    @bp.route("/api/browser-surface/policy", methods=["GET"])
    def api_policy():
        url = request.args.get("url", "")
        payload = {
            "ok": True,
            "nav_mode": bs.current_nav_mode(),
            "nav_modes": bs.NAV_MODES,
            "extra_domains": bs._extra_domains(),
            "blocked_schemes": list(bs._BLOCKED_SCHEMES),
        }
        if url:
            payload["evaluation"] = bs.evaluate_navigation(url)
        return jsonify(payload)

    # ── 标签页管理（对标 Chrome/Safari Tabs）────────────────────
    @bp.route("/api/browser-surface/tabs", methods=["GET"])
    def api_tabs():
        return jsonify(bs.list_tabs(account=_acct(), port=_port()))

    @bp.route("/api/browser-surface/tab/new", methods=["POST"])
    def api_tab_new():
        data = request.get_json(silent=True) or {}
        url = (data.get("url") or "").strip()
        if not url:
            return jsonify({"ok": False, "error": "url 不能为空"}), 400
        return jsonify(bs.new_tab(url, account=_acct(), port=_port(),
                                  mode=data.get("mode"),
                                  background=bool(data.get("background"))))

    @bp.route("/api/browser-surface/tab/close", methods=["POST"])
    def api_tab_close():
        return jsonify(bs.close_tab(_target_id() or "", account=_acct(), port=_port()))

    @bp.route("/api/browser-surface/tab/activate", methods=["POST"])
    def api_tab_activate():
        return jsonify(bs.activate_tab(_target_id() or "", account=_acct(), port=_port()))

    @bp.route("/api/browser-surface/tab/navigate", methods=["POST"])
    def api_tab_navigate():
        data = request.get_json(silent=True) or {}
        url = (data.get("url") or "").strip()
        if not url:
            return jsonify({"ok": False, "error": "url 不能为空"}), 400
        try:
            wait_ms = int(data.get("wait_ms", 600))
        except (TypeError, ValueError):
            wait_ms = 600
        return jsonify(bs.navigate_tab(url, target_id=_target_id(), account=_acct(),
                                       port=_port(), mode=data.get("mode"),
                                       wait_ms=wait_ms,
                                       confirmed=bool(data.get("confirmed", False))))

    @bp.route("/api/browser-surface/tab/history", methods=["POST"])
    def api_tab_history():
        """内置浏览器页内历史：back/forward/reload，保持端口与标签页一致。"""
        data = request.get_json(silent=True) or {}
        action = (data.get("action") or "reload").strip().lower()
        if action not in ("back", "forward", "reload"):
            return jsonify({"ok": False, "error": "action 必须是 back/forward/reload"}), 400
        return jsonify(bs.history_tab(action=action, target_id=_target_id(),
                                      account=_acct(), port=_port()))

    # ── 页面截图（对标浏览器截图，支持指定 port/target_id）──────────
    @bp.route("/api/browser-surface/screenshot", methods=["GET"])
    def api_screenshot():
        try:
            quality = int(request.args.get("quality", "60"))
        except (TypeError, ValueError):
            quality = 60
        return jsonify(bs._hybrid_screenshot(target_id=_target_id(), account=_acct(),
                                              port=_port(), quality=quality))

    # ── 页面内容提取（对标 Safari Reader / 结构化 DOM）──────────
    @bp.route("/api/browser-surface/extract", methods=["POST", "GET"])
    def api_extract():
        data = request.get_json(silent=True) or {}
        kind = request.args.get("kind") or data.get("kind") or "meta"
        try:
            max_chars = int(request.args.get("max_chars") or data.get("max_chars")
                            or bs.MAX_TEXT_CHARS)
        except (TypeError, ValueError):
            max_chars = bs.MAX_TEXT_CHARS
        return jsonify(bs.extract(kind, target_id=_target_id(), account=_acct(),
                                  port=_port(), max_chars=max_chars))

    # ── 多源搜索（平台内，不跳站外）────────────────────────────
    @bp.route("/api/browser-surface/search", methods=["GET", "POST"])
    def api_search():
        data = request.get_json(silent=True) or {}
        query = (request.args.get("q") or data.get("q") or "").strip()
        if not query:
            return jsonify({"ok": False, "error": "q 不能为空"}), 400
        engines = request.args.get("engines") or data.get("engines")
        if isinstance(engines, str) and engines.strip():
            engines = [e.strip() for e in engines.split(",") if e.strip()]
        try:
            limit = int(request.args.get("limit") or data.get("limit") or 30)
        except (TypeError, ValueError):
            limit = 30
        limit = max(1, min(limit, 100))
        try:
            items = bd.search(query, limit=limit, engines=engines)
            return jsonify({"ok": True, "query": query, "count": len(items),
                            "engines": engines or list(bd.DEFAULT_ENGINES), "items": items})
        except Exception as e:
            return jsonify({"ok": False, "query": query, "error": str(e)}), 502

    # ── 书签（对标浏览器 Bookmarks）────────────────────────────
    @bp.route("/api/browser-surface/bookmarks", methods=["GET", "POST"])
    def api_bookmarks():
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            return jsonify(bs.add_bookmark(data.get("title", ""), data.get("url", "")))
        return jsonify(bs.list_bookmarks())

    @bp.route("/api/browser-surface/bookmark/remove", methods=["POST"])
    def api_bookmark_remove():
        data = request.get_json(silent=True) or {}
        return jsonify(bs.remove_bookmark(data.get("url", "")))

    # ── 历史（对标浏览器 History）──────────────────────────────
    @bp.route("/api/browser-surface/history", methods=["GET", "POST"])
    def api_history():
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            return jsonify(bs.record_history(data.get("title", ""), data.get("url", "")))
        try:
            limit = int(request.args.get("limit", 100))
        except (TypeError, ValueError):
            limit = 100
        return jsonify(bs.list_history(limit))

    @bp.route("/api/browser-surface/history/clear", methods=["POST"])
    def api_history_clear():
        return jsonify(bs.clear_history())

    # ── 导航配置（open 开关后台通道，对标浏览器站点设置）──────────
    @bp.route("/api/browser-surface/nav-config", methods=["GET", "POST"])
    def api_nav_config():
        if request.method == "GET":
            return jsonify(bs.get_nav_config())
        data = request.get_json(silent=True) or {}
        mode = data.get("mode")
        extra = data.get("extra_domains")
        append = data.get("append", True)
        if mode is None and extra is None:
            return jsonify({"ok": False, "error": "需提供 mode 或 extra_domains"}), 400
        return jsonify(bs.set_nav_config(mode=mode, extra_domains=extra, append=bool(append)))

    # ── 通用浏览实例（9224，按需，与获批采集端口物理隔离）─────
    @bp.route("/api/browser-surface/general-browser/status", methods=["GET"])
    def api_general_status():
        return jsonify({"ok": True, "port": bs.GENERAL_CDP_PORT,
                        "online": bs.general_browser_online()})

    @bp.route("/api/browser-surface/general-browser/ensure", methods=["POST"])
    def api_general_ensure():
        data = request.get_json(silent=True) or {}
        return jsonify(bs.ensure_general_browser(force=bool(data.get("force"))))

    @bp.route("/api/browser-surface/general-browser/stop", methods=["POST"])
    def api_general_stop():
        return jsonify(bs.stop_general_browser())

    # ── 页内查找（对标 Safari/Chrome find-in-page）──────────────
    @bp.route("/api/browser-surface/find", methods=["POST"])
    def api_find():
        data = request.get_json(silent=True) or {}
        query = (data.get("query") or "").strip()
        if not query:
            return jsonify({"ok": False, "error": "query 不能为空"}), 400
        return jsonify(bs.find_in_page(query, target_id=_target_id(), account=_acct(),
                                       port=_port(),
                                       case_sensitive=bool(data.get("case_sensitive"))))

    @bp.route("/api/browser-surface/find/stop", methods=["POST"])
    def api_find_stop():
        return jsonify(bs.stop_find_in_page(target_id=_target_id(), account=_acct(), port=_port()))

    # ── 下载管理（对标 Chrome 下载，平台内目录）─────────────────
    @bp.route("/api/browser-surface/downloads/config", methods=["POST"])
    def api_downloads_config():
        data = request.get_json(silent=True) or {}
        enabled = data.get("enabled", True)
        return jsonify(bs.set_download_behavior(enabled=bool(enabled),
                                                download_path=data.get("download_path"),
                                                account=_acct(), port=_port()))

    @bp.route("/api/browser-surface/downloads", methods=["GET"])
    def api_downloads_list():
        return jsonify(bs.list_downloads())

    # ── Vision+DOM Hybrid 分析（IC-053，受 AI Gate 治理）──────────────
    @bp.route("/api/browser-surface/hybrid/analyze", methods=["POST"])
    def api_hybrid_analyze():
        data = request.get_json(silent=True) or {}
        query = (data.get("query") or "").strip()
        prefer = (data.get("prefer") or "auto").lower()
        if prefer not in ("auto", "dom", "vision"):
            return jsonify({"ok": False, "error": "prefer 必须是 auto/dom/vision"}), 400
        try:
            max_dom = int(data.get("max_dom_nodes") or bs.MAX_DOM_NODES)
        except (TypeError, ValueError):
            max_dom = bs.MAX_DOM_NODES
        try:
            quality = int(data.get("screenshot_quality") or 60)
        except (TypeError, ValueError):
            quality = 60
        return jsonify(bs.hybrid_analyze(
            query=query, target_id=_target_id(), account=_acct(), port=_port(),
            prefer=prefer, max_dom_nodes=max_dom, screenshot_quality=quality))

    # ── 下载实时进度监听（持久 WS + Browser.downloadProgress 事件）──────────
    @bp.route("/api/browser-surface/downloads/monitor/start", methods=["POST"])
    def api_download_monitor_start():
        return jsonify(bs.download_monitor_start(account=_acct(), port=_port()))

    @bp.route("/api/browser-surface/downloads/monitor/stop", methods=["POST"])
    def api_download_monitor_stop():
        return jsonify(bs.download_monitor_stop(account=_acct(), port=_port()))

    @bp.route("/api/browser-surface/downloads/monitor/status", methods=["GET"])
    def api_download_monitor_status():
        return jsonify(bs.download_monitor_status(account=_acct(), port=_port()))

    @bp.route("/api/browser-surface/downloads/active", methods=["GET"])
    def api_download_active():
        return jsonify(bs.download_active(account=_acct(), port=_port()))

    @bp.route("/api/browser-surface/downloads/cancel", methods=["POST"])
    def api_download_cancel():
        data = request.get_json(silent=True) or {}
        guid = (data.get("guid") or "").strip()
        if not guid:
            return jsonify({"ok": False, "error": "guid 不能为空"}), 400
        return jsonify(bs.download_cancel(guid, account=_acct(), port=_port()))

    app.register_blueprint(bp)
    return bp
