# -*- coding: utf-8 -*-
"""
Aggregate generated per-screen JSON (single source) into:
 04_design_system  : design tokens + Pattern Registry
 05_components     : Component Registry (renderer -> component/state coverage)
 06_motion         : Motion Registry M01..M15 (canonical names, timing, reduced-motion)
 12_contracts      : six-Port registries + BINDING_MATRIX + UNKNOWN/BACKEND-GAP
 11_integration_skeleton : binding adapter stub + schema (Codex-facing)
 codex_handoff     : ten handoff registries (mirrors for one-place handoff)
No network/randomness. Re-runnable.
"""
import os, sys, json, glob
HERE = os.path.dirname(os.path.abspath(__file__)); EV = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "src"))
import screens_meta as SM
META = SM.META; IDS = SM.SCREEN_IDS
SR = os.path.join(EV, "07_screens")
DS, COMP, MOT, CONTRACTS, INTEG, HANDOFF = [os.path.join(EV, p) for p in
    ("04_design_system", "05_components", "06_motion", "12_contracts", "11_integration_skeleton", "codex_handoff")]
HANDOFF19 = os.path.join(EV, "19_handoff")
for d in (DS, COMP, MOT, CONTRACTS, INTEG, HANDOFF, HANDOFF19): os.makedirs(d, exist_ok=True)

def jw(p, o):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(o, ensure_ascii=False, indent=2) + "\n")

def load(sid, name):
    with open(os.path.join(SR, sid, name), encoding="utf-8") as f: return json.load(f)

specs = {sid: load(sid, f"{sid}.spec.json")["spec"] for sid in IDS}
vms   = {sid: load(sid, f"{sid}.viewmodel.json") for sid in IDS}
acts  = {sid: load(sid, f"{sid}.actions.json") for sid in IDS}

# ----------------------------------------------------------- Pattern Registry
PATTERNS = {
 "PAT-NAV-01": {"name":"Compact Rail Navigation","family":"navigation","renderer":"shell.rail","motion":["M02"],"used_by":[]},
 "PAT-NAV-02": {"name":"Bottom Dock + AI FAB","family":"navigation","renderer":"shell.dock","motion":["M05"],"used_by":[]},
 "PAT-DATA-01":{"name":"KPI Overview + Sparkline + Evidence source","family":"data","renderer":"R.kpis","motion":["M07"],"used_by":[]},
 "PAT-EVD-01": {"name":"Evidence Chain Panel","family":"evidence","renderer":"R.evidence","motion":["M08"],"used_by":[]},
 "PAT-AI-01":  {"name":"AI Composer Intent Home","family":"ai","renderer":"R.ai","motion":["M15","M05"],"used_by":[]},
 "PAT-AI-02":  {"name":"Artifact-first AI Thread + Stage Steps","family":"ai","renderer":"R.ai+R.steps","motion":["M06","M07"],"used_by":[]},
 "PAT-UPLOAD-01":{"name":"Upload Pipeline (stage progress, no fake %)","family":"input","renderer":"R.upload","motion":["M12"],"used_by":[]},
 "PAT-FILTER-01":{"name":"Filter Chips / Segmented","family":"input","renderer":"R.filters","motion":["M10"],"used_by":[]},
 "PAT-EMPTY-01":{"name":"13-state State Block","family":"state","renderer":"LumUI.stateBlock","motion":["M13","M14"],"used_by":[]},
}
for sid, sp in specs.items():
    for pat in sp.get("patterns", []):
        if pat in PATTERNS: PATTERNS[pat]["used_by"].append(sid)
jw(os.path.join(DS, "PATTERN_REGISTRY.json"), {"version":"V2","count":len(PATTERNS),"patterns":PATTERNS})

