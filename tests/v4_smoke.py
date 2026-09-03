# -*- coding: utf-8 -*-
"""V4 模块零污染旁路冒烟测试：临时库 + Flask test_client，不碰真实 data/monitor.db、不占 8200。"""
import os, sys, tempfile, json, traceback
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
TMP = os.path.join(ROOT, "tests", "_v4_smoke.db")
if os.path.exists(TMP):
    os.remove(TMP)
os.environ["MONITOR_DB_PATH"] = TMP  # 必须在 import v4_upgrade 之前
os.environ["V4_TOKEN_SECRET"] = "smoke-test-secret"

PASS, FAIL = [], []
def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {extra}")

# 1) 依赖/import
try:
    from flask import Flask
    import v4_upgrade
    from v4_upgrade import create_v4_blueprint, init_v4_modules
    from v4_upgrade.adapters import registry, register_default_adapters
    from v4_upgrade.importer.analyzer import analyze_text
    check("import v4_upgrade 成功", True, v4_upgrade.__version__)
except Exception:
    traceback.print_exc(); print("import 阶段即失败，终止"); sys.exit(1)

# 2) 8 适配器能否全部 import+注册（重点：是否有顶层硬依赖缺失）
try:
    register_default_adapters()
    plats = registry.list_platforms()
    check("8 个采集适配器全部注册", len(plats) == 8, f"-> {plats}")
except Exception:
    traceback.print_exc(); check("8 个采集适配器全部注册", False)

# 3) 独立 app + 蓝图（不碰 app.py / 8200）
app = Flask(__name__)
app.config["TESTING"] = True
init_v4_modules()
app.register_blueprint(create_v4_blueprint())

# 临时库建最小 notes 表 + 样本（隔离验证 data_cleanup / importer 列对齐）
import sqlite3
c = sqlite3.connect(TMP)
c.execute("""CREATE TABLE IF NOT EXISTS notes(
  id INTEGER PRIMARY KEY, note_id TEXT, title TEXT, content TEXT, url TEXT,
  author_nickname TEXT, publish_date TEXT, collected_at TEXT, xsec_token TEXT,
  source_platform TEXT, sentiment TEXT, sentiment_score REAL, topics TEXT,
  category TEXT, summary TEXT)""")
c.execute("INSERT INTO notes(note_id,title,content,publish_date,collected_at) VALUES('n1','空正文笔记','','3小时前','2026-08-29 10:00:00')")
c.execute("INSERT INTO notes(note_id,title,content,publish_date,collected_at) VALUES('n2','正常笔记','太古汇商场环境很舒适，很喜欢','2026-08-28','2026-08-29 10:00:00')")
c.commit(); c.close()

# 4) 临时库是否只建了 v4_ 表（不污染既有表名）
c = sqlite3.connect(TMP)
tabs = [r[0] for r in c.execute("select name from sqlite_master where type='table'")]
v4tabs = [t for t in tabs if t.startswith("v4_")]
check("建表全部带 v4_ 前缀(5张)", set(v4tabs) >= {"v4_users","v4_sessions","v4_audit_logs","v4_security_questions","v4_login_attempts"}, str(v4tabs))
c.close()

cli = app.test_client()

def jpost(path, obj, token=None):
    h = {"Content-Type": "application/json"}
    if token: h["Authorization"] = "Bearer " + token
    return cli.post(path, data=json.dumps(obj), headers=h)
def jget(path, token=None):
    h = {}
    if token: h["Authorization"] = "Bearer " + token
    return cli.get(path, headers=h)

# 5) health
r = cli.get("/v4/health"); d = r.get_json()
check("GET /v4/health 200", r.status_code == 200 and d.get("success"), str(d))

# 6) 未登录 401
r = jget("/v4/auth/me"); check("未登录访问 /v4/auth/me ->401", r.status_code == 401, str(r.status_code))

# 7) 错误密码
r = jpost("/v4/auth/login", {"username":"Zachary","password":"wrong"})
check("错误密码登录失败", r.status_code == 200 and r.get_json().get("success") is False)

# 8) 主账号登录
r = jpost("/v4/auth/login", {"username":"Zachary","password":"Zachary01"})
d = r.get_json(); owner_token = d.get("token","")
check("主账号 Zachary 登录成功", d.get("success") is True and d["user"]["role"]=="owner", str(d.get("user")))

# 9) me
r = jget("/v4/auth/me", owner_token); check("Bearer /v4/auth/me=owner", r.get_json().get("user",{}).get("role")=="owner")

