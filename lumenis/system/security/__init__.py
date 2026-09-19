"""LUMENIS SYSTEM Security canonical ownership boundary.

SYSTEM owns Permission, Action Firewall, Effect Fence and side-effect
idempotency. Domain and Agent runtimes consume this package; they do not own
parallel permission or effect-admission implementations.
"""
from .permission import (
    ApprovalToken,
    AuditEntry,
    OperationSpec,
    OperationType,
    PermissionGate,
    PermissionLevel,
    PermissionResult,
    RiskLevel,
    get_permission_gate,
    is_testing_bypass_enabled,
    require_permission,
    reset_permission_gate,
    set_testing_bypass,
)
from .action_firewall import (
    ActionRequest,
    AgentAction,
    FirewallResult,
    FirewallRisk,
    validate_action,
)
from .effect_fence import EffectFence, FenceDecision, get_effect_fence

__all__ = [
    "ApprovalToken", "AuditEntry", "OperationSpec", "OperationType",
    "PermissionGate", "PermissionLevel", "PermissionResult", "RiskLevel",
    "get_permission_gate", "is_testing_bypass_enabled", "require_permission",
    "reset_permission_gate", "set_testing_bypass",
    "ActionRequest", "AgentAction", "FirewallResult", "FirewallRisk",
    "validate_action", "EffectFence", "FenceDecision", "get_effect_fence",
]
