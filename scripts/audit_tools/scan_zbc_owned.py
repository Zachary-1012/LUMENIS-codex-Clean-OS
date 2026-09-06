import os
ROOT = r"D:\Taikoo-monitor-new"
def is_noise(d):
    return d.startswith((".", "edge-cdp", "__pycache__")) or d in ("node_modules","site-packages","00-GOVERNANCE","99-ARCHIVE")
def walk():
    for dp,dn,fn in os.walk(ROOT):
        dn[:]=[d for d in dn if not is_noise(d)]
        for f in fn:
            yield os.path.relpath(os.path.join(dp,f),ROOT).replace("\\","/")
files=list(walk())

print("===== 1) docs 下规则/术语/设计/标准文档 =====")
for r in sorted(files):
    if r.startswith("docs/") and r.endswith(".md") and any(k in r.lower() for k in
        ("termin","naming","rule","规则","术语","design","design","ui","ux","language","standard","标准","i18n","多语","lang")):
        print("  ",r)

print("\n===== 2) static 前端资产结构 =====")
for r in sorted(files):
    if r.startswith("static/") and (r.endswith((".css",".svg",".woff",".woff2",".ttf")) or "/i18n/" in r or "/locale" in r or "/icons" in r):
        print("  ",r)
print("  -- static/js 顶层脚本 --")
for r in sorted(files):
    if r.startswith("static/js/") and r.endswith(".js"): print("   ",r)

print("\n===== 3) 核心功能规则模块(存在性+行数) =====")
core=["subject_rules.py","risk_engine.py","kos_metrics.py","kos_attribution.py","kos_engine.py",
      "canonical_data.py","zbc_canonical_data.py","evidence_chain.py","data_quality_gate.py",
      "domain_isolation.py","subject_classifier.py","subject_context.py","compliance_gate.py",
      "evaluation_system.py","evaluation_dimensions.py","ui_view_model.py","canonical_metrics.py",
      "data_boundary.py","alert_engine.py","daily_report.py","report_engine.py"]
for c in core:
    hit=[r for r in files if r.endswith("/"+c) or r==c]
    for r in hit:
        try:
            n=sum(1 for _ in open(os.path.join(ROOT,r),"rb"))
        except Exception: n=-1
        print(f"   {n:>5}行  {r}")

print("\n===== 4) ZBC自有 i18n/三语/语言切换 真实命中(排除浏览器) =====")
import re
pat=re.compile(r"(i18n|zh-CN|zh_CN|locale|多语|中英|languageSwitch|switchLang|lang\s*=|한국|en-US)",re.I)
cnt=0
for r in files:
    if r.startswith(("static/","templates/")) and r.endswith((".js",".html",".json")):
        try:
            t=open(os.path.join(ROOT,r),encoding="utf-8",errors="ignore").read()
            if pat.search(t): print("   命中:",r); cnt+=1
        except Exception: pass
print("   ZBC自有i18n命中文件数:",cnt)

print("\n===== 5) ZBC自有图标(static内svg/图标字体/sprite) =====")
ic=[r for r in files if r.startswith("static/") and (r.endswith(".svg") or "icon" in r.lower() and r.endswith((".css",".js",".json")))]
for r in sorted(ic)[:40]: print("   ",r)
print("   图标相关文件数:",len(ic))
