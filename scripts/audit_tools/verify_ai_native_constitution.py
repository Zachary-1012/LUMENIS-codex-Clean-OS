"""Blocking governance validator for the LUMENIS AI-native product constitution.

This gate validates that the Product Owner's lightweight constitution remains
inside the existing AGENTS -> governance -> implementation -> evidence chain.
It does not claim that any product capability, live environment, Round, release,
or commercial gate has passed.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

AGENTS = ROOT / "AGENTS.md"
README = ROOT / "README.md"
CONSTITUTION = ROOT / "00-GOVERNANCE" / "AI-NATIVE-PRODUCT-CONSTITUTION.md"
TAKEOVER = ROOT / "00-GOVERNANCE" / "LUMENIS-CODEX-TAKEOVER-CURRENT.md"
PLATFORM_GATE = ROOT / ".github" / "workflows" / "platform-verify.yml"
APP_GATE = ROOT / ".github" / "workflows" / "app-verify.yml"
REPORT_TEST = ROOT / "tests" / "test_report_audit.py"
TEST_TIERS = ROOT / "tests" / "CI_TEST_TIERS.md"

errors: list[str] = []


def read(path: Path) -> str:
    if not path.is_file():
        errors.append(f"missing required file: {path.relative_to(ROOT)}")
        return ""

    return path.read_text(encoding="utf-8")


def require(text: str, token: str, label: str) -> None:
    if token not in text:
        errors.append(f"{label}: missing required token: {token}")


def require_order(text: str, tokens: list[str], label: str) -> None:
    cursor = -1
    for token in tokens:
        position = text.find(token, cursor + 1)
        if position < 0:
            errors.append(f"{label}: missing chain token: {token}")
            return
        if position <= cursor:
            errors.append(f"{label}: chain order invalid at: {token}")
            return
        cursor = position


agents = read(AGENTS)
readme = read(README)
constitution = read(CONSTITUTION)
takeover = read(TAKEOVER)
workflow = read(PLATFORM_GATE)
app_workflow = read(APP_GATE)
report_test = read(REPORT_TEST)
test_tiers = read(TEST_TIERS)

principles = [
    int(match.group(1))
    for match in re.finditer(r"^##\s+(\d+)\.", constitution, flags=re.MULTILINE)
]
if principles != list(range(1, 19)):
    errors.append(f"constitution: expected numbered principles 1..18, got {principles}")

bootstrap_chain = [
    "AGENTS.md",
    "00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md",
    "00-GOVERNANCE/AI-NATIVE-PRODUCT-CONSTITUTION.md",
    "00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md",
]
require_order(agents, bootstrap_chain, "AGENTS mandatory bootstrap")
require_order(readme, bootstrap_chain, "README bootstrap")

for token in (
    "AI-native constitution execution chain — NON-BYPASS",
    "MACHINE_BLOCKING",
    "LIVE_NOT_VERIFIED",
    "HUMAN_DECISION_REQUIRED",
    "never delete, skip, weaken, quarantine",
    "never turn a blocking gate into advisory / informational",
    "never convert missing/unknown/uncollected data to zero",
    "never use reset/clean/checkout/restore",
    "never expand product scope",
    "python scripts/audit_tools/verify_ai_native_constitution.py",
):
    require(agents, token, "AGENTS constitution enforcement")

for token in (
    "MACHINE_BLOCKING",
    "LIVE_NOT_VERIFIED",
    "HUMAN_DECISION_REQUIRED",
    "python scripts/audit_tools/verify_ai_native_constitution.py",
    "M=`GPT-6 Astra / ultra`",
    "F=`GPT-6 Astra / ultra`",
    "C1–C6=`GPT-6.1 Sol / ultra`",
    "任务型 Subagent=`GPT-6 Luna / max`",
    "手动账号、模型、推理强度与速度/服务档位选择具有最高优先级",
    "Hook 不拥有模型选择权",
    "无任务时停止并待命",
):
    require(constitution, token, "constitution execution status")

for forbidden_allocation in (
    "M（Sol 或 Astra）",
    "Luna 处理有界机械子任务",
):
    if forbidden_allocation in constitution:
        errors.append(
            "constitution: fixed historical Codex model allocation is forbidden: "
            + forbidden_allocation
        )

require(
    takeover,
    "[The Product Owner's lightweight AI-native constitution](AI-NATIVE-PRODUCT-CONSTITUTION.md)",
    "CURRENT takeover",
)

workflow_step = (
    "- name: Validate AI-native product constitution execution chain (BLOCKING)\n"
    "        run: python scripts/audit_tools/verify_ai_native_constitution.py"
)
require(workflow, workflow_step, "Product Gate")
require(workflow, "Run clean-checkout hermetic pytest (BLOCKING)", "Product Gate")
require(
    app_workflow,
    "- name: Validate AI-native product constitution execution chain (BLOCKING)\n"
    "        run: python3 scripts/audit_tools/verify_ai_native_constitution.py",
    "App Gate",
)
require(app_workflow, '"00-GOVERNANCE/AI-NATIVE-PRODUCT-CONSTITUTION.md"', "App Gate paths")
require(app_workflow, '"scripts/audit_tools/verify_ai_native_constitution.py"', "App Gate paths")

step_start = workflow.find(
    "- name: Validate AI-native product constitution execution chain (BLOCKING)"
)
if step_start >= 0:
    next_step = workflow.find("\n      - name:", step_start + 1)
    step_block = workflow[step_start : next_step if next_step >= 0 else None]
    if "continue-on-error" in step_block:
        errors.append("Product Gate: constitution blocking step may not use continue-on-error")

for token in (
    "test_missing_total_notes_fails",
    "test_explicit_zero_total_notes_is_valid",
):
    require(report_test, token, "missing != 0 regression")

for token in (
    "quarantine is temporary and is not PASS",
    "Do not move a failing deterministic regression into Tier C or quarantine merely to make CI green.",
):
    require(test_tiers, token, "CI test-tier anti-bypass")

for forbidden in (
    ROOT / "00-GOVERNANCE" / "LUMENIS-PRODUCT-CONSTITUTION.md",
    ROOT / "00-GOVERNANCE" / "ENGINEERING-GOVERNANCE.md",
):
    if forbidden.exists():
        errors.append(
            "parallel governance authority is forbidden by the adopted constitution: "
            + str(forbidden.relative_to(ROOT))
        )

if errors:
    print("AI-NATIVE CONSTITUTION GATE: FAIL")
    for item in errors:
        print(f" - {item}")
    sys.exit(1)

print("AI-NATIVE CONSTITUTION GATE: PASS")
print(" - 18 lightweight principles present")
print(" - AGENTS/README bootstrap routes through the constitution")
print(" - non-bypass status and dirty-worktree protections present")
print(" - missing!=0 and CI anti-bypass regression anchors present")
print(" - Product Gate executes this validator as BLOCKING")
