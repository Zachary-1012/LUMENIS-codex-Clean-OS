"""Blocking guard for LUMENIS Only-One / multi-surface convergence."""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import re
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from .experience_gate_mode import frontend_state
except ImportError:
    from experience_gate_mode import frontend_state

ROOT = Path(__file__).resolve().parents[2]
ARCH = ROOT / "00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md"
EXPERIENCE = ROOT / "00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md"
SURFACE_DECISION = ROOT / "00-GOVERNANCE/LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md"
SECURITY_BOUNDARY = ROOT / "00-GOVERNANCE/SECURITY-BOUNDARY-CURRENT.md"
PRODUCT_POSITIONING = ROOT / "00-GOVERNANCE/PRODUCT-POSITIONING-CURRENT.md"
README = ROOT / "README.md"
CROSS_REPO_REGISTRY = ROOT / "00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md"

PRODUCT_POSITIONING_MARKERS = (
    "CTH · 商业运营",
    "BMP · 品牌市场",
    "Shared Capability",
    "SYSTEM",
    "Subject-first",
    "Brand/Market-first",
)
ECOSYSTEM_REPOSITORY_MARKERS = (
    "Zachary-1012/Zachary-OS-AI",
    "Zachary-1012/global-growth-intelligence",
    "Zachary-1012/lumenis-command",
)
LEGACY_PATH_TOKEN = re.compile(
    r"(?i)(?:^|[^a-z0-9])(?:zbc|zbmp|zachary|osai|dcc|sici|zbip|adrh|legacy|frontend|z-brand-core|experience_v2)(?=$|[^a-z0-9])"
)

