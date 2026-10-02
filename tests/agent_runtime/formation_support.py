"""Declared unit-test implementations; these fixtures are not product evidence."""
from agent_capability.formation import BoundToolExecutor


def unit_identity():
    # Callback counters/results are test observations, not safety configuration.
    return {"configuration": {"fixture": True}, "environment": {"external_effects": False},
            "origin_scope_id": "unit-test-owner-v1", "implementation_revision": "unit-test-v1",
            "available": True}


def trusted_test_executor(callback):
    return BoundToolExecutor(callback, origin="lumenis-unit-tests",
                             resource_uri="tool://unit-test-direct-callback",
                             identity_provider=unit_identity)
