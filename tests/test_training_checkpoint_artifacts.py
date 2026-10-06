"""Storage-contract tests; toy bytes do not prove a model checkpoint or CUDA."""
import copy
import hashlib
import json
import os
import subprocess
import sys

import pytest

import shared_artifacts as owner
from lumenis.shared.database import get_repository


@pytest.fixture
def storage(tmp_path, monkeypatch):
    monkeypatch.setenv("ZBC_DB_PATH", str(tmp_path / "isolated.db"))
    monkeypatch.setenv("ZBC_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    root = owner.artifact_root()
    source = root / "owned-stage"
    source.mkdir(parents=True)
    (source / "checkpoint-1").mkdir()
    body = b"toy optimizer state, not a model checkpoint"
    (source / "checkpoint-1" / "optimizer.pt").write_bytes(body)
    inventory = {"schema_version": 1, "operation_id": "5e1cccd4-66be-455b-93f8-8c73b283d1c4",
        "completed_step": 1, "checkpoint_relative_path": "checkpoint-1", "policy_sha256": "a" * 64,
        "fingerprints": {}, "framework_versions": {}, "trainer_config_sha256": "b" * 64,
        "data_order_sha256": "c" * 64, "data_position": {},
        "files": [{"path": "checkpoint-1/optimizer.pt", "role": "optimizer", "size_bytes": len(body),
                   "sha256": hashlib.sha256(body).hexdigest()}]}
    binding = {"task_id": "task-test", "domain_id": "cth", "task_digest": "d" * 64,
        "operation_id": inventory["operation_id"], "attempt_id": "7ae18f8a-9ef5-4986-a87a-e897571433e1", "worker_epoch": 1,
        "actor_identity": {"actor_id": None, "caller": "workspace:local", "principal_kind": "local_workspace",
                           "principal_ref": "workspace:local"},
        "scope_descriptors": {"GLOBAL / ALL": {"domain_id": "cth", "subject_id": None,
                                              "brand_focus_id": None, "global_scope": True}},
        "artifact_version": 1, "parent_ref": None}
    owner.ensure_artifact_table()
    return source, inventory, binding


def stage(storage, **kwargs):
    source, inventory, binding = storage
    return owner.stage_training_checkpoint_artifact(source_root=source, inventory=inventory,
        binding=binding, max_bytes=4096, authorize=lambda: None, **kwargs)


def test_atomic_rollback_and_lost_ack_reopen_across_process(storage):
    staged = stage(storage)
    repo = get_repository()
    with repo.connection() as con:
        con.execute("BEGIN IMMEDIATE")
        owner.register_training_checkpoint_artifact(connection=con, staged=staged, authorize=lambda: None)
        con.rollback()
    with repo.connection(read_only=True, wal=False) as con:
        assert con.execute("SELECT COUNT(*) FROM lumenis_shared_artifacts").fetchone()[0] == 0
        with pytest.raises(owner.LocalArtifactError, match="CHECKPOINT_NOT_COMMITTED"):
            owner.read_training_checkpoint_artifact(connection=con, artifact_ref=staged["artifact_ref"],
                expected_sha256=staged["sha256"], authorize=lambda: None)
    with repo.transaction() as con:
        con.execute("BEGIN IMMEDIATE")
        record = owner.register_training_checkpoint_artifact(connection=con, staged=staged, authorize=lambda: None)
        assert con.in_transaction
    code = """import json,sys
from lumenis.shared.database import get_repository
from shared_artifacts import read_training_checkpoint_artifact
with get_repository().connection(read_only=True,wal=False) as con:
 r=read_training_checkpoint_artifact(connection=con,artifact_ref=sys.argv[1],expected_sha256=sys.argv[2],authorize=lambda:None)
 print(json.dumps({'ref':r['artifact_ref'],'bytes':(r['load_root']/'checkpoint-1/optimizer.pt').read_bytes().hex()}))
"""
    result = subprocess.run([sys.executable, "-c", code, staged["artifact_ref"], staged["sha256"]],
                            capture_output=True, text=True, check=True, env=os.environ.copy())
    assert json.loads(result.stdout)["ref"] == record["artifact_id"]
    assert owner.get_artifact(staged["artifact_ref"]) is None
    assert owner.artifact_file_path(staged["artifact_ref"]) is None


def test_exact_stage_and_registration_replay_adds_no_version(storage):
    staged = stage(storage, artifact_ref="ART-0123456789abcdef")
    assert stage(storage, artifact_ref=staged["artifact_ref"]) == staged
    with get_repository().transaction() as con:
        con.execute("BEGIN IMMEDIATE")
        one = owner.register_training_checkpoint_artifact(connection=con, staged=staged, authorize=lambda: None)
        two = owner.register_training_checkpoint_artifact(connection=con, staged=staged, authorize=lambda: None)
        assert one == two
        assert con.execute("SELECT COUNT(*) FROM lumenis_shared_artifacts").fetchone()[0] == 1


def test_changed_binding_cannot_replace_existing_stage(storage):
    staged = stage(storage)
    storage[2]["artifact_version"] = 2
    with pytest.raises(owner.LocalArtifactError, match="CHECKPOINT_OPERATION_CONFLICT"):
        stage(storage, artifact_ref=staged["artifact_ref"])


def test_tampered_bytes_block_transactional_registration(storage):
    staged = stage(storage)
    (owner.artifact_root() / staged["relative_path"]).parent.joinpath("checkpoint-1/optimizer.pt").write_bytes(b"changed")
    with get_repository().transaction() as con:
        con.execute("BEGIN IMMEDIATE")
        with pytest.raises(owner.LocalArtifactError, match="CHECKPOINT_INTEGRITY_FAILED"):
            owner.register_training_checkpoint_artifact(connection=con, staged=staged, authorize=lambda: None)
        assert con.execute("SELECT COUNT(*) FROM lumenis_shared_artifacts").fetchone()[0] == 0


@pytest.mark.parametrize("bad_path", ["../optimizer.pt", "checkpoint-1/NUL.pt", "checkpoint-1/optimizer.pt:stream"])
def test_paths_cannot_read_outside_inventory(storage, bad_path):
    storage[1]["files"][0]["path"] = bad_path
    with pytest.raises(owner.LocalArtifactError, match="CHECKPOINT_REQUEST_INVALID"):
        stage(storage)


def test_unlisted_files_and_byte_budget_are_rejected(storage):
    (storage[0] / "unlisted.txt").write_text("not inventoried")
    with pytest.raises(owner.LocalArtifactError, match="CHECKPOINT_INVENTORY_MISMATCH"):
        stage(storage)
    (storage[0] / "unlisted.txt").unlink()
    with pytest.raises(owner.LocalArtifactError, match="CHECKPOINT_STORAGE_LIMIT_EXCEEDED"):
        owner.stage_training_checkpoint_artifact(source_root=storage[0], inventory=storage[1], binding=storage[2],
                                                max_bytes=1, authorize=lambda: None)


def test_final_revocation_prevents_registry_write(storage):
    staged = stage(storage)
    calls = []
    def deny_final():
        calls.append(None)
        if len(calls) == 2:
            raise PermissionError("freshly revoked")
    with pytest.raises(PermissionError, match="freshly revoked"):
        with get_repository().transaction() as con:
            con.execute("BEGIN IMMEDIATE")
            owner.register_training_checkpoint_artifact(connection=con, staged=staged, authorize=deny_final)
    with get_repository().connection(read_only=True, wal=False) as con:
        assert con.execute("SELECT COUNT(*) FROM lumenis_shared_artifacts").fetchone()[0] == 0


def test_real_parent_and_next_version_are_required(storage):
    first = stage(storage)
    with get_repository().transaction() as con:
        con.execute("BEGIN IMMEDIATE")
        owner.register_training_checkpoint_artifact(connection=con, staged=first, authorize=lambda: None)
    storage[2]["parent_ref"] = first["artifact_ref"]
    storage[2]["artifact_version"] = 2
    second = stage(storage)
    with get_repository().transaction() as con:
        con.execute("BEGIN IMMEDIATE")
        owner.register_training_checkpoint_artifact(connection=con, staged=second, authorize=lambda: None)
    storage[2]["artifact_version"] = 4
    wrong = stage(storage)
    with get_repository().transaction() as con:
        con.execute("BEGIN IMMEDIATE")
        with pytest.raises(owner.LocalArtifactError, match="CHECKPOINT_PARENT_MISMATCH"):
            owner.register_training_checkpoint_artifact(connection=con, staged=wrong, authorize=lambda: None)


def test_owner_reserved_manifest_cannot_hide_an_unlisted_source(storage):
    (storage[0] / "checkpoint.manifest.json").write_text("not an owner manifest")
    with pytest.raises(owner.LocalArtifactError, match="CHECKPOINT_INVENTORY_MISMATCH"):
        stage(storage)
