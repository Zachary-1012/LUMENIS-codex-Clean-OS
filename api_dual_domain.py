# -*- coding: utf-8 -*-
"""
ZBC API Dual-Domain Namespace（双域核心扩展）
================================================
三个独立域路由蓝图：
  - zbmp_bp: /api/zbmp/*  多品牌平台域
  - cth_bp:  /api/cth/*   CTH 商业运营域
  - system_bp: /api/system/*  系统基础设施域

每个端点：
  1. 从请求头 X-Domain-Id / X-Product-Id 或 session 解析域身份
  2. 设置线程 SubjectContext + DomainContext
  3. 业务读取须通过当前 Scope / Permission / Canonical owner；系统状态使用现有 runtime owner
  4. 返回统一 JSON: {success, data, error, domain_id, product_id}

CTH 的缺省选择保持 GLOBAL / ALL；参考主体不会因兼容路由而自动选中。

Compatibility Layer：现有 /api/* 端点保持不变，本模块仅新增域命名空间端点。
硬约束：禁止假数据/Mock，禁止吞异常，ZBMP 不读 CTH 专项字段。
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from datetime import datetime as _datetime, timedelta as _timedelta
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request, g

from domain_isolation import (
    DomainContext,
    DOMAIN_CTH,
    DOMAIN_ZBMP,
    DOMAIN_SYSTEM,
    PRODUCT_CTH,
    PRODUCT_ZBMP,
    PRODUCT_SYSTEM,
    domain_summary,
    get_domain_context,
    set_domain_context,
    clear_domain_context,
    domain_to_product,
    product_to_domain,
)
from subject_context import (
    CTH_BRAND_KEY,
    PRODUCT_CTH as SC_PRODUCT_CTH,
    PRODUCT_ZBMP as SC_PRODUCT_ZBMP,
    SubjectContext,
    set_thread_context,
    clear_thread_context,
    get_subject_context,
)
from domain_adapter import get_adapter, CTH_ONLY_FIELDS, ZBMP_ONLY_FIELDS
from lumenis.shared.database import get_repository


def _same_business_scope(original, current):
    """Compare canonical context while keeping its signed display label intact."""
    from lumenis.shared.reporting.source_brief_job import _scope_material
    if not isinstance(original, dict) or not isinstance(current, dict):
        return False
    try:
        for scope in (original, current):
            canonical = _scope_material(
                product_id=scope["product_id"], global_scope=scope["global"],
                subject_id=scope["subject_id"], brand_focus_id=scope["brand_focus_id"],
                entity_label=scope["entity_label"])
            if json.dumps(canonical, sort_keys=True) != json.dumps(scope, sort_keys=True):
                return False
    except (KeyError, TypeError, ValueError):
        return False
    comparable = {**original, "entity_label": current["entity_label"]}
    return json.dumps(comparable, sort_keys=True) == json.dumps(current, sort_keys=True)


def authorize_business_work_request(operation, *, actor_ref, scope):
    """Fresh server receipt for W6 composition; never accept receipt JSON."""
    from experience_runtime import _source_brief_context
    from lumenis.shared.reporting.source_brief_job import _scope_material
    from lumenis.system.security import get_permission_gate, OperationType
    if operation not in {"read", "prepare", "choose", "adopt", "cancel", "interrupt", "resume", "action", "manual_action", "observation", "outcome", "outcome_unknown", "evaluate", "review", "restore"}:
        raise PermissionError("BUSINESS_WORK_OPERATION_DENIED")
    action = "read" if operation == "read" else "write"
    current_ref, scope_audit, material = _source_brief_context(action)
    current_scope = _scope_material(**material)
    if current_ref != actor_ref or current_scope != scope or current_scope["global"] is not False:
        raise PermissionError("BUSINESS_WORK_CONTEXT_CHANGED")
    audit = scope_audit
    if operation != "read":
        resource = scope["domain_id"] + ":" + (scope["subject_id"] or scope["brand_focus_id"])
        allowed = get_permission_gate().check(
            OperationType.REPORT_REVIEW, resource=resource, caller=actor_ref, domain_id=scope["domain_id"],
        )
        if (not allowed.allowed or not allowed.audit_id or allowed.resource != resource
                or allowed.caller != actor_ref or allowed.domain_id != scope["domain_id"]):
            raise PermissionError("BUSINESS_WORK_INTERNAL_RECORD_DENIED")
        audit = allowed.audit_id
    return {"actor_id": current_ref, "scope": current_scope, "operation": operation,
            "permission_audit_ref": scope_audit, "operation_audit_ref": audit}


def authorize_business_related_read(principal, *, actor_ref, original_scope, operation):
    """Server-only read adapter; an unsealed JSON principal is never accepted."""
    from lumenis.system.security.permission import check_local_workspace_scope_permission
    if operation != "read" or getattr(principal, "principal_ref", None) != actor_ref:
        raise PermissionError("BUSINESS_LENS_READ_ONLY_PRINCIPAL_REQUIRED")
    result = check_local_workspace_scope_permission(
        principal, domain_id=original_scope.get("domain_id"), module="reports", action="read",
        subject_id=original_scope.get("subject_id"), brand_focus_id=original_scope.get("brand_focus_id"),
        global_scope=original_scope.get("global"))
    if not result.allowed or not result.audit_id:
        raise PermissionError("BUSINESS_LENS_ORIGINAL_SCOPE_READ_DENIED")
    return {"actor_id": actor_ref, "scope": original_scope, "operation": "read",
            "permission_audit_ref": result.audit_id, "operation_audit_ref": result.audit_id}


class BusinessDecisionWorkflow:
    """CTH/BMP operator decisions over existing Shared report artifacts.

    This is domain work, not an AI, database, Artifact or Permission owner.
    The composing API must supply a fresh server authorization closure for
    every operation. Options are attributed operator proposals, never inferred
    consumer facts. An injected server owner reader can reconcile internal
    creation already performed; this service never executes a task or campaign.
    Signed transitions live in the existing Evidence store without a migration.
    """

    VERSION = "cth-bmp-decision/1"
    ACTION_VERSION = "cth-bmp-decision/2"
    REVISION_VERSION = "cth-bmp-decision/3"
    OBSERVATION_VERSION = "cth-bmp-decision/4"
    FINANCIAL_OBSERVATION_VERSION = "cth-bmp-decision/5"
    DOMAIN_ANALYSIS_VERSION = "cth-bmp-domain-analysis/1"
    QUESTION_ANALYSIS_VERSION = "cth-bmp-domain-analysis/2"
    CURRENT_ANALYSIS_VERSION = "cth-bmp-domain-analysis/3"
    REVISED_RESEARCH_GENERATION = "OPERATOR_REVISED_DERIVED_RECOMMENDATION"
    FEATURE = "CTH_BMP_DECISION_WORK"
    KINDS = {"venue_operations", "consumer_risk", "brand_market", "creator_campaign"}

    def __init__(self, *, internal_action_reader=None, action_actor=None, source_actor=None):
        # W6 binds the observed read_internal_pitch(task_id, *, actor, scope)
        # callable and server principal. Never load owner candidates implicitly
        # or take a reader/principal/receipt from an HTTP/model payload.
        self._internal_action_reader = internal_action_reader
        self._action_actor = action_actor
        self._source_actor = source_actor

    @staticmethod
    def _action_scope(scope):
        return {"domain_id": scope["domain_id"], "subject_id": scope.get("subject_id"),
                "brand_focus_id": scope.get("brand_focus_id"), "global_scope": scope["global"]}

    def _read_action(self, task_id, actor_ref, scope, authorize):
        """Consume the frozen Shared reader, not a caller-supplied receipt."""
        self._text(task_id, 256)
        if not callable(self._internal_action_reader) or self._action_actor is None:
            raise RuntimeError("BUSINESS_WORK_ACTION_OWNER_NOT_BOUND")
        self._authorize(authorize, actor_ref, scope, "read")
        owner_scope = self._action_scope(scope)
        observed = self._internal_action_reader(task_id, actor=self._action_actor, scope=owner_scope)
        self._authorize(authorize, actor_ref, scope, "read")
        if (not isinstance(observed, dict) or observed.get("task_id") != task_id
                or observed.get("scope") != owner_scope
                or observed["scope"].get("global_scope") is not owner_scope["global_scope"]):
            raise PermissionError("BUSINESS_WORK_ACTION_CONTEXT_MISMATCH")
        if observed.get("state") != "succeeded" or observed.get("error") is not None:
            raise RuntimeError("BUSINESS_WORK_ACTION_NOT_COMMITTED")
        receipt, work = observed.get("action_receipt"), observed.get("work")
        if not isinstance(receipt, dict) or not isinstance(work, dict):
            raise RuntimeError("BUSINESS_WORK_ACTION_RECEIPT_INVALID")
        committed, doc, artifact = work.get("receipt"), work.get("document"), work.get("artifact")
        if not all(isinstance(item, dict) for item in (committed, doc, artifact)):
            raise RuntimeError("BUSINESS_WORK_ACTION_RECEIPT_INVALID")
        context = doc.get("context", {})
        actor_matches = isinstance(context, dict) and context.get("principal_ref") == actor_ref
        if isinstance(self._action_actor, dict) and type(self._action_actor.get("id")) is int:
            actor_matches = (isinstance(context, dict)
                             and context.get("actor_id") == self._action_actor["id"]
                             and actor_ref == f"actor:{self._action_actor['id']}"
                             and "principal_ref" not in context)
        if (not actor_matches
                or any(context.get(k) != v for k, v in owner_scope.items())
                or receipt.get("scope") != owner_scope or committed.get("scope") != owner_scope
                or context.get("global_scope") is not owner_scope["global_scope"]
                or receipt["scope"].get("global_scope") is not owner_scope["global_scope"]
                or committed["scope"].get("global_scope") is not owner_scope["global_scope"]):
            raise PermissionError("BUSINESS_WORK_ACTION_CONTEXT_MISMATCH")
        # W4's exact historical ShotPlan contract and explicit manuscript-only
        # contract. Shared verifies the sealed task input, committed bytes and
        # unchanged work contract; never infer a profile from missing content.
        contract = committed.get("contract")
        supported_contracts = (
            {"id": "lumenis.internal-pitch", "version": "1",
             "required_payload_paths": ["manuscript", "shot_plan", "truth_state"]},
            {"id": "lumenis.internal-pitch", "version": "2",
             "required_payload_paths": ["manuscript", "input_manifest", "truth_state"]},
            {"id": "lumenis.internal-pitch", "version": "3",
             "required_payload_paths": ["manuscript", "upstream_binding", "truth_state"]},
            {"id": "lumenis.internal-pitch", "version": "4",
             "required_payload_paths": ["manuscript", "truth_state"]},
            {"id": "lumenis.internal-pitch", "version": "5",
             "required_payload_paths": ["manuscript", "audiovisual_plan", "truth_state"]},
        )
        if (receipt.get("owner") != "Shared ContentCreation/TaskEngine/SavedWork"
                or receipt.get("action_kind") != ("INTERNAL_TEXT_CREATION" if receipt.get("version") == 1 else "INTERNAL_TEXT_REVISION")
                or receipt.get("execution_state") != "ARTIFACT_COMMITTED"
                or receipt.get("business_outcome") != "NOT_OBSERVED"
                or receipt.get("external_effect") != "NOT_PERFORMED"
                or receipt.get("task_id") != task_id or doc.get("task_id") != task_id
                or committed.get("task_id") != task_id
                or committed.get("schema") != "lumenis.committed-saved-work/v1"
                or contract not in supported_contracts or doc.get("contract") != contract):
            raise RuntimeError("BUSINESS_WORK_ACTION_RECEIPT_INVALID")
        checks = committed.get("constraint_observations", {})
        if (not isinstance(checks, dict) or checks.get("committed_bytes_match") is not True
                or checks.get("parent_chain_verified") is not True):
            raise RuntimeError("BUSINESS_WORK_ACTION_RECEIPT_INVALID")
        for key in ("work_id", "version"):
            if receipt.get(key) != committed.get(key) or receipt.get(key) != doc.get(key):
                raise RuntimeError("BUSINESS_WORK_ACTION_RECEIPT_INVALID")
        if type(committed.get("version")) is not int or type(doc.get("version")) is not int:
            raise RuntimeError("BUSINESS_WORK_ACTION_RECEIPT_INVALID")
        for action_key, committed_key in (("artifact_id", "ref"), ("sha256", "sha256"), ("size_bytes", "size_bytes")):
            if (receipt.get(action_key) != committed.get(committed_key)
                    or receipt.get(action_key) != artifact.get(action_key)):
                raise RuntimeError("BUSINESS_WORK_ACTION_RECEIPT_INVALID")
        parent = committed.get("parent")
        if not isinstance(parent, dict) or parent != {"ref": receipt.get("parent_artifact_id"), "sha256": receipt.get("parent_sha256")}:
            raise RuntimeError("BUSINESS_WORK_ACTION_RECEIPT_INVALID")
        if any(doc.get(k) != receipt.get(k) for k in ("parent_artifact_id", "parent_sha256")):
            raise RuntimeError("BUSINESS_WORK_ACTION_RECEIPT_INVALID")
        import re
        if (type(receipt.get("version")) is not int or receipt["version"] < 1
                or type(receipt.get("size_bytes")) is not int or receipt["size_bytes"] < 1
                or not isinstance(receipt.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", receipt["sha256"])):
            raise RuntimeError("BUSINESS_WORK_ACTION_RECEIPT_INVALID")
        for key in ("artifact_id", "work_id"):
            self._text(receipt.get(key), 256)
        if receipt["version"] == 1:
            if parent != {"ref": None, "sha256": None}:
                raise RuntimeError("BUSINESS_WORK_ACTION_PARENT_INVALID")
        elif (not isinstance(parent["ref"], str) or not parent["ref"]
              or not isinstance(parent["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", parent["sha256"])):
            raise RuntimeError("BUSINESS_WORK_ACTION_PARENT_INVALID")
        output = receipt.get("output")
        if (not isinstance(output, dict) or doc.get("attachments") != [output]
                or type(output.get("size_bytes")) is not int or output["size_bytes"] < 1
                or not isinstance(output.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", output["sha256"])):
            raise RuntimeError("BUSINESS_WORK_ACTION_OUTPUT_INVALID")
        for key in ("artifact_id", "name", "media_type"):
            self._text(output.get(key), 256)
        # Store only immutable lineage, not owner content, grants or source
        # statements. Shared remains the authority for bytes and source uses.
        return json.loads(self._json(receipt))

    def _verify_actions(self, history, actor_ref, scope, authorize):
        actions = [e["outputs"]["action"] for e in history if e["inputs"]["operation"] == "action"]
        if not actions:
            return {"state": "NOT_REQUESTED"}
        if not callable(self._internal_action_reader) or self._action_actor is None:
            return {"state": "UNAVAILABLE", "reason": "ACTION_OWNER_NOT_BOUND"}
        for action in actions:
            if self._read_action(action["receipt"]["task_id"], actor_ref, scope, authorize) != action["receipt"]:
                raise RuntimeError("BUSINESS_WORK_ACTION_RECEIPT_CHANGED")
        return {"state": "FRESH_OWNER_VERIFIED", "count": len(actions)}

    def _resources(self, value):
        """Preserve operator constraints; estimates are neither quotes nor spend."""
        from decimal import Decimal, InvalidOperation
        from datetime import datetime
        import re
        keys = {"budget_amount", "estimated_cost_amount", "currency", "as_of", "limits"}
        if not isinstance(value, dict) or set(value) != keys:
            raise ValueError("BUSINESS_WORK_RESOURCE_CONSTRAINTS_INVALID")
        for key in ("budget_amount", "estimated_cost_amount"):
            amount = value[key]
            if amount is not None:
                try:
                    if not isinstance(amount, str) or len(amount) > 40 or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", amount):
                        raise ValueError("BUSINESS_WORK_RESOURCE_AMOUNT_INVALID")
                    if not Decimal(amount).is_finite() or Decimal(amount) < 0:
                        raise ValueError("BUSINESS_WORK_RESOURCE_AMOUNT_INVALID")
                except InvalidOperation as exc:
                    raise ValueError("BUSINESS_WORK_RESOURCE_AMOUNT_INVALID") from exc
        currency, as_of = value["currency"], value["as_of"]
        if currency is not None and (not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency)):
            raise ValueError("BUSINESS_WORK_RESOURCE_CURRENCY_INVALID")
        if as_of is not None:
            self._text(as_of, 80)
            if datetime.fromisoformat(as_of.replace("Z", "+00:00")).tzinfo is None:
                raise ValueError("BUSINESS_WORK_RESOURCE_TIMEZONE_REQUIRED")
        if any(value[k] is not None for k in ("budget_amount", "estimated_cost_amount")) and (currency is None or as_of is None):
            raise ValueError("BUSINESS_WORK_RESOURCE_BASIS_REQUIRED")
        if not isinstance(value["limits"], list) or not 1 <= len(value["limits"]) <= 8:
            raise ValueError("BUSINESS_WORK_RESOURCE_LIMITS_REQUIRED")
        for limit in value["limits"]:
            self._text(limit)
        known = value["budget_amount"] is not None and value["estimated_cost_amount"] is not None
        return {**value, "claim_type": "OPERATOR_CONSTRAINT_AND_ESTIMATE", "actual_spend": None,
                "budget_fit": ("OVER_BUDGET" if Decimal(value["estimated_cost_amount"]) > Decimal(value["budget_amount"])
                               else "WITHIN_OPERATOR_ESTIMATE") if known else "UNKNOWN"}

    @staticmethod
    def _timestamp(value):
        from datetime import datetime
        BusinessDecisionWorkflow._text(value, 80)
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("BUSINESS_WORK_TIME_INVALID") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("BUSINESS_WORK_TIMEZONE_REQUIRED")
        return parsed

    @staticmethod
    def _amount(value, *, nonnegative=False):
        import re
        from decimal import Decimal
        if (not isinstance(value, str) or len(value) > 40
                or not re.fullmatch(r"-?[0-9]+(?:\.[0-9]+)?", value)):
            raise ValueError("BUSINESS_WORK_OBSERVATION_AMOUNT_INVALID")
        amount = Decimal(value)
        if not amount.is_finite() or (nonnegative and amount < 0):
            raise ValueError("BUSINESS_WORK_OBSERVATION_AMOUNT_INVALID")
        return amount

    @staticmethod
    def _money_sum(values):
        from decimal import Decimal, localcontext
        with localcontext() as context:
            context.prec = 100
            return sum((Decimal(value) for value in values), Decimal(0))

    def _source_claim(self, connection, payload, actor_ref, scope):
        """Retain the permitted original; operator transcription is not verification."""
        import hashlib
        self._text(payload["source_job_id"], 256)
        self._text(payload["source_id"], 256)
        report = self._report(connection, payload["source_job_id"], actor_ref, scope)
        if payload["source_id"] not in {s["source_id"] for s in report["source_brief"]["records"]}:
            raise PermissionError("BUSINESS_WORK_OUTCOME_SOURCE_INVALID")
        quote = self._text(payload["quote"], 1200)
        body = self._outcome_material(connection, report, actor_ref, scope, payload["source_id"], quote)
        if quote not in body:
            raise ValueError("BUSINESS_WORK_OUTCOME_QUOTE_NOT_IN_SOURCE")
        return {key: payload[key] for key in ("source_job_id", "source_id", "quote")} | {
            "report_hash": report["row"]["artifact_hash"],
            "body_sha256": hashlib.sha256(body.encode()).hexdigest(),
            "claim_type": "OPERATOR_PROVIDED_SOURCE_CLAIM",
            "independent_verification": "NOT_VERIFIED", "causation": "NOT_ESTABLISHED"}

    def _manual_action(self, connection, payload, actor_ref, scope, option_id):
        import hashlib
        if payload["option_id"] != option_id:
            raise RuntimeError("BUSINESS_WORK_ACTION_SELECTED_OPTION_REQUIRED")
        for key in ("performer", "exact_target", "limits"):
            self._text(payload[key])
        self._timestamp(payload["performed_at"])
        claim = self._source_claim(connection, payload, actor_ref, scope)
        identity = {key: payload[key] for key in ("option_id", "performer", "exact_target", "performed_at")}
        digest = hashlib.sha256(self._json({**identity, "scope": scope, "actor_ref": actor_ref}).encode()).hexdigest()
        return {**identity, "limits": payload["limits"], "source_claim": claim,
                "operation_digest": digest, "action_kind": "MANUAL_EXECUTION",
                "recorded_by": actor_ref, "execution_state": "REPORTED_PERFORMED",
                "independent_verification": "NOT_VERIFIED", "approval": "NOT_GRANTED_BY_RECORD",
                "external_effect": "NOT_PERFORMED_BY_LUMENIS", "business_outcome": "NOT_OBSERVED"}

    def _cost_action_binding(self, action_id, prior):
        """Bind a transcription to the declared action version; never infer one."""
        if action_id is None:
            return None
        import hashlib
        self._text(action_id, 160)
        plan = self._work_domain_plan(prior or {})
        action = next((item for item in (plan or {}).get('actions', []) if item['action_id'] == action_id), None)
        if action is None:
            raise ValueError('BUSINESS_WORK_COST_ACTION_NOT_FOUND')
        return {'action_id': action_id, 'plan_sha256': hashlib.sha256(self._json(plan).encode()).hexdigest(),
                'action_sha256': hashlib.sha256(self._json(action).encode()).hexdigest(),
                'target': action['target'], 'responsible': action['responsible'],
                'deliverable': action['deliverable'], 'cost_estimate': action['cost_estimate'],
                'claim_type': 'OPERATOR_DECLARED_COST_ASSOCIATION', 'causation': 'NOT_ESTABLISHED'}

    @staticmethod
    def _active_cost_entries(ledger):
        superseded = {entry['supersedes_entry_id'] for entry in ledger if entry.get('supersedes_entry_id')}
        return [entry for entry in ledger if entry['entry_id'] not in superseded]

    @staticmethod
    def _cost_origin(entry, by_id):
        seen = set()
        while entry.get('supersedes_entry_id'):
            if entry['entry_id'] in seen:
                raise ValueError('BUSINESS_WORK_COST_RELATION_CYCLE')
            seen.add(entry['entry_id'])
            entry = by_id[entry['supersedes_entry_id']]
        return entry['entry_id']

    def _cost_totals(self, ledger, *, extended=False):
        """Amounts are reported inputs; absence and explicit unknown remain distinct."""
        totals = {}
        for entry in self._active_cost_entries(ledger):
            total = totals.setdefault(entry['currency'], {kind: None for kind in ('ESTIMATE', 'COMMITTED', 'ACTUAL', 'REFUND')})
            if extended:
                total.setdefault('known_subtotals', {kind: None for kind in ('ESTIMATE', 'COMMITTED', 'ACTUAL', 'REFUND')})
                total.setdefault('unknown_amount_counts', {kind: 0 for kind in ('ESTIMATE', 'COMMITTED', 'ACTUAL', 'REFUND')})
            if entry['amount'] is None:
                total['unknown_amount_counts'][entry['kind']] += 1
            else:
                key = total['known_subtotals'] if extended else total
                key[entry['kind']] = str(self._money_sum((key[entry['kind']] or '0', entry['amount'])))
        for total in totals.values():
            if extended:
                for kind in ('ESTIMATE', 'COMMITTED', 'ACTUAL', 'REFUND'):
                    total[kind] = None if total['unknown_amount_counts'][kind] else total['known_subtotals'][kind]
            total['net_actual'] = (str(self._money_sum((total['ACTUAL'], '-' + (total['REFUND'] or '0'))))
                if total['ACTUAL'] is not None and not (extended and total['unknown_amount_counts']['REFUND']) else None)
        return totals

    def _record_observed_costs(self, costs, previous_costs, claim, observed_at, prior):
        """Append source-supported corrections without overwriting original records."""
        import re
        from decimal import Decimal
        base = {'entry_id', 'kind', 'amount', 'currency', 'related_entry_id'}
        extra = {'plan_action_id', 'occurred_at', 'supersedes_entry_id', 'correction_reason'}
        if any(not isinstance(cost, dict) or not base <= set(cost) or set(cost) - base - extra for cost in costs):
            raise ValueError('BUSINESS_WORK_COST_INVALID')
        ledger = list(previous_costs)
        by_id = {entry['entry_id']: entry for entry in ledger}
        submitted_ids = set()
        for cost in costs:
            self._text(cost['entry_id'], 160)
            if cost['entry_id'] in submitted_ids:
                raise ValueError('BUSINESS_WORK_COST_DUPLICATE')
            submitted_ids.add(cost['entry_id'])
            if not isinstance(cost['kind'], str) or cost['kind'] not in {'ESTIMATE', 'COMMITTED', 'ACTUAL', 'REFUND'}:
                raise ValueError('BUSINESS_WORK_COST_KIND_INVALID')
            if cost['amount'] is not None:
                self._amount(cost['amount'], nonnegative=True)
            if not isinstance(cost['currency'], str) or not re.fullmatch(r'[A-Z]{3}', cost['currency']):
                raise ValueError('BUSINESS_WORK_RESOURCE_CURRENCY_INVALID')
            for key in ('related_entry_id', 'supersedes_entry_id', 'plan_action_id'):
                if cost.get(key) is not None:
                    self._text(cost[key], 160)
            if cost.get('occurred_at') is not None and self._timestamp(cost['occurred_at']) > self._timestamp(observed_at):
                raise ValueError('BUSINESS_WORK_COST_EVENT_AFTER_OBSERVATION')
            if cost.get('supersedes_entry_id'):
                self._text(cost.get('correction_reason'))
            elif cost.get('correction_reason') is not None:
                raise ValueError('BUSINESS_WORK_COST_CORRECTION_BASIS_REQUIRED')
        pending = list(costs)
        while pending:
            progressed = False
            for cost in list(pending):
                original = by_id.get(cost['entry_id'])
                if original:
                    if any(original.get(key) != value for key, value in cost.items()):
                        raise ValueError('BUSINESS_WORK_COST_ID_CONFLICT')
                    pending.remove(cost)
                    progressed = True
                    continue
                dependencies = [cost.get('supersedes_entry_id')]
                if cost['kind'] == 'REFUND':
                    dependencies.append(cost['related_entry_id'])
                if any(key is not None and key not in by_id for key in dependencies):
                    continue
                replacement = by_id.get(cost.get('supersedes_entry_id'))
                if replacement:
                    if (replacement['kind'] != cost['kind'] or replacement['currency'] != cost['currency']
                            or replacement.get('related_entry_id') != cost['related_entry_id']):
                        raise ValueError('BUSINESS_WORK_COST_CORRECTION_IDENTITY_CHANGED')
                    if replacement['entry_id'] not in {item['entry_id'] for item in self._active_cost_entries(ledger)}:
                        raise ValueError('BUSINESS_WORK_COST_CORRECTION_SUPERSEDED')
                    planned = replacement.get('planned_action')
                    if 'plan_action_id' in cost and cost['plan_action_id'] != replacement.get('plan_action_id'):
                        raise ValueError('BUSINESS_WORK_COST_CORRECTION_ACTION_CHANGED')
                elif cost['kind'] == 'REFUND':
                    parent = by_id.get(cost['related_entry_id'])
                    if not parent or parent['kind'] != 'ACTUAL' or parent['currency'] != cost['currency']:
                        raise ValueError('BUSINESS_WORK_REFUND_BASIS_REQUIRED')
                    planned = parent.get('planned_action')
                    if 'plan_action_id' in cost and cost['plan_action_id'] != parent.get('plan_action_id'):
                        raise ValueError('BUSINESS_WORK_REFUND_ACTION_MISMATCH')
                else:
                    if cost['related_entry_id'] is not None:
                        raise ValueError('BUSINESS_WORK_COST_RELATION_INVALID')
                    planned = self._cost_action_binding(cost.get('plan_action_id'), prior)
                entry = {**cost, 'source_claim': claim, 'observed_at': observed_at,
                         'claim_type': 'OPERATOR_TRANSCRIPTION', 'independent_verification': 'NOT_VERIFIED'}
                if planned is not None:
                    entry.update(planned_action=planned, plan_action_id=planned['action_id'])
                if cost['kind'] == 'REFUND':
                    parent = by_id.get(cost['related_entry_id'])
                    if not parent or parent['kind'] != 'ACTUAL' or parent['currency'] != cost['currency']:
                        raise ValueError('BUSINESS_WORK_REFUND_BASIS_REQUIRED')
                    if (entry.get('occurred_at') and parent.get('occurred_at') and
                            self._timestamp(entry['occurred_at']) < self._timestamp(parent['occurred_at'])):
                        raise ValueError('BUSINESS_WORK_REFUND_EVENT_BEFORE_ACTUAL')
                ledger.append(entry)
                by_id[entry['entry_id']] = entry
                pending.remove(cost)
                progressed = True
            if not progressed:
                missing_refunds = any(cost['kind'] == 'REFUND' and cost['related_entry_id'] not in by_id
                                      and cost['related_entry_id'] not in submitted_ids for cost in pending)
                raise ValueError('BUSINESS_WORK_REFUND_BASIS_REQUIRED' if missing_refunds else
                                 'BUSINESS_WORK_COST_CORRECTION_BASIS_REQUIRED')
        # The cap applies to the current corrected actual and active refunds,
        # even when a later observation corrects an earlier transcription.
        active = self._active_cost_entries(ledger)
        for actual in (entry for entry in active if entry['kind'] == 'ACTUAL'):
            origin = self._cost_origin(actual, by_id)
            refunds = [entry for entry in active if entry['kind'] == 'REFUND'
                       and self._cost_origin(by_id[entry['related_entry_id']], by_id) == origin]
            known_refunds = self._money_sum(entry['amount'] for entry in refunds if entry['amount'] is not None)
            if actual['amount'] is not None and known_refunds > Decimal(actual['amount']):
                raise ValueError('BUSINESS_WORK_REFUND_EXCEEDS_ACTUAL')
            if actual.get('occurred_at') and any(entry.get('occurred_at') and
                    self._timestamp(entry['occurred_at']) < self._timestamp(actual['occurred_at']) for entry in refunds):
                raise ValueError('BUSINESS_WORK_REFUND_EVENT_BEFORE_ACTUAL')
        extended = any(entry['amount'] is None or set(entry) & extra for entry in ledger)
        return ledger, self._cost_totals(ledger, extended=extended), extended

    def _action_cost_review(self, observation, prior):
        """Compare the current declared plan with its exact reported cost versions."""
        import hashlib
        plan = self._work_domain_plan(prior or {})
        plan_hash = hashlib.sha256(self._json(plan).encode()).hexdigest() if plan else None
        active = self._active_cost_entries(observation['cost_ledger'])
        actions, matched_ids = [], set()
        for action in (plan or {}).get('actions', []):
            action_hash = hashlib.sha256(self._json(action).encode()).hexdigest()
            records = [entry for entry in active if (entry.get('planned_action') or {}).get('action_id') == action['action_id']
                       and (entry.get('planned_action') or {}).get('action_sha256') == action_hash]
            matched_ids.update(entry['entry_id'] for entry in records)
            totals = self._cost_totals(records, extended=True)
            estimate = action['cost_estimate']
            matching = totals.get(estimate['currency'], {}) if estimate else {}
            net = matching.get('net_actual')
            remaining = self._decimal_remaining(estimate['amount'], net) if estimate else None
            foreign = sorted(set(totals) - ({estimate['currency']} if estimate else set()))
            actions.append({'action_id': action['action_id'], 'plan_sha256': plan_hash,
                'declared_estimate': estimate, 'reported_costs': totals,
                'remaining_against_declared_estimate': remaining,
                'unconverted_cost_currencies': foreign,
                'estimate_comparison': 'UNKNOWN' if remaining is None else
                    'PARTIAL_CURRENCY_CONVERSION_REQUIRED' if foreign else
                    'OVER_DECLARED_ESTIMATE' if self._amount(remaining) < 0 else 'WITHIN_DECLARED_ESTIMATE',
                'entry_ids': [entry['entry_id'] for entry in records],
                'retained_prior_plan_entry_ids': [entry['entry_id'] for entry in records
                    if entry['planned_action']['plan_sha256'] != plan_hash],
                'execution_state': 'NOT_ESTABLISHED_BY_COST', 'financial_verification': 'NOT_VERIFIED'})
        unmatched = [entry for entry in active if entry['entry_id'] not in matched_ids]
        by_id = {entry['entry_id']: entry for entry in observation['cost_ledger']}
        current_actual = {self._cost_origin(entry, by_id): entry for entry in active if entry['kind'] == 'ACTUAL'}
        refund_checks = []
        for refund in (entry for entry in active if entry['kind'] == 'REFUND'):
            actual = current_actual[self._cost_origin(by_id[refund['related_entry_id']], by_id)]
            refunds = [entry for entry in active if entry['kind'] == 'REFUND'
                       and self._cost_origin(by_id[entry['related_entry_id']], by_id) == self._cost_origin(actual, by_id)]
            refund_checks.append({'entry_id': refund['entry_id'], 'original_actual_entry_id': refund['related_entry_id'],
                'current_actual_entry_id': actual['entry_id'],
                'state': 'AMOUNT_UNKNOWN_CAP_NOT_ESTABLISHED' if actual['amount'] is None or any(entry['amount'] is None for entry in refunds)
                         else 'REPORTED_AMOUNTS_WITHIN_ACTUAL',
                'event_time_state': 'REPORTED_EVENT_ORDER_CHECKED' if refund.get('occurred_at') and actual.get('occurred_at')
                                    else 'EVENT_TIME_UNKNOWN'})
        return {'recipe': 'declared-action-observed-cost-review/1', 'plan_sha256': plan_hash,
                'actions': actions, 'unallocated_entry_ids': [entry['entry_id'] for entry in unmatched if not entry.get('planned_action')],
                'prior_plan_entry_ids': [entry['entry_id'] for entry in unmatched if entry.get('planned_action')],
                'unmatched_reported_costs': self._cost_totals(unmatched, extended=True),
                'active_entry_ids': [entry['entry_id'] for entry in active],
                'superseded_entry_ids': [entry['entry_id'] for entry in observation['cost_ledger'] if entry not in active],
                'refund_checks': refund_checks,
                'claim_type': 'CALCULATED_FROM_OPERATOR_REPORTED_COSTS', 'currency_conversion': 'NOT_PERFORMED',
                'profit': None, 'causal_roi': None, 'spending_authorization': 'NOT_GRANTED'}

    def _observation(self, connection, payload, actor_ref, scope, previous_costs, previous_observation=None, prior=None):
        import re
        from decimal import Decimal
        observed = self._timestamp(payload["observed_at"])
        window = payload["window"]
        if not isinstance(window, dict) or set(window) != {"start", "end"}:
            raise ValueError("BUSINESS_WORK_OBSERVATION_WINDOW_INVALID")
        start, end = self._timestamp(window["start"]), self._timestamp(window["end"])
        if start >= end or observed < end:
            raise ValueError("BUSINESS_WORK_OBSERVATION_WINDOW_INVALID")
        self._text(payload["limits"])
        claim = self._source_claim(connection, payload, actor_ref, scope)
        if not all(isinstance(payload[key], list) for key in ("metrics", "costs")):
            raise ValueError("BUSINESS_WORK_OBSERVATION_ITEMS_INVALID")
        metrics, names = [], set()
        for metric in payload["metrics"]:
            if not isinstance(metric, dict) or set(metric) != {"name", "definition", "value", "unit", "numerator", "denominator"}:
                raise ValueError("BUSINESS_WORK_OBSERVATION_METRIC_INVALID")
            for key in ("name", "definition", "unit"):
                self._text(metric[key])
            if metric["name"] in names:
                raise ValueError("BUSINESS_WORK_OBSERVATION_METRIC_DUPLICATE")
            names.add(metric["name"])
            for key in ("value", "numerator", "denominator"):
                if metric[key] is not None:
                    self._amount(metric[key], nonnegative=key == "denominator")
            if (metric["numerator"] is None) != (metric["denominator"] is None):
                raise ValueError("BUSINESS_WORK_OBSERVATION_RATIO_BASIS_REQUIRED")
            denominator = Decimal(metric["denominator"]) if metric["denominator"] is not None else None
            metrics.append({**metric, "claim_type": "OPERATOR_TRANSCRIPTION",
                            "independent_verification": "NOT_VERIFIED",
                            "source_claim": claim, "observed_at": payload["observed_at"],
                            "window": dict(window), "limits": payload["limits"],
                            "ratio": str(Decimal(metric["numerator"]) / denominator) if denominator else None,
                            "ratio_state": "ZERO_DENOMINATOR" if denominator == 0 else
                                           "CALCULATED_FROM_REPORTED_INPUTS" if denominator else "NOT_REQUESTED"})
        ledger, totals, extended_costs = self._record_observed_costs(
            payload['costs'], previous_costs, claim, payload['observed_at'], prior)
        previous_observation = previous_observation or {}
        retained_metrics = {
            item["name"]: {**item,
                           "source_claim": item.get("source_claim", previous_observation.get("source_claim")),
                           "observed_at": item.get("observed_at", previous_observation.get("observed_at")),
                           "window": item.get("window", previous_observation.get("window")),
                           "limits": item.get("limits", previous_observation.get("limits"))}
            for item in previous_observation.get("metrics", [])}
        for metric in metrics:
            retained_metrics[metric["name"]] = metric
        metric_history = list(previous_observation.get("metric_observations", []))
        if not metric_history and previous_observation.get("metrics"):
            metric_history.append({key: previous_observation[key] for key in
                                   ("source_claim", "observed_at", "window", "limits", "metrics")})
        if metrics:
            metric_history.append({"source_claim": claim, "observed_at": payload["observed_at"],
                                   "window": dict(window), "limits": payload["limits"], "metrics": metrics})
        result = {key: payload[key] for key in ("observed_at", "window", "limits")} | {
            "metrics": list(retained_metrics.values()), "metric_updates": metrics,
            "metric_observations": metric_history,
            "source_claim": claim, "cost_ledger": ledger, "cost_totals": totals,
            "claim_type": "OPERATOR_REPORTED_OBSERVATION", "independent_verification": "NOT_VERIFIED",
            "causation": "NOT_ESTABLISHED", "attribution": "NOT_ESTABLISHED"}
        if extended_costs or self._work_domain_plan(prior or {}) is not None:
            result['action_cost_review'] = self._action_cost_review(result, prior)
        return result

    def _observation_result(self, observation, decision, previous, previous_revision):
        """Deterministic business arithmetic over explicitly attributed operator inputs."""
        from decimal import Decimal
        resources = decision.get("resource_constraints") or {}
        currency, budget = resources.get("currency"), resources.get("budget_amount")
        totals = observation["cost_totals"].get(currency, {})
        actual = totals.get("net_actual")
        foreign = sorted(set(observation["cost_totals"]) - ({currency} if currency else set()))
        remaining = str(self._money_sum((budget, "-" + actual))) if budget is not None and actual is not None else None
        result = {"budget_amount": budget, "currency": currency,
                  "budget_as_of": resources.get("as_of"), "estimated_cost_amount": resources.get("estimated_cost_amount"),
                  "reported_actual_amount": totals.get("ACTUAL"), "reported_refund_amount": totals.get("REFUND"),
                  "reported_net_actual_amount": actual, "remaining_budget_amount": remaining,
                  "unconverted_cost_currencies": foreign,
                  "state": "UNKNOWN" if remaining is None else "PARTIAL_CURRENCY_CONVERSION_REQUIRED" if foreign else
                           "OVER_OPERATOR_BUDGET" if Decimal(remaining) < 0 else "WITHIN_OPERATOR_BUDGET",
                  "claim_type": "CALCULATED_FROM_OPERATOR_REPORTED_COSTS",
                  "financial_verification": "NOT_VERIFIED", "spending_authorization": "NOT_GRANTED",
                  "commitment_treatment": "SEPARATE_NOT_ASSUMED_OUTSTANDING_OR_ADDED_TO_ACTUAL"}
        comparison = {"state": "NO_PRIOR_OBSERVATION", "baseline_revision": None,
                      "causation": "NOT_ESTABLISHED", "items": []}
        updates = observation.get("metric_updates", observation["metrics"])
        if previous and updates:
            comparison.update(state="DESCRIPTIVE_COMPARISON_ONLY", baseline_revision=previous_revision,
                              baseline_window=previous["window"])
            baseline = {metric["name"]: metric for metric in previous["metrics"]}
            for metric in updates:
                prior = baseline.get(metric["name"])
                old_window = prior.get("window", previous["window"]) if prior else previous["window"]
                current_window = metric.get("window", observation["window"])
                old_duration = self._timestamp(old_window["end"]) - self._timestamp(old_window["start"])
                duration = self._timestamp(current_window["end"]) - self._timestamp(current_window["start"])
                reason = ("BASELINE_METRIC_MISSING" if prior is None else
                          "METRIC_DEFINITION_CHANGED" if metric["definition"] != prior["definition"] else
                          "UNIT_CHANGED" if metric["unit"] != prior["unit"] else
                          "WINDOW_DURATION_CHANGED" if duration != old_duration else
                          "VALUE_UNKNOWN" if metric["value"] is None or prior["value"] is None else None)
                before = prior["value"] if prior else None
                delta = str(Decimal(metric["value"]) - Decimal(before)) if reason is None else None
                relative = (str((Decimal(metric["value"]) - Decimal(before)) / Decimal(before))
                            if reason is None and Decimal(before) != 0 else None)
                comparison["items"].append({"name": metric["name"], "unit": metric["unit"],
                    "baseline_value": before, "current_value": metric["value"],
                    "baseline_source_claim": prior.get("source_claim", previous["source_claim"]) if prior else None,
                    "baseline_window": old_window, "current_window": current_window,
                    "difference": delta, "relative_change": relative,
                    "state": "INPUTS_NOT_COMPARABLE" if reason else "REPORTED_VALUE_DIFFERENCE",
                    "reason": reason or ("ZERO_BASELINE_RELATIVE_CHANGE_UNKNOWN" if Decimal(before) == 0 else None),
                    "comparability": "POPULATION_OPERATING_HOURS_SELECTION_AND_CONFOUNDERS_NOT_ESTABLISHED"})
        elif previous:
            comparison["state"] = "NO_NEW_METRIC_OBSERVATION"
        return {**observation, "resource_result": result, "comparison": comparison}

    @staticmethod
    def _work_domain_plan(outputs):
        return ((outputs.get('domain_analysis') or {}).get('question_result', {})
                .get('business_report', {}).get('domain_workbench', {}).get('plan'))

    def _bind_planned_execution(self, record, payload, prior):
        action_id = payload.get('plan_action_id')
        if action_id is None:
            return record
        self._text(action_id, 160)
        plan = self._work_domain_plan(prior)
        action = next((item for item in (plan or {}).get('actions', []) if item['action_id'] == action_id), None)
        if action is None:
            raise ValueError('BUSINESS_WORK_PLANNED_ACTION_NOT_FOUND')
        if record['exact_target'] != action['target'] or record['performer'] != action['responsible']:
            raise ValueError('BUSINESS_WORK_PLANNED_EXECUTION_MISMATCH')
        completed = {item['planned_action']['action_id']: item for item in prior.get('execution_records', [])
                     if item.get('planned_action')}
        if action_id in completed:
            raise ValueError('BUSINESS_WORK_PLANNED_ACTION_ALREADY_RECORDED')
        if not set(action['depends_on']) <= set(completed):
            raise RuntimeError('BUSINESS_WORK_ACTION_DEPENDENCIES_NOT_RECORDED')
        if any(self._timestamp(completed[key]['performed_at']) > self._timestamp(record['performed_at'])
               for key in action['depends_on']):
            raise ValueError('BUSINESS_WORK_ACTION_DEPENDENCY_TIME_INVALID')
        import hashlib
        return {**record, 'planned_action': {'action_id': action_id,
            'plan_sha256': hashlib.sha256(self._json(plan).encode()).hexdigest(),
            'action_sha256': hashlib.sha256(self._json(action).encode()).hexdigest(),
            'deliverable': action['deliverable'], 'due_at': action['due_at'],
            'timeliness': ('DUE_TIME_UNKNOWN' if action['due_at'] is None else
                          'REPORTED_LATE' if self._timestamp(record['performed_at']) > self._timestamp(action['due_at'])
                          else 'REPORTED_WITHIN_DEADLINE'),
            'dependency_receipts': [completed[key]['operation_digest'] for key in action['depends_on']],
            'verification': 'OPERATOR_REPORTED_NOT_INDEPENDENTLY_VERIFIED'}}

    def _domain_target_review(self, observation, prior):
        """Describe comparable reported results against operator-declared targets.

        A numerical gap is not a causal effect or a success decision. Different
        definitions, units or windows do not yield a computed comparison.
        """
        plan = self._work_domain_plan(prior)
        if plan is None:
            return None
        from decimal import Decimal, localcontext
        import hashlib
        reviews = []
        metrics = {item['name']: item for item in observation['metrics']}
        for action in plan['actions']:
            target = action['success_measure']
            if target is None:
                reviews.append({'action_id': action['action_id'], 'state': 'TARGET_NOT_DEFINED',
                                'target_gap': None, 'reported_change_from_declared_baseline': None})
                continue
            metric = metrics.get(target['name'])
            reason = ('METRIC_NOT_REPORTED' if metric is None else
                      'METRIC_DEFINITION_CHANGED' if metric['definition'] != target['definition'] else
                      'UNIT_CHANGED' if metric['unit'] != target['unit'] else
                      'WINDOW_CHANGED' if any(self._timestamp(metric['window'][key]) != self._timestamp(target['window'][key])
                                               for key in ('start', 'end')) else
                      'VALUE_UNKNOWN' if metric['value'] is None or target['target_value'] is None else None)
            gap, change = None, None
            if reason is None:
                # Domain amounts may exceed the ambient Decimal precision.
                with localcontext() as context:
                    context.prec = max(64, sum(len(str(value or '')) for value in
                        (metric['value'], target['target_value'], target['baseline_value'])) + 8)
                    gap = str(Decimal(metric['value']) - Decimal(target['target_value']))
                    if target['baseline_value'] is not None:
                        change = str(Decimal(metric['value']) - Decimal(target['baseline_value']))
            reviews.append({'action_id': action['action_id'], 'metric': target['name'],
                'state': reason or 'REPORTED_TARGET_COMPARISON', 'target': target,
                'reported_value': metric['value'] if metric else None, 'target_gap': gap,
                'reported_change_from_declared_baseline': change,
                'source_claim': metric.get('source_claim') if metric else None,
                'metric_observed_at': metric.get('observed_at') if metric else None,
                'business_success': 'REQUIRES_OPERATOR_JUDGMENT', 'causation': 'NOT_ESTABLISHED'})
        return {'method': 'declared_plan_reported_outcome_comparison/1', 'actions': reviews,
                'plan_sha256': hashlib.sha256(self._json(plan).encode()).hexdigest(),
                'baseline_claim': 'OPERATOR_DECLARED_NOT_INDEPENDENTLY_OBSERVED',
                'attribution': 'NOT_ESTABLISHED', 'causation': 'NOT_ESTABLISHED'}

    def _domain_execution_progress(self, outputs):
        plan = self._work_domain_plan(outputs)
        if plan is None:
            return None
        completed = {item['planned_action']['action_id']: item for item in outputs.get('execution_records', [])
                     if item.get('planned_action')}
        target_review = (outputs.get('observation') or {}).get('domain_target_review') or {}
        import hashlib
        current_targets = target_review.get('plan_sha256') == hashlib.sha256(self._json(plan).encode()).hexdigest()
        by_target = {item['action_id']: item for item in target_review.get('actions', [])} if current_targets else {}
        costs = (outputs.get('observation') or {}).get('action_cost_review') or {}
        current_costs = costs.get('plan_sha256') == hashlib.sha256(self._json(plan).encode()).hexdigest()
        by_cost = {item['action_id']: item for item in costs.get('actions', [])} if current_costs else {}
        actions = []
        for item in plan['actions']:
            record = completed.get(item['action_id'])
            waiting = [key for key in item['depends_on'] if key not in completed]
            actions.append({'action_id': item['action_id'], 'target': item['target'],
                'responsible': item['responsible'], 'deliverable': item['deliverable'],
                'due_at': item['due_at'], 'waiting_for': waiting,
                'state': 'REPORTED_PERFORMED' if record else 'WAITING_DEPENDENCY' if waiting else
                         'DECISION_REQUIRED' if not outputs.get('decision') else 'READY_FOR_OPERATOR',
                'execution_record': record, 'target_review': by_target.get(item['action_id']),
                'cost_review': by_cost.get(item['action_id']),
                'external_effect': 'NOT_PERFORMED_BY_LUMENIS'})
        return {'workflow': plan['workflow'], 'objective': plan['objective'], 'actions': actions,
                'reported_performed': len(completed), 'planned': len(actions),
                'target_review_state': ('PRIOR_PLAN_ONLY' if target_review and not current_targets else
                                        'PRIOR_OBSERVATION_ONLY' if outputs.get('outcome_state') == 'PRIOR_OBSERVATION_ONLY' else
                                        'CURRENT_PLAN_REPORTED_INPUTS' if current_targets else 'NOT_OBSERVED'),
                'cost_review_state': 'PRIOR_PLAN_ONLY' if costs and not current_costs else
                                     'PRIOR_OBSERVATION_ONLY' if costs and outputs.get('outcome_state') == 'PRIOR_OBSERVATION_ONLY' else
                                     'CURRENT_PLAN_REPORTED_INPUTS' if current_costs else 'NOT_OBSERVED',
                'business_outcome': outputs.get('business_outcome', 'NOT_OBSERVED'),
                'platform_execution': 'NOT_ESTABLISHED', 'causation': 'NOT_ESTABLISHED'}

    def _carry_prior_observation(self, history, source_job_id, adopted):
        """Retain this work's original records without inheriting a plan's effect."""
        if not history or source_job_id != self._active_origin(history)["inputs"]["payload"]["source_job_id"]:
            return adopted
        previous = history[-1]
        observation = previous["outputs"].get("observation")
        if not observation:
            return adopted
        observation = json.loads(self._json(observation))
        # Source/time/metrics/ledger stay exact. Only the calculation against the
        # newly declared budget changes; it is not a new observed business effect.
        observation["resource_result"] = self._observation_result(
            observation, adopted.get("decision") or {}, {}, None)["resource_result"]
        observation["adoption_lineage"] = {
            "prior_revision": previous["evidence_ref"], "source_job_id": source_job_id,
            "relationship": "PRIOR_RECORDS_NOT_CURRENT_PLAN_EFFECT"}
        return {**adopted, "observation": observation, "outcome_state": "PRIOR_OBSERVATION_ONLY"}

    @classmethod
    def _record_version(cls, outputs):
        if (outputs.get('observation') or {}).get('action_cost_review'):
            return cls.FINANCIAL_OBSERVATION_VERSION
        if outputs.get("execution_records") or outputs.get("observation"):
            return cls.OBSERVATION_VERSION
        if outputs.get("adoption"):
            return cls.REVISION_VERSION
        return (cls.ACTION_VERSION if outputs.get("action") or
                "resource_constraints" in (outputs.get("decision") or {}) else cls.VERSION)

    @staticmethod
    def _json(value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)

    @staticmethod
    def _text(value, maximum=1500):
        if (not isinstance(value, str) or not value.strip() or value != value.strip()
                or len(value) > maximum or any(ord(c) < 32 and c not in "\n\t" for c in value)):
            raise ValueError("BUSINESS_WORK_TEXT_INVALID")
        return value

    def _authorize(self, authorize, actor_ref, scope, operation):
        if not callable(authorize):
            raise PermissionError("BUSINESS_WORK_AUTHORIZATION_REQUIRED")
        receipt = authorize(operation)
        if (not isinstance(receipt, dict) or receipt.get("actor_id") != actor_ref
                or receipt.get("scope") != scope or receipt.get("operation") != operation):
            raise PermissionError("BUSINESS_WORK_AUTHORIZATION_MISMATCH")
        try:
            return {key: self._text(receipt.get(key), 256)
                    for key in ("permission_audit_ref", "operation_audit_ref")}
        except ValueError as exc:
            raise PermissionError("BUSINESS_WORK_AUDIT_REQUIRED") from exc

    def _report(self, connection, job_id, actor_ref, scope, *, require_content=True):
        from lumenis.shared.reporting.source_brief_job import _verify_report, resolve_report_sources
        from lumenis.system.security import permission
        actor = self._source_actor
        if actor is None:
            actor = permission.resolve_local_workspace_principal(module="reports", action="read")
        if actor is None:
            actor = self._action_actor
        if actor is None:
            raise PermissionError("BUSINESS_WORK_SOURCE_ACTOR_REQUIRED")
        # This owner reopens original retained bytes and current SourceUse;
        # neither a signed scope annotation nor a body hash grants content use.
        row = connection.execute(
            "SELECT * FROM daily_reports WHERE report_id=? ORDER BY id DESC LIMIT 1", (job_id,),
        ).fetchone()
        if row is None:
            raise LookupError("BUSINESS_WORK_SOURCE_REPORT_NOT_FOUND")
        verified = _verify_report(dict(row), job_id=job_id, actor_id=actor_ref)
        if not _same_business_scope(verified["snapshot"]["scope"], scope):
            raise PermissionError("SOURCE_BRIEF_SCOPE_MISMATCH")
        import canonical_data
        for source in verified["source_brief"]["records"]:
            record = self._canonical_source(connection, source["source_id"], scope)
            if str(record["scope_evidence_ref"]) != str(source["scope_evidence_ref"]):
                raise PermissionError("BUSINESS_WORK_SOURCE_LINEAGE_CHANGED")
            canonical_data._validate_canonical_scope(connection, canonical_data.CanonicalRecord(
                source_id=source["source_id"], product_id=scope["product_id"], domain_id=scope["domain_id"],
                subject_id=scope.get("subject_id"), brand_focus_id=scope.get("brand_focus_id"),
                scope_status="VERIFIED", scope_evidence_ref=str(source["scope_evidence_ref"])))
        if require_content:
            admitted = resolve_report_sources(job_id, actor=actor, actor_id=actor_ref,
                                              expected_scope=verified["snapshot"]["scope"], connection=connection)
            if not _same_business_scope(admitted["scope"], scope) or admitted["allowed_use"] != "research_reference":
                raise PermissionError("BUSINESS_WORK_DOMAIN_SOURCE_USE_REQUIRED")
            # Consume the current owner projection, not the immutable report's
            # historical analysis. Manual review versions are approval inputs.
            current = admitted["report"]
            verified = {**verified, "hypothesis_review": current.get("hypothesis_review"),
                        "business_analysis": current.get("business_analysis"),
                        "research_analysis": current.get("research_analysis")}

        else:
            # The related lens is an index, not permission to quote source
            # bodies or expose profile compilations/analysis from other scopes.
            brief = dict(verified["source_brief"])
            brief["records"] = [{k: v for k, v in source.items() if k != "profile_research"}
                                for source in brief["records"]]
            brief["markdown"] = "Related source index; full source use requires current SourceUse admission."
            import hashlib
            brief["content_hash"] = hashlib.sha256(brief["markdown"].encode()).hexdigest()
            brief["view_kind"] = "METADATA_INDEX_ONLY"
            verified = {**verified, "source_brief": brief}
        return verified

    @staticmethod
    def _canonical_source(connection, source_id, scope):
        from canonical_data import CANONICAL_SOURCE_LEVEL_PREDICATE
        rows = connection.execute(
            "SELECT * FROM canonical_data WHERE source_id=? AND product_id=? AND domain_id=? "
            "AND COALESCE(subject_id,'')=? AND COALESCE(brand_focus_id,'')=? AND scope_status='VERIFIED' "
            "AND " + CANONICAL_SOURCE_LEVEL_PREDICATE,
            (source_id, scope["product_id"], scope["domain_id"], scope.get("subject_id") or "", scope.get("brand_focus_id") or ""),
        ).fetchall()
        if len(rows) != 1:
            raise PermissionError("BUSINESS_WORK_SOURCE_SCOPE_INVALID")
        return dict(rows[0])

    def _bound_report(self, connection, history, actor_ref, scope):
        origin = self._active_origin(history)
        report = self._report(connection, origin["inputs"]["payload"]["source_job_id"], actor_ref, scope)
        if report["row"]["artifact_hash"] != origin["outputs"]["source_report_hash"]:
            raise RuntimeError("BUSINESS_WORK_SOURCE_REPORT_CHANGED")
        if origin["outputs"].get("hypothesis_review") != report.get("hypothesis_review"):
            raise RuntimeError("BUSINESS_WORK_RESEARCH_REVIEW_CHANGED")
        bindings = origin["outputs"].get("source_body_bindings")
        if bindings is not None and bindings != self._source_bindings(connection, report, scope):
            raise RuntimeError("BUSINESS_WORK_SOURCE_BODY_CHANGED")
        case_id = origin["inputs"]["payload"].get("case_id")
        if case_id:
            case = self._case(connection, case_id, actor_ref, scope)
            if (case["source_job_id"] != report["snapshot"]["job_id"]
                    or case["creation_evidence_ref"] != origin["outputs"].get("case_evidence_ref")):
                raise RuntimeError("BUSINESS_WORK_CASE_BINDING_CHANGED")
        return report

    def _source_bindings(self, connection, report, scope):
        import hashlib
        result = []
        for source in report["source_brief"]["records"]:
            row = self._canonical_source(connection, source["source_id"], scope)
            result.append({"source_id": source["source_id"], "canonical_id": row["canonical_id"],
                           "body_sha256": hashlib.sha256((row.get("content") or "").encode()).hexdigest()})
        return result

    @staticmethod
    def _active_origin(history):
        return next(event for event in reversed(history)
                    if event["inputs"]["operation"] in {"prepare", "adopt"})

    @staticmethod
    def _analysis_origin(history):
        return next(event for event in reversed(history)
                    if event["inputs"]["operation"] in {"prepare", "adopt"}
                    and not (event["outputs"].get("adoption") or {}).get("analysis_retained"))

    def _retains_analysis(self, history, payload):
        if not history:
            return False
        prior = history[-1]["outputs"]
        analysis = prior.get("domain_analysis") or {}
        result = analysis.get("question_result")
        if not result or analysis.get("version") not in {self.QUESTION_ANALYSIS_VERSION, self.CURRENT_ANALYSIS_VERSION}:
            return False
        active = self._active_origin(history)["inputs"]["payload"]
        keys = ("option_id", "proposal", "rationale", "source_ids", "assumptions", "unknowns", "check")
        return (payload.get("source_job_id") == active["source_job_id"]
                and payload.get("question") == active["question"]
                and payload.get("options") == [{key: option[key] for key in keys} for option in prior["options"]]
                and self._planning_constraints(payload.get("planning_constraints", result.get("planning_constraints")))
                == result.get("planning_constraints"))

    @staticmethod
    def _active_history(history):
        origin = BusinessDecisionWorkflow._active_origin(history)
        return history[history.index(origin):]

    @staticmethod
    def _case(connection, case_id, actor_ref, scope):
        from cth_cases import _checked
        from lumenis.shared.database.cth_cases import TABLE
        row = connection.execute(f"SELECT * FROM {TABLE} WHERE case_id=?", (case_id,)).fetchone()
        if row is None:
            raise LookupError("CTH_CASE_NOT_FOUND")
        return _checked(connection, row, actor_ref=actor_ref, expected_scope=scope)

    def _history(self, connection, work_id, actor_ref, scope):
        import re
        from lumenis.shared.evidence import store
        from lumenis.shared.reporting.operator_review import _expected_scope_marker
        if not isinstance(work_id, str) or not re.fullmatch(r"work-[0-9a-f]{64}", work_id):
            raise ValueError("BUSINESS_WORK_ID_INVALID")
        rows = connection.execute(
            "SELECT * FROM app_evidence_records WHERE feature_id=? AND asset_id=? ORDER BY id",
            (self.FEATURE, work_id),
        ).fetchall()
        history, previous = [], None
        for raw in rows:
            row = dict(raw)
            if not store.verify_evidence_record_integrity(row):
                raise RuntimeError("BUSINESS_WORK_SIGNATURE_INVALID")
            inputs, outputs = json.loads(row["inputs_json"]), json.loads(row["outputs_json"])
            if inputs.get("actor_ref") != actor_ref or not _same_business_scope(inputs.get("scope"), scope):
                raise PermissionError("BUSINESS_WORK_CONTEXT_MISMATCH")
            if (row["version"] not in {self.VERSION, self.ACTION_VERSION, self.REVISION_VERSION, self.OBSERVATION_VERSION,
                                      self.FINANCIAL_OBSERVATION_VERSION} or row["source"] != "cth_bmp_business"
                    or row["product_id"] != scope["product_id"] or row["domain_id"] != scope["domain_id"]
                    or row["status"] != "derived" or row["result"] != "RECORDED"
                    or inputs.get("_lumenis_scope") != _expected_scope_marker(inputs["scope"])
                    or inputs.get("parent_ref") != previous or inputs.get("work_id") != work_id
                    or inputs.get("submission_id") != row["test_name"]):
                raise RuntimeError("BUSINESS_WORK_BINDING_INVALID")
            analysis = outputs.get("domain_analysis")
            if analysis is not None:
                self._check_analysis_digest(analysis)
                if (analysis["source_report"]["artifact_hash"] != outputs.get("source_report_hash")
                        or analysis["kind"] != inputs["payload"].get("kind", history[0]["inputs"]["payload"]["kind"] if history else None)):
                    raise RuntimeError("BUSINESS_WORK_ANALYSIS_BINDING_INVALID")
                if analysis["version"] in {self.QUESTION_ANALYSIS_VERSION, self.CURRENT_ANALYSIS_VERSION}:
                    self._check_question_options(analysis, outputs["options"])
                    retained = inputs.get("operation") == "adopt" and (outputs.get("adoption") or {}).get("analysis_retained")
                    if retained:
                        ignored = {"resource_assessment", "content_sha256"}
                        if (not self._retains_analysis(history, inputs["payload"])
                                or outputs["options"] != history[-1]["outputs"]["options"]
                                or {key: value for key, value in analysis.items() if key not in ignored}
                                != {key: value for key, value in history[-1]["outputs"]["domain_analysis"].items() if key not in ignored}):
                            raise RuntimeError("BUSINESS_WORK_ANALYSIS_BINDING_INVALID")
                    if (inputs.get("operation") == "adopt"
                            and not retained
                            and analysis["question_result"]["generation"] == self.REVISED_RESEARCH_GENERATION):
                        expected_analysis, expected_options = self._revise_single_derived_option(
                            history, inputs["payload"], actor_ref)
                        ignored = {"resource_assessment", "content_sha256"}
                        if (outputs["options"] != expected_options
                                or {key: item for key, item in analysis.items() if key not in ignored}
                                != {key: item for key, item in expected_analysis.items() if key not in ignored}):
                            raise RuntimeError("BUSINESS_WORK_DERIVED_REVISION_BINDING_INVALID")
                    origin = (inputs if inputs.get("operation") in {"prepare", "adopt"} and not retained
                              else self._analysis_origin(history)["inputs"])
                    generated = origin["payload"].get("options") is None
                    if generated != (analysis["question_result"]["generation"] == "SYSTEM_DERIVED_RECOMMENDATIONS"):
                        raise RuntimeError("BUSINESS_WORK_ANALYSIS_PROPOSAL_ORIGIN_INVALID")
                    if inputs.get("operation") in {"prepare", "adopt"} and generated:
                        expected_state = ("DECIDED" if outputs.get("decision") else
                                          "PREPARED" if outputs["options"] else "NOT_READY")
                        if outputs["state"] != expected_state:
                            raise RuntimeError("BUSINESS_WORK_ANALYSIS_STATE_INVALID")
            if history and inputs.get("operation") not in {"prepare", "adopt"}:
                prior_analysis = history[-1]["outputs"].get("domain_analysis")
                if (analysis is None) != (prior_analysis is None):
                    raise RuntimeError("BUSINESS_WORK_ANALYSIS_VERSION_CHANGED")
                if analysis is not None:
                    prior_facts = {key: value for key, value in prior_analysis.items()
                                   if key not in {"resource_assessment", "content_sha256"}}
                    facts = {key: value for key, value in analysis.items()
                             if key not in {"resource_assessment", "content_sha256"}}
                    if facts != prior_facts:
                        raise RuntimeError("BUSINESS_WORK_ANALYSIS_VERSION_CHANGED")
            if row["version"] == self.VERSION:
                if outputs.get("action_state") != "NOT_EXECUTED" or outputs.get("action") is not None:
                    raise RuntimeError("BUSINESS_WORK_BINDING_INVALID")
            else:
                action = outputs.get("action")
                expected_action = "EXECUTED" if action else "MANUALLY_REPORTED" if outputs.get("execution_records") else "NOT_EXECUTED"
                if outputs.get("action_state") != expected_action:
                    raise RuntimeError("BUSINESS_WORK_BINDING_INVALID")
                if action:
                    if (not isinstance(action, dict) or not isinstance(action.get("receipt"), dict)
                            or action.get("option_id") != outputs.get("decision", {}).get("option_id")
                            or action.get("association") != "OPERATOR_LINK_TO_SELECTED_OPTION"):
                        raise RuntimeError("BUSINESS_WORK_BINDING_INVALID")
                    if inputs.get("operation") == "action":
                        payload = inputs["payload"]
                        if (payload.get("task_id") != action["receipt"].get("task_id")
                                or payload.get("option_id") != action["option_id"]):
                            raise RuntimeError("BUSINESS_WORK_BINDING_INVALID")
                    elif not history or action != history[-1]["outputs"].get("action"):
                        raise RuntimeError("BUSINESS_WORK_BINDING_INVALID")
                if row["version"] == self.REVISION_VERSION or outputs.get("adoption"):
                    adoption = outputs.get("adoption")
                    if not isinstance(adoption, dict):
                        raise RuntimeError("BUSINESS_WORK_ADOPTION_BINDING_INVALID")
                    if inputs.get("operation") == "adopt":
                        carried = outputs.get("observation")
                        expected_observation = self._carry_prior_observation(
                            history, inputs["payload"].get("source_job_id"),
                            {"decision": outputs.get("decision")}).get("observation") if carried else None
                        if (not history or action is not None
                                or adoption.get("parent_revision") != previous
                                or adoption.get("reason") != inputs["payload"].get("reason")
                                or adoption.get("source_job_id") != inputs["payload"].get("source_job_id")
                                or outputs.get("outcome_state") != ("PRIOR_OBSERVATION_ONLY" if carried else "NOT_OBSERVED")
                                or (carried and (carried != expected_observation
                                                 or outputs.get("business_outcome") != "NOT_OBSERVED"))):
                            raise RuntimeError("BUSINESS_WORK_ADOPTION_BINDING_INVALID")
                    elif not history or adoption != history[-1]["outputs"].get("adoption"):
                        raise RuntimeError("BUSINESS_WORK_ADOPTION_BINDING_INVALID")
            evidence_ref = f"app_evidence_records:{row['id']}"
            history.append({"inputs": inputs, "outputs": outputs, "evidence_ref": evidence_ref})
            previous = evidence_ref
        return history

    def _options(self, options, source_ids):
        if not isinstance(options, list) or not 2 <= len(options) <= 4:
            raise ValueError("BUSINESS_WORK_COMPARABLE_OPTIONS_REQUIRED")
        result = [self._operator_option(option, source_ids) for option in options]
        if len({item["option_id"] for item in result}) != len(result):
            raise ValueError("BUSINESS_WORK_OPTION_ID_DUPLICATE")
        return result

    def _operator_option(self, option, source_ids):
        if not isinstance(option, dict) or set(option) != {"option_id", "proposal", "rationale", "source_ids", "assumptions", "unknowns", "check"}:
            raise ValueError("BUSINESS_WORK_OPTION_INVALID")
        for key in ("option_id", "proposal", "rationale", "check"):
            self._text(option[key], 80 if key == "option_id" else 1500)
        refs = option["source_ids"]
        if (not isinstance(refs, list) or not refs or any(type(source) is not str for source in refs)
                or len(refs) != len(set(refs)) or not set(refs) <= source_ids):
            raise PermissionError("BUSINESS_WORK_OPTION_SOURCE_INVALID")
        for key in ("assumptions", "unknowns"):
            if not isinstance(option[key], list) or not 1 <= len(option[key]) <= 8:
                raise ValueError("BUSINESS_WORK_LIMITS_REQUIRED")
            for text in option[key]:
                self._text(text)
        return {**option, "claim_type": "OPERATOR_PROPOSAL", "causation": "NOT_ESTABLISHED"}

    def _revise_single_derived_option(self, history, payload, actor_ref):
        """Revise one existing research action, never create a one-option comparison."""
        import hashlib
        prior = history[-1]["outputs"]
        analysis = prior.get("domain_analysis") or {}
        result = analysis.get("question_result") or {}
        requested = payload.get("options")
        if (result.get("generation") not in {"SYSTEM_DERIVED_RECOMMENDATIONS", self.REVISED_RESEARCH_GENERATION}
                or analysis.get("version") not in {self.QUESTION_ANALYSIS_VERSION, self.CURRENT_ANALYSIS_VERSION}
                or len(prior["options"]) != 1 or not isinstance(requested, list) or len(requested) != 1):
            raise ValueError("BUSINESS_WORK_SINGLE_DERIVED_REVISION_REQUIRED")
        self._check_analysis_digest(analysis)
        self._check_question_options(analysis, prior["options"])
        origin = self._analysis_origin(history)
        if result["generation"] == self.REVISED_RESEARCH_GENERATION:
            root_ref = result["single_option_revision"]["original_revision"]
            origin = next((event for event in history if event["evidence_ref"] == root_ref), None)
        if origin is None:
            raise RuntimeError("BUSINESS_WORK_DERIVED_REVISION_BINDING_INVALID")
        root = origin["outputs"].get("domain_analysis") or {}
        root_result = root.get("question_result") or {}
        if (root_result.get("generation") != "SYSTEM_DERIVED_RECOMMENDATIONS"
                or origin["inputs"]["payload"].get("options") is not None
                or len(origin["outputs"]["options"]) != 1
                or payload["source_job_id"] != origin["inputs"]["payload"]["source_job_id"]
                or payload["question"] != origin["inputs"]["payload"]["question"]
                or self._planning_constraints(payload.get("planning_constraints", result.get("planning_constraints")))
                   != root_result.get("planning_constraints")):
            raise ValueError("BUSINESS_WORK_DERIVED_REVISION_CONTEXT_CHANGED")
        excluded = {"question_result", "resource_assessment", "content_sha256"}
        if ({key: value for key, value in analysis.items() if key not in excluded}
                != {key: value for key, value in root.items() if key not in excluded}
                or {key: value for key, value in result.items() if key not in {"generation", "options_sha256", "single_option_revision"}}
                != {key: value for key, value in root_result.items() if key not in {"generation", "options_sha256", "single_option_revision"}}):
            raise RuntimeError("BUSINESS_WORK_DERIVED_REVISION_BINDING_INVALID")
        option = self._operator_option(requested[0], set(result["verified_source_ids"]))
        original, previous = origin["outputs"]["options"][0], prior["options"][0]
        if any(option[key] != original[key] or previous[key] != original[key]
               for key in ("option_id", "source_ids", "assumptions", "unknowns")):
            raise PermissionError("BUSINESS_WORK_DERIVED_REVISION_SOURCE_CHANGED")
        changed = [key for key in ("proposal", "rationale", "check") if option[key] != previous[key]]
        if not changed:
            raise ValueError("BUSINESS_WORK_ADOPTION_HAS_NO_CHANGE")
        revision = {"original_revision": origin["evidence_ref"],
                    "original_analysis_sha256": root["content_sha256"],
                    "original_options_sha256": root_result["options_sha256"],
                    "basis_sha256": root_result["basis_sha256"],
                    "parent_revision": history[-1]["evidence_ref"], "editor": actor_ref, "changed_fields": changed}
        option.update(claim_type=self.REVISED_RESEARCH_GENERATION,
                      basis_sha256=root_result["basis_sha256"], cost_estimate=None, budget_fit="UNKNOWN",
                      operator_revision=revision)
        options = [option]
        return self._seal_analysis({**analysis, "question_result": {**result,
            "generation": self.REVISED_RESEARCH_GENERATION, "single_option_revision": revision,
            "options_sha256": hashlib.sha256(self._json(options).encode()).hexdigest()}}), options

    def _append(self, *, actor_ref, scope, work_id, submission_id, operation,
                payload, authorize, expected_revision=None):
        import re
        from lumenis.shared.evidence import store
        if not isinstance(submission_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", submission_id):
            raise ValueError("BUSINESS_WORK_SUBMISSION_INVALID")
        self._authorize(authorize, actor_ref, scope, operation)
        with get_repository().transaction(timeout=10) as connection:
            connection.execute("BEGIN IMMEDIATE")
            if operation == "prepare":
                work_id = self._prepare_work_id(connection, actor_ref, scope, submission_id)
            history = self._history(connection, work_id, actor_ref, scope)
            # Replay is checked before optimistic revision: lost responses must
            # recover the same event, while conflicting intent cannot overwrite it.
            existing = [event for event in history if event["inputs"]["submission_id"] == submission_id]
            if existing:
                if len(existing) != 1 or existing[0]["inputs"]["operation"] != operation or existing[0]["inputs"]["payload"] != payload:
                    raise ValueError("BUSINESS_WORK_SUBMISSION_CONFLICT")
            else:
                revision = history[-1]["evidence_ref"] if history else None
                if revision != expected_revision:
                    raise RuntimeError("BUSINESS_WORK_REVISION_CONFLICT")
                outputs = self._transition(connection, history, operation, payload, actor_ref, scope, authorize)
                self._verify_outcome(connection, outputs, actor_ref, scope)
                audits = self._authorize(authorize, actor_ref, scope, operation)
                inputs = {"work_id": work_id, "actor_ref": actor_ref, "scope": scope,
                          "submission_id": submission_id, "operation": operation,
                          "payload": payload, "parent_ref": revision, **audits}
                ref = store.record_evidence(
                    connection=connection, source="cth_bmp_business", project="LUMENIS",
                    product=scope["product_id"], domain_id=scope["domain_id"],
                    subject_id=scope.get("subject_id"), brand_focus_id=scope.get("brand_focus_id"),
                    global_scope=False, feature_id=self.FEATURE, asset_id=work_id,
                    test_name=submission_id,
                    version=self._record_version(outputs),
                    status="derived", result="RECORDED",
                    inputs=inputs, outputs=outputs,
                )
                if type(ref) is not int or ref < 1:
                    raise RuntimeError("BUSINESS_WORK_EVIDENCE_WRITE_FAILED")
                history = self._history(connection, work_id, actor_ref, scope)
            # Explicit adoption replaces the active input, never its signed history.
            self._bound_report(connection, history, actor_ref, scope)
            self._verify_outcome(connection, history[-1]["outputs"], actor_ref, scope)
            active_history = self._active_history(history)
            action_read = self._verify_actions(active_history, actor_ref, scope, authorize)
            if any(e["inputs"]["operation"] == "action" for e in active_history):
                if action_read["state"] != "FRESH_OWNER_VERIFIED":
                    raise RuntimeError("BUSINESS_WORK_ACTION_OWNER_NOT_BOUND")
                self._authorize(authorize, actor_ref, scope, operation)
            # Owner readers and authorization callbacks may observe revocation;
            # verify the source chain last, before this Evidence transaction commits.
            current_report = self._bound_report(connection, history, actor_ref, scope)
            self._verify_outcome(connection, history[-1]["outputs"], actor_ref, scope)
            current_analysis = history[-1]["outputs"].get("domain_analysis")
            if current_analysis is not None:
                self._verify_domain_analysis(connection, current_analysis, current_report, actor_ref, scope)
        if history[-1]["outputs"]["state"] == "OUTCOME_RECORDED":
            # Evaluation is a recoverable derivative side-write. Replay retains
            # the signed outcome and repairs its exact deterministic evaluation.
            from lumenis.shared.evaluation.recorder import record_evaluation
            import hashlib
            self._authorize(authorize, actor_ref, scope, "evaluate")
            with get_repository().transaction(timeout=10) as evaluation_connection:
                evaluation_connection.execute("BEGIN IMMEDIATE")
                latest = self._history(evaluation_connection, work_id, actor_ref, scope)
                if latest[-1]["evidence_ref"] != history[-1]["evidence_ref"]:
                    raise RuntimeError("BUSINESS_WORK_REVISION_CONFLICT")
                self._bound_report(evaluation_connection, latest, actor_ref, scope)
                self._verify_outcome(evaluation_connection, latest[-1]["outputs"], actor_ref, scope)
                self._authorize(authorize, actor_ref, scope, "evaluate")
                # Recheck after the permission callback, while the write lock
                # prevents another DB writer changing the admitted source chain.
                self._bound_report(evaluation_connection, latest, actor_ref, scope)
                self._verify_outcome(evaluation_connection, latest[-1]["outputs"], actor_ref, scope)
                record_evaluation(
                    dimension="report", metric_name="business_decision_usefulness",
                    metric_value=None, pass_threshold=1.0, warn_threshold=0.8,
                    source="cth_bmp_business", evidence_ref=latest[-1]["evidence_ref"],
                    evaluation_id=hashlib.sha256((work_id + latest[-1]["evidence_ref"]).encode()).hexdigest(),
                    metadata=self._evaluation_metadata(work_id, latest[-1], actor_ref, scope),
                    connection=evaluation_connection,
                )
                self._authorize(authorize, actor_ref, scope, "evaluate")
                self._bound_report(evaluation_connection, latest, actor_ref, scope)
                self._verify_outcome(evaluation_connection, latest[-1]["outputs"], actor_ref, scope)
        return self.reopen(work_id, actor_ref=actor_ref, scope=scope, authorize=authorize)

    @staticmethod
    def _evaluation_metadata(work_id, event, actor_ref, scope):
        outputs = event["outputs"]
        metadata = {"work_id": work_id, "actor_ref": actor_ref, "scope": event["inputs"]["scope"],
                    "outcome_state": outputs["outcome_state"], "causation": "NOT_ESTABLISHED",
                    "action_state": outputs["action_state"]}
        if outputs.get("action"):
            metadata["action"] = outputs["action"]
            metadata["business_outcome"] = outputs["business_outcome"]
        if outputs.get("operator_review"):
            metadata["operator_review"] = outputs["operator_review"]
        for key in ("execution_records", "observation"):
            if outputs.get(key):
                metadata[key] = outputs[key]
        if "resource_constraints" in (outputs.get("decision") or {}):
            metadata["resource_constraints"] = outputs["decision"]["resource_constraints"]
        return metadata

    def _transition(self, connection, history, operation, payload, actor_ref, scope, authorize):
        if operation == "prepare":
            if history:
                raise RuntimeError("BUSINESS_WORK_ALREADY_EXISTS")
            if scope.get("global") is not False or scope.get("product_id") not in {"CTH", "ZBMP"}:
                raise PermissionError("BUSINESS_WORK_EXACT_FOCUS_REQUIRED")
            report = self._report(connection, payload["source_job_id"], actor_ref, scope)
            sources = report["source_brief"]["records"]
            if not sources:
                raise ValueError("BUSINESS_WORK_SOURCE_MATERIAL_REQUIRED")
            kind = payload["kind"]
            allowed = {"venue_operations", "consumer_risk"} if scope["product_id"] == "CTH" else {"brand_market", "creator_campaign"}
            if kind not in allowed:
                raise ValueError("BUSINESS_WORK_DOMAIN_JOB_MISMATCH")
            self._text(payload["question"])
            case = None
            if payload.get("case_id"):
                if scope["product_id"] != "CTH":
                    raise PermissionError("BUSINESS_WORK_CASE_DOMAIN_MISMATCH")
                case = self._case(connection, payload["case_id"], actor_ref, scope)
                if case["source_job_id"] != payload["source_job_id"] or case["question"] != payload["question"]:
                    raise PermissionError("BUSINESS_WORK_CASE_INPUT_MISMATCH")
            selected = {s["source_id"] for s in (case["source_refs"] if case else sources)}
            planning = payload.get("planning_constraints")
            if payload.get("options") is None or planning is not None:
                analysis, options = self._prepare_analysis(
                    connection, report, actor_ref, scope, kind, payload["question"],
                    payload.get("options"), selected, planning)
                analysis = self._analysis_resources(analysis, None)
                return {"state": "PREPARED" if options else "NOT_READY", "options": options, "decision": None,
                        "domain_analysis": analysis, "source_report_hash": report["row"]["artifact_hash"],
                        "source_body_bindings": self._source_bindings(connection, report, scope),
                        "hypothesis_review": report.get("hypothesis_review"),
                        "case_id": payload.get("case_id"),
                        "case_evidence_ref": case["creation_evidence_ref"] if case else None,
                        "resume_count": 0, "outcome_state": "NOT_OBSERVED",
                        "business_outcome": "NOT_OBSERVED", "action_state": "NOT_EXECUTED"}
            options = self._options(payload["options"], selected)
            return {"state": "PREPARED", "options": options, "decision": None,
                    "source_report_hash": report["row"]["artifact_hash"],
                    "source_body_bindings": self._source_bindings(connection, report, scope),
                    "hypothesis_review": report.get("hypothesis_review"),
                    "case_id": payload.get("case_id"),
                    "case_evidence_ref": case["creation_evidence_ref"] if case else None,
                    "resume_count": 0, "outcome_state": "NOT_OBSERVED", "business_outcome": "NOT_OBSERVED",
                    "action_state": "NOT_EXECUTED"}
        if not history:
            raise LookupError("BUSINESS_WORK_NOT_FOUND")
        original = history[0]["inputs"]["payload"]
        prior = history[-1]["outputs"]
        state = prior["state"]
        if (state == "CANCELLED" and operation != "restore") or (state == "OUTCOME_RECORDED" and operation not in {"action", "manual_action", "observation", "adopt", "review"}):
            raise RuntimeError("BUSINESS_WORK_TERMINAL")
        if operation == "restore":
            if state != "CANCELLED":
                raise RuntimeError("BUSINESS_WORK_CANCELLED_REQUIRED")
            self._text(payload["reason"])
            # Restore the exact pre-cancel record, including an interrupted
            # state's original resume target. Never restart an external task.
            cancelled = next(i for i in range(len(history) - 1, -1, -1)
                             if history[i]["inputs"]["operation"] == "cancel")
            restored = dict(history[cancelled - 1]["outputs"])
            restored["recovery"] = {"cancelled_revision": history[cancelled]["evidence_ref"],
                                    "reason": payload["reason"], "restored_by": actor_ref,
                                    "external_effect": "NOT_PERFORMED"}
            return restored
        if operation == "adopt":
            if state == "INTERRUPTED":
                raise RuntimeError("BUSINESS_WORK_RESUME_REQUIRED")
            self._text(payload["reason"])
            self._text(payload["question"])
            self._text(payload["source_job_id"], 256)
            report = self._report(connection, payload["source_job_id"], actor_ref, scope)
            source_ids = {source["source_id"] for source in report["source_brief"]["records"]}
            if not source_ids:
                raise ValueError("BUSINESS_WORK_SOURCE_MATERIAL_REQUIRED")
            active = self._active_origin(history)
            previous_analysis = prior.get("domain_analysis") or {}
            if (payload["source_job_id"] == active["inputs"]["payload"]["source_job_id"]
                    and previous_analysis.get("question_result") is not None):
                source_ids = set(previous_analysis["question_result"]["selected_source_ids"])
            if previous_analysis:
                previous_planning = previous_analysis.get("question_result", {}).get("planning_constraints")
                planning = payload.get("planning_constraints", previous_planning)
                retained_analysis = self._retains_analysis(history, payload)
                if retained_analysis:
                    self._bound_report(connection, history, actor_ref, scope)
                    self._verify_domain_analysis(connection, previous_analysis, report, actor_ref, scope)
                    analysis, options = previous_analysis, prior["options"]
                elif isinstance(payload["options"], list) and len(payload["options"]) == 1:
                    self._bound_report(connection, history, actor_ref, scope)
                    self._verify_domain_analysis(connection, previous_analysis, report, actor_ref, scope)
                    analysis, options = self._revise_single_derived_option(history, payload, actor_ref)
                else:
                    analysis, options = self._prepare_analysis(
                        connection, report, actor_ref, scope, original["kind"], payload["question"],
                        payload["options"], source_ids, planning)
                old_options = {option["option_id"]: option for option in prior["options"]}
                changed = [option["option_id"] for option in options
                           if option != old_options.get(option["option_id"])]
                unchanged = [option["option_id"] for option in options if option["option_id"] not in changed]
                options = [old_options[option["option_id"]] if option["option_id"] in unchanged else option
                           for option in options]
                generated = analysis["question_result"]["generation"] == "SYSTEM_DERIVED_RECOMMENDATIONS"
                if generated and payload["decision"] is None:
                    selection = None
                else:
                    selection = self._selection(payload["decision"], options)
                analysis = self._analysis_resources(analysis, selection)
                if (payload["source_job_id"] == active["inputs"]["payload"]["source_job_id"]
                        and payload["question"] == active["inputs"]["payload"]["question"]
                        and options == prior["options"] and selection == prior["decision"]
                        and analysis == previous_analysis):
                    raise ValueError("BUSINESS_WORK_ADOPTION_HAS_NO_CHANGE")
                adoption = {"parent_revision": history[-1]["evidence_ref"], "reason": payload["reason"],
                            "analysis_retained": retained_analysis,
                            "source_job_id": payload["source_job_id"], "changed_option_ids": changed,
                            "removed_option_ids": sorted(set(old_options) - {option["option_id"] for option in options}),
                            "unchanged_option_ids": unchanged,
                            "source_changed": payload["source_job_id"] != active["inputs"]["payload"]["source_job_id"],
                            "question_changed": payload["question"] != active["inputs"]["payload"]["question"],
                            "resources_changed": (selection or {}).get("resource_constraints") != (prior["decision"] or {}).get("resource_constraints"),
                            "previous_action_ref": (prior.get("action") or {}).get("receipt", {}).get("artifact_id"),
                            "previous_outcome_revision": history[-1]["evidence_ref"] if state == "OUTCOME_RECORDED" else None,
                            "downstream_adoption": "EXPLICIT_NEW_VERSION_REQUIRED",
                            "uncited_dependencies": "NOT_VERIFIED"}
                return self._carry_prior_observation(history, payload["source_job_id"], {
                        "state": "DECIDED" if selection else "PREPARED" if options else "NOT_READY",
                        "options": options, "decision": selection, "source_report_hash": report["row"]["artifact_hash"],
                        "source_body_bindings": self._source_bindings(connection, report, scope),
                        "hypothesis_review": report.get("hypothesis_review"),
                        "domain_analysis": analysis,
                        "case_id": history[0]["outputs"].get("case_id"),
                        "case_evidence_ref": history[0]["outputs"].get("case_evidence_ref"),
                        "resume_count": prior["resume_count"], "outcome_state": "NOT_OBSERVED",
                        "business_outcome": "NOT_OBSERVED", "action_state": "NOT_EXECUTED", "adoption": adoption})
            options = self._options(payload["options"], source_ids)
            old_options = {option["option_id"]: option for option in prior["options"]}
            changed = [option["option_id"] for option in options
                       if option != old_options.get(option["option_id"])]
            unchanged = [option["option_id"] for option in options if option["option_id"] not in changed]
            options = [old_options[option["option_id"]] if option["option_id"] in unchanged else option
                       for option in options]
            selection = self._selection(payload["decision"], options)
            if (payload["source_job_id"] == active["inputs"]["payload"]["source_job_id"]
                    and payload["question"] == active["inputs"]["payload"]["question"]
                    and options == prior["options"] and selection == prior["decision"]
                    and report.get("hypothesis_review") == active["outputs"].get("hypothesis_review")):
                raise ValueError("BUSINESS_WORK_ADOPTION_HAS_NO_CHANGE")
            adoption = {"parent_revision": history[-1]["evidence_ref"], "reason": payload["reason"],
                        "source_job_id": payload["source_job_id"], "changed_option_ids": changed,
                        "removed_option_ids": sorted(set(old_options) - {option["option_id"] for option in options}),
                        "unchanged_option_ids": unchanged,
                        "source_changed": payload["source_job_id"] != active["inputs"]["payload"]["source_job_id"],
                        "question_changed": payload["question"] != active["inputs"]["payload"]["question"],
                        "research_review_changed": report.get("hypothesis_review") != active["outputs"].get("hypothesis_review"),
                        "resources_changed": selection.get("resource_constraints") != (prior["decision"] or {}).get("resource_constraints"),
                        "previous_action_ref": (prior.get("action") or {}).get("receipt", {}).get("artifact_id"),
                        "previous_outcome_revision": history[-1]["evidence_ref"] if state == "OUTCOME_RECORDED" else None,
                        "downstream_adoption": "EXPLICIT_NEW_VERSION_REQUIRED",
                        "uncited_dependencies": "NOT_VERIFIED"}
            return self._carry_prior_observation(history, payload["source_job_id"], {
                    "state": "DECIDED", "options": options, "decision": selection, "selected_by": actor_ref,
                    "source_report_hash": report["row"]["artifact_hash"],
                    "source_body_bindings": self._source_bindings(connection, report, scope),
                    "hypothesis_review": report.get("hypothesis_review"),
                    "case_id": history[0]["outputs"].get("case_id"),
                    "case_evidence_ref": history[0]["outputs"].get("case_evidence_ref"),
                    "resume_count": prior["resume_count"], "outcome_state": "NOT_OBSERVED",
                    "business_outcome": "NOT_OBSERVED", "action_state": "NOT_EXECUTED", "adoption": adoption})
        report = self._bound_report(connection, history, actor_ref, scope)
        if prior.get("domain_analysis") is not None and operation not in {"cancel", "interrupt"}:
            self._verify_domain_analysis(connection, prior["domain_analysis"], report, actor_ref, scope)
        result = dict(prior)
        if operation == "review":
            if state != "OUTCOME_RECORDED":
                raise RuntimeError("BUSINESS_WORK_OUTCOME_REVIEW_REQUIRED")
            if (not isinstance(payload["assessment"], str) or not isinstance(payload["next_step"], str)
                    or payload["assessment"] not in {"useful", "not_useful", "inconclusive"}
                    or payload["next_step"] not in {"retain", "revise", "stop"}):
                raise ValueError("BUSINESS_WORK_REVIEW_INVALID")
            self._text(payload["observations"])
            limits = payload["limitations"]
            if not isinstance(limits, list) or not 1 <= len(limits) <= 8:
                raise ValueError("BUSINESS_WORK_REVIEW_LIMITATIONS_REQUIRED")
            for limitation in limits:
                self._text(limitation)
            report = self._bound_report(connection, history, actor_ref, scope)
            available = {r["source_id"] for r in report["source_brief"]["records"]}
            if prior.get("outcome"):
                available.add(prior["outcome"]["source_id"])
            if prior.get("observation"):
                available.add(prior["observation"]["source_claim"]["source_id"])
            available.update(claim["source_id"] for claim in self._result_claims(prior))
            refs = payload["source_ids"]
            if (not isinstance(refs, list) or not refs or any(type(ref) is not str for ref in refs)
                    or len(refs) != len(set(refs)) or not set(refs) <= available):
                raise PermissionError("BUSINESS_WORK_REVIEW_SOURCE_INVALID")
            result["operator_review"] = {**payload, "reviewer": actor_ref,
                "reviewed_revision": history[-1]["evidence_ref"],
                "outcome_revision": next(e["evidence_ref"] for e in reversed(history)
                                         if e["inputs"]["operation"] in {"outcome", "outcome_unknown", "observation"}),
                "outcome_state": prior["outcome_state"],
                "claim_type": "OPERATOR_FEEDBACK", "causation": "NOT_ESTABLISHED",
                "metric_value": None, "external_effect": "NOT_PERFORMED"}
        elif operation == "choose":
            if state not in {"PREPARED", "DECIDED"} or payload["option_id"] not in {o["option_id"] for o in prior["options"]}:
                raise ValueError("BUSINESS_WORK_DECISION_INVALID")
            result.update(state="DECIDED", decision=self._selection(payload, prior["options"]),
                          selected_by=actor_ref)
            if result.get("domain_analysis") is not None:
                result["domain_analysis"] = self._analysis_resources(result["domain_analysis"], result["decision"])
            if result.get("observation"):
                result["observation"] = {**result["observation"], "resource_result": self._observation_result(
                    result["observation"], result["decision"], {}, None)["resource_result"]}
        elif operation in {"cancel", "interrupt"}:
            self._text(payload["reason"])
            if operation == "interrupt" and state == "INTERRUPTED":
                raise RuntimeError("BUSINESS_WORK_ALREADY_INTERRUPTED")
            result.update(state="CANCELLED" if operation == "cancel" else "INTERRUPTED",
                          previous_state=state, reason=payload["reason"])
        elif operation == "resume":
            if state != "INTERRUPTED" or prior["resume_count"] >= 2:
                raise RuntimeError("BUSINESS_WORK_RESUME_LIMIT_OR_STATE")
            result.update(state=prior["previous_state"], resume_count=prior["resume_count"] + 1)
        elif operation == "action":
            if state not in {"DECIDED", "ACTION_RECORDED", "OUTCOME_RECORDED"} or payload["option_id"] != prior["decision"]["option_id"]:
                raise RuntimeError("BUSINESS_WORK_ACTION_SELECTED_OPTION_REQUIRED")
            receipt = self._read_action(payload["task_id"], actor_ref, scope, authorize)
            if prior.get("action"):
                parent = prior["action"]["receipt"]
                if (receipt["work_id"] != parent["work_id"] or receipt["version"] != parent["version"] + 1
                        or receipt["parent_artifact_id"] != parent["artifact_id"]
                        or receipt["parent_sha256"] != parent["sha256"]):
                    raise RuntimeError("BUSINESS_WORK_ACTION_REVISION_INVALID")
            result.update(state="ACTION_RECORDED", action_state="EXECUTED",
                          action={"option_id": payload["option_id"], "association": "OPERATOR_LINK_TO_SELECTED_OPTION",
                                  "receipt": receipt}, business_outcome="NOT_OBSERVED",
                          outcome_state="SOURCE_REPORTED" if result.get("outcome") else "NOT_OBSERVED")
            # A new committed revision starts a new effects review. Previous
            # evaluations/UNKNOWN limitations remain in immutable history.
            result.pop("outcome_unknown", None)
            result.pop("operator_review", None)
        elif operation == "manual_action":
            if state not in {"DECIDED", "ACTION_RECORDED", "OUTCOME_RECORDED"}:
                raise RuntimeError("BUSINESS_WORK_DECISION_REQUIRED")
            record = self._manual_action(connection, payload, actor_ref, scope, prior["decision"]["option_id"])
            record = self._bind_planned_execution(record, payload, prior)
            records = list(prior.get("execution_records", []))
            if any(item["operation_digest"] == record["operation_digest"] for item in records):
                raise ValueError("BUSINESS_WORK_MANUAL_ACTION_ALREADY_RECORDED")
            records.append(record)
            result.update(state="ACTION_RECORDED", execution_records=records,
                          action_state="EXECUTED" if prior.get("action") else "MANUALLY_REPORTED",
                          business_outcome="NOT_OBSERVED", outcome_state="NOT_OBSERVED")
            if result.get("observation"):
                result["outcome_state"] = "PRIOR_OBSERVATION_ONLY"
            for key in ("outcome", "outcome_unknown", "operator_review"):
                result.pop(key, None)
        elif operation == "observation":
            if state not in {"DECIDED", "ACTION_RECORDED", "OUTCOME_RECORDED"}:
                raise RuntimeError("BUSINESS_WORK_DECISION_REQUIRED")
            last_event = next((event for event in reversed(self._active_history(history))
                               if event["outputs"].get("observation")), None)
            last_observation = last_event["outputs"]["observation"] if last_event else {}
            observation = self._observation(connection, payload, actor_ref, scope,
                                            last_observation.get("cost_ledger", []), last_observation, prior)
            observation = self._observation_result(observation, prior["decision"], last_observation,
                                                   last_event["evidence_ref"] if last_event else None)
            target_review = self._domain_target_review(observation, prior)
            if target_review is not None:
                observation['domain_target_review'] = target_review
            result.update(state="OUTCOME_RECORDED", outcome_state="OPERATOR_REPORTED_OBSERVATION",
                          business_outcome="SOURCE_REPORTED_NOT_ATTRIBUTED", observation=observation)
            for key in ("outcome", "outcome_unknown", "operator_review"):
                result.pop(key, None)
        elif operation == "outcome_unknown":
            if state != "ACTION_RECORDED":
                raise RuntimeError("BUSINESS_WORK_ACTION_REQUIRED")
            self._text(payload["limits"])
            result.update(state="OUTCOME_RECORDED", outcome_state="UNKNOWN", business_outcome="UNKNOWN",
                          outcome_unknown={"limits": payload["limits"], "claim_type": "OPERATOR_REVIEW",
                                           "causation": "NOT_ESTABLISHED"})
        elif operation == "outcome":
            if state not in {"DECIDED", "ACTION_RECORDED"}:
                raise RuntimeError("BUSINESS_WORK_DECISION_REQUIRED")
            outcome_report = self._report(connection, payload["source_job_id"], actor_ref, scope)
            source_ids = {s["source_id"] for s in outcome_report["source_brief"]["records"]}
            if payload["source_id"] not in source_ids:
                raise PermissionError("BUSINESS_WORK_OUTCOME_SOURCE_INVALID")
            quote = self._text(payload["quote"], 1200)
            body = self._outcome_material(connection, outcome_report, actor_ref, scope,
                                          payload["source_id"], quote)
            if quote not in body:
                raise ValueError("BUSINESS_WORK_OUTCOME_QUOTE_NOT_IN_SOURCE")
            import hashlib
            self._text(payload["limits"])
            result.update(state="OUTCOME_RECORDED", outcome_state="SOURCE_REPORTED",
                          outcome={**payload, "report_hash": outcome_report["row"]["artifact_hash"],
                                   "body_sha256": hashlib.sha256(body.encode()).hexdigest(),
                                   "claim_type": "SOURCE_CLAIM", "causation": "NOT_ESTABLISHED"})
        else:
            raise ValueError("BUSINESS_WORK_OPERATION_INVALID")
        return result

    def _selection(self, payload, options):
        required = {"option_id", "reason", "owner", "review_at"}
        if (not isinstance(payload, dict) or set(payload) not in (required, required | {"resource_constraints"})
                or payload["option_id"] not in {option["option_id"] for option in options}):
            raise ValueError("BUSINESS_WORK_DECISION_INVALID")
        for key in ("reason", "owner"):
            self._text(payload[key])
        self._text(payload["review_at"], 80)
        from datetime import datetime
        if datetime.fromisoformat(payload["review_at"].replace("Z", "+00:00")).tzinfo is None:
            raise ValueError("BUSINESS_WORK_REVIEW_TIMEZONE_REQUIRED")
        result = {**payload, "approval": "INTERNAL_SELECTION_ONLY"}
        if "resource_constraints" in payload:
            result["resource_constraints"] = self._resources(payload["resource_constraints"])
        return result

    def _prepare_work_id(self, connection, actor_ref, scope, submission_id):
        """Recover the original signed request identity across display-only changes."""
        import hashlib
        from lumenis.shared.evidence import store
        from lumenis.shared.reporting.operator_review import _expected_scope_marker
        self._text(actor_ref, 256)
        candidates = connection.execute(
            "SELECT * FROM app_evidence_records "
            "WHERE feature_id=? AND test_name=? AND product_id=? AND domain_id=?",
            (self.FEATURE, submission_id, scope["product_id"], scope["domain_id"]),
        ).fetchall()
        matches = set()
        for row in candidates:
            if not store.verify_evidence_record_integrity(dict(row)):
                raise RuntimeError("BUSINESS_WORK_SIGNATURE_INVALID")
            inputs = json.loads(row["inputs_json"])
            if not isinstance(inputs, dict):
                raise RuntimeError("BUSINESS_WORK_BINDING_INVALID")
            if inputs.get("operation") == "prepare" and inputs.get("actor_ref") == actor_ref:
                if _expected_scope_marker(inputs.get("scope")) != _expected_scope_marker(scope):
                    continue
                if not _same_business_scope(inputs.get("scope"), scope):
                    raise PermissionError("BUSINESS_WORK_CONTEXT_MISMATCH")
                self._history(connection, row["asset_id"], actor_ref, scope)
                matches.add(row["asset_id"])
        if len(matches) > 1:
            raise RuntimeError("BUSINESS_WORK_PREPARE_IDENTITY_CONFLICT")
        if matches:
            return matches.pop()
        return "work-" + hashlib.sha256(self._json([actor_ref, scope, submission_id]).encode()).hexdigest()

    def prepare(self, *, actor_ref, scope, submission_id, source_job_id, kind, question, authorize,
                options=None, planning_constraints=None):
        payload = {"source_job_id": source_job_id, "kind": kind, "question": question, "options": options}
        if planning_constraints is not None:
            payload["planning_constraints"] = planning_constraints
        return self._append(actor_ref=actor_ref, scope=scope, work_id=None,
                            submission_id=submission_id, operation="prepare", authorize=authorize,
                            payload=payload)

    def prepare_from_case(self, case_id, *, actor_ref, scope, submission_id, kind, authorize,
                          options=None, planning_constraints=None):
        """Continue the existing signed CTH Case without replacing its owner."""
        self._authorize(authorize, actor_ref, scope, "read")
        with get_repository().connection(read_only=True, wal=False) as connection:
            case = self._case(connection, case_id, actor_ref, scope)
        payload = {"source_job_id": case["source_job_id"], "kind": kind,
                   "question": case["question"], "options": options, "case_id": case_id}
        if planning_constraints is not None:
            payload["planning_constraints"] = planning_constraints
        return self._append(actor_ref=actor_ref, scope=scope, work_id=None,
                            submission_id=submission_id, operation="prepare", authorize=authorize,
                            payload=payload)

    def advance(self, work_id, *, actor_ref, scope, submission_id, operation, payload, expected_revision, authorize):
        fields = {"choose": {"option_id", "reason", "owner", "review_at"},
                  "adopt": {"source_job_id", "question", "options", "decision", "reason"},
                  "cancel": {"reason"}, "restore": {"reason"}, "interrupt": {"reason"}, "resume": set(),
                  "review": {"assessment", "observations", "limitations", "next_step", "source_ids"},
                  "manual_action": {"option_id", "source_job_id", "source_id", "quote", "performed_at", "performer", "exact_target", "limits"},
                  "observation": {"source_job_id", "source_id", "quote", "observed_at", "window", "metrics", "costs", "limits"},
                  "action": {"option_id", "task_id"}, "outcome_unknown": {"limits"},
                  "outcome": {"source_job_id", "source_id", "quote", "limits"}}
        if operation not in fields or not isinstance(payload, dict):
            raise ValueError("BUSINESS_WORK_OPERATION_PAYLOAD_INVALID")
        if operation == "choose":
            allowed = (fields[operation], fields[operation] | {"resource_constraints"})
        elif operation == "adopt":
            allowed = (fields[operation], fields[operation] | {"planning_constraints"})
        elif operation == 'manual_action':
            allowed = (fields[operation], fields[operation] | {'plan_action_id'})
        else:
            allowed = (fields[operation],)
        if set(payload) not in allowed:
            raise ValueError("BUSINESS_WORK_OPERATION_PAYLOAD_INVALID")
        return self._append(work_id=work_id, actor_ref=actor_ref, scope=scope,
                            submission_id=submission_id, operation=operation, payload=payload,
                            expected_revision=expected_revision, authorize=authorize)

    @staticmethod
    def read_learning_material(work_id, *, actor, actor_ref, scope, expected_revision, connection=None):
        """Minimal fresh business feedback projection for the existing learning owner.

        No client reader, action receipt or claimed evaluation is accepted.
        The caller must bind the exact business revision it intends to learn from.
        """
        from lumenis.system.security import permission
        from lumenis.shared.content_creation.internal_pitch import read_internal_pitch
        media_scope = BusinessDecisionWorkflow._action_scope(scope)
        def authorized(operation):
            if operation != "read":
                raise PermissionError("BUSINESS_LEARNING_READ_ONLY")
            checker = (permission.check_local_workspace_scope_permission
                       if type(actor) is permission.LocalWorkspacePrincipal
                       else permission.check_actor_scope_permission)
            decision = checker(actor, module="reports", action="read", **media_scope,
                               **({"connection": connection} if connection is not None else {}))
            actual_ref = (actor.principal_ref if type(actor) is permission.LocalWorkspacePrincipal
                          else f"actor:{actor.get('id')}" if type(actor) is dict else None)
            if (not decision.allowed or not decision.audit_id or actual_ref != actor_ref
                    or decision.verification_state != "verified"):
                raise PermissionError("BUSINESS_LEARNING_CONTEXT_DENIED")
            return {"actor_id": actual_ref, "scope": scope, "operation": "read",
                    "permission_audit_ref": decision.audit_id, "operation_audit_ref": decision.audit_id}
        service = BusinessDecisionWorkflow(internal_action_reader=read_internal_pitch,
                                           action_actor=actor, source_actor=actor)
        current = service.reopen(work_id, actor_ref=actor_ref, scope=scope, authorize=authorized)
        if current["revision"] != expected_revision:
            raise RuntimeError("BUSINESS_WORK_REVISION_CONFLICT")
        feedback = current.get("operator_review")
        evaluation = current["evaluation"]
        if (current["state"] != "OUTCOME_RECORDED" or not feedback
                or evaluation["state"] != "RECORDED" or feedback["reviewer"] != actor_ref):
            raise RuntimeError("BUSINESS_LEARNING_REVIEW_REQUIRED")
        authorized("read")
        return {"work_id": work_id, "revision": current["revision"],
                "job_id": current["source_report"]["job_id"],
                "artifact_hash": current["source_report"]["artifact_hash"],
                "evaluation_id": evaluation["evaluation_id"],
                "feedback_decision": feedback["assessment"],
                "feedback_text": feedback["observations"], "limitations": feedback["limitations"],
                "outcome_state": current["outcome_state"],
                "business_outcome": current["business_outcome"],
                "review_evidence_ref": current["revision"],
                "outcome_evidence_ref": feedback["outcome_revision"]}

    @classmethod
    def _seal_analysis(cls, analysis):
        import hashlib
        value = {key: item for key, item in analysis.items() if key != "content_sha256"}
        return {**value, "content_sha256": hashlib.sha256(cls._json(value).encode()).hexdigest()}

    @classmethod
    def _check_analysis_digest(cls, analysis):
        if (not isinstance(analysis, dict) or analysis.get("version") not in {
                cls.DOMAIN_ANALYSIS_VERSION, cls.QUESTION_ANALYSIS_VERSION, cls.CURRENT_ANALYSIS_VERSION}
                or analysis != cls._seal_analysis(analysis)):
            raise RuntimeError("BUSINESS_WORK_ANALYSIS_BINDING_INVALID")

    def _planning_constraints(self, value):
        """User constraints bind a planning version; they establish no facts."""
        from datetime import datetime
        import re
        if value is None:
            return {}
        if not isinstance(value, dict) or set(value) - {"time_range", "resource_constraints", "domain_plan", "analysis_artifacts"}:
            raise ValueError("BUSINESS_WORK_PLANNING_CONSTRAINTS_INVALID")
        result = {}
        if "time_range" in value:
            period = value["time_range"]
            if not isinstance(period, dict) or set(period) != {"start", "end"}:
                raise ValueError("BUSINESS_WORK_PLANNING_PERIOD_INVALID")
            parsed = []
            for endpoint in ("start", "end"):
                self._text(period[endpoint], 80)
                try:
                    moment = datetime.fromisoformat(period[endpoint].replace("Z", "+00:00"))
                except ValueError as exc:
                    raise ValueError("BUSINESS_WORK_PLANNING_PERIOD_INVALID") from exc
                if moment.tzinfo is None:
                    raise ValueError("BUSINESS_WORK_PLANNING_TIMEZONE_REQUIRED")
                parsed.append(moment)
            if parsed[0] > parsed[1]:
                raise ValueError("BUSINESS_WORK_PLANNING_PERIOD_INVALID")
            result["time_range"] = dict(period)
        if "resource_constraints" in value:
            resources = value["resource_constraints"]
            # Previous normalized constraints may be inherited on explicit adopt.
            keys = {"budget_amount", "estimated_cost_amount", "currency", "as_of", "limits"}
            if not isinstance(resources, dict) or set(resources) not in (
                    keys, keys | {"claim_type", "actual_spend", "budget_fit"}):
                raise ValueError("BUSINESS_WORK_RESOURCE_CONSTRAINTS_INVALID")
            result["resource_constraints"] = self._resources({key: resources[key] for key in keys})
        if "domain_plan" in value:
            result["domain_plan"] = self._domain_plan(value["domain_plan"])
        if 'analysis_artifacts' in value:
            refs = value['analysis_artifacts']
            if not isinstance(refs, list):
                raise ValueError('BUSINESS_WORK_ANALYSIS_ARTIFACTS_INVALID')
            seen = set()
            for ref in refs:
                if not isinstance(ref, dict) or set(ref) != {'artifact_id', 'expected_sha256'}:
                    raise ValueError('BUSINESS_WORK_ANALYSIS_ARTIFACTS_INVALID')
                self._text(ref['artifact_id'], 256)
                if (ref['artifact_id'] in seen or not isinstance(ref['expected_sha256'], str)
                        or not re.fullmatch(r'[0-9a-f]{64}', ref['expected_sha256'])):
                    raise ValueError('BUSINESS_WORK_ANALYSIS_ARTIFACTS_INVALID')
                seen.add(ref['artifact_id'])
            result['analysis_artifacts'] = json.loads(self._json(refs))
        return result

    def _quantitative_artifacts(self, connection, analysis, references, *, accepted=None):
        """Consume existing Reporting calculations through SavedWork, never JSON claims.

        At explicit adoption, the numerical owner reproduces a saved result from
        its currently authorized original dataset. The domain signs that exact
        result. Later reads validate immutable bytes, sources and rights without
        recalculating or replacing an earlier decision's result.
        """
        if not references:
            return []
        actor = self._source_actor or self._action_actor
        if actor is None:
            raise RuntimeError('BUSINESS_WORK_ANALYSIS_ACTOR_NOT_BOUND')
        from lumenis.shared.reporting import saved_work, business_brief
        checks = {item['source_id']: item for item in analysis['source_checks']
                  if item['state'] == 'SOURCE_USE_VERIFIED'}
        outputs = []
        for index, reference in enumerate(references):
            committed = saved_work.read_committed_work(reference['artifact_id'], actor=actor,
                scope=self._action_scope(analysis['scope']), connection=connection)
            artifact, document = committed['artifact'], committed['document']
            if artifact['sha256'] != reference['expected_sha256']:
                raise RuntimeError('BUSINESS_WORK_ANALYSIS_ARTIFACT_CHANGED')
            statistics = document['payload'].get('statistics')
            if (not isinstance(statistics, dict) or statistics.get('recipe') != 'report-statistics-source/1'
                    or type(statistics.get('source_evidence_id')) is not int
                    or statistics.get('source_asset_id') not in checks
                    or statistics.get('dataset_sha256') != checks[statistics['source_asset_id']]['body_sha256']):
                raise PermissionError('BUSINESS_WORK_NUMERICAL_SOURCE_NOT_IN_TASK')
            check = checks[statistics['source_asset_id']]
            if str(statistics['source_evidence_id']) != str(check['binding']['evidence_ref']).split(':')[-1]:
                raise PermissionError('BUSINESS_WORK_NUMERICAL_SOURCE_NOT_IN_TASK')
            if accepted is None:
                # A user can edit a generic SavedWork payload. Storage integrity
                # alone must not promote hand-entered numbers to an executed method.
                produced = business_brief.analyze_statistics_source(statistics['source_evidence_id'],
                    actor=actor, scope=self._action_scope(analysis['scope']),
                    options=statistics.get('options'), business_purpose=statistics.get('business_purpose'))
                if self._json(produced['saved_work_draft']['payload']['statistics']) != self._json(statistics):
                    raise RuntimeError('BUSINESS_WORK_NUMERICAL_RESULT_NOT_REPRODUCED')
            value = {'artifact_id': artifact['artifact_id'], 'sha256': artifact['sha256'],
                     'work_id': document['work_id'], 'version': document['version'],
                     'parent_artifact_id': document.get('parent_artifact_id'),
                     'draft_digest': document['draft_digest'], 'title': document['title'],
                     'statistics': statistics, 'source_binding': check['binding'],
                     'processing': 'REPRODUCED_BY_EXISTING_REPORTING_OWNER_AT_ADOPTION',
                     'business_validation': 'NOT_ESTABLISHED', 'causation': 'NOT_ESTABLISHED'}
            if accepted is not None and (index >= len(accepted) or value != accepted[index]):
                raise RuntimeError('BUSINESS_WORK_NUMERICAL_RESULT_CHANGED')
            outputs.append(value)
        if accepted is not None and len(outputs) != len(accepted):
            raise RuntimeError('BUSINESS_WORK_NUMERICAL_RESULT_CHANGED')
        return outputs

    def _domain_plan(self, value):
        """Editable operator plans belong to the existing signed work version.

        A plan is not an authorization, a platform receipt, or a Canonical fact.
        The same constraints are checked on initial prepare and explicit adopt.
        """
        import re
        if (not isinstance(value, dict) or set(value) != {"workflow", "objective", "actions"}
                or not isinstance(value['actions'], list)):
            raise ValueError('BUSINESS_WORK_DOMAIN_PLAN_INVALID')
        self._text(value['workflow'], 80)
        self._text(value['objective'])
        if value['workflow'] not in {'venue_operations', 'event_response', 'feedback_resolution',
                'consumer_risk', 'brand_market', 'competitor_review', 'creator_collaboration', 'campaign'}:
            raise ValueError('BUSINESS_WORK_DOMAIN_PLAN_INVALID')
        result = json.loads(self._json(value))
        actions = result['actions']
        by_id = {}
        for action in actions:
            if (not isinstance(action, dict) or set(action) != {'action_id', 'target', 'responsible',
                    'due_at', 'deliverable', 'source_ids', 'depends_on', 'cost_estimate', 'success_measure'}):
                raise ValueError('BUSINESS_WORK_PLANNED_ACTION_INVALID')
            for key in ('action_id', 'target', 'responsible', 'deliverable'):
                self._text(action[key], 160 if key == 'action_id' else 1500)
            if action['action_id'] in by_id:
                raise ValueError('BUSINESS_WORK_PLANNED_ACTION_DUPLICATE')
            by_id[action['action_id']] = action
            if action['due_at'] is not None:
                self._timestamp(action['due_at'])
            for key in ('source_ids', 'depends_on'):
                if (not isinstance(action[key], list)
                        or any(not isinstance(item, str) or not item for item in action[key])
                        or len(set(action[key])) != len(action[key])):
                    raise ValueError('BUSINESS_WORK_PLANNED_ACTION_INVALID')
            if not action['source_ids']:
                raise ValueError('BUSINESS_WORK_PLANNED_ACTION_SOURCE_REQUIRED')
            cost = action['cost_estimate']
            if cost is not None:
                if not isinstance(cost, dict) or set(cost) != {'amount', 'currency'}:
                    raise ValueError('BUSINESS_WORK_PLANNED_COST_INVALID')
                if cost['amount'] is not None:
                    self._amount(cost['amount'], nonnegative=True)
                if not isinstance(cost['currency'], str) or not re.fullmatch(r'[A-Z]{3}', cost['currency']):
                    raise ValueError('BUSINESS_WORK_RESOURCE_CURRENCY_INVALID')
            measure = action['success_measure']
            if measure is not None:
                if (not isinstance(measure, dict) or set(measure) != {'name', 'definition', 'unit',
                        'baseline_value', 'target_value', 'window'}):
                    raise ValueError('BUSINESS_WORK_TARGET_MEASURE_INVALID')
                for key in ('name', 'definition', 'unit'):
                    self._text(measure[key])
                for key in ('baseline_value', 'target_value'):
                    if measure[key] is not None:
                        self._amount(measure[key])
                period = measure['window']
                if (not isinstance(period, dict) or set(period) != {'start', 'end'}
                        or self._timestamp(period['start']) >= self._timestamp(period['end'])):
                    raise ValueError('BUSINESS_WORK_TARGET_WINDOW_INVALID')
        # Iterative topological validation works for long campaign schedules;
        # no recursive depth limit or truncation hides missing dependencies.
        pending = {key: set(action['depends_on']) for key, action in by_id.items()}
        if any(not dependencies <= set(by_id) for dependencies in pending.values()):
            raise ValueError('BUSINESS_WORK_ACTION_DEPENDENCY_UNKNOWN')
        ready = [key for key, dependencies in pending.items() if not dependencies]
        reverse = {key: [] for key in by_id}
        for key, dependencies in pending.items():
            for dependency in dependencies:
                reverse[dependency].append(key)
        visited = 0
        while ready:
            current = ready.pop()
            visited += 1
            for successor in reverse[current]:
                pending[successor].remove(current)
                if not pending[successor]:
                    ready.append(successor)
        if visited != len(actions):
            raise ValueError('BUSINESS_WORK_ACTION_DEPENDENCY_CYCLE')
        return result

    def _domain_workbench(self, analysis, materials, planning):
        """Task-specific source review and executable internal planning results.

        Statement matches are locatable source claims, not semantic model
        conclusions. Actions, accountable people and targets come from the
        operator's plan; missing professional inputs stay explicit in each lane.
        """
        import re
        kind = analysis['kind']
        definitions = {
            'venue_operations': [
                ('operations', '门店与经营条件', r'营业|闭店|开放|停车|交通|时段|\b(?:hours|opening|closure|parking|access)\b',
                 ['场所/门店对应关系', '适用日期与营业时段', '经营方确认']),
                ('events', '活动与日历', r'活动|展览|发售|市集|\b(?:event|exhibition|launch|calendar)\b',
                 ['活动对象与场地', '开始/结束时间和时区', '取消与变更状态']),
                ('feedback', '服务反馈与处置', r'投诉|反馈|排队|服务|\b(?:complaint|feedback|queue|service)\b',
                 ['原反馈与回应', '适用门店/触点', '责任人与处理期限']),
            ],
            'consumer_risk': [
                ('feedback', '消费者陈述与反证', r'投诉|反馈|体验|消费者|\b(?:complaint|feedback|experience|consumer)\b',
                 ['原陈述与身份范围', '独立核验/反证', '样本与时间口径']),
                ('risk', '风险线索与依据', r'风险|侵权|安全|欺诈|\b(?:risk|rights|safety|fraud)\b',
                 ['原始依据', '权利/事实待核项', '人工处置责任与期限']),
            ],
            'brand_market': [
                ('positioning', '品牌与产品定位', r'品牌|产品|定位|品类|\b(?:brand|product|positioning|category)\b',
                 ['品牌/集团/门店层级', '市场与受众', '品牌自述与独立材料的区别']),
                ('competition', '市场与竞品比较', r'竞品|市场|份额|价格|\b(?:competitor|market|share|price)\b',
                 ['相同市场/期间/单位', '样本框与覆盖', '销售分母与提及分母分别核验']),
                ('consumer', '消费者与机会', r'消费者|需求|反馈|\b(?:consumer|demand|feedback|opportunity)\b',
                 ['获准消费者原资料', '需求与反证', '机会验证计划']),
            ],
            'creator_campaign': [
                ('creator', '创作者与合作依据', r'创作者|达人|博主|合作|\b(?:creator|influencer|KOS|KOL|KOC|UGC|collaboration)\b',
                 ['原生账号与合作身份', '受众/内容适配依据', '报价、使用权与人工候选']),
                ('campaign', '内容与渠道排期', r'排期|营销|传播|渠道|投放|\b(?:campaign|channel|schedule|post|content)\b',
                 ['Brief/内容版本', '目标账号与渠道格式', '排期/时区与具体批准']),
                ('measurement', '费用与复盘口径', r'预算|费用|退款|归因|转化|\b(?:budget|cost|refund|attribution|conversion)\b',
                 ['估算/承诺/实支/退款', '订单/触点身份', '观察窗口与归因方法']),
            ],
        }
        verified = {item['source_id'] for item in analysis['source_checks'] if item['state'] == 'SOURCE_USE_VERIFIED'}
        index = {item['source_id']: item for item in materials if item['source_id'] in verified}
        lanes = []
        for lane_id, label, pattern, requirements in definitions[kind]:
            claims = []
            for source_id, material in index.items():
                body = material['content']
                for sentence in re.finditer(r'[^\r\n。！？!?]+[。！？!?]?', body):
                    statement = sentence.group().strip()
                    if not statement or not re.search(pattern, statement, re.IGNORECASE):
                        continue
                    start = sentence.start() + len(sentence.group()) - len(sentence.group().lstrip())
                    end = start + len(statement)
                    claims.append({'source_id': source_id, 'title': material['title'],
                        'claim_type': 'SOURCE_REPORTED_CANDIDATE_NOT_CONFIRMED_FACT',
                        'reference': {'source_id': source_id, 'start': start, 'end': end,
                                      'statement': body[start:end],
                                      'body_sha256': material['binding']['content_hash'],
                                      'evidence_ref': material['binding']['evidence_ref']}})
            lanes.append({'lane_id': lane_id, 'label': label, 'claims': claims,
                          'state': 'SOURCE_REVIEW_REQUIRED' if claims else 'MATERIAL_NOT_FOUND',
                          'required_inputs': requirements, 'business_conclusion': 'NOT_ESTABLISHED'})
        plan = planning.get('domain_plan')
        allowed = ({'venue_operations', 'event_response', 'feedback_resolution', 'consumer_risk'}
                   if kind in {'venue_operations', 'consumer_risk'} else
                   {'brand_market', 'competitor_review', 'creator_collaboration', 'campaign'})
        if plan and plan['workflow'] not in allowed:
            raise ValueError('BUSINESS_WORK_PLAN_DOMAIN_MISMATCH')
        if plan and any(not set(action['source_ids']) <= verified for action in plan['actions']):
            raise PermissionError('BUSINESS_WORK_PLAN_SOURCE_NOT_AUTHORIZED')
        costs, schedule_conflicts = {}, []
        by_id = {item['action_id']: item for item in plan['actions']} if plan else {}
        for action in by_id.values():
            for dependency in action['depends_on']:
                parent = by_id[dependency]
                if (action['due_at'] is not None and parent['due_at'] is not None
                        and self._timestamp(parent['due_at']) > self._timestamp(action['due_at'])):
                    schedule_conflicts.append({'action_id': action['action_id'], 'dependency': dependency,
                        'state': 'DEPENDENCY_DUE_AFTER_SUCCESSOR'})
            cost = action['cost_estimate']
            if cost is not None:
                currency = costs.setdefault(cost['currency'], {'known_estimate': None, 'unknown_estimates': 0})
                if cost['amount'] is None:
                    currency['unknown_estimates'] += 1
                else:
                    currency['known_estimate'] = str(self._money_sum((currency['known_estimate'] or '0', cost['amount'])))
        budget = planning.get('resource_constraints')
        for currency, cost in costs.items():
            cost['complete_estimate'] = None if cost['unknown_estimates'] else cost['known_estimate']
            cost['budget_amount'] = budget['budget_amount'] if budget and budget['currency'] == currency else None
            cost['remaining_amount'] = self._decimal_remaining(cost['budget_amount'], cost['complete_estimate'])
            cost['actual_spend'] = None
        return {'method': 'source_bound_domain_workbench/1', 'kind': kind,
                'domain_id': analysis['scope']['domain_id'], 'review_lanes': lanes,
                'workflow': plan['workflow'] if plan else kind,
                'plan': plan, 'plan_origin': 'OPERATOR_DECLARED_NOT_EXTERNAL_FACT' if plan else None,
                'plan_state': 'SCHEDULE_CONFLICT' if schedule_conflicts else 'PLANNED' if plan else 'NOT_PROVIDED',
                'schedule_conflicts': schedule_conflicts, 'cost_assessment': costs,
                'unpriced_action_ids': [item['action_id'] for item in by_id.values() if item['cost_estimate'] is None],
                'coverage': {'authorized_materials': len(index),
                             'scanned_characters': sum(len(item['content']) for item in index.values()),
                             'semantic_completeness': 'NOT_ESTABLISHED'},
                'external_effect': 'NOT_AUTHORIZED', 'causation': 'NOT_ESTABLISHED'}

    @classmethod
    def _check_question_options(cls, analysis, options):
        import hashlib
        result = analysis.get("question_result")
        if (not isinstance(result, dict)
                or result.get("method") != ("source_bound_business_question_analysis/1"
                    if analysis["version"] == cls.CURRENT_ANALYSIS_VERSION else "source_bound_question_research_actions/1")
                or result.get("options_sha256") != hashlib.sha256(cls._json(options).encode()).hexdigest()):
            raise RuntimeError("BUSINESS_WORK_ANALYSIS_PROPOSAL_BINDING_INVALID")
        if result.get("generation") == "SYSTEM_DERIVED_RECOMMENDATIONS":
            verified = {item["source_id"] for item in analysis["source_checks"]
                        if item["state"] == "SOURCE_USE_VERIFIED"}
            if (not isinstance(options, list) or len(options) > 4
                    or len({option["option_id"] for option in options}) != len(options)
                    or any(option.get("claim_type") != "SYSTEM_DERIVED_RECOMMENDATION"
                           or option.get("basis_sha256") != result["basis_sha256"]
                           or not option["source_ids"] or not set(option["source_ids"]) <= verified
                           or option.get("cost_estimate") is not None or option.get("budget_fit") != "UNKNOWN"
                           for option in options)
                    or (not options) != (result.get("state") == "NOT_READY")):
                raise RuntimeError("BUSINESS_WORK_ANALYSIS_PROPOSAL_BINDING_INVALID")
        elif result.get("generation") == cls.REVISED_RESEARCH_GENERATION:
            revision = result.get("single_option_revision")
            if (not isinstance(options, list) or len(options) != 1 or not isinstance(revision, dict)
                    or options[0].get("claim_type") != cls.REVISED_RESEARCH_GENERATION
                    or options[0].get("operator_revision") != revision
                    or options[0].get("basis_sha256") != result.get("basis_sha256")
                    or revision.get("basis_sha256") != result.get("basis_sha256")
                    or not set(options[0]["source_ids"]) <= set(result["verified_source_ids"])):
                raise RuntimeError("BUSINESS_WORK_DERIVED_REVISION_BINDING_INVALID")
        elif result.get("generation") == "OPERATOR_PROPOSALS":
            verified = {item["source_id"] for item in analysis["source_checks"]
                        if item["state"] == "SOURCE_USE_VERIFIED"}
            if any(not set(option["source_ids"]) <= verified for option in options):
                raise RuntimeError("BUSINESS_WORK_ANALYSIS_PROPOSAL_BINDING_INVALID")
        else:
            raise RuntimeError("BUSINESS_WORK_ANALYSIS_PROPOSAL_ORIGIN_INVALID")

    def _prepare_analysis(self, connection, report, actor_ref, scope, kind, question,
                          requested_options, selected_sources, planning):
        report_ids = {item["source_id"] for item in report["source_brief"]["records"]}
        if not selected_sources or not selected_sources <= report_ids:
            raise PermissionError("BUSINESS_WORK_ANALYSIS_SELECTION_INVALID")
        analysis_report = {**report, "source_brief": {**report["source_brief"], "records": [
            item for item in report["source_brief"]["records"] if item["source_id"] in selected_sources]}}
        analysis = self._analyze_domain_sources(connection, analysis_report, actor_ref, scope, kind, question)
        if requested_options is not None and planning is None and selected_sources == report_ids:
            # Preserve the original manual writer and formatter exactly. Reading
            # an old signed version never reruns the new recommendation method.
            return analysis, self._options(requested_options, selected_sources)
        constraints = self._planning_constraints(planning)
        manual = (self._options(requested_options, selected_sources)
                  if requested_options is not None else None)
        return self._business_question_analysis(connection, analysis, selected_sources, constraints, manual)

    def _question_analysis(self, analysis, selected_sources, planning, manual, *, allow_partial=False):
        """Return traceable research actions supported by this question's inputs.

        This finite method provides source review, calendar checks and interaction
        input review. It does not solve an arbitrary market question or infer event
        validity, strategy, demand, sales, ROI or creator suitability from mentions.
        Each actual action has its own basis; no quota of comparable plans is filled.
        """
        import hashlib
        import re

        question = analysis["question"]
        patterns = {
            "SOURCE_REVIEW": r"核对|核验|复核|整理|导览|研究|来源|材料|검토|연구|출처|자료|\b(?:review|research|source|guide|organize|verify)\b",
            "CALENDAR_REVIEW": r"日期|时间|日程|活动|发售|날짜|일정|발매|\b(?:date|dates|calendar|schedule|release|event|events)\b",
            "INTERACTION_REVIEW": r"互动|点赞|评论|收藏|分享|반응|댓글|\b(?:interaction|interactions|engagement|likes|comments|shares)\b",
        }
        def negated(start):
            return re.search(r"(?:不要|无需|不需要|不做|不要求|不预测|禁止|금지|하지\s*않|do\s+not|don't|without|no)\s*.{0,4}$",
                             question[max(0, start - 18):start], flags=re.IGNORECASE) is not None

        matches = [{"goal": goal, "start": match.start(), "end": match.end()}
                   for goal, pattern in patterns.items()
                   for match in re.finditer(pattern, question, flags=re.IGNORECASE) if not negated(match.start())]
        unsupported = [{"start": match.start(), "end": match.end()}
                       for match in re.finditer(
                           r"预测|销量|营收|利润|市场份额|投资回报|竞品排名|投放优化|推荐创作者|매출|예측|"
                           r"\b(?:predict|prediction|forecast|sales|revenue|profit|roi|optimize|ranking)\b",
                           question, flags=re.IGNORECASE) if not negated(match.start())]
        goals = {item["goal"] for item in matches}
        verified = [item for item in analysis["source_checks"]
                    if item["state"] == "SOURCE_USE_VERIFIED" and item["source_id"] in selected_sources]
        source_ids = sorted(item["source_id"] for item in verified)
        materials = {item["source_id"]: item for item in analysis["material_review"]["sources"]
                     if item["source_id"] in source_ids}
        dates = [{"source_id": item["source_id"], **mention}
                 for item in verified for mention in item["source_reported_dates"]]
        complete = [materials[source_id] for source_id in source_ids
                    if materials[source_id]["engagement"]["state"] == "COMPLETE_INPUT"]
        basis = {"method": "source_bound_question_research_actions/1", "question": question,
                 "kind": analysis["kind"], "scope": analysis["scope"],
                 "source_report": analysis["source_report"], "source_checks": verified,
                 "materials": list(materials.values()), "planning_constraints": planning,
                 "goal_matches": matches, "unsupported_requests": unsupported}
        basis_hash = hashlib.sha256(self._json(basis).encode()).hexdigest()
        options = []

        def recommend(option_id, proposal, rationale, refs, unknowns, check):
            options.append({"option_id": option_id, "proposal": proposal, "rationale": rationale,
                            "source_ids": refs, "assumptions": ["仅在当前获准范围进行内部研究；由用户确认负责人与可用资源。"],
                            "unknowns": unknowns, "check": check, "claim_type": "SYSTEM_DERIVED_RECOMMENDATION",
                            "causation": "NOT_ESTABLISHED", "basis_sha256": basis_hash,
                            "cost_estimate": None, "budget_fit": "UNKNOWN"})

        if source_ids and "SOURCE_REVIEW" in goals:
            missing = [item["required_role"] for item in analysis["material_review"]["checks"]
                       if item["state"] == "MISSING_MATERIAL"]
            recommend("source-review", "将已核验材料整理为可回溯的内部研究底稿",
                      "本次可使用来源：" + "、".join(source_ids) + "；保留各来源链接、原生时间、角色标注与证据定位，不把材料整理当作市场判断。",
                      source_ids, ["缺少的业务材料角色：" + "、".join(missing) if missing else "材料角色标注仍需核对原文。",
                                   "消费者、市场表现与商业使用权不由这些来源自动成立。"],
                      "逐来源核对适用对象、引用权限和报告问题；把无法确认的业务结论保留为未知。")
        if source_ids and "CALENDAR_REVIEW" in goals:
            dated_ids = sorted({item["source_id"] for item in dates})
            reported = sorted({item["date"] for item in dates})
            recommend("calendar-review", "建立来源日期核验清单" if dates else "核对当前材料未提供的活动日期",
                      ("本次来源提及日期：" + "、".join(reported) + "；每一项已绑定来源和正文位置。"
                       if dates else "获准文本窗口没有找到完整年月日，不能把发布时间或采集时间替代为活动日期。"),
                      dated_ids or source_ids, ["事件对象、时区、有效期与是否落入用户期间尚未确认。"],
                      "按清单逐项回到原来源核对；确认前不更新活动日历或对外宣称活动有效。")
        if source_ids and "INTERACTION_REVIEW" in goals:
            recommend("interaction-review", "核对来源互动字段及可比口径",
                      ("当前四项字段齐全的来源：" + "、".join(item["source_id"] for item in complete)
                       if complete else "当前来源缺少完整互动输入，不能产出互动合计或比较排名。"),
                      source_ids, ["品牌、期间、平台口径、样本分母与真实业务效果的可比性尚未建立。"],
                      "核对 likes/comments/collects/shares 四项和观测期间；缺值不填零，互动不折算销量或回报。")
        reason = ("NO_AUTHORIZED_ANALYSIS_SOURCE" if not source_ids else
                  "BUSINESS_QUESTION_METHOD_UNSUPPORTED" if not matches or (unsupported and not allow_partial) else None)
        if reason is not None:
            options = []
        if manual is not None:
            # A manual proposal is still the user's own proposal, even when this
            # finite method cannot answer the business question. No body rights
            # means no new derived analysis, including this mixed planning path.
            admissible = all(set(option["source_ids"]) <= set(source_ids) for option in manual)
            options = manual if admissible else []
            if not admissible:
                reason = "OPERATOR_PROPOSAL_SOURCE_USE_UNAVAILABLE"
        result = {"state": ("OPERATOR_PROPOSALS_ONLY" if manual is not None and options else
                            "RESEARCH_ACTIONS_PROPOSED" if reason is None else "NOT_READY"),
                  "reason": reason, "method": basis["method"], "goal_matches": matches,
                  "unsupported_requests": unsupported,
                  "planning_constraints": planning, "selected_source_ids": sorted(selected_sources),
                  "verified_source_ids": source_ids, "basis_sha256": basis_hash,
                  "generation": "OPERATOR_PROPOSALS" if manual is not None else "SYSTEM_DERIVED_RECOMMENDATIONS",
                  "unadmitted_operator_option_ids": [option["option_id"] for option in manual] if manual and not options else [],
                  "options_sha256": hashlib.sha256(self._json(options).encode()).hexdigest(),
                  "findings": {"source_materials": list(materials.values()), "reported_dates": dates,
                               "complete_interaction_inputs": complete},
                  "answer_scope": "SOURCE_REVIEW_CALENDAR_AND_INTERACTION_INPUTS_ONLY",
                  "options_relation": "INDEPENDENT_RESEARCH_ACTIONS_NOT_COMPARABLE_BUSINESS_STRATEGIES",
                  "full_business_answer": "NOT_ESTABLISHED", "proposal_costs": "UNKNOWN",
                  "time_applicability": "EVENT_AND_TIMEZONE_CONFIRMATION_REQUIRED",
                  "external_effect": "NOT_AUTHORIZED"}
        conclusion = ("人工提案按原归属保留；本有限方法没有完成该问题的完整业务分析。"
                      if manual is not None and options and reason is not None else
                      "根据本次问题与获准材料，已形成可核对的研究动作及对应来源清单；完整业务判断仍需补齐所列材料、口径与结果证据。"
                      if reason is None else "当前没有形成可用的业务建议；请补充获准材料或明确研究目标，再显式生成新的分析版本。")
        return self._seal_analysis({**analysis, "version": self.QUESTION_ANALYSIS_VERSION,
                                   "state": "ANALYZED_WITH_LIMITATIONS" if reason is None else "NOT_READY",
                                   "question_result": result,
                                   "judgment": {**analysis["judgment"], "conclusion": conclusion}}), options

    @staticmethod
    def _business_role_name(value):
        return {"VENUE_OPERATOR_DISCLOSURE": "运营方披露", "CONSUMER_FEEDBACK": "消费者反馈",
                "OFFICIAL_BRAND_SELF_DESCRIPTION": "品牌官方资料", "MARKET_DISCLOSURE": "市场与竞品资料",
                "CREATOR_CONTENT": "创作者内容", "ENTITY_PROFILE_RESEARCH_COMPILATION": "主体研究汇编",
                "UNKNOWN": "待确认用途的资料"}.get(value, "待确认用途的资料")

    @staticmethod
    def _reported_quantity_review(content, *, source_id, evidence_ref, body_sha256, locators=()):
        """Exact arithmetic on explicit report groups, never inferred native rows/NLP."""
        import re

        lines, offset = [], 0
        for raw in content.splitlines(keepends=True):
            end = offset + len(raw.rstrip("\r\n"))
            plain = re.sub(r"[*`#]", "", raw).strip()
            lines.append({"plain": plain, "raw": raw.rstrip("\r\n"), "start": offset, "end": end})
            offset += len(raw)

        def reference(line):
            start, end = line["start"], min(line["end"], line["start"] + 700)
            return {"source_id": source_id, "evidence_ref": evidence_ref,
                    "start": start, "end": end, "body_sha256": body_sha256,
                    "statement": content[start:end], "locators": [dict(item) for item in locators
                    if isinstance(item, dict) and type(item.get("start")) is int and type(item.get("end")) is int
                    and item["start"] < end and item["end"] > start]}

        integer = r"(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)"
        approximate = r"约|大约|至少|至多|超过|不足|估计|预计|about|approximately|at least"
        declarations, checks, scope_notes = [], [], []
        sections, current = [], None
        for line in lines:
            plain, raw = line["plain"], line["raw"]
            if re.search(r"数据范围|统计范围|超范围|超出.{0,40}范围|范围外|懒加载|显示总数|局限|未定位|缺口|完整性声明", plain):
                scope_notes.append(reference(line))
            if re.search(r"数据规模|样本(?:规模|总量|总数)|数据总量|dataset|sample size", plain, re.IGNORECASE):
                for match in re.finditer(r"(?<![\d,+-])(" + integer + r")\s*(篇帖子|条帖子|篇笔记|条笔记|条评论|posts?|comments?)", plain, re.IGNORECASE):
                    if len(match[1].replace(",", "")) > 40:
                        continue
                    unit = "评论" if re.search(r"评论|comment", match[2], re.IGNORECASE) else "帖子"
                    exact = not re.search(r"(?:" + approximate + r")\s*$", plain[:match.start()], re.IGNORECASE)
                    declarations.append({"value": match[1].replace(",", ""), "unit": unit,
                        "exact": exact, "claim_type": "SOURCE_REPORTED_NOT_INDEPENDENTLY_VERIFIED",
                        "reference": reference(line)})
                totals = [item for item in declarations if item["reference"]["start"] == line["start"]
                          and item["unit"] == "帖子" and item["exact"]]
                for parenthesis in re.findall(r"[（(]([^（）()]*)[）)]", plain):
                    pairs = list(re.finditer(r"([^\d，,；;]{1,30}?)\s*(" + integer + r")\s*(篇|条)", parenthesis))
                    if len(totals) != 1 or len(pairs) < 2 or re.search(approximate, parenthesis, re.IGNORECASE):
                        continue
                    if len({item[3] for item in pairs}) != 1 or any(len(item[2].replace(",", "")) > 40 for item in pairs):
                        continue
                    members = [{"label": item[1].strip(), "value": item[2].replace(",", ""),
                                "unit": "帖子", "reference": reference(line)} for item in pairs]
                    total = sum(int(item["value"]) for item in members)
                    declared = int(totals[0]["value"])
                    checks.append({"kind": "EXPLICIT_TOTAL_PARTITION", "title": "报告总量与分组",
                        "state": "ARITHMETIC_MATCH" if total == declared else "REVIEW_REQUIRED",
                        "unit": "帖子", "members": members, "calculated_sum": str(total),
                        "reported_total": str(declared), "difference": str(declared - total),
                        "summary": " + ".join(item["label"] + " " + item["value"] for item in members)
                                   + f" = {total} 篇；报告声明 {declared} 篇。",
                        "reference": reference(line),
                        "limitation": "仅核对同一句报告声明的数值关系；不证明分组互斥、去重或原生帖子完整性。",
                        "next_action": "回到逐帖记录核对身份、去重和官方分类；保留报告声明与原生核验的区别。"})
            heading = re.match(r"^\s*#{1,6}\s+(.+?)\s*$", raw)
            bold_heading = re.match(r"^\s*\*\*([^*]+)\*\*\s*[：:]?\s*$", raw)
            if heading or bold_heading or plain in {"时间分布", "情感分布"}:
                current = {"title": (heading[1] if heading else bold_heading[1] if bold_heading else plain).strip(),
                           "header": line, "lines": []}
                sections.append(current)
            elif current is not None:
                current["lines"].append(line)
        exact_post_totals = {item["value"] for item in declarations if item["unit"] == "帖子" and item["exact"]}
        for section in sections:
            title = section["title"]
            if title == "时间分布":
                members, inexact = [], False
                for line in section["lines"]:
                    plain = line["plain"]
                    match = re.match(r"^[-•\s]*(.+?)[：:]\s*(" + integer + r")\s*(篇|条)(帖子|笔记|评论)?(?:[，,。；;]|$)", plain)
                    if re.search(r"(?:" + approximate + r")\s*" + integer + r"\s*(?:篇|条)", plain, re.IGNORECASE):
                        inexact = True
                    if match and len(match[2].replace(",", "")) <= 40:
                        members.append({"label": match[1], "value": match[2].replace(",", ""),
                                        "unit": match[3], "entity": match[4], "reference": reference(line)})
                compatible = (len(members) >= 2 and len({item["unit"] for item in members}) == 1
                              and all(item["entity"] in {None, "帖子", "笔记"} for item in members)
                              and all(item["unit"] == "篇" or item["entity"] in {"帖子", "笔记"} for item in members)
                              and not inexact and len(exact_post_totals) == 1)
                if compatible:
                    total, declared = sum(int(item["value"]) for item in members), int(next(iter(exact_post_totals)))
                    checks.append({"kind": "TIME_GROUP_TOTAL", "title": "时间分布与报告总量",
                        "state": "ARITHMETIC_MATCH" if total == declared else "REVIEW_REQUIRED",
                        "unit": "帖子", "members": members, "calculated_sum": str(total),
                        "reported_total": str(declared), "difference": str(declared - total),
                        "summary": " + ".join(item["value"] for item in members)
                                   + f" = {total} 篇；报告总量 {declared} 篇，相差 {declared - total} 篇。",
                        "reference": reference(section["header"]),
                        "limitation": "仅比较报告中的同单位列示项；分组完整性、互斥性和总数是否包含范围外记录尚未证实，差额不等于漏采数量。",
                        "next_action": "按原帖发布时间核对分母、范围外记录及未列示项，明确统计口径后再修订报告。"})
            if title == "情感分布":
                rows = []
                for line in section["lines"]:
                    match = re.match(r"^\|\s*([^|]+?)\s*\|\s*(" + integer + r")\s*\|\s*([0-9]+(?:\.[0-9]+)?)%\s*\|$", line["plain"])
                    if match and len(match[2].replace(",", "")) <= 40:
                        rows.append({"label": match[1].strip(), "value": match[2].replace(",", ""),
                                     "reported_percent": match[3], "reference": reference(line)})
                if len(rows) >= 2:
                    total = sum(int(item["value"]) for item in rows)
                    checks.append({"kind": "TABLE_COUNT_DENOMINATOR", "title": "情感表的统计分母",
                        "state": "DENOMINATOR_REVIEW_REQUIRED", "unit": "表内数量", "members": rows,
                        "calculated_sum": str(total), "reference": reference(section["header"]),
                        "summary": "表内列示数量 " + " + ".join(item["value"] for item in rows)
                                   + f" = {total}；占比仍是报告声明，未显式确认按帖子还是评论编码。",
                        "limitation": "仅加总同一表的数量列；不以数值巧合推断总体、互斥性、完整分母或真实消费者情绪。",
                        "next_action": "核对情感编码对象、互斥规则和实际分母，再验算各占比及四舍五入。"})
            top = re.search(r"(?<![A-Za-z])top\s*([1-9][0-9]{0,3})(?![0-9])", title, re.IGNORECASE)
            if top:
                ranked = []
                for line in section["lines"]:
                    row = re.match(r"^\s*\|\s*([1-9][0-9]*)\s*\|", line["plain"])
                    entry = re.match(r"^\s*([1-9][0-9]*)[.、)]\s+", line["plain"])
                    if row or entry:
                        number = (row or entry)[1]
                        ranked.append({"rank": int(number) if len(number) <= 40 else None, "reference": reference(line)})
                if ranked:
                    target, count = int(top[1]), len(ranked)
                    ranks = [item["rank"] for item in ranked]
                    valid = all(type(rank) is int for rank in ranks) and len(set(ranks)) == count and sorted(ranks) == list(range(1, count + 1))
                    checks.append({"kind": "TOP_LIST_COVERAGE", "title": title + "的列示完整性",
                        "state": "ARITHMETIC_MATCH" if valid and count == target else "REVIEW_REQUIRED",
                        "declared_items": target, "listed_items": count, "members": ranked,
                        "summary": f"标题声明 Top {target}，实际列示 {count} 个排名或编号条目。",
                        "reference": reference(section["header"]),
                        "limitation": "编号条目数不证明独立对象或独立热词数；一项可包含多个词，重复、并列及未列示名次需核验。",
                        "next_action": "核对完整排名依据和并列项；补齐可定位条目或明确改标实际列示范围。"})
        return {"method": "deterministic_explicit_report_groups/1", "source_id": source_id,
                "evidence_ref": evidence_ref, "body_sha256": body_sha256,
                "coverage": {"scanned_characters": len(content), "source_characters": len(content),
                             "nonempty_lines": sum(bool(line["plain"]) for line in lines)},
                "declared_counts": declarations, "checks": checks, "scope_notes": scope_notes,
                "claim_type": "SOURCE_REPORT_ARITHMETIC_NOT_NATIVE_OBSERVATIONS",
                "limitations": ["只处理正文明确的数据规模、同单位分组和Top编号结构；不进行通用语义理解。",
                    "报告声明的帖子数和评论数分别保留；一份报告不等于已核验其全部原生记录。",
                    "未声明或近似数、单位不同、多个分母及范围未对齐时，不自动建立比例、增长、因果或采集完整性结论。"]}

    def _report_quantity_materials(self, connection, analysis):
        """Reuse verified original Evidence/SourceUse and its imported locators."""
        import hashlib

        from lumenis.shared.reporting import saved_work
        from lumenis.shared.reporting.business_brief import _source_use_material
        from lumenis.system.security import permission

        scope = analysis["scope"]
        actor = self._source_actor or permission.resolve_local_workspace_principal(module="reports", action="read") or self._action_actor
        if actor is None:
            raise PermissionError("BUSINESS_WORK_SOURCE_ACTOR_REQUIRED")
        context = saved_work.authorize(actor, self._action_scope(scope), action="read", connection=connection)
        materials = []
        for check in analysis["source_checks"]:
            if check["state"] != "SOURCE_USE_VERIFIED":
                continue
            row = self._canonical_source(connection, check["source_id"], scope)
            original = saved_work._verified_evidence(connection, int(check["binding"]["evidence_ref"].split(":")[-1]), context, actor)
            content = original["raw_content"]
            if (content != row.get("content") or hashlib.sha256(content.encode()).hexdigest() != check["body_sha256"]):
                raise RuntimeError("BUSINESS_WORK_ANALYSIS_SOURCE_CHANGED")
            source = {**row, "text": content, "body_sha256": check["body_sha256"],
                      "content_evidence_ref": check["binding"]["evidence_ref"],
                      "text_selection": {"start": 0, "end": len(content)}}
            binding = _source_use_material({"scope": self._action_scope(scope), "sources": [source]}, actor, connection=connection)[0]
            locators = original["provenance"].get("locators", [])
            materials.append({"source_id": row["source_id"], "title": row.get("title") or "获准材料",
                              "content": content, "binding": binding,
                              "locators": locators if isinstance(locators, list) else []})
        return materials

    def _business_question_analysis(self, connection, analysis, selected_sources, planning, manual):
        """Analyze admitted observations, keeping missing business inputs explicit.

        This is a signed derived snapshot, not another Canonical owner. Native
        publication defines a cohort; neither capture time nor current counters
        establish interactions during that period. Stored labels lack individual
        model/reviewer provenance and cannot become observed consumer facts.
        """
        import hashlib
        import re
        from datetime import datetime

        from canonical_metrics import (
            engagement_stats,
            neg_ratio,
            risk_count,
            sentiment_count,
        )

        previous, options = self._question_analysis(
            analysis, selected_sources, planning, manual, allow_partial=True)
        result = previous["question_result"]
        verified_ids = set(result["verified_source_ids"])
        document_reviews = []
        source_materials = self._report_quantity_materials(connection, analysis)
        for material in source_materials:
            binding = material["binding"]
            review = self._reported_quantity_review(material["content"], source_id=material["source_id"],
                evidence_ref=binding["evidence_ref"], body_sha256=binding["content_hash"], locators=material["locators"])
            document_reviews.append({**review, "title": material["title"], "binding": binding})
        fields = ("canonical_id", "source_id", "source_platform", "subject_id", "brand_focus_id",
                  "publish_datetime", "captured_at", "sentiment", "risk_level",
                  "engagement_likes", "engagement_comments", "engagement_collects", "engagement_shares")
        inputs = [{key: row.get(key) for key in fields}
                  for source_id in sorted(verified_ids)
                  for row in [self._canonical_source(connection, source_id, analysis["scope"])]]
        period = {"basis": "NATIVE_PUBLICATION_COHORT_NOT_INTERACTION_OBSERVATION",
                  "time_range": planning.get("time_range"), "included_source_ids": [], "excluded": []}
        bounds = planning.get("time_range")
        start = datetime.fromisoformat(bounds["start"].replace("Z", "+00:00")) if bounds else None
        end = datetime.fromisoformat(bounds["end"].replace("Z", "+00:00")) if bounds else None
        included = []
        for row in inputs:
            reason = None
            if bounds:
                try:
                    published = datetime.fromisoformat((row["publish_datetime"] or "").replace("Z", "+00:00"))
                    reason = ("NATIVE_PUBLICATION_TIMEZONE_UNKNOWN" if published.tzinfo is None else
                              "OUTSIDE_PUBLICATION_PERIOD" if not start <= published <= end else None)
                except (ValueError, TypeError, AttributeError):
                    reason = "NATIVE_PUBLICATION_TIME_UNKNOWN"
            if reason:
                period["excluded"].append({"source_id": row["source_id"], "reason": reason})
            else:
                included.append(row)
                period["included_source_ids"].append(row["source_id"])
        groups = {}
        for row in included:
            key = (row["source_platform"], row["subject_id"], row["brand_focus_id"])
            groups.setdefault(key, []).append(row)
        cohorts = []
        for (platform, subject, brand), rows in sorted(groups.items(), key=lambda item: self._json(item[0])):
            sentiment = sentiment_count(rows)
            counters = [{name: row["engagement_" + name] for name in ("likes", "comments", "collects", "shares")}
                        for row in rows]
            cohorts.append({"source_platform": platform, "subject_id": subject, "brand_focus_id": brand,
                            "source_ids": [row["source_id"] for row in rows], "source_count": len(rows),
                            "engagement": engagement_stats(counters), "sentiment": sentiment,
                            "risk": risk_count(rows), "negative_label_ratio": neg_ratio(sentiment),
                            "label_interpretation": "STORED_ANNOTATIONS_NOT_OBSERVED_CONSUMER_FACTS",
                            "comparison_state": "SAMPLE_FRAME_AND_METRIC_OBSERVATION_TIME_NOT_ESTABLISHED"})
        limits = ["仅分析本次获准选定来源，不代表全市场或消费者总体；未采集与真实零分别保留。",
                  "平台与主体分别呈现；没有同口径样本框及指标观测时间，不跨组排名或推断增长。",
                  "情感和风险为存储标签，缺少逐项标注出处，不能作为已核实消费者情绪或风险发生率。",
                  "发布时间用于发布样本筛选；采集时间不替代发布时间，当前互动不代表期间内发生的互动。",
                  "历史互动字段的采集完整性需原来源核验，存储零不自动证明平台原生实测。"]
        answers = []

        def answer(goal, state, summary, refs, limitations, next_action):
            answers.append({"goal": goal, "state": state, "summary": summary, "source_ids": sorted(refs),
                            "limitations": limitations, "next_action": next_action})

        goals = {item["goal"] for item in result["goal_matches"]}
        if "SOURCE_REVIEW" in goals:
            missing = [item["required_role"] for item in analysis["material_review"]["checks"]
                       if item["state"] == "MISSING_MATERIAL"]
            answer("SOURCE_REVIEW", "PARTIAL" if missing or len(inputs) < len(selected_sources) else "AVAILABLE",
                   f"本次可用于内部研究的来源为 {len(inputs)} 项；"
                   + ("仍需补充：" + "、".join(self._business_role_name(role) for role in missing) + "。" if missing else "所需材料已有用途标注，仍需核对原文。"),
                   verified_ids, ["角色标注和官网自述不等于消费者或市场结论。"],
                   "核验报告列出的来源和用途；补充缺少角色的获准材料后显式采用新版本。")
        if "CALENDAR_REVIEW" in goals:
            dates = result["findings"]["reported_dates"]
            answer("CALENDAR_REVIEW", "PARTIAL" if dates else "UNAVAILABLE",
                   "来源文本提及日期：" + "、".join(sorted({item["date"] for item in dates}))
                   if dates else "获准文本窗口未提供可核验的完整活动日期。",
                   {item["source_id"] for item in dates}, ["日期提及不证明活动对象、时区、有效期或已执行。"],
                   "逐项核对原活动公告的对象、日期、时区与有效期；核实前不更新正式活动或外发结论。")
        if "INTERACTION_REVIEW" in goals:
            summaries = []
            for cohort in cohorts:
                metric = cohort["engagement"]
                q = metric["quality"]
                summaries.append(f"{cohort['source_platform'] or '未知平台'}，"
                                 f"当前获准范围：{cohort['source_count']}项材料，已知互动组件{q['known_field_count']}/{q['expected_field_count']}，"
                                 + (f"完整合计{metric['sum']}。" if metric["sum"] is not None else
                                    f"已知组件小计{metric['observed_sum']}；完整合计未知。" if metric["observed_sum"] is not None else
                                    "无已知互动组件，合计未知。"))
            answer("INTERACTION_REVIEW", "UNAVAILABLE" if not cohorts else
                   "AVAILABLE" if all(c["engagement"]["quality"]["state"] == "COMPLETE" for c in cohorts) else "PARTIAL",
                   "；".join(summaries) if summaries else "用户期间内没有可用于互动核对的获准发布样本。",
                   period["included_source_ids"], limits[1:2] + limits[3:],
                   "核对缺失互动字段和各平台观测时点；补齐同口径样本前不比较增长、销量或回报。")
        def positive_matches(pattern):
            for match in re.finditer(pattern, analysis["question"], flags=re.IGNORECASE):
                prefix = re.split(r"[，。；！？,;.!?]", analysis["question"][:match.start()])[-1]
                if not re.search(
                    r"(?:不要|不需要|无需|不做|\b(?:without|no|not)\b|don't|하지\s*말).{0,32}$",
                    prefix, re.IGNORECASE,
                ):
                    yield match

        label_pattern = r"情感|反馈|消费者|风险|舆情|口碑|sentiment|consumer|feedback|risk|소비자|피드백|위험"
        label_matches = list(positive_matches(label_pattern))
        if label_matches:
            result["goal_matches"] += [{"goal": "LABEL_REVIEW", "start": m.start(), "end": m.end()} for m in label_matches]
            summaries = [f"{c['source_platform'] or '未知平台'}：{c['source_count']}条来源中，"
                         f"情感已知{c['sentiment']['known']}、未知{c['sentiment']['unknown']}，"
                         f"负面标签{c['sentiment']['negative']}；风险high={c['risk']['high']}、critical={c['risk']['critical']}。"
                         for c in cohorts]
            answer("LABEL_REVIEW", "PARTIAL" if cohorts else "UNAVAILABLE",
                   "；".join(summaries) if summaries else "用户期间内没有获准可核对的来源标签。",
                   period["included_source_ids"], limits[:3],
                   "回到获准原文核对标签与消费者身份；需要同口径获准反馈样本才能评价体验或风险。")
            if inputs and manual is None:
                options.append({"option_id": "label-review", "proposal": "核对来源标签及消费者反馈缺口",
                                "rationale": answers[-1]["summary"], "source_ids": sorted(verified_ids),
                                "assumptions": ["仅在获准范围内核验，不把标签当成消费者事实。"],
                                "unknowns": limits[:3], "check": answers[-1]["next_action"],
                                "claim_type": "SYSTEM_DERIVED_RECOMMENDATION", "causation": "NOT_ESTABLISHED",
                                "cost_estimate": None, "budget_fit": "UNKNOWN"})
        compare_pattern = r"市场|竞品|比较|品牌|创作者|market|competitor|compar(?:e|ison)|brand|creator|시장|경쟁|비교"
        if any(positive_matches(compare_pattern)):
            objects = {(row["subject_id"], row["brand_focus_id"]) for row in included}
            answer("BUSINESS_COMPARISON", "PARTIAL" if included else "UNAVAILABLE",
                   f"期间内获准资料包含 {len(objects)} 个范围对象、{len(cohorts)} 个平台/对象样本组；"
                   "当前可核对各组材料与指标完整性，尚不能确立市场优劣、创作者适配度或投放回报。",
                   period["included_source_ids"], limits[:3],
                   "补充比较对象相同期间、单位与来源口径的市场/受众/成本结果；保留各组原范围，核验后继续比较。")
            if inputs and manual is None and not options:
                options.append({"option_id": "source-review", "proposal": "核对本次比较对象与同口径材料缺口",
                                "rationale": answers[-1]["summary"], "source_ids": sorted(verified_ids),
                                "assumptions": ["比较只使用本次获准资料，不把缺失对象或结果填零。"],
                                "unknowns": limits[:3], "check": answers[-1]["next_action"],
                                "claim_type": "SYSTEM_DERIVED_RECOMMENDATION", "causation": "NOT_ESTABLISHED",
                                "cost_estimate": None, "budget_fit": "UNKNOWN"})
        if result["unsupported_requests"]:
            answer("BUSINESS_RESULT", "UNAVAILABLE", "销量、营收、预测或投放回报缺少已授权的业务结果与可比基线，当前不能计算。",
                   [], ["互动、官网自述和标签不能替代销量、转化、成本、曝光或因果。"],
                   "提供对应期间、对象和单位的获准销量/转化/成本及可比基线；核验后由既有业务分析采用新版本。")
        numeric_reviews = [item for item in document_reviews if item["declared_counts"] or item["checks"]]
        if numeric_reviews:
            count_summaries = []
            for item in numeric_reviews:
                values = "、".join(("约 " if not value["exact"] else "") + value["value"] + " " + value["unit"]
                                   for value in item["declared_counts"])
                count_summaries.append(item["title"] + "：" + ("报告声明 " + values + "。" if values else "已核对正文中明确列示的分组。"))
            answer("REPORT_QUANTITIES", "PARTIAL", " ".join(count_summaries),
                   {item["source_id"] for item in numeric_reviews},
                   ["报告中的样本量、评论和占比是来源声明；本次读入材料数不等于逐条核验的帖子数。",
                    "仅对明确同单位、同来源的列示分组做数值核对；差额不能自动解释为漏采或经营效果。"],
                   "先核对下面的总分关系、统计分母和榜单列示项；带原文定位回查后，显式采用修订版本。")
            answers = [answers[-1], *answers[:-1]]
            if manual is None:
                replacement = {"proposal": "校准报告数字、统计分母与列示缺口",
                               "rationale": " ".join(check["summary"] for item in numeric_reviews for check in item["checks"])
                                            or answers[0]["summary"],
                               "check": "按来源定位核对总分关系与范围；保留未证实口径，修订后由用户明确采用新版本。"}
                found = any(item["option_id"] == "source-review" for item in options)
                if found:
                    options = [{**item, **replacement} if item["option_id"] == "source-review" else item for item in options]
                elif len(options) < 4:
                    options.append({"option_id": "source-review", **replacement, "source_ids": sorted(verified_ids),
                        "assumptions": ["报告数据仅作来源声明，核验不授予外部执行权限。"],
                        "unknowns": answers[0]["limitations"], "claim_type": "SYSTEM_DERIVED_RECOMMENDATION",
                        "causation": "NOT_ESTABLISHED", "cost_estimate": None, "budget_fit": "UNKNOWN"})
        if manual is None:
            by_goal = {item["goal"]: item for item in answers}
            roles = {"VENUE_OPERATOR_DISCLOSURE", "CONSUMER_FEEDBACK", "OFFICIAL_BRAND_SELF_DESCRIPTION",
                     "MARKET_DISCLOSURE", "CREATOR_CONTENT", "ENTITY_PROFILE_RESEARCH_COMPILATION"}
            def prose(value):
                for role in roles:
                    value = value.replace(role, self._business_role_name(role))
                return value
            rewritten = []
            for item in options:
                goal = {"source-review": "SOURCE_REVIEW", "calendar-review": "CALENDAR_REVIEW",
                        "interaction-review": "INTERACTION_REVIEW", "label-review": "LABEL_REVIEW"}.get(item["option_id"])
                rationale = (by_goal[goal]["summary"] if goal in by_goal and
                             not (numeric_reviews and item["option_id"] == "source-review") else item["rationale"])
                rewritten.append({**item, "rationale": prose(rationale), "unknowns": [prose(value) for value in item["unknowns"]]})
            options = rewritten
        if not answers:
            answer("BUSINESS_QUESTION", "UNAVAILABLE", "当前问题缺少可匹配的获准分析输入。", [], limits,
                   "明确需要核对的运营、反馈、品牌或传播问题，提供对象/期间及获准材料，继续同一任务。")
        if manual is None and options:
            result["reason"] = None
            result["state"] = "RESEARCH_ACTIONS_PROPOSED"
        report = {"state": "UNAVAILABLE" if not verified_ids or all(item["state"] == "UNAVAILABLE" for item in answers) else
                  "AVAILABLE" if all(item["state"] == "AVAILABLE" for item in answers) else "PARTIAL",
                  "answers": answers, "canonical_inputs": inputs, "cohorts": cohorts, "period": period,
                  "document_reviews": document_reviews,
                  "limitations": limits, "next_actions": [item["next_action"] for item in answers],
                  "business_outcome": "NOT_OBSERVED", "causation": "NOT_ESTABLISHED",
                  "metric_input_claim": "IMMUTABLE_CANONICAL_SNAPSHOT_NOT_NEW_EXTERNAL_FACT"}
        report['domain_workbench'] = self._domain_workbench(previous, source_materials, planning)
        if planning.get('analysis_artifacts'):
            report['quantitative_results'] = self._quantitative_artifacts(
                connection, previous, planning['analysis_artifacts'])
            for item in report['quantitative_results']:
                statistics = item['statistics']
                computed = statistics['result']
                answer('QUANTITATIVE_ANALYSIS', 'AVAILABLE' if computed['state'] == 'READY' else 'PARTIAL',
                       '已按原始获准数据复核已保存的计算成果：' + item['title'] + '。'
                       + ('计算已完成；业务适用性和因果解释仍须核验。' if computed['state'] == 'READY'
                          else '已保留原方法返回的输入不足或计算限制，未补造结果。'),
                       [statistics['source_asset_id']], computed.get('limitations', [])
                       + ['计算只覆盖声明的数据集和方法假设，不证明总体代表性或经营因果。'],
                       '检查原结果的单位、分母、窗口、假设与反证，选择适用建议并记录实际行动和观察。')
            if manual is None and not options:
                options.append({'option_id': 'quantitative-review', 'proposal': '采用本次已复核计算作为方案讨论依据',
                    'rationale': '已复核的原结果和数据集随本决定保存；采用其明确口径，不把数值计算当经营因果。',
                    'source_ids': sorted({item['statistics']['source_asset_id'] for item in report['quantitative_results']}),
                    'assumptions': ['核验该方法假设与当前经营问题匹配，由用户确定责任行动。'],
                    'unknowns': ['结果尚未经过实际经营验证；行动成本和真实效果仍需依据。'],
                    'check': '记录适用范围、反证、实际行动与独立观察，保留计算和决定原版本。',
                    'claim_type': 'SYSTEM_DERIVED_RECOMMENDATION', 'causation': 'NOT_ESTABLISHED',
                    'cost_estimate': None, 'budget_fit': 'UNKNOWN'})
                result.update(state='RESEARCH_ACTIONS_PROPOSED', reason=None)
            report['state'] = ('AVAILABLE' if all(item['state'] == 'AVAILABLE' for item in answers) else 'PARTIAL')
            for item in answers:
                if item['goal'] == 'BUSINESS_RESULT':
                    item['summary'] = '除下列已复核计算明确覆盖的结果外，其他销量、营收、预测或回报结论仍缺少对应业务依据，不能外推。'
        if "resource_constraints" in planning:
            resources = planning["resource_constraints"]
            budget, estimate = resources["budget_amount"], resources["estimated_cost_amount"]
            remainder = self._decimal_remaining(budget, estimate)
            report["resource_assessment"] = {"claim_type": "OPERATOR_CONSTRAINT_AND_ESTIMATE",
                                             "budget_remaining_amount": remainder, "currency": resources["currency"],
                                             "budget_fit": resources["budget_fit"], "actual_spend": None,
                                             "next_action": "估算超预算时调整范围或资源；缺少估算时先确认成本，不触发采购或执行。"}
        method = "source_bound_business_question_analysis/1"
        basis_hash = hashlib.sha256(self._json({"method": method, "previous_basis": result["basis_sha256"],
                                               "business_report": report}).encode()).hexdigest()
        if manual is None:
            options = [{**item, "basis_sha256": basis_hash} for item in options]
        result = {**result, "method": method, "basis_sha256": basis_hash,
                  "options_sha256": hashlib.sha256(self._json(options).encode()).hexdigest(),
                  "business_report": report, "answer_scope": "AUTHORIZED_BUSINESS_OBSERVATIONS_WITH_EXPLICIT_GAPS"}
        conclusion = " ".join(item["summary"] for item in answers)
        # The v1 combined counter is retained as a schema slot but cannot assert
        # comparable cross-platform/subject totals in the new version.
        metrics = {**previous["metric_snapshot"], "total_engagement_complete_sources": None,
                   "interpretation": "SEE_AUTHORIZED_PLATFORM_AND_SOURCE_SCOPE_COHORTS"}
        return self._seal_analysis({**previous, "version": self.CURRENT_ANALYSIS_VERSION,
                                   "state": "ANALYZED_WITH_LIMITATIONS" if options else "NOT_READY",
                                   "metric_snapshot": metrics, "question_result": result,
                                   "judgment": {**previous["judgment"], "conclusion": conclusion},
                                   "limitations": limits}), options

    @staticmethod
    def _decimal_remaining(budget, estimate):
        from decimal import Decimal, localcontext
        if budget is None or estimate is None:
            return None
        with localcontext() as context:
            context.prec = max(28, len(budget) + len(estimate) + 2)
            return format(Decimal(budget) - Decimal(estimate), "f")

    @classmethod
    def _analysis_resources(cls, analysis, decision):
        from decimal import Decimal
        resources = (decision or {}).get("resource_constraints")
        assessment = None
        if resources is not None:
            budget, estimate = resources["budget_amount"], resources["estimated_cost_amount"]
            remaining = (format(Decimal(budget) - Decimal(estimate), "f")
                         if budget is not None and estimate is not None else None)
            if analysis["version"] == cls.CURRENT_ANALYSIS_VERSION:
                remaining = cls._decimal_remaining(budget, estimate)
            assessment = {"claim_type": "OPERATOR_CONSTRAINT_AND_ESTIMATE",
                          "budget_amount": budget, "estimated_cost_amount": estimate,
                          "budget_remaining_amount": remaining, "currency": resources["currency"],
                          "as_of": resources["as_of"], "budget_fit": resources["budget_fit"],
                          "actual_spend": None}
        return cls._seal_analysis({**analysis, "resource_assessment": assessment})

    @staticmethod
    def _analysis_unavailable_reason(exc, fallback):
        import re
        code = getattr(exc, "code", str(exc))
        # Existing owners use stable codes; never expose exception details or
        # source text when a library returns an arbitrary diagnostic string.
        return code if isinstance(code, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{0,127}", code) else fallback

    def _analysis_source_windows(self, connection, report, actor_ref, scope, question):
        """Read one explicitly selected Canonical source through the existing SourceUse owner."""
        from lumenis.shared.reporting.business_brief import (
            _current_actor,
            _source_use_material,
        )
        from lumenis.shared.reporting.operational_brief import build_scoped_source_brief

        actor = _current_actor(actor_ref, self._source_actor or self._action_actor)
        source_ids = [item["source_id"] for item in report["source_brief"]["records"]]
        verified = []
        for source_id in source_ids:
            try:
                row = self._canonical_source(connection, source_id, scope)
                source_scope = {
                    "domain_id": row["domain_id"],
                    "subject_id": row.get("subject_id") or None,
                    "brand_focus_id": row.get("brand_focus_id") or None,
                    "global_scope": not (row.get("subject_id") or row.get("brand_focus_id")),
                }
                entity_label = (
                    (row.get("subject_id") or row.get("brand_focus_id") or scope["entity_label"])
                    if scope["global"] else scope["entity_label"]
                )
                brief = build_scoped_source_brief(
                    connection,
                    product_id=scope["product_id"],
                    global_scope=source_scope["global_scope"],
                    entity_label=entity_label,
                    subject_id=source_scope["subject_id"],
                    brand_focus_id=source_scope["brand_focus_id"],
                    source_ids=[source_id],
                    limit=1,
                    include_analysis_text=True,
                    analysis_question=question,
                    actor_ref=actor_ref,
                )
            except (ValueError, PermissionError) as exc:
                verified.append(({"source_id": source_id}, {
                    "unavailable_reason": self._analysis_unavailable_reason(exc, "SOURCE_READ_UNAVAILABLE")
                }))
                continue
            windows = {item["source_id"]: item for item in brief.get("_analysis_sources", [])}
            source = windows.get(source_id)
            if source is None:
                verified.append(({"source_id": source_id}, {"unavailable_reason": "SOURCE_BODY_UNAVAILABLE"}))
                continue
            try:
                binding = _source_use_material(
                    {"scope": self._action_scope(scope), "sources": [source]},
                    actor,
                    connection=connection,
                )[0]
            except (ValueError, PermissionError) as exc:
                row = self._canonical_source(connection, source_id, scope)
                binding = {"unavailable_reason": self._analysis_unavailable_reason(exc, "SOURCE_USE_UNAVAILABLE")}
            verified.append((source, binding))
        return verified

    def _outcome_material(self, connection, report, actor_ref, scope, source_id, quote):
        """Use the same SourceUse owner before recording source expression."""
        import hashlib
        selected = {**report, "source_brief": {**report["source_brief"], "records": [
            item for item in report["source_brief"]["records"] if item["source_id"] == source_id]}}
        if len(selected["source_brief"]["records"]) != 1:
            raise PermissionError("BUSINESS_WORK_OUTCOME_SOURCE_INVALID")
        windows = self._analysis_source_windows(connection, selected, actor_ref, scope, quote)
        if len(windows) != 1 or "unavailable_reason" in windows[0][1]:
            raise PermissionError("BUSINESS_WORK_OUTCOME_SOURCE_USE_UNAVAILABLE")
        body = self._canonical_source(connection, source_id, scope)["content"] or ""
        if hashlib.sha256(body.encode()).hexdigest() != windows[0][0]["body_sha256"]:
            raise RuntimeError("BUSINESS_WORK_OUTCOME_SOURCE_CHANGED")
        return body

    def _analyze_domain_sources(self, connection, report, actor_ref, scope, kind, question):
        """Bounded deterministic business calculations over permitted source inputs.

        Dates are source-reported mentions, not confirmed events. Interaction
        fields and source windows cannot establish demand, ROI or causation.
        No source expression is copied into the derived result or saved payload.
        """
        import hashlib
        import re
        from datetime import date
        source_report = {"job_id": report["snapshot"]["job_id"], "artifact_hash": report["row"]["artifact_hash"]}
        source_checks = []
        try:
            windows = self._analysis_source_windows(connection, report, actor_ref, scope, question)
        except (ValueError, PermissionError) as exc:
            # Metadata work remains possible; denied source body use is never
            # replaced by a raw Canonical read or a model/provider fallback.
            windows = []
            reason = self._analysis_unavailable_reason(exc, "BUSINESS_WORK_ANALYSIS_SOURCE_USE_UNAVAILABLE")
            source_checks = [{"source_id": item["source_id"], "state": "UNAVAILABLE", "reason": reason}
                             for item in report["source_brief"]["records"]]
        for source, binding in windows:
            if "unavailable_reason" in binding:
                source_checks.append({"source_id": source["source_id"], "state": "UNAVAILABLE",
                                      "reason": binding["unavailable_reason"]})
                continue
            selection = source["text_selection"]
            dates = []
            for match in re.finditer(r"(?<!\d)(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})(?:日)?(?!\d)", source["text"]):
                try:
                    value = date(*(int(part) for part in match.groups())).isoformat()
                except ValueError:
                    continue
                dates.append({"date": value, "start": selection["start"] + match.start(),
                              "end": selection["start"] + match.end()})
            source_checks.append({"source_id": source["source_id"], "state": "SOURCE_USE_VERIFIED",
                                  "binding": binding, "body_sha256": source["body_sha256"],
                                  "selected_text_sha256": hashlib.sha256(source["text"].encode()).hexdigest(),
                                  "selection": selection, "source_reported_dates": dates,
                                  "date_interpretation": "SOURCE_REPORTED_MENTION_NOT_CONFIRMED_EVENT",
                                  "window_truncated": source["truncated"]})
        source_checks.sort(key=lambda item: item["source_id"])
        analyzed_ids = {item["source_id"] for item in source_checks if item["state"] == "SOURCE_USE_VERIFIED"}
        analyzed_report = {**report, "source_brief": {**report["source_brief"], "records": [
            item for item in report["source_brief"]["records"] if item["source_id"] in analyzed_ids]}}
        from canonical_metrics import engagement_of
        complete_values = []
        for item in analyzed_report["source_brief"]["records"]:
            record = self._canonical_source(connection, item["source_id"], scope)
            components = {key: record.get("engagement_" + key) for key in ("likes", "comments", "collects", "shares")}
            if all(type(value) is int and value >= 0 for value in components.values()):
                complete_values.append(engagement_of(components))
        metrics = {"source_count": len(analyzed_ids),
                   "unavailable_source_count": len(source_checks) - len(analyzed_ids),
                   "complete_engagement_source_count": len(complete_values),
                   "total_engagement_complete_sources": sum(complete_values) if complete_values else None,
                   "incomplete_engagement_source_count": len(analyzed_ids) - len(complete_values),
                   "interpretation": "COMPLETE_SOURCE_INTERACTION_INPUTS_ONLY_NOT_DEMAND_OR_ROI"}
        material_review = self._material_review(connection, analyzed_report, scope, kind)
        from lumenis.shared.reporting.operational_brief import _source_url
        for item in material_review["sources"]:
            item["url"] = _source_url(item.get("url"))[0]
        verified_checks = [item for item in source_checks if item["state"] == "SOURCE_USE_VERIFIED"]
        verified_count = len(verified_checks)
        dated_sources = sum(bool(item["source_reported_dates"]) for item in verified_checks) if verified_checks else None
        date_confirmation = ("NOT_ANALYZED" if not verified_checks else
                             "REVIEW_REQUIRED" if dated_sources else "NOT_FOUND_IN_ANALYZED_WINDOWS")
        judgments = {
            "venue_operations": "以获准运营材料形成内部导览核对底稿；来源中出现的日期须逐项确认适用对象与有效期，不能直接列为已确认活动。",
            "consumer_risk": "把获准来源作为反馈核验材料；没有消费者样本、事件核验与分母时，不能从内容数量或互动判断真实风险发生率。",
            "brand_market": "以获准品牌材料整理可追溯的内部研究；品牌自述与发售记录不能直接支持市场份额、竞品优劣或销售预测。",
            "creator_campaign": "以获准材料核对传播语境和制作约束；没有可比创作者、受众与结果数据时，不把互动当成投放回报。",
        }
        return self._seal_analysis({
            "version": self.DOMAIN_ANALYSIS_VERSION, "state": "ANALYZED_WITH_LIMITATIONS",
            "method": "verified_source_windows_calendar_and_decimal_constraints/1",
            "question": question, "kind": kind, "scope": dict(scope), "source_report": source_report,
            "source_checks": source_checks, "metric_snapshot": metrics,
            "material_review": material_review,
            "judgment": {"claim_type": "DERIVED_INTERNAL_RESEARCH", "conclusion": judgments[kind],
                         "verified_body_source_count": verified_count, "sources_with_reported_dates": dated_sources,
                         "date_confirmation": date_confirmation,
                         "consumer_conclusion": "NOT_ESTABLISHED", "causation": "NOT_ESTABLISHED",
                         "business_outcome": "NOT_OBSERVED"},
            "resource_assessment": None,
            "limitations": ["词项窗口不证明语义相关或完整正文覆盖。", "日期提及不证明活动有效、已执行或有业务效果。",
                            "来源和互动样本不代表市场、消费者总体、转化或因果；缺失值保持未知。"],
        })

    def _verify_domain_analysis(self, connection, analysis, report, actor_ref, scope):
        self._check_analysis_digest(analysis)
        if (analysis["source_report"] != {"job_id": report["snapshot"]["job_id"], "artifact_hash": report["row"]["artifact_hash"]}
                or not _same_business_scope(analysis["scope"], scope)):
            raise RuntimeError("BUSINESS_WORK_ANALYSIS_BINDING_INVALID")
        checks = analysis["source_checks"]
        if analysis["version"] == self.CURRENT_ANALYSIS_VERSION:
            snapshot = analysis["question_result"]["business_report"]["canonical_inputs"]
            verified_ids = {item["source_id"] for item in checks if item["state"] == "SOURCE_USE_VERIFIED"}
            if (not isinstance(snapshot, list) or len(snapshot) != len(verified_ids)
                    or {item["source_id"] for item in snapshot} != verified_ids):
                raise RuntimeError("BUSINESS_WORK_ANALYSIS_SNAPSHOT_INVALID")
            for item in snapshot:
                current = self._canonical_source(connection, item["source_id"], scope)
                if any(current.get(key) != item.get(key) for key in
                       ("canonical_id", "source_id", "subject_id", "brand_focus_id")):
                    raise RuntimeError("BUSINESS_WORK_ANALYSIS_SOURCE_CHANGED")
        report_ids = {item["source_id"] for item in report["source_brief"]["records"]}
        selected_ids = (set(analysis["question_result"]["selected_source_ids"])
                        if analysis["version"] in {self.QUESTION_ANALYSIS_VERSION, self.CURRENT_ANALYSIS_VERSION} else report_ids)
        if (not selected_ids <= report_ids
                or {item["source_id"] for item in checks} != selected_ids):
            raise RuntimeError("BUSINESS_WORK_ANALYSIS_BINDING_INVALID")
        if any(item["state"] == "SOURCE_USE_VERIFIED" for item in checks):
            selected_report = {**report, "source_brief": {**report["source_brief"], "records": [
                item for item in report["source_brief"]["records"] if item["source_id"] in selected_ids]}}
            fresh = self._analysis_source_windows(connection, selected_report, actor_ref, scope, analysis["question"])
            current = {source["source_id"]: (source, binding) for source, binding in fresh}
            import hashlib
            for item in checks:
                if item["state"] != "SOURCE_USE_VERIFIED":
                    continue
                source, binding = current[item["source_id"]]
                if "unavailable_reason" in binding:
                    raise PermissionError("BUSINESS_WORK_ANALYSIS_SOURCE_USE_UNAVAILABLE:" + binding["unavailable_reason"])
                if (binding != item["binding"] or source["body_sha256"] != item["body_sha256"]
                        or source["text_selection"] != item["selection"]
                        or hashlib.sha256(source["text"].encode()).hexdigest() != item["selected_text_sha256"]):
                    raise RuntimeError("BUSINESS_WORK_ANALYSIS_SOURCE_CHANGED")
        quantities = analysis.get('question_result', {}).get('business_report', {}).get('quantitative_results')
        if quantities is not None:
            references = analysis['question_result']['planning_constraints'].get('analysis_artifacts', [])
            if not isinstance(quantities, list) or not references:
                raise RuntimeError('BUSINESS_WORK_NUMERICAL_RESULT_CHANGED')
            self._quantitative_artifacts(connection, analysis, references, accepted=quantities)
        reviews = analysis.get("question_result", {}).get("business_report", {}).get("document_reviews")
        if reviews is not None:
            # Revalidate original bytes and rights, never rerun a new algorithm
            # over an already signed analysis or silently replace its result.
            materials = {item["source_id"]: item for item in self._report_quantity_materials(connection, analysis)}
            if (not isinstance(reviews, list) or len(reviews) != len(materials)
                    or {item.get("source_id") for item in reviews} != set(materials)):
                raise RuntimeError("BUSINESS_WORK_REPORT_NUMBERS_BINDING_INVALID")
            for review in reviews:
                current = materials[review["source_id"]]
                if (review.get("method") != "deterministic_explicit_report_groups/1"
                        or review.get("binding") != current["binding"]
                        or review.get("evidence_ref") != current["binding"]["evidence_ref"]
                        or review.get("body_sha256") != current["binding"]["content_hash"]
                        or review.get("coverage", {}).get("scanned_characters") != len(current["content"])):
                    raise RuntimeError("BUSINESS_WORK_REPORT_NUMBERS_BINDING_INVALID")
                def verify_references(value, material=current):
                    if isinstance(value, dict):
                        if {"start", "end", "statement", "body_sha256", "evidence_ref"} <= set(value):
                            start, end = value["start"], value["end"]
                            if (type(start) is not int or type(end) is not int
                                    or not 0 <= start < end <= len(material["content"])
                                    or value["statement"] != material["content"][start:end]
                                    or value.get("source_id") != material["source_id"]
                                    or value["evidence_ref"] != material["binding"]["evidence_ref"]
                                    or value["body_sha256"] != material["binding"]["content_hash"]):
                                raise RuntimeError("BUSINESS_WORK_REPORT_NUMBERS_BINDING_INVALID")
                        for nested in value.values():
                            verify_references(nested)
                    elif isinstance(value, list):
                        for nested in value:
                            verify_references(nested)
                verify_references(review)
            workbench = analysis.get('question_result', {}).get('business_report', {}).get('domain_workbench')
            if workbench is not None:
                if workbench.get('method') != 'source_bound_domain_workbench/1':
                    raise RuntimeError('BUSINESS_WORK_DOMAIN_WORKBENCH_INVALID')
                for lane in workbench['review_lanes']:
                    for claim in lane['claims']:
                        reference = claim['reference']
                        material = materials.get(claim['source_id'])
                        if material is None:
                            raise RuntimeError('BUSINESS_WORK_DOMAIN_WORKBENCH_INVALID')
                        start, end = reference['start'], reference['end']
                        if (type(start) is not int or type(end) is not int
                                or not 0 <= start < end <= len(material['content'])
                                or reference['statement'] != material['content'][start:end]
                                or reference['source_id'] != material['source_id']
                                or reference['body_sha256'] != material['binding']['content_hash']
                                or reference['evidence_ref'] != material['binding']['evidence_ref']):
                            raise RuntimeError('BUSINESS_WORK_DOMAIN_WORKBENCH_INVALID')

    def _analysis_input_status(self, connection, analysis, scope):
        """Report mutable Canonical changes without rewriting a saved analysis snapshot."""
        if analysis["version"] != self.CURRENT_ANALYSIS_VERSION:
            return None
        fields = ("canonical_id", "source_id", "source_platform", "subject_id", "brand_focus_id",
                  "publish_datetime", "captured_at", "sentiment", "risk_level",
                  "engagement_likes", "engagement_comments", "engagement_collects", "engagement_shares")
        snapshot = analysis["question_result"]["business_report"]["canonical_inputs"]
        affected = []
        for item in snapshot:
            if not isinstance(item, dict) or set(item) != set(fields):
                raise RuntimeError("BUSINESS_WORK_ANALYSIS_SNAPSHOT_INVALID")
            current = self._canonical_source(connection, item["source_id"], scope)
            if any(current.get(key) != item[key] for key in fields):
                affected.append(item["source_id"])
        if not affected:
            return None
        return {"state": "CURRENT_INPUTS_CHANGED", "affected_source_ids": sorted(affected),
                "snapshot_immutable": True, "adoption_required": True}

    def _material_review(self, connection, report, scope, kind):
        """Task-specific gaps from signed provenance, never inferred source roles.

        A source's declared role is a capture annotation, not a truth/rights
        verdict. Even complete role coverage requires material review; one
        official identity page cannot establish consumer demand or ROI.
        """
        requirements = {
            "venue_operations": [("VENUE_OPERATOR_DISCLOSURE", "核对主体级品牌/业态、经营口径与统计窗口"),
                                 ("CONSUMER_FEEDBACK", "核对获准消费者样本、体验主题与偏差")],
            "consumer_risk": [("CONSUMER_FEEDBACK", "核对反馈原文、时间与样本偏差"),
                              ("VENUE_OPERATOR_DISCLOSURE", "向运营披露核验风险范围与处置事实")],
            "brand_market": [("OFFICIAL_BRAND_SELF_DESCRIPTION", "核对品牌身份与自述范围"),
                             ("MARKET_DISCLOSURE", "补充同口径市场/竞品材料与比较期")],
            "creator_campaign": [("OFFICIAL_BRAND_SELF_DESCRIPTION", "核对品牌任务与表达边界"),
                                 ("CREATOR_CONTENT", "核对获准创作者内容与传播语境"),
                                 ("CONSUMER_FEEDBACK", "核对受众样本与真实反馈")],
        }[kind]
        sources = []
        for source in report["source_brief"]["records"]:
            record = self._canonical_source(connection, source["source_id"], scope)
            ref = str(source["scope_evidence_ref"])
            # Canonical scope validation already verified this signed record.
            evidence_id = ref.split(":")[-1]
            evidence = connection.execute(
                "SELECT inputs_json FROM app_evidence_records WHERE id=?", (evidence_id,),
            ).fetchone()
            annotations = json.loads(evidence["inputs_json"]) if evidence else {}
            role = annotations.get("source_role")
            allowed_roles = {"OFFICIAL_BRAND_SELF_DESCRIPTION", "VENUE_OPERATOR_DISCLOSURE",
                             "CONSUMER_FEEDBACK", "MARKET_DISCLOSURE", "CREATOR_CONTENT"}
            role = role if isinstance(role, str) and role in allowed_roles else "UNKNOWN"
            from lumenis.shared.reporting.operational_brief import project_profile_research
            research = project_profile_research(connection, record, evidence_id, actor_ref=report["snapshot"]["actor_id"])
            if research is not None:
                role = "ENTITY_PROFILE_RESEARCH_COMPILATION"
            fields = {key: record.get("engagement_" + key) if type(record.get("engagement_" + key)) is int and record["engagement_" + key] >= 0 else None
                      for key in ("likes", "comments", "collects", "shares")}
            # Use the sole metric owner only when every component was measured.
            from canonical_metrics import engagement_of
            complete = all(value is not None for value in fields.values())
            sources.append({"source_id": source["source_id"], "scope_evidence_ref": ref,
                            "url": record.get("url"), "declared_role": role,
                            "role_status": "CAPTURE_ANNOTATION_ONLY",
                            "profile_research": research,
                            "captured_at": record.get("captured_at"),
                            "published_at": record.get("publish_datetime") or None,
                            "commercial_reuse": annotations.get("commercial_reuse", "UNKNOWN"),
                            "engagement": {"components": fields,
                                           "value": engagement_of(fields) if complete else None,
                                           "state": "COMPLETE_INPUT" if complete else "MISSING_INPUT",
                                           "interpretation": "SOURCE_INTERACTIONS_ONLY_NOT_DEMAND_OR_ROI"}})
        roles = {item["declared_role"] for item in sources}
        checks = [{"required_role": role, "check": check,
                   "state": "REVIEW_REQUIRED" if role in roles else "MISSING_MATERIAL",
                   "source_ids": [s["source_id"] for s in sources if s["declared_role"] == role]}
                  for role, check in requirements]
        if any(item.get("profile_research") for item in sources):
            checks.append({"required_role": "ENTITY_PROFILE_RESEARCH_COMPILATION",
                           "check": "已有身份/地址/官网等来源断言可逐字段核对，仍未独立验真或自动采纳",
                           "state": "AVAILABLE_FOR_REVIEW",
                           "source_ids": [item["source_id"] for item in sources if item.get("profile_research")]})
        return {"state": "INSUFFICIENT_MATERIAL" if any(c["state"] == "MISSING_MATERIAL" for c in checks)
                else "MATERIAL_REVIEW_REQUIRED", "checks": checks, "sources": sources,
                "consumer_conclusion": "NOT_ESTABLISHED", "causation": "NOT_ESTABLISHED",
                "commercial_readiness": "NOT_VERIFIED", "collection_triggered": False}

    def _verify_outcome(self, connection, outputs, actor_ref, scope):
        """Recheck source bytes before a derivative write as well as on reopen."""
        import hashlib
        for outcome in self._result_claims(outputs):
            body = self._canonical_source(connection, outcome["source_id"], scope)["content"] or ""
            if (hashlib.sha256(body.encode()).hexdigest() != outcome["body_sha256"]
                    or outcome["quote"] not in body):
                raise RuntimeError("BUSINESS_WORK_OUTCOME_SOURCE_CHANGED")
            report = self._report(connection, outcome["source_job_id"], actor_ref, scope)
            if report["row"]["artifact_hash"] != outcome["report_hash"]:
                raise RuntimeError("BUSINESS_WORK_OUTCOME_SOURCE_CHANGED")

    @staticmethod
    def _result_claims(outputs):
        claims = [outputs["outcome"]] if outputs.get("outcome") else []
        claims += [item["source_claim"] for item in outputs.get("execution_records", [])]
        observation = outputs.get("observation")
        if observation:
            claims.append(observation["source_claim"])
            claims += [item["source_claim"] for item in observation["cost_ledger"]]
            claims += [item["source_claim"] for item in observation["metrics"] if item.get("source_claim")]
            claims += [item["source_claim"] for item in observation.get("metric_observations", [])]
            baseline = observation.get("comparison", {}).get("baseline_source_claim")
            if baseline:
                claims.append(baseline)
            claims += [item["baseline_source_claim"] for item in observation.get("comparison", {}).get("items", [])
                       if item.get("baseline_source_claim")]
        unique = {}
        for claim in claims:
            unique[(claim["source_job_id"], claim["source_id"], claim["body_sha256"])] = claim
        return list(unique.values())

    def _result_sources(self, connection, work, actor_ref, scope):
        required = {source for option in work["options"] for source in option["source_ids"]}
        claims = self._result_claims(work)
        required.update(claim["source_id"] for claim in claims)
        jobs = {work["source_report"]["job_id"]}
        jobs.update(claim["source_job_id"] for claim in claims)
        records = []
        for job_id in sorted(jobs):
            report = self._report(connection, job_id, actor_ref, scope)
            records += [{**source, "source_job_id": job_id} for source in report["source_brief"]["records"]]
        return required, records

    def _citation_candidates(self, connection, work, actor_ref, scope):
        """Offer grounded quotes for explicit selection; this grants no export."""
        import hashlib

        from lumenis.shared.reporting import saved_work
        from lumenis.shared.reporting.operational_brief import _content_evidence_ref
        from lumenis.system.security import permission
        actor = self._source_actor or permission.resolve_local_workspace_principal(module="reports", action="read") or self._action_actor
        if actor is None:
            raise PermissionError("BUSINESS_WORK_SOURCE_ACTOR_REQUIRED")
        context = saved_work.authorize(actor, self._action_scope(scope), action="read", connection=connection)
        required, records = self._result_sources(connection, work, actor_ref, scope)
        candidates, covered = [], set()
        for source in records:
            if source["source_id"] not in required or source["source_id"] in covered:
                continue
            canonical = self._canonical_source(connection, source["source_id"], scope)
            ref = _content_evidence_ref(connection, canonical, str(source["scope_evidence_ref"]))
            if ref is None:
                raise PermissionError("SOURCE_BRIEF_SOURCE_USE_UNAVAILABLE")
            evidence_id = int(ref.split(":")[-1])
            original = saved_work._verified_evidence(connection, evidence_id, context, actor)
            body = original["raw_content"]
            if (original["asset_id"] != source["source_id"] or body != canonical.get("content")
                    or hashlib.sha256(body.encode()).hexdigest() != original["content_hash"]):
                raise PermissionError("SOURCE_BRIEF_ORIGINAL_SOURCE_CHANGED")
            quote = next((claim["quote"] for claim in self._result_claims(work)
                          if claim["source_id"] == source["source_id"]), body[:1200])
            if not quote or quote not in body:
                raise ValueError("BUSINESS_WORK_SAVE_CITATION_UNAVAILABLE")
            start = body.index(quote)
            citation = {"evidence_id": evidence_id, "start": start, "end": start + len(quote), "quote": quote,
                        "source_scope": {key: original["provenance"]["context"][key]
                                         for key in ("domain_id", "subject_id", "brand_focus_id", "global_scope")}}
            candidates.append({"source_id": source["source_id"], "source_job_id": source["source_job_id"],
                               "title": source.get("title") or source["source_id"], "citation": citation,
                               "body_sha256": original["content_hash"], "source_version": original["version"],
                               "claim_type": "SOURCE_STATEMENT", "fact_verified": False})
            covered.add(source["source_id"])
        if covered != required:
            raise ValueError("BUSINESS_WORK_SAVE_SOURCE_CITATION_MISSING")
        return {"state": "AVAILABLE_FOR_EXPLICIT_SELECTION", "items": candidates,
                "required_source_ids": sorted(required), "source_count": len(required),
                "selection_required": True, "export_authorization": "NOT_GRANTED",
                "save_limit_state": "WITHIN_SHARED_CITATION_LIMIT" if len(required) <= 100 else "SHARED_CITATION_LIMIT_EXCEEDED"}

    def list_recent(self, *, actor_ref, scope, authorize, limit=30):
        """Authenticated index of existing signed work; unavailable entries stay visible."""
        if type(limit) is not int or not 1 <= limit <= 30:
            raise ValueError("BUSINESS_WORK_LIST_LIMIT_INVALID")
        self._authorize(authorize, actor_ref, scope, "read")
        if scope.get("global") is not False or scope.get("product_id") not in {"CTH", "ZBMP"}:
            raise PermissionError("BUSINESS_WORK_EXACT_FOCUS_REQUIRED")
        with get_repository().connection(read_only=True, wal=False) as connection:
            rows = connection.execute(
                "SELECT asset_id, MAX(id) AS last_id FROM app_evidence_records "
                "WHERE feature_id=? AND product_id=? AND domain_id=? "
                "AND json_extract(inputs_json, '$.actor_ref')=? "
                "AND json_extract(inputs_json, '$.scope.subject_id') IS ? "
                "AND json_extract(inputs_json, '$.scope.brand_focus_id') IS ? "
                "AND json_extract(inputs_json, '$.scope.global')=0 "
                "GROUP BY asset_id ORDER BY last_id DESC LIMIT ?",
                (self.FEATURE, scope["product_id"], scope["domain_id"], actor_ref,
                 scope.get("subject_id"), scope.get("brand_focus_id"), limit)).fetchall()
        items = []
        for row in rows:
            try:
                current = self.reopen(row[0], actor_ref=actor_ref, scope=scope, authorize=authorize)
            except (PermissionError, LookupError, ValueError, RuntimeError):
                # No withdrawn content or raw exception detail in the index.
                items.append({"work_id": row[0], "availability": "UNAVAILABLE",
                              "reason": "CURRENT_SOURCE_OR_PERMISSION_UNAVAILABLE"})
                continue
            items.append({key: current[key] for key in ("work_id", "revision", "question", "kind", "state", "action_state", "outcome_state")} |
                         {"availability": "AVAILABLE", "source_report": current["source_report"]})
        self._authorize(authorize, actor_ref, scope, "read")
        return {"items": items, "limit": limit, "state": "PARTIAL" if any(item["availability"] == "UNAVAILABLE" for item in items) else "AVAILABLE"}

    def available_sources(self, *, actor_ref, scope, authorize, limit=30, cursor=None):
        """Page the existing SourceBrief owner, offering real authorized quote choices."""
        from lumenis.shared.reporting import saved_work
        from lumenis.shared.reporting.source_brief_job import list_source_brief_jobs
        from lumenis.system.security import permission
        self._authorize(authorize, actor_ref, scope, "read")
        if scope.get("global") is not False or scope.get("product_id") not in {"CTH", "ZBMP"}:
            raise PermissionError("BUSINESS_WORK_EXACT_FOCUS_REQUIRED")
        actor = self._source_actor or permission.resolve_local_workspace_principal(module="reports", action="read") or self._action_actor
        if actor is None:
            raise PermissionError("BUSINESS_WORK_SOURCE_ACTOR_REQUIRED")
        identity = saved_work.authorize(actor, self._action_scope(scope), action="read")
        if (identity.get("principal_ref") or f"actor:{identity.get('actor_id')}") != actor_ref:
            raise PermissionError("BUSINESS_WORK_SOURCE_ACTOR_MISMATCH")
        page = list_source_brief_jobs(actor=actor, scope=self._action_scope(scope), limit=limit, cursor=cursor)
        items = []
        with get_repository().connection(read_only=True, wal=False) as connection:
            for item in page["items"]:
                try:
                    report = self._report(connection, item["job_id"], actor_ref, scope)
                    projection = {"source_report": {"job_id": item["job_id"]},
                                  "options": [{"source_ids": [source["source_id"] for source in report["source_brief"]["records"]]}]}
                    candidates = self._citation_candidates(connection, projection, actor_ref, scope)
                except (ValueError, LookupError, PermissionError, RuntimeError):
                    items.append({"job_id": item["job_id"], "availability": "UNAVAILABLE",
                                  "reason": "CURRENT_SOURCE_USE_UNAVAILABLE"})
                    continue
                items.append({"job_id": item["job_id"], "artifact_hash": item["artifact_hash"],
                              "source_count": candidates["source_count"], "availability": "AVAILABLE",
                              "citation_candidates": candidates})
            # Reopen the permitted originals once more after the other reads;
            # page membership is never a cached grant to quote withdrawn bytes.
            for item in items:
                if item["availability"] == "AVAILABLE":
                    self._report(connection, item["job_id"], actor_ref, scope)
        self._authorize(authorize, actor_ref, scope, "read")
        partial = any(item["availability"] == "UNAVAILABLE" for item in items)
        return {**page, "items": items, "state": "PARTIAL" if partial else page["state"],
                "read_complete": page["read_complete"] and not partial}

    def _saved_results(self, connection, work, history, actor_ref, scope):
        """Project only this work's verified Shared versions and exact next-parent identity."""
        import hashlib

        from lumenis.shared.reporting import saved_work
        from lumenis.system.security import permission
        actor = self._source_actor or permission.resolve_local_workspace_principal(module="reports", action="read") or self._action_actor
        if actor is None:
            raise PermissionError("BUSINESS_WORK_SOURCE_ACTOR_REQUIRED")
        owner_scope = self._action_scope(scope)
        context = saved_work.authorize(actor, owner_scope, action="read", connection=connection)
        stable_id = "WORK-" + hashlib.sha256(self._json([actor_ref, history[0]["inputs"]["scope"], work["work_id"]]).encode()).hexdigest()[:24]
        versions = saved_work._versions(connection, stable_id, context, actor)
        items, unavailable = [], 0
        latest = None
        for version in versions:
            try:
                verified = saved_work.read_committed_work(version["artifact"]["artifact_id"], actor=actor,
                                                         scope=owner_scope, connection=connection)
            except (saved_work.SavedWorkError, PermissionError):
                unavailable += 1
                continue
            document, artifact = verified["document"], verified["artifact"]
            business = document["payload"].get("business_work", {})
            if (document["work_id"] != stable_id or business.get("work_id") != work["work_id"]
                    or not _same_business_scope(business.get("scope"), scope)):
                raise RuntimeError("BUSINESS_WORK_SAVED_RESULT_BINDING_INVALID")
            item = {"artifact_id": artifact["artifact_id"], "sha256": artifact["sha256"],
                    "version": document["version"], "title": document["title"],
                    "draft_digest": document["draft_digest"], "business_revision": business["revision"]}
            items.append(item)
            if version["artifact"]["artifact_id"] == versions[-1]["artifact"]["artifact_id"]:
                latest = item
        saved_work.authorize(actor, owner_scope, action="read", connection=connection)
        return {"items": items, "latest": latest, "saved_work_id": stable_id,
                "unavailable_count": unavailable,
                "state": "PARTIAL" if unavailable else "AVAILABLE" if items else "NOT_SAVED",
                "next_parent_state": "UNAVAILABLE" if versions and latest is None else "AVAILABLE" if latest else "FIRST_VERSION"}

    def reopen(self, work_id, *, actor_ref, scope, authorize, revision=None):
        self._authorize(authorize, actor_ref, scope, "read")
        with get_repository().connection(read_only=True, wal=False) as connection:
            connection.execute("BEGIN")
            history = self._history(connection, work_id, actor_ref, scope)
            if not history:
                raise LookupError("BUSINESS_WORK_NOT_FOUND")
            latest_revision = history[-1]["evidence_ref"]
            if revision is not None:
                selected = next((index for index, event in enumerate(history)
                                 if event["evidence_ref"] == revision), None)
                if selected is None:
                    raise RuntimeError("BUSINESS_WORK_REVISION_CONFLICT")
                history = history[:selected + 1]
            original = self._active_origin(history)["inputs"]["payload"]
            current = history[-1]
            self._verify_outcome(connection, current["outputs"], actor_ref, scope)
            report = self._bound_report(connection, history, actor_ref, scope)
            kind = history[0]["inputs"]["payload"]["kind"]
            analysis = current["outputs"].get("domain_analysis")
            analysis_input_status = None
            if analysis is not None:
                self._verify_domain_analysis(connection, analysis, report, actor_ref, scope)
                if analysis != self._analysis_resources(analysis, current["outputs"].get("decision")):
                    raise RuntimeError("BUSINESS_WORK_ANALYSIS_BINDING_INVALID")
                analysis_input_status = self._analysis_input_status(connection, analysis, scope)
            material_review = analysis["material_review"] if analysis is not None else self._material_review(connection, report, scope, kind)
            if current["outputs"].get("outcome"):
                import hashlib
                outcome = current["outputs"]["outcome"]
                outcome_report = self._report(connection, outcome["source_job_id"], actor_ref, scope)
                body = self._outcome_material(connection, outcome_report, actor_ref, scope,
                                              outcome["source_id"], outcome["quote"])
                if (outcome_report["row"]["artifact_hash"] != outcome["report_hash"]
                        or hashlib.sha256(body.encode()).hexdigest() != outcome["body_sha256"]
                        or outcome["quote"] not in body):
                    raise RuntimeError("BUSINESS_WORK_OUTCOME_SOURCE_CHANGED")
            self._verify_outcome(connection, current["outputs"], actor_ref, scope)
        active_history = self._active_history(history)
        action_read = self._verify_actions(active_history, actor_ref, scope, authorize)
        evaluation = {"state": "NOT_EVALUATED", "business_usefulness": "UNKNOWN"}
        if current["outputs"]["state"] == "OUTCOME_RECORDED":
            import hashlib
            from lumenis.shared.evaluation.recorder import get_evaluation_record
            evaluation_id = hashlib.sha256((work_id + current["evidence_ref"]).encode()).hexdigest()
            record = get_evaluation_record(evaluation_id)
            if record is None:
                evaluation["state"] = "PENDING_RECOVERY"
            else:
                metadata = json.loads(record["metadata"])
                if (record["evidence_ref"] != current["evidence_ref"] or record["status"] != "unknown"
                        or record["metric_value"] is not None or metadata.get("work_id") != work_id
                        or metadata.get("actor_ref") != actor_ref or metadata.get("scope") != current["inputs"]["scope"]):
                    raise RuntimeError("BUSINESS_WORK_EVALUATION_BINDING_INVALID")
                if metadata != self._evaluation_metadata(work_id, current, actor_ref, scope):
                    raise RuntimeError("BUSINESS_WORK_EVALUATION_BINDING_INVALID")
                evaluation.update(state="RECORDED", evaluation_id=evaluation_id)
        result = {"version": self._record_version(current["outputs"]),
                "work_id": work_id, "scope": current["inputs"]["scope"],
                "revision": current["evidence_ref"], "latest_revision": latest_revision,
                "is_current_revision": current["evidence_ref"] == latest_revision,
                **current["outputs"], "action_read": action_read,
                "action_service": {"state": "BOUND_READER"} if callable(self._internal_action_reader) and self._action_actor is not None
                                  else {"state": "UNAVAILABLE", "reason": "ACTION_OWNER_NOT_BOUND"},
                "question": original["question"], "kind": kind,
                "source_report": {"job_id": original["source_job_id"], "artifact_hash": report["row"]["artifact_hash"]},
                "source_brief": report["source_brief"], "multimodal": report["snapshot"]["multimodal"],
                "material_review": material_review,
                "owned_analysis": {"state": "UNAVAILABLE", "reason": "OWNED_RUNTIME_NOT_BOUND"},
                "timeline": [{"operation": e["inputs"]["operation"], "evidence_ref": e["evidence_ref"]} for e in history],
                "return_context": {"product_id": scope["product_id"], "global": True,
                                   "subject_id": None, "brand_focus_id": None},
                "evaluation": evaluation}
        if analysis_input_status is not None:
            result["analysis_input_status"] = analysis_input_status
        domain_execution = self._domain_execution_progress(current['outputs'])
        if domain_execution is not None:
            result['domain_execution'] = domain_execution
        result["usable_result"] = self.render_result(result)
        with get_repository().connection(read_only=True, wal=False) as connection:
            result["citation_candidates"] = self._citation_candidates(connection, result, actor_ref, scope)
            result["saved_results"] = self._saved_results(connection, result, history, actor_ref, scope)
            self._verify_outcome(connection, result, actor_ref, scope)
        # Shared read/use permissions may change during rendering independently
        # of this domain's report permission. Reconcile all linked versions again.
        if action_read["state"] == "FRESH_OWNER_VERIFIED":
            self._verify_actions(active_history, actor_ref, scope, authorize)
        self._authorize(authorize, actor_ref, scope, "read")
        return result

    def _saved_result_args(self, connection, work, *, actor_ref, scope, request_id,
                           citations, previous_artifact_id, expected_draft_digest, _staging_artifact_id=None):
        """Project this exact domain revision into the existing Shared writer."""
        import hashlib
        from lumenis.shared.reporting import saved_work
        if self._action_actor is None:
            raise RuntimeError("BUSINESS_WORK_SERVER_ACTOR_NOT_BOUND")
        media_scope = self._action_scope(scope)
        context = saved_work.authorize(self._action_actor, media_scope, action="write", connection=connection)
        identity = context.get("principal_ref") or f"actor:{context.get('actor_id')}"
        if identity != actor_ref:
            raise PermissionError("BUSINESS_WORK_SAVE_ACTOR_MISMATCH")
        if work["state"] not in {"DECIDED", "ACTION_RECORDED", "OUTCOME_RECORDED"}:
            raise RuntimeError("BUSINESS_WORK_SAVE_DECISION_REQUIRED")
        if not isinstance(citations, list) or not 1 <= len(citations) <= 100:
            raise ValueError("BUSINESS_WORK_SAVE_CITATIONS_REQUIRED")
        required_sources, records = self._result_sources(connection, work, actor_ref, scope)
        bindings, covered = [], set()
        for citation in citations:
            if (not isinstance(citation, dict) or type(citation.get("evidence_id")) is not int
                    or citation["evidence_id"] < 1 or not isinstance(citation.get("quote"), str)
                    or not citation["quote"]):
                raise ValueError("BUSINESS_WORK_SAVE_CITATION_INVALID")
            matches = []
            for source in records:
                if (source["source_id"] not in required_sources
                        or str(citation["evidence_id"]) != str(source["evidence_id"])):
                    continue
                row = self._canonical_source(connection, source["source_id"], scope)
                if citation["quote"] not in (row.get("content") or ""):
                    continue
                matches.append(source["source_id"])
                covered.add(source["source_id"])
                binding = {"source_id": source["source_id"], "canonical_id": row["canonical_id"],
                           "evidence_id": citation["evidence_id"],
                           "body_sha256": hashlib.sha256((row.get("content") or "").encode()).hexdigest()}
                if binding not in bindings:
                    bindings.append(binding)
            if not matches:
                raise PermissionError("BUSINESS_WORK_SAVE_CITATION_NOT_IN_TASK")
        if covered != required_sources:
            raise ValueError("BUSINESS_WORK_SAVE_SOURCE_CITATION_MISSING")
        # Shared checks exact offsets, signed original bytes, use rights and
        # Permission. A domain Source/Scope signature alone grants none of them.
        fields = ("version", "work_id", "revision", "scope", "kind", "question", "state", "options", "decision",
                  "source_report", "action_state", "outcome_state", "business_outcome")
        business = {key: work[key] for key in fields}
        if work.get("domain_analysis") is not None:
            business["domain_analysis"] = work["domain_analysis"]
        # Evaluation is a recoverable derivative. Its changing read status is
        # separate from this immutable save intent and its durable replay hash.
        outcome_revision = work["revision"] if work["state"] == "OUTCOME_RECORDED" else None
        business["evaluation"] = {
            "evaluation_id": hashlib.sha256((work["work_id"] + outcome_revision).encode()).hexdigest()
                             if outcome_revision else None,
            "evidence_ref": outcome_revision,
        }
        for key in ("adoption", "action", "execution_records", "observation", "outcome", "outcome_unknown", "case_id", "case_evidence_ref",
                    "operator_review", "recovery", "selected_by"):
            if key in work:
                business[key] = work[key]
        business["source_bindings"] = sorted(bindings, key=lambda item: item["source_id"])
        business["source_selection"] = "EXPLICIT_OPERATOR_QUOTES_CHECKED_BY_SHARED"
        business["model_state"] = work["owned_analysis"]
        history = self._history(connection, work["work_id"], actor_ref, scope)
        identity_scope = history[0]["inputs"]["scope"]
        snapshot_scope = work["scope"]
        selected = next(option for option in work["options"] if option["option_id"] == work["decision"]["option_id"])
        payload = {"business_work": business,
                   "brief": {"goal": work["question"], "kind": work["kind"], "scope": snapshot_scope,
                             "selected_option": selected, "resource_constraints": work["decision"].get("resource_constraints"),
                             "source_report": work["source_report"], "source_bindings": business["source_bindings"]}}
        if work.get("domain_analysis") is not None:
            payload["brief"]["domain_analysis"] = work["domain_analysis"]
        markdown = work["usable_result"]["markdown"] + "\n## 本版本选定引用\n\n"
        from lumenis.shared.reporting.operational_brief import _markdown_text
        for citation in citations:
            markdown += f"Evidence {citation['evidence_id']} · 字符 {citation.get('start')}–{citation.get('end')}\n\n"
            markdown += "\n".join("> " + _markdown_text(line) for line in citation["quote"].splitlines()) + "\n\n"
        # Reuse the business owner's report heading, including its report kind
        # and language. The complete question remains in the body and payload.
        report_title = work["usable_result"]["markdown"].splitlines()[0].removeprefix("# ")
        title = snapshot_scope["entity_label"][:120] + report_title.removeprefix(
            _markdown_text(snapshot_scope["entity_label"]))
        saved_work_id = "WORK-" + hashlib.sha256(self._json(
            [actor_ref, identity_scope, work["work_id"]]).encode()).hexdigest()[:24]
        # A committed request retains its original presentation across renderer
        # updates. Shared still compares every request field and the full hash;
        # finding the same key is not permission to replay changed input.
        for previous in saved_work._versions(connection, saved_work_id, context, self._action_actor):
            if previous["artifact"]["artifact_id"] == _staging_artifact_id:
                # Shared's before_commit callback sees its own uncommitted row;
                # that row cannot establish a prior durable request.
                continue
            if previous["document"]["request_id"] != request_id:
                continue
            committed = saved_work.read_committed_work(previous["artifact"]["artifact_id"],
                actor=self._action_actor, scope=media_scope, connection=connection)["document"]
            previous_business = committed["payload"].get("business_work", {})
            if (committed["work_id"] != saved_work_id or previous_business.get("work_id") != work["work_id"]
                    or not _same_business_scope(previous_business.get("scope"), scope)):
                raise RuntimeError("BUSINESS_WORK_SAVED_RESULT_BINDING_INVALID")
            title = committed["title"]
            break
        return {"title": title,
                "markdown": markdown, "kind": "report", "payload": payload,
                "citations": citations, "request_id": request_id,
                "work_id": saved_work_id,
                "previous_artifact_id": previous_artifact_id, "expected_draft_digest": expected_draft_digest,
                "contract": {"id": "lumenis.cth-bmp-business-result", "version": "1",
                             "required_payload_paths": ["business_work.work_id", "business_work.revision",
                                                        "business_work.source_bindings", "brief.goal", "brief.selected_option"]},
                "actor": self._action_actor, "scope": media_scope}

    def save_result_request(self, work_id, *, actor_ref, scope, authorize, expected_revision,
                            request_id, citations, previous_artifact_id=None, expected_draft_digest=None):
        """Return the exact existing Shared approval resource without writing."""
        from lumenis.shared.reporting import saved_work
        work = self.reopen(work_id, actor_ref=actor_ref, scope=scope, authorize=authorize,
                           revision=expected_revision)
        if work["revision"] != expected_revision:
            raise RuntimeError("BUSINESS_WORK_REVISION_CONFLICT")
        citations = json.loads(self._json(citations))
        with get_repository().connection(read_only=True, wal=False) as connection:
            args = self._saved_result_args(connection, work, actor_ref=actor_ref, scope=scope,
                                          request_id=request_id, citations=citations,
                                          previous_artifact_id=previous_artifact_id,
                                          expected_draft_digest=expected_draft_digest)
        resource = saved_work.work_write_resource(**args)
        self._authorize(authorize, actor_ref, scope, "read")
        return {"resource": resource, "work_id": work_id, "revision": expected_revision,
                "saved_work_id": args["work_id"], "request_id": request_id,
                "state": "AWAITING_SHARED_SAVE_PERMISSION", "publish_status": "not_performed"}

    def save_result(self, work_id, *, actor_ref, scope, authorize, expected_revision,
                    request_id, citations, previous_artifact_id=None, expected_draft_digest=None):
        """Save the selected business result with current citations and a fixed upstream.

        The domain prepares content; Shared owns Permission, staging, Artifact,
        versions, replay, export and independent committed readback. Direct
        Shared versioning also permits replacing revoked old citations without
        opening or copying the withdrawn parent text.
        """
        from lumenis.shared.reporting import saved_work
        # Read the signed requested revision so an already committed request
        # can replay after business progress. New stale writes still fail in
        # before_commit; Shared alone owns the durable idempotency receipt.
        work = self.reopen(work_id, actor_ref=actor_ref, scope=scope, authorize=authorize,
                           revision=expected_revision)
        if work["revision"] != expected_revision:
            raise RuntimeError("BUSINESS_WORK_REVISION_CONFLICT")
        citations = json.loads(self._json(citations))
        with get_repository().connection(read_only=True, wal=False) as connection:
            args = self._saved_result_args(connection, work, actor_ref=actor_ref, scope=scope,
                                          request_id=request_id, citations=citations,
                                          previous_artifact_id=previous_artifact_id,
                                          expected_draft_digest=expected_draft_digest)
        self._authorize(authorize, actor_ref, scope, "read")

        def before_commit(connection, _artifact, document):
            history = self._history(connection, work_id, actor_ref, scope)
            if not history or history[-1]["evidence_ref"] != expected_revision:
                raise RuntimeError("BUSINESS_WORK_REVISION_CONFLICT")
            self._bound_report(connection, history, actor_ref, scope)
            current = self._saved_result_args(connection, work, actor_ref=actor_ref, scope=scope,
                                             request_id=request_id, citations=citations,
                                             previous_artifact_id=previous_artifact_id,
                                             expected_draft_digest=expected_draft_digest,
                                             _staging_artifact_id=_artifact["artifact_id"])
            if document["payload"] != current["payload"] or document["markdown"] != current["markdown"]:
                raise RuntimeError("BUSINESS_WORK_SAVE_INPUT_CHANGED")

        result = saved_work.save_work(**args, before_commit=before_commit)
        self._authorize(authorize, actor_ref, scope, "read")
        current = self.reopen(work_id, actor_ref=actor_ref, scope=scope, authorize=authorize)
        changed = current["revision"] != expected_revision
        return {"work_id": work_id, "revision": expected_revision, "saved_work": result,
                "creation_upstream": {"kind": "saved_work", "artifact_id": result["artifact"]["artifact_id"],
                                      "expected_sha256": result["artifact"]["sha256"],
                                      "expected_version": result["document"]["version"]},
                "current_revision": current["revision"], "current_revision_changed": changed,
                "current_evaluation": {"revision": current["revision"], **current["evaluation"]},
                "state": "SAVED_PREVIOUS_REVISION" if changed else "SAVED_CURRENT_REVISION",
                "publish_status": "not_performed"}

    def focus_lens(self, work_id, *, actor_ref, scope, authorize, related_reports, authorize_related):
        """Read separately authorized reports without rebinding their Evidence.

        W6 supplies fresh server read receipts for each ORIGINAL scope. A
        requested contextual citation is not an accepted entity relationship.
        Shared report exact-scope contracts and stores remain unchanged.
        """
        focus = self.reopen(work_id, actor_ref=actor_ref, scope=scope, authorize=authorize)
        if not isinstance(related_reports, list) or len(related_reports) > 4:
            raise ValueError("BUSINESS_LENS_CONTEXT_LIMIT")
        if related_reports and not callable(authorize_related):
            raise PermissionError("BUSINESS_LENS_CONTEXT_AUTHORIZATION_REQUIRED")
        contexts, seen = [], {focus["source_report"]["job_id"]}
        with get_repository().connection(read_only=True, wal=False) as connection:
            connection.execute("BEGIN")
            for descriptor in related_reports:
                if not isinstance(descriptor, dict) or set(descriptor) != {"job_id", "original_scope", "purpose"}:
                    raise ValueError("BUSINESS_LENS_CONTEXT_DESCRIPTOR_INVALID")
                original = descriptor["original_scope"]
                if not isinstance(original, dict) or original.get("product_id") != scope["product_id"]:
                    raise PermissionError("BUSINESS_LENS_DOMAIN_MISMATCH")
                if original.get("global") is True:
                    raise RuntimeError("BUSINESS_LENS_GLOBAL_REPORT_SOURCE_SCOPE_OWNER_REQUIRED")
                job_id = self._text(descriptor["job_id"], 256)
                purpose = self._text(descriptor["purpose"])
                if job_id in seen:
                    raise ValueError("BUSINESS_LENS_DUPLICATE_REPORT")
                seen.add(job_id)
                receipt = lambda operation: authorize_related(original, operation)
                self._authorize(receipt, actor_ref, original, "read")
                report = self._report(connection, job_id, actor_ref, original, require_content=False)
                contexts.append({"job_id": job_id, "artifact_hash": report["row"]["artifact_hash"],
                                 "original_scope": original, "task_focus_scope": scope, "purpose": purpose,
                                 "relationship_state": "OPERATOR_CONTEXT_REQUEST_NOT_VERIFIED_RELATION",
                                 "source_brief": report["source_brief"],
                                 "multimodal": {"state": "unavailable", "reason": "SOURCE_USE_REQUIRED"},
                                 "interpretation": "BACKGROUND_ONLY_NOT_FOCUS_FACT_OR_CAUSATION"})
                # Revocation during the read must prevent returning material.
                self._authorize(receipt, actor_ref, original, "read")
        # A later related read may revoke an earlier scope. Recheck every
        # original scope at the response boundary before returning any material.
        for context in contexts:
            original = context["original_scope"]
            receipt = lambda operation, original=original: authorize_related(original, operation)
            self._authorize(receipt, actor_ref, original, "read")
        self._authorize(authorize, actor_ref, scope, "read")
        return {"state": "SCOPED_REFERENCES_PREPARED", "task_focus_scope": scope,
                "focus_work": focus, "related_context": contexts,
                "analysis": {"state": "UNAVAILABLE", "reason": "W2_OWNED_GATEWAY_NOT_BOUND"},
                "grounded_analysis_input": {"question": focus["question"], "task_focus_scope": scope,
                    "focus_report": focus["source_report"],
                    "related_reports": [{k: c[k] for k in ("job_id", "artifact_hash", "original_scope", "purpose")}
                                        for c in contexts],
                    "full_source_read": "REQUIRES_ORIGINAL_SCOPE_SOURCE_PERMISSION_AND_CANONICAL_OWNER",
                    "cross_scope_metric_comparability": "NOT_ESTABLISHED"},
                "truth_rewritten": False, "collection_triggered": False,
                "return_context": focus["return_context"]}

    @staticmethod
    def render_result(work):
        """Business-owned decision content; Shared still owns save/export assets."""
        import hashlib
        import re

        from lumenis.shared.reporting.operational_brief import (
            _markdown_text,
            _source_url,
        )
        text = _markdown_text
        labels = {
            "RESEARCH_ACTIONS_PROPOSED": "已形成待确认的研究建议",
            "OPERATOR_PROPOSALS_ONLY": "仅保留用户提出的方案，完整判断尚未完成",
            "NOT_READY": "必要材料或研究问题仍需补充", "NOT_ESTABLISHED": "尚未形成完整业务结论",
            "INSUFFICIENT_MATERIAL": "必要业务材料仍不齐全",
            "MATERIAL_REVIEW_REQUIRED": "材料用途已覆盖，仍需核对原文",
            "MISSING_MATERIAL": "缺少对应业务材料", "REVIEW_REQUIRED": "已有材料，仍需核验",
            "AVAILABLE_FOR_REVIEW": "可供核对，尚未独立核实",
            "NATIVE_PUBLICATION_TIMEZONE_UNKNOWN": "原生发布时间缺少时区",
            "OUTSIDE_PUBLICATION_PERIOD": "不在所选发布期间内",
            "NATIVE_PUBLICATION_TIME_UNKNOWN": "原生发布时间未知或无法识别",
            "WITHIN_OPERATOR_ESTIMATE": "按用户估计未超预算", "OVER_BUDGET": "用户估计已超预算",
            "UNKNOWN": "未知", "NOT_VERIFIED": "尚未核实", "NOT_GRANTED": "未获授权",
            "ESTIMATE": "估计费用", "COMMITTED": "已承诺费用", "ACTUAL": "实际支出", "REFUND": "退款",
            'OVER_DECLARED_ESTIMATE': '所报净实支超过该行动的声明估计',
            'WITHIN_DECLARED_ESTIMATE': '所报同币种净实支未超过该行动的声明估计',
            "OVER_OPERATOR_BUDGET": "所报净实支已超出用户预算",
            "WITHIN_OPERATOR_BUDGET": "所报同币种净实支未超出用户预算",
            "PARTIAL_CURRENCY_CONVERSION_REQUIRED": "仅完成同币种核对，其他币种尚未换算",
            "BASELINE_METRIC_MISSING": "前次观察没有同名指标",
            "METRIC_DEFINITION_CHANGED": "指标定义已变化", "UNIT_CHANGED": "指标单位已变化",
            "WINDOW_DURATION_CHANGED": "观察窗口时长不同", "VALUE_UNKNOWN": "本次或前次数值未知",
            "ZERO_BASELINE_RELATIVE_CHANGE_UNKNOWN": "前次数值为零，相对变化未知",
            "REPORTED_VALUE_DIFFERENCE": "仅为所报同口径数值的描述差值",
            "INPUTS_NOT_COMPARABLE": "输入口径不同，不能比较",
            "useful": "用户认为有用", "not_useful": "用户认为无用", "inconclusive": "用户尚无法判断",
            "retain": "保留当前方案", "revise": "修订方案", "stop": "停止后续工作",
            "likes": "点赞", "comments": "评论", "collects": "收藏", "shares": "分享",
            "post": "篇帖子", "posts": "篇帖子", "comment": "条评论",
        }

        def label(value):
            return labels.get(value, value)

        def business_text(value):
            # Apply only to generated analysis/proposal prose, never to quoted
            # source statements, operator questions, reasons or source identities.
            value = str(value)
            for role in ("VENUE_OPERATOR_DISCLOSURE", "CONSUMER_FEEDBACK",
                         "OFFICIAL_BRAND_SELF_DESCRIPTION", "MARKET_DISCLOSURE", "CREATOR_CONTENT",
                         "ENTITY_PROFILE_RESEARCH_COMPILATION"):
                value = value.replace(role, BusinessDecisionWorkflow._business_role_name(role))
            for code, display in {"public_document": "来源文档", "approved_research_document": "获准研究材料",
                                  "likes": "点赞", "comments": "评论", "collects": "收藏", "shares": "分享"}.items():
                value = re.sub(r"(?<![A-Za-z0-9_])" + code + r"(?![A-Za-z0-9_])", display, value)
            return text(value.replace("风险high=", "高风险标签=").replace("、critical=", "、严重风险标签="))

        generated_options = bool((work.get("domain_analysis") or {}).get("question_result", {}).get("generation")
                                 in {"SYSTEM_DERIVED_RECOMMENDATIONS", BusinessDecisionWorkflow.REVISED_RESEARCH_GENERATION})

        def option_text(option, field):
            value = option[field]
            if isinstance(value, list):
                value = "；".join(value)
            authored = bool(option.get("operator_revision")) and field in {"proposal", "rationale", "check"}
            return (business_text if generated_options and not authored else text)(value)

        def option_title(option_id):
            return next((option_text(option, "proposal") for option in work["options"]
                         if option["option_id"] == option_id), "历史方案（标题未保留）")
        lines = ["# " + text(work["scope"]["entity_label"]) + " · 工作决策记录", "",
                 text(work["question"]), "", "## 可比较的人工提案（不是已核实事实）", ""]
        analysis = work.get("domain_analysis")
        question_result = (analysis or {}).get("question_result")
        if analysis is not None:
            lines[0] = "# " + text(work["scope"]["entity_label"]) + " · 业务分析与决策报告"
            if question_result and question_result.get("generation") == "SYSTEM_DERIVED_RECOMMENDATIONS":
                lines[4] = "## 来源支持的研究建议（待用户确认）"
            elif question_result and question_result.get("generation") == BusinessDecisionWorkflow.REVISED_RESEARCH_GENERATION:
                lines[4] = "## 来源支持的研究建议（人工修订）"
            if question_result:
                lines += ["## 本次问题分析", "", "核对方式：基于获准原文和已提供字段，逐项核对材料、日期、数值及统计口径；不推断缺失事实。",
                          "分析进展：" + text(label(question_result["state"])),
                          "完整业务判断：" + text(label(question_result.get("full_business_answer", "NOT_ESTABLISHED")))]
                business = question_result.get("business_report")
                if isinstance(business, dict):
                    states = {"AVAILABLE": "已得到限定结果", "PARTIAL": "部分可回答", "UNAVAILABLE": "缺少必要输入"}
                    for answer in business.get("answers", []):
                        lines += ["### " + states.get(answer["state"], "未完成"),
                                  business_text(answer["summary"]), "下一步：" + business_text(answer["next_action"])]
                        lines += [business_text(limit) for limit in answer.get("limitations", [])]
                    for calculation in business.get('quantitative_results', []):
                        statistics = calculation['statistics']
                        calculated = statistics['result']
                        lines += ['## ' + text(calculation['title']),
                                  '计算方法：' + text(calculated.get('method', statistics['analysis'])),
                                  '结果状态：' + ('计算完成，业务解释待核验' if calculated['state'] == 'READY' else '必要条件不足或方法受限'),
                                  '数据单位：' + text(statistics['dataset_unit']),
                                  '原计算成果版本：' + str(calculation['version'])]
                        if calculated.get('value') is not None:
                            lines += ['计算值：' + text(str(calculated['value']))]
                        if calculated.get('interval') is not None:
                            lines += ['区间：' + text(' 至 '.join(str(value) for value in calculated['interval']))]
                        for channel in calculated.get('channels', []):
                            lines += ['渠道：' + text(channel['id']) + '；声明路径的归因份额：'
                                      + text(str(channel.get('attribution_share', '未知')))]
                        lines += [text(limit) for limit in calculated.get('limitations', [])]
                    for review in business.get("document_reviews", []):
                        if not review["declared_counts"] and not review["checks"]:
                            continue
                        lines += ["## 报告数字与统计口径", "材料：" + text(review["title"]),
                                  "本节核对来源报告中明确陈述的数字，不是原生帖子、评论或经营效果的独立核验。"]
                        for declared in review["declared_counts"]:
                            lines += ["报告声明：" + text(declared["value"]) + " " + text(label(declared["unit"]))]
                        for check in review["checks"]:
                            lines += ["### " + text(check["title"]), text(check["summary"]),
                                      "口径限制：" + text(check["limitation"]), "下一步：" + text(check["next_action"]),
                                      "原文定位：字符 " + str(check["reference"]["start"]) + "–" + str(check["reference"]["end"])]
                        for note in review["scope_notes"]:
                            lines += ["来源自述的范围/局限：" + text(note["statement"])]
                    workbench = business.get('domain_workbench')
                    if workbench:
                        headings = {'venue_operations': '经营、活动与服务处置', 'consumer_risk': '反馈与风险核验',
                                    'brand_market': '品牌、市场与消费者研究', 'creator_campaign': '创作者合作与传播计划'}
                        lines += ['## ' + headings[workbench['kind']],
                                  '以下内容为获准来源中的待核陈述；分类匹配不代表已确认的事件、市场结论或风险事实。']
                        for lane in workbench['review_lanes']:
                            lines += ['### ' + text(lane['label'])]
                            if not lane['claims']:
                                lines += ['当前获准材料中未找到对应陈述。']
                            for claim in lane['claims']:
                                ref = claim['reference']
                                lines += ['来源：' + text(claim['source_id']), '原文：' + text(ref['statement']),
                                          '定位：字符 ' + str(ref['start']) + '–' + str(ref['end'])]
                            lines += ['须核验：' + text('；'.join(lane['required_inputs']))]
                        plan = workbench.get('plan')
                        if plan:
                            lines += ['## 责任行动与排期', '用户目标：' + text(plan['objective']),
                                      '计划由用户提供，未授予采购、外发或平台操作权限。']
                            for action in plan['actions']:
                                lines += ['### ' + text(action['deliverable']), '对象：' + text(action['target']),
                                          '责任人：' + text(action['responsible']),
                                          '期限：' + text(action['due_at'] or '尚未确定'),
                                          '前置行动：' + text('、'.join(action['depends_on']) or '无'),
                                          '依据：' + text('、'.join(action['source_ids']))]
                                cost = action['cost_estimate']
                                lines += ['估计费用：' + (text(cost['amount'] or '未知') + ' ' + text(cost['currency']) if cost else '未知')]
                                measure = action['success_measure']
                                if measure:
                                    lines += ['观察指标：' + text(measure['name']) + '；定义：' + text(measure['definition']),
                                              '用户声明基线：' + text(measure['baseline_value'] or '未知')
                                              + '；目标：' + text(measure['target_value'] or '未知') + ' ' + text(measure['unit']),
                                              '观察窗口：' + text(measure['window']['start']) + ' 至 ' + text(measure['window']['end'])]
                            for conflict in workbench['schedule_conflicts']:
                                lines += ['排期冲突：' + text(conflict['action_id']) + ' 的前置行动 '
                                          + text(conflict['dependency']) + ' 截止时间更晚，需修订计划。']
                    period = business.get("period", {})
                    bounds = period.get("time_range")
                    if bounds:
                        lines += ["发布样本期间：" + text(bounds["start"]) + " 至 " + text(bounds["end"]),
                                  "按原生发布时间筛选；不代表期间内发生的互动或增长。"]
                    for excluded in period.get("excluded", []):
                        lines += ["期间外或时间未知来源：" + text(excluded["source_id"])
                                  + "（" + text(label(excluded["reason"])) + "）；采集时间不替代发布时间。"]
                for material in question_result.get("findings", {}).get("source_materials", []):
                    lines += ["可核对来源：" + text(material["source_id"]),
                              "原来源链接：" + text(material.get("url") or "未知"),
                              "原生发布时间：" + text(material.get("published_at") or "未知"),
                              "采集时间：" + text(material.get("captured_at") or "未知"),
                              "材料用途标注：" + text(BusinessDecisionWorkflow._business_role_name(material.get("declared_role"))) + "（仍需核验原文）"]
                for mention in question_result.get("findings", {}).get("reported_dates", []):
                    lines += ["待核验日期：" + text(mention["date"]) + "；来源：" + text(mention["source_id"]),
                              "日期提及不代表事件已确认，须核对事件对象、时区与有效期。"]
                planning = question_result.get("planning_constraints", {})
                if planning.get("time_range"):
                    lines += ["用户研究期间：" + text(planning["time_range"]["start"]) + " 至 "
                              + text(planning["time_range"]["end"])]
                if planning.get("resource_constraints"):
                    resources = planning["resource_constraints"]
                    lines += ["用户预算上限：" + text(resources["budget_amount"] or "未知")
                              + " " + text(resources["currency"] or "未知币种"),
                              "资源限制：" + text("；".join(resources["limits"])),
                              "方案成本仍未知；没有自动采购或外部执行授权。"]
                lines += ["各项建议用于不同的内部研究工作，尚不是经同口径比较的商业策略；业务结果和因果关系仍未得到确认。", ""]
            lines += ["## 分析口径与限制", "", business_text(analysis["judgment"]["conclusion"])]
            for limitation in analysis.get("limitations", []):
                lines.append(text(limitation))
            if question_result is None:
                metrics = analysis["metric_snapshot"]
                total = metrics["total_engagement_complete_sources"]
                lines += ["完整互动字段的来源：" + str(metrics["complete_engagement_source_count"]),
                          "字段合计：" + (str(total) if total is not None else "未知（没有完整输入）"),
                          "互动不是总体需求、销量或投放回报。"]
        lines += ["## 本任务材料与缺口", "", text(label(work["material_review"]["state"]))]
        for check in work["material_review"]["checks"]:
            lines += [text(check["check"]) + "：" + text(label(check["state"]))]
        lines += ["材料角色仅为捕获时标注，仍须核对原文、范围、时效与权利；官网自述不代表消费者意见。", ""]
        lines += ["## 可复查来源", ""]
        for source in work["material_review"]["sources"]:
            source_url, url_state = _source_url(source.get("url"))
            lines += ["来源：" + text(source["source_id"]),
                      "出处：" + text(source_url or ("多个研究出处，详见下列逐字段引用" if source.get("profile_research") else "已隐去（地址含未经批准的参数或凭据）" if url_state == "WITHHELD" else "未知")),
                      "捕获时间：" + text(source.get("captured_at") or "未知"),
                      "发布时间：" + text(source.get("published_at") or "未知（不能以捕获时间替代）"),
                      "材料用途标注：" + text(BusinessDecisionWorkflow._business_role_name(source["declared_role"])) + "（仍需原文核验）",
                      "商业使用许可：" + text(label(source.get("commercial_reuse") or "UNKNOWN")),
                      "范围证据：" + text(source["scope_evidence_ref"])]
            research = source.get("profile_research")
            if research:
                lines += ["研究汇编多出处（签名不等于事实验证；捕获方式为工具文本提取）："]
                for reference in research["references"]:
                    lines += [text(reference["source_id"]) + "：" + text(reference["url"] or reference["url_state"]),
                              "来源时点：" + text(reference["source_as_of"] or "未知") + "；" + text(reference["temporal_scope_note"] or "当前有效性未核实")]
                for assertion in research["assertions"]:
                    selected = research["review"].get(assertion["field"]) == assertion["id"]
                    lines += [text(assertion["field"]) + "：" + text(str(assertion["value"])) +
                              "；来源 " + text(assertion["source_id"]) +
                              ("；人工选择（仍非独立验真）" if selected else "；未采纳来源断言")]
            metric = source["engagement"]
            lines += ["来源互动字段合计：" + (str(metric["value"]) if metric["value"] is not None else "未知（字段未齐）"),
                      "此数值仅来自来源互动字段，不代表客流、需求、销量或投放回报。", ""]
        for option in work["options"]:
            lines += ["### " + option_text(option, "proposal"),
                      option_text(option, "rationale"), "来源：" + text(", ".join(option["source_ids"])),
                      "假设：" + option_text(option, "assumptions"),
                      "未知：" + option_text(option, "unknowns"), "验证与停止条件：" + option_text(option, "check"), ""]
            if option.get("operator_revision"):
                lines += ["人工修订人：" + text(option["operator_revision"]["editor"]),
                          "原始研究建议版本：" + text(option["operator_revision"]["original_revision"]),
                          "修订保留原来源与方法边界，不构成新的商业事实或外部执行批准。"]
        decision = work["decision"]
        lines += ["## 决策与后续工作", ""]
        if decision:
            lines += ["选择：" + option_title(decision["option_id"]), "理由：" + text(decision["reason"]),
                      "责任人：" + text(decision["owner"]), "复查时间：" + text(decision["review_at"])]
            resources = decision.get("resource_constraints")
            if resources:
                lines += ["预算上限（人工输入）：" + text(resources["budget_amount"] if resources["budget_amount"] is not None else "未知"),
                          "方案成本估计（人工输入）：" + text(resources["estimated_cost_amount"] if resources["estimated_cost_amount"] is not None else "未知"),
                          "币种：" + text(resources["currency"] or "未知"), "估计时点：" + text(resources["as_of"] or "未知"),
                          "预算适配：" + text(label(resources["budget_fit"])), "资源与停止约束：" + text("；".join(resources["limits"])),
                          "估计不代表已取得报价、已承诺采购或实际支出；超预算方案需调整。"]
        else:
            lines += ["尚未选择方案。"]
        if work.get("adoption"):
            adoption = work["adoption"]
            lines += ["", "## 已明确采用的修订", "采用理由：" + text(adoption["reason"]),
                      "上一业务版本：" + text(adoption["parent_revision"]),
                      "修改方案：" + ("、".join(option_title(ref) for ref in adoption["changed_option_ids"]) or "无"),
                      "保持方案：" + ("、".join(option_title(ref) for ref in adoption["unchanged_option_ids"]) or "无"),
                      "制作成果需要明确采用本版本；未记录引用的其他影响仍未核实。"]
            if adoption["previous_action_ref"]:
                lines += ["上一版本已执行内部制作的回执：" + text(adoption["previous_action_ref"]),
                          "既有制作事实与历史评价保留；本次修改尚未重新执行或产生新的业务效果。"]
        review = work.get("operator_review")
        if review:
            lines += ["", "## 人工效果复核（不是增长事实或执行授权）",
                      "复核版本：" + text(review["reviewed_revision"]),
                      "复核人：" + text(review["reviewer"]),
                      "评价：" + text(label(review["assessment"])), text(review["observations"]),
                      "限制：" + text("；".join(review["limitations"])),
                      "建议下一步：" + text(label(review["next_step"])),
                      "反馈来源：" + text("、".join(review["source_ids"])),
                      "评价是人工意见；实际收益和因果仍未验证。"]
        action = work.get("action")
        if action:
            receipt = action["receipt"]
            fresh = work.get("action_read", {}).get("state") == "FRESH_OWNER_VERIFIED"
            lines += ["已记录内部文字制作（" + ("本次已向成果服务复查" if fresh else "本次成果读取服务不可用，历史回执尚未重新核验") + "）。",
                      "人工关联方案：" + option_title(action["option_id"]), "制作任务记录：" + text(receipt["task_id"]),
                      "成果：" + text(receipt["artifact_id"]) + " · 版本 " + str(receipt["version"]),
                      "父成果：" + text(receipt["parent_artifact_id"] or "首版，无父成果"),
                      "内容校验值：" + text(receipt["sha256"]), "Word校验值：" + text(receipt["output"]["sha256"]),
                      "内部制作完成不代表活动已执行、内容已获商业许可或消费者效果已验证。"]
        else:
            lines += ["尚未记录已执行行动。"]
        for record in work.get("execution_records", []):
            lines += ["", "## 人工执行声明（尚未独立核实）",
                      "执行人声明：" + text(record["performer"]),
                      "具体对象：" + text(record["exact_target"]),
                      "声明执行时间：" + text(record["performed_at"]),
                      "关联方案：" + option_title(record["option_id"]),
                      "原文：" + text(record["source_claim"]["quote"]),
                      "来源：" + text(record["source_claim"]["source_id"]),
                      "限制：" + text(record["limits"]),
                      "这是人工提供的执行声明；寰意未执行外部动作，也未确认真实经营效果。"]
            planned = record.get('planned_action')
            if planned:
                lines += ['计划交付：' + text(planned['deliverable']),
                          '计划期限：' + text(planned['due_at'] or '尚未确定'),
                          '期限核对：' + {'REPORTED_LATE': '按声明时间已迟于期限',
                              'REPORTED_WITHIN_DEADLINE': '按声明时间未超过期限',
                              'DUE_TIME_UNKNOWN': '期限未知'}[planned['timeliness']]]
        observation = work.get("observation")
        if observation:
            if observation.get("adoption_lineage"):
                lines += ["", "原始观察版本：" + text(observation["adoption_lineage"]["prior_revision"]),
                          "沿用的观察与费用保留原始来源和时间，不是修订方案的新效果。"]
            lines += ["", "## 业务观察与费用（人工转录，尚未独立核实）",
                      "观察时间：" + text(observation["observed_at"]),
                      "观察窗口：" + text(observation["window"]["start"]) + " 至 " + text(observation["window"]["end"]),
                      "来源：" + text(observation["source_claim"]["source_id"]),
                      "原文：" + text(observation["source_claim"]["quote"])]
            for metric in observation["metrics"]:
                lines += [text(label(metric["name"])) + "：" + text(metric["value"] if metric["value"] is not None else "未知") + " " + text(metric["unit"]),
                          "口径：" + text(metric["definition"]),
                          "分子 / 分母：" + text(metric["numerator"] if metric["numerator"] is not None else "未知") + " / "
                          + text(metric["denominator"] if metric["denominator"] is not None else "未知"),
                          "按转录分子分母计算的比率：" + text(metric["ratio"] if metric["ratio"] is not None else "未知")]
                if metric.get("source_claim"):
                    lines += ["本指标来源：" + text(metric["source_claim"]["source_id"]),
                              "本指标原文：" + text(metric["source_claim"]["quote"]),
                              "本指标观察窗口：" + text(metric["window"]["start"]) + " 至 " + text(metric["window"]["end"]),
                              "本指标观察时间：" + text(metric["observed_at"])]
            for cost in observation["cost_ledger"]:
                lines += [text(cost["entry_id"]) + " · " + text(label(cost["kind"])) + "：" + text(cost["amount"] if cost['amount'] is not None else '金额未知') + " " + text(cost["currency"]),
                          "费用来源：" + text(cost["source_claim"]["source_id"])]
                if cost.get('planned_action'):
                    lines += ['人工关联行动：' + text(cost['planned_action']['deliverable']),
                              '所报费用发生时间：' + text(cost.get('occurred_at') or '未知')]
                if cost.get('supersedes_entry_id'):
                    lines += ['更正的原费用记录：' + text(cost['supersedes_entry_id']),
                              '更正原因：' + text(cost['correction_reason']),
                              '原记录保留；合计只使用本次明确更正后的有效记录。']
            for currency, totals in observation["cost_totals"].items():
                lines += [text(currency) + " 估计 / 承诺 / 实支 / 退款 / 净实支：" + " / ".join(
                    text(totals[key] if totals[key] is not None else "未知")
                    for key in ("ESTIMATE", "COMMITTED", "ACTUAL", "REFUND", "net_actual"))]
            if not observation["cost_ledger"]:
                lines += ["费用尚未提供；实际支出与退款为未知。"]
            cost_review = observation.get('action_cost_review')
            if cost_review:
                lines += ['', '## 行动费用与更正核对',
                          '费用关联由用户声明；估计、承诺、实支与退款分开。同币种比较不代表利润、成交归因或新增支出授权。']
                for item in cost_review['actions']:
                    lines += ['行动：' + text(item['action_id']),
                              '与该行动声明估计的余额：' + text(item['remaining_against_declared_estimate']
                                  if item['remaining_against_declared_estimate'] is not None else '未知'),
                              '核对状态：' + text(label(item['estimate_comparison']))]
                    for currency, total in item['reported_costs'].items():
                        lines += [text(currency) + ' 所报实支 / 退款 / 净实支：' + ' / '.join(
                            text(total[key] if total[key] is not None else '未知') for key in ('ACTUAL', 'REFUND', 'net_actual'))]
                        if any(total['unknown_amount_counts'].values()):
                            lines += ['存在金额未知的原始记录；已知金额小计不能代表完整费用。']
                    if item['unconverted_cost_currencies']:
                        lines += ['尚未换算：' + text('、'.join(item['unconverted_cost_currencies']))]
                if cost_review['unallocated_entry_ids']:
                    lines += ['尚未明确归属行动的费用：' + text('、'.join(cost_review['unallocated_entry_ids']))]
                if cost_review['prior_plan_entry_ids']:
                    lines += ['先前行动版本的费用保留原归属：' + text('、'.join(cost_review['prior_plan_entry_ids']))]
                for check in cost_review['refund_checks']:
                    if check['state'] == 'AMOUNT_UNKNOWN_CAP_NOT_ESTABLISHED':
                        lines += ['退款 ' + text(check['entry_id']) + ' 的金额上限因原金额未知尚不能核实。']
            resource_result = observation.get("resource_result")
            if resource_result:
                lines += ["预算核对：" + text(label(resource_result["state"])),
                          "预算余额（人工预算减同币种所报净实支）：" + text(resource_result["remaining_budget_amount"] if resource_result["remaining_budget_amount"] is not None else "未知"),
                          "未换算币种：" + text("、".join(resource_result["unconverted_cost_currencies"]) or "无已记录项"),
                          "承诺独立列示，不假设仍未支出，也不与实际费用重复相加；预算余额不授予新增支出。"]
            comparison = observation.get("comparison", {})
            if comparison.get("baseline_revision"):
                lines += ["前次观察版本：" + text(comparison["baseline_revision"])]
            for item in comparison.get("items", []):
                lines += [text(label(item["name"])) + " 前后转录差值：" + text(item["difference"] if item["difference"] is not None else "不可比较"),
                          "相对变化（比例）：" + text(item["relative_change"] if item["relative_change"] is not None else "未知"),
                          "比较状态：" + text(label(item["reason"] or item["state"])),
                          "同名同口径的描述差值仍未排除营业时长、样本选择、外生事件或总体范围变化，不是本方案的因果效果。"]
            lines += ["限制：" + text(observation["limits"]),
                      "观察、费用与退款均保留来源声明；这些数值不证明因果影响、销售归因或利润。"]
            targets = observation.get('domain_target_review')
            if targets:
                lines += ['## 计划目标与所报结果', '基线和目标由用户声明；数值差额不证明本方案的因果效果或经营成功。']
                for item in targets['actions']:
                    lines += ['行动：' + text(item['action_id']),
                              '与目标的差额：' + text(item['target_gap'] if item['target_gap'] is not None else '不可比较'),
                              '相对声明基线的数值变化：' + text(item['reported_change_from_declared_baseline']
                                   if item['reported_change_from_declared_baseline'] is not None else '未知')]
        lines += ["此记录不授予联系、发布、投放、资金或采集权限。", "",
                  "## 来源报告与结果", "", "来源报告：" + text(work["source_report"]["job_id"])]
        if work.get("outcome"):
            outcome = work["outcome"]
            lines += ["来源原文：" + text(outcome["quote"]), "限制：" + text(outcome["limits"]),
                      "这是来源报告的说法，不证明本方案的效果或因果关系。"]
        if work.get("outcome_unknown"):
            lines += ["业务效果：未知。", "复查限制：" + text(work["outcome_unknown"]["limits"]),
                      "未观察效果不撤销已经完成的内部制作事实。" if work.get("action") else
                      "未观察效果不撤销人工声明的历史记录；执行本身仍未独立核实。"]
        elif not work.get("outcome") and not work.get("observation"):
            lines += ["尚无结果证据。客流、销售、消费者意见与活动效果不得由来源存在性推断。"]
        lines += ["", "## 证据与复查", ""]
        lines += [text(e["evidence_ref"]) for e in work["timeline"]]
        lines += ["", "业务有用性尚未验证；保存与导出由既有共享成果服务处理。"]
        markdown = "\n".join(lines) + "\n"
        return {"state": "OPERATOR_WORKING_RECORD", "markdown": markdown,
                "content_sha256": hashlib.sha256(markdown.encode()).hexdigest(),
                "artifact_state": "W5_EXPORT_BINDING_REQUIRED", "review_status": "HUMAN_PENDING"}

