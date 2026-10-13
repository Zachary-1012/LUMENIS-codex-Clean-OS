# -*- coding: utf-8 -*-
"""Contract tests: browser screencast move, SSE frame stream and PO defaults."""
from __future__ import annotations

import base64
import importlib
import json
import subprocess
from pathlib import Path

import pytest

from lumenis.system.browser.runtime import frame_stream as fs

ROOT = Path(__file__).resolve().parents[2]
OWNER = Path("lumenis/system/browser/runtime")
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


class _Pending(Exception):
    pass


class _FakeSession:
    def __init__(self, session_id="bs_test", human=False, frames=3, pending_first=False,
                 url="https://example.com/page"):
        self.session_id = session_id
        self.human = human
        self.remaining = frames
        self.pending_first = pending_first
        self.current_url = url
        self.captures = 0

    @property
    def evidence_store(self):  # any Evidence write would fail the test
        raise AssertionError("frame stream must not touch Evidence")

    def capture_frame(self):
        self.captures += 1
        if self.pending_first and self.captures == 1:
            raise _Pending()
        self.remaining -= 1
        return {"frame_id": f"bf_{self.captures}", "target_id": "t1", "page_revision": 2,
                "captured_at": "2026-10-13T08:00:00+00:00", "width": 8, "height": 8,
                "viewport": {"width": 8, "height": 8, "dpr": 1.0}, "image": PNG}


def _events(session, presence, **kw):
    out = []
    for chunk in fs.iter_frame_events(
        session, is_running=lambda s: s.remaining > 0,
        human_control_active=lambda s: s.human, pending_errors=(_Pending,),
        presence=presence, sleep=lambda _s: None, **kw,
    ):
        if chunk.startswith("data: "):
            out.append(json.loads(chunk[6:]))
    return out


def test_po_defaults():
    p = fs.DEFAULT_POLICY
    assert p.page_ai_readable is False
    assert p.evidence_requires_registration is True
    assert p.pause_agent_when_user_leaves_sensitive is True
    assert p.frames_to_ai_during_human_control is False
    assert p.store_frames_during_human_control is False
    assert p.human_control_keeps_action_receipts is True
    assert p.isolated_session is True and p.personal_cookies is False


def test_ai_and_store_gates():
    p = fs.DEFAULT_POLICY
    assert not fs.frame_may_reach_ai(p, human_control_active=False, page_registered=True)
    assert not fs.frame_may_reach_ai(p, human_control_active=False, page_registered=False,
                                     page_ai_readable=True)
    assert fs.frame_may_reach_ai(p, human_control_active=False, page_registered=True,
                                 page_ai_readable=True)
    assert not fs.frame_may_reach_ai(p, human_control_active=True, page_registered=True,
                                     page_ai_readable=True)
    assert not fs.frame_may_be_stored(p, human_control_active=False, page_registered=False)
    assert fs.frame_may_be_stored(p, human_control_active=False, page_registered=True)
    assert not fs.frame_may_be_stored(p, human_control_active=True, page_registered=True)


def test_sensitive_fail_closed():
    assert fs.is_sensitive_page("https://example.com/x") is True  # login unknown
    assert fs.is_sensitive_page("https://example.com/x", logged_in=False) is False
    assert fs.is_sensitive_page("https://bank.example.com/", logged_in=False) is True
    assert fs.is_sensitive_page("https://a.com/login", logged_in=False) is True


def test_stream_emits_frames_never_stored_or_ai():
    presence = fs.ViewerPresence()
    events = _events(_FakeSession(frames=3), presence)
    assert events[0]["t"] == "policy" and events[0]["policy"]["page_ai_readable"] is False
    frames = [e for e in events if e["t"] == "frame"]
    assert len(frames) == 3
    for f in frames:
        assert base64.b64decode(f["data"]) == PNG
        assert f["stored"] is False and f["ai_readable"] is False
    assert events[-1] == {"t": "state", "state": "STOPPED"}


def test_human_takeover_stops_capture():
    presence = fs.ViewerPresence()
    session = _FakeSession(human=True, frames=2)
    events = _events(session, presence)
    assert session.captures == 0
    assert not [e for e in events if e["t"] == "frame"]
    assert events[-1] == {"t": "state", "state": "HUMAN_CONTROL"}


def test_lost_authorization_ends_stream():
    presence = fs.ViewerPresence()
    ticks = iter(range(100))
    allowed = iter([True, False])
    session = _FakeSession(frames=50)
    events = _events(session, presence, authorize=lambda: next(allowed),
                     authorize_every_seconds=1.0, clock=lambda: float(next(ticks)))
    assert events[-1] == {"t": "state", "state": "UNAUTHORIZED"}
    assert session.captures < 50


