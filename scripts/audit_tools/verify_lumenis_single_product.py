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
    "evaluation_system.py",
    "evaluation_runner.py",
    "evaluation_recorder.py",
    "evaluation_dimensions.py",
    "ai_evaluation.py",
    "agent_runtime/evaluation.py",
    "evaluation/collection_benchmark.py",
    "evaluation/agent_benchmark_contract.py",
    "evaluation/benchmark_cases.json",
    "ai_learning_engine.py",
    "learning_collector.py",
    "learning_persistence.py",
    "data_feedback_loop.py",
    "agent_memory/learning.py",
    "agent_memory/learning_loop.py",
    "permission_gate.py",
    "p2_action_firewall.py",
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

    evaluation_recorder_path = ROOT / "lumenis/shared/evaluation/recorder.py"
    if evaluation_recorder_path.is_file():
        evaluation_recorder_text = evaluation_recorder_path.read_text(encoding="utf-8")
        if 'os.path.dirname(os.path.abspath(__file__))' in evaluation_recorder_text:
            errors.append("Shared Evaluation recorder must not derive Production DB from module-local directory")
        if 'Path(__file__).resolve().parents[3]' not in evaluation_recorder_text:
            errors.append("Shared Evaluation recorder must anchor repository Production Truth")

    learning_owner = ROOT / "lumenis/shared/learning"
    required_learning_files = (
        "memory.py", "loop.py", "collector.py", "feedback.py", "persistence.py",
        "operations.py",
    )
    for filename in required_learning_files:
        if not (learning_owner / filename).is_file():
            errors.append(f"missing Shared Learning owner: lumenis/shared/learning/{filename}")

    for filename in ("collector.py", "feedback.py", "persistence.py", "operations.py"):
        path = learning_owner / filename
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            if "Path(__file__).resolve().parents[3]" not in text:
                errors.append(f"Shared Learning {filename} must anchor repository root explicitly")

    if learning_owner.is_dir():
        for path in learning_owner.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "INSERT INTO web_events" in text or "UPDATE web_events" in text:
                errors.append(
                    f"Shared Learning must not write AI-generated learning directly into canonical web_events: {path.name}"
                )

    operations_path = learning_owner / "operations.py"
    if operations_path.is_file():
        operations_text = operations_path.read_text(encoding="utf-8")
        if "INSERT INTO web_events" in operations_text or "UPDATE web_events" in operations_text:
            errors.append("Shared Learning operations must never write generated data into canonical web_events")
        if "ark_llm" in operations_text:
            errors.append("Shared Learning operations must not restore retired ungrounded ark_llm web search")

    security_owner = ROOT / "lumenis/system/security"
    for filename in ("__init__.py", "permission.py", "action_firewall.py", "effect_fence.py"):
        if not (security_owner / filename).is_file():
            errors.append(f"missing SYSTEM Security owner: lumenis/system/security/{filename}")

    skill_execution_path = ROOT / "lumenis/shared/agents/skills/execution.py"
    if skill_execution_path.is_file():
        skill_text = skill_execution_path.read_text(encoding="utf-8")
        if "_ACTION_POLICY =" in skill_text:
            errors.append("Skill runtime reintroduced a parallel Action Firewall policy")
        if "from p2_action_firewall" in skill_text or "import p2_action_firewall" in skill_text:
            errors.append("Skill runtime depends on retired p2_action_firewall owner")
        if "from evidence_chain" in skill_text or "import evidence_chain" in skill_text:
            errors.append("Skill runtime depends on retired root Evidence owner")
        if "lumenis.system.security" not in skill_text:
            errors.append("Skill runtime is not bound to canonical SYSTEM Security")

    security_boundary_path = ROOT / "security_boundary.py"
    if security_boundary_path.is_file():
        security_boundary_text = security_boundary_path.read_text(encoding="utf-8")
        if "_action_firewall_rules" in security_boundary_text:
            errors.append("SecurityBoundary reintroduced a parallel Action Firewall rule owner")
        if "from lumenis.system.security import" not in security_boundary_text:
            errors.append("SecurityBoundary is not bound to canonical SYSTEM Security")

    ad_permission_path = ROOT / "ad_intelligence/permission_gate.py"
    if ad_permission_path.is_file():
        ad_permission_text = ad_permission_path.read_text(encoding="utf-8")
        if "from lumenis.system.security import" not in ad_permission_text:
            errors.append("Ad permission adapter is not bound to canonical SYSTEM Permission")
        if "_human_approved" in ad_permission_text or "_approval_expiry" in ad_permission_text:
            errors.append("Ad permission adapter owns parallel human-approval state")

    security_owner = ROOT / "lumenis/system/security"
    for filename in ("permission.py", "action_firewall.py", "effect_fence.py", "__init__.py"):
        if not (security_owner / filename).is_file():
            errors.append(f"missing canonical SYSTEM security owner: lumenis/system/security/{filename}")

    agent_loop_path = ROOT / "agent_runtime/loop.py"
    if agent_loop_path.is_file():
        agent_loop_text = agent_loop_path.read_text(encoding="utf-8")
        for retired in ("from permission_gate", "import permission_gate", "skill_execution_chain"):
            if retired in agent_loop_text:
                errors.append(f"Agent Runtime bypasses canonical SYSTEM security owner: {retired}")

    routes_path = ROOT / "lumenis/shared/reporting/routes.py"
    if routes_path.is_file():
        routes_text = routes_path.read_text(encoding="utf-8")
        if "from app import" in routes_text or "import app" in routes_text:
            errors.append("Shared Reporting routes must not depend on app.py implementation")

    grep = subprocess.run(
        ["git", "grep", "-n", "-E", r"lumenis\.report_center|from brand_report_generator|import brand_report_generator|^[[:space:]]*from daily_report|^[[:space:]]*import daily_report|^[[:space:]]*from report_artifact|^[[:space:]]*import report_artifact|^[[:space:]]*from report_filter|^[[:space:]]*import report_filter|^[[:space:]]*from report_export|^[[:space:]]*import export_report|^[[:space:]]*from report_api|^[[:space:]]*import report_api|^[[:space:]]*from kos_report|^[[:space:]]*import kos_report|^[[:space:]]*from evidence_chain|^[[:space:]]*import evidence_chain|^[[:space:]]*from evidence_store|^[[:space:]]*import evidence_store|^[[:space:]]*from evidence_api|^[[:space:]]*import evidence_api|^[[:space:]]*from production_evidence_contract|^[[:space:]]*import production_evidence_contract|^[[:space:]]*from app_evidence|^[[:space:]]*import app_evidence|from collector_guard|import collector_guard|from collector_v2|import collector_v2|from platform_adapters|import platform_adapters|from browser_runtime|import browser_runtime|from provider_registry|import provider_registry|^[[:space:]]*import ai_channel|from ai_channel|from skill_registry|import skill_registry|from skill_execution_chain|import skill_execution_chain|from skill_package_runtime|import skill_package_runtime|^[[:space:]]*from evaluation_recorder|^[[:space:]]*import evaluation_recorder|^[[:space:]]*from evaluation_dimensions|^[[:space:]]*import evaluation_dimensions|^[[:space:]]*from evaluation_runner|^[[:space:]]*import evaluation_runner|^[[:space:]]*from evaluation_system|^[[:space:]]*import evaluation_system|^[[:space:]]*from ai_evaluation|^[[:space:]]*import ai_evaluation|from agent_runtime\\.evaluation|from evaluation\\.agent_benchmark_contract|from evaluation\\.collection_benchmark|^[[:space:]]*from learning_collector|^[[:space:]]*import learning_collector|^[[:space:]]*from learning_persistence|^[[:space:]]*import learning_persistence|^[[:space:]]*from data_feedback_loop|^[[:space:]]*import data_feedback_loop|^[[:space:]]*from ai_learning_engine|^[[:space:]]*import ai_learning_engine|^[[:space:]]*from agent_memory\\.learning|^[[:space:]]*from agent_memory\\.learning_loop|^[[:space:]]*from permission_gate|^[[:space:]]*import permission_gate|^[[:space:]]*from p2_action_firewall|^[[:space:]]*import p2_action_firewall"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if grep.returncode == 0 and grep.stdout.strip():
        errors.append("retired owner import present:\n" + grep.stdout.strip())

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