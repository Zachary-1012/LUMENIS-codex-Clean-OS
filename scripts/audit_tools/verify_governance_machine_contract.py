from __future__ import annotations

import argparse
import json
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "00-GOVERNANCE" / "LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json"
AGENTS_PATH = ROOT / "AGENTS.md"
CURRENT_PATH = ROOT / "00-GOVERNANCE" / "LUMENIS-CODEX-TAKEOVER-CURRENT.md"

EXPECTED_ROLES = {"M", "F", "C1", "C2", "C3", "C4", "C5", "C6"}
EXPECTED_C_WINDOWS = {f"C{i}": f"W{i}" for i in range(1, 7)}
EXPECTED_STATES = [
    "ELIGIBLE",
    "DISPATCHED",
    "RUNNING",
    "WAITING_DEPENDENCY",
    "BLOCKED",
    "JOB_CLOSED",
]
EXPECTED_LADDER = [
    "DEFINED",
    "IMPLEMENTED",
    "INTEGRATED",
    "VERIFIED",
    "JOB_CLOSED",
    "RELEASED",
    "OPERATING",
]


def fail(message: str) -> None:
    raise AssertionError(message)


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"missing governance JSON: {path.relative_to(ROOT)}")
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path.relative_to(ROOT)}: {exc}")
    if not isinstance(value, dict):
        fail(f"governance JSON root must be object: {path.relative_to(ROOT)}")
    return value


