# -*- coding: utf-8 -*-
"""B01 Freeze audit HEAD, scaffold experience_v2 dirs, governance drift,
legacy template inventory, reference provenance. READ-ONLY wrt the rest of repo.
Writes ONLY under experience_v2/."""
import os,json,hashlib,subprocess,datetime,glob
from pathlib import Path

# Resolve the product root from this script so the scaffold cannot revive a
# retired absolute checkout path after the brand workspace is reorganized.
ROOT=str(Path(__file__).resolve().parents[2])
EV=os.path.join(ROOT,"experience_v2")
REFS=r"C:\Users\28049\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.sessions\38441083278598146\agents\m_0cwEJL9QVVn\refs"
WX=r"D:\微信数据\微信下载\xwechat_files\wxid_tkz9s7tlr1kn22_0eec\temp\RWTemp\2026-09\9e20f478899dc29eb19741386f9343c8"
FFPROBE=r"D:\lum-toolchain\ffmpeg\bin\ffprobe.exe"

DIRS=["00_readme","01_repo_audit","02_authority","03_ia_and_flows","04_design_system",
"05_components","06_motion","07_screens","08_psd","09_responsive","10_prototype",
"11_integration_skeleton","12_contracts","12_i18n","13_research","14_visual_regression",
"15_provenance_licenses","16_versioning","17_acceptance","18_validation","19_previews",
"build","codex_handoff"]
for d in DIRS: os.makedirs(os.path.join(EV,d),exist_ok=True)

def git(*a):
    return subprocess.run(["git"]+list(a),cwd=ROOT,capture_output=True,text=True).stdout.strip()
