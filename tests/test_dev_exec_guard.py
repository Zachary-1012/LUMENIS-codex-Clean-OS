"""App-only boundary: legacy arbitrary code execution endpoints are retired."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_legacy_dev_execution_routes_are_not_registered():
    import app
    rules = {rule.rule for rule in app.app.url_map.iter_rules()}
    for route in ("/api/developer/run", "/api/config/run-code", "/api/dev/run-code"):
        assert route not in rules
