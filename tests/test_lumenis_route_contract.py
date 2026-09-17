"""The legacy LUMENIS page paths must resolve to the canonical Experience UI."""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lumenis_route_contract import (  # noqa: E402
    canonical_screen_for_lumenis_path,
)


@pytest.mark.parametrize(
    ("path", "screen"),
    [
        ("/lumenis/", "AI-01"),
        ("/lumenis/cth/overview", "CTH-01"),
        ("/lumenis/cth/realtime/", "CTH-03"),
        ("/lumenis/zbmp/overview", "BMP-01"),
        ("/lumenis/zbmp/content", "SH-01"),
        ("/lumenis/system/browser", "SYS-06"),
        ("/lumenis/unknown-old-page", "AI-01"),
    ],
)
def test_legacy_page_routes_enter_experience_v2(path, screen):
    assert canonical_screen_for_lumenis_path(path) == screen


@pytest.mark.parametrize(
    "path",
    ["/lumenis/healthz", "/lumenis/api/skills/status", "/lumenis/static/legacy.css"],
)
def test_compatibility_paths_are_not_page_redirects(path):
    assert canonical_screen_for_lumenis_path(path) is None


def test_real_app_redirects_legacy_page_without_rendering_old_template(monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "_auth_enabled", lambda: False)
    client = app_module.app.test_client()
    response = client.get("/lumenis/cth/overview", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/experience/#/CTH-01")
    assert b"zbc-nav" not in response.data


def test_real_app_redirects_bmp_overview_without_rendering_old_template(monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "_auth_enabled", lambda: False)
    client = app_module.app.test_client()
    response = client.get("/lumenis/zbmp/overview", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/experience/#/BMP-01")
    assert b"zbc-nav" not in response.data