RETIRED_IMPORT_MODULES = (
    "lumenis.report_center", "brand_report_generator", "daily_report",
    "report_engine",
    "report_artifact", "report_filter", "report_export", "export_report",
    "report_api", "kos_report", "evidence_chain", "evidence_store",
    "evidence_api", "production_evidence_contract", "app_evidence",
    "collector_guard", "collector_v2", "platform_adapters", "browser_runtime",
    "provider_registry", "ai_channel", "skill_registry", "skill_execution_chain",
    "skill_package_runtime", "evaluation_recorder", "evaluation_dimensions",
    "evaluation_runner", "evaluation_system", "ai_evaluation",
    "agent_runtime.evaluation", "evaluation.agent_benchmark_contract",
    "evaluation.collection_benchmark", "learning_collector", "learning_persistence",
    "data_feedback_loop", "ai_learning_engine", "agent_memory.learning",
    "agent_memory.learning_loop", "permission_gate", "p2_action_firewall",
    "web_monitor_v570",
)

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
    "Multi-surface product direction",
    "Public Website",
    "Web Workspace",
    "Desktop App",
    "Mobile Companion",
    "lumenis/system/ai_gateway/ remains the sole SYSTEM owner",
    "commercially usable open foundation weights",
    "Jev is an inactive historical typed candidate",
    "no calls, probes, auto-discovery",
    "fallback or reactivation",
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
    out = subprocess.check_output(
        ["git", "-c", "core.quotePath=false", "ls-files"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    )
    return [line.strip().replace("\\", "/") for line in out.splitlines() if line.strip()]


def production_python_files(root: Path) -> list[Path]:
    """Audit source without entering local trees or Flutter's generated output."""
    ignored_dirs = {".git", "__pycache__", "node_modules", "tests", "test", "docs"}
    local_roots = {"work", ".venv", "venv", "vendor"}
    result = []
    for directory, dirs, files in os.walk(root, onerror=_scan_error):
        current = Path(directory)
        dirs[:] = [name for name in dirs if name.lower() not in ignored_dirs
                   and not (current == root and name in local_roots)
                   and current / name != root / "app" / "build"]
        result.extend(current / name for name in files if name.endswith(".py")
                      and not name.lower().startswith(("test_", "audit_")))
    return sorted(result)


def _scan_error(error: OSError) -> None:
    raise error

def tracked_path_errors(tracked_paths: list[str]) -> list[str]:
    """Historical provenance is not a live product path or execution authority."""
    try:
        from . import verify_codex_takeover_governance as recovery
    except ImportError:
        import verify_codex_takeover_governance as recovery
    errors: list[str] = []
    recovered_paths: set[str] = set()
    if recovery.RECOVERED_EVIDENCE_RECEIPT in tracked_paths:
        try:
            inventory = recovery._recovered_evidence_inventory()
            assert set(inventory).issubset(tracked_paths), "recovery inventory contains untracked files"
            recovery._assert_recovered_evidence_integrity()
            recovered_paths = set(inventory)
        except (AssertionError, OSError, ValueError, TypeError) as exc:
            errors.append(f"invalid recovered evidence inventory: {exc}")
    for path in tracked_paths:
        normalized = path.replace("\\", "/")
        if normalized.casefold().startswith("app/build/") and normalized.casefold().endswith(".py"):
            errors.append(f"tracked Python source in generated app/build output: {path}")
        if normalized.casefold().startswith("08-audit/"):
            errors.append(f"obsolete audit archive path present: {path}")
        if LEGACY_PATH_TOKEN.search(normalized) and path not in recovered_paths:
            errors.append(f"obsolete product/archive path token present: {path}")
        if any(path.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
            errors.append(f"legacy UI/UX/reference artifact present: {path}")
        if path in FORBIDDEN_EXACT:
            errors.append(f"legacy UI/UX/reference artifact present: {path}")
        if ".pre-opt" in path:
            errors.append(f"pre-opt backup artifact present: {path}")

    return errors


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
    if not SURFACE_DECISION.is_file():
        errors.append("missing approved multi-surface decision")
    else:
        decision_text = SURFACE_DECISION.read_text(encoding="utf-8")
        for marker in (
            "PRODUCT OWNER APPROVED / ARCHITECTURE DECISION",
            "ONE Product Core",
            "Public Website",
            "Web Workspace",
            "Desktop App",
            "Mobile Companion",
            "Jev product decision",
            "ROUND 07",
        ):
            if marker not in decision_text:
                errors.append(f"multi-surface decision marker missing: {marker}")
    if not SECURITY_BOUNDARY.is_file():
        errors.append("missing current layered security boundary")
    if not PRODUCT_POSITIONING.is_file():
        errors.append("missing current product positioning and ownership contract")
    else:
        positioning_text = PRODUCT_POSITIONING.read_text(encoding="utf-8")
        for marker in (
            "CTH",
            "BMP",
            "Shared Capability",
            "SYSTEM",
            "Public Website",
            "Web Workspace",
            "Desktop App",
            "Mobile Companion",
            "ONE Product Core",
            "ONE Canonical API / ViewModel contract",
            "DESIGN_EXPLORATION",
            "DESIGN_READY",
            "Windows",
            "macOS",
            "Linux",
            "Android",
            "iOS",
        ):
            if marker not in positioning_text:
                errors.append(f"current product positioning marker missing: {marker}")
        for stale in (
            "Website/Web优先及原生Windows/macOS/iOS顺序不变",
            "Public Website and Web Workspace close first.",
            "Later native application targets",
            "Exact seven-domain coverage",
        ):
            if stale in positioning_text:
                errors.append(f"obsolete positioning rule: {stale}")
        for current in ("built in parallel", "accepted independently", "Independently usable"):
            if current not in positioning_text:
                errors.append(f"positioning omits current surface/Shared boundary: {current}")
    if not README.is_file():
        errors.append("missing product definition and engineering entry point")
    else:
        readme_text = README.read_text(encoding="utf-8")
        for marker in PRODUCT_POSITIONING_MARKERS:
            if marker not in readme_text:
                errors.append(f"product positioning marker missing: {marker}")
    if not CROSS_REPO_REGISTRY.is_file():
        errors.append("missing cross-repository ecosystem boundary")
    else:
        registry_text = CROSS_REPO_REGISTRY.read_text(encoding="utf-8")
        for marker in ECOSYSTEM_REPOSITORY_MARKERS:
            if marker not in registry_text:
                errors.append(f"ecosystem repository marker missing: {marker}")

    required_app_files = (
        "app/pubspec.yaml",
        "app/lib/main.dart",
        "app/lib/core/lumenis_core_client.dart",
        "app/lib/product/product_domain.dart",
        "app/lib/product/lumenis_app.dart",
        "app/lib/features/launch/launch_surface.dart",
    )
    try:
        retired = frontend_state(ROOT) == 'REMOVED_PENDING_REBUILD'
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
        retired = False
    removed_entries = {'app/lib/main.dart', 'app/lib/product/lumenis_app.dart', 'app/lib/features/launch/launch_surface.dart'}
    for path in required_app_files:
        if retired and path in removed_entries:
            continue
        if not (ROOT / path).is_file():
            errors.append(f"missing canonical app foundation: {path}")

    errors.extend(tracked_path_errors(tracked()))

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
        if "from lumenis.shared.database import DatabaseRepository, main_db_path" not in evaluation_recorder_text:
            errors.append("Shared Evaluation recorder must use the canonical database owner")
        if "path = db_path or main_db_path()" not in evaluation_recorder_text:
            errors.append("Shared Evaluation recorder must resolve the canonical Production Truth path")

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
        if re.search(r"self\._(?:human_approved|approval_expiry)\s*=", ad_permission_text):
            errors.append("Ad permission adapter owns parallel human-approval state")
        for marker in (".grant_approval(", ".revoke_approval(", ".is_approved("):
            if marker not in ad_permission_text:
                errors.append(f"Ad permission adapter bypasses canonical approval owner: {marker}")

    security_owner = ROOT / "lumenis/system/security"
    for filename in ("permission.py", "action_firewall.py", "effect_fence.py", "__init__.py"):
        if not (security_owner / filename).is_file():
            errors.append(f"missing canonical SYSTEM security owner: lumenis/system/security/{filename}")

    agent_loop_path = ROOT / "agent_runtime/loop.py"
    if agent_loop_path.is_file():
        agent_loop_text = agent_loop_path.read_text(encoding="utf-8")
        for retired in (
            "from permission_gate",
            "import permission_gate",
            "from skill_execution_chain",
            "import skill_execution_chain",
        ):
            if retired in agent_loop_text:
                errors.append(f"Agent Runtime bypasses canonical SYSTEM security owner: {retired}")

    # Current product identity/default-context guard. Historical compatibility
    # IDs may exist only behind the documented compatibility boundary; active
    # runtime/config surfaces must not reintroduce a Taikoo-only product.
    app_identity_text = (ROOT / "app.py").read_text(encoding="utf-8")
    for marker in ("???????????", "taikoo-monitor"):
        if marker in app_identity_text:
            errors.append(f"active Product Core reintroduced legacy product identity: {marker}")

    experience_runtime_text = (ROOT / "experience_runtime.py").read_text(encoding="utf-8")
    for marker in (
        '"mode": "GLOBAL_ALL"',
        '"selection_authority": "/api/settings/context"',
        'identity["subject"] = None',
        'identity["domain"] = None',
    ):
        if marker not in experience_runtime_text:
            errors.append(f"runtime identity lost GLOBAL / ALL selection marker: {marker}")
    if "scope = sc.current_scope()" in experience_runtime_text[
        experience_runtime_text.find("def runtime_identity()"):
        experience_runtime_text.find('@experience_bp.route("/api/experience/subjects")')
    ]:
        errors.append("runtime identity must not project legacy subject_context fallback as current product focus")

    package_path = ROOT / "package.json"
    if package_path.is_file():
        try:
            package = json.loads(package_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"cannot inspect package identity: {exc}")
        else:
            if package.get("name") != "lumenis-core-tools":
                errors.append("active Node helper package must use lumenis-core-tools identity")

    repo_registry_path = ROOT / "repo_registry.json"
    if repo_registry_path.is_file():
        try:
            repository_registry = json.loads(repo_registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"cannot inspect repository registry: {exc}")
        else:
            production = [
                row for row in repository_registry.get("repositories", [])
                if row.get("role") == "production_core" and row.get("status") == "active"
            ]
            if len(production) != 1 or production[0].get("git_remote") != (
                "https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS.git"
            ):
                errors.append("repo_registry active production_core is not the canonical LUMENIS repository")

    sync_helper = ROOT / "scripts/github_upgrade_check.py"
    if sync_helper.is_file():
        helper_text = sync_helper.read_text(encoding="utf-8")
        for marker in ("Zachary-1012/Z-Brand-Core", "Doubao", "??"):
            if marker in helper_text:
                errors.append(f"current Git sync helper reintroduced legacy development authority: {marker}")
        if 'remote", "get-url", "origin"' not in helper_text:
            errors.append("current Git sync helper must derive repository authority from origin")

    routes_path = ROOT / "lumenis/shared/reporting/routes.py"
    if routes_path.is_file():
        routes_text = routes_path.read_text(encoding="utf-8")
        if "from app import" in routes_text or "import app" in routes_text:
            errors.append("Shared Reporting routes must not depend on app.py implementation")

    # Inspect executable production imports, not docs, tests, comments or
    # identifiers that merely share a retired module prefix. Stable API facades
    # such as browser_runtime_api and collector_guard_integration stay valid.
    retired_imports = []
    for source_path in production_python_files(ROOT):
        relative = source_path.relative_to(ROOT)
        try:
            tree = ast.parse(source_path.read_text(encoding="utf-8-sig"), filename=str(relative))
        except (OSError, UnicodeError, SyntaxError) as exc:
            errors.append(f"cannot inspect production Python source {relative}: {exc}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    package = list(relative.parts[:-1])
                    package = package[:max(0, len(package) - node.level + 1)]
                    base = ".".join(package)
                    module = ".".join(part for part in (base, node.module) if part)
                    imported = [module] if node.module else [
                        ".".join(part for part in (base, alias.name) if part)
                        for alias in node.names
                    ]
                elif node.module:
                    imported = [node.module]
                else:
                    imported = []
            else:
                continue
            for module in imported:
                retired = next(
                    (name for name in RETIRED_IMPORT_MODULES
                     if module == name or module.startswith(name + ".")),
                    None,
                )
                if retired:
                    retired_imports.append(
                        f"{relative.as_posix()}:{node.lineno}: {module} (retired owner {retired})"
                    )
    if retired_imports:
        errors.append("retired owner imports in production source:\n" + "\n".join(sorted(retired_imports)))

    if errors:
        print("LUMENIS Only-One/multi-surface architecture guard: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("LUMENIS Only-One/multi-surface architecture guard: PASS")
    print("product_architecture=00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md")
    print("experience_authority=00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md")
    print("surface_decision=00-GOVERNANCE/LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md")
    print("legacy_ui_reference_paths=0")
    return 0

if __name__ == "__main__":
    sys.exit(main())