def test_self_navigation_ends_stream_without_emitting_new_document():
    presence = fs.ViewerPresence()
    session = _FakeSession(frames=5)
    urls = iter(["https://a.example/", "https://a.example/", "https://b.example/"])
    events = _events(session, presence, document_url=lambda s: next(urls))
    frames = [e for e in events if e["t"] == "frame"]
    assert len(frames) == 2
    assert events[-1] == {"t": "state", "state": "NAVIGATED"}


def test_expired_session_ends_stream():
    presence = fs.ViewerPresence()
    session = _FakeSession(frames=50)
    alive = iter([True, True, False])
    events = _events(session, presence, ) if False else [
        __import__("json").loads(c[6:]) for c in fs.iter_frame_events(
            session, is_running=lambda s: next(alive), human_control_active=lambda s: False,
            presence=presence, sleep=lambda _s: None) if c.startswith("data: ")]
    assert [e["t"] for e in events].count("frame") == 2
    assert events[-1] == {"t": "state", "state": "STOPPED"}


def test_pending_frame_reports_state_and_continues():
    presence = fs.ViewerPresence()
    events = _events(_FakeSession(frames=1, pending_first=True), presence)
    assert {"t": "state", "state": "PENDING"} in events
    assert any(e["t"] == "frame" for e in events)


def test_leaving_view_pauses_agent_and_returning_clears():
    presence = fs.ViewerPresence()
    _events(_FakeSession(session_id="bs_a", frames=1), presence)
    assert presence.viewers("bs_a") == 0
    assert presence.agent_pause_reason("bs_a") == "USER_LEFT_VIEW"
    presence.enter("bs_a")
    assert presence.agent_pause_reason("bs_a") is None


def test_early_disconnect_also_pauses():
    presence = fs.ViewerPresence()
    gen = fs.iter_frame_events(_FakeSession(session_id="bs_b", frames=99),
                               is_running=lambda s: True, human_control_active=lambda s: False,
                               presence=presence, sleep=lambda _s: None)
    next(gen); next(gen); next(gen)
    assert presence.viewers("bs_b") == 1
    gen.close()
    assert presence.agent_pause_reason("bs_b") == "USER_LEFT_VIEW"


def test_root_stream_module_moved_to_single_owner():
    assert not (ROOT / "internal_browser_stream.py").exists()
    assert (ROOT / OWNER / "screencast_stream.py").exists()
    import sys
    sys.path.insert(0, str(ROOT))
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("internal_browser_stream")
    mod = importlib.import_module("lumenis.system.browser.runtime.screencast_stream")
    assert hasattr(mod, "ScreencastManager") and hasattr(mod, "register_stream")
    app_src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "import internal_browser_stream\n" not in app_src.replace("\r\n", "\n")
    assert "lumenis.system.browser.runtime import screencast_stream" in app_src


def test_no_screencast_stream_module_outside_owner():
    out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "--", "*.py"],
                         cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True)
    offenders = []
    for rel in out.stdout.splitlines():
        p = Path(rel)
        if p.parts[:1] in {("tests",), (".codex",), (".venv",), ("node_modules",), ("intelligence_library",)}:
            continue
        if Path(*p.parts[:4]) == OWNER:
            continue
        full = ROOT / p
        if not full.is_file():
            continue
        try:
            text = full.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "Page.startScreencast" in text or "text/event-stream" in text and "screencastFrame" in text:
            offenders.append(rel)
    assert offenders == []


def test_core_session_stream_routes_registered_and_allowlisted():
    src = (ROOT / "ai_browser_api.py").read_text(encoding="utf-8")
    assert '"/api/browser/sessions/<session_id>/frames/stream"' in src
    assert '"/api/browser/sessions/<session_id>/stream-policy"' in src
    assert "AGENT_PAUSED_USER_LEFT_VIEW" in src
    assert "_still_authorized" in src and "is_alive" in src
    app_src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "'ai_browser_runtime.stream_session_frames': {'GET'}" in app_src
    assert "'ai_browser_runtime.stream_policy': {'GET'}" in app_src


def test_core_routes_live_on_flask_app():
    flask = pytest.importorskip("flask")
    import sys
    sys.path.insert(0, str(ROOT))
    try:
        import ai_browser_api
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"ai_browser_api import unavailable: {exc}")
    app = flask.Flask(__name__)
    ai_browser_api.register_ai_browser_api(app)
    rules = {r.rule: r.endpoint for r in app.url_map.iter_rules()}
    assert rules["/api/browser/sessions/<session_id>/frames/stream"] == "ai_browser_runtime.stream_session_frames"
    assert rules["/api/browser/sessions/<session_id>/stream-policy"] == "ai_browser_runtime.stream_policy"
