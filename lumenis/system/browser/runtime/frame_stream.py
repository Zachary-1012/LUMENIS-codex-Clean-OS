# -*- coding: utf-8 -*-
"""SYSTEM Browser Runtime: live frame stream over SSE for an isolated session.

Single owner: ``lumenis.system.browser.runtime``.  The CDP screencast for
platform accounts lives in ``screencast_stream`` (moved from repo-root
``internal_browser_stream.py``); this module streams frames of the isolated
``/api/browser/sessions/<id>`` page to its authorized human viewer only.

PO defaults (sys06-browser-research.md decisions, 2026-10-13):
  * "this page is AI-readable" defaults OFF; nothing reaches Evidence unless
    the page is registered.
  * Sensitive / logged-in pages: when the user leaves the view, the agent is
    paused (default ON).  Login state is not reliably known, so unknown counts
    as logged-in (fail closed).
  * During human takeover no frame goes to AI and no frame is stored; only
    action receipts are kept by the existing human-control path.
  * Sessions are isolated from the personal browser and carry no personal
    cookies.
Frames produced here are held in memory for one SSE write and never persisted.
"""
from __future__ import annotations

import base64
import json
import threading
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, Iterator, Optional, Tuple
from urllib.parse import urlsplit

SENSITIVE_URL_MARKERS: Tuple[str, ...] = (
    "login", "signin", "sign-in", "logon", "passport", "account", "auth",
    "sso", "oauth", "bank", "pay", "wallet", "checkout", "password",
)


@dataclass(frozen=True)
class BrowserStreamPolicy:
    page_ai_readable: bool = False
    evidence_requires_registration: bool = True
    pause_agent_when_user_leaves_sensitive: bool = True
    frames_to_ai_during_human_control: bool = False
    store_frames_during_human_control: bool = False
    human_control_keeps_action_receipts: bool = True
    isolated_session: bool = True
    personal_cookies: bool = False

    def to_dict(self) -> Dict[str, bool]:
        return asdict(self)


DEFAULT_POLICY = BrowserStreamPolicy()


def is_sensitive_page(url: Optional[str], logged_in: Optional[bool] = None) -> bool:
    """Fail closed: unknown login state is treated as logged in."""
    if logged_in is None or logged_in:
        return True
    lowered = (url or "").lower()
    try:
        parts = urlsplit(lowered)
        haystack = f"{parts.netloc}{parts.path}"
    except ValueError:
        return True
    return any(marker in haystack for marker in SENSITIVE_URL_MARKERS)


def frame_may_reach_ai(policy: BrowserStreamPolicy, *, human_control_active: bool,
                       page_registered: bool, page_ai_readable: Optional[bool] = None) -> bool:
    if human_control_active:
        return policy.frames_to_ai_during_human_control
    readable = policy.page_ai_readable if page_ai_readable is None else bool(page_ai_readable)
    return readable and bool(page_registered)


def frame_may_be_stored(policy: BrowserStreamPolicy, *, human_control_active: bool,
                        page_registered: bool) -> bool:
    if human_control_active:
        return policy.store_frames_during_human_control
    if policy.evidence_requires_registration:
        return bool(page_registered)
    return False


