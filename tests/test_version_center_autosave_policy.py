import json

import pytest

from lumenis.version_center.git_manager import GitVersionManager
from lumenis.version_center import watcher


def _manager(tmp_path):
    root = tmp_path / "repo"
    (root / "data").mkdir(parents=True)
    return GitVersionManager(root)


def test_missing_config_disables_automatic_commit_and_push(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    monkeypatch.setattr(manager, "status", lambda: pytest.fail("status must not run"))

    config = manager.load_config()
    assert config["auto_commit"] is False
    assert config["auto_push"] is False
    assert manager.auto_save_if_changed()["skipped"] == "auto_commit_off"


@pytest.mark.parametrize("raw", [
    "{broken",
    '{"auto_commit":"true","auto_push":"true"}',
    '{"auto_commit":1,"auto_push":1}',
    '[true,true]',
])
def test_corrupt_or_non_boolean_config_fails_closed(tmp_path, monkeypatch, raw):
    manager = _manager(tmp_path)
    manager._cfg_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(manager, "status", lambda: pytest.fail("status must not run"))

    config = manager.load_config()
    assert config["auto_commit"] is False
    assert config["auto_push"] is False
    assert manager.auto_save_if_changed()["skipped"] == "auto_commit_off"


def test_save_config_does_not_coerce_non_boolean_enable_values(tmp_path):
    manager = _manager(tmp_path)

    saved = manager.save_config({"auto_commit": True, "auto_push": "true"})

    assert saved["auto_commit"] is True
    assert saved["auto_push"] is False
    assert json.loads(manager._cfg_path.read_text(encoding="utf-8")) == saved


def test_explicit_boolean_opt_in_keeps_local_autosave_path(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    manager._cfg_path.write_text(
        '{"auto_commit":true,"auto_push":true,"interval_minutes":30}',
        encoding="utf-8",
    )
    manager._boot_ts = 0
    calls = []
    monkeypatch.setattr(manager, "status", lambda: {"ok": True, "changed_count": 1})
    monkeypatch.setattr(
        manager,
        "save_version",
        lambda *args, **kwargs: calls.append((args, kwargs)) or {"ok": True},
    )

    result = manager.auto_save_if_changed(min_interval_sec=0)

    assert result == {"ok": True}
    assert len(calls) == 1
    assert calls[0][1]["do_push"] is True
    assert calls[0][1]["author"] == "auto-watch"


def test_non_boolean_auto_push_cannot_enable_push(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    manager._cfg_path.write_text(
        '{"auto_commit":true,"auto_push":"true"}',
        encoding="utf-8",
    )
    manager._boot_ts = 0
    calls = []
    monkeypatch.setattr(manager, "status", lambda: {"ok": True, "changed_count": 1})
    monkeypatch.setattr(
        manager,
        "save_version",
        lambda *args, **kwargs: calls.append((args, kwargs)) or {"ok": True},
    )

    manager.auto_save_if_changed(min_interval_sec=0)

    assert len(calls) == 1
    assert calls[0][1]["do_push"] is False


def test_watcher_does_not_create_thread_when_auto_commit_is_off(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    monkeypatch.delenv("ZBC_TEST_OFFLINE", raising=False)
    monkeypatch.setattr(watcher, "_watcher_started", False)
    monkeypatch.setattr(watcher, "gm", lambda: manager)
    monkeypatch.setattr(manager, "is_repo", lambda: pytest.fail("repo check must not run"))
    monkeypatch.setattr(
        watcher.threading,
        "Thread",
        lambda **kwargs: pytest.fail("background thread must not be created"),
    )

    assert watcher.start_version_watcher() is False


def test_watcher_loop_rechecks_config_and_skips_when_disabled(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    monkeypatch.setattr(watcher, "gm", lambda: manager)
    calls = []
    monkeypatch.setattr(
        manager,
        "auto_save_if_changed",
        lambda: calls.append("autosave"),
    )

    class StopLoop(BaseException):
        pass

    sleeps = 0

    def stop_after_one_check(_seconds):
        nonlocal sleeps
        sleeps += 1
        if sleeps > 1:
            raise StopLoop

    monkeypatch.setattr(watcher.time, "sleep", stop_after_one_check)
    with pytest.raises(StopLoop):
        watcher._loop()

    assert calls == []
