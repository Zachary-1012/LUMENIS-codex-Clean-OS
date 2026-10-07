from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "00-GOVERNANCE" / "LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json"
AGENTS_PATH = ROOT / "AGENTS.md"
CURRENT_PATH = ROOT / "00-GOVERNANCE" / "LUMENIS-CODEX-TAKEOVER-CURRENT.md"

EXPECTED_ROLES = {"M", "F", "C1", "C2", "C3", "C4", "C5", "C6"}
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


def validate_contract() -> dict:
    c = load_json(CONTRACT_PATH)
    if c.get("schema") != "lumenis.governance-machine-contract/v1":
        fail("unexpected governance contract schema")
    if c.get("contract_id") != "lumenis-governance-machine" or c.get("contract_version") != "1.0.0":
        fail("unexpected governance contract identity/version")
    if c.get("status") != "ACTIVE" or c.get("scope") != "GOVERNANCE_ONLY":
        fail("governance machine contract must remain ACTIVE and GOVERNANCE_ONLY")
    if c.get("product_semantics_may_change") is not False:
        fail("governance optimization may not change product semantics")

    repo = c.get("repository", {})
    if repo.get("full_name") != "Zachary-1012/LUMENIS-codex-Clean-OS" or repo.get("canonical_branch") != "main":
        fail("governance contract repository/main identity drift")

    if set(c.get("roles", {})) != EXPECTED_ROLES:
        fail(f"governance role set drift: {sorted(c.get('roles', {}))}")
    if any(not data.get("eligible") for data in c["roles"].values()):
        fail("all canonical delivery roles must remain eligible")

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
    if "affected_tests" not in gates["change_gate"].get("requires", []):
        fail("Change Gate must retain affected tests")
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
    if branch.get("direct_main_allowed") is not True or branch.get("force_push_allowed") is not False:
        fail("current direct-main/no-force-push policy drift")
    if branch.get("harden_at") != "INTERNAL_BETA_ENTRY":
        fail("branch hardening trigger drift")

    runtime_rel = dispatch.get("runtime_state_path")
    if not isinstance(runtime_rel, str) or not runtime_rel.startswith("data/runtime/governance/"):
        fail("live dispatch path must stay under ignored data/runtime/governance")
    check = subprocess.run(
        ["git", "check-ignore", "-q", runtime_rel],
        cwd=ROOT,
        check=False,
    )
    if check.returncode != 0:
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
    contract = validate_contract()
    validate_approval_receipts(contract)
    if args.live_dispatch is not None:
        validate_live_dispatch(args.live_dispatch, contract)
    print("GOVERNANCE MACHINE CONTRACT: PASS")
    print(" - semantic governance is JSON-backed, not Markdown-string-backed")
    print(" - live dispatch stays local/untracked")
    print(" - PO approvals require receipts; agents cannot self-approve")
    print(" - Change / Owner Closure / Release gates remain distinct")
    print(" - branch hardening is deferred to INTERNAL_BETA_ENTRY")


if __name__ == "__main__":
    main()
