"""Known-vector and boundary tests for public owned-training phase fingerprints."""
from dataclasses import replace
import hashlib
import json

import pytest

from lumenis.system.ai_gateway.owned_training import TrainingApprovalRequest
from lumenis.system.security import permission as p


_GLOBAL_CTH = {"scope_descriptors": {
    "GLOBAL / ALL": {
        "domain_id": "cth",
        "product_id": "CTH",
        "global_scope": True,
        "subject_id": None,
        "brand_focus_id": None,
    },
}}


def _request(**changes):
    values = {
        "model_id": "openai/gpt-oss-20b",
        "model_revision": "6cee5e81ee83917806bbde320786a8fb61efebee",
        "train_sha256": "1" * 64,
        "heldout_sha256": "2" * 64,
        "scopes": ("GLOBAL / ALL",),
        "recipe": "openai-h100-bf16",
        "manifest_sha256": "3" * 64,
        "domain_id": "cth",
    }
    values.update(changes)
    return TrainingApprovalRequest(**values)


def _canonical_digest(value):
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def test_phase_fingerprints_match_independent_known_vectors(monkeypatch):
    # Fingerprinting must not request a grant or touch any database connector.
    monkeypatch.setattr(
        p.PermissionGate, "grant_approval",
        lambda *args, **kwargs: pytest.fail("fingerprinting attempted a grant"),
    )
    request = _request()
    actual = p.owned_training_phase_fingerprints(
        request, actor_id=17, domain_id="cth", context=_GLOBAL_CTH,
    )

    descriptor = [{
        "scope": "GLOBAL / ALL", "domain_id": "cth", "product_id": "CTH",
        "global_scope": True, "subject_id": None, "brand_focus_id": None,
    }]
    expected = {
        "request_sha256": _canonical_digest({
            "schema_version": 1, "operation": "model_train", "domain_id": "cth",
            "model_id": "openai/gpt-oss-20b",
            "model_revision": "6cee5e81ee83917806bbde320786a8fb61efebee",
            "recipe": "openai-h100-bf16", "manifest_sha256": "3" * 64,
            "train_sha256": "1" * 64, "heldout_sha256": "2" * 64,
            "scopes": ["GLOBAL / ALL"], "scope_descriptors": descriptor,
        }),
        "model_identity_sha256": _canonical_digest({
            "schema_version": 1, "model_id": "openai/gpt-oss-20b",
            "model_revision": "6cee5e81ee83917806bbde320786a8fb61efebee",
        }),
        "manifest_sha256": "3" * 64,
        "train_sha256": "1" * 64,
        "heldout_sha256": "2" * 64,
        "recipe_sha256": _canonical_digest({
            "schema_version": 1, "recipe": "openai-h100-bf16",
        }),
        "scope_sha256": _canonical_digest({
            "schema_version": 1, "domain_id": "cth",
            "scopes": ["GLOBAL / ALL"], "scope_descriptors": descriptor,
        }),
    }
    assert expected == {
        "request_sha256": "cd810e6960b564d95ee34b912ce07b94442281ee019201e3e95d1c1ffccbce5d",
        "model_identity_sha256": "c2bbcdb92e790fbd62cef5a94d1939323a51d9e116c1929f132f95fd274b04b5",
        "manifest_sha256": "3" * 64,
        "train_sha256": "1" * 64,
        "heldout_sha256": "2" * 64,
        "recipe_sha256": "91be2da7a3f2fc099a1d50451c0e0f082e651b8558545decba3284b15b3fdb0b",
        "scope_sha256": "e38877153199a4070bfb96f6a2ac403b00ba8a096fd1a01a7e7b6c55402ce52e",
    }
    assert actual == expected


@pytest.mark.parametrize(
    ("change", "changed_keys"),
    [
        ({"model_revision": "a" * 40}, {"request_sha256", "model_identity_sha256"}),
        ({"recipe": "unsloth-t4-nf4"}, {"request_sha256", "recipe_sha256"}),
        ({"manifest_sha256": "4" * 64}, {"request_sha256", "manifest_sha256"}),
        ({"train_sha256": "5" * 64}, {"request_sha256", "train_sha256"}),
        ({"heldout_sha256": "6" * 64}, {"request_sha256", "heldout_sha256"}),
    ],
)
def test_request_tampering_changes_only_its_bound_fingerprints(change, changed_keys):
    baseline = p.owned_training_phase_fingerprints(
        _request(), actor_id=17, domain_id="cth", context=_GLOBAL_CTH,
    )
    altered = p.owned_training_phase_fingerprints(
        _request(**change), actor_id=17, domain_id="cth", context=_GLOBAL_CTH,
    )
    assert {key for key in baseline if baseline[key] != altered[key]} == changed_keys


def test_scope_and_identity_are_separate_bindings():
    request = _request()
    first = p.owned_training_phase_fingerprints(
        request, actor_id=17, domain_id="cth", context=_GLOBAL_CTH,
    )
    second_actor = p.owned_training_phase_fingerprints(
        request, actor_id=18, domain_id="cth", context=_GLOBAL_CTH,
    )
    first_resource = p.owned_training_approval_resource(
        request, actor_id=17, domain_id="cth", context=_GLOBAL_CTH,
    )
    second_resource = p.owned_training_approval_resource(
        request, actor_id=18, domain_id="cth", context=_GLOBAL_CTH,
    )
    assert first == second_actor
    assert first_resource != second_resource

    focused = TrainingApprovalRequest(
        **{**request.__dict__, "scopes": ("SUBJ-CTH-A",)}
    )
    focused_context = {"scope_descriptors": {"SUBJ-CTH-A": {
        "domain_id": "cth", "product_id": "CTH", "global_scope": False,
        "subject_id": "SUBJ-CTH-A", "brand_focus_id": None,
    }}}
    changed_scope = p.owned_training_phase_fingerprints(
        focused, actor_id=17, domain_id="cth", context=focused_context,
    )
    assert changed_scope["scope_sha256"] != first["scope_sha256"]
    assert changed_scope["request_sha256"] != first["request_sha256"]
    assert changed_scope["model_identity_sha256"] == first["model_identity_sha256"]
    assert changed_scope["recipe_sha256"] == first["recipe_sha256"]


def test_rejects_missing_identity_and_cross_domain_scope():
    with pytest.raises(ValueError):
        p.owned_training_phase_fingerprints(
            _request(), domain_id="cth", context=_GLOBAL_CTH,
        )

    cross_domain = {"scope_descriptors": {"GLOBAL / ALL": {
        **_GLOBAL_CTH["scope_descriptors"]["GLOBAL / ALL"],
        "domain_id": "bmp", "product_id": "ZBMP",
    }}}
    with pytest.raises(ValueError):
        p.owned_training_phase_fingerprints(
            _request(), actor_id=17, domain_id="cth", context=cross_domain,
        )

    mismatched_request = replace(_request(), domain_id="bmp")
    with pytest.raises(ValueError):
        p.owned_training_phase_fingerprints(
            mismatched_request, actor_id=17, domain_id="cth", context=_GLOBAL_CTH,
        )