# ---------------------------------------------------------------------------
# 数据库连接：统一通过 Shared Database repository
# ---------------------------------------------------------------------------
def _get_conn() -> sqlite3.Connection:
    return get_repository().connect(timeout=15)


# ---------------------------------------------------------------------------
# 统一响应格式
# ---------------------------------------------------------------------------
def _api_response(data: Any = None, error: str = "",
                  domain_id: str = "", product_id: str = "",
                  status: int = 200):
    """统一 JSON 响应格式：{success, data, error, domain_id, product_id}"""
    success = error == ""
    resp = {
        "success": success,
        "data": data if data is not None else {},
        "error": error,
        "domain_id": domain_id,
        "product_id": product_id,
    }
    return jsonify(resp), status


def _resolve_domain_from_request() -> Dict[str, str]:
    """Use the shared strict request identity resolver (not an authority grant)."""
    from subject_context import resolve_request_identity
    domain_id, product_id = resolve_request_identity()
    return {"domain_id": domain_id, "product_id": product_id}


def _setup_domain_context(domain_id: str, product_id: str) -> DomainContext:
    """Bind the route domain while retaining only explicitly supplied focus."""
    from subject_context import bind_request_context
    from domain_isolation import resolve_domain_identity
    domain_id, _ = resolve_domain_identity(domain_id, product_id)
    return bind_request_context(domain_id)


