"""Fail-closed SYSTEM adapter for an isolated Agent Zero GUI worker.

This module does not call Agent Zero's stock ``/api_message`` or file APIs.
Execution is enabled only when the existing LUMENIS runtime, secret, Gateway,
browser-scope, Permission and Artifact owners inject their verified bindings,
and the pinned worker exposes the LUMENIS-scoped protocol below. No credentials
or user/browser session are loaded by this module.
"""
from __future__ import annotations

import base64
import hashlib
import http.client
import ipaddress
import json
import logging
import re
import threading
import time
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Callable, Mapping, Optional
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

AGENT_ZERO_IMAGE_DIGEST = (
    "sha256:1ab9d73c448ba44d1a569803be8ae586b092fa3dedb7422061b61e9cdf877e88"
)
AGENT_ZERO_TASK_MODE = "agent_zero_gui"
AGENT_ZERO_TASK_RECORD = "_agent_zero_gui"
AGENT_ZERO_CAPABILITIES_PATH = "/api/lumenis/v1/capabilities"
AGENT_ZERO_TASKS_PATH = "/api/lumenis/v1/tasks"
AGENT_ZERO_ARTIFACT_ROOT = "/a0/lumenis-artifacts"
AGENT_ZERO_EFFECT_FENCE_VERSION = "lumenis.read-only-browser/v1"
AGENT_ZERO_MAX_REQUEST_BYTES = 64 * 1024
AGENT_ZERO_MAX_RESPONSE_BYTES = 12 * 1024 * 1024
AGENT_ZERO_MAX_ARTIFACT_BYTES = 4 * 1024 * 1024
AGENT_ZERO_MAX_ARTIFACTS = 8
AGENT_ZERO_MAX_TOTAL_ARTIFACT_BYTES = 8 * 1024 * 1024
AGENT_ZERO_REQUEST_DEADLINE_SECONDS = 5.0
_ALLOWED_ARTIFACT_MIME = frozenset(
    {"image/png", "image/jpeg", "text/plain", "application/json"}
)
_SAFE_TASK_ID = re.compile(r"^[A-Za-z0-9_-]{8,96}$")
_SAFE_REF = re.compile(r"^[A-Za-z0-9_.:-]{1,160}$")
_SAFE_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class AgentZeroUnavailable(RuntimeError):
    """An explicit fail-closed result; never includes endpoint or secret data."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class AgentZeroDependencies:
    """Bindings supplied by existing LUMENIS owners; no owner is created here."""

    config_provider: Callable[[], Mapping[str, Any]]
    resource_probe: Callable[[], Mapping[str, Any]]
    owned_gateway_probe: Callable[[Mapping[str, Any]], Mapping[str, Any]]
    request_provider: Callable[[Mapping[str, Any], str], Mapping[str, Any]]
    scope_provider: Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]]
    artifact_sink: Callable[[Mapping[str, Any], bytes], Mapping[str, Any]]
    outcome_evaluator: Optional[Any] = None


class AgentZeroGuiExecutor:
    """One-shot, task-scoped GUI executor over an isolated loopback worker."""

    def __init__(self, dependencies: Optional[AgentZeroDependencies] = None):
        self._dependencies = dependencies

    @property
    def configured(self) -> bool:
        return self._dependencies is not None

    def execute(
        self,
        task: Mapping[str, Any],
        *,
        permission: Mapping[str, Any],
        existing_record: Optional[Mapping[str, Any]],
        claim_attempt: Callable[[Mapping[str, Any]], bool],
        transition_attempt: Callable[[str, Mapping[str, Any]], bool],
        is_cancelled: Callable[[], bool],
    ) -> dict[str, Any]:
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not _SAFE_TASK_ID.fullmatch(task_id):
            return self._unavailable("AGENT_ZERO_TASK_ID_INVALID")
        if self._dependencies is None:
            return self._unavailable("AGENT_ZERO_BINDINGS_NOT_CONFIGURED")

        record = dict(existing_record or {})
        if record:
            # A persisted claim may have crossed the network boundary. Never POST it again.
            state = record.get("state")
            if state in {"completed", "cancelled"}:
                return self._replayed_terminal(record)
            if state in {"dispatching", "submitted", "outcome_unknown", "cancel_requested"}:
                return self._unavailable(
                    "AGENT_ZERO_PRIOR_ATTEMPT_REQUIRES_RECONCILIATION",
                    outcome="OUTCOME_UNKNOWN",
                    attempt_id=record.get("attempt_id"),
                    upstream_task_id=record.get("upstream_task_id"),
                )
            return self._unavailable("AGENT_ZERO_TASK_RECORD_INVALID")

        preflight = self._preflight(task, permission)
        if isinstance(preflight, dict):
            return preflight
        config, _, gateway, scope, request_data, outcome_contract_sha256 = preflight

        attempt_id = hashlib.sha256(
            (task_id + ":" + hashlib.sha256(request_data["request_text"].encode("utf-8")).hexdigest()).encode("utf-8")
        ).hexdigest()[:32]
        idempotency_key = hashlib.sha256(
            ("lumenis-agent-zero-gui:" + task_id).encode("utf-8")
        ).hexdigest()
        attempt = {
            "schema": "lumenis.agent-zero-gui-attempt/v1",
            "task_id": task_id,
            "attempt_id": attempt_id,
            "idempotency_key": idempotency_key,
            "request_sha256": request_data["request_sha256"],
            "permission_audit_id": permission.get("audit_id"),
            "image_digest": AGENT_ZERO_IMAGE_DIGEST,
            "model_revision": gateway["model_revision"],
            "scope_ref": scope["scope_ref"],
            "browser_lease_ref": scope["browser_lease_ref"],
            "outcome_contract_sha256": outcome_contract_sha256,
            "state": "dispatching",
            "upstream_task_id": None,
            "artifact_refs": [],
        }
        try:
            if not claim_attempt(attempt):
                return self._unavailable("AGENT_ZERO_ATTEMPT_ALREADY_CLAIMED")
        except Exception:
            logger.error("Agent Zero dispatch claim failed; no remote call was made")
            return self._unavailable("AGENT_ZERO_ATTEMPT_CLAIM_FAILED")

        # Re-read the owning task state after the durable claim and immediately
        # before crossing the network boundary. If cancellation state cannot be
        # read, do not dispatch an external browser operation.
        try:
            cancelled = is_cancelled()
        except Exception:
            unknown = {**attempt, "state": "outcome_unknown"}
            self._safe_transition(transition_attempt, attempt_id, unknown)
            return self._unavailable(
                "AGENT_ZERO_CANCEL_STATE_UNAVAILABLE",
                outcome="OUTCOME_UNKNOWN",
                attempt_id=attempt_id,
            )
        if cancelled:
            cancelled_attempt = {**attempt, "state": "cancelled"}
            if not self._safe_transition(transition_attempt, attempt_id, cancelled_attempt):
                return self._unavailable(
                    "AGENT_ZERO_CANCEL_STATE_RACE",
                    outcome="OUTCOME_UNKNOWN",
                    attempt_id=attempt_id,
                )
            return {
                "executor": "agent_zero_gui",
                "execution_status": "CANCELLED",
                "task_outcome": "CANCELLED",
                "failure_code": None,
                "task_id": task_id,
                "attempt_id": attempt_id,
                "external_submission": False,
            }

        payload = {
            "schema": "lumenis.agent-zero-gui-task/v1",
            "task_id": task_id,
            "attempt_id": attempt_id,
            "idempotency_key": idempotency_key,
            "intent": task.get("intent"),
            "scope_ref": scope["scope_ref"],
            "browser_lease_ref": scope["browser_lease_ref"],
            "allowed_origins": list(scope["allowed_origins"]),
            "target_url": request_data["target_url"],
            "request_text": request_data["request_text"],
            "model_binding": {
                "provider": "owned",
                "binding_id": gateway["binding_id"],
                "model_revision": gateway["model_revision"],
            },
            "allowed_actions": list(scope["allowed_actions"]),
            "read_only": True,
        }
        try:
            response = self._request(
                config,
                "POST",
                AGENT_ZERO_TASKS_PATH + "/" + task_id + "/execute",
                payload,
            )
        except Exception:
            # Once the dispatch claim exists, any transport failure is ambiguous.
            unknown = {**attempt, "state": "outcome_unknown"}
            self._safe_transition(transition_attempt, attempt_id, unknown)
            return self._unavailable(
                "AGENT_ZERO_DISPATCH_OUTCOME_UNKNOWN",
                outcome="OUTCOME_UNKNOWN",
                attempt_id=attempt_id,
            )

        if response.get("http_status") not in {200, 201, 202}:
            unknown = {**attempt, "state": "outcome_unknown"}
            self._safe_transition(transition_attempt, attempt_id, unknown)
            return self._unavailable(
                "AGENT_ZERO_DISPATCH_OUTCOME_UNKNOWN",
                outcome="OUTCOME_UNKNOWN",
                attempt_id=attempt_id,
            )

        body = response.get("body")
        if not isinstance(body, dict) or body.get("task_id") != task_id:
            unknown = {**attempt, "state": "outcome_unknown"}
            self._safe_transition(transition_attempt, attempt_id, unknown)
            return self._unavailable(
                "AGENT_ZERO_RESPONSE_BINDING_INVALID",
                outcome="OUTCOME_UNKNOWN",
                attempt_id=attempt_id,
            )
        upstream_task_id = body.get("upstream_task_id")
        if (body.get("attempt_id") != attempt_id
                or body.get("idempotency_key") != idempotency_key
                or not isinstance(upstream_task_id, str)
                or not _SAFE_REF.fullmatch(upstream_task_id)):
            unknown = {**attempt, "state": "outcome_unknown"}
            self._safe_transition(transition_attempt, attempt_id, unknown)
            return self._unavailable(
                "AGENT_ZERO_RESPONSE_TASK_ID_INVALID",
                outcome="OUTCOME_UNKNOWN",
                attempt_id=attempt_id,
            )
        submitted = {**attempt, "state": "submitted", "upstream_task_id": upstream_task_id}
        if response["http_status"] == 202 or body.get("status") not in {"completed", "failed"}:
            self._safe_transition(transition_attempt, attempt_id, submitted)
            return self._unavailable(
                "AGENT_ZERO_TASK_SUBMITTED_RECONCILIATION_REQUIRED",
                outcome="OUTCOME_UNKNOWN",
                attempt_id=attempt_id,
                upstream_task_id=upstream_task_id,
            )

        if body.get("status") != "completed" or not isinstance(body.get("result"), dict):
            failed = {**submitted, "state": "failed"}
            self._safe_transition(transition_attempt, attempt_id, failed)
            return self._unavailable(
                "AGENT_ZERO_EXECUTION_FAILED",
                attempt_id=attempt_id,
                upstream_task_id=upstream_task_id,
            )

        try:
            public_result = self._public_result(body["result"])
            artifact_refs = self._persist_artifacts(
                config, task, attempt_id, upstream_task_id, body.get("artifacts"),
                submitted=submitted,
                transition_attempt=transition_attempt,
            )
            outcome_verification = self._verify_outcome(task, outcome_contract_sha256)
        except AgentZeroUnavailable as exc:
            unknown = {
                **submitted,
                "state": "outcome_unknown",
                "artifact_refs": getattr(exc, "artifact_refs", []),
            }
            self._safe_transition(transition_attempt, attempt_id, unknown)
            return self._unavailable(
                exc.code,
                outcome="OUTCOME_UNKNOWN",
                attempt_id=attempt_id,
                upstream_task_id=upstream_task_id,
            )

        completed = {
            **submitted,
            "state": "completed",
            "artifact_refs": artifact_refs,
            "result_sha256": self._json_digest(public_result),
            "outcome_verification": outcome_verification,
        }
        if not self._safe_transition(transition_attempt, attempt_id, completed):
            return self._unavailable(
                "AGENT_ZERO_TASK_STATE_CHANGED_DURING_EXECUTION",
                outcome="OUTCOME_UNKNOWN",
                attempt_id=attempt_id,
                upstream_task_id=upstream_task_id,
            )
        if (outcome_verification.get("state") != "VERIFIED"
                or outcome_verification.get("verified_goal_achieved") is not True):
            return self._unavailable(
                "AGENT_ZERO_OUTCOME_NOT_VERIFIED",
                outcome="UNAVAILABLE",
                attempt_id=attempt_id,
                upstream_task_id=upstream_task_id,
                external_submission=True,
                artifact_refs=artifact_refs,
                outcome_verification=outcome_verification,
            )
        return {
            "executor": "agent_zero_gui",
            "execution_status": "COMPLETED",
            "task_outcome": "COMPLETED",
            "task_id": task_id,
            "attempt_id": attempt_id,
            "upstream_task_id": upstream_task_id,
            "provider": "owned",
            "model_revision": gateway["model_revision"],
            "result": public_result,
            "artifact_refs": artifact_refs,
            "outcome_verification": outcome_verification,
            "external_submission": True,
        }

    def cancel(
        self,
        task: Mapping[str, Any],
        *,
        permission: Mapping[str, Any],
        existing_record: Mapping[str, Any],
        transition_attempt: Callable[[str, Mapping[str, Any]], bool],
    ) -> dict[str, Any]:
        """Request cancellation only through a verified history-preserving route."""
        task_id = task.get("task_id")
        attempt_id = existing_record.get("attempt_id")
        upstream_task_id = existing_record.get("upstream_task_id")
        idempotency_key = existing_record.get("idempotency_key")
        if (not isinstance(task_id, str) or not _SAFE_TASK_ID.fullmatch(task_id)
                or not isinstance(attempt_id, str) or not _SAFE_REF.fullmatch(attempt_id)
                or not isinstance(idempotency_key, str) or not _SAFE_SHA256.fullmatch(idempotency_key)
                or existing_record.get("state") not in {"dispatching", "submitted", "outcome_unknown"}):
            return self._unavailable("AGENT_ZERO_CANCEL_BINDING_UNAVAILABLE", outcome="OUTCOME_UNKNOWN")
        if upstream_task_id is not None and (
                not isinstance(upstream_task_id, str) or not _SAFE_REF.fullmatch(upstream_task_id)):
            return self._unavailable("AGENT_ZERO_CANCEL_BINDING_UNAVAILABLE", outcome="OUTCOME_UNKNOWN")
        if self._dependencies is None:
            return self._unavailable("AGENT_ZERO_BINDINGS_NOT_CONFIGURED", outcome="OUTCOME_UNKNOWN")
        if not self._permission_matches(permission, task_id):
            unknown = {**dict(existing_record), "state": "outcome_unknown", "cancel_requested": True}
            self._safe_transition(transition_attempt, attempt_id, unknown)
            return self._unavailable(
                "AGENT_ZERO_CANCEL_PERMISSION_NOT_VERIFIED",
                outcome="OUTCOME_UNKNOWN",
                attempt_id=attempt_id,
            )
        try:
            config, capabilities = self._safe_runtime_and_capabilities(task, permission)
            if (capabilities.get("cancel_preserves_history") is not True
                    or capabilities.get("cancel_by_idempotency_key") is not True):
                raise AgentZeroUnavailable("AGENT_ZERO_HISTORY_PRESERVING_CANCEL_UNAVAILABLE")
            response = self._request(
                config,
                "POST",
                AGENT_ZERO_TASKS_PATH + "/" + task_id + "/cancel",
                {
                    "schema": "lumenis.agent-zero-gui-cancel/v1",
                    "task_id": task_id,
                    "attempt_id": attempt_id,
                    "upstream_task_id": upstream_task_id,
                    "idempotency_key": idempotency_key,
                    "cancel_scope": "lumenis_task_attempt",
                },
            )
            body = response.get("body")
            if (response.get("http_status") not in {200, 201}
                    or not isinstance(body, dict)
                    or body.get("task_id") != task_id
                    or body.get("attempt_id") != attempt_id
                    or (upstream_task_id is not None and body.get("upstream_task_id") != upstream_task_id)
                    or (body.get("upstream_task_id") is not None
                        and (not isinstance(body.get("upstream_task_id"), str)
                             or not _SAFE_REF.fullmatch(body.get("upstream_task_id"))))
                    or body.get("idempotency_key") != idempotency_key
                    or body.get("cancel_scope") != "lumenis_task_attempt"
                    or body.get("status") != "cancelled"
                    or body.get("history_preserved") is not True):
                raise AgentZeroUnavailable("AGENT_ZERO_CANCEL_NOT_CONFIRMED")
            cancelled = {
                **dict(existing_record),
                "state": "cancelled",
                "upstream_task_id": body.get("upstream_task_id") or upstream_task_id,
                "history_preserved": True,
            }
            if not self._safe_transition(transition_attempt, attempt_id, cancelled):
                raise AgentZeroUnavailable("AGENT_ZERO_CANCEL_STATE_RACE")
            return {
                "executor": "agent_zero_gui",
                "execution_status": "CANCELLED",
                "task_outcome": "CANCELLED",
                "failure_code": None,
                "external_submission": True,
                "history_preserved": True,
            }
        except AgentZeroUnavailable as exc:
            unknown = {**dict(existing_record), "state": "outcome_unknown", "cancel_requested": True}
            self._safe_transition(transition_attempt, attempt_id, unknown)
            return self._unavailable(exc.code, outcome="OUTCOME_UNKNOWN", attempt_id=attempt_id)
        except Exception:
            unknown = {**dict(existing_record), "state": "outcome_unknown", "cancel_requested": True}
            self._safe_transition(transition_attempt, attempt_id, unknown)
            return self._unavailable(
                "AGENT_ZERO_CANCEL_OUTCOME_UNKNOWN", outcome="OUTCOME_UNKNOWN", attempt_id=attempt_id,
            )

    def _preflight(self, task: Mapping[str, Any], permission: Mapping[str, Any]):
        if task.get("agent_id") != "browser_agent":
            return self._unavailable("AGENT_ZERO_REQUIRES_EXISTING_BROWSER_AGENT")
        if task.get("intent") not in {"open_browser", "web_search", "page_operation"}:
            return self._unavailable("AGENT_ZERO_BROWSER_INTENT_REQUIRED")
        if task.get("risk_level") != "L2" or task.get("permission_result") != "allowed":
            return self._unavailable("AGENT_ZERO_PERMISSION_NOT_VERIFIED")
        if not self._permission_matches(permission, task.get("task_id")):
            return self._unavailable("AGENT_ZERO_PERMISSION_SCOPE_INVALID")
        if task.get("admin_required") or task.get("permanent_deny") or task.get("human_approval_required"):
            return self._unavailable("AGENT_ZERO_TASK_NOT_ADMITTED")
        outcome_contract_sha256 = self._outcome_contract_hash(task.get("task_id"))
        if outcome_contract_sha256 is None:
            return self._unavailable(
                "AGENT_ZERO_OUTCOME_CONTRACT_NOT_BOUND",
                outcome="UNAVAILABLE",
                outcome_verification={
                    "state": "NOT_VERIFIED",
                    "verified_goal_achieved": False,
                    "reason": "OUTCOME_OWNER_NOT_BOUND",
                },
            )
        try:
            task_binding = {
                "task_id": task.get("task_id"),
                "created_by": task.get("created_by"),
                "intent": task.get("intent"),
            }
            gateway = self._dependencies.owned_gateway_probe(task_binding)
            request_data = self._dependencies.request_provider(
                task_binding, task.get("user_input") if isinstance(task.get("user_input"), str) else "",
            )
            if not isinstance(request_data, Mapping):
                raise AgentZeroUnavailable("AGENT_ZERO_REQUEST_POLICY_NOT_BOUND")
            request_data = self._validated_request(request_data)
            scope = self._dependencies.scope_provider(task_binding, request_data)
            config, capabilities = self._safe_runtime_and_capabilities(task, permission)
        except AgentZeroUnavailable as exc:
            return self._unavailable(exc.code)
        except Exception:
            return self._unavailable("AGENT_ZERO_PREFLIGHT_OWNER_UNAVAILABLE")
        if (not isinstance(gateway, Mapping) or gateway.get("available") is not True
                or gateway.get("provider") != "owned"
                or not self._valid_ref(gateway.get("binding_id"))
                or not self._valid_ref(gateway.get("model_revision"))):
            return self._unavailable("OWNED_GATEWAY_NOT_BOUND")
        if (capabilities.get("gateway_binding_id") != gateway.get("binding_id")
                or capabilities.get("model_revision") != gateway.get("model_revision")):
            return self._unavailable("AGENT_ZERO_OWNED_GATEWAY_BINDING_MISMATCH")
        if (not isinstance(scope, Mapping) or scope.get("allowed") is not True
                or scope.get("read_only") is not True
                or scope.get("personal_profile_access") is not False
                or not self._valid_ref(scope.get("scope_ref"))
                or not self._valid_ref(scope.get("browser_lease_ref"))
                or scope.get("target_url") != request_data.get("target_url")
                or not isinstance(scope.get("allowed_actions"), (list, tuple))
                or not scope.get("allowed_actions")
                or not all(
                    isinstance(action, str)
                    and action in {"navigate", "observe", "capture", "click", "type", "scroll", "keypress"}
                    for action in scope.get("allowed_actions", [])
                )):
            return self._unavailable("AGENT_ZERO_BROWSER_SCOPE_NOT_BOUND")
        origins = scope.get("allowed_origins")
        if (not isinstance(origins, (list, tuple)) or not origins or len(origins) > 16
                or not all(isinstance(origin, str) for origin in origins)):
            return self._unavailable("AGENT_ZERO_ORIGIN_SCOPE_NOT_BOUND")
        try:
            normalized_origins = {self._url_origin(origin, require_origin=True) for origin in origins}
            target_origin = self._url_origin(request_data["target_url"])
        except AgentZeroUnavailable as exc:
            return self._unavailable(exc.code)
        if target_origin not in normalized_origins:
            return self._unavailable("AGENT_ZERO_TARGET_ORIGIN_NOT_ALLOWED")
        if not capabilities.get("task_scope_enforced") or not capabilities.get("read_only_effect_fence"):
            return self._unavailable("AGENT_ZERO_SCOPE_OR_EFFECT_FENCE_UNAVAILABLE")
        runtime_actions = capabilities.get("allowed_actions")
        if (not isinstance(runtime_actions, list)
                or not all(isinstance(action, str) for action in runtime_actions)
                or not set(scope.get("allowed_actions", [])).issubset(set(runtime_actions))):
            return self._unavailable("AGENT_ZERO_ACTION_SCOPE_MISMATCH")
        return config, capabilities, gateway, scope, request_data, outcome_contract_sha256

    def _safe_runtime_and_capabilities(self, task, permission):
        dependencies = self._dependencies
        if dependencies is None:
            raise AgentZeroUnavailable("AGENT_ZERO_BINDINGS_NOT_CONFIGURED")
        config = dependencies.config_provider()
        if not isinstance(config, Mapping):
            raise AgentZeroUnavailable("AGENT_ZERO_CONFIG_UNAVAILABLE")
        if config.get("secret_owner_bound") is not True:
            raise AgentZeroUnavailable("AGENT_ZERO_SECRET_OWNER_NOT_BOUND")
        token = config.get("api_token")
        secret_ref = config.get("secret_ref")
        if not isinstance(token, str) or not token.strip() or not self._valid_ref(secret_ref):
            raise AgentZeroUnavailable("AGENT_ZERO_SERVER_TOKEN_UNAVAILABLE")
        if config.get("expected_image_digest") != AGENT_ZERO_IMAGE_DIGEST:
            raise AgentZeroUnavailable("AGENT_ZERO_IMAGE_PIN_MISMATCH")
        endpoint = self._endpoint(config.get("base_url"))
        if config.get("cost_class") != "ZERO_COST":
            raise AgentZeroUnavailable("AGENT_ZERO_COST_NOT_ZERO")
        resource = dependencies.resource_probe()
        if (not isinstance(resource, Mapping) or resource.get("ready") is not True
                or resource.get("zero_cost") is not True
                or resource.get("image_digest") != AGENT_ZERO_IMAGE_DIGEST
                or resource.get("bound_endpoint") != config.get("base_url")
                or resource.get("process_identity_verified") is not True
                or resource.get("host_bind_mounts") != 0
                or resource.get("personal_session_access") is not False
                or resource.get("isolated") is not True):
            raise AgentZeroUnavailable("AGENT_ZERO_RESOURCE_BLOCKED")
        capability_response = self._request(config, "GET", AGENT_ZERO_CAPABILITIES_PATH)
        capabilities = capability_response.get("body")
        if (capability_response.get("http_status") != 200
                or not isinstance(capabilities, Mapping)
                or capabilities.get("schema") != "lumenis.agent-zero-gui-capabilities/v1"
                or capabilities.get("image_digest") != AGENT_ZERO_IMAGE_DIGEST
                or capabilities.get("protocol_version") != 1
                or capabilities.get("task_scope_enforced") is not True
                or capabilities.get("session_scope_enforced") is not True
                or capabilities.get("network_allowlist_enforced") is not True
                or capabilities.get("durable_idempotency") is not True
                or capabilities.get("idempotency_scope") != "lumenis_task_attempt"
                or capabilities.get("read_only_effect_fence") is not True
                or capabilities.get("effect_fence_version") != AGENT_ZERO_EFFECT_FENCE_VERSION
                or capabilities.get("owned_gateway_only") is not True
                or capabilities.get("cancel_preserves_history") is not True
                or capabilities.get("cancel_by_idempotency_key") is not True
                or capabilities.get("artifact_scope_enforced") is not True
                or capabilities.get("artifact_root") != AGENT_ZERO_ARTIFACT_ROOT
                or capabilities.get("no_host_profile_access") is not True):
            raise AgentZeroUnavailable("AGENT_ZERO_SAFE_PROTOCOL_UNAVAILABLE")
        return {**dict(config), "_endpoint": endpoint}, dict(capabilities)

    @staticmethod
    def _endpoint(raw: Any) -> tuple[str, int]:
        if not isinstance(raw, str) or not raw:
            raise AgentZeroUnavailable("AGENT_ZERO_ENDPOINT_UNAVAILABLE")
        try:
            parsed = urlsplit(raw)
            address = ipaddress.ip_address(parsed.hostname or "")
            port = parsed.port or 80
        except (ValueError, TypeError):
            raise AgentZeroUnavailable("AGENT_ZERO_ENDPOINT_INVALID") from None
        if (parsed.scheme != "http" or not address.is_loopback or parsed.username
                or parsed.password or parsed.path not in {"", "/"}
                or parsed.query or parsed.fragment or not 1 <= port <= 65535):
            raise AgentZeroUnavailable("AGENT_ZERO_ENDPOINT_NOT_LOOPBACK")
        return str(address), port

    @classmethod
    def _permission_matches(cls, permission: Mapping[str, Any], task_id: Any) -> bool:
        if not isinstance(permission, Mapping):
            return False
        return (
            isinstance(task_id, str)
            and permission.get("allowed") is True
            and permission.get("operation_type") == "browser_operation"
            and permission.get("resource") == "ai_task:" + task_id
            and permission.get("requires_approval") is False
            and permission.get("operation_id") in {
                "agent_zero_dispatch_" + task_id,
                "agent_zero_cancel_" + task_id,
            }
            and cls._valid_ref(permission.get("audit_id"))
        )

    def _request(self, config: Mapping[str, Any], method: str, path: str, payload=None):
        if path not in {AGENT_ZERO_CAPABILITIES_PATH} and not path.startswith(AGENT_ZERO_TASKS_PATH + "/"):
            raise AgentZeroUnavailable("AGENT_ZERO_ENDPOINT_PATH_REJECTED")
        endpoint = config.get("_endpoint") or self._endpoint(config.get("base_url"))
        host, port = endpoint
        token = config.get("api_token")
        if not isinstance(token, str) or not token.strip():
            raise AgentZeroUnavailable("AGENT_ZERO_SERVER_TOKEN_UNAVAILABLE")
        body = None
        headers = {"X-API-KEY": token, "Accept": "application/json", "Connection": "close"}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
            if len(body) > AGENT_ZERO_MAX_REQUEST_BYTES:
                raise AgentZeroUnavailable("AGENT_ZERO_REQUEST_TOO_LARGE")
            headers["Content-Type"] = "application/json"
        deadline = time.monotonic() + AGENT_ZERO_REQUEST_DEADLINE_SECONDS
        connection = http.client.HTTPConnection(
            host, port, timeout=AGENT_ZERO_REQUEST_DEADLINE_SECONDS,
        )
        try:
            connection.connect()
            self._set_deadline_timeout(connection, deadline)
            connection.request(method, path, body=body, headers=headers)
            self._set_deadline_timeout(connection, deadline)
            response = connection.getresponse()
            raw_chunks = []
            total_bytes = 0
            while True:
                self._set_deadline_timeout(connection, deadline)
                remaining_bytes = AGENT_ZERO_MAX_RESPONSE_BYTES + 1 - total_bytes
                chunk = response.read1(min(64 * 1024, remaining_bytes))
                if not chunk:
                    break
                raw_chunks.append(chunk)
                total_bytes += len(chunk)
                if total_bytes > AGENT_ZERO_MAX_RESPONSE_BYTES:
                    raise AgentZeroUnavailable("AGENT_ZERO_RESPONSE_TOO_LARGE")
            raw = b"".join(raw_chunks)
            if response.status in {301, 302, 303, 307, 308}:
                raise AgentZeroUnavailable("AGENT_ZERO_REDIRECT_REJECTED")
            if not raw:
                parsed_body = None
            else:
                try:
                    parsed_body = json.loads(raw.decode("utf-8"), object_pairs_hook=self._unique_pairs)
                except Exception:
                    raise AgentZeroUnavailable("AGENT_ZERO_RESPONSE_INVALID") from None
            return {"http_status": response.status, "body": parsed_body}
        except AgentZeroUnavailable:
            raise
        except TimeoutError:
            raise AgentZeroUnavailable("AGENT_ZERO_REQUEST_DEADLINE_EXCEEDED") from None
        except Exception:
            raise AgentZeroUnavailable("AGENT_ZERO_TRANSPORT_UNAVAILABLE") from None
        finally:
            connection.close()

    @staticmethod
    def _set_deadline_timeout(connection, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AgentZeroUnavailable("AGENT_ZERO_REQUEST_DEADLINE_EXCEEDED")
        if connection.sock is None:
            raise AgentZeroUnavailable("AGENT_ZERO_TRANSPORT_UNAVAILABLE")
        connection.sock.settimeout(remaining)

    def _outcome_contract_hash(self, task_id):
        evaluator = self._dependencies.outcome_evaluator if self._dependencies is not None else None
        if evaluator is None:
            return None
        try:
            from lumenis.shared.evaluation.trajectory import TrajectoryEvaluator

            if not isinstance(evaluator, TrajectoryEvaluator) or evaluator.has_outcome_contract is not True:
                return None
            contract_sha256 = evaluator.form_outcome_contract(task_id)
            if not isinstance(contract_sha256, str) or not _SAFE_SHA256.fullmatch(contract_sha256):
                return None
            return contract_sha256
        except Exception:
            return None

    def _verify_outcome(self, task, expected_contract_sha256):
        evaluator = self._dependencies.outcome_evaluator if self._dependencies is not None else None
        task_id = task.get("task_id")
        if (evaluator is None or not isinstance(task_id, str)
                or not isinstance(expected_contract_sha256, str)
                or not _SAFE_SHA256.fullmatch(expected_contract_sha256)):
            return {
                "state": "NOT_VERIFIED",
                "verified_goal_achieved": False,
                "reason": "OUTCOME_OWNER_NOT_BOUND",
            }
        try:
            outcome = evaluator.verify_outcome(
                task_id,
                expected_contract_sha256,
                expected_output_receipts=None,
                require_bound_receipts=True,
            )
        except Exception:
            outcome = None
        if not isinstance(outcome, Mapping):
            return {
                "state": "BLOCKED",
                "verified_goal_achieved": False,
                "reason": "OUTCOME_OWNER_UNAVAILABLE",
            }
        state = outcome.get("state")
        verified = state == "VERIFIED" and outcome.get("verified_goal_achieved") is True
        if state not in {"VERIFIED", "FAILED", "NOT_VERIFIED", "BLOCKED"}:
            state = "BLOCKED"
        if state == "VERIFIED" and not verified:
            state = "NOT_VERIFIED"
        reason = outcome.get("reason")
        safe_reasons = {
            "CANONICAL_OUTCOME_CHECKS", "OUTCOME_OWNER_NOT_BOUND", "OUTCOME_CONTRACT_INVALID",
            "OUTCOME_EXPECTED_IDENTITY_MISSING", "OUTCOME_CONTRACT_MISSING", "OUTCOME_CONTRACT_CHANGED",
            "OUTCOME_GENERATED_REQUIREMENT_INVALID", "OUTCOME_COMMIT_BINDING_INVALID",
            "OUTCOME_OWNER_UNAVAILABLE", "OUTCOME_UNAVAILABLE", "OUTCOME_COMMIT_UNAVAILABLE",
            "OUTCOME_COMMIT_LINEAGE_MISMATCH", "OUTCOME_COMMIT_IDENTITY_INVALID",
            "OUTCOME_COMMIT_CONSTRAINT_MISMATCH", "OUTCOME_COMMIT_BINDING_MISSING",
            "OUTCOME_COMMIT_BINDING_CHANGED", "OUTCOME_COMMITTED_READBACK_MISMATCH",
            "OUTCOME_COMMIT_CHANGED_DURING_READ", "OUTCOME_COMMITTED_OWNER_NOT_BOUND",
        }
        if reason not in safe_reasons:
            reason = "OUTCOME_OWNER_UNAVAILABLE"
        return {
            "state": state,
            "verified_goal_achieved": verified,
            "reason": reason,
        }

    def _persist_artifacts(
        self, config, task, attempt_id, upstream_task_id, artifacts, *,
        submitted, transition_attempt,
    ):
        if not isinstance(artifacts, list) or not artifacts or len(artifacts) > AGENT_ZERO_MAX_ARTIFACTS:
            raise AgentZeroUnavailable("AGENT_ZERO_ARTIFACTS_MISSING_OR_INVALID")
        sink = self._dependencies.artifact_sink
        refs = []
        total = 0
        validated = []
        for item in artifacts:
            if not isinstance(item, Mapping):
                raise AgentZeroUnavailable("AGENT_ZERO_ARTIFACT_INVALID")
            if (item.get("task_id") != task["task_id"]
                    or item.get("attempt_id") != attempt_id
                    or item.get("upstream_task_id") != upstream_task_id):
                raise AgentZeroUnavailable("AGENT_ZERO_ARTIFACT_BINDING_INVALID")
            path = item.get("path")
            mime = item.get("mime_type")
            digest = item.get("sha256")
            encoded = item.get("content_base64")
            safe_path = self._artifact_relative_path(path, task["task_id"])
            if mime not in _ALLOWED_ARTIFACT_MIME or not isinstance(encoded, str):
                raise AgentZeroUnavailable("AGENT_ZERO_ARTIFACT_TYPE_REJECTED")
            try:
                content = base64.b64decode(encoded, validate=True)
            except Exception:
                raise AgentZeroUnavailable("AGENT_ZERO_ARTIFACT_ENCODING_INVALID") from None
            if (not content or len(content) > AGENT_ZERO_MAX_ARTIFACT_BYTES
                    or not isinstance(digest, str) or not _SAFE_SHA256.fullmatch(digest)
                    or hashlib.sha256(content).hexdigest() != digest):
                raise AgentZeroUnavailable("AGENT_ZERO_ARTIFACT_HASH_OR_SIZE_INVALID")
            if not self._artifact_content_matches_type(mime, content):
                raise AgentZeroUnavailable("AGENT_ZERO_ARTIFACT_CONTENT_TYPE_MISMATCH")
            total += len(content)
            if total > AGENT_ZERO_MAX_TOTAL_ARTIFACT_BYTES:
                raise AgentZeroUnavailable("AGENT_ZERO_ARTIFACT_TOTAL_SIZE_EXCEEDED")
            metadata = {
                "task_id": task["task_id"],
                "attempt_id": attempt_id,
                "upstream_task_id": upstream_task_id,
                "relative_path": safe_path,
                "mime_type": mime,
                "sha256": digest,
                "origin": "agent_zero_isolated_gui",
            }
            validated.append((metadata, content, digest, mime))

        # Validate the complete response before the first persistent write.
        # Then record every successful Artifact receipt in the same task
        # attempt so a later sink/transition failure does not lose lineage.
        try:
            for metadata, content, digest, mime in validated:
                try:
                    saved = sink(metadata, content)
                except Exception:
                    raise AgentZeroUnavailable("AGENT_ZERO_ARTIFACT_PERSIST_FAILED") from None
                if (not isinstance(saved, Mapping)
                        or not self._valid_ref(saved.get("artifact_ref"))
                        or saved.get("sha256") != digest
                        or saved.get("size_bytes") != len(content)):
                    raise AgentZeroUnavailable("AGENT_ZERO_ARTIFACT_RECEIPT_INVALID")
                refs.append({"artifact_ref": saved["artifact_ref"], "sha256": digest, "mime_type": mime})
                if not self._safe_transition(
                        transition_attempt, attempt_id,
                        {**dict(submitted), "artifact_refs": list(refs)}):
                    raise AgentZeroUnavailable("AGENT_ZERO_ARTIFACT_LINEAGE_PERSIST_FAILED")
        except AgentZeroUnavailable as exc:
            exc.artifact_refs = list(refs)
            raise
        return refs

    @staticmethod
    def _artifact_relative_path(raw_path: Any, task_id: str) -> str:
        if (not isinstance(raw_path, str) or "\\" in raw_path or "\x00" in raw_path
                or not raw_path.startswith(AGENT_ZERO_ARTIFACT_ROOT + "/")):
            raise AgentZeroUnavailable("AGENT_ZERO_ARTIFACT_PATH_REJECTED")
        parts = raw_path.split("/")
        expected_prefix = ["", "a0", "lumenis-artifacts", task_id]
        if (parts[:4] != expected_prefix or len(parts) < 5
                or any(
                    part in {"", ".", ".."}
                    or part.startswith(".")
                    or "%" in part
                    or ":" in part
                    or any(ord(char) < 32 for char in part)
                    for part in parts[1:]
                )):
            raise AgentZeroUnavailable("AGENT_ZERO_ARTIFACT_PATH_REJECTED")
        normalized = PurePosixPath(raw_path)
        if str(normalized) != raw_path or normalized.is_absolute() is False:
            raise AgentZeroUnavailable("AGENT_ZERO_ARTIFACT_PATH_REJECTED")
        return "/".join(parts[4:])

    @classmethod
    def _artifact_content_matches_type(cls, mime: str, content: bytes) -> bool:
        if mime == "image/png":
            return content.startswith(b"\x89PNG\r\n\x1a\n")
        if mime == "image/jpeg":
            return content.startswith(b"\xff\xd8\xff")
        if mime == "text/plain":
            try:
                content.decode("utf-8", errors="strict")
                return True
            except UnicodeDecodeError:
                return False
        if mime == "application/json":
            try:
                value = json.loads(content.decode("utf-8"), object_pairs_hook=cls._unique_pairs)
                return isinstance(value, (dict, list))
            except Exception:
                return False
        return False

    @staticmethod
    def _validated_request(request):
        if type(request) is not dict or set(request) != {
                "request_text", "target_url", "request_sha256", "input_sanitized", "target_url_sanitized",
        }:
            raise AgentZeroUnavailable("AGENT_ZERO_REQUEST_POLICY_NOT_BOUND")
        text = request.get("request_text")
        if (request.get("input_sanitized") is not True
                or not isinstance(text, str) or not text.strip()
                or len(text.encode("utf-8")) > 4000):
            raise AgentZeroUnavailable("AGENT_ZERO_REQUEST_INVALID")
        target_url = request.get("target_url")
        if (not isinstance(target_url, str) or len(target_url) > 2048
                or request.get("target_url_sanitized") is not True):
            raise AgentZeroUnavailable("AGENT_ZERO_TARGET_NOT_BOUND")
        try:
            parsed = urlsplit(target_url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError
        except (ValueError, TypeError):
            raise AgentZeroUnavailable("AGENT_ZERO_TARGET_INVALID") from None
        request_text = text.strip()
        supplied_hash = request.get("request_sha256")
        actual_hash = hashlib.sha256(request_text.encode("utf-8")).hexdigest()
        if not isinstance(supplied_hash, str) or supplied_hash != actual_hash:
            raise AgentZeroUnavailable("AGENT_ZERO_REQUEST_HASH_INVALID")
        return {
            "request_text": request_text,
            "target_url": target_url,
            "request_sha256": actual_hash,
        }

    @staticmethod
    def _url_origin(raw_url: str, *, require_origin: bool = False) -> str:
        try:
            parsed = urlsplit(raw_url)
            if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                    or parsed.username or parsed.password):
                raise ValueError
            host = parsed.hostname.rstrip(".")
            try:
                host = str(ipaddress.ip_address(host))
            except ValueError:
                host = host.encode("idna").decode("ascii").lower()
            port = parsed.port
            default_port = 443 if parsed.scheme == "https" else 80
            if ":" in host:
                host = "[" + host + "]"
            if require_origin and (parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
                raise ValueError
            suffix = "" if port in {None, default_port} else ":" + str(port)
            return f"{parsed.scheme}://{host}{suffix}"
        except (ValueError, UnicodeError, TypeError):
            raise AgentZeroUnavailable("AGENT_ZERO_ORIGIN_INVALID") from None

    @classmethod
    def _public_result(cls, value: Mapping[str, Any]) -> dict[str, Any]:
        # Treat upstream content as untrusted task output; keep only bounded JSON.
        try:
            encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        except (TypeError, ValueError):
            raise AgentZeroUnavailable("AGENT_ZERO_RESULT_INVALID") from None
        if len(encoded.encode("utf-8")) > 32 * 1024:
            raise AgentZeroUnavailable("AGENT_ZERO_RESULT_TOO_LARGE")
        return json.loads(encoded)

    @staticmethod
    def _json_digest(value: Mapping[str, Any]) -> str:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @staticmethod
    def _valid_ref(value: Any) -> bool:
        return isinstance(value, str) and bool(_SAFE_REF.fullmatch(value))

    @staticmethod
    def _unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    @staticmethod
    def _safe_transition(callback, attempt_id, record) -> bool:
        try:
            return callback(attempt_id, record) is True
        except Exception:
            logger.error("Agent Zero task-state transition failed")
            return False

    @staticmethod
    def _unavailable(code, *, outcome="UNAVAILABLE", **fields):
        return {
            "executor": "agent_zero_gui",
            "execution_status": outcome,
            "task_outcome": outcome,
            "failure_code": code,
            "error": code,
            "external_submission": False,
            **{key: value for key, value in fields.items() if value is not None},
        }

    @staticmethod
    def _replayed_terminal(record):
        # A terminal record is immutable; the task engine should return its
        # persisted task row instead of treating this as a fresh execution.
        return AgentZeroGuiExecutor._unavailable(
            "AGENT_ZERO_TASK_ALREADY_TERMINAL_DO_NOT_REPLAY",
            outcome="OUTCOME_UNKNOWN",
            attempt_id=record.get("attempt_id"),
        )


_executor_lock = threading.Lock()
_executor: Optional[AgentZeroGuiExecutor] = None


def configure_agent_zero_gui_executor(executor: AgentZeroGuiExecutor) -> None:
    """Bind an executor assembled by existing SYSTEM owners during startup."""
    if not isinstance(executor, AgentZeroGuiExecutor) or not executor.configured:
        raise ValueError("a fully bound AgentZeroGuiExecutor is required")
    global _executor
    with _executor_lock:
        _executor = executor


def get_agent_zero_gui_executor() -> AgentZeroGuiExecutor:
    with _executor_lock:
        return _executor or AgentZeroGuiExecutor()


def is_agent_zero_gui_task(task: Mapping[str, Any]) -> bool:
    context = task.get("context")
    return (
        isinstance(context, Mapping)
        and context.get("execution_mode") == AGENT_ZERO_TASK_MODE
        and context.get("execution_schema") == "lumenis.computer-execution-request/v1"
    )
