"""Real Git inventory preserves UTF-8, spaces and newlines without changing Git configuration."""
import subprocess
from pathlib import Path

import pytest

from tests.browser_runtime import test_browser_frame_stream as inventory


def _repository(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


@pytest.mark.parametrize("relative", [
    "deployment/健康检查.py",
    "deployment/file with spaces.py",
    "deployment/line\nbreak.py",
])
def test_real_git_inventory_preserves_complete_paths(tmp_path, monkeypatch, relative):
    root = _repository(tmp_path)
    source = root / relative
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("value = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "--", relative], cwd=root, check=True)
    monkeypatch.setattr(inventory, "ROOT", root)
    inventory.test_no_screencast_stream_module_outside_owner()
    assert source.read_text(encoding="utf-8") == "value = 1\n"
    assert subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=root,
                          capture_output=True).returncode != 0


def test_real_git_inventory_still_detects_untracked_foreign_owner(tmp_path, monkeypatch):
    root = _repository(tmp_path)
    source = root / "deployment" / "异常\nnew owner.py"
    source.parent.mkdir(parents=True)
    source.write_text("value = 'Page.startScreencast'\n", encoding="utf-8")
    monkeypatch.setattr(inventory, "ROOT", root)
    with pytest.raises(AssertionError):
        inventory.test_no_screencast_stream_module_outside_owner()