def _bind_blueprint_context(domain_id):
    _teardown_domain_context()
    try:
        _setup_domain_context(domain_id, domain_to_product(domain_id))
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return None


def _teardown_domain_context():
    """请求结束后清除线程上下文（防止线程复用泄漏）。"""
    clear_domain_context()
    clear_thread_context()


# ---------------------------------------------------------------------------
# 蓝图定义
# ---------------------------------------------------------------------------
zbmp_bp = Blueprint("zbmp_api", __name__, url_prefix="/api/zbmp")
cth_bp = Blueprint("cth_api", __name__, url_prefix="/api/cth")
system_bp = Blueprint("system_api", __name__, url_prefix="/api/system")


# ---------------------------------------------------------------------------
# ZBMP canonical snapshot
# ---------------------------------------------------------------------------
# ZBMP is a market-intelligence consumer of the canonical layer.  It must not
# infer a brand from a CTH author, source, or an unverified row in notes.  This
# snapshot is the single read path shared by the ZBMP APIs and Experience
# screen bindings; it intentionally does not create tables or write data.
def _optional_int(value: Any) -> Optional[int]:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _sum_optional(values: List[Any]) -> Optional[int]:
    observed = [_optional_int(value) for value in values]
    observed = [value for value in observed if value is not None]
    return sum(observed) if observed else None