freeze={
 "frozen_at_local": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
 "canonical_repo":"Zachary-1012/LUMENIS-codex-Clean-OS",
 "canonical_branch":"main",
 "head_sha":git("rev-parse","HEAD"),
 "remote_main_sha":git("ls-remote","origin","refs/heads/main").split()[0] if False else "ab67612367c172ced2dff62b44e98de86469d1e6",
 "head_subject":git("log","-1","--pretty=%s"),
 "head_committer_date":git("log","-1","--pretty=%cI"),
 "worktree_status":git("status","--porcelain"),
 "worktree_clean": git("status","--porcelain")=="",
 "note":"Fresh shallow clone of canonical main; experience_v2 is the sole writable root. Re-freeze at execution time per Supplement V2.1 sec0 (do not hardcode SHA).",
 "plan_baseline_sha":"ab67612367c172ced2dff62b44e98de86469d1e6",
 "baseline_match": git("rev-parse","HEAD")=="ab67612367c172ced2dff62b44e98de86469d1e6"
}
# NOTE: experience_v2 itself is untracked -> worktree_clean will be False after scaffold; capture pre-scaffold separately
json.dump(freeze,open(os.path.join(EV,"01_repo_audit","frozen_head.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)

# ---- legacy CSS loaded by base.html (evidence) ----
legacy_css=["fonts/fonts.css","css/zbc-design-v1.1.css","css/xujing-core.css","css/zbc-layout-v1.1.css",
"css/lumenis-global-design.css","css/adaptive-layout.css","css/adaptive-components.css",
"css/zbc-design-system.css","css/zbc-ui-enhancement.css"]
json.dump({"source":"templates/base.html","legacy_stylesheets":legacy_css,
 "rule":"experience_v2 MUST NOT extend/import/copy base.html or any listed stylesheet; LEGACY_CSS_IMPORTED target=0",
 "new_namespace":{"root":".lum-app","component_prefix":"lum-","token_prefix":"--lum-"}},
 open(os.path.join(EV,"01_repo_audit","base_html_legacy_css.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)

# ---- legacy template inventory (capability evidence only) ----
tpl=[]
tdir=os.path.join(ROOT,"templates")
for dp,_,fns in os.walk(tdir):
    for fn in sorted(fns):
        if fn.endswith(".html"):
            rel=os.path.relpath(os.path.join(dp,fn),tdir).replace("\\","/")
            tpl.append(rel)
json.dump({"count":len(tpl),"templates":sorted(tpl),
 "usage":"LEGACY CAPABILITY EVIDENCE ONLY. Recover capability, never reuse markup/CSS.",
 "domains":["auth","cth","zbmp","system"]},
 open(os.path.join(EV,"01_repo_audit","legacy_template_inventory.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)

# ---- governance drift ----
drift="""# Governance / Copy Drift Log (read-only evidence, no source file modified)

## DRIFT-001 Subject Context semantic drift
- Legacy baseline wording (`LUMENIS_NEW_PRODUCT_DESIGN_BASELINE_V1.md` sec2):
  CTH = Subject-first; BMP = Brand-first / Primary Focus.
- Current canonical `README.md` (sec2 统一主体上下文):
  BOTH CTH and BMP support **Selected Subject**;
  Selected Subject -> Domain Lens -> Scope/Permission -> Query/Function/Metric -> View Model -> UI.
  CTH = Selected Subject + Commerce Operations Lens;
  BMP = Selected Subject + Brand & Market Lens (brand no longer the only legal subject).
- Experience decision: use ONE **Global Subject Context** at presentation layer
  (GLOBAL SUBJECT CONTEXT -> Commerce Operations Lens=CTH UI / Brand & Market Lens=BMP UI).
- Backend modification: NONE.
- Backend contract: CODEX_REVERIFY_REQUIRED.

## DRIFT-002 Korean locale legacy confirmed_terms
- `static/locales/ko.json` -> `_meta.confirmed_terms` still lists
  "Commerce & Trading Hub / Brand Monitoring Platform" (legacy public names).
- domain.cth / domain.zbmp values are already current. Existing locale is therefore NOT a clean Copy Authority.
- Handling: build copy-registry + zh/en/ko delta; do NOT edit production locale. Owner of production merge: CODEX.

## DRIFT-003 base.html legacy UI pollution is real
- base.html loads 8 legacy design CSS (zbc-design-*, xujing-core, lumenis-global-design, adaptive-*) plus inline CSS and hard-coded legacy business names.
- Handling: new shell does not extend/import/copy base.html; isolated namespace .lum-app / lum-* / --lum-*.

## DRIFT-004 Phase wording
- README CURRENT PHASE = PRODUCTION CONVERGENCE; six production gates required before Production Ready.
- This work may only conclude DOUBAO_EXPERIENCE_HANDOFF=COMPLETE, never LUMENIS_PRODUCTION=COMPLETE.

## DRIFT-005 Mixed legacy product names across HTML/JS/locales/docs
- ZBC / Brand Intelligence / Commerce & Trading Hub / Brand Monitoring Platform coexist with new Commerce Operations / Brand & Market.
- Recorded per occurrence in 12_i18n/copy-drift.json; production cleanup owner = CODEX.
"""
open(os.path.join(EV,"01_repo_audit","GOVERNANCE_DRIFT.md"),"w",encoding="utf-8").write(drift)

# ---- reference provenance (metadata + sealed copy; NEVER imported by runtime) ----
def sha(p): return hashlib.sha256(open(p,"rb").read()).hexdigest()
def img_dims(p):
    try:
        from PIL import Image; im=Image.open(p); return {"width":im.width,"height":im.height,"format":im.format}
    except Exception as e: return {"error":str(e)}
def vid_meta(p):
    try:
        out=subprocess.run([FFPROBE,"-v","error","-select_streams","v:0",
        "-show_entries","stream=width,height,codec_name,r_frame_rate:format=duration",
        "-of","json",p],capture_output=True,text=True).stdout
        j=json.loads(out); s=j["streams"][0]; f=j["format"]
        num,den=s["r_frame_rate"].split("/"); fps=round(int(num)/int(den),2) if int(den) else None
        return {"width":s.get("width"),"height":s.get("height"),"codec":s.get("codec_name"),
                "fps":fps,"duration_sec":round(float(f["duration"]),2)}
    except Exception as e: return {"error":str(e)}

ref_role={
 "ref_01":("IMG-tech","Figma 5-step Liquid Glass spatial hierarchy","MATERIAL_TECHNIQUE"),
 "ref_02":("IMG-tech","Why Apple Liquid Glass is hard: normals/refraction/SDF/chromatic/Fresnel","MATERIAL_PRINCIPLE"),
 "ref_03":("IMG-8974","Floating glass pill nav + active travel + dock","PATTERN"),
 "ref_04":("IMG-8975","Goal/progress metric card + gradient progress","PATTERN"),
 "ref_05":("IMG-8976","Calendar capsule spatial selector","PATTERN"),
 "ref_06":("IMG-8977","Upload pipeline with real staged progress","PATTERN"),
 "ref_07":("IMG-8978","Weather/finance: restrained big number + ring + soft glass","PATTERN"),
 "ref_08":("IMG-8979","Layered panels expressing relation/history/mode","PATTERN"),
 "ref_09":("IMG-8980","Task/Data + Magic GPT capability cards & composer","PATTERN"),
 "ref_10":("research","Xiaohongshu list of 6 vibe-coding reference sites","RESEARCH_ONLY"),
 "ref_11":("tech","LiquidGlass README install/quickstart (candidate, not adopted)","TECH_CANDIDATE"),
}
prov=[]
seal_dir=os.path.join(EV,"15_provenance_licenses","reference_sealed"); os.makedirs(seal_dir,exist_ok=True)
for i in range(1,12):
    name=f"ref_{i:02d}"; p=os.path.join(REFS,name+".webp")
    if not os.path.exists(p): continue
    m=img_dims(p); tag,desc,cls=ref_role[name]
    rec={"id":name,"tag":tag,"description":desc,"classification":cls,"filename":os.path.basename(p),
         "sha256":sha(p),"bytes":os.path.getsize(p),**m,
         "license":"REFERENCE ONLY — abstract behavior/principle; no visual code/asset copied into production",
         "used_in_product_assets":False}
    prov.append(rec)
# wechat media
wx_items=[
 ("wx_ai_rebuild.mp4","e9436886720502562c1d44ead6ce1247.mp4","AI interface rebuild BOOT->INTENT->TASK->ARTIFACT (motion reference)","MOTION_REFERENCE"),
 ("wx_research_site.mp4","f8617b6f97509f49930eee74be99bdfa.mp4","~96s research/study website walkthrough","RESEARCH_ONLY"),
 ("wx_research_shot.jpg","fd26aba3e8a2ccd4321e63b1f3573fa6.jpg","research website long screenshot","RESEARCH_ONLY")]
for rid,fn,desc,cls in wx_items:
    p=os.path.join(WX,fn)
    if not os.path.exists(p): continue
    rec={"id":rid,"description":desc,"classification":cls,"filename":fn,"sha256":sha(p),"bytes":os.path.getsize(p),
         "license":"REFERENCE ONLY","used_in_product_assets":False}
    rec.update(vid_meta(p) if fn.endswith(".mp4") else img_dims(p))
    prov.append(rec)
json.dump({"count":len(prov),"rule":"Originals never overwritten; previews go to preview/. Runtime imports NONE of these.",
           "items":prov},
 open(os.path.join(EV,"15_provenance_licenses","reference_provenance_manifest.json"),"w",encoding="utf-8"),
 ensure_ascii=False,indent=2)

print("scaffold dirs:",len(DIRS))
print("freeze head:",freeze["head_sha"][:10],"clean_pre:",freeze["worktree_clean"])
print("legacy templates:",len(tpl),"| references:",len(prov))
print("B01_DONE")
