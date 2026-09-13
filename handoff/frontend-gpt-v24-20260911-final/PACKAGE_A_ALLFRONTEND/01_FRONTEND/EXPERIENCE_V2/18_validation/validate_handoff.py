# -*- coding: utf-8 -*-
"""Deterministic handoff validation (Design Authority V2 14 gates + supplement sec35).
Read-only over the generated artifacts; writes only 17_acceptance/validation_report.json."""
import os, sys, json, re, glob
HERE=os.path.dirname(os.path.abspath(__file__)); EV=os.path.dirname(HERE)
sys.path.insert(0, os.path.join(EV,"build","src")); import screens_meta as SM
IDS=SM.SCREEN_IDS
ACC=os.path.join(EV,"17_acceptance"); os.makedirs(ACC,exist_ok=True)
checks=[]
def ck(gate, ok, detail=""): checks.append({"gate":gate,"pass":bool(ok),"detail":detail})

# 1. every JSON parses
bad=[]
for root,_,files in os.walk(EV):
    if "source_captures" in root or os.sep+"build"+os.sep in root: continue
    for fn in files:
        if fn.endswith(".json"):
            p=os.path.join(root,fn)
            try: json.load(open(p,encoding="utf-8"))
            except Exception as e: bad.append((os.path.relpath(p,EV),str(e)))
ck("all_json_parse", not bad, bad[:10])

# 2. 44 screen packages complete
need=lambda sid:[f"{sid}.html",f"{sid}.spec.json",f"{sid}.fixture.json",f"{sid}.viewmodel.json",f"{sid}.actions.json",f"{sid}.state-board.html"]
miss=[]
for sid in IDS:
    d=os.path.join(EV,"07_screens",sid)
    for fn in need(sid):
        if not os.path.exists(os.path.join(d,fn)): miss.append(f"{sid}/{fn}")
ck("screen_packages_44x6", not miss, miss[:10])

# 3. runtime data + index present
for fn in ["index.html","data/copy.js","data/fixtures.js","data/shell.js","data/screens.js"]:
    ck("runtime:"+fn, os.path.exists(os.path.join(EV,"10_prototype",fn)))
for fn in ["tokens.css","base.css","components.css","shell.css","optical.css","motion.css",
           "icons.js","orb.js","motion.js","i18n.js","optical.js","components.js","sections.js","shell.js","app.js"]:
    ck("asset:"+fn, os.path.exists(os.path.join(EV,"10_prototype","assets",fn)))

# 4. three-locale parity
reg=json.load(open(os.path.join(EV,"12_i18n","copy-registry.json"),encoding="utf-8"))
noparity=[k for k,v in reg["keys"].items() if not v["parity"]]
ck("i18n_parity", not noparity, {"key_count":reg["key_count"],"missing":noparity[:10]})

# 5. no external/third-party runtime in assets or generated html
ext=[]
pat=re.compile(r'(https?:)?//(cdn|unpkg|jsdelivr|cdnjs|ajax\.googleapis|fonts\.googleapis)',re.I)
for p in glob.glob(os.path.join(EV,"10_prototype","**","*.*"),recursive=True):
    if os.path.splitext(p)[1] in (".css",".js",".html"):
        t=open(p,encoding="utf-8",errors="ignore").read()
        if pat.search(t): ext.append(os.path.relpath(p,EV))
ck("zero_third_party_runtime", not ext, ext[:10])

# 6. no legacy product CSS/HTML leakage (old template class names) in prototype
legacy=[]; lpat=re.compile(r'\b(cortech|zbrand|taikoo-smart|app-main|el-table|ant-)[A-Za-z-]*',re.I)
for p in glob.glob(os.path.join(EV,"10_prototype","assets","*.*")):
    t=open(p,encoding="utf-8",errors="ignore").read()
    m=lpat.findall(t)
    if m: legacy.append((os.path.basename(p),sorted(set(m))[:5]))