# ----------------------------------------------------------- Design tokens doc
TOKENS = {
 "version":"v2.4",
 "language":"序 · Editorial Lumen OS — serif editorial display over sans body; metal monochrome; the Lumen Axis",
 "color_authority":"LUMENIS-EXPERIENCE-DESIGN-AUTHORITY-V2.4 (black-silver / silver-white, no purple)",
 "light_black_on_silver":{"canvas":"#ECEDEF","ambient":"#E3E6EA/#DDE0E5","surface":"rgba(250,250,251,.86)","surface_raised":"#FFFFFF",
          "text_primary":"#16181D","text_secondary":"#545963","text_tertiary":"#888D96","border":"rgba(20,22,28,.10)",
          "brand_primary_metal":"#1B1D23","brand_gradient":"#3A3D45->#17191E->#05060A",
          "data_viz_only":"Icy #4FC4E8 (never chrome fill)","positive":"#1F9D6B","warning":"#B07416","critical":"#C0414D","info":"#3A63A8"},
 "dark_silver_on_black":{"canvas":"#07080A","ambient":"#10131A/#0E1016","surface":"rgba(18,19,23,.8)","surface_raised":"#1F2128",
         "text_primary":"#F1F2F4","text_secondary":"#AEB3BD","text_tertiary":"#7E848F","border":"rgba(255,255,255,.09)",
         "brand_primary_silver":"#E9EBEF","brand_gradient":"#FFFFFF->#D7DAE0->#A9AFB9","inverse_text_on_silver":"#0E0F12",
         "data_viz_only":"Icy #6FD6F2 (never chrome fill)","positive":"#43C68B","warning":"#F0B45B","critical":"#FF7A85","info":"#79A7FF"},
 "type":{"family_display":"Songti SC/STSong/Noto Serif SC/SimSun + Georgia/Times (serif) — page titles, section editorial heads, KPI numerals",
         "family_body":"system-ui/PingFang SC/Microsoft YaHei (sans) — all body & controls",
         "family_mono":"ui-monospace/Consolas — evidence id, trace, eyebrow index",
         "display_weight":600,"body_weights":"400/450/600","numerals":"tabular-nums lining-nums",
         "fluid_scale_clamp":"body near-constant; display 28/32 @360 -> 38/48 @1440"},
 "spacing":"4/8/12/16/20/24/32/40/48/64","editorial_section_gap":"clamp(22px,2vw+14px,44px)","control_height":"32/40/48",
 "radius":{"xs":3,"sm":6,"md":10,"lg":14,"xl":18,"pill":999},
 "signature":{"lumen_axis":"desktop margin vertical axis + rail continuous axis with hollow/filled metal nodes",
              "lumen_line":"brand->slate->icy hairline gradient (KPI top edge, steps, evidence, masthead rule)",
              "strata_grid":"faint 320px column / 88px baseline grid behind content","orb":"self-rendered canvas nebula sphere, in-sphere flow, state-colored, no star"},
 "material":{"outer_strata":"open, near-flat, hairline, shadowless .lum-card","inner_artifact":"solid .lum-card-solid with flat top light",
             "floating":"glass/sh-2/sh-3 only for drawer/modal/OPT optical tiers"},
 "optical_degradation":"HIGH -> STANDARD -> SOFT_GLASS -> OPAQUE (function 100% at every tier)",
 "ratio":"70% information clarity / 20% spatial texture / 10% motion delight",
 "source_css":"10_prototype/assets/tokens.css"}
jw(os.path.join(DS, "design-tokens.json"), TOKENS)

# ----------------------------------------------------------- Component registry
COMPONENTS = {
 "foundation":["AppShell","Rail","Topbar","ContextPanel","BottomDock","SubjectPill","DomainSwitch","Button","IconButton","Segmented","Tabs","Chips","Select/Input/Textarea","Badge","Pill","Toast","Modal","Drawer/BottomSheet","Skeleton","StateBlock"],
 "data":["KpiCard+Sparkline","DataTable","EvidenceChain","InsightPanel","EventList","RiskCard","Timeline","BarChart","LineChart","RingChart","Heatmap","CalendarCell","RuntimeStatus","UploadPipeline","StepsChain","FactualityWall"],
 "ai":["AIComposer","AIThreadBubble","AIStageSteps","AgentSkillCard","ProviderStatus","CapabilityTaskMorph"],
 "states_16":["Default","Hover","FocusVisible","Pressed","Selected","Loading","Disabled","Empty","Updating","Partial","Stale","Degraded","Blocked","Error","Offline","PermissionDenied"],
 "renderer_map":{
   "R.head":"section header (eyebrow/title/desc/actions)","R.kpis":"KpiCard row","R.evidence":"EvidenceChain",
   "R.insight":"InsightPanel","R.events":"EventList","R.risks":"RiskCard","R.timeline":"Timeline",
   "R.table":"DataTable","R.chart":"inline-SVG charts","R.filters":"Chips/Segmented","R.cards":"Card grid",
   "R.actions":"ActionPanel (4 classes)","R.upload":"UploadPipeline","R.runtime":"RuntimeStatus",
   "R.ai":"AI thread+stages","R.split":"main/side layout","R.stack":"vertical stack","R.tabs":"Tabs",
   "R.steps":"StepsChain","R.form":"Form","R.note":"Rule/Note callout","LumUI.stateBlock":"13 non-ready states"},
 "icon_set":"10_prototype/assets/icons.js (original inline stroke, 24x24, currentColor)",
 "naming":".lum-app / .lum-* / --lum-* (isolated; no global/legacy CSS)"}