def _canonical_from_row(row: sqlite3.Row):
    """Build the existing CanonicalRecord without inventing missing columns."""
    from canonical_data import CanonicalRecord

    keys = set(row.keys())
    values = {}
    for field_name in CanonicalRecord.__dataclass_fields__:
        if field_name in keys and row[field_name] is not None:
            values[field_name] = row[field_name]
    return CanonicalRecord(**values)


class CTHScopedReadError(RuntimeError):
    """A CTH read could not resolve or authorize its explicit request scope."""

    def __init__(self, code: str, status: int):
        super().__init__(code)
        self.code = code
        self.status = status


def _scope_alias(value: str) -> str:
    import re
    import unicodedata

    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).strip()).casefold()


def _cth_request_subject(connection: sqlite3.Connection) -> Optional[str]:
    """Resolve request metadata to one active canonical CTH Subject, or GLOBAL."""
    context = get_domain_context()
    if context is None or context.domain_id != DOMAIN_CTH:
        raise CTHScopedReadError("CTH_REQUEST_CONTEXT_UNAVAILABLE", 503)

    subject_id = context.subject_id
    brand_key = context.brand_key
    for value in (subject_id, brand_key):
        if (not isinstance(value, str) or value != value.strip()
                or any(ord(char) < 32 or ord(char) == 127 for char in value)):
            raise CTHScopedReadError("INVALID_CTH_FOCUS", 400)
    if not subject_id and not brand_key:
        return None

    try:
        from subject_registry import list_subjects
        subjects = list_subjects("CTH", connection=connection)
    except Exception as exc:
        raise CTHScopedReadError("CTH_SUBJECT_REGISTRY_UNAVAILABLE", 503) from exc

    selected = None
    if subject_id:
        matches = [row for row in subjects if row.get("subject_id") == subject_id]
        if len(matches) != 1:
            raise CTHScopedReadError("CTH_SUBJECT_NOT_FOUND", 404)
        selected = matches[0]

    if brand_key:
        requested_alias = _scope_alias(brand_key)
        alias_matches = []
        for row in subjects:
            aliases = [row.get("subject_id"), row.get("name_en"), row.get("name_zh")]
            aliases.extend(row.get("keywords") if isinstance(row.get("keywords"), list) else [])
            if requested_alias in {
                _scope_alias(alias) for alias in aliases
                if isinstance(alias, str) and alias.strip()
            }:
                alias_matches.append(row)
        unique_matches = {row.get("subject_id"): row for row in alias_matches}
        if len(unique_matches) != 1:
            raise CTHScopedReadError(
                "CTH_FOCUS_ALIAS_AMBIGUOUS" if unique_matches else "CTH_FOCUS_ALIAS_NOT_FOUND",
                400 if unique_matches else 404,
            )
        alias_subject = next(iter(unique_matches.values()))
        if selected is not None and selected.get("subject_id") != alias_subject.get("subject_id"):
            raise CTHScopedReadError("CTH_FOCUS_IDENTITY_CONFLICT", 400)
        selected = alias_subject

    if selected is None or selected.get("subject_type") != "company":
        raise CTHScopedReadError("INVALID_CTH_SUBJECT_TYPE", 400)
    return selected["subject_id"]


