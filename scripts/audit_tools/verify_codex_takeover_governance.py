from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EXPECTED_CONTRACT_ID = "lumenis-ggi-cross-product"
EXPECTED_VERSION = "1.1.0"
EXPECTED_FINGERPRINT = "68caa37c3f4a8d50f0c0b77befac0e8ae0c954b63b1a7583a8f822a28eaa690f"
EXPECTED_LOCAL_REPO = "Zachary-1012/LUMENIS-codex-Clean-OS"
CONTRACT_BASENAME = "LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json"

PATHS = {
    "agents": ROOT / "AGENTS.md",
    "readme": ROOT / "README.md",
    "takeover": ROOT / "00-GOVERNANCE" / "LUMENIS-CODEX-TAKEOVER-CURRENT.md",
    "architecture": ROOT / "00-GOVERNANCE" / "LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md",
    "experience": ROOT / "00-GOVERNANCE" / "LUMENIS-EXPERIENCE-CONSTITUTION.md",
    "surface_decision": ROOT / "00-GOVERNANCE" / "LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md",
    "source_index": ROOT / "00-GOVERNANCE" / "LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md",
    "launch_plan": ROOT / "00-GOVERNANCE" / "LAUNCH-CONVERGENCE-MASTER-PLAN-V1.md",
    "experience_contracts": ROOT / "contracts" / "experience" / "README.md",
    "registry": ROOT / "00-GOVERNANCE" / "CROSS-REPO-CANONICAL-REGISTRY-V1.md",
    "contract": ROOT / "00-GOVERNANCE" / CONTRACT_BASENAME,
    "platform_workflow": ROOT / ".github" / "workflows" / "platform-verify.yml",
}


