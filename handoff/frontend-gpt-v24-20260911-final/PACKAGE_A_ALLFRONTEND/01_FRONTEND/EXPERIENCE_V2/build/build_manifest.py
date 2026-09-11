# -*- coding: utf-8 -*-
"""Assemble codex_handoff/MANIFEST.json from the REAL on-disk tree (no invented counts)."""
import os,sys,json,hashlib,datetime
HERE=os.path.dirname(os.path.abspath(__file__)); EV=os.path.dirname(HERE)
sys.path.insert(0,os.path.join(HERE,"src")); import screens_meta as SM
def load(p):
    return json.load(open(os.path.join(EV,p),encoding="utf-8")) if os.path.exists(os.path.join(EV,p)) else None
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(65536),b""):h.update(b)
    return h.hexdigest()[:16]

# inventory by top folder
inv={}; total_files=0; total_bytes=0
for root,_,files in os.walk(EV):
    for fn in files:
        p=os.path.join(root,fn); rel=os.path.relpath(p,EV); top=rel.split(os.sep)[0]
        n=inv.setdefault(top,{"files":0,"bytes":0}); n["files"]+=1; n["bytes"]+=os.path.getsize(p)
        total_files+=1; total_bytes+=os.path.getsize(p)

copyreg=load("12_i18n/copy-registry.json"); actreg=load("12_contracts/ACTION_REGISTRY.json")
bind=load("12_contracts/BINDING_MATRIX.json"); gap=load("12_contracts/BACKEND_GAP.json")
pat=load("04_design_system/PATTERN_REGISTRY.json"); mot=load("06_motion/MOTION_REGISTRY.json")
reg=load("14_visual_regression/regression_report.json")
# per-screen file presence
screen_packages={}
for sid in SM.SCREEN_IDS:
    d=os.path.join(EV,"07_screens",sid)
    screen_packages[sid]=sorted(os.listdir(d)) if os.path.isdir(d) else []
shots={}
sd=os.path.join(EV,"14_visual_regression","shots")
if os.path.isdir(sd):
    for sid in os.listdir(sd): shots[sid]=sorted(os.listdir(os.path.join(sd,sid)))

manifest={
 "generated_at":datetime.datetime.now().isoformat(timespec="seconds"),
 "completion_token":"DOUBAO_FRONTEND_HANDOFF (NOT Production Ready)",
 "freeze":{"local_checkout":"ab67612367c172ced2dff62b44e98de86469d1e6",
           "remote_main":"b910117567a81b98746468e98dee3a4105d275cc",
           "remote_delta":"5 commits docs/governance only, zero source diff",
           "writable_root":"experience_v2/ (untracked, isolated)"},
 "counts":{"screens":len(SM.SCREEN_IDS),
           "copy_keys":(copyreg or {}).get("key_count"),
           "copy_parity":(sum(1 for v in (copyreg or {}).get("keys",{}).values() if v.get("parity")) if copyreg else None),
           "actions_total":(actreg or {}).get("total"),
           "actions_by_class":(actreg or {}).get("by_class"),
           "binding_rows":(bind or {}).get("rows"),
           "backend_gaps":len(gap["gaps"]) if gap and "gaps" in gap else (gap.get("rows") if gap else None),
           "patterns":len(pat.get("patterns",[])) if pat else None,
           "motions":len([k for k in (mot.get("motions",{}) if mot else {}) if k.startswith("M")]),
           "total_files":total_files,"total_bytes":total_bytes},
 "screen_packages":screen_packages,
 "regression":{"viewports":[1920,1440,1280,1024,768,430,390,360],"dark":"1440","state_boards":True,
               "errors":(reg or {}).get("errors"),"shots_per_screen":shots.get("AI-01")},
 "inventory":dict(sorted(inv.items())),
 "build_commands":["python build/verify_specs.py","python build/generate.py","python build/build_registries.py",
                   "python build/smoke_render.py","python build/capture_all.py","python 18_validation/validate_handoff.py"],
 "entry":{"codex_start":"19_handoff/INTEGRATION_START_HERE.md","prototype":"10_prototype/index.html",
          "integration_guide":"11_integration_skeleton/INTEGRATION_GUIDE.md","binding_adapter_example":"11_integration_skeleton/server_binding_adapter.example.py"},
 "deferred":{"logo_and_launch_animation":"LOGO_DEFERRED by explicit user instruction"},
 "honest_boundaries":["dense per-screen business fixture body is zh DESIGN_ONLY representative data, replaced by backend ViewModel",
                      "all data surfaces PARTIAL + CODEX_BINDING_REQUIRED; no fake endpoint","research sources never shipped as assets"]
}
out=os.path.join(EV,"codex_handoff","MANIFEST.json")
json.dump(manifest,open(out,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
print("MANIFEST",total_files,"files",total_bytes,"bytes ->",os.path.relpath(out,EV))
print("counts",json.dumps(manifest["counts"],ensure_ascii=False))
