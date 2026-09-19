#!/usr/bin/env python3
"""Enforce one App-only LUMENIS Experience design authority in current main."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANONICAL = "00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md"

ROUTERS = {
    "AGENTS.md",
    "00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md",
}

# Historical design/reference trees that must never return to current main.
FORBIDDEN_PREFIXES = (
    "00-GOVERNANCE/BRAND/LOGO-V1/",
    "00-GOVERNANCE/handoff/FRONTEND_GPT_IMPORT_20260911/",
    "audit/screenshots/frontend/",
    "audit/screenshots/ui_v1.1/",
    "docs/reference/apple-ui-reference/",
    "docs/reference/ui-research/",
    "docs/learning/ui/",
    "handoff/frontend-gpt-v24-20260911-final/",
    "heritage_intelligence/07_product_ux_design/",
    "intelligence_library/08_UI-UX/",
    "tests/frames/",
    "experience_v2/00_DELIVERY/",
    "experience_v2/00_readme/",
    "experience_v2/01_DOCUMENTS/",
    "experience_v2/01_repo_audit/",
    "experience_v2/02_REPO_AUDIT/",
    "experience_v2/03_ia_and_flows/",
    "experience_v2/04_VISUAL_BASELINES/",
    "experience_v2/04_design_system/",
    "experience_v2/06_motion/",
    "experience_v2/08_FIXTURES/DESIGN_ONLY/",
    "experience_v2/08_psd/",
    "experience_v2/09_QA/",
    "experience_v2/09_responsive/",
    "experience_v2/10_ORIGINALITY/",
    "experience_v2/11_integration_skeleton/",
    "experience_v2/13_research/",
    "experience_v2/14_visual_regression/",
    "experience_v2/15_provenance_licenses/",
    "experience_v2/16_versioning/",
    "experience_v2/17_acceptance/",
    "experience_v2/18_validation/",
    "experience_v2/19_handoff/",
    "experience_v2/19_previews/",
    "experience_v2/codex_handoff/",
    "experience_v2/build/",
    "experience_v2/12_contracts/presentation-mapping/",
)

FORBIDDEN_EXACT = {
    "00-GOVERNANCE/AI-EXECUTION-CONSTITUTION-UI-RUNTIME-20260904.md",
    "00-GOVERNANCE/LUMENIS-DOUBAO-CODEX-COMPLIANCE-HANDOFF-20260911.md",
    "00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION-V3-20260918.md",
    "00-GOVERNANCE/LUMENIS-EXPERIENCE-CURRENT-DIRECTION-READ-FIRST-20260911.md",
    "00-GOVERNANCE/LUMENIS-EXPERIENCE-DESIGN-AUTHORITY-V2-20260911.md",
    "00-GOVERNANCE/LUMENIS-EXPERIENCE-DESIGN-LANGUAGE-V2.4-20260911.md",
    "00-GOVERNANCE/LUMENIS-EXPERIENCE-RESEARCH-LEARNING-ASSET-V1-20260911.md",
    "00-GOVERNANCE/UNIFIED_UI_UX_INFORMATION_ARCHITECTURE_V1.md",
    "00-GOVERNANCE/WEB-NO-SCROLL-INTEGRATED-UI-EXECUTION-CONTRACT-20260904.md",
    "00-GOVERNANCE/handoff/LUMENIS-CODEX-FINAL-ENTRYPOINT-AUDIT-20260911.md",
    "00-GOVERNANCE/handoff/LUMENIS_Doubao_PreProduction_Audit_to_Codex_Handoff.md",
    "00-GOVERNANCE/handoff/LUMENIS_P0-D_Codex_Closure_Handoff.md",
    "00-GOVERNANCE/ui_only_disposition_shardC.md",
    "00-GOVERNANCE/ui_page_audit_shardC.csv",
    "08-AUDIT/_frontend_files.txt",
    "DESIGN_PHILOSOPHY_SEED_MUSTERY_TAIJI_V1.md",
    "DOUBAO_FRONTEND_DELIVERY_EXECUTION_REQUIRED.md",
    "LUMENIS_FRONTEND_IA_AUDIT_AND_REDESIGN_V1.md",
    "LUMENIS_NEW_PRODUCT_DESIGN_BASELINE_V1.md",
    "UIUX_AUDIT_REPORT.md",
    "UIUX_FINAL_SYSTEM.md",
    "UIUX_IMPLEMENTATION_PLAN.md",
    "UI_DELETE_MANIFEST.md",
    "archive/deprecated/upgrade-history-v5/V5.2_UI_EVENT_DESIGN.md",
    "audit/ADAPTIVE_MOTION_EVIDENCE.md",
    "audit/ADAPTIVE_UI_INVENTORY.md",
    "audit/FRONTEND_PAGE_AUDIT.md",
    "audit/MOTION_SYSTEM_SPEC.md",
    "audit/UI_CLEANUP.md",
    "audit/UI_CLEANUP_files_deleted.txt",
    "audit/VISUAL_REFRESH_AND_APPLEID_ACCOUNT_REQUIREMENT_V1.0.md",
    "audit/ZBC_Design_System_V1.1.html",
    "audit/ZBC_LOCAL_AUDIT_REUSE_AND_UI_SEQUENCING_V1.0.md",
    "audit/ZBC_PAGE_LEVEL_DESIGN_V1.1.md",
    "audit/dual_domain_ui_audit.md",
    "audit/feature_governance/scan_ui.json",
    "audit/ui_audit.md",
    "contracts/kos/KOS_UI_INTERACTION_HIERARCHY_v1.md",
    "docs/DATA/DATA_PIPELINE_VISUALIZATION_EXECUTION_SPEC.md",
    "docs/DOUBAO_HANDOFF.md",
    "docs/LUMENIS_SPATIAL_EXPERIENCE_RESEARCH_20260918-1549.md",
    "docs/MASTER/B03-B04-PRE-VISUAL-MASTER-20260904.md",
    "docs/MASTER/FINAL-SYSTEM-PANORAMA-VISUAL-SPEC-20260904.md",
    "docs/MASTER/FINAL-VISUAL-SYSTEM-PRE-DESIGN-20260904.md",
    "docs/MASTER/P0-UI-SHELL-FIRST-CONSTRUCTION-BENCHMARK-20260904.md",
    "docs/MASTER/UI_DATA_PODCAST_BUILD_PLAN_V1.md",
    "docs/MASTER/UI_DATA_PODCAST_RESEARCH_SPEC_V2.md",
    "docs/UI-FINAL-CAPABILITY-MAP.md",
    "docs/UI-INTERACTION-SYSTEM-V1-20260903.md",
    "docs/UI_HANDOFF_MULTI_PLATFORM.md",
    "docs/UI_UX_ARCHITECTURE_EXECUTION_TASK.md",
    "docs/UI_UX_NON_REGRESSION_CONTRACT.md",
    "docs/ZHIPU_UI_DESIGN_INTEGRATION.md",
    "docs/design/LUMENIS-UI-STANDARD-v1.0.md",
    "docs/design/LUMENIS-UI-UX-MASTER-v1.0.md",
    "docs/design/ZBC_UI_UX_LANGUAGE_V2.md",
    "docs/governance/consolidation-002/UI-FEATURE-MAP.md",
    "docs/learning/P0C-UI-DESIGN-REVIEW-20260903.md",
    "docs/learning/UI-KEEPALIVE-RESEARCH-20260903.md",
    "podcast/UX_ARCHITECTURE_V1.md",
    "podcast/contracts/ui-architecture-v1.json",
    "序境/01-PRODUCT/UI_UX_DESIGN_BASELINE.md",
    "序境/01-PRODUCT/VISUALIZATION_REGISTRY_V1.md",
    "序境/08-AUDIT/CSS_CONVERGENCE_AUDIT_01.md",
    "序境/08-AUDIT/CSS_CONVERGENCE_AUDIT_02.md",
    "序境/08-AUDIT/DOUBAO_DELETE_REVIEW.md",
    "序境/08-AUDIT/UI_AUDIT_03_NAMING_ICON_EMOJI.md",
    "序境/08-AUDIT/UI_AUDIT_04_METRIC_INTEGRATION_LIGHTNING.md",
    "序境/08-AUDIT/UI_AUDIT_05_DATA_DRIVEN_MOTION.md",
    "序境/08-AUDIT/UI_KOS_AUDIT_06_DFS_TABLES.md",
    "序境/08-AUDIT/UI_VISUAL_AUDIT_01.md",
    "experience_v2/07_I18N/text-expansion/TEXT_EXPANSION.md",
    "experience_v2/08_FIXTURES/DESIGN_ONLY/README.md",
}

FORBIDDEN_EXACT.update(
    {f"序境/08-AUDIT/P1_UI_CONVERGENCE_EVIDENCE_{i:02d}.md" for i in range(2, 14)}
)

# Historical copies inside the intelligence library.
FORBIDDEN_EXACT.update({
    "intelligence_library/02_ZBMP研究/播客研究/podcast-module/UI_REFERENCE_XIAOYUZHOU_V1.md",
    "intelligence_library/02_ZBMP研究/品牌营销知识/brand-marketing-knowledge-23-global-regions-overseas-ui-20260903.md",
    "intelligence_library/09_Research-Hub/AI操作系统研究/05-experience-engine.md",
    "intelligence_library/09_Research-Hub/docs/MASTER/UI_DATA_PODCAST_BUILD_PLAN_V1.md",
    "intelligence_library/09_Research-Hub/docs/MASTER/UI_DATA_PODCAST_RESEARCH_SPEC_V2.md",
    "intelligence_library/09_Research-Hub/docs/product/OSAI_MOBILE_APP_UI_SPEC_V1.md",
    "intelligence_library/09_Research-Hub/learning-feed/pattern-data-driven-motion-20260903.md",
    "intelligence_library/10_工程审计方法/ZBC审计/VISUAL_REFRESH_AND_APPLEID_ACCOUNT_REQUIREMENT_V1.0.md",
    "intelligence_library/10_工程审计方法/ZBC审计/dual_domain_ui_audit.md",
    "intelligence_library/10_工程审计方法/ZBC审计/ui_audit.md",
    "intelligence_library/10_工程审计方法/合约/kos/KOS_UI_INTERACTION_HIERARCHY_v1.md",
    "intelligence_library/10_工程审计方法/对账/09_UI_UX_RECONCILIATION.md",
    "intelligence_library/10_工程审计方法/治理架构/00-GOVERNANCE/AI-EXECUTION-CONSTITUTION-UI-RUNTIME-20260904.md",
    "intelligence_library/10_工程审计方法/治理架构/00-GOVERNANCE/UNIFIED_UI_UX_INFORMATION_ARCHITECTURE_V1.md",
    "intelligence_library/10_工程审计方法/治理架构/00-GOVERNANCE/WEB-NO-SCROLL-INTEGRATED-UI-EXECUTION-CONTRACT-20260904.md",
    "intelligence_library/10_工程审计方法/治理架构/00-GOVERNANCE/ui_only_disposition_shardC.md",
    "intelligence_library/10_工程审计方法/治理架构/00-GOVERNANCE/ui_page_audit_shardC.csv",
    "intelligence_library/10_工程审计方法/治理架构/contracts/kos/KOS_UI_INTERACTION_HIERARCHY_v1.md",
})

LEGACY_COMPOSER_PHRASE = (
    "44 screens may ONLY compose registered patterns/components (no bespoke layout)"
)

# Future-proof catch: a renamed design bible must not bypass the historical blacklist.
# This intentionally targets presentation-authority style document names, not generic
# business/architecture documents that happen to contain the word "design".
SUSPICIOUS_DOC_RE = re.compile(
    r"(?:^|/)[^/]*(?:"
    r"UI[_-]?UX|UIUX|"
    r"UX[_-](?:ARCHITECTURE|DESIGN|SYSTEM)|"
    r"UI[_-](?:DESIGN|STANDARD|SYSTEM|ARCHITECTURE|INTERACTION|VISUAL)|"
    r"DESIGN[_-](?:SYSTEM|LANGUAGE|BASELINE|AUTHORITY)|"
    r"EXPERIENCE[_-](?:DESIGN|LANGUAGE|AUTHORITY)|"
    r"VISUAL[_-](?:SYSTEM|SPEC|BASELINE|DESIGN|AUDIT)|"
    r"MOTION[_-](?:SYSTEM|SPEC|GUIDE|GUIDELINE|TOKENS)|"
    r"FRONTEND[_-](?:DESIGN|REDESIGN|HANDOFF)|"
    r"PAGE[_-]LEVEL[_-]DESIGN|"
    r"LOGO[_-](?:DESIGN|SPEC|MOTION|STATIC)"
    r")[^/]*\.(?:md|docx|pdf|xlsx|html|txt)$",
    re.IGNORECASE,
)


def tracked() -> list[str]:
    out = subprocess.check_output(
        ["git", "ls-files"], cwd=ROOT, text=True, encoding="utf-8"
    )
    return [p.strip().replace("\\", "/") for p in out.splitlines() if p.strip()]


def main() -> int:
    files = tracked()
    file_set = set(files)
    errors: list[str] = []

    if CANONICAL not in file_set:
        errors.append(f"missing sole Experience authority: {CANONICAL}")

    # Exactly one governance Experience document may exist.
    governance_experience = sorted(
        p for p in file_set
        if p.startswith("00-GOVERNANCE/LUMENIS-EXPERIENCE-")
        and p.endswith(".md")
    )
    if governance_experience != [CANONICAL]:
        errors.append(
            "Experience governance authority is not exclusive: "
            + ", ".join(governance_experience)
        )

    for p in files:
        if p in FORBIDDEN_EXACT:
            errors.append(f"legacy design artifact present: {p}")
        if any(p.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
            errors.append(f"legacy design tree present: {p}")

        if p != CANONICAL and SUSPICIOUS_DOC_RE.search(p):
            errors.append(f"competing design-authority-like document present: {p}")

        # Under experience_v2, human-authored docs are not allowed except AGENTS router.
        if (
            p.startswith("experience_v2/")
            and p.lower().endswith((".md", ".docx", ".pdf", ".xlsx"))
            and p != "experience_v2/AGENTS.md"
        ):
            errors.append(f"competing Experience document present: {p}")

    for router in ROUTERS:
        if router not in file_set:
            errors.append(f"required execution router missing: {router}")
            continue
        text = (ROOT / router).read_text(encoding="utf-8", errors="replace")
        if CANONICAL not in text:
            errors.append(f"router not bound to sole Experience authority: {router}")

    if errors:
        print("LUMENIS Experience authority exclusivity: FAIL")
        for error in sorted(set(errors)):
            print(f"- {error}")
        return 2

    print("LUMENIS Experience authority exclusivity: PASS")
    print(f"sole_authority={CANONICAL}")
    print("canonical_experience_surface=app/")
    print("legacy_design_authorities=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())