def changed_paths() -> set[str]:
    proc = subprocess.run(
        ["git", "diff-tree", "--root", "--first-parent", "--no-commit-id", "--name-only", "-r", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        fail(f"cannot inspect HEAD changed paths: {proc.stderr.strip()}")
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


def path_requires_current(path: str, publication: dict) -> bool:
    if path in set(publication["exact_paths"]):
        return True
    if any(path.startswith(prefix) for prefix in publication["prefixes"]):
        return True
    if "/" not in path and any(path.endswith(ext) for ext in publication["root_extensions"]):
        return True
    return False


def validate_publication_policy(contract: dict, paths: set[str]) -> None:
    publication = contract["publication_policy"]
    if publication.get("copublish_current_for_delivery_commit") is not True:
        fail("delivery commits must co-publish CURRENT")
    delivered = sorted(path for path in paths if path_requires_current(path, publication))
    if delivered and publication["current_status_path"] not in paths:
        fail(f"delivery commit changed without CURRENT co-publication: {delivered[:12]}")


def validate_semantic_change_receipt(contract: dict, paths: set[str]) -> None:
    policy = contract["semantic_change_policy"]
    if policy.get("machine_contract_is_semantic_source") is not True:
        fail("machine contract must remain the semantic governance source")
    if policy.get("markdown_only_change_may_change_machine_semantics") is not False:
        fail("Markdown-only edits may not change machine governance semantics")
    if policy.get("product_authorities_remain_external_references") is not True:
        fail("governance machine contract may not become a second product authority")
    changed_semantic = set(policy["semantic_machine_paths"]) & paths
    if not changed_semantic:
        return
    if policy.get("semantic_machine_change_requires_po_receipt") is not True:
        fail("semantic machine changes must require a PO approval receipt")
    prefix = contract["approval"]["receipt_directory"].rstrip("/") + "/"
    receipts = [path for path in paths if path.startswith(prefix) and path.endswith(".json")]
    if not receipts:
        fail(f"semantic governance changed without same-commit PO approval receipt: {sorted(changed_semantic)}")


def validate_model_routing(contract: dict) -> None:
    semantics = contract["model_routing"]
    routing_path = ROOT / semantics["routing_source"]
    config_path = ROOT / semantics["project_config_source"]
    if not routing_path.is_file() or not config_path.is_file():
        fail("structured Codex routing/config files are missing")

    routing = tomllib.loads(routing_path.read_text(encoding="utf-8-sig"))
    config = tomllib.loads(config_path.read_text(encoding="utf-8-sig"))

    if routing.get("manual_window_selection_wins") is not semantics["manual_window_selection_wins"]:
        fail("manual-window selection precedence drift")
    if routing.get("hooks_may_change_model") is not semantics["hooks_may_change_model"]:
        fail("Hook model authority drift")
    if routing.get("profiles_are_launch_helpers_only") is not semantics["profiles_are_launch_helpers_only"]:
        fail("profile model authority drift")

    roles = routing.get("roles", {})
    for role, expected in semantics["role_defaults"].items():
        actual = roles.get(role, {})
        if actual.get("model") != expected["model"] or actual.get("reasoning_effort") != expected["reasoning_effort"]:
            fail(f"structured model routing mismatch for {role}")

    expected_sub = semantics["subagents"]
    actual_sub = routing.get("subagents", {})
    for key in ("model", "reasoning_effort", "explicit_spawn_overrides_default"):
        if actual_sub.get(key) != expected_sub[key]:
            fail(f"structured subagent routing mismatch: {key}")

    cfg_sem = semantics["project_config"]
    forbidden = {
        "model", "model_provider", "service_tier", "review_model", "profile",
        "model_reasoning_effort", "plan_mode_reasoning_effort",
        "model_reasoning_summary", "model_verbosity", "model_context_window",
        "model_auto_compact_token_limit", "model_catalog_json",
    }
    if cfg_sem["top_level_model_selection_forbidden"] and forbidden.intersection(config):
        fail(f"repository config sets forbidden top-level model keys: {sorted(forbidden.intersection(config))}")
    if config.get("web_search") != cfg_sem["web_search"]:
        fail("repository live web-search policy drift")
    features = config.get("features", {})
    for key in cfg_sem["required_features"]:
        if features.get(key) is not True:
            fail(f"required Codex feature disabled: {key}")
    mcp_expected = cfg_sem["official_docs_mcp"]
    mcp_actual = config.get("mcp_servers", {}).get(mcp_expected["name"], {})
    for key in ("url", "enabled", "required"):
        if mcp_actual.get(key) != mcp_expected[key]:
            fail(f"official developer-docs MCP drift: {key}")
    budget = int(config.get("project_doc_max_bytes") or 0)
    needed = len(AGENTS_PATH.read_bytes()) + int(cfg_sem["project_doc_headroom_bytes"])
    if budget < needed:
        fail(f"project_doc_max_bytes below AGENTS+headroom: budget={budget} needed={needed}")


def validate_contract() -> dict:
    c = load_json(CONTRACT_PATH)
    if c.get("schema") != "lumenis.governance-machine-contract/v1":
        fail("unexpected governance contract schema")
    if c.get("contract_id") != "lumenis-governance-machine" or c.get("contract_version") != "1.3.0":
        fail("unexpected governance contract identity/version")
    if c.get("status") != "ACTIVE" or c.get("scope") != "GOVERNANCE_ONLY":
        fail("governance machine contract must remain ACTIVE and GOVERNANCE_ONLY")
    if c.get("product_semantics_may_change") is not False:
        fail("governance optimization may not change product semantics")

    repo = c.get("repository", {})
    if repo.get("full_name") != "Zachary-1012/LUMENIS-codex-Clean-OS" or repo.get("canonical_branch") != "main":
        fail("governance contract repository/main identity drift")

    roles = c.get("roles", {})
    if set(roles) != EXPECTED_ROLES:
        fail(f"governance role set drift: {sorted(roles)}")
    if any(not data.get("eligible") for data in roles.values()):
        fail("all canonical delivery roles must remain eligible")
    for role, window in EXPECTED_C_WINDOWS.items():
        if roles[role].get("window") != window or roles[role].get("environment") != "Local Codex":
            fail(f"{role} delivery window/environment drift")
    if roles["M"].get("kind") != "controller_integrator_acceptance":
        fail("M controller/integration/acceptance role drift")
    if roles["F"].get("kind") != "frontend_experience":
        fail("F Experience role drift")

    dispatch = c.get("dispatch", {})
    if dispatch.get("published_state_is_live_scheduler") is not False:
        fail("PUBLISHED_STATE must never become the live scheduler")
    if dispatch.get("allowed_states") != EXPECTED_STATES:
        fail("live dispatch state vocabulary drift")
    if dispatch.get("runtime_state_tracked") is not False:
        fail("live dispatch runtime state must remain local/untracked")
    if dispatch.get("live_authority") != "latest_explicit_product_owner_instruction_for_that_window":
        fail("live dispatch authority drift")
    if dispatch.get("wait_resume_condition_is_binding") is not True:
        fail("WAITING_DEPENDENCY resume condition must remain binding")
    if dispatch.get("resume_after_condition_without_second_approval") is not True:
        fail("satisfied resume conditions must not require redundant re-approval")

    execution = c.get("execution_policy", {})
    required_true = (
        "full_outcome_required",
        "minimum_subset_for_gate_forbidden",
        "incremental_integration_allowed",
        "owner_resolves_ordinary_failures",
        "delta_bootstrap_for_continuous_same_task",
    )
    for key in required_true:
        if execution.get(key) is not True:
            fail(f"execution semantic drift: {key}")
    if execution.get("m_review_granularity") != "outcome_package":
        fail("M must review coherent outcome packages, not every function")
    if execution.get("progress_only_report_is_delivery") is not False:
        fail("progress-only reports may not count as delivery")
    if execution.get("no_actionable_work_policy") != "WAIT":
        fail("idle controller/window policy drift")
    if execution.get("deterministic_internal_failure_requires_external_research") is not False:
        fail("deterministic internal bugs must not force unrelated research")
    if execution.get("external_or_uncertain_failure_requires_current_research") is not True:
        fail("external/uncertain failures must retain current research")

    red = c.get("red_lines", {})
    if not red or any(value is not False for value in red.values()):
        fail("all governance red lines must remain false/forbidden")

    completion = c.get("completion", {})
    if completion.get("ladder") != EXPECTED_LADDER:
        fail("completion ladder drift")
    if completion.get("mapped_user_outcome_complete_from") != "JOB_CLOSED":
        fail("mapped user outcome may not complete before JOB_CLOSED")
    if completion.get("source_or_test_alone_is_completion") is not False:
        fail("source/test alone may not become completion")
    if completion.get("release_requires_same_sha_evidence") is not True:
        fail("release must keep same-SHA evidence")

    gates = c.get("gates", {})
    if set(gates) != {"change_gate", "owner_closure_gate", "release_gate"}:
        fail("governance requires exactly Change/Owner Closure/Release gate semantics")
    policy = c.get("verification_policy", {})
    for key in ("unit_integration_required", "mock_fixture_http_success_is_acceptance",
                "gate_pass_is_product_closure"):
        if policy.get(key) is not False:
            fail(f"PO verification policy drift: {key}")
    for key in ("create_unit_integration_allowed", "run_unit_integration_allowed",
                "renamed_module_suites_allowed", "affected_regressions_required",
                "historical_tests_and_failures_preserved", "known_real_defects_must_be_repaired"):
        if policy.get(key) is not True:
            fail(f"verification integrity missing: {key}")
    required_checks = {"compilation", "static_quality", "security_permission", "data_consistency",
                       "real_user_e2e", "recovery", "release_verification"}
    if not required_checks.issubset(policy.get("retained_checks", [])):
        fail("retained build/static/security/data/E2E/recovery/release checks missing")
    receipt = load_json(ROOT / policy["approval_receipt"])
    if receipt.get("approved_by") != "Product Owner" or receipt.get("status") != "APPROVED":
        fail("verification policy lacks actual PO receipt")
    requirements = set(gates["change_gate"].get("requires", []))
    if "affected_tests" not in requirements or not {
        "applicable_build_static_security_data_checks", "applicable_real_operation_evidence",
        "mandatory_blocking_guards"}.issubset(requirements):
        fail("Change Gate does not implement current real-outcome policy")
    if "mapped_R_J_U" not in gates["owner_closure_gate"].get("requires", []):
        fail("Owner Closure Gate must retain mapped R/J/U")
    for item in ("R01-R15", "J1-J8", "U01-U25", "Product_Gate", "App_Gate", "Critical_E2E"):
        if item not in gates["release_gate"].get("requires", []):
            fail(f"Release Gate missing {item}")

    approval = c.get("approval", {})
    if approval.get("agent_may_self_assert_po_approved") is not False:
        fail("agents may never self-assert PO approval")
    if approval.get("policy_admission_allowed_for_same_class") is not True:
        fail("same-class policy admission should remain allowed")
    if approval.get("approved_by_value") != "Product Owner":
        fail("approval authority drift")

    evolution = c.get("capability_evolution", {})
    if evolution.get("enabled") is not True or evolution.get("feature_creep_allowed") is not False:
        fail("capability evolution must be enabled without feature creep")
    if evolution.get("output_branches") != ["PRODUCT_ADOPTION", "MODEL_LEARNING_CANDIDATE"]:
        fail("capability evolution dual-output contract drift")
    if evolution.get("stop_rule") != "DEFER_IF_NO_MATERIAL_CURRENT_JOB_BENEFIT_OR_UNJUSTIFIED_CLOSURE_DELAY":
        fail("capability evolution stop rule drift")

    branch = c.get("branch_policy", {})
    if branch.get("phase") != "PRE_INTERNAL_BETA_CLOSURE":
        fail("unexpected branch-governance phase")
    if branch.get("platform_branch_protection_required_now") is not False:
        fail("pre-beta closure should not silently force PR/branch-protection workflow")
    if branch.get("direct_main_allowed") is not False or branch.get("force_push_allowed") is not False:
        fail("reviewed branch integration/no-force-push policy drift")
    for key in ("working_branches_allowed", "pull_requests_allowed", "merge_requires_current_head_review"):
        if branch.get(key) is not True:
            fail(f"PO branch authorization missing: {key}")
    if branch.get("default_workflow") != "BRANCH_VERIFY_REVIEW_MERGE_MAIN":
        fail("branch verification/review/merge workflow drift")
    if branch.get("active_branch_auto_cleanup_allowed") is not False:
        fail("active branches may not be deleted automatically")
    branch_receipt = load_json(ROOT / branch["approval_receipt"])
    if branch_receipt.get("status") != "APPROVED" or branch_receipt.get("approved_by") != "Product Owner":
        fail("branch workflow lacks PO approval receipt")
    if branch.get("harden_at") != "INTERNAL_BETA_ENTRY":
        fail("branch hardening trigger drift")

    runtime_rel = dispatch.get("runtime_state_path")
    if not isinstance(runtime_rel, str) or not runtime_rel.startswith("data/runtime/governance/"):
        fail("live dispatch path must stay under ignored data/runtime/governance")
    ignored = subprocess.run(["git", "check-ignore", "-q", runtime_rel], cwd=ROOT, check=False)
    if ignored.returncode != 0:
        fail(f"live dispatch runtime path is not git-ignored: {runtime_rel}")
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", runtime_rel],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if tracked.returncode == 0:
        fail(f"live dispatch runtime path must not be tracked: {runtime_rel}")

    for path in (AGENTS_PATH, CURRENT_PATH):
        text = path.read_text(encoding="utf-8")
        if CONTRACT_PATH.name not in text:
            fail(f"{path.name} must reference the governance machine contract")

    validate_model_routing(c)
    return c


def validate_approval_receipts(contract: dict) -> None:
    approval = contract["approval"]
    directory = ROOT / approval["receipt_directory"]
    if not directory.exists():
        fail("approval receipt directory missing")
    required = set(approval["required_fields"])
    allowed_sources = set(approval["allowed_source_types"])
    for path in sorted(directory.glob("*.json")):
        receipt = load_json(path)
        missing = required - set(receipt)
        if missing:
            fail(f"{path.name} missing approval fields: {sorted(missing)}")
        if receipt["schema"] != approval["receipt_schema"]:
            fail(f"{path.name} approval schema mismatch")
        if receipt["approved_by"] != approval["approved_by_value"]:
            fail(f"{path.name} must be approved by Product Owner")
        if receipt["approval_source_type"] not in allowed_sources:
            fail(f"{path.name} has unsupported approval source type")
        if receipt["status"] not in {"APPROVED", "SUPERSEDED", "REVOKED"}:
            fail(f"{path.name} invalid approval status")
        if not isinstance(receipt["scope_manifest"], dict) or not receipt["scope_manifest"]:
            fail(f"{path.name} requires non-empty scope_manifest")
        if not isinstance(receipt["constraints"], list) or not receipt["constraints"]:
            fail(f"{path.name} requires non-empty constraints")


def validate_live_dispatch(path: Path, contract: dict) -> None:
    state = load_json(path)
    if state.get("schema") != "lumenis.live-dispatch/v1":
        fail("live dispatch schema mismatch")
    roles = state.get("roles")
    if not isinstance(roles, dict) or set(roles) != EXPECTED_ROLES:
        fail("live dispatch must contain M/F/C1-C6 exactly")
    requirements = contract["dispatch"]["state_requirements"]
    allowed = set(contract["dispatch"]["allowed_states"])
    for role, row in roles.items():
        if not isinstance(row, dict):
            fail(f"live dispatch row must be object: {role}")
        status = row.get("state")
        if status not in allowed:
            fail(f"invalid live dispatch state for {role}: {status}")
        for field in requirements[status]:
            if not row.get(field):
                fail(f"{role}/{status} missing required field: {field}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-dispatch", type=Path)
    args = parser.parse_args()
    paths = changed_paths()
    contract = validate_contract()
    validate_approval_receipts(contract)
    validate_semantic_change_receipt(contract, paths)
    validate_publication_policy(contract, paths)
    if args.live_dispatch is not None:
        validate_live_dispatch(args.live_dispatch, contract)
    print("GOVERNANCE MACHINE CONTRACT: PASS")
    print(" - current semantic governance is JSON-backed")
    print(" - model routing is validated from structured TOML, not prose markers")
    print(" - delivery commits co-publish CURRENT through machine policy")
    print(" - live dispatch stays local/untracked")
    print(" - PO approvals require receipts; agents cannot self-approve")
    print(" - Change / Owner Closure / Release gates remain distinct")
    print(" - branch hardening is deferred to INTERNAL_BETA_ENTRY")


if __name__ == "__main__":
    main()
