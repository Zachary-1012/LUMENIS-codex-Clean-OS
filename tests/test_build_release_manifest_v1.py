# -*- coding: utf-8 -*-
import pytest

from scripts import build_release_manifest as builder


def test_builder_refuses_tracked_dirty_tree(monkeypatch):
    monkeypatch.setattr(builder, "_git", lambda *args: " M app.py")
    with pytest.raises(RuntimeError, match="dirty"):
        builder.build_manifest("release-test", "CUSTOMER_RELEASE")


def test_builder_binds_release_to_commit_and_tree(monkeypatch):
    def fake_git(*args):
        if args[0] == "status":
            return ""
        if args[-1] == "HEAD^{tree}":
            return "tree-digest"
        return "commit-digest"

    monkeypatch.setattr(builder, "_git", fake_git)
    manifest = builder.build_manifest("release-test", "ZBRAND_PLATFORM", "brand-a")

    assert manifest["schema_version"] == "lumenis.release-manifest.v1"
    assert manifest["release_id"] == "release-test"
    assert manifest["core_commit"] == "commit-digest"
    assert manifest["source_tree_digest"] == "tree-digest"
    assert manifest["product_mode"] == "ZBRAND_PLATFORM"
    assert manifest["profile_id"] == "brand-a"
