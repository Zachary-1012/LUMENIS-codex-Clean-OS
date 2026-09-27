"""A fixed preexisting v2 signature guards real Evidence read compatibility."""
from __future__ import annotations

import hashlib
import hmac

from lumenis.shared.evidence import store


def test_deployed_v2_canonical_payload_is_stable():
    # This digest was produced by the preexisting full-record v2 canonicalizer,
    # independently of the current signer implementation. No product DB or
    # production secret is used in this fixture.
    row = dict.fromkeys(store._EVIDENCE_V2_MATERIAL_FIELDS)
    row.update({
        "id": 17,
        "inputs_json": '{"z":1,"a":{"b":2,"a":1}}',
        "outputs_json": '{"ok":true}',
        "collection_metadata": '{"source":"official","attempt":1}',
        "source": "compat-fixture",
        "project": "LUMENIS",
        "product": "BMP",
        "result": "PASS",
        "status": "verified",
        "domain_id": "zbmp",
        "product_id": "ZBMP",
        "evidence_hash": "",
        "integrity_version": 2,
        "integrity_algorithm": "hmac-sha256",
        "integrity_key_id": "fixture-key",
        "integrity_digest": "",
    })
    signature = hmac.new(
        b"synthetic-compat-key", store._integrity_payload(row), hashlib.sha256,
    ).hexdigest()
    assert signature == "010d310b191d2bef426d558b5006c93918a8f26266e00ba8b25717d3cb0dba02"
