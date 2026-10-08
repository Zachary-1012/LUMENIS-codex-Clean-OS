"""Compatibility state reads must never access Cookie/profile material."""
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def metadata_owner(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1] / "weibo_login_manager.py"
    spec = importlib.util.spec_from_file_location("metadata_owner_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "__file__", str(tmp_path / "weibo_login_manager.py"))
    data = tmp_path / "data"
    data.mkdir()
    original = Path.read_text
    def read_state_only(path, *args, **kwargs):
        assert path.name == "weibo_login_status.json", "Cookie or profile read is forbidden"
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", read_state_only)
    return module.WeiboLoginManager, data


def test_missing_saved_state_is_unavailable_without_profile_creation(metadata_owner):
    owner, data = metadata_owner
    result = owner.read_saved_session_metadata()
    assert result == {"state": "NOT_AVAILABLE", "saved_logged_in": None,
                      "cookie_count": None, "last_login": None}
    assert list(data.iterdir()) == []


def test_saved_state_filters_secret_fields_and_is_not_live_verification(metadata_owner):
    owner, data = metadata_owner
    (data / "weibo_login_status.json").write_text(json.dumps({
        "logged_in": True, "cookie_count": 0, "last_login": "2026-10-08 09:00:00",
        "cookie_string": "test-only-secret-sentinel", "profile": "/test-only-profile",
    }), encoding="utf-8")
    result = owner.read_saved_session_metadata()
    assert result == {"state": "UNVERIFIED", "saved_logged_in": True,
                      "cookie_count": 0, "last_login": "2026-10-08 09:00:00"}
    assert "test-only-secret-sentinel" not in json.dumps(result)
    assert not (data / "weibo_profile").exists()


@pytest.mark.parametrize("count", [None, True, -1, "3", 1.5])
def test_unknown_or_invalid_count_is_not_zero(metadata_owner, count):
    owner, data = metadata_owner
    (data / "weibo_login_status.json").write_text(json.dumps({"cookie_count": count}), encoding="utf-8")
    assert owner.read_saved_session_metadata()["cookie_count"] is None


@pytest.mark.parametrize("raw", ["not json", "[]", '{"last_login":"not a timestamp"}', "x" * 65537],
                         ids=["malformed-json", "wrong-type", "invalid-timestamp", "oversized"])
def test_invalid_state_has_honest_error(metadata_owner, raw):
    owner, data = metadata_owner
    (data / "weibo_login_status.json").write_text(raw, encoding="utf-8")
    assert owner.read_saved_session_metadata() == {
        "state": "ERROR", "saved_logged_in": None, "cookie_count": None, "last_login": None,
    }
