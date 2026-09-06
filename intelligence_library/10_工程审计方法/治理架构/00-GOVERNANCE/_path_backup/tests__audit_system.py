# -*- coding: utf-8 -*-
import sys, io, os, sqlite3, re, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = r"D:\Taikoo-monitor-new"
os.chdir(ROOT)

def sec(t): print("\n" + "="*20 + f" {t} " + "="*20)

# ---------- 数据库 ----------
sec("数据库 data/monitor.db")
db = os.path.join(ROOT, "data", "monitor.db")
print("db exists:", os.path.exists(db), "size=%.1fKB" % (os.path.getsize(db)/1024))
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
cur = con.cursor()
tabs = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
print("表数量:", len(tabs))
rows = {}
for t in tabs:
    try:
        n = cur.execute(f"SELECT COUNT(*) FROM '{t}'").fetchone()[0]
    except Exception as e:
        n = f"ERR:{e}"
    rows[t] = n
for t in tabs:
    print(f"  {t:32} {rows[t]}")

def cols(table):
    try:
        return [r[1] for r in cur.execute(f"PRAGMA table_info('{table}')")]
    except Exception:
        return []
for key in ("notes", "events", "swire_projects", "swire_events", "swire_notes"):
    if key in tabs:
        print(f"\n[{key}] 列:", cols(key))
# 关键口径核查
if "notes" in tabs:
    nc = cols("notes")
    print("\nnotes 时间列: publish_datetime?", "publish_datetime" in nc,
          "| publish_date?", "publish_date" in nc, "| captured_at/collected_at?",
          [c for c in nc if "captur" in c or "collect" in c])
    # 空正文
    bodycol = next((c for c in nc if c in ("content","body","note_text","text")), None)
    if bodycol:
        empty = cur.execute(f"SELECT COUNT(*) FROM notes WHERE {bodycol} IS NULL OR TRIM({bodycol})=''").fetchone()[0]
        total = cur.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        print(f"notes 总数={total}, 空正文({bodycol})={empty}")
    # subject_type/content_type
    print("notes subject_type?", "subject_type" in nc, " content_type?", "content_type" in nc,
          " user_type?", "user_type" in nc)
if "events" in tabs:
    ec = cols("events")
    print("events event_type?", [c for c in ec if "type" in c or "kind" in c or "relation" in c],
          " event_date?", "event_date" in ec)
# event_relation 表?
print("event_relation 相关表:", [t for t in tabs if "relation" in t])
con.close()

# ---------- 路由枚举 ----------
sec("路由 / 蓝图")
appsrc = open(os.path.join(ROOT,"app.py"), encoding="utf-8").read()
routes = re.findall(r"@app\.route\((['\"])(.*?)\1", appsrc)
methods = re.findall(r"@app\.route\([^)]*\)", appsrc)
print("app.py @app.route 数量:", len(routes))
pfx = {}
for _, p in routes:
    top = "/" + p.strip("/").split("/")[0]
    pfx[top] = pfx.get(top,0)+1
for k,v in sorted(pfx.items(), key=lambda x:-x[1])[:25]:
    print(f"   {k:28} {v}")
# v4 蓝图
print("\nv4_upgrade 子蓝图:")
for f in glob.glob(r"v4_upgrade\**\routes.py", recursive=True):
    src=open(f,encoding="utf-8").read()
    bps=re.findall(r'Blueprint\(\s*["\']([^"\']+)["\']',src)
    rs=re.findall(r'@\w+_bp\.route\((["\'])(.*?)\1',src)
    print(f"  {f.split('v4_upgrade')[1]:40} bp={bps} routes={len(rs)}")

