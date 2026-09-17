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
    "registry": ROOT / "00-GOVERNANCE" / "CROSS-REPO-CANONICAL-REGISTRY-V1.md",
    "contract": ROOT / "00-GOVERNANCE" / CONTRACT_BASENAME,
    "contract_workflow": ROOT / ".github" / "workflows" / "lumenis-ggi-contract.yml",
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
    registry = _read("registry")
    contract_workflow = _read("contract_workflow")
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
        "git rev-parse origin/main",
        "version     = 1.1.0",
        EXPECTED_FINGERPRINT,
        "verify_codex_takeover_governance.py",
        label="CURRENT takeover",
    )

    _require(
        agents,
        "### Mandatory Codex bootstrap",
        "00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md",
        "00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md",
        "00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json",
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

    # Both the dedicated contract workflow and the broader product gate must
    # enforce the machine contract and the Codex takeover governance together.
    for label, workflow in (
        ("dedicated contract workflow", contract_workflow),
        ("platform verify workflow", platform_workflow),
    ):
        _require(
            workflow,
            "verify_lumenis_ggi_contract.py",
            "verify_codex_takeover_governance.py",
            label=label,
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