def _read(name: str) -> str:
    path = PATHS[name]
    if not path.is_file():
        raise AssertionError(f"missing required takeover/governance file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def _require(text: str, *needles: str, label: str) -> None:
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise AssertionError(f"{label} missing required current markers: {missing}")


def _assert_single_machine_contract() -> None:
    canonical = PATHS["contract"].resolve()
    copies = sorted(
        path.resolve()
        for path in ROOT.rglob(CONTRACT_BASENAME)
        if path.resolve() != canonical
    )
    if copies:
        relative = [str(path.relative_to(ROOT.resolve())) for path in copies]
        raise AssertionError(
            "duplicate live machine contract copies are forbidden; "
            f"canonical={canonical.relative_to(ROOT.resolve())}; duplicates={relative}"
        )


def validate() -> None:
    agents = _read("agents")
    readme = _read("readme")
    takeover = _read("takeover")
    architecture = _read("architecture")
    experience = _read("experience")
    surface_decision = _read("surface_decision")
    source_index = _read("source_index")
    launch_plan = _read("launch_plan")
    experience_contracts = _read("experience_contracts")
    registry = _read("registry")
    platform_workflow = _read("platform_workflow")
    contract = json.loads(_read("contract"))

    _assert_single_machine_contract()

    assert contract["contract_id"] == EXPECTED_CONTRACT_ID
    assert contract["contract_version"] == EXPECTED_VERSION
    assert contract["protocol_fingerprint_sha256"] == EXPECTED_FINGERPRINT
    assert contract["status"] == "ACTIVE"
    assert contract["canonical_registry"][EXPECTED_LOCAL_REPO]["truth_owner"] == "Production Truth"

    _require(
        registry,
        "Effective protocol: **lumenis-ggi-cross-product v1.1.0**",
        "version     = 1.1.0",
        f"fingerprint = {EXPECTED_FINGERPRINT}",
        "序境 / LUMENIS · Production Core",
        "序蕴 / LUMENIS Intelligence",
        "序衍 / LUMENIS Growth",
        "序枢 / LUMENIS Command",
        "00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json",
        label="cross-repo registry",
    )
    if "version     = 1.0.0" in registry:
        raise AssertionError("cross-repo registry regressed the CURRENT machine contract to v1.0.0")

    _require(
        takeover,
        "Status: **CURRENT EXECUTION ENTRYPOINT / NO-REDISCOVERY**",
        "AGENTS.md",
        "00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md",
        "00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json",
        "00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md",
        "git rev-parse origin/main",
        "version     = 1.1.0",
        EXPECTED_FINGERPRINT,
        "verify_codex_takeover_governance.py",
        "only repository execution router",
        "ROUND 02 starts only in a new Sol-controlled task",
        "DESIGN_READY",
        label="CURRENT takeover",
    )

    _require(
        architecture,
        "CANONICAL / SOLE PRODUCT ARCHITECTURE AUTHORITY",
        "DESIGN_EXPLORATION",
        "DESIGN_READY",
        "implementation from a PDF, screenshot, fixture, Figma frame",
        label="CURRENT product architecture",
    )

    _require(
        experience,
        "CANONICAL / SOLE EXPERIENCE DESIGN AUTHORITY",
        "Internal version: **3.2**",
        "DESIGN_EXPLORATION",
        "DESIGN_READY",
        "copied directly into production UI",
        "Sol acceptance decision is `REWORK`",
        label="CURRENT Experience Constitution",
    )

    _require(
        surface_decision,
        "PRODUCT OWNER APPROVED / ARCHITECTURE DECISION",
        "Public Website",
        "Web Workspace",
        "Desktop App",
        "Mobile Companion",
        "Jev product decision",
        "ROUND 07",
        "DESIGN_EXPLORATION",
        "DESIGN_READY",
        label="CURRENT multi-surface decision",
    )

    _require(
        source_index,
        "CURRENT EXECUTION INDEX / FIFTEEN-ROUND CLOSED LOOP",
        "Authority, Only-One and multi-surface decision",
        "Cross-Surface Experience Foundation",
        "Closed-loop internal beta",
        "Jev",
        ".opencode/opencode.json",
        "lumenis/system/ai_gateway/",
        "lumenis/system/collector/",
        "LUMENIS product account remains deferred until its approved identity/tenant gate after internal beta",
        "Do not repeat a full-repository audit for normal work",
        "Product Skill Store is a named P0 capability",
        "Direct PDF/sketch implementation is `REWORK`",
        label="CURRENT source owner index",
    )

    _require(
        launch_plan,
        "SUBORDINATE ROUND 15 LAUNCH GATE / NOT THE TASK-SEQUENCE AUTHORITY",
        "D:\\LUMENIS_REBUILD\\序\\序境",
        "exact 15-round sequence",
        label="launch convergence plan",
    )

    _require(
        experience_contracts,
        "DESIGN_EXPLORATION",
        "DESIGN_READY",
        "direct code target",
        "REWORK",
        label="Experience contract router",
    )

    for required_path in (
        ROOT / ".opencode" / "opencode.json",
        ROOT / "app" / "lib",
        ROOT / "contracts" / "experience",
        ROOT / "lumenis" / "system" / "ai_gateway",
        ROOT / "lumenis" / "system" / "collector",
        ROOT / "lumenis" / "system" / "browser" / "runtime",
        ROOT / "lumenis" / "shared" / "evidence",
        ROOT / "lumenis" / "shared" / "database",
    ):
        if not required_path.exists():
            raise AssertionError(
                "CURRENT source owner path is missing: "
                f"{required_path.relative_to(ROOT)}"
            )

    _require(
        agents,
        "### Mandatory Codex bootstrap",
        "00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md",
        "00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md",
        "00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json",
        "00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md",
        "00-GOVERNANCE/LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md",
        "### Fifteen-round closed-loop red line",
        "only repository execution router",
        "ROUND 02 begins in its own Sol-controlled task",
        "DESIGN_EXPLORATION",
        "DESIGN_READY",
        "Sol returns `REWORK`",
        "git rev-parse origin/main",
        "v1.1.0",
        EXPECTED_FINGERPRINT,
        label="root AGENTS.md",
    )

    _require(
        readme,
        "Coding Agent 必须首先读取 [`AGENTS.md`](AGENTS.md)。",
        "Zachary-1012/LUMENIS-codex-Clean-OS",
        label="root README.md",
    )

    # The single Product Gate owns both the cross-product machine contract and
    # Codex takeover consistency. A duplicate standalone workflow is retired.
    _require(
        platform_workflow,
        "verify_lumenis_ggi_contract.py",
        "verify_codex_takeover_governance.py",
        label="platform verify workflow",
    )

    # Dated source-audit SHAs may remain as provenance. What must never regress is
    # the CURRENT takeover path pretending a fixed SHA is the live HEAD.
    if "current HEAD = READ WITH git fetch + git rev-parse origin/main" not in takeover:
        raise AssertionError("CURRENT takeover must resolve origin/main dynamically")


if __name__ == "__main__":
    validate()
    print(
        "CODEX TAKEOVER GOVERNANCE OK "
        f"{EXPECTED_CONTRACT_ID} v{EXPECTED_VERSION} {EXPECTED_FINGERPRINT} "
        "single-machine-contract=PASS workflow-guards=PASS"
    )