def _authorize_cth_read(connection: sqlite3.Connection, *, module: str) -> Dict[str, Any]:
    """Resolve request identity and ask the canonical Permission owner on every read."""
    if module not in {"content", "reports", "cases", "collector"}:
        raise CTHScopedReadError("INVALID_CTH_READ_MODULE", 400)
    subject_id = _cth_request_subject(connection)
    global_scope = subject_id is None
    try:
        from lumenis.auth.service import get_current_user
        from lumenis.system.security.permission import (
            check_actor_scope_permission,
            check_local_workspace_scope_permission,
            resolve_local_workspace_principal,
        )

        actor = get_current_user(read_only=True)
        if isinstance(actor, dict) and type(actor.get("id")) is int and actor["id"] > 0:
            decision = check_actor_scope_permission(
                actor, domain_id=DOMAIN_CTH, action="read", module=module,
                subject_id=subject_id, global_scope=global_scope,
                connection=connection,
            )
        else:
            principal = resolve_local_workspace_principal(module=module, action="read")
            if principal is None:
                raise CTHScopedReadError("AUTH_REQUIRED", 401)
            decision = check_local_workspace_scope_permission(
                principal, domain_id=DOMAIN_CTH, action="read", module=module,
                subject_id=subject_id, global_scope=global_scope,
                connection=connection,
            )
    except CTHScopedReadError:
        raise
    except Exception as exc:
        raise CTHScopedReadError("CTH_SCOPE_AUTHORIZATION_UNAVAILABLE", 503) from exc

    if getattr(decision, "verification_state", None) != "verified":
        raise CTHScopedReadError("CTH_SCOPE_AUTHORIZATION_UNAVAILABLE", 503)
    if not getattr(decision, "allowed", False):
        raise CTHScopedReadError("CTH_SCOPE_READ_DENIED", 403)
    audit_id = getattr(decision, "audit_id", None)
    if not isinstance(audit_id, str) or not audit_id:
        raise CTHScopedReadError("CTH_SCOPE_AUDIT_UNAVAILABLE", 503)

    return {
        "mode": "GLOBAL_ALL" if global_scope else "FOCUS",
        "domain_id": DOMAIN_CTH,
        "product_id": PRODUCT_CTH,
        "subject_id": subject_id,
        "global": global_scope,
        "permission_audit_id": audit_id,
    }


