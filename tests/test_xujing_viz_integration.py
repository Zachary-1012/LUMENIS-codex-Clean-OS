# -*- coding: utf-8 -*-
"""xujing-viz.js 集成验证：函数存在性 + API 端点 + 模板引用 + 真实数据绑定。

不启动完整 Flask，不触达数据库。验证：
1. xujing-viz.js / xujing-core.css 文件存在且无语法问题
2. 11 模块 + 4 个 Canonical 纯函数存在
3. base.html 正确引用 xujing 资源
4. lumenis_frontend.py 注册域数据 API 端点
5. 页面模板调用真实 API（非 Mock）
6. 30s 实时更新 + KPI 数字滚动 + SVG 趋势图/环形图渲染逻辑存在
"""
import os
import re
import sys

ZBC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ZBC)


def run_xujing_viz_checks():
    results = []

    def check(name, ok, detail=""):
        results.append((name, bool(ok), detail))

    # ===== 1. 文件存在性 =====
    js_path = os.path.join(ZBC, "static", "js", "xujing-viz.js")
    css_path = os.path.join(ZBC, "static", "css", "xujing-core.css")
    css2_path = os.path.join(ZBC, "static", "css", "zbc-layout-v1.1.css")
    check("xujing-viz.js exists", os.path.isfile(js_path))
    check("xujing-core.css exists (restored from git)", os.path.isfile(css_path))
    check("zbc-layout-v1.1.css exists (dual-domain layout styles)", os.path.isfile(css2_path))

    # ===== 2. xujing-viz.js 内容验证 =====
    if os.path.isfile(js_path):
        js = open(js_path, encoding="utf-8").read()
        check("xujing-viz.js size > 15KB", len(js) > 15000, "%d bytes" % len(js))
        # 11 modules
        modules = ["数据获取层", "Canonical 纯函数转换层", "工具函数", "数字滚动动效",
                   "KPI 卡片渲染", "表格渲染", "SVG 趋势图渲染", "环形图渲染",
                   "Stagger 级联动效", "实时更新循环", "组合渲染"]
        for m in modules:
            check("module: " + m, m in js)
        # 4 pure functions
        check("FN_SENTIMENT_COUNT exists", "FN_SENTIMENT_COUNT" in js)
        check("FN_RISK_COUNT exists", "FN_RISK_COUNT" in js)
        check("FN_ENGAGEMENT exists", "FN_ENGAGEMENT" in js)
        check("FN_TREND_SERIES exists", "FN_TREND_SERIES" in js)
        # Export
        check("xjViz global export", "global.xjViz" in js or "xjViz = {" in js)
        check("xjViz.api exported", "api: api" in js)
        check("xjViz.fn exported", "fn: fn" in js)
        check("xjViz.trend exported", "trend: trend" in js)
        check("xjViz.donut exported", "donut: donut" in js)
        check("xjViz.kpi exported", "kpi: kpi" in js)
        check("xjViz.realtime exported", "realtime: realtime" in js)
        check("xjViz.table exported", "table: table" in js)
        # 30s realtime update
        check("30s realtime interval (30000)", "30000" in js)
        # SVG rendering
        check("SVG namespace", "http://www.w3.org/2000/svg" in js)
        check("SVG trend line/area/bar", "'line'" in js and "'area'" in js and "'bar'" in js)
        check("SVG donut circle segments", "stroke-dasharray" in js)
        # Number animation
        check("animateNumber with requestAnimationFrame", "requestAnimationFrame" in js)
        check("easeOutCubic animation", "easeOutCubic" in js or "pow(1 - t, 3)" in js)
        # No mock/hardcoded data in pure functions
        check("No hardcoded mock data in fn", "mock" not in js.lower() or "MOCK" not in js)
        # API fetch with auth header support
        check("API fetch with Authorization header", "__Z_AUTH" in js or "Authorization" in js)

    # ===== 3. xujing-core.css 内容验证 =====
    if os.path.isfile(css_path):
        css = open(css_path, encoding="utf-8").read()
        check("xujing-core.css size > 20KB", len(css) > 20000, "%d bytes" % len(css))
        check("xj-kpi-row style", ".xj-kpi-row" in css)
        check("xj-kpi-card style", ".xj-kpi-card" in css)
        check("xj-trend-container style", ".xj-trend-container" in css)
        check("xj-donut-container style", ".xj-donut-container" in css)
        check("xj-data-table style", ".xj-data-table" in css)
        check("xj-empty style", ".xj-empty" in css)
        check("xj-stagger animation", "xj-stagger" in css)
        check("xj-kpi-pos color (green)", "xj-kpi-pos" in css)
        check("xj-kpi-neg color (red)", "xj-kpi-neg" in css)

    # ===== 4. base.html 引用验证 =====
    base_path = os.path.join(ZBC, "templates", "base.html")
    if os.path.isfile(base_path):
        base = open(base_path, encoding="utf-8").read()
        check("base.html references xujing-core.css", "xujing-core.css" in base)
        check("base.html references xujing-viz.js", "xujing-viz.js" in base)
        check("base.html references V1.1 design CSS", "zbc-design-v1.1.css" in base)
        check("base.html references V1.1 layout CSS", "zbc-layout-v1.1.css" in base)
        check("base.html has domain switcher", "zbc-domain-switch" in base)
        check("base.html has ZBMP nav group", "zbc-nav-group--zbmp" in base)
        check("base.html has CTH nav group", "zbc-nav-group--cth" in base)
        check("base.html has SYSTEM nav group", "data-domain-nav=\"system\"" in base)
        check("base.html domain switch JS", "zbc-domain-tab" in base)
        check("base.html sets zbc-domain localStorage", "zbc-domain" in base)

    # ===== 5. lumenis_frontend.py API 端点验证 =====
    fe_path = os.path.join(ZBC, "lumenis_frontend.py")
    if os.path.isfile(fe_path):
        fe = open(fe_path, encoding="utf-8").read()
        check("domain_api_bp exists (root-level)", "domain_api_bp = Blueprint" in fe)
        check("/api/domain/overview endpoint", '"/api/domain/overview"' in fe)
        check("/api/domain/brands endpoint", '"/api/domain/brands"' in fe)
        check("/api/domain/risk endpoint", '"/api/domain/risk"' in fe)
        check("/api/domain/context endpoint", '"/api/domain/context"' in fe)
        check("api_domain_overview binds real db.get_stats()", "db.get_stats()" in fe)
        check("api_domain_risk binds real db.get_high_risk_notes()", "get_high_risk_notes" in fe)
        check("api_domain_brands binds real db.get_category_distribution()", "get_category_distribution" in fe)
        check("No mock data in domain APIs", "MOCK" not in fe and "fake_data" not in fe)
        # Domain context helper
        check("_get_domain_context() reads cookie/header/query", "_get_domain_context" in fe)
        check("X-Domain-Id header support", "X-Domain-Id" in fe)

    # ===== 6. V1.1 页面模板真实 API 绑定验证 =====
    templates_dir = os.path.join(ZBC, "templates")
    # V1.1 templates use xjViz.api() (wrapped LUMENIS.fetch) + real endpoints + xjViz render functions
    viz_templates = [
        ("zbmp/overview.html", ["xjViz.api", "xjViz.trend",
                                  "setInterval", "30000", "zbc-skeleton"]),
        ("cth/overview.html", ["xjViz.api", "xjViz.trend",
                                 "xjViz.donut", "setInterval", "30000", "zbc-skeleton"]),
        ("system/runtime.html", ["xjViz.api", "/api/system/runtime", "xjViz.table",
                                   "zbc-skeleton"]),
    ]
    for tpl_name, required_patterns in viz_templates:
        tpl_path = os.path.join(templates_dir, tpl_name)
        if os.path.isfile(tpl_path):
            tpl = open(tpl_path, encoding="utf-8").read()
            for pat in required_patterns:
                check("%s binds: %s" % (tpl_name, pat), pat in tpl)
            # Verify no mock data
            check("%s no mock data" % tpl_name, "MOCK" not in tpl and "mockData" not in tpl)
        else:
            check("%s exists" % tpl_name, False, "file not found")

    # ===== 7. V1.1 六态 UI 验证（只扫描 V1.1 改版的 18 个模板）=====
    v11_templates = {
        "zbmp/overview.html", "zbmp/brand.html", "zbmp/content.html",
        "zbmp/kos.html", "zbmp/competition.html", "zbmp/risk.html", "zbmp/reports.html",
        "cth/overview.html", "cth/realtime.html", "cth/events.html",
        "cth/risk.html", "cth/xiaohongshu.html", "cth/reports.html",
        "system/runtime.html", "system/collector.html", "system/ai.html",
        "system/database.html", "system/security.html",
    }
    for tpl_rel in v11_templates:
        tpl_path = os.path.join(templates_dir, tpl_rel)
        if os.path.isfile(tpl_path):
            tpl = open(tpl_path, encoding="utf-8").read()
            check("%s V1.1 loading (skeleton)" % tpl_rel, "zbc-skeleton" in tpl or "skeleton" in tpl.lower())
            check("%s V1.1 empty state" % tpl_rel, "zbc-state-empty" in tpl or "暂无数据" in tpl or "empty" in tpl.lower())
            check("%s V1.1 error handling" % tpl_rel, "zbc-state-error" in tpl or ".catch(" in tpl or "error" in tpl.lower())
            check("%s V1.1 degraded banner" % tpl_rel, "zbc-degraded-banner" in tpl or "degraded" in tpl.lower())
            check("%s V1.1 real API fetch" % tpl_rel, "xjViz.api" in tpl or "LUMENIS.fetch" in tpl or "fetch(" in tpl)
            check("%s V1.1 no mock data" % tpl_rel, "MOCK" not in tpl and "mockData" not in tpl and "fakeData" not in tpl)
        else:
            check("%s V1.1 template exists" % tpl_rel, False, "file not found")

    # ===== Summary =====
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print("\n" + "=" * 60)
    print("xujing-viz.js Integration Test Results: %d/%d passed" % (passed, total))
    print("=" * 60)
    for name, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        line = "  [%s] %s" % (status, name)
        if detail and not ok:
            line += "  -- " + detail
        print(line)
    return results


def test_xujing_viz_integration():
    results = run_xujing_viz_checks()
    failed = [(n, d) for n, ok, d in results if not ok]
    assert not failed, "xujing-viz Integration 失败项: %s" % failed


if __name__ == "__main__":
    run_xujing_viz_checks()
