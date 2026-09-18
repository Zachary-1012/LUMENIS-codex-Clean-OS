#!/usr/bin/env python3
"""Block competing LUMENIS UI/UX/Experience design authorities."""
from __future__ import annotations
import fnmatch, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CANONICAL="00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md"
ROUTERS={"AGENTS.md","experience_v2/AGENTS.md","00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md"}
FORBIDDEN_PREFIXES=(
"00-GOVERNANCE/BRAND/LOGO-V1/","00-GOVERNANCE/handoff/FRONTEND_GPT_IMPORT_20260911/",
"audit/screenshots/ui_v1.1/","docs/reference/apple-ui-reference/","docs/reference/ui-research/",
"docs/learning/ui/","experience_v2/00_DELIVERY/","experience_v2/00_readme/",
"experience_v2/01_DOCUMENTS/","experience_v2/01_repo_audit/","experience_v2/02_REPO_AUDIT/",
"experience_v2/03_ia_and_flows/","experience_v2/04_VISUAL_BASELINES/","experience_v2/04_design_system/",
"experience_v2/06_motion/","experience_v2/08_psd/","experience_v2/09_QA/",
"experience_v2/09_responsive/","experience_v2/10_ORIGINALITY/","experience_v2/11_integration_skeleton/",
"experience_v2/13_research/","experience_v2/14_visual_regression/","experience_v2/15_provenance_licenses/",
"experience_v2/16_versioning/","experience_v2/17_acceptance/","experience_v2/18_validation/",
"experience_v2/19_handoff/","experience_v2/19_previews/","experience_v2/codex_handoff/","experience_v2/build/"
)
FORBIDDEN_EXACT={
"00-GOVERNANCE/AI-EXECUTION-CONSTITUTION-UI-RUNTIME-20260904.md",
"00-GOVERNANCE/LUMENIS-DOUBAO-CODEX-COMPLIANCE-HANDOFF-20260911.md",
"00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION-V3-20260918.md",
"00-GOVERNANCE/LUMENIS-EXPERIENCE-CURRENT-DIRECTION-READ-FIRST-20260911.md",
"00-GOVERNANCE/LUMENIS-EXPERIENCE-DESIGN-AUTHORITY-V2-20260911.md",
"00-GOVERNANCE/LUMENIS-EXPERIENCE-DESIGN-LANGUAGE-V2.4-20260911.md",
"00-GOVERNANCE/LUMENIS-EXPERIENCE-RESEARCH-LEARNING-ASSET-V1-20260911.md",
"00-GOVERNANCE/UNIFIED_UI_UX_INFORMATION_ARCHITECTURE_V1.md",
"00-GOVERNANCE/WEB-NO-SCROLL-INTEGRATED-UI-EXECUTION-CONTRACT-20260904.md",
"DESIGN_PHILOSOPHY_SEED_MUSTERY_TAIJI_V1.md","DOUBAO_FRONTEND_DELIVERY_EXECUTION_REQUIRED.md",
"LUMENIS_FRONTEND_IA_AUDIT_AND_REDESIGN_V1.md","LUMENIS_NEW_PRODUCT_DESIGN_BASELINE_V1.md",
"UIUX_AUDIT_REPORT.md","UIUX_FINAL_SYSTEM.md","UIUX_IMPLEMENTATION_PLAN.md","UI_DELETE_MANIFEST.md",
"contracts/kos/KOS_UI_INTERACTION_HIERARCHY_v1.md","docs/LUMENIS_SPATIAL_EXPERIENCE_RESEARCH_20260918-1549.md"
}
ALLOWED_EXPERIENCE_DOCS={"experience_v2/AGENTS.md"}
LEGACY_PHRASE="44 screens may ONLY compose registered patterns/components (no bespoke layout)"

def tracked():
    out=subprocess.check_output(["git","ls-files"],cwd=ROOT,text=True,encoding="utf-8")
    return [x.strip().replace("\\","/") for x in out.splitlines() if x.strip()]

def main():
    files=tracked(); fs=set(files); errors=[]
    if CANONICAL not in fs: errors.append("missing sole authority: "+CANONICAL)
    for p in files:
        if p in FORBIDDEN_EXACT: errors.append("legacy design artifact: "+p)
        if any(p.startswith(x) for x in FORBIDDEN_PREFIXES): errors.append("legacy design tree: "+p)
        if p.startswith("experience_v2/") and p.lower().endswith((".md",".docx",".pdf",".xlsx")) and p not in ALLOWED_EXPERIENCE_DOCS:
            errors.append("competing Experience document: "+p)
    gov=sorted(p for p in fs if p.startswith("00-GOVERNANCE/LUMENIS-EXPERIENCE-") and p.endswith(".md"))
    if gov != [CANONICAL]: errors.append("Experience governance not exclusive: "+", ".join(gov))
    for p in ROUTERS:
        if p not in fs: errors.append("missing router: "+p); continue
        txt=(ROOT/p).read_text(encoding="utf-8",errors="replace")
        if CANONICAL not in txt: errors.append("router not bound to sole authority: "+p)
    sec=ROOT/"experience_v2/10_prototype/assets/sections.js"
    if sec.exists() and LEGACY_PHRASE in sec.read_text(encoding="utf-8",errors="replace"):
        errors.append("legacy fixed-composer rule remains in sections.js")
    if errors:
        print("LUMENIS Experience authority exclusivity: FAIL")
        for e in sorted(set(errors)): print("- "+e)
        return 2
    print("LUMENIS Experience authority exclusivity: PASS")
    print("sole_authority="+CANONICAL)
    print("legacy_design_authorities=0")
    return 0

if __name__=="__main__": sys.exit(main())
