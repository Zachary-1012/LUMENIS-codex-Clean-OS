# -*- coding: utf-8 -*-
"""LUMENIS Global Design System 验证：新设计系统CSS + 双域模板 + 动效引擎 + 路由。
不启动完整 Flask、不触达数据库/采集/业务逻辑。
UI清理后重写：旧lumenis-*.css和旧模板已删除，替换为lumenis-global-design.css + 双域模板。
"""
import os
import re
import sys

ZBC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ZBC)

from jinja2 import Environment, FileSystemLoader, select_autoescape


def run_foundation_checks():
    results = []

    def check(name, ok, detail=""):
        results.append((name, bool(ok), detail))

    css_dir = os.path.join(ZBC, "static", "css")
    js_dir = os.path.join(ZBC, "static", "js")

    # 1. 新设计系统 CSS 文件齐全
    for f in ["lumenis-global-design.css", "zbc-design-v1.1.css",
              "zbc-layout-v1.1.css", "xujing-core.css"]:
        check("CSS exists: " + f, os.path.isfile(os.path.join(css_dir, f)))

    # 2. 旧 lumenis CSS 已删除（确认清理完成）
    for f in ["lumenis.css", "lumenis-tokens.css", "lumenis-tokens-v2.css",
              "lumenis-reset.css", "lumenis-layout.css", "lumenis-components.css",
              "lumenis-core-components.css", "lumenis-motion.css",
              "lumenis-responsive.css", "xujing-dual-domain.css"]:
        check("Old CSS removed: " + f, not os.path.isfile(os.path.join(css_dir, f)))

    # 3. JS 文件齐全（新动效引擎 + 核心）
    for f in ["lumenis-motion-engine.js", "lumenis-core.js", "lumenis-icons.js",
              "i18n.js", "domain-context.js", "xujing-viz.js"]:
        check("JS exists: " + f, os.path.isfile(os.path.join(js_dir, f)))

    # 4. 新设计系统包含核心设计令牌
    ds = open(os.path.join(css_dir, "lumenis-global-design.css"), encoding="utf-8").read()
    check("Design: mint green primary", "--ld-mint" in ds and "#00D4AA" in ds)
    check("Design: purple-blue gradient", "--ld-gradient-purple-blue" in ds)
    check("Design: pink-purple-blue chart gradient", "--ld-gradient-pink-purple-blue" in ds)
    check("Design: large card radius", "--ld-radius-card" in ds and "20px" in ds)
    check("Design: glass blur", "--ld-glass-blur" in ds and "blur(20px)" in ds)
    check("Design: KPI large font", "--ld-text-kpi" in ds and "36px" in ds)
    check("Design: platform brand colors", all(x in ds for x in ["--ld-platform-xhs", "--ld-platform-douyin", "--ld-platform-bilibili", "--ld-platform-weibo"]))
    check("Design: dark card variant", "--ld-dark-bg" in ds and "#0F172A" in ds)
    check("Design: motion tokens", "--ld-motion-normal" in ds and "--ld-ease-out" in ds)
    check("Design: reduced-motion support", "prefers-reduced-motion" in ds)

    # 5. 动效引擎包含核心能力
    me = open(os.path.join(js_dir, "lumenis-motion-engine.js"), encoding="utf-8").read()
    check("Motion: countUp", "countUp" in me)
    check("Motion: drawAreaChart", "drawAreaChart" in me)
    check("Motion: fillProgress", "fillProgress" in me)
    check("Motion: staggerChildren", "staggerChildren" in me)
    check("Motion: pulse", "pulse" in me)
    check("Motion: reduced-motion check", "_reduced" in me and "prefers-reduced-motion" in me)
    check("Motion: LDMotion global", "window.LDMotion" in me)

    # 6. 双域模板存在且可渲染
    env = Environment(loader=FileSystemLoader(os.path.join(ZBC, "templates")),
                      autoescape=select_autoescape(["html"]))
    env.globals["url_for"] = lambda endpoint, **kw: (
        "/static/" + kw.get("filename", "") if endpoint == "static" else "#")
    env.globals["active_domain"] = "cth"
    env.globals["active_nav"] = "cth_overview"

    for tpl in ["base.html", "zbmp/overview.html", "cth/overview.html",
                "cth/xiaohongshu.html", "zbmp/content.html", "system/ai.html",
                "system/browser.html"]:
        try:
            html = env.get_template(tpl).render(active_domain="cth", active_nav="cth_overview")
            check("Template renders: " + tpl, len(html) > 100, "%d chars" % len(html))
        except Exception as e:
            check("Template renders: " + tpl, False, repr(e))

    # 7. base.html 引用新设计系统
    base_html = env.get_template("base.html").render(active_domain="cth", active_nav="cth_overview")
    check("base.html links global design CSS", "lumenis-global-design.css" in base_html)
    check("base.html links motion engine JS", "lumenis-motion-engine.js" in base_html)
    check("base.html does NOT link old lumenis.css", "lumenis.css" not in base_html)

    # 8. 小红书页面包含新设计元素
    xhs_html = env.get_template("cth/xiaohongshu.html").render(active_domain="cth", active_nav="cth_xhs")
    check("XHS: platform header", "ld-platform-header--xhs" in xhs_html)
    check("XHS: KPI cards", "ld-kpi-card" in xhs_html)
    check("XHS: card view grid", "ld-content-grid" in xhs_html)
    check("XHS: count-up attributes", "ld-count-up" in xhs_html)
    check("XHS: pill tabs", "ld-tabs" in xhs_html or "ld-tab" in xhs_html)

    # 9. 旧模板目录已删除
    for d in ["home", "intelligence", "production", "operations", "research", "_preview"]:
        check("Old template dir removed: " + d,
              not os.path.isdir(os.path.join(ZBC, "templates", d)))

    # 10. Blueprint 路由（新双域 + API + healthz，旧遗留路由已移除）
    try:
        import flask
        import lumenis_frontend
        check("blueprint import", isinstance(lumenis_frontend.lumenis_bp, flask.Blueprint))
        app = flask.Flask(__name__, template_folder=os.path.join(ZBC, "templates"),
                          static_folder=os.path.join(ZBC, "static"))
        app.register_blueprint(lumenis_frontend.lumenis_bp)
        rules = [r.rule for r in app.url_map.iter_rules()]

        # 核心路由保留
        check("route: /lumenis/ (root)", "/lumenis/" in rules)
        check("route: /lumenis/healthz", "/lumenis/healthz" in rules)

        # 双域路由保留
        for route in ["/lumenis/zbmp/overview", "/lumenis/cth/overview",
                      "/lumenis/cth/xiaohongshu", "/lumenis/system/runtime",
                      "/lumenis/system/ai", "/lumenis/system/browser"]:
            check("dual-domain route: " + route, route in rules)

        # API 路由保留
        for route in ["/lumenis/api/skills/status", "/lumenis/api/skills/invoke",
                      "/lumenis/api/intelligence/evidence"]:
            check("API route: " + route, route in rules)

        # 旧遗留路由已移除
        for route in ["/lumenis/intelligence", "/lumenis/production",
                      "/lumenis/operations", "/lumenis/research",
                      "/lumenis/production/risk", "/lumenis/intelligence/skills"]:
            check("old route removed: " + route, route not in rules)

        # healthz 正常
        with app.test_client() as c:
            hz = c.get("/lumenis/healthz")
            check("healthz ok", hz.status_code == 200 and hz.get_json()["status"] == "ok")

            # root 重定向到 cth/overview
            root = c.get("/lumenis/", follow_redirects=False)
            check("root redirects", root.status_code in (301, 302),
                  "status=%d location=%s" % (root.status_code, root.headers.get("Location", "")))

    except Exception as e:
        check("blueprint route", False, repr(e))

    return results


def test_frontend_foundation():
    results = run_foundation_checks()
    failed = [(n, d) for n, ok, d in results if not ok]
    assert not failed, "Frontend Foundation 失败项: %s" % failed


if __name__ == "__main__":
    res = run_foundation_checks()
    for name, ok, detail in res:
        print(("[PASS] " if ok else "[FAIL] ") + name + ((" — " + detail) if detail else ""))
    p = sum(1 for _, ok, _ in res if ok)
    print("\n===== %d/%d passed =====" % (p, len(res)))
    sys.exit(0 if p == len(res) else 1)
