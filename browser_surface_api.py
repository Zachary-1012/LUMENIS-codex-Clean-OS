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

    def _acct():
        """账号/profile（双账号 9222/9223）；显式 port 优先于 account。"""
        return (request.args.get("account") or
                (request.get_json(silent=True) or {}).get("account") or "")

    def _port():
        data = request.get_json(silent=True) or {}
        raw = request.args.get("port") or data.get("port")
        try:
            return int(raw) if raw else None
        except (TypeError, ValueError):
            return None

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
                                       wait_ms=wait_ms))

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

    app.register_blueprint(bp)
    return bp