# ---------- AI 调用链 ----------
sec("AI / Ollama 调用链（云端AI默认开关）")
ai_pat = re.compile(r"^\s*(?:from|import)\s+(\w+)", re.M)
hits = {"openai":[], "dashscope":[], "openai_lib":[], "ark":[], "deepseek":[], "ollama":[], "zhipuai":[], "requests_to_ai":[]}
scan_dirs = ["."]
for py in glob.glob(r"**\*.py", recursive=True):
    if any(x in py for x in (".venv","__pycache__","node_modules",".skills-router",".trae-cn","tests")):
        continue
    try: src=open(py,encoding="utf-8",errors="replace").read()
    except: continue
    if re.search(r"\bimport openai\b|from openai", src): hits["openai_lib"].append(py)
    if "dashscope" in src: hits["dashscope"].append(py)
    if re.search(r"volcenginesdkark|ark_runtime|from ark|import ark", src): hits["ark"].append(py)
    if "deepseek" in src.lower(): hits["deepseek"].append(py)
    if "ollama" in src.lower(): hits["ollama"].append(py)
for k,v in hits.items():
    print(f"  {k:14} ({len(v)}): {v[:8]}")
# AI_PROVIDER 默认
m=re.findall(r"AI_PROVIDER[^\n]{0,60}", appsrc)
print("  app.py AI_PROVIDER 行:", m[:3])
for f in ("intelligence.py","local_ai_client.py","ai_gateway_v570.py"):
    if os.path.exists(f):
        s=open(f,encoding="utf-8",errors="replace").read()
        prov=re.findall(r"(?:provider|PROVIDER|prefer|DEFAULT)[^\n]{0,55}", s)[:4]
        print(f"  {f} 关键行:", prov)

# ---------- subject_type/content_type/三类事件 落地 ----------
sec("品牌传播：subject_type/content_type/三类事件/event_relation 源码落地")
terms = ["subject_type","content_type","user_type","营销事件","传播事件","舆情事件","event_relation","KOL","KOC","KOS"]
counts={}
for term in terms:
    c=0; files=set()
    for py in glob.glob(r"**\*.py",recursive=True)+glob.glob(r"**\*.html",recursive=True)+glob.glob(r"**\*.js",recursive=True):
        if any(x in py for x in (".venv","__pycache__","node_modules",".skills-router",".trae-cn")):continue
        try:s=open(py,encoding="utf-8",errors="replace").read()
        except:continue
        n=s.count(term)
        if n:c+=n;files.add(py.replace("\\","/"))
    counts[term]=(c,sorted(files)[:6])
for t,(c,f) in counts.items():
    print(f"  {t:10} 出现{c}次  文件={f}")

# ---------- 前端页面 ----------
sec("前端页面")
print("templates/:", sorted(os.path.basename(x) for x in glob.glob(r"templates\*")))
st = sorted(os.path.basename(x) for x in glob.glob(r"static\*.html"))
print("static/*.html 数量:", len(st), st[:40])
v4html = [x.replace("\\","/").split("v4_upgrade/")[1] for x in glob.glob(r"v4_upgrade\**\*.html",recursive=True)]
print("v4 模板:", v4html)

# ---------- 测试 ----------
sec("测试文件（正式 test，排除 _ 临时）")
tests=[os.path.basename(x) for x in glob.glob(r"tests\test*.py")]+[os.path.basename(x) for x in glob.glob(r"test_*.py")]
tmp=[os.path.basename(x) for x in glob.glob(r"tests\_*.py")]
print("正式 test 数量:", len(tests))
for t in sorted(set(tests)): print("   ",t)
print("临时 _ 脚本数量:", len(tmp))

# ---------- 调度 ----------
sec("调度器线索")
for f in ("collector_automation.py","topic_campaign.py","system_guardian.py","auto_recovery.py"):
    if os.path.exists(f):
        s=open(f,encoding="utf-8",errors="replace").read()
        th=len(re.findall(r"Thread\(|schedule|APScheduler|BlockingScheduler|BackgroundScheduler",s))
        dis = "禁用" if ("暂时禁用" in s or "disabled" in s.lower() and "scheduler" in s.lower()) else ""
        print(f"  {f:28} 调度关键词{th} {dis}")
print("\nAUDIT_DONE")