def read_cth_scoped_canonical(
    connection: sqlite3.Connection, *, module: str, limit: int = 100,
    source_ids: Optional[List[str]] = None, platform: Optional[str] = None,
    offset: int = 0, source_type: Optional[str] = None,
    source_table: Optional[str] = None,
) -> Dict[str, Any]:
    """Read signed Canonical rows after fresh CTH scope authorization.

    Optional platform or typed-source paging selects candidate source IDs from
    the existing Canonical table, then sends those IDs through the Canonical
    owner's signed scope validator. Candidate queries grant no access and
    return no business rows directly.
    """
    if not isinstance(connection, sqlite3.Connection):
        raise CTHScopedReadError("CTH_CANONICAL_CONNECTION_INVALID", 503)
    if type(limit) is not int or not 1 <= limit <= 100:
        raise CTHScopedReadError("INVALID_CTH_READ_LIMIT", 400)
    if type(offset) is not int or offset < 0:
        raise CTHScopedReadError("INVALID_CTH_READ_OFFSET", 400)
    if source_ids is not None and (platform is not None or offset != 0):
        raise CTHScopedReadError("CTH_SOURCE_SELECTION_CONFLICT", 400)
    if source_ids is not None and source_type is not None:
        raise CTHScopedReadError("CTH_SOURCE_SELECTION_CONFLICT", 400)
    if platform is not None and source_type is not None:
        raise CTHScopedReadError("CTH_SOURCE_SELECTION_CONFLICT", 400)
    if (source_type is None) != (source_table is None):
        raise CTHScopedReadError("CTH_SOURCE_TYPE_TABLE_PAIR_REQUIRED", 400)
    if source_type is not None and (source_type, source_table) not in {
        ("note", "notes"), ("web_mention", "web_mentions"),
    }:
        raise CTHScopedReadError("CTH_SOURCE_TYPE_TABLE_UNSUPPORTED", 400)

    scope = _authorize_cth_read(connection, module=module)
    try:
        import canonical_data
        if platform is None and source_type is None and offset == 0:
            canonical = canonical_data.list_scoped_canonical(
                connection, product_id=PRODUCT_CTH,
                subject_id=scope["subject_id"], limit=limit,
                source_ids=source_ids,
            )
        elif platform is None:
            filters = [
                "product_id=?", "domain_id=?", "scope_status='VERIFIED'",
                "source_id IS NOT NULL", "TRIM(source_id) != ''",
            ]
            params: List[Any] = [PRODUCT_CTH, DOMAIN_CTH]
            if scope["subject_id"] is not None:
                filters.extend(["subject_id=?", "(brand_focus_id IS NULL OR brand_focus_id='')"])
                params.append(scope["subject_id"])
            if source_type is not None:
                filters.extend(["source_type=?", "source_table=?"])
                params.extend([source_type, source_table])
            predicate = " AND ".join(filters)
            total = connection.execute(
                "SELECT COUNT(*) FROM (SELECT source_id FROM canonical_data WHERE "
                + predicate + " GROUP BY source_id)", tuple(params),
            ).fetchone()[0]
            rows = connection.execute(
                "SELECT source_id, MAX(COALESCE(captured_at,'')) AS latest "
                "FROM canonical_data WHERE " + predicate
                + " GROUP BY source_id ORDER BY latest DESC, source_id ASC LIMIT ? OFFSET ?",
                tuple(params + [limit, offset]),
            ).fetchall()
            selected_ids = [row[0] for row in rows]
            if selected_ids:
                canonical = canonical_data.list_scoped_canonical(
                    connection, product_id=PRODUCT_CTH,
                    subject_id=scope["subject_id"], limit=limit,
                    source_ids=selected_ids,
                )
            else:
                canonical = {
                    "records": [], "candidate_count": 0, "scanned_count": 0,
                    "rejected_count": 0, "returned_count": 0,
                    "limit": limit, "truncated": False,
                }
            canonical["page"] = {
                "candidate_source_count": total,
                "offset": offset,
                "limit": limit,
                "returned_source_count": len(selected_ids),
                "truncated": offset + len(selected_ids) < total or canonical.get("truncated", False),
            }
        else:
            from lumenis.system.collector.adapters.platform_naming import (
                get_platform_aliases, normalize_platform,
            )
            normalized_platform = normalize_platform(platform)
            if normalized_platform is None:
                raise CTHScopedReadError("UNKNOWN_PLATFORM_ALIAS", 400)
            aliases = get_platform_aliases(normalized_platform)
            placeholders = ",".join("?" for _ in aliases)
            filters = [
                "product_id=?", "domain_id=?", "scope_status='VERIFIED'",
                "source_id IS NOT NULL", "TRIM(source_id) != ''",
                f"LOWER(source_platform) IN ({placeholders})",
            ]
            params: List[Any] = [PRODUCT_CTH, DOMAIN_CTH, *aliases]
            if scope["subject_id"] is not None:
                filters.extend(["subject_id=?", "(brand_focus_id IS NULL OR brand_focus_id='')"])
                params.append(scope["subject_id"])
            predicate = " AND ".join(filters)
            total = connection.execute(
                "SELECT COUNT(*) FROM (SELECT source_id FROM canonical_data WHERE "
                + predicate + " GROUP BY source_id)", tuple(params),
            ).fetchone()[0]
            rows = connection.execute(
                "SELECT source_id, MAX(COALESCE(captured_at,'')) AS latest "
                "FROM canonical_data WHERE " + predicate
                + " GROUP BY source_id ORDER BY latest DESC, source_id ASC LIMIT ? OFFSET ?",
                tuple(params + [limit, offset]),
            ).fetchall()
            selected_ids = [row[0] for row in rows]
            if selected_ids:
                canonical = canonical_data.list_scoped_canonical(
                    connection, product_id=PRODUCT_CTH,
                    subject_id=scope["subject_id"], limit=limit,
                    source_ids=selected_ids,
                )
            else:
                canonical = {
                    "records": [], "candidate_count": 0, "scanned_count": 0,
                    "rejected_count": 0, "returned_count": 0,
                    "limit": limit, "truncated": False,
                }
            canonical["records"] = [
                row for row in canonical["records"]
                if normalize_platform(row.get("source_platform")) == normalized_platform
            ]
            canonical["returned_count"] = len(canonical["records"])
            canonical["page"] = {
                "candidate_source_count": total,
                "offset": offset,
                "limit": limit,
                "returned_source_count": len(selected_ids),
                "truncated": offset + len(selected_ids) < total,
            }
    except CTHScopedReadError:
        raise
    except ValueError as exc:
        raise CTHScopedReadError("INVALID_CTH_CANONICAL_SCOPE", 400) from exc
    except Exception as exc:
        raise CTHScopedReadError("CTH_CANONICAL_SCOPE_UNAVAILABLE", 503) from exc

    return {"scope": {key: value for key, value in scope.items() if key != "permission_audit_id"},
            "permission_audit_id": scope["permission_audit_id"], "canonical": canonical}


