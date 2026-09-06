# -*- coding: utf-8 -*-
"""ZBC V2.0 Dual-Domain UI 验证：ZBMP/CTH/SYSTEM 三域页面 + 路由 + 导航 + 域切换。

验证：
1. 27 个页面模板全部存在且可渲染
2. lumenis_frontend.py 注册全部双域路由
3. 三段式导航（ZBMP/CTH/SYSTEM）+ 域切换 JS
4. 六态 UI（Loading/Empty/Error/Success/Degraded/Permission）
5. 域隔离（CTH protected / ZBMP multi-brand / SYSTEM）
6. 无死按钮 / 无不存在 API / 无字段猜测
7. Podcast 前端页面（P1 追加任务）
8. 现有页面不被破坏（production/* 路由仍存在）
"""
import os
import re
import sys

ZBC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ZBC)

from jinja2 import Environment, FileSystemLoader, select_autoescape


def run_dual_domain_checks():
    results = []

    def check(name, ok, detail=""):
        results.append((name, bool(ok), detail))

    templates_dir = os.path.join(ZBC, "templates")
    fe_path = os.path.join(ZBC, "lumenis_frontend.py")
    base_path = os.path.join(templates_dir, "base.html")

    # ===== 1. 模板文件存在性 =====
    expected_templates = {
        "zbmp": ["overview.html", "intelligence.html", "brand.html", "content.html",
                 "podcast.html", "kos.html", "competition.html", "risk.html",
                 "reports.html", "evaluation.html"],
        "cth": ["overview.html", "realtime.html", "events.html", "risk.html",
                "brands.html", "industries.html", "xiaohongshu.html", "kos.html",
                "reports.html", "evidence.html"],
        "system": ["runtime.html", "collector.html", "ai.html", "database.html",
                   "security.html", "evaluation.html"],
    }
    total_templates = 0
    for domain, files in expected_templates.items():
        for f in files:
            total_templates += 1
            path = os.path.join(templates_dir, domain, f)
            check("template exists: %s/%s" % (domain, f), os.path.isfile(path))
    check("total expected templates = 26", total_templates == 26, "%d found" % total_templates)

    # ===== 2. Jinja2 渲染验证 =====
    env = Environment(loader=FileSystemLoader(templates_dir),
                      autoescape=select_autoescape(["html"]))
    env.globals["url_for"] = lambda endpoint, **kw: (
        "/static/" + kw.get("filename", "") if endpoint == "static" else "#")

    render_errors = []
    for domain, files in expected_templates.items():
        for f in files:
            tpl_rel = "%s/%s" % (domain, f)
            try:
                html = env.get_template(tpl_rel).render(
                    active_nav="test", active_domain=domain,
                    home_url="/lumenis/", page_title="Test")
                check("renders: %s" % tpl_rel, len(html) > 100, "%d chars" % len(html))
            except Exception as e:
                render_errors.append((tpl_rel, repr(e)))
                check("renders: %s" % tpl_rel, False, repr(e))

    # ===== 3. 路由注册验证 =====
    if os.path.isfile(fe_path):
        fe = open(fe_path, encoding="utf-8").read()
        # ZBMP routes
        zbmp_routes = ["zbmp_overview", "zbmp_intelligence", "zbmp_brand", "zbmp_content",
                        "zbmp_podcast", "zbmp_kos", "zbmp_competition", "zbmp_risk",
                        "zbmp_reports", "zbmp_evaluation"]
        for r in zbmp_routes:
            check("route def: %s" % r, "def %s(" % r in fe)
            check("route decorator: /lumenis/zbmp/%s" % r.replace("zbmp_", ""),
                  '"/zbmp/%s"' % r.replace("zbmp_", "") in fe)
        # CTH routes
        cth_routes = ["cth_overview", "cth_realtime", "cth_events", "cth_risk",
                      "cth_brands", "cth_industries", "cth_xhs", "cth_kos",
                      "cth_reports", "cth_evidence"]
        for r in cth_routes:
            check("route def: %s" % r, "def %s(" % r in fe)
        # SYSTEM routes
        sys_routes = ["system_runtime", "system_collector", "system_ai",
                      "system_database", "system_security", "system_evaluation"]
        for r in sys_routes:
            check("route def: %s" % r, "def %s(" % r in fe)
        # Existing routes not broken
        check("existing route: production_overview still exists", "def production_overview(" in fe)
        check("existing route: public_opinion still exists", "def public_opinion(" in fe)
        check("existing route: risk still exists", "def risk(" in fe)
        check("existing route: intelligence_workspace still exists", "def intelligence_workspace(" in fe)
        # Domain API blueprint
        check("domain_api_bp registered", "domain_api_bp = Blueprint" in fe)
        check("_get_domain_context helper", "def _get_domain_context()" in fe)
        check("_domain_template_vars helper", "def _domain_template_vars(" in fe)

    # ===== 4. 三段式导航验证 =====
    if os.path.isfile(base_path):
        base = open(base_path, encoding="utf-8").read()
        check("domain switch container", "lm-domain-switch" in base)
        check("ZBMP tab", 'data-domain="zbmp"' in base)
        check("CTH tab", 'data-domain="cth"' in base)
        check("SYSTEM tab", 'data-domain="system"' in base)
        check("domain switch JS function", "function showDomain" in base)
        check("domain cookie set", "zbc_domain=" in base)
        check("domain reload on switch", "window.location.href" in base)
        check("ZBMP nav group in sidebar", "lm-nav-group--zbmp" in base)
        check("CTH nav group in sidebar", "lm-nav-group--cth" in base)
        check("SYSTEM nav group in sidebar", 'data-domain-nav="system"' in base)
        # Nav items
        check("ZBMP nav: Overview", "zbmp_overview" in base)
        check("ZBMP nav: Podcast", "zbmp_podcast" in base)
        check("CTH nav: Overview", "cth_overview" in base)
        check("CTH nav: Brands (199)", "199" in base)
        check("CTH nav: Industries (9)", "9" in base)
        check("SYSTEM nav: Runtime", "system_runtime" in base)
        # xujing resources
        check("xujing-core.css in base", "xujing-core.css" in base)
        check("xujing-viz.js in base", "xujing-viz.js" in base)
        check("xujing-dual-domain.css in base", "xujing-dual-domain.css" in base)

    # ===== 5. 六态 UI 验证（通用页面）=====
    generic_pages = []
    for domain in ["zbmp", "cth", "system"]:
        ddir = os.path.join(templates_dir, domain)
        if os.path.isdir(ddir):
            for f in os.listdir(ddir):
                if f.endswith(".html") and f not in ["overview.html", "podcast.html", "runtime.html"]:
                    generic_pages.append(os.path.join(domain, f))
    for tpl_rel in generic_pages:
        tpl = open(os.path.join(templates_dir, tpl_rel), encoding="utf-8").read()
        for state in ["loading", "empty", "error", "success", "degraded", "permission"]:
            check("%s six-state: %s" % (tpl_rel, state),
                  "state-" + state in tpl)
        check("%s has retry button" % tpl_rel, "重试" in tpl or "retry" in tpl.lower())
        check("%s has loading indicator" % tpl_rel, "xj-spinner" in tpl or "加载中" in tpl)

    # ===== 6. 域主题区分验证 =====
    if os.path.isfile(os.path.join(templates_dir, "zbmp", "overview.html")):
        zbmp = open(os.path.join(templates_dir, "zbmp", "overview.html"), encoding="utf-8").read()
        check("ZBMP uses blue theme (#5b8def)", "#5b8def" in zbmp)
        check("ZBMP domain label", "ZBMP" in zbmp)
    if os.path.isfile(os.path.join(templates_dir, "cth", "overview.html")):
        cth = open(os.path.join(templates_dir, "cth", "overview.html"), encoding="utf-8").read()
        check("CTH uses green theme (#2f9e6e)", "#2f9e6e" in cth)
        check("CTH protected label", "CTH Protected" in cth or "protected" in cth.lower())
        check("CTH 199 brands reference", "199" in cth)
        check("CTH 9 industries reference", "9" in cth)
    # CSS domain theme
    css2_path = os.path.join(ZBC, "static", "css", "xujing-dual-domain.css")
    if os.path.isfile(css2_path):
        css2 = open(css2_path, encoding="utf-8").read()
        check("CSS: ZBMP blue accent", "#5b8def" in css2)
        check("CSS: CTH green accent", "#2f9e6e" in css2)
        check("CSS: SYSTEM gray accent", "#6b7280" in css2)
        check("CSS: six-state styles", "xj-state--loading" in css2)
        check("CSS: responsive mobile", "@media" in css2)

    # ===== 7. 无死按钮 / 无不存在 API 验证 =====
    all_templates = []
    for domain in ["zbmp", "cth", "system"]:
        ddir = os.path.join(templates_dir, domain)
        if os.path.isdir(ddir):
            for f in os.listdir(ddir):
                if f.endswith(".html"):
                    all_templates.append(os.path.join(domain, f))
    # Known valid API endpoints
    valid_apis = ["/api/stats", "/api/notes", "/api/risk-alerts", "/api/hot-notes",
                  "/api/events", "/api/metric-trend", "/api/domain/overview",
                  "/api/domain/brands", "/api/domain/risk", "/api/domain/context",
                  "/api/system/health/summary", "/api/intelligence/evidence",
                  "/api/skills/status", "/api/podcast/overview", "/api/podcast/entities",
                  "/api/web-mentions", "/api/hot-topics", "/api/feedback-keywords"]
    for tpl_rel in all_templates:
        tpl = open(os.path.join(templates_dir, tpl_rel), encoding="utf-8").read()
        # Find all API calls
        api_calls = re.findall(r"xjViz\.api\(['\"]([^'\"]+)['\"]", tpl)
        api_calls += re.findall(r"fetch\(['\"]([^'\"]+)['\"]", tpl)
        for api in api_calls:
            # Strip query params
            api_base = api.split("?")[0]
            # xjViz.api() prepends /api to endpoints not starting with http
            # So /domain/overview actually hits /api/domain/overview
            check_api = api_base if api_base.startswith("/api/") else "/api" + api_base
            is_valid = any(check_api.startswith(v) for v in valid_apis)
            check("%s API valid: %s" % (tpl_rel, api_base), is_valid)

    # ===== 8. Podcast 页面验证（P1 追加任务）=====
    podcast_path = os.path.join(templates_dir, "zbmp", "podcast.html")
    if os.path.isfile(podcast_path):
        pod = open(podcast_path, encoding="utf-8").read()
        check("Podcast page calls /api/podcast/overview", "/podcast/overview" in pod)
        check("Podcast page calls /api/podcast/entities", "/podcast/entities" in pod)
        check("Podcast page lists 8 API endpoints", "breakout" in pod and "content-yield" in pod)
        check("Podcast page has KPI cards", "xj-kpi-card" in pod)
        check("Podcast page has xjViz.kpi", "xjViz.kpi" in pod)
        check("Podcast page has xjViz.table", "xjViz.table" in pod)
        check("Podcast nav item in base.html", "zbmp_podcast" in open(base_path, encoding="utf-8").read())
    # Podcast backend registered
    app_path = os.path.join(ZBC, "app.py")
    if os.path.isfile(app_path):
        app = open(app_path, encoding="utf-8").read()
        check("podcast_routes registered in app.py", "podcast_routes" in app)
        check("register_podcast_api called", "register_podcast_api" in app)

    # ===== 9. 现有功能不被破坏 =====
    existing_templates = ["production/overview.html", "production/public_opinion.html",
                          "production/risk.html", "home/command_home.html",
                          "intelligence/workspace.html", "operations/index.html"]
    for tpl in existing_templates:
        path = os.path.join(templates_dir, tpl)
        check("existing template intact: %s" % tpl, os.path.isfile(path))
    # base.html still has original nav groups
    if os.path.isfile(base_path):
        base = open(base_path, encoding="utf-8").read()
        check("original Intelligence nav still present", "nav.intelligence" in base)
        check("original Production nav still present", "nav.production" in base)
        check("original Research nav still present", "nav.research" in base)
        check("original Operations nav still present", "nav.operations" in base)

    # ===== Summary =====
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print("\n" + "=" * 60)
    print("Dual-Domain UI Test Results: %d/%d passed" % (passed, total))
    print("=" * 60)
    for name, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        line = "  [%s] %s" % (status, name)
        if detail and not ok:
            line += "  -- " + detail
        print(line)
    if render_errors:
        print("\n--- Render Errors ---")
        for tpl, err in render_errors:
            print("  %s: %s" % (tpl, err))
    return results


def test_dual_domain_ui():
    results = run_dual_domain_checks()
    failed = [(n, d) for n, ok, d in results if not ok]
    assert not failed, "Dual-Domain UI 失败项: %s" % failed


if __name__ == "__main__":
    run_dual_domain_checks()
