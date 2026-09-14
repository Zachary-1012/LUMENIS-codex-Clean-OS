"""Canonical page routing for the LUMENIS product shell.

The repository still contains historical Jinja page handlers under
``/lumenis/*`` for compatibility and source recovery.  They are not allowed
to become the product UI again.  This module is intentionally pure so the
cutover contract can be tested without importing the full application or
touching a database.
"""
from __future__ import annotations


# Compatibility APIs and probes keep their existing contracts.  Only page
# navigation is cut over to Experience V2.
COMPATIBLE_LUMENIS_PREFIXES = (
    "/lumenis/api/",
    "/lumenis/static/",
)
COMPATIBLE_LUMENIS_PATHS = frozenset({
    "/lumenis/healthz",
})


LEGACY_LUMENIS_SCREEN_ROUTES = {
    "/lumenis": "AI-01",
    "/lumenis/ai": "AI-01",
    "/lumenis/cth": "CTH-01",
    "/lumenis/cth/overview": "CTH-01",
    "/lumenis/cth/realtime": "CTH-03",
    "/lumenis/cth/topics": "CTH-04",
    "/lumenis/cth/events": "CTH-04",
    "/lumenis/cth/risk": "CTH-09",
    "/lumenis/cth/brands": "CTH-02",
    "/lumenis/cth/industries": "CTH-02",
    "/lumenis/cth/xiaohongshu": "CTH-03",
    "/lumenis/cth/kos": "CTH-02",
    "/lumenis/cth/reports": "CTH-10",
    "/lumenis/cth/evidence": "CTH-10",
    "/lumenis/cth/brand-industry": "CTH-02",
    "/lumenis/cth/trend": "CTH-07",
    "/lumenis/cth/topic-campaign": "CTH-04",
    "/lumenis/cth/weekly": "CTH-10",
    "/lumenis/cth/weibo": "CTH-03",
    "/lumenis/cth/workspace": "AI-02",
    "/lumenis/cth/data-center": "CTH-03",
    "/lumenis/cth/qa": "AI-03",
    "/lumenis/cth/negative": "CTH-06",
    "/lumenis/cth/official": "CTH-03",
    "/lumenis/cth/event-graph": "CTH-04",
    "/lumenis/cth/calendar": "CTH-05",
    "/lumenis/cth/analysis": "CTH-07",
    "/lumenis/cth/cases": "CTH-08",
    "/lumenis/cth/case-analysis": "CTH-08",
    "/lumenis/cth/knowledge": "CTH-08",
    "/lumenis/cth/notes": "CTH-03",
    "/lumenis/cth/launch": "CTH-01",
    "/lumenis/zbmp": "BMP-01",
    "/lumenis/zbmp/overview": "BMP-01",
    "/lumenis/zbmp/intelligence": "BMP-03",
    "/lumenis/zbmp/brand": "BMP-02",
    "/lumenis/zbmp/content": "SH-01",
    "/lumenis/zbmp/podcast": "BMP-08",
    "/lumenis/zbmp/kos": "BMP-05",
    "/lumenis/zbmp/competition": "BMP-11",
    "/lumenis/zbmp/risk": "BMP-10",
    "/lumenis/zbmp/reports": "BMP-09",
    "/lumenis/zbmp/evaluation": "BMP-09",
    "/lumenis/zbmp/launch": "BMP-01",
    "/lumenis/system/runtime": "SYS-01",
    "/lumenis/system/collector": "SYS-02",
    "/lumenis/system/browser": "SYS-06",
    "/lumenis/system/ai": "AI-01",
    "/lumenis/system/database": "SYS-03",
    "/lumenis/system/security": "SYS-04",
    "/lumenis/system/evaluation": "SYS-07",
    "/lumenis/system/adaptive-demo": "SYS-08",
    "/lumenis/intelligence": "AI-03",
}


def canonical_screen_for_lumenis_path(path: str | None) -> str | None:
    """Return the Experience V2 screen for a legacy page path.

    ``None`` means the path is a compatibility API/static/probe and must not
    be redirected.  Unknown historical page paths still enter the canonical
    LUMENIS AI home rather than rendering an old template.
    """
    raw = str(path or "").split("?", 1)[0]
    normalized = "/" + raw.lstrip("/")
    if normalized != "/lumenis":
        normalized = normalized.rstrip("/")

    if normalized in COMPATIBLE_LUMENIS_PATHS:
        return None
    if any(normalized.startswith(prefix) for prefix in COMPATIBLE_LUMENIS_PREFIXES):
        return None
    if normalized == "/lumenis" or normalized == "/lumenis/":
        return "AI-01"
    if normalized in LEGACY_LUMENIS_SCREEN_ROUTES:
        return LEGACY_LUMENIS_SCREEN_ROUTES[normalized]
    if normalized.startswith("/lumenis/cth/"):
        return "CTH-01"
    if normalized.startswith("/lumenis/zbmp/"):
        return "BMP-01"
    if normalized.startswith("/lumenis/system/"):
        return "SYS-05"
    if normalized.startswith("/lumenis/"):
        return "AI-01"
    return None
