"""Multi-surface guard: retired browser asset roots must stay absent."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def test_legacy_browser_asset_roots_are_absent():
    assert not (ROOT / "templates").exists()
    assert not (ROOT / "static").exists()
    assert not (ROOT / "experience_v2").exists()
