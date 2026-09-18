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
)

FORBIDDEN_EXACT = {
    "08-AUDIT/SCREENSHOT-ARCHITECTURE-INTAKE-20260917.md",
    "audit/take_screenshot.ps1",
    "static/css/zbc-design-system.css",
    "brand_report_generator.py",
    "report_artifact.py",
    "report_filter.py",
    "report_engine.py",
    "daily_report.py",
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

    grep = subprocess.run(
        ["git", "grep", "-n", "-E", r"lumenis\.report_center|from brand_report_generator|import brand_report_generator|from collector_guard|import collector_guard|from collector_v2|import collector_v2"],
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
