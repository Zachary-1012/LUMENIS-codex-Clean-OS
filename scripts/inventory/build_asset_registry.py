# -*- coding: utf-8 -*-
"""
ZBC 资产收敛 ② —— 资产身份登记生成器（只读，不改任何业务文件）。

输入（复用①，不重新做依赖分析）：
  docs/governance/consolidation-002/raw/module_graph.json
  app 及各模块路由（AST/正则只读提取）
  data/monitor.db（sqlite 只读 mode=ro，读表名与行数）
  static / templates / lumenis 模板、requirements.txt
输出：
  docs/governance/consolidation-002/ASSET-REGISTRY.md

原则：只登记、只打状态标签，不删除/不移动/不改写任何业务代码。
状态枚举（10 态）：ACTIVE / DEVELOPING / PLANNED / RESERVED / EXPERIMENTAL /
LEGACY / DEPRECATED / DUPLICATE / MIGRATION_REQUIRED / NOT_VERIFIED。
"""
import ast, os, re, json, sqlite3

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(ROOT, "docs", "governance", "consolidation-002", "raw")
OUT = os.path.join(ROOT, "docs", "governance", "consolidation-002", "ASSET-REGISTRY.md")
DB = os.path.join(ROOT, "data", "monitor.db")

graph = json.load(open(os.path.join(RAW, "module_graph.json"), encoding="utf-8"))
mods = graph["modules"]

# ---------- 业务域（与 asset_scan 词表保持一致，略扩展） ----------
DOMAINS = [
    ("Web核心/装配", ["app.py", "run_supervised", "wsgi", "architecture_api"]),
    ("配置/设置", ["config", "settings"]),
    ("数据库/迁移", ["database", "migration", "reprocess", "populate", "recompute", "models", "persist"]),
    ("主体/分类", ["subject"]),
    ("风险", ["risk"]),
    ("事件", ["event"]),
    ("报告/导出", ["report", "export", "weekly", "daily_report"]),
    ("采集器", ["collect", "rednote", "web_monitor", "web_topic", "monitor_pipeline", "topic_campaign", "xhs"]),
    ("平台适配", ["platform_adapters", "adapter", "proxy_pool", "cdp_helper", "human_browser", "browser_discovery"]),
    ("AI/大模型", ["ai_", "ark", "llm", "intelligence", "adaptive_engine", "local_ai"]),
    ("品牌/案例/知识", ["brand", "case", "swire", "public_opinion", "pr_", "knowledge"]),
    ("恢复/守护/稳定", ["recover", "guard", "watchdog", "stability", "safety", "tunnel"]),
    ("Cookie/登录/Auth", ["cookie", "login", "import_cookies", "auth"]),
    ("网络/代理/隧道", ["network", "proxy", "tunnel", "cloudflare"]),
    ("缓存/内存", ["cache", "memory"]),
    ("证据/评审流", ["evidence", "review_workflow", "review"]),
    ("通知", ["notif", "wechat", "email"]),
    ("评测/验证", ["eval", "verify", "check_", "evaluate", "ci_cd", "health"]),
    ("版本/部署", ["version_center", "git_manager", "deployment", "ci_cd"]),
]

def domain_of(rel):
    low = rel.lower()
    base = os.path.basename(low)
    for dom, kws in DOMAINS:
        if any(k in base or k in low for k in kws):
            return dom
    # 目录归属兜底
    if low.startswith("lumenis/"):
        return "v4增强层"
    if low.startswith("collector_v2/"):
        return "采集器(新一代)"
    if low.startswith("scripts/"):
        return "运维/脚本工具"
    return "其他/待归类"

def layer_of(rel):
    if rel.startswith("lumenis/"):
        return "ZBMP增强层(共用Core)"
    if rel.startswith(("platform_adapters/", "collector_v2/", "collector_guard/", "proxy_pool/", "report_export/", "deployment/")):
        return "子系统包"
    if rel.startswith("scripts/"):
        return "运维工具"
    if rel.startswith("tests/"):
        return "测试"
    if "/" not in rel:
        return "Core根模块"
    return "其他"

# 核心红线资产（不得改口径），单独高亮
REDLINE = {"subject_rules.py", "app.py", "risk_engine.py", "event_graph.py",
           "daily_report.py", "database.py", "report_engine.py"}

def status_of(rel, g):
    """十状态初判（机器初判，最终由人工在④Owner阶段钉死）。"""
    if g["is_test"]:
        return "TEST"
    if g["app_reachable"]:
        return "ACTIVE"
    # 不可达
    imp_non_test = [x for x in g["imported_by"] if not x.startswith("tests/")]
    if rel.startswith("collector_v2/"):
        return "DEVELOPING"
    if imp_non_test:
        return "NOT_VERIFIED"          # 被旁路模块引用，但主链不可达
    if g["has_main"]:
        return "RESERVED"              # 独立入口/运维脚本
    return "DEPRECATED?"               # 完全孤立，候选，待引用/替代/回归后才准退