jw(os.path.join(COMP, "COMPONENT_REGISTRY.json"), {"version":"V2","components":COMPONENTS})

# ----------------------------------------------------------- Motion registry
MOTION = {
 "M01":{"name":"App Shell Reveal","band":"Workspace 320-520ms","semantic_reason":"establish spatial hierarchy once on entry","reduced_motion":"instant opacity 1, no translate"},
 "M02":{"name":"Nav Active Travel","band":"Micro 80-180ms","semantic_reason":"show location continuity between destinations","reduced_motion":"active state color only"},
 "M03":{"name":"Context Change","band":"Layout 260-420ms","semantic_reason":"signal Subject/domain context switched, data ownership unchanged","reduced_motion":"crossfade only"},
 "M04":{"name":"Card -> Workspace Morph","band":"Special <=650ms","semantic_reason":"preserve object identity when expanding card to workspace","reduced_motion":"instant swap"},
 "M05":{"name":"Capability -> Task","band":"Component 180-280ms","semantic_reason":"map chosen capability to concrete task","reduced_motion":"state swap, no scale"},
 "M06":{"name":"Task Stage Progress","band":"Micro 80-180ms","semantic_reason":"show deterministic pipeline stage advance","reduced_motion":"step color fill only"},
 "M07":{"name":"Artifact Reveal","band":"Component 180-280ms","semantic_reason":"present generated artifact after real completion (never fake thinking)","reduced_motion":"instant show"},
 "M08":{"name":"Evidence Preview -> Rail","band":"Layout 260-420ms","semantic_reason":"anchor claim to its evidence without losing place","reduced_motion":"instant panel"},
 "M09":{"name":"Drawer / Bottom Sheet","band":"Component 180-280ms","semantic_reason":"secondary action without leaving page; bottom-sheet on mobile","reduced_motion":"instant, focus-trap kept"},
 "M10":{"name":"Segmented Travel","band":"Micro 80-180ms","semantic_reason":"indicate active segment","reduced_motion":"active fill only"},
 "M11":{"name":"Calendar Selection","band":"Micro 80-180ms","semantic_reason":"date selection continuity","reduced_motion":"selected bg only"},
 "M12":{"name":"Upload Pipeline","band":"Component 180-280ms","semantic_reason":"reflect real stage/byte progress; never animate fake percent","reduced_motion":"stage label only"},
 "M13":{"name":"Success Resolution","band":"Component 180-280ms","semantic_reason":"confirm completed action once","reduced_motion":"static success state"},
 "M14":{"name":"Error / Recovery","band":"Component 180-280ms","semantic_reason":"surface failure + recovery path, no decorative shake","reduced_motion":"static error state"},
 "M15":{"name":"Composer State","band":"Layout 260-420ms","semantic_reason":"AI 9-state transition BOOT..EVALUATION","reduced_motion":"state label swap"},
 "global_rules":["every motion carries semantic_reason","stagger <=5","prefers-reduced-motion fallback mandatory",
   "one primary motion per moment","gradient/aurora at most one per screen","WAAPI/Canvas/SVG original, zero third-party runtime"],
 "ai_nine_states":["BOOT","INTENT_HOME","COMPOSING","TASK_ACCEPTED","EXECUTING","ARTIFACT_READY","APPROVAL","ACTION","EVALUATION"],
 "source_js":"10_prototype/assets/motion.js"}
used_motion = sorted({m for sp in specs.values() for m in sp.get("motions", [])})
MOTION["used_in_specs"] = used_motion
jw(os.path.join(MOT, "MOTION_REGISTRY.json"), {"version":"V2","count":15,"motions":MOTION})

# ----------------------------------------------------------- Six-Port contracts
viewmodel_registry = {sid: {"domain": META[sid]["domain"], "title": META[sid]["zh"],
                            "viewmodel": vms[sid]["viewmodel"], "binding": vms[sid]["binding"],
                            "unknown_binding_keys": vms[sid]["unknown_binding_keys"]} for sid in IDS}
jw(os.path.join(CONTRACTS, "VIEWMODEL_REGISTRY.json"), {"status_enum":["VERIFIED_AVAILABLE","VERIFIED_UNAVAILABLE","PARTIAL","UNKNOWN","BLOCKED","CODEX_BINDING_REQUIRED"],
    "state_source_enum":["backend","frontend-derived","user-input","DESIGN_ONLY fixture"],"screens":viewmodel_registry})
action_registry = {"contract_fields":["action_id","display_key","capability_status","permission_requirement","input_context","success_state","failure_state","evidence_effect","binding_owner"],
                   "total": sum(acts[s]["count"] for s in IDS),
                   "by_class": {}, "screens": {sid: acts[sid]["actions"] for sid in IDS}}
for sid in IDS:
    for a in acts[sid]["actions"]: action_registry["by_class"][a["action_class"]] = action_registry["by_class"].get(a["action_class"],0)+1
jw(os.path.join(CONTRACTS, "ACTION_REGISTRY.json"), action_registry)
perms = sorted({a["permission_requirement"] for sid in IDS for a in acts[sid]["actions"]})
jw(os.path.join(CONTRACTS, "PERMISSION_REGISTRY.json"), {"note":"permission strings are prototype placeholders UNKNOWN until Codex maps to real RBAC; READ/TASK/AUDIT/WRITE/DEPLOY boundary must be enforced server-side","permissions":perms})
evid = {sid: vms[sid]["ports"]["Evidence"] for sid in IDS}
jw(os.path.join(CONTRACTS, "EVIDENCE_REGISTRY.json"), {"note":"all prototype evidence ids are DESIGN_ONLY; production claims must link Source->Evidence->Canonical","screens":evid})
capability = {sid: {"domain":META[sid]["domain"],"patterns":specs[sid].get("patterns",[]),"motions":specs[sid].get("motions",[]),
                    "capability_status":"PARTIAL","frontend":"READY_DESIGN_ONLY","backend":"CODEX_BINDING_REQUIRED"} for sid in IDS}
jw(os.path.join(CONTRACTS, "CAPABILITY_REGISTRY.json"), {"screens":capability})
jw(os.path.join(CONTRACTS, "STATE_REGISTRY.json"), {"non_ready_states":["loading","updating","partial","stale","degraded","empty_true","empty_notcollected","empty_filter","empty_permission","permission_denied","blocked","offline","error"],
    "ready":"rendered from ViewModel; every other state explicit, never silent fallback"})
# binding matrix (field-level) + unknown list / backend gaps
matrix, unknowns, gaps = [], [], []
for sid in IDS:
    for key, expr in vms[sid]["binding"].items():
        row={"screen":sid,"field":key,"current_source":expr,"frontend_viewmodel":"READY","owner":"CODEX","status":"CODEX_BINDING_REQUIRED"}
        matrix.append(row); unknowns.append(row)
        gaps.append({"gap_id":f"BACKEND-GAP-{len(gaps)+1:03d}","screen":sid,"field":key,
                     "current_api":"UNKNOWN","permission":"UNKNOWN","evidence":"UNKNOWN",
                     "frontend_viewmodel":"READY","owner":"CODEX","action":"map real endpoint/permission/evidence; do not invent API"})
jw(os.path.join(CONTRACTS, "BINDING_MATRIX.json"), {"rows":len(matrix),"matrix":matrix})
jw(os.path.join(CONTRACTS, "UNKNOWN_LIST.json"), {"rule":"UNKNOWN preserved, never guessed","count":len(unknowns),"items":unknowns})
jw(os.path.join(CONTRACTS, "BACKEND_GAP.json"), {"count":len(gaps),"gaps":gaps})

# ----------------------------------------------------------- integration skeleton
schema = {
 "$schema":"http://json-schema.org/draft-07#","title":"LUMENIS Screen ViewModel Binding Contract",
 "type":"object","required":["screen","state_source","sections"],
 "properties":{"screen":{"type":"string"},"state_source":{"enum":["backend","frontend-derived","user-input","DESIGN_ONLY fixture"]},
  "subject_context":{"type":"object","required":["subject_id","subject_type","domain","scope","permissions","time_window","locale","context_version"]},
  "sections":{"type":"object"},"actions":{"type":"object"},"evidence_refs":{"type":"array"}}}
