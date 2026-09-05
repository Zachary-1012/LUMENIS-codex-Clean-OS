# -*- coding: utf-8 -*-
"""LUMENIS Frontend Foundation 验证：模板渲染 + Token 合规 + 状态系统。
不启动完整 Flask、不触达数据库/采集/业务逻辑。
既可被 pytest 收集（test_frontend_foundation），也可独立运行（python 本文件）。
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

    # 1. CSS / JS 文件齐全
    css_dir = os.path.join(ZBC, "static", "css")
    for f in ["lumenis.css", "lumenis-tokens.css", "lumenis-reset.css",
              "lumenis-layout.css", "lumenis-components.css",
              "lumenis-motion.css", "lumenis-responsive.css"]:
        check("CSS exists: " + f, os.path.isfile(os.path.join(css_dir, f)))
    js_dir = os.path.join(ZBC, "static", "js")
    for f in ["lumenis-core.js", "lumenis-icons.js"]:
        check("JS exists: " + f, os.path.isfile(os.path.join(js_dir, f)))

    # 2. Jinja 渲染 command_home
    env = Environment(loader=FileSystemLoader(os.path.join(ZBC, "templates")),
                      autoescape=select_autoescape(["html"]))
    env.globals["url_for"] = lambda endpoint, **kw: (
        "/static/" + kw.get("filename", "") if endpoint == "static" else "#")
    html = ""
    try:
        html = env.get_template("home/command_home.html").render(
            active_nav="home", home_url="/lumenis/")
        check("command_home.html renders", len(html) > 500, "%d chars" % len(html))
    except Exception as e:
        check("command_home.html renders", False, repr(e))

    # 3. 六区 + AI 入口
    for z in ["System State", "Intelligence Pulse", "Active Risks",
              "Active Tasks", "Recent Evidence", "Recommended Actions"]:
        check("zone: " + z, z in html)
    check("AI command entry present", "lm-command-input" in html)

    # 4. 无 emoji icon；内联样式无硬编码 hex
    emojis = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F600-\U0001F64F]").findall(html)
    check("No emoji icons", len(emojis) == 0, str(emojis))
    hardcoded = [m for s in re.findall(r'style="([^"]*)"', html)
                 for m in re.findall(r"#[0-9A-Fa-f]{3,6}\b", s)]
    check("No hardcoded hex inline", len(hardcoded) == 0, str(hardcoded))

    # 5. Token 双主题 / z-index / 圆角 / 动效
    tokens = open(os.path.join(css_dir, "lumenis-tokens.css"), encoding="utf-8").read()
    check("Light tokens", "--lm-canvas: #F5F4F1" in tokens)
    check("Dark tokens", '[data-theme="dark"]' in tokens and "#111111" in tokens)
    check("Z-index 8 layers", tokens.count("--lm-z-") >= 8)
    check("Radius scale", all(x in tokens for x in ["8px", "12px", "16px", "20px", "9999"]))
    check("Motion scale", all(x in tokens for x in ["120ms", "180ms", "240ms", "320ms", "420ms"]))

    # 6. JS 9 态 + 防假数据
    core = open(os.path.join(js_dir, "lumenis-core.js"), encoding="utf-8").read()
    for st in ["loading", "empty", "success", "warning", "error",
               "blocked", "offline", "processing", "completed"]:
        check("UI state: " + st, '"%s"' % st in core)
    check("Fake-state guard", "dataRef" in core and "fakeStateCount" in core)
    check("reduced-motion", "prefers-reduced-motion" in open(
        os.path.join(css_dir, "lumenis-motion.css"), encoding="utf-8").read())
    check("reduced-transparency", "prefers-reduced-transparency" in open(
        os.path.join(css_dir, "lumenis-reset.css"), encoding="utf-8").read())

    # 7. 玻璃克制 + 实色卡
    comp = open(os.path.join(css_dir, "lumenis-components.css"), encoding="utf-8").read()
    check("Card solid surface", ".lm-card" in comp and "var(--lm-surface)" in comp)
    check("Glass present", "backdrop-filter" in comp)

    # 8. Blueprint 路由（临时 app，不触达业务）
    try:
        import flask
        import lumenis_frontend
        check("blueprint import", isinstance(lumenis_frontend.lumenis_bp, flask.Blueprint))
        app = flask.Flask(__name__, template_folder=os.path.join(ZBC, "templates"),
                          static_folder=os.path.join(ZBC, "static"))
        app.register_blueprint(lumenis_frontend.lumenis_bp)
        rules = [r.rule for r in app.url_map.iter_rules()]
        check("routes exposed", "/lumenis/" in rules and "/lumenis/healthz" in rules, str(sorted(rules)))
        # PHASE 3 新页面路由
        for route in ["/lumenis/intelligence/skills", "/lumenis/intelligence/agents",
                      "/lumenis/intelligence/evaluation", "/lumenis/research"]:
            check("PHASE3 route: " + route, route in rules)
        with app.test_client() as c:
            hz = c.get("/lumenis/healthz")
            check("healthz ok", hz.status_code == 200 and hz.get_json()["status"] == "ok")
            hm = c.get("/lumenis/")
            check("home renders", hm.status_code == 200 and b"Command Home" in hm.data)
            # PHASE 3 页面渲染
            for route, keyword in [
                ("/lumenis/intelligence/skills", b"Skill Hub"),
                ("/lumenis/intelligence/agents", b"Agent Center"),
                ("/lumenis/intelligence/evaluation", b"Evaluation Center"),
                ("/lumenis/research", b"Research Workspace"),
            ]:
                try:
                    r = c.get(route)
                    check("PHASE3 render: " + route, r.status_code == 200 and keyword in r.data,
                          "status=%d" % r.status_code)
                except Exception as e:
                    check("PHASE3 render: " + route, False, repr(e))
            # Skill Hub V2 功能断言
            try:
                r = c.get("/lumenis/intelligence/skills")
                data = r.data
                check("SkillHub V2: search input", b"lm-skill-search" in data)
                check("SkillHub V2: create button", b"lm-btn-create-skill" in data)
                check("SkillHub V2: sync button", b"lm-btn-sync" in data)
                check("SkillHub V2: detail drawer", b"lm-skill-drawer" in data)
                check("SkillHub V2: 11 categories",
                      sum(1 for cat in [b"Engineering", b"Research", b"Analysis", b"Data",
                                        b"Intelligence", b"Production", b"KOS", b"Monitoring",
                                        b"Evaluation", b"Governance", b"System"]
                          if cat in data) >= 11)
                check("SkillHub V2: S01-S12 cards",
                      all(b"data-skill=\"S%02d\"" % i in data for i in range(1, 13)))
                check("SkillHub V2: enable/disable buttons", b"lm-skill-toggle" in data)
                check("SkillHub V2: run buttons", b"lm-skill-run" in data)
                check("SkillHub V2: identity policy in drawer", b"Identity Policy" in data)
                check("SkillHub V2: version badges", b"v1.0.0" in data)
            except Exception as e:
                check("SkillHub V2 features", False, repr(e))
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