def _safe_zbmp_record(row: sqlite3.Row, adapter: Any) -> Optional[Dict[str, Any]]:
    """Adapt one already domain-filtered row and retain provenance only."""
    try:
        record = _canonical_from_row(row)
        domain_record = adapter.to_domain(record)
    except (TypeError, ValueError):
        return None

    raw = dict(row)
    safe = domain_record.to_dict()
    # These are generic trace fields, not CTH-specific data.  Keeping them at
    # the view boundary makes source -> canonical -> UI traceable without
    # exposing the rest of the raw row.
    for key in (
        "source_id", "external_id", "source_type", "source_table",
        "source_keyword", "provenance", "content_hash", "evidence_ref",
        "raw_ref", "verification_status", "quality_status",
    ):
        if key in raw:
            safe[key] = raw.get(key)

    # A brand is only a brand when an explicitly verified field exists.  The
    # current canonical schema has neither field, so current output is
    # intentionally empty instead of treating author_name as brand_key.
    if "brand_key" in raw and "brand_key_verified" in raw and raw.get("brand_key_verified"):
        brand_key = str(raw.get("brand_key") or "").strip()
        if brand_key:
            safe["brand_key"] = brand_key
    return safe


def _build_zbmp_brands(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for record in records:
        brand_key = str(record.get("brand_key") or "").strip()
        if not brand_key:
            continue
        item = grouped.setdefault(brand_key, {
            "brand_key": brand_key,
            "platforms": set(),
            "record_count": 0,
            "total_likes": [],
            "total_comments": [],
            "domain": DOMAIN_ZBMP,
        })
        platform = str(record.get("source_platform") or "").strip()
        if platform:
            item["platforms"].add(platform)
        item["record_count"] += 1
        item["total_likes"].append(record.get("engagement_likes"))
        item["total_comments"].append(record.get("engagement_comments"))

    result = []
    for item in grouped.values():
        result.append({
            "brand_key": item["brand_key"],
            "platforms": sorted(item["platforms"]),
            "record_count": item["record_count"],
            "total_likes": _sum_optional(item["total_likes"]),
            "total_comments": _sum_optional(item["total_comments"]),
            "domain": item["domain"],
        })
    result.sort(key=lambda value: (-value["record_count"], value["brand_key"]))
    return result[:100]


def _zbmp_capture_trend(records: List[Dict[str, Any]], days: int = 14) -> Dict[str, Any]:
    today = _datetime.now().date()
    counts: Dict[str, Dict[str, int]] = {}
    for record in records:
        captured_at = str(record.get("captured_at") or "")
        date_key = captured_at[:10]
        if len(date_key) != 10:
            continue
        bucket = counts.setdefault(date_key, {"total": 0, "negative": 0})
        bucket["total"] += 1
        if str(record.get("sentiment") or "").lower() == "negative":
            bucket["negative"] += 1

    labels = []
    totals = []
    negatives = []
    for back in range(days - 1, -1, -1):
        day = today - _timedelta(days=back)
        key = day.isoformat()
        bucket = counts.get(key, {"total": 0, "negative": 0})
        labels.append(key[5:])
        totals.append(bucket["total"])
        negatives.append(bucket["negative"])
    return {"labels": labels, "total": totals, "negative": negatives}


def get_zbmp_product_snapshot() -> Dict[str, Any]:
    """Stream the domain slice; distinguish missing data, rejection and read errors.

    Aggregates cover all accepted rows. Returned record previews are bounded and
    carry their own count, so a 200-row preview is never presented as all data.
    """
    from collections import Counter
    from datetime import timezone

    from canonical_data import PRODUCT_ZBMP

    snapshot: Dict[str, Any] = {
        "data_state": "NOT_COLLECTED", "records": [], "canonical_records": [],
        "brands": [], "total_records": 0, "errors": [],
        "page": {"limit": 200, "returned_count": 0, "truncated": False},
        "rejected_count": 0,
        "brand_page": {"total_count": 0, "returned_count": 0, "truncated": False},
        "metrics": {
            "total_notes": 0, "total_web_mentions": 0, "total_canonical_zbmp": 0,
            "total_engagement": {"likes": None, "comments": None, "collects": None, "shares": None},
            "engagement_known_counts": {}, "sentiment_distribution": {},
            "risk_distribution": {}, "platform_distribution": {}, "latest_capture": "",
            "capture_trend": {"labels": [], "total": [], "negative": []},
            "counts_basis": "accepted BMP Canonical rows; capture dates are not publication dates",
        },
    }
    conn = None
    try:
        conn = _get_conn()
        conn.execute("BEGIN")  # one read snapshot, no source writes
        cursor = conn.execute(
            "SELECT * FROM canonical_data WHERE product_id=? AND domain_id=? "
            "ORDER BY captured_at DESC, canonical_id DESC", (PRODUCT_ZBMP, DOMAIN_ZBMP))
        adapter = get_adapter(DOMAIN_ZBMP)
        metrics = snapshot["metrics"]
        today = _datetime.now(tz=timezone.utc).astimezone().date()
        totals, known = Counter(), Counter()
        captures, negative_captures = Counter(), Counter()
        brand_groups = {}
        while True:
            batch = cursor.fetchmany(200)
            if not batch:
                break
            for row in batch:
                safe = _safe_zbmp_record(row, adapter)
                if safe is None:
                    snapshot["rejected_count"] += 1
                    continue
                snapshot["total_records"] += 1
                if len(snapshot["records"]) < 200:
                    snapshot["records"].append(safe)
                source_type = safe.get("source_type")
                metrics["total_notes"] += source_type in ("note", "collected_note")
                metrics["total_web_mentions"] += source_type == "web_mention"
                for output in ("likes", "comments", "collects", "shares"):
                    value = _optional_int(safe.get("engagement_" + output))
                    if value is not None:
                        totals[output] += value
                        known[output] += 1
                for field, output in (("source_platform", "platform_distribution"),
                                      ("sentiment", "sentiment_distribution"),
                                      ("risk_level", "risk_distribution")):
                    value = str(safe.get(field) or "UNKNOWN")
                    metrics[output][value] = metrics[output].get(value, 0) + 1
                captured = str(safe.get("captured_at") or "")
                if captured:
                    metrics["latest_capture"] = max(metrics["latest_capture"], captured)
                try:
                    date = _datetime.fromisoformat(captured.replace("Z", "+00:00")).date()
                except ValueError:
                    date = None
                if date is not None and 0 <= (today - date).days < 14:
                    captures[date.isoformat()] += 1
                    if str(safe.get("sentiment") or "").lower() == "negative":
                        negative_captures[date.isoformat()] += 1
                brand_key = safe.get("brand_key")
                if brand_key:
                    item = brand_groups.setdefault(brand_key, {
                        "brand_key": brand_key, "platforms": set(), "record_count": 0,
                        "total_likes": None, "total_comments": None, "domain": DOMAIN_ZBMP})
                    item["record_count"] += 1
                    if safe.get("source_platform"):
                        item["platforms"].add(safe["source_platform"])
                    for key in ("likes", "comments"):
                        value = _optional_int(safe.get("engagement_" + key))
                        if value is not None:
                            item["total_" + key] = (item["total_" + key] or 0) + value
        metrics["total_canonical_zbmp"] = snapshot["total_records"]
        for key in metrics["total_engagement"]:
            metrics["total_engagement"][key] = totals[key] if known[key] else None
            metrics["engagement_known_counts"][key] = known[key]
        snapshot["canonical_records"] = list(snapshot["records"])
        snapshot["page"].update(returned_count=len(snapshot["records"]),
                                 truncated=snapshot["total_records"] > len(snapshot["records"]))
        brands = sorted(brand_groups.values(), key=lambda b: (-b["record_count"], b["brand_key"]))
        for item in brands[:100]:
            item["platforms"] = sorted(item["platforms"])
        snapshot["brands"] = brands[:100]
        snapshot["brand_page"] = {"total_count": len(brands), "returned_count": len(snapshot["brands"]),
                                  "truncated": len(brands) > 100}
        if snapshot["total_records"]:
            snapshot["data_state"] = "PARTIAL" if snapshot["rejected_count"] else "READY"
            days = [(today - _timedelta(days=n)).isoformat() for n in range(13, -1, -1)]
            metrics["capture_trend"] = {"labels": [day[5:] for day in days],
                                        "total": [captures[day] for day in days],
                                        "negative": [negative_captures[day] for day in days]}
        elif snapshot["rejected_count"]:
            snapshot["data_state"] = "REJECTED"
        if snapshot["rejected_count"]:
            snapshot["errors"].append("CANONICAL_DOMAIN_ROWS_REJECTED")
        return snapshot
    except Exception as exc:
        # Never expose database/path details or turn an exception into empty data.
        snapshot["data_state"] = "ERROR"
        snapshot["errors"].append("BMP_CANONICAL_READ_FAILED:" + type(exc).__name__)
        snapshot["records"] = []
        snapshot["canonical_records"] = []
        snapshot["brands"] = []
        snapshot["total_records"] = None
        snapshot["page"] = {"limit": 200, "returned_count": 0, "truncated": None}
        snapshot["brand_page"] = {"total_count": None, "returned_count": 0, "truncated": None}
        snapshot["rejected_count"] = None
        snapshot["metrics"] = {key: None for key in snapshot["metrics"]}
        return snapshot
    finally:
        if conn is not None:
            conn.close()



# ---------------------------------------------------------------------------
# before_request / after_request 钩子（每个蓝图独立）
# ---------------------------------------------------------------------------
@zbmp_bp.before_request
def _zbmp_before():
    return _bind_blueprint_context(DOMAIN_ZBMP)


@zbmp_bp.after_request
def _zbmp_after(response):
    _teardown_domain_context()
    return response


@cth_bp.before_request
def _cth_before():
    return _bind_blueprint_context(DOMAIN_CTH)


@cth_bp.after_request
def _cth_after(response):
    _teardown_domain_context()
    return response


@system_bp.before_request
def _system_before():
    return _bind_blueprint_context(DOMAIN_SYSTEM)


@system_bp.after_request
def _system_after(response):
    _teardown_domain_context()
    return response


# ===========================================================================
# ZBMP 端点
# ===========================================================================
@zbmp_bp.route("/overview", methods=["GET"])
def zbmp_overview():
    """ZBMP 品牌总览：只读经过域校验的 ZBMP canonical slice。"""
    try:
        snapshot = get_zbmp_product_snapshot()
        metrics = snapshot["metrics"]
        data = {
            "data_state": snapshot["data_state"],
            "brands": snapshot["brands"],
            "total_records": snapshot["total_records"],
            "by_platform": metrics["platform_distribution"],
            "by_sentiment": metrics["sentiment_distribution"],
            "canonical_records": snapshot["canonical_records"],
            "page": snapshot["page"],
            "brand_page": snapshot["brand_page"],
            "rejected_count": snapshot["rejected_count"],
            "errors": snapshot["errors"],
        }
        read_error = snapshot["data_state"] == "ERROR"
        return _api_response(data=data, error="BMP_CANONICAL_READ_FAILED" if read_error else "",
                             domain_id=DOMAIN_ZBMP, product_id=PRODUCT_ZBMP,
                             status=503 if read_error else 200)
    except Exception as e:
        return _api_response(error=str(e), domain_id=DOMAIN_ZBMP, product_id=PRODUCT_ZBMP, status=500)


@zbmp_bp.route("/brands", methods=["GET"])
def zbmp_brands():
    """ZBMP 品牌列表：只接受 canonical 中显式且已验证的 brand_key。"""
    try:
        snapshot = get_zbmp_product_snapshot()
        data = {
            "data_state": snapshot["data_state"],
            "brands": snapshot["brands"],
            "total_brands": snapshot["brand_page"]["total_count"],
            "page": snapshot["brand_page"],
            "rejected_count": snapshot["rejected_count"],
            "errors": snapshot["errors"],
        }
        read_error = snapshot["data_state"] == "ERROR"
        return _api_response(data=data, error="BMP_CANONICAL_READ_FAILED" if read_error else "",
                             domain_id=DOMAIN_ZBMP, product_id=PRODUCT_ZBMP,
                             status=503 if read_error else 200)
    except Exception as e:
        return _api_response(error=str(e), domain_id=DOMAIN_ZBMP, product_id=PRODUCT_ZBMP, status=500)


@zbmp_bp.route("/metrics", methods=["GET"])
def zbmp_metrics():
    """ZBMP 指标：从同一 canonical snapshot 计算，避免重复口径。"""
    try:
        snapshot = get_zbmp_product_snapshot()
        metrics = dict(snapshot["metrics"])
        metrics["data_state"] = snapshot["data_state"]
        metrics["errors"] = snapshot["errors"]
        read_error = snapshot["data_state"] == "ERROR"
        return _api_response(data=metrics, error="BMP_CANONICAL_READ_FAILED" if read_error else "",
                             domain_id=DOMAIN_ZBMP, product_id=PRODUCT_ZBMP,
                             status=503 if read_error else 200)
    except Exception as e:
        return _api_response(error=str(e), domain_id=DOMAIN_ZBMP, product_id=PRODUCT_ZBMP, status=500)


# ===========================================================================
# CTH 端点
# ===========================================================================
def _cth_scoped_projection(snapshot: Dict[str, Any], *, include_content: bool = False) -> List[Dict[str, Any]]:
    """Project only verified Canonical rows into the existing CTH view shape."""
    adapter = get_adapter(DOMAIN_CTH)
    allowed = (
        "canonical_id", "product_id", "domain_id", "subject_id", "source_platform",
        "title", "content", "url", "author_name", "publish_datetime", "captured_at",
        "sentiment", "sentiment_score", "risk_level", "risk_score", "engagement_likes",
        "engagement_comments", "engagement_collects", "engagement_shares", "topics", "tags",
        "event_hint", "source_type", "source_id", "scope_status", "scope_evidence_ref",
        "provenance", "evidence_ref",
    )
    projected: List[Dict[str, Any]] = []
    for row in snapshot["canonical"]["records"]:
        # Adaptation is the existing domain boundary; raw row keys are then
        # explicitly allow-listed so adapter defaults cannot invent facts.
        adapter.to_domain(_canonical_from_row(row))
        item = {key: row.get(key) for key in allowed if key in row}
        if not include_content:
            item.pop("content", None)
        elif isinstance(item.get("content"), str):
            item["content"] = item["content"][:500]
        projected.append(item)
    return projected


def _cth_read_error_response(exc: Exception):
    if isinstance(exc, CTHScopedReadError):
        return _api_response(error=exc.code, domain_id=DOMAIN_CTH,
                             product_id=PRODUCT_CTH, status=exc.status)
    return _api_response(error="CTH_SCOPED_READ_UNAVAILABLE", domain_id=DOMAIN_CTH,
                         product_id=PRODUCT_CTH, status=503)


# ===========================================================================
# CTH 端点 — scoped Canonical only
# ===========================================================================
@cth_bp.route("/overview", methods=["GET"])
def cth_overview():
    """Scoped CTH overview backed only by signed Canonical records."""
    conn = None
    try:
        conn = _get_conn()
        snapshot = read_cth_scoped_canonical(conn, module="reports", limit=100)
        records = _cth_scoped_projection(snapshot)
        canonical = snapshot["canonical"]

        def distribution(field: str) -> Dict[str, int]:
            result: Dict[str, int] = {}
            for record in records:
                value = record.get(field)
                if isinstance(value, str) and value.strip():
                    result[value] = result.get(value, 0) + 1
            return result

        def engagement(field: str) -> Optional[int]:
            values = [record.get(field) for record in records]
            return _sum_optional(values)

        complete_scan = not canonical["truncated"] and canonical["rejected_count"] == 0
        data = {
            "scope": snapshot["scope"],
            "subject_id": snapshot["scope"]["subject_id"],
            "total_canonical": canonical["returned_count"] if complete_scan else None,
            "total_notes": None,
            "total_web_mentions": None,
            "source_tables_state": "NOT_READ_OUTSIDE_CANONICAL_OWNER",
            "by_platform": distribution("source_platform"),
            "by_sentiment": distribution("sentiment"),
            "by_risk": distribution("risk_level"),
            "recent_records": records[:20],
            "engagement_summary": {
                "likes": engagement("engagement_likes"),
                "comments": engagement("engagement_comments"),
                "collects": engagement("engagement_collects"),
                "shares": engagement("engagement_shares"),
                "basis": "VERIFIED_RETURNED_CANONICAL_ROWS",
            },
            "canonical_read": {
                "candidate_count": canonical["candidate_count"],
                "scanned_count": canonical["scanned_count"],
                "rejected_count": canonical["rejected_count"],
                "verified_returned_count": canonical["returned_count"],
                "truncated": canonical["truncated"],
            },
        }
        return _api_response(data=data, domain_id=DOMAIN_CTH, product_id=PRODUCT_CTH)
    except Exception as exc:
        return _cth_read_error_response(exc)
    finally:
        if conn is not None:
            conn.close()


@cth_bp.route("/events", methods=["GET"])
def cth_events():
    """List topic/event hints from signed Canonical rows in the requested scope."""
    conn = None
    try:
        conn = _get_conn()
        snapshot = read_cth_scoped_canonical(conn, module="reports", limit=100)
        records = _cth_scoped_projection(snapshot)
        events = []
        for record in records:
            event_hint = record.get("event_hint")
            topics = record.get("topics")
            has_topics = bool(topics)
            if isinstance(topics, str):
                normalized_topics = topics.strip()
                if normalized_topics in {"", "[]", "{}", "null"}:
                    has_topics = False
                else:
                    try:
                        has_topics = bool(json.loads(normalized_topics))
                    except (TypeError, ValueError):
                        has_topics = True
            if not (isinstance(event_hint, str) and event_hint.strip()) and not has_topics:
                continue
            events.append({
                "event_id": record.get("canonical_id"),
                "title": record.get("title"),
                "event_hint": event_hint,
                "topics": topics,
                "tags": record.get("tags"),
                "publish_datetime": record.get("publish_datetime"),
                "captured_at": record.get("captured_at"),
                "sentiment": record.get("sentiment"),
                "risk_level": record.get("risk_level"),
                "platform": record.get("source_platform"),
                "domain": DOMAIN_CTH,
                "subject_id": record.get("subject_id"),
                "source_id": record.get("source_id"),
                "scope_evidence_ref": record.get("scope_evidence_ref"),
            })
        canonical = snapshot["canonical"]
        data = {
            "scope": snapshot["scope"],
            "events": events,
            "total_events": len(events),
            "canonical_read": {
                "candidate_count": canonical["candidate_count"],
                "scanned_count": canonical["scanned_count"],
                "rejected_count": canonical["rejected_count"],
                "truncated": canonical["truncated"],
            },
        }
        return _api_response(data=data, domain_id=DOMAIN_CTH, product_id=PRODUCT_CTH)
    except Exception as exc:
        return _cth_read_error_response(exc)
    finally:
        if conn is not None:
            conn.close()


@cth_bp.route("/xiaohongshu", methods=["GET"])
def cth_xiaohongshu():
    """List verified scoped RedNote Canonical records without inferred focus."""
    conn = None
    try:
        try:
            limit = int(request.args.get("limit", 50))
            offset = int(request.args.get("offset", 0))
        except (TypeError, ValueError):
            raise CTHScopedReadError("INVALID_CTH_READ_PAGINATION", 400)
        conn = _get_conn()
        snapshot = read_cth_scoped_canonical(
            conn, module="content", limit=limit, offset=offset, platform="xiaohongshu",
        )
        records = _cth_scoped_projection(snapshot, include_content=True)
        output = []
        for record in records:
            item = dict(record)
            # Preserve the legacy response field names without converting
            # unknown engagement into zero or asserting a Taikoo match.
            item["note_id"] = item.get("source_id")
            item["publish_date"] = item.get("publish_datetime")
            item["collected_at"] = item.get("captured_at")
            item["likes"] = item.get("engagement_likes")
            item["comments"] = item.get("engagement_comments")
            item["collects"] = item.get("engagement_collects")
            item["shares"] = item.get("engagement_shares")
            item["platform"] = item.get("source_platform")
            item["domain"] = DOMAIN_CTH
            output.append(item)
        canonical = snapshot["canonical"]
        page = canonical.get("page", {})
        data = {
            "scope": snapshot["scope"],
            "records": output,
            "total_candidates": page.get("candidate_source_count"),
            "limit": limit,
            "offset": offset,
            "platform": "xiaohongshu",
            "verified_records_count": len(output),
            "rejected_count": canonical["rejected_count"],
            "truncated": page.get("truncated", canonical["truncated"]),
        }
        return _api_response(data=data, domain_id=DOMAIN_CTH, product_id=PRODUCT_CTH)
    except Exception as exc:
        return _cth_read_error_response(exc)
    finally:
        if conn is not None:
            conn.close()


# ===========================================================================
# System 端点
# ===========================================================================
@system_bp.route("/status", methods=["GET"])
def system_status():
    """系统状态：DB/Collector/AI/Guardian 健康度。

    读真实数据：runtime_guardian_workers、DB 连接状态、collector_automation 状态。
    """
    try:
        status = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "database": {"status": "unknown", "tables": 0},
            "collector": {"status": "unknown", "running": False},
            "ai": {"status": "unknown"},
            "guardian": {"status": "unknown", "workers": 0, "running": 0},
            "overall": "healthy",
        }

        # DB 健康度
        try:
            conn = _get_conn()
            tables = conn.execute(
                "SELECT COUNT(*) as c FROM sqlite_master WHERE type='table'"
            ).fetchone()["c"]
            status["database"] = {"status": "healthy", "tables": tables}
            conn.close()
        except Exception as e:
            status["database"] = {"status": "error", "error": str(e)}
            status["overall"] = "degraded"

        # Guardian 健康度
        try:
            from runtime_guardian import get_guardian
            g = get_guardian("default")
            health = g.health_check()
            status["guardian"] = {
                "status": health.get("overall", "unknown"),
                "workers": health.get("workers", {}).get("total", 0),
                "running": health.get("workers", {}).get("running", 0),
                "failed": health.get("workers", {}).get("failed", 0),
                "dead": health.get("workers", {}).get("dead", 0),
                "dlq": health.get("dlq", {}),
            }
            if health.get("overall") == "degraded":
                status["overall"] = "degraded"
        except Exception as e:
            status["guardian"] = {"status": "error", "error": str(e)}

        # Collector 状态
        try:
            import collector_automation
            ca = collector_automation.get_collector_automation()
            ca_status = ca.get_status()
            status["collector"] = {
                "status": "running" if ca_status.get("is_running") else "idle",
                "running": ca_status.get("is_running", False),
                "current_task": ca_status.get("current_task", {}).get("id") if ca_status.get("current_task") else None,
                "state": ca_status.get("state", "unknown"),
            }
        except Exception as e:
            status["collector"] = {"status": "unknown", "error": str(e)}

        # AI 状态来自唯一 Gateway 的服务观测。ai_analyzer 只代表确定性分析
        # 模块可导入，不能代表任何模型服务已绑定。
        try:
            from lumenis.system.ai_gateway import core, user_api_adapter

            gateway = (user_api_adapter.status() if user_api_adapter.is_selected()
                       else core.owned_service_observation())
            if not isinstance(gateway, dict) or type(gateway.get("available")) is not bool:
                raise RuntimeError("AI_GATEWAY_STATUS_INVALID")
            status["ai"] = {
                **gateway,
                "status": "available" if gateway["available"] else "unavailable",
            }
        except Exception:  # noqa: BLE001 - Gateway status failures must remain unavailable.
            status["ai"] = {
                "provider": "gateway",
                "available": False,
                "status": "unavailable",
                "reason": "AI_GATEWAY_STATUS_UNAVAILABLE",
            }

        try:
            from importlib import import_module

            deterministic_module = import_module("ai_analyzer")
            status["deterministic_analysis"] = {
                "status": "available", "module": deterministic_module.__name__,
            }
        except Exception:  # noqa: BLE001 - deterministic importability is also fail-closed.
            status["deterministic_analysis"] = {
                "status": "unavailable", "module": "ai_analyzer",
            }

        return _api_response(data=status, domain_id=DOMAIN_SYSTEM, product_id=PRODUCT_SYSTEM)
    except Exception as e:
        return _api_response(error=str(e), domain_id=DOMAIN_SYSTEM, product_id=PRODUCT_SYSTEM, status=500)