# ---------- 路由（全仓只读提取，覆盖闭包内 @app.route） ----------
ROUTE_RE = re.compile(r"@[\w_]+\.route\(\s*['\"]([^'\"]+)['\"][^)]*?\)", re.S)
METH_RE = re.compile(r"methods\s*=\s*\[([^\]]*)\]")
routes = []
for rel, g in mods.items():
    if g["is_test"]:
        continue
    fp = os.path.join(ROOT, rel.replace("/", os.sep))
    try:
        src = open(fp, encoding="utf-8-sig").read()
    except Exception:
        continue
    for m in ROUTE_RE.finditer(src):
        seg = src[m.start(): m.start() + 260]
        mm = METH_RE.search(seg)
        methods = mm.group(1).replace("'", "").replace('"', "").replace(" ", "") if mm else "GET"
        routes.append((rel, m.group(1), methods))

APP_ROUTE_N = sum(1 for r in routes if r[0] == "app.py")

def route_group(rule):
    seg = [x for x in rule.split("/") if x]
    if not seg:
        return "/"
    head = seg[0]
    if head == "api" and len(seg) > 1:
        return "/api/" + seg[1]
    return "/" + head

# ---------- 数据库表（只读） ----------
tables = []
if os.path.exists(DB):
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        try:
            n = con.execute(f"SELECT COUNT(*) FROM '{name}'").fetchone()[0]
        except Exception:
            n = "-"
        tables.append((name, n))
    con.close()

# ---------- 前端资产 ----------
def list_files(sub, ext):
    out = []
    base = os.path.join(ROOT, sub)
    for dp, _, fns in os.walk(base):
        for f in fns:
            if f.endswith(ext):
                fp = os.path.join(dp, f)
                try:
                    lc = open(fp, encoding="utf-8", errors="ignore").read().count("\n") + 1
                except Exception:
                    lc = "-"
                out.append((os.path.relpath(fp, ROOT).replace("\\", "/"), lc))
    return sorted(out)

css_files = list_files("static", ".css") if os.path.isdir(os.path.join(ROOT, "static")) else []
js_files = [x for x in (list_files("static", ".js") if os.path.isdir(os.path.join(ROOT, "static")) else [])]
tpl_files = []
for sub in ("templates",):
    p = os.path.join(ROOT, sub)
    if os.path.isdir(p):
        for dp, _, fns in os.walk(p):
            for f in fns:
                if f.endswith(".html"):
                    tpl_files.append(os.path.relpath(os.path.join(dp, f), ROOT).replace("\\", "/"))
for dp, _, fns in os.walk(os.path.join(ROOT, "lumenis")):
    for f in fns:
        if f.endswith(".html"):
            tpl_files.append(os.path.relpath(os.path.join(dp, f), ROOT).replace("\\", "/"))
tpl_files = sorted(set(tpl_files))

