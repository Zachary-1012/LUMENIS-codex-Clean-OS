"""Checked-in owned-foundation policy bindings; no model, GPU, or endpoint is used."""

import json

from lumenis.system.ai_gateway import owned_training as training
from lumenis.system.ai_gateway import owned_training_checkpoints as checkpoints


def test_checked_in_recipes_and_checkpoint_policies_are_loadable():
    manifest_path = training.APPROVED_MANIFEST_PATH
    manifest = json.loads(manifest_path.read_bytes())

    assert manifest["training_recipes"][training.ADA_RECIPE] == training.ADA_RECIPE_POLICY
    assert (
        manifest["training_recipes"][training.BLACKWELL_RECIPE]
        == training.BLACKWELL_RECIPE_POLICY
    )

    registry = manifest["checkpoint_recovery_policies"]
    assert registry["schema_version"] == 1
    assert registry["policies"]
    for pinned_hash, document in registry["policies"].items():
        policy = checkpoints.CheckpointPolicy.validate(document)
        assert policy.sha256 == pinned_hash
        assert checkpoints.load_recovery_policy(policy.recipe, manifest_path) == policy
