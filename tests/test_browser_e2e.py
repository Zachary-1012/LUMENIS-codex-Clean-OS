"""Guard the retired personal-browser entrypoint during test discovery.

The historical script in Git history executed a 9222 CDP connection at module
import time. That identity is prohibited for LUMENIS startup, tests and E2E.
This safety regression does not stand in for the pending real-user SYS-06 E2E.
"""

import pytest

import browser_surface
from ai_browser_runtime import BrowserSessionManager


def test_retired_personal_cdp_port_is_unavailable_to_product_and_ai_browser():
    with pytest.raises(PermissionError, match="POLICY_BLOCKED: unregistered browser endpoint"):
        browser_surface._resolve_port(port=9222)
    with pytest.raises(ValueError, match="isolated LUMENIS browser"):
        BrowserSessionManager().create_session(cdp_port=9222)