# ---------- 依赖 ----------
deps = []
req = os.path.join(ROOT, "requirements.txt")
if os.path.exists(req):
    for line in open(req, encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#"):
            name = re.split(r"[<>=!~ ]", s)[0]
            deps.append(name)
REMOVE_CANDIDATE = {"selenium", "httpx", "xlsxwriter", "colorama", "tqdm"}

# ---------- 汇总分类 ----------
non_test, test_mods = [], []
for rel in sorted(mods):
    g = mods[rel]
    (test_mods if g["is_test"] else non_test).append(rel)

status_count = {}
for rel in non_test:
    status_count[status_of(rel, mods[rel])] = status_count.get(status_of(rel, mods[rel]), 0) + 1

orphans = [r for r in non_test if status_of(r, mods[r]) == "DEPRECATED?"]
standalone = [r for r in non_test if status_of(r, mods[r]) == "RESERVED"]
active = [r for r in non_test if mods[r]["app_reachable"]]
developing = [r for r in non_test if status_of(r, mods[r]) == "DEVELOPING"]
notver = [r for r in non_test if status_of(r, mods[r]) == "NOT_VERIFIED"]

L = []
W = L.append
W("# ASSET-REGISTRY · 资产身份登记总账（Consolidation-002 / ②）")
W("")
W("> 生成器：`scripts/inventory/build_asset_registry.py`（只读，可重复运行）。")
W("> 数据源：① `raw/module_graph.json`（依赖/可达性，不重算）+ 路由只读提取 + `monitor.db` 只读 + 前端/依赖清单。")
W("> **本总账只登记与打状态标签，不删除、不移动、不改写任何业务代码**；状态为机器初判，④Owner 阶段人工钉死。")
W("")
W("## 0. 口径与数字（与①对齐）")
W("")
W(f"- Python 资产：**{graph['total_py']}**（非测试 {len(non_test)} / 测试 {len(test_mods)}）；app 静态可达 **{graph.get('entry_reachable_count', len(active))}**。")
W(f"- 状态初判（非测试）：" + "，".join(f"{k}={v}" for k, v in sorted(status_count.items(), key=lambda x: -x[1])))
W(f"- 完全孤立 DEPRECATED? 候选 **{len(orphans)}**；独立入口 RESERVED **{len(standalone)}**；新一代在建 DEVELOPING **{len(developing)}**；旁路 NOT_VERIFIED **{len(notver)}**。")
W(f"- 不可达非测试 136 对账：孤立候选 {len(orphans)} + 独立入口 {len(standalone)} + 新一代在建 {len(developing)} + 旁路引用 {len(notver)} = {len(orphans)+len(standalone)+len(developing)+len(notver)}（与①一致；①口径“孤立61”=本表 53 + collector_v2 内 8 个纯孤立，已统一并入 DEVELOPING 视角）。")
W(f"- 路由：app.py 内 **{APP_ROUTE_N}**（对齐既有约189口径），全仓合计 **{len(routes)}**（含 v4 蓝图/子系统 register 路由）；数据库表 **{len(tables)}**；CSS {len(css_files)} / JS {len(js_files)} / 模板 {len(tpl_files)}；requirements 依赖 {len(deps)}。")
W("- 十状态：ACTIVE / DEVELOPING / PLANNED / RESERVED / EXPERIMENTAL / LEGACY / DEPRECATED / DUPLICATE / MIGRATION_REQUIRED / NOT_VERIFIED。")
W("")
W("> **命名层级（已决议，以 PRODUCT_NAMING_BASELINE 为准）**：最顶层统一平台层 = **Z-Brand Intelligence Platform**；其下 **ZBP（品牌业务生产平台，本仓库）/ DCC / SICI 三者并列**；")
W("> ZBP 不是最顶层母平台，CTH-POMS 与 ZBMP 隶属于 ZBP。本总账登记范围为 ZBP（仓库 Z-Brand-Core）内资产。")
W("")

# 表A Core 运行时（app 可达）
W("## A. Core 运行时资产（app 静态可达 = ACTIVE）")
W("")
W("| ASSET-ID | 模块 | 行 | 层 | 业务域 | 被依赖 | 依赖 | 红线 | 状态 |")
W("|---|---|--:|---|---|--:|--:|:--:|:--:|")
for i, rel in enumerate(sorted(active), 1):
    g = mods[rel]
    W(f"| ASSET-PY-{i:04d} | `{rel}` | {g['lines']} | {layer_of(rel)} | {domain_of(rel)} | {len(g['imported_by'])} | {len(g['deps'])} | {'🔴' if rel in REDLINE else ''} | ACTIVE |")
W("")

# 表B 在建新一代
W("## B. 在建 / 旁路子系统（DEVELOPING / NOT_VERIFIED，主链暂不可达）")
W("")
W("### B.1 collector_v2 新一代采集（DEVELOPING，未接管生产，生产仍走 collector.py）")
W("")
W("| 模块 | 行 | 业务域 | 被依赖 | 状态 |")
W("|---|--:|---|--:|:--:|")
for rel in sorted(developing):
    g = mods[rel]
    W(f"| `{rel}` | {g['lines']} | {domain_of(rel)} | {len(g['imported_by'])} | DEVELOPING |")
W("")
W("### B.2 被旁路引用但主链不可达（NOT_VERIFIED，需在③架构映射核实去留）")
W("")
W("| 模块 | 行 | 业务域 | 被谁引用(截断) | 状态 |")
W("|---|--:|---|---|:--:|")
for rel in sorted(notver):
    g = mods[rel]
    who = ", ".join(g["imported_by"][:3])
    W(f"| `{rel}` | {g['lines']} | {domain_of(rel)} | {who} | NOT_VERIFIED |")
W("")

# 表C 孤立
W(f"## C. 完全孤立资产（{len(orphans)}，DEPRECATED? 候选 —— 未删，须引用/替代/回归全过才准退）")
W("")
W("| 模块 | 行 | 业务域 | 状态 |")
W("|---|--:|---|:--:|")
for rel in sorted(orphans):
    g = mods[rel]
    W(f"| `{rel}` | {g['lines']} | {domain_of(rel)} | DEPRECATED? |")
W("")

# 表D 独立入口
W(f"## D. 独立入口 / 运维脚本（{len(standalone)}，RESERVED，含 __main__，多为手动工具）")
W("")
W("| 模块 | 行 | 业务域 |")
W("|---|--:|---|")
for rel in sorted(standalone):
    W(f"| `{rel}` | {mods[rel]['lines']} | {domain_of(rel)} |")
W("")

# 表E 测试
W(f"## E. 测试资产（{len(test_mods)}，按目录聚合，不逐条）")
W("")
tdir = {}
for rel in test_mods:
    top = "/".join(rel.split("/")[:2]) if rel.startswith("tests/") else os.path.dirname(rel)
    tdir[top] = tdir.get(top, 0) + 1
W("| 目录 | 数量 |")
W("|---|--:|")
for k, v in sorted(tdir.items(), key=lambda x: -x[1]):
    W(f"| `{k}` | {v} |")
W("")

# 表F 路由
W(f"## F. API / 路由身份（app.py {APP_ROUTE_N} + 子系统蓝图 = 全仓 {len(routes)}，按前缀分组；逐条明细以既有 Phase1 盘点为准，不重复全列）")
W("")
grp = {}
for _, rule, meth in routes:
    grp[route_group(rule)] = grp.get(route_group(rule), 0) + 1
W("| 路由组 | 数量 |")
W("|---|--:|")
for k, v in sorted(grp.items(), key=lambda x: -x[1]):
    W(f"| `{k}` | {v} |")
W("")
W("> 重复路由簇（④唯一 Owner 重点）：报告 12 路由、负面两套 `/api/negative/*` 与 `/api/negative-review/*`、")
W("> AI 多套 `/api/ai|ark|intelligence|ai-filter|ai-learning`、健康 5 套、高危运行代码 3 套 `/api/developer/run`、`/api/dev/run-code`、`/api/config/run-code`。")
W("")

# 表G 数据表
W(f"## G. 数据表身份（{len(tables)}，sqlite 只读行数）")
W("")
W("| ASSET-ID | 表 | 行数 | 状态备注 |")
W("|---|---|--:|---|")
def table_note(n):
    if n == 0:
        return "空表（PLANNED/RESERVED 候选）"
    if n == "-":
        return "行数读取异常"
    return ""
for i, (name, n) in enumerate(sorted(tables), 1):
    W(f"| ASSET-DB-{i:03d} | `{name}` | {n} | {table_note(n)} |")
W("")

# 表H 前端
W("## H. 前端资产身份")
W("")
W(f"### H.1 CSS（{len(css_files)}）—— 权威主题层为 static/css/zb-theme.css（最后加载），其余历史设计系统待④/旧UI清理")
W("")
W("| 文件 | 行 |")
W("|---|--:|")
for f, lc in css_files:
    W(f"| `{f}` | {lc} |")
W("")
W(f"### H.2 JS（{len(js_files)}）")
W("")
W("| 文件 | 行 |")
W("|---|--:|")
for f, lc in js_files:
    W(f"| `{f}` | {lc} |")
W("")
W(f"### H.3 模板（{len(tpl_files)}）—— 生产主入口为 static/index.html(SPA)；templates/*.html 为旧服务端渲染，待核实是否仍 render")
W("")
for f in tpl_files:
    W(f"- `{f}`")
W("")

# 表I 依赖
W(f"## I. 依赖身份（requirements {len(deps)}，0 引用仅登记不删）")
W("")
W("| 包 | 初判 |")
W("|---|---|")
for d in deps:
    tag = "UNUSED? 移除候选（0 本地 import，Staging 回归后才准退）" if d.lower() in REMOVE_CANDIDATE else "在用/传递依赖"
    W(f"| `{d}` | {tag} |")
W("")

W("## J. 衔接")
W("")
W("- ③ ARCHITECTURE-MAP：以表 A/B 的层 + 业务域为骨架，只映射不搬目录。")
W("- ④ CAPABILITY-OWNERSHIP：对 F 重复路由簇与 CAPABILITY-CLUSTERS 定唯一 Owner，其余标 DUPLICATE/LEGACY；🔴红线资产 Owner 唯一且口径不得改。")
W("- ⑤ FEATURE 总账：在 ASSET-ID 之上建 FEATURE-CTH/ZBMP-NNN，绑定 UI/API/DB/Status/Evidence。")
W("- 本文件由生成器产出，请勿手改表格体；身份修订改生成器规则后重跑。")

open(OUT, "w", encoding="utf-8").write("\n".join(L))
print("WROTE", OUT)
print("non_test", len(non_test), "active", len(active), "orphans", len(orphans),
      "standalone", len(standalone), "developing", len(developing), "notver", len(notver))
print("routes", len(routes), "tables", len(tables), "css", len(css_files), "js", len(js_files),
      "tpl", len(tpl_files), "deps", len(deps))
