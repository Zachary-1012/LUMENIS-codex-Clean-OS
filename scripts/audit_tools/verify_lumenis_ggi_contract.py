from __future__ import annotations

import hashlib
import json
from pathlib import Path

EXPECTED_FINGERPRINT = "a5e8d6e16bb99d1b5b0985d9fb406d53c853097315699c3a99ecfa914004a9c7"
EXPECTED_CONTRACT_ID = "lumenis-ggi-cross-product"
EXPECTED_VERSION = "1.0.0"
EXPECTED_REPOS = {
    "Zachary-1012/LUMENIS-codex-Clean-OS",
    "Zachary-1012/Zachary-OS-AI",
    "Zachary-1012/global-growth-intelligence",
    "Zachary-1012/lumenis-command",
}
EXPECTED_DOMAINS = {"CTH", "BMP", "SHARED_CAPABILITY", "SYSTEM"}
EXPECTED_ADOPTION_GATE = ["RECEIVE", "VERIFY", "EVALUATE", "ADAPT", "TEST", "LOCAL_RELEASE"]
EXPECTED_STATES = {"PENDING", "EXPORTED", "ACKNOWLEDGED", "REJECTED", "FAILED", "DEAD_LETTER"}


def validate_contract(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    fingerprint = data.pop("protocol_fingerprint_sha256", None)
    canonical = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    actual = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    assert fingerprint == EXPECTED_FINGERPRINT, (fingerprint, EXPECTED_FINGERPRINT)
    assert actual == EXPECTED_FINGERPRINT, (actual, EXPECTED_FINGERPRINT)
    assert data["contract_id"] == EXPECTED_CONTRACT_ID
    assert data["contract_version"] == EXPECTED_VERSION
    assert data["status"] == "ACTIVE"
    assert set(data["canonical_registry"]) == EXPECTED_REPOS
    assert set(data["lumenis_domain_contract"]["domains"]) == EXPECTED_DOMAINS

    boundary = data["truth_and_runtime_boundary"]
    for key in (
        "shared_production_database",
        "cross_product_runtime_hard_dependency",
        "copy_product_business_code",
        "unrestricted_cross_product_writer",
        "ai_or_research_may_overwrite_lumenis_production_truth",
    ):
        assert boundary[key] is False, key
    assert boundary["ggi_operates_when_osai_unavailable"] is True
    assert boundary["lumenis_operates_when_ggi_unavailable"] is True

    contribution = data["ggi_shared_intelligence_contribution"]
    assert contribution["critical_path"] is False
    assert contribution["max_retries"] == 3
    assert set(contribution["states"]) == EXPECTED_STATES
    assert data["adoption_gate"] == EXPECTED_ADOPTION_GATE
    assert data["compatibility_gate"]["ci_blocking"] is True


if __name__ == "__main__":
    import sys

    validate_contract(Path(sys.argv[1]))
    print(f"CONTRACT OK {EXPECTED_CONTRACT_ID} v{EXPECTED_VERSION} {EXPECTED_FINGERPRINT}")