@system_bp.route("/runtime-workers", methods=["GET"])
def system_runtime_workers():
    """Runtime worker/task 列表，按域分组（详细视图）。

    注意：/api/system/runtime 已由 lumenis_agg_api 提供（含 runtime_by_domain 字段），
    本端点提供更详细的 worker/task 列表，统一 JSON 格式。
    读真实数据：runtime_guardian_workers（按 domain_id 分组）、runtime_guardian_dlq。
    """
    try:
        from runtime_guardian import get_guardian
        g = get_guardian("default")

        # 按域查询
        cth_tasks = g.get_tasks_by_domain(DOMAIN_CTH)
        zbmp_tasks = g.get_tasks_by_domain(DOMAIN_ZBMP)
        system_tasks = g.get_tasks_by_domain(DOMAIN_SYSTEM)

        # 全部 workers（含未分类）
        all_workers = g.list_workers()

        data = {
            "by_domain": {
                DOMAIN_CTH: {
                    "total_workers": cth_tasks["total_workers"],
                    "running": cth_tasks["running"],
                    "failed": cth_tasks["failed"],
                    "dlq_count": cth_tasks["dlq_count"],
                    "workers": [{"worker_id": w["worker_id"], "worker_name": w["worker_name"],
                                 "status": w["status"], "last_heartbeat_at": w.get("last_heartbeat_at", "")}
                                for w in cth_tasks["workers"]],
                },
                DOMAIN_ZBMP: {
                    "total_workers": zbmp_tasks["total_workers"],
                    "running": zbmp_tasks["running"],
                    "failed": zbmp_tasks["failed"],
                    "dlq_count": zbmp_tasks["dlq_count"],
                    "workers": [{"worker_id": w["worker_id"], "worker_name": w["worker_name"],
                                 "status": w["status"], "last_heartbeat_at": w.get("last_heartbeat_at", "")}
                                for w in zbmp_tasks["workers"]],
                },
                DOMAIN_SYSTEM: {
                    "total_workers": system_tasks["total_workers"],
                    "running": system_tasks["running"],
                    "failed": system_tasks["failed"],
                    "dlq_count": system_tasks["dlq_count"],
                    "workers": [{"worker_id": w["worker_id"], "worker_name": w["worker_name"],
                                 "status": w["status"], "last_heartbeat_at": w.get("last_heartbeat_at", "")}
                                for w in system_tasks["workers"]],
                },
            },
            "total_workers_all": len(all_workers),
            "guardian_health": g.health_check().get("overall", "unknown"),
        }

        return _api_response(data=data, domain_id=DOMAIN_SYSTEM, product_id=PRODUCT_SYSTEM)
    except Exception as e:
        return _api_response(error=str(e), domain_id=DOMAIN_SYSTEM, product_id=PRODUCT_SYSTEM, status=500)


@system_bp.route("/domains", methods=["GET"])
def system_domains():
    """域隔离总览：调用 domain_isolation.domain_summary()。

    返回所有域的边界定义、当前域上下文、隔离资源/共享资源。
    """
    try:
        summary = domain_summary()
        # 补充各域 worker 数量
        try:
            from runtime_guardian import get_guardian
            g = get_guardian("default")
            for did in (DOMAIN_CTH, DOMAIN_ZBMP, DOMAIN_SYSTEM):
                tasks = g.get_tasks_by_domain(did)
                if did in summary.get("domains", {}):
                    summary["domains"][did]["runtime_workers"] = tasks["total_workers"]
                    summary["domains"][did]["running_workers"] = tasks["running"]
        except Exception:
            pass

        return _api_response(data=summary, domain_id=DOMAIN_SYSTEM, product_id=PRODUCT_SYSTEM)
    except Exception as e:
        return _api_response(error=str(e), domain_id=DOMAIN_SYSTEM, product_id=PRODUCT_SYSTEM, status=500)


# ---------------------------------------------------------------------------
# 注册函数（供 app.py 调用）
# ---------------------------------------------------------------------------
def register_dual_domain_api(app):
    """注册三个双域 API 蓝图到 Flask app。

    用法（在 app.py 中）：
        from api_dual_domain import register_dual_domain_api
        register_dual_domain_api(app)
    """
    app.register_blueprint(zbmp_bp)
    app.register_blueprint(cth_bp)
    app.register_blueprint(system_bp)
    print("[dual-domain] API blueprints registered: /api/zbmp, /api/cth, /api/system")
    return app
