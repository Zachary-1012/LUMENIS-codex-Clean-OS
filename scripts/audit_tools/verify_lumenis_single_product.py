"""Blocking guard for LUMENIS Only-One / App-first convergence."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCH = ROOT / "00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md"
EXPERIENCE = ROOT / "00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md"

FORBIDDEN_PREFIXES = (
    "research/ui-ux/",
    "ref_gpt_v2/",
    "audit/screenshots/",
    "intelligence_library/10_工程审计方法/治理架构/00-GOVERNANCE/_path_backup/",
    "collector_v2/",
    "collector_guard/",
    "platform_adapters/",
    "browser_runtime/",
)

FORBIDDEN_EXACT = {
    "08-AUDIT/SCREENSHOT-ARCHITECTURE-INTAKE-20260917.md",
    "audit/take_screenshot.ps1",
    "static/css/zbc-design-system.css",
    "ai_channel.py",
    "provider_registry.py",
    "skill_registry.py",
    "skill_execution_chain.py",
    "skill_package_runtime.py",
    "brand_report_generator.py",
    "report_artifact.py",
    "report_filter.py",
    "report_engine.py",
    "daily_report.py",
    "export_report.py",
    "report_export/report_engine.py",
    "report_api.py",
    "kos_report.py",
    "evidence_chain.py",
    "evidence_store.py",
    "evidence_api.py",
    "production_evidence_contract.py",
    "app_evidence.py",
    "lumenis/shared/reporting/export_engine.py",
    "research/podcast/UX_ARCHITECTURE_V1.md",
    "research/research-hub/docs/MASTER/UI_DATA_PODCAST_BUILD_PLAN_V1.md",
    "research/research-hub/docs/MASTER/UI_DATA_PODCAST_RESEARCH_SPEC_V2.md",
    "research/research-hub/docs/product/OSAI_MOBILE_APP_UI_SPEC_V1.md",
    "research/research-hub/learning-feed/pattern-data-driven-motion-20260903.md",
}

REQUIRED_ARCH_MARKERS = (
    "Only One / All-in",
    "Subject-first",
    "Brand-first / Primary Focus",
    "Shared Capability Layer",
    "Agent Groups",
    "SYSTEM",
    "App-only product direction",
    "Flutter",
    "Windows",
    "macOS",
    "Linux",
    "Android",
    "iOS",
    "original baseline capability regressions = 0",
    "later capability regressions = 0",
)

def tracked() -> list[str]:
    out = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True)
    return [line.strip().replace("\\", "/") for line in out.splitlines() if line.strip()]

def main() -> int:
    errors: list[str] = []
    if not ARCH.is_file():
        errors.append(f"missing product architecture authority: {ARCH.relative_to(ROOT)}")
    else:
        text = ARCH.read_text(encoding="utf-8")
        for marker in REQUIRED_ARCH_MARKERS:
            if marker not in text:
                errors.append(f"architecture marker missing: {marker}")
    if not EXPERIENCE.is_file():
        errors.append("missing sole Experience authority")

    required_app_files = (
        "app/pubspec.yaml",
        "app/lib/main.dart",
        "app/lib/core/lumenis_core_client.dart",
        "app/lib/product/product_domain.dart",
        "app/lib/product/lumenis_app.dart",
        "app/lib/features/launch/launch_surface.dart",
    )
    for path in required_app_files:
        if not (ROOT / path).is_file():
            errors.append(f"missing canonical app foundation: {path}")

    tracked_paths = tracked()
    for path in tracked_paths:
        if any(path.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
            errors.append(f"legacy UI/UX/reference artifact present: {path}")
        if path in FORBIDDEN_EXACT:
            errors.append(f"legacy UI/UX/reference artifact present: {path}")
        if ".pre-opt" in path:
            errors.append(f"pre-opt backup artifact present: {path}")

    # Shared Reporting must remain the sole implementation owner.
    app_text = (ROOT / "app.py").read_text(encoding="utf-8")
    forbidden_app_reporting = (
        "def export_report_to_csv(",
        "def _classify_category(",
        "def _calc_alert_level(",
        "def _generate_core_conclusion(",
        "INSERT OR REPLACE INTO weekly_reports",
        "INSERT OR REPLACE INTO daily_reports",
    )
    for marker in forbidden_app_reporting:
        if marker in app_text:
            errors.append(f"app.py reintroduced Reporting implementation: {marker}")

    evidence_store_path = ROOT / "lumenis/shared/evidence/store.py"
    if evidence_store_path.is_file():
        evidence_store_text = evidence_store_path.read_text(encoding="utf-8")
        if "Path(__file__).parent / \"data\" / \"monitor.db\"" in evidence_store_text:
            errors.append("Shared Evidence Store points at module-local DB instead of production DB truth")

    routes_path = ROOT / "lumenis/shared/reporting/routes.py"
    if routes_path.is_file():
        routes_text = routes_path.read_text(encoding="utf-8")
        if "from app import" in routes_text or "import app" in routes_text:
            errors.append("Shared Reporting routes must not depend on app.py implementation")

    grep = subprocess.run(
        ["git", "grep", "-n", "-E", r"lumenis\.report_center|from brand_report_generator|import brand_report_generator|^from daily_report|^import daily_report|^from report_artifact|^import report_artifact|^from report_filter|^import report_filter|^from report_export|^import export_report|^from report_api|^import report_api|^from kos_report|^import kos_report|^from evidence_chain|^import evidence_chain|^from evidence_store|^import evidence_store|^from evidence_api|^import evidence_api|^from production_evidence_contract|^import production_evidence_contract|^from app_evidence|^import app_evidence|from collector_guard|import collector_guard|from collector_v2|import collector_v2|from platform_adapters|import platform_adapters|from browser_runtime|import browser_runtime|from provider_registry|import provider_registry|^import ai_channel|from ai_channel|from skill_registry|import skill_registry|from skill_execution_chain|import skill_execution_chain|from skill_package_runtime|import skill_package_runtime"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if grep.returncode == 0 and grep.stdout.strip():
        errors.append("legacy reporting import present:\n" + grep.stdout.strip())

    if errors:
        print("LUMENIS Only-One/App-first architecture guard: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("LUMENIS Only-One/App-first architecture guard: PASS")
    print("product_architecture=00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md")
    print("experience_authority=00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md")
    print("legacy_ui_reference_paths=0")
    return 0

if __name__ == "__main__":
    sys.exit(main())