jw(os.path.join(INTEG, "binding_contract.schema.json"), schema)
adapter = '''# -*- coding: utf-8 -*-
"""LUMENIS Experience V2 -> backend Binding Adapter (EXAMPLE / stub for Codex).
The experience layer is backend-agnostic. Replace DESIGN_ONLY fixtures by returning
the SAME view-model shape from real services. Never create a second truth store.
Contract: 12_contracts/VIEWMODEL_REGISTRY.json + binding_contract.schema.json.
"""
from __future__ import annotations
from typing import Any, Dict

# screen id -> callable that loads the production view-model (Codex implements)
_PROVIDERS: Dict[str, Any] = {}

def register_provider(screen_id: str, fn) -> None:
    """fn(subject_context) -> view-model dict matching <screen>.viewmodel.json"""
    _PROVIDERS[screen_id] = fn

def get_viewmodel(screen_id: str, subject_context: dict) -> dict:
    """Server-side: re-verify permission for subject_context BEFORE reading data.
    Missing values must be explicit null/'unknown' — never 0 or '未知' silent fill."""
    fn = _PROVIDERS.get(screen_id)
    if fn is None:
        return {"screen": screen_id, "state_source": "DESIGN_ONLY fixture",
                "note": "no production provider bound yet (CODEX_BINDING_REQUIRED)"}
    vm = fn(subject_context)
    vm["state_source"] = "backend"
    return vm

# Jinja-friendly: render the static shell, then hydrate sections from this VM.
# Static templates live in 10_prototype (HTML+Vanilla/ESM); no React/Vue required.
'''
with open(os.path.join(INTEG, "server_binding_adapter.example.py"), "w", encoding="utf-8", newline="\n") as f: f.write(adapter)
integ_md = """# Integration Skeleton — Codex binding guide

1. The experience layer (`10_prototype`) is static HTML + CSS + Vanilla ESM, Jinja-friendly. Do NOT introduce React/Vue for effect.
2. Each screen has, in `07_screens/<id>/`:
   - `<id>.viewmodel.json` — exact shape the UI renders (`viewmodel`) and where each field comes from today (`binding`).
   - `<id>.actions.json` — the 9-field Action Contract; EFFECT/QUERY actions are CODEX_BINDING_REQUIRED.
   - `<id>.fixture.json` — DESIGN_ONLY data to replace (never ship as production data).
3. Backend returns the SAME view-model shape (see `binding_contract.schema.json`); use `server_binding_adapter.example.py`.
4. SubjectContext eight fields travel with every request; server RE-VERIFIES authorization. Switching subject changes view context only, never data ownership.
5. State: backend supplies a state per section (ready/loading/partial/stale/…). The UI already renders all 13 non-ready states — do not fake 200.
6. Evidence: every factual claim links Source->Evidence->Canonical; unresolved facts stay UNKNOWN.
7. Isolation: all experience code stays under `experience_v2/**`; backend files are read-only to this layer.
"""
with open(os.path.join(INTEG, "INTEGRATION_GUIDE.md"), "w", encoding="utf-8", newline="\n") as f: f.write(integ_md)

# ----------------------------------------------------------- handoff mirrors
for name, obj in [("SCREEN_REGISTRY", {"screens":{sid:META[sid] for sid in IDS}}),
                  ("COMPONENT_REGISTRY", COMPONENTS),
                  ("MOTION_REGISTRY", MOTION),
                  ("PATTERN_REGISTRY", PATTERNS)]:
    jw(os.path.join(HANDOFF, name+".json"), obj if not isinstance(obj,tuple) else obj)
import shutil
for fn in ["VIEWMODEL_REGISTRY.json","ACTION_REGISTRY.json","PERMISSION_REGISTRY.json","EVIDENCE_REGISTRY.json",
           "CAPABILITY_REGISTRY.json","STATE_REGISTRY.json","BINDING_MATRIX.json","UNKNOWN_LIST.json","BACKEND_GAP.json"]:
    shutil.copyfile(os.path.join(CONTRACTS, fn), os.path.join(HANDOFF, fn))
copy_registry_src=os.path.join(EV,"12_i18n","copy-registry.json")
if os.path.exists(copy_registry_src): shutil.copyfile(copy_registry_src, os.path.join(HANDOFF,"COPY_REGISTRY.json"))

print("REGISTRIES OK")
print("patterns:", len(PATTERNS), "motion used:", used_motion)
print("binding rows:", len(matrix), "backend gaps:", len(gaps), "actions:", action_registry["total"], action_registry["by_class"])