# 9.5) 密钥登录（替代短信验证码的第二登录方式）
r = jpost("/v4/auth/login-by-key", {"access_key": "wrong"})
check("错误密钥被拒且非500", r.status_code == 200 and r.get_json().get("success") is False, str(r.status_code))
r = jpost("/v4/auth/login-by-key", {"access_key": "张志宏"})
kd = r.get_json()
check("正确密钥(张志宏)->owner登录", kd.get("success") is True and kd["user"]["role"] == "owner", str(kd.get("user")))
anon = app.test_client()  # 全新匿名 client，避免前面登录的 cookie 污染“未登录”断言
r = anon.get("/v4/settings/")
check("未登录访问设置页302到登录页", r.status_code == 302 and "/login" in (r.headers.get("Location") or ""), str(r.status_code))
r = anon.get("/v4/settings/login")
check("V4自带登录页200", r.status_code == 200 and "密钥登录" in r.get_data(as_text=True))

# 10) 设置页渲染（苹果风模板）
r = jget("/v4/settings/", owner_token)
body = r.get_data(as_text=True)
check("设置页 /v4/settings/ 渲染200", r.status_code==200 and len(body)>500, f"len={len(body)}")

# 11) 用户列表 / 审计统计 / 安全问答
r = jget("/v4/settings/api/users", owner_token)
us = r.get_json(); check("owner 看用户列表含Zachary", any(u["username"]=="Zachary" for u in us.get("users",[])))
r = jget("/v4/settings/api/audit-stats", owner_token); check("审计统计200", r.status_code==200)
r = jget("/v4/settings/api/security-questions", owner_token)
check("默认安全问答2条", len(r.get_json().get("questions",[]))==2)

# 12) 创建管理员：缺安全问答->403；带正确问答->成功
r = jpost("/v4/settings/api/users", {"username":"admin1","password":"abc123","role":"admin"}, owner_token)
check("建管理员缺安全问答->403", r.status_code==403)
r = jpost("/v4/settings/api/users", {"username":"admin1","password":"abc123","role":"admin",
    "security_answers":{"手机号":"18504635216","生日":"1012"}}, owner_token)
check("带正确安全问答建管理员成功", r.get_json().get("success") is True, str(r.get_json()))
# 错误问答
r = jpost("/v4/settings/api/users", {"username":"u2","password":"abc123","role":"user",
    "security_answers":{"手机号":"000","生日":"1012"}}, owner_token)
check("错误安全问答被拒", r.status_code==403)
# 管理员上限/角色
r = jpost("/v4/settings/api/users", {"username":"admin4","password":"abc123","role":"admin",
    "security_answers":{"手机号":"18504635216","生日":"1012"}}, owner_token)  # 只建了1个，应成功第2个；测到第4个才拒
# 13) admin 登录后越权 owner 接口
r = jpost("/v4/auth/login", {"username":"admin1","password":"abc123"}); at=r.get_json().get("token","")
check("管理员登录成功", bool(at))
r = jget("/v4/settings/api/users", at); check("admin 访问 owner 用户列表->403", r.status_code==403)
r = jget("/v4/adapters/platforms", at); check("admin 可访问登录级 适配器列表", r.status_code==200)

# 14) 适配器状态（owner）
r = jget("/v4/adapters/platforms", owner_token); dd=r.get_json()
check("适配器平台状态列表", dd.get("success") and len(dd.get("platforms",[]))==8, str([p['platform'] for p in dd.get('platforms',[])]))

# 15) analyzer 规则回退（AI 撤出也能跑）
notes = analyze_text("太古汇15周年活动很热闹，整体体验不错，值得推荐。")
check("analyze_text 规则回退产出笔记", len(notes)>=1 and notes[0].title, f"sentiment={notes[0].sentiment if notes else '-'}")

# 16) 数据清洗（隔离库样本）
from v4_upgrade.data_cleanup.fix_publish_date import fix_publish_dates, find_empty_content_notes, generate_backfill_tasks
dry = fix_publish_dates(dry_run=True)
check("publish_date dry-run 识别脏数据", dry["dirty_count"]>=1, str({k:dry[k] for k in ('total_checked','dirty_count')}))
emp = find_empty_content_notes()
check("空正文笔记识别", emp["total"]>=1, f"total={emp['total']} by={emp['by_platform']}")
bt = generate_backfill_tasks(10)
check("补抓任务分批", bt["total_batches"]>=1, f"batches={bt['total_batches']}")

# 17) 登出
r = jpost("/v4/auth/logout", {}, owner_token); check("登出成功", r.get_json().get("success") is True)
r = jget("/v4/auth/me", owner_token); check("登出后 token 失效->401", r.status_code==401)

print(f"\n==== 结果：PASS {len(PASS)} / FAIL {len(FAIL)} ====")
if FAIL: print("失败项:", FAIL)
sys.exit(1 if FAIL else 0)