ck("zero_legacy_css_html", not legacy, legacy[:10])

# 7. every fixture marked prototype
unmarked=[]
for sid in IDS:
    fx=json.load(open(os.path.join(EV,"07_screens",sid,f"{sid}.fixture.json"),encoding="utf-8"))
    if fx.get("data_source")!="prototype" or "DESIGN_ONLY" not in fx.get("state_source",""): unmarked.append(sid)
ck("fixtures_marked_design_only", not unmarked, unmarked[:10])

# 8. motion registry semantic_reason + reduced-motion for all M01..M15
mr=json.load(open(os.path.join(EV,"06_motion","MOTION_REGISTRY.json"),encoding="utf-8"))["motions"]
mm=[k for k in mr if k.startswith("M") and isinstance(mr[k],dict) and (not mr[k].get("semantic_reason") or not mr[k].get("reduced_motion"))]
ck("motion_semantic_and_reduced", not mm, mm)

# 9. optical degradation chain present
tok=json.load(open(os.path.join(EV,"04_design_system","design-tokens.json"),encoding="utf-8"))
ck("optical_fallback_chain", "HIGH" in tok.get("optical_degradation","") and "OPAQUE" in tok.get("optical_degradation",""))
ocss=open(os.path.join(EV,"10_prototype","assets","optical.css"),encoding="utf-8").read().lower()
ck("optical_css_tiers", all(x in ocss for x in ("opaque","soft","standard")))

# 10. binding unknowns explicitly marked
bm=json.load(open(os.path.join(EV,"12_contracts","BINDING_MATRIX.json"),encoding="utf-8"))
badrow=[r for r in bm["matrix"] if r.get("status")!="CODEX_BINDING_REQUIRED"]
ck("unknown_bindings_marked", not badrow and bm["rows"]>0, {"rows":bm["rows"]})

# 11. action contract 9 fields
ar=json.load(open(os.path.join(EV,"12_contracts","ACTION_REGISTRY.json"),encoding="utf-8"))
needfields=set(ar["contract_fields"]); badact=[]
for sid,lst in ar["screens"].items():
    for a in lst:
        if set(a.keys()) & needfields != needfields: badact.append(sid)
ck("action_9field_contract", not badact and ar["total"]>0, {"total":ar["total"],"by_class":ar["by_class"]})

# 12. regression report exists and zero overflow/missing
rrp=os.path.join(EV,"14_visual_regression","regression_report.json")
if os.path.exists(rrp):
    rr=json.load(open(rrp,encoding="utf-8")); ck("visual_regression_zero_errors", not rr.get("errors"), rr.get("errors")[:8])
else: ck("visual_regression_zero_errors", False, "regression_report.json missing (run capture_all.py)")

# 13. handoff entry present (README read-order #9)
ck("handoff_entry", os.path.exists(os.path.join(EV,"19_handoff","INTEGRATION_START_HERE.md")))

# 14. no fake endpoint declared in fixtures
fake=[]
for sid in IDS:
    sp=json.load(open(os.path.join(EV,"07_screens",sid,f"{sid}.spec.json"),encoding="utf-8"))["spec"]
    t=json.dumps(sp,ensure_ascii=False)
    if re.search(r'(fetch\(|axios|/api/[a-z0-9_/-]+\.(get|post))',t): fake.append(sid)
ck("no_fake_endpoint", not fake, fake[:10])

passed=sum(1 for c in checks if c["pass"]); total=len(checks)
report={"passed":passed,"total":total,"all_pass":passed==total,"checks":checks,
        "completion_token":"DOUBAO_FRONTEND_HANDOFF_COMPLETE_ONLY_WHEN_ALL_PASS (never Production Ready)"}
json.dump(report,open(os.path.join(ACC,"validation_report.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
print(f"VALIDATE {passed}/{total}")
for c in checks:
    if not c["pass"]: print("  FAIL",c["gate"],c["detail"])
sys.exit(0 if passed==total else 1)