class ViewerPresence:
    """Tracks live viewers per session and the agent pause caused by leaving."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._viewers: Dict[str, int] = {}
        self._paused: Dict[str, str] = {}

    def enter(self, session_id: str) -> None:
        with self._lock:
            self._viewers[session_id] = self._viewers.get(session_id, 0) + 1
            self._paused.pop(session_id, None)

    def leave(self, session_id: str, *, sensitive: bool,
              policy: BrowserStreamPolicy = DEFAULT_POLICY) -> None:
        with self._lock:
            count = max(0, self._viewers.get(session_id, 0) - 1)
            if count:
                self._viewers[session_id] = count
                return
            self._viewers.pop(session_id, None)
            if sensitive and policy.pause_agent_when_user_leaves_sensitive:
                self._paused[session_id] = "USER_LEFT_VIEW"

    def viewers(self, session_id: str) -> int:
        with self._lock:
            return self._viewers.get(session_id, 0)

    def agent_pause_reason(self, session_id: str) -> Optional[str]:
        with self._lock:
            return self._paused.get(session_id)

    def forget(self, session_id: str) -> None:
        with self._lock:
            self._viewers.pop(session_id, None)
            self._paused.pop(session_id, None)


PRESENCE = ViewerPresence()


def _event(payload: Dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def iter_frame_events(
    session: Any,
    *,
    is_running: Callable[[Any], bool],
    human_control_active: Callable[[Any], bool],
    pending_errors: Tuple[type, ...] = (),
    empty_errors: Tuple[type, ...] = (),
    authorize: Optional[Callable[[], bool]] = None,
    document_url: Optional[Callable[[Any], Optional[str]]] = None,
    authorize_every_seconds: float = 1.0,
    clock: Callable[[], float] = time.monotonic,
    policy: BrowserStreamPolicy = DEFAULT_POLICY,
    presence: ViewerPresence = PRESENCE,
    interval_seconds: float = 0.2,
    max_frames: Optional[int] = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Iterator[str]:
    """Yield SSE events with fresh frames of ``session`` for its human viewer.

    The stream ends (never silently continues) when the session stops or
    expires, authorization is lost, a human-control lease starts (no capture
    may replace the lease-bound frame), or the document navigates on its own.
    """
    session_id = str(session.session_id)
    presence.enter(session_id)
    sent = 0
    first_document: Optional[str] = None
    last_authorized = clock()
    try:
        yield "retry: 3000\n\n"
        yield _event({"t": "policy", "policy": policy.to_dict()})
        while True:
            if not is_running(session):
                yield _event({"t": "state", "state": "STOPPED"})
                return
            if authorize is not None and clock() - last_authorized >= authorize_every_seconds:
                try:
                    allowed = bool(authorize())
                except Exception:
                    allowed = False
                if not allowed:
                    yield _event({"t": "state", "state": "UNAUTHORIZED"})
                    return
                last_authorized = clock()
            human = bool(human_control_active(session))
            if human:
                # No capture during a lease: each capture would replace the
                # binding that authorizes human input, and takeover frames must
                # not reach AI or storage.
                yield _event({"t": "state", "state": "HUMAN_CONTROL"})
                return
            try:
                frame = session.capture_frame()
            except pending_errors:
                yield _event({"t": "state", "state": "PENDING"})
                sleep(interval_seconds)
                continue
            except empty_errors:
                yield _event({"t": "state", "state": "EMPTY"})
                sleep(interval_seconds)
                continue
            except Exception:
                yield _event({"t": "state", "state": "UNAVAILABLE"})
                return
            if document_url is not None:
                current_document = document_url(session)
                if first_document is None:
                    first_document = current_document
                elif current_document != first_document:
                    del frame
                    yield _event({"t": "state", "state": "NAVIGATED"})
                    return
            viewport = frame.get("viewport") or {}
            yield _event({
                "t": "frame",
                "frame_id": frame["frame_id"],
                "target_id": frame["target_id"],
                "page_revision": frame["page_revision"],
                "captured_at": frame["captured_at"],
                "width": frame["width"],
                "height": frame["height"],
                "viewport": {
                    "width": viewport.get("width"),
                    "height": viewport.get("height"),
                    "dpr": viewport.get("dpr"),
                },
                "mime": "image/png",
                "data": base64.b64encode(frame["image"]).decode("ascii"),
                "human_control_active": human,
                "ai_readable": frame_may_reach_ai(policy, human_control_active=human,
                                                  page_registered=False),
                "stored": False,
            })
            del frame
            sent += 1
            if max_frames is not None and sent >= max_frames:
                return
            sleep(interval_seconds)
    finally:
        url = getattr(session, "current_url", None)
        if callable(url):
            try:
                url = url()
            except Exception:
                url = None
        presence.leave(session_id, sensitive=is_sensitive_page(url if isinstance(url, str) else None),
                       policy=policy)
