from __future__ import annotations

import hashlib
import json
from pathlib import Path

EXPECTED_FINGERPRINT = "68caa37c3f4a8d50f0c0b77befac0e8ae0c954b63b1a7583a8f822a28eaa690f"
EXPECTED_CONTRACT_ID = "lumenis-ggi-cross-product"
EXPECTED_VERSION = "1.1.0"
LOCAL_REPO = "Zachary-1012/LUMENIS-codex-Clean-OS"

EXPECTED_REGISTRY = {
    "Zachary-1012/LUMENIS-codex-Clean-OS": {
        "product": "序境 / LUMENIS",
        "role": "Production Core",
        "truth_owner": "Production Truth",
    },
    "Zachary-1012/Zachary-OS-AI": {
        "product": "序蕴 / LUMENIS Intelligence",
        "role": "Shared Intelligence Capability",
        "truth_owner": "Shared Intelligence Assets",
    },
    "Zachary-1012/global-growth-intelligence": {
        "product": "序衍 / LUMENIS Growth",
        "role": "Independent Research & Growth Product",
        "truth_owner": "Research / Growth Truth",
    },
    "Zachary-1012/lumenis-command": {
        "product": "序枢 / LUMENIS Command",
        "role": "R&D Control Sidecar",
        "truth_owner": "Engineering Evidence",
    },
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
    assert data["canonical_registry"] == EXPECTED_REGISTRY
    assert data["canonical_registry"][LOCAL_REPO]["truth_owner"] == "Production Truth"
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

    exchange = data["exchange_contract"]
    assert set(exchange["allowed"]) == {
        "versioned_contract",
        "artifact",
        "evidence_reference",
        "validated_learning_candidate",
    }
    assert set(exchange["forbidden"]) == {
        "production_database_copy",
        "production_credentials",
        "unrestricted_raw_secret_data",
        "automatic_production_truth_write",
    }

    contribution = data["ggi_shared_intelligence_contribution"]
    assert contribution["critical_path"] is False
    assert contribution["transport_pattern"] == "local_outbox_then_async_delivery"
    assert contribution["max_retries"] == 3
    assert set(contribution["states"]) == EXPECTED_STATES
    assert data["adoption_gate"] == EXPECTED_ADOPTION_GATE
    assert data["compatibility_gate"]["ci_blocking"] is True

    # 序境 / LUMENIS alone owns Production Truth. 序蕴、序衍、序枢 remain
    # independently governed products/capabilities and never receive unrestricted writes.
    assert EXPECTED_REGISTRY[LOCAL_REPO]["role"] == "Production Core"
    assert boundary["ai_or_research_may_overwrite_lumenis_production_truth"] is False
    assert boundary["unrestricted_cross_product_writer"] is False


if __name__ == "__main__":
    import sys

    validate_contract(Path(sys.argv[1]))
    from verify_source_adoption import validate_local_adoption
    validate_local_adoption(Path(sys.argv[1]).resolve().parents[1])
    print(
        f"CONTRACT OK {EXPECTED_CONTRACT_ID} v{EXPECTED_VERSION} "
        f"{EXPECTED_FINGERPRINT} repo={LOCAL_REPO}"
    )
