"""Contract checks for the legacy function-map inventory."""

import json
import re
from pathlib import Path


def test_function_map_classifies_compatibility_inventory_against_current_routes(app):
    repo_root = Path(__file__).resolve().parents[1]
    function_map = json.loads((repo_root / "function_map.json").read_text(encoding="utf-8"))
    authority = function_map["authority"]

    assert authority["classification"] == "LEGACY_COMPATIBILITY_INVENTORY"
    assert authority["runtime_route_truth"] == "current Flask app.url_map"
    assert authority["product_skill_store_canonical_owner"] == "lumenis/shared/agents/skills"
    assert authority["is_skill_availability_registry"] is False
    assert authority["is_production_truth"] is False

    from openapi_spec import flask_rule_to_path

    current_routes = {
        (flask_rule_to_path(rule), method.upper())
        for rule in app.url_map.iter_rules()
        for method in rule.methods
        if method not in {"HEAD", "OPTIONS"}
    }
    functions = function_map["functions"]
    assert len(functions) == 30

    exact = []
    unmatched = []
    for name, entry in functions.items():
        resolution = entry.get("resolution", {})
        status = resolution.get("status", "UNCLASSIFIED")
        path = re.sub(r"<([^<>]+)>", r"{\1}", entry["endpoint"])
        route_key = (path, entry["method"].upper())

        if status == "EXACT_CURRENT_ROUTE":
            assert route_key in current_routes, name
            exact.append(name)
        else:
            assert status in {"BLOCKED", "DEFERRED_POST_LAUNCH"}, name
            assert route_key not in current_routes, name
            for field in ("canonical_owner_family", "scheduled_round", "milestone", "reason"):
                assert isinstance(resolution.get(field), str) and resolution[field].strip(), (name, field)
            unmatched.append(name)

    assert len(exact) == 19
    assert len(unmatched) == 11
    assert len(exact) + len(unmatched) == len(functions)
