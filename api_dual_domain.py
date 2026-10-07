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


def authorize_business_work_request(operation, *, actor_ref, scope):
    """Fresh server receipt for W6 composition; never accept receipt JSON."""
    from experience_runtime import _source_brief_context
    from lumenis.shared.reporting.source_brief_job import _scope_material
    from lumenis.system.security import get_permission_gate, OperationType
    if operation not in {"read", "prepare", "choose", "cancel", "interrupt", "resume", "action", "outcome", "outcome_unknown", "evaluate"}:
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
    FEATURE = "CTH_BMP_DECISION_WORK"
    KINDS = {"venue_operations", "consumer_risk", "brand_market", "creator_campaign"}

    def __init__(self, *, internal_action_reader=None, action_actor=None):
        # W6 binds the observed read_internal_pitch(task_id, *, actor, scope)
        # callable and server principal. Never load owner candidates implicitly
        # or take a reader/principal/receipt from an HTTP/model payload.
        self._internal_action_reader = internal_action_reader
        self._action_actor = action_actor

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

    def _report(self, connection, job_id, actor_ref, scope):
        from lumenis.shared.reporting.source_brief_job import _verify_report
        row = connection.execute(
            "SELECT * FROM daily_reports WHERE report_id=? ORDER BY id DESC LIMIT 1", (job_id,),
        ).fetchone()
        if row is None:
            raise LookupError("BUSINESS_WORK_SOURCE_REPORT_NOT_FOUND")
        verified = _verify_report(dict(row), job_id=job_id, actor_id=actor_ref, expected_scope=scope)
        import canonical_data
        for source in verified["source_brief"]["records"]:
            record = self._canonical_source(connection, source["source_id"], scope)
            if str(record["scope_evidence_ref"]) != str(source["scope_evidence_ref"]):
                raise PermissionError("BUSINESS_WORK_SOURCE_LINEAGE_CHANGED")
            canonical_data._validate_canonical_scope(connection, canonical_data.CanonicalRecord(
                source_id=source["source_id"], product_id=scope["product_id"], domain_id=scope["domain_id"],
                subject_id=scope.get("subject_id"), brand_focus_id=scope.get("brand_focus_id"),
                scope_status="VERIFIED", scope_evidence_ref=str(source["scope_evidence_ref"])))
        return verified

    @staticmethod
    def _canonical_source(connection, source_id, scope):
        rows = connection.execute(
            "SELECT * FROM canonical_data WHERE source_id=? AND product_id=? AND domain_id=? "
            "AND COALESCE(subject_id,'')=? AND COALESCE(brand_focus_id,'')=? AND scope_status='VERIFIED'",
            (source_id, scope["product_id"], scope["domain_id"], scope.get("subject_id") or "", scope.get("brand_focus_id") or ""),
        ).fetchall()
        if len(rows) != 1:
            raise PermissionError("BUSINESS_WORK_SOURCE_SCOPE_INVALID")
        return dict(rows[0])

    def _bound_report(self, connection, history, actor_ref, scope):
        report = self._report(connection, history[0]["inputs"]["payload"]["source_job_id"], actor_ref, scope)
        if report["row"]["artifact_hash"] != history[0]["outputs"]["source_report_hash"]:
            raise RuntimeError("BUSINESS_WORK_SOURCE_REPORT_CHANGED")
        case_id = history[0]["inputs"]["payload"].get("case_id")
        if case_id:
            case = self._case(connection, case_id, actor_ref, scope)
            if (case["source_job_id"] != report["snapshot"]["job_id"]
                    or case["creation_evidence_ref"] != history[0]["outputs"].get("case_evidence_ref")):
                raise RuntimeError("BUSINESS_WORK_CASE_BINDING_CHANGED")
        return report

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
            if inputs.get("actor_ref") != actor_ref or inputs.get("scope") != scope:
                raise PermissionError("BUSINESS_WORK_CONTEXT_MISMATCH")
            if (row["version"] not in {self.VERSION, self.ACTION_VERSION} or row["source"] != "cth_bmp_business"
                    or row["product_id"] != scope["product_id"] or row["domain_id"] != scope["domain_id"]
                    or row["status"] != "derived" or row["result"] != "RECORDED"
                    or inputs.get("_lumenis_scope") != _expected_scope_marker(scope)
                    or inputs.get("parent_ref") != previous or inputs.get("work_id") != work_id
                    or inputs.get("submission_id") != row["test_name"]):
                raise RuntimeError("BUSINESS_WORK_BINDING_INVALID")
            if row["version"] == self.VERSION:
                if outputs.get("action_state") != "NOT_EXECUTED" or outputs.get("action") is not None:
                    raise RuntimeError("BUSINESS_WORK_BINDING_INVALID")
            else:
                action = outputs.get("action")
                if outputs.get("action_state") != ("EXECUTED" if action else "NOT_EXECUTED"):
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
            evidence_ref = f"app_evidence_records:{row['id']}"
            history.append({"inputs": inputs, "outputs": outputs, "evidence_ref": evidence_ref})
            previous = evidence_ref
        return history

    def _options(self, options, source_ids):
        if not isinstance(options, list) or not 2 <= len(options) <= 4:
            raise ValueError("BUSINESS_WORK_COMPARABLE_OPTIONS_REQUIRED")
        result = []
        for option in options:
            if not isinstance(option, dict) or set(option) != {"option_id", "proposal", "rationale", "source_ids", "assumptions", "unknowns", "check"}:
                raise ValueError("BUSINESS_WORK_OPTION_INVALID")
            for key in ("option_id", "proposal", "rationale", "check"):
                self._text(option[key], 80 if key == "option_id" else 1500)
            refs = option["source_ids"]
            if (not isinstance(refs, list) or not refs or any(type(s) is not str for s in refs)
                    or len(refs) != len(set(refs)) or not set(refs) <= source_ids):
                raise PermissionError("BUSINESS_WORK_OPTION_SOURCE_INVALID")
            for key in ("assumptions", "unknowns"):
                if not isinstance(option[key], list) or not 1 <= len(option[key]) <= 8:
                    raise ValueError("BUSINESS_WORK_LIMITS_REQUIRED")
                for text in option[key]:
                    self._text(text)
            result.append({**option, "claim_type": "OPERATOR_PROPOSAL", "causation": "NOT_ESTABLISHED"})
        if len({item["option_id"] for item in result}) != len(result):
            raise ValueError("BUSINESS_WORK_OPTION_ID_DUPLICATE")
        return result

    def _append(self, *, actor_ref, scope, work_id, submission_id, operation,
                payload, authorize, expected_revision=None):
        import re
        from lumenis.shared.evidence import store
        if not isinstance(submission_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", submission_id):
            raise ValueError("BUSINESS_WORK_SUBMISSION_INVALID")
        self._authorize(authorize, actor_ref, scope, operation)
        with get_repository().transaction(timeout=10) as connection:
            connection.execute("BEGIN IMMEDIATE")
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
                    version=self.ACTION_VERSION if (outputs.get("action") or "resource_constraints" in (outputs.get("decision") or {})) else self.VERSION,
                    status="derived", result="RECORDED",
                    inputs=inputs, outputs=outputs,
                )
                if type(ref) is not int or ref < 1:
                    raise RuntimeError("BUSINESS_WORK_EVIDENCE_WRITE_FAILED")
                history = self._history(connection, work_id, actor_ref, scope)
            # Every replay validates its original report and still-visible source chain.
            self._bound_report(connection, history, actor_ref, scope)
            action_read = self._verify_actions(history, actor_ref, scope, authorize)
            if any(e["inputs"]["operation"] == "action" for e in history):
                if action_read["state"] != "FRESH_OWNER_VERIFIED":
                    raise RuntimeError("BUSINESS_WORK_ACTION_OWNER_NOT_BOUND")
                self._authorize(authorize, actor_ref, scope, operation)
        if history[-1]["outputs"]["state"] == "OUTCOME_RECORDED":
            # Evaluation is a recoverable derivative side-write. Replay retains
            # the signed outcome and repairs its exact deterministic evaluation.
            from lumenis.shared.evaluation.recorder import record_evaluation
            import hashlib
            self._authorize(authorize, actor_ref, scope, "evaluate")
            record_evaluation(
                dimension="report", metric_name="business_decision_usefulness",
                metric_value=None, pass_threshold=1.0, warn_threshold=0.8,
                source="cth_bmp_business", evidence_ref=history[-1]["evidence_ref"],
                evaluation_id=hashlib.sha256((work_id + history[-1]["evidence_ref"]).encode()).hexdigest(),
                metadata=self._evaluation_metadata(work_id, history[-1], actor_ref, scope),
            )
        return self.reopen(work_id, actor_ref=actor_ref, scope=scope, authorize=authorize)

    @staticmethod
    def _evaluation_metadata(work_id, event, actor_ref, scope):
        outputs = event["outputs"]
        metadata = {"work_id": work_id, "actor_ref": actor_ref, "scope": scope,
                    "outcome_state": outputs["outcome_state"], "causation": "NOT_ESTABLISHED",
                    "action_state": outputs["action_state"]}
        if outputs.get("action"):
            metadata["action"] = outputs["action"]
            metadata["business_outcome"] = outputs["business_outcome"]
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
            options = self._options(payload["options"], selected)
            return {"state": "PREPARED", "options": options, "decision": None,
                    "source_report_hash": report["row"]["artifact_hash"],
                    "case_id": payload.get("case_id"),
                    "case_evidence_ref": case["creation_evidence_ref"] if case else None,
                    "resume_count": 0, "outcome_state": "NOT_OBSERVED", "business_outcome": "NOT_OBSERVED",
                    "action_state": "NOT_EXECUTED"}
        if not history:
            raise LookupError("BUSINESS_WORK_NOT_FOUND")
        original = history[0]["inputs"]["payload"]
        self._bound_report(connection, history, actor_ref, scope)
        prior = history[-1]["outputs"]
        state = prior["state"]
        if state == "CANCELLED" or (state == "OUTCOME_RECORDED" and operation != "action"):
            raise RuntimeError("BUSINESS_WORK_TERMINAL")
        result = dict(prior)
        if operation == "choose":
            if state not in {"PREPARED", "DECIDED"} or payload["option_id"] not in {o["option_id"] for o in prior["options"]}:
                raise ValueError("BUSINESS_WORK_DECISION_INVALID")
            self._text(payload["reason"])
            self._text(payload["owner"])
            self._text(payload["review_at"], 80)
            from datetime import datetime
            when = datetime.fromisoformat(payload["review_at"].replace("Z", "+00:00"))
            if when.tzinfo is None:
                raise ValueError("BUSINESS_WORK_REVIEW_TIMEZONE_REQUIRED")
            result.update(state="DECIDED", decision={**payload, "approval": "INTERNAL_SELECTION_ONLY"})
            if "resource_constraints" in payload:
                result["decision"]["resource_constraints"] = self._resources(payload["resource_constraints"])
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
            body = self._canonical_source(connection, payload["source_id"], scope)["content"] or ""
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

    def prepare(self, *, actor_ref, scope, submission_id, source_job_id, kind, question, options, authorize):
        import hashlib
        self._text(actor_ref, 256)
        work_id = "work-" + hashlib.sha256(self._json([actor_ref, scope, submission_id]).encode()).hexdigest()
        return self._append(actor_ref=actor_ref, scope=scope, work_id=work_id,
                            submission_id=submission_id, operation="prepare", authorize=authorize,
                            payload={"source_job_id": source_job_id, "kind": kind, "question": question, "options": options})

    def prepare_from_case(self, case_id, *, actor_ref, scope, submission_id, kind, options, authorize):
        """Continue the existing signed CTH Case without replacing its owner."""
        import hashlib
        self._authorize(authorize, actor_ref, scope, "read")
        with get_repository().connection(read_only=True, wal=False) as connection:
            case = self._case(connection, case_id, actor_ref, scope)
        work_id = "work-" + hashlib.sha256(self._json([actor_ref, scope, submission_id]).encode()).hexdigest()
        return self._append(actor_ref=actor_ref, scope=scope, work_id=work_id,
                            submission_id=submission_id, operation="prepare", authorize=authorize,
                            payload={"source_job_id": case["source_job_id"], "kind": kind,
                                     "question": case["question"], "options": options, "case_id": case_id})

    def advance(self, work_id, *, actor_ref, scope, submission_id, operation, payload, expected_revision, authorize):
        fields = {"choose": {"option_id", "reason", "owner", "review_at"},
                  "cancel": {"reason"}, "interrupt": {"reason"}, "resume": set(),
                  "action": {"option_id", "task_id"}, "outcome_unknown": {"limits"},
                  "outcome": {"source_job_id", "source_id", "quote", "limits"}}
        if (operation not in fields or not isinstance(payload, dict)
                or set(payload) not in (fields[operation], fields[operation] | {"resource_constraints"})
                or ("resource_constraints" in payload and operation != "choose")):
            raise ValueError("BUSINESS_WORK_OPERATION_PAYLOAD_INVALID")
        return self._append(work_id=work_id, actor_ref=actor_ref, scope=scope,
                            submission_id=submission_id, operation=operation, payload=payload,
                            expected_revision=expected_revision, authorize=authorize)

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
            fields = {key: record.get("engagement_" + key) if type(record.get("engagement_" + key)) is int and record["engagement_" + key] >= 0 else None
                      for key in ("likes", "comments", "collects", "shares")}
            # Use the sole metric owner only when every component was measured.
            from canonical_metrics import engagement_of
            complete = all(value is not None for value in fields.values())
            sources.append({"source_id": source["source_id"], "scope_evidence_ref": ref,
                            "url": record.get("url"), "declared_role": role,
                            "role_status": "CAPTURE_ANNOTATION_ONLY",
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
        return {"state": "INSUFFICIENT_MATERIAL" if any(c["state"] == "MISSING_MATERIAL" for c in checks)
                else "MATERIAL_REVIEW_REQUIRED", "checks": checks, "sources": sources,
                "consumer_conclusion": "NOT_ESTABLISHED", "causation": "NOT_ESTABLISHED",
                "commercial_readiness": "NOT_VERIFIED", "collection_triggered": False}

    def reopen(self, work_id, *, actor_ref, scope, authorize):
        self._authorize(authorize, actor_ref, scope, "read")
        with get_repository().connection(read_only=True, wal=False) as connection:
            connection.execute("BEGIN")
            history = self._history(connection, work_id, actor_ref, scope)
            if not history:
                raise LookupError("BUSINESS_WORK_NOT_FOUND")
            original = history[0]["inputs"]["payload"]
            report = self._bound_report(connection, history, actor_ref, scope)
            current = history[-1]
            material_review = self._material_review(connection, report, scope, original["kind"])
            if current["outputs"].get("outcome"):
                import hashlib
                outcome = current["outputs"]["outcome"]
                outcome_report = self._report(connection, outcome["source_job_id"], actor_ref, scope)
                body = self._canonical_source(connection, outcome["source_id"], scope)["content"] or ""
                if (outcome_report["row"]["artifact_hash"] != outcome["report_hash"]
                        or hashlib.sha256(body.encode()).hexdigest() != outcome["body_sha256"]
                        or outcome["quote"] not in body):
                    raise RuntimeError("BUSINESS_WORK_OUTCOME_SOURCE_CHANGED")
        action_read = self._verify_actions(history, actor_ref, scope, authorize)
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
                        or metadata.get("actor_ref") != actor_ref or metadata.get("scope") != scope):
                    raise RuntimeError("BUSINESS_WORK_EVALUATION_BINDING_INVALID")
                if metadata != self._evaluation_metadata(work_id, current, actor_ref, scope):
                    raise RuntimeError("BUSINESS_WORK_EVALUATION_BINDING_INVALID")
                evaluation.update(state="RECORDED", evaluation_id=evaluation_id)
        result = {"version": self.ACTION_VERSION if (current["outputs"].get("action") or
                                                     "resource_constraints" in (current["outputs"].get("decision") or {})) else self.VERSION,
                "work_id": work_id, "scope": scope,
                "revision": current["evidence_ref"], **current["outputs"], "action_read": action_read,
                "action_service": {"state": "BOUND_READER"} if callable(self._internal_action_reader) and self._action_actor is not None
                                  else {"state": "UNAVAILABLE", "reason": "ACTION_OWNER_NOT_BOUND"},
                "question": original["question"], "kind": original["kind"],
                "source_report": {"job_id": original["source_job_id"], "artifact_hash": report["row"]["artifact_hash"]},
                "source_brief": report["source_brief"], "multimodal": report["snapshot"]["multimodal"],
                "material_review": material_review,
                "owned_analysis": {"state": "UNAVAILABLE", "reason": "OWNED_RUNTIME_NOT_BOUND"},
                "timeline": [{"operation": e["inputs"]["operation"], "evidence_ref": e["evidence_ref"]} for e in history],
                "return_context": {"product_id": scope["product_id"], "global": True,
                                   "subject_id": None, "brand_focus_id": None},
                "evaluation": evaluation}
        result["usable_result"] = self.render_result(result)
        # Shared read/use permissions may change during rendering independently
        # of this domain's report permission. Reconcile all linked versions again.
        if action_read["state"] == "FRESH_OWNER_VERIFIED":
            self._verify_actions(history, actor_ref, scope, authorize)
        self._authorize(authorize, actor_ref, scope, "read")
        return result

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
                report = self._report(connection, job_id, actor_ref, original)
                contexts.append({"job_id": job_id, "artifact_hash": report["row"]["artifact_hash"],
                                 "original_scope": original, "task_focus_scope": scope, "purpose": purpose,
                                 "relationship_state": "OPERATOR_CONTEXT_REQUEST_NOT_VERIFIED_RELATION",
                                 "source_brief": report["source_brief"],
                                 "multimodal": report["snapshot"]["multimodal"],
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
        from lumenis.shared.reporting.operational_brief import _markdown_text, _source_url
        text = _markdown_text
        lines = ["# " + text(work["scope"]["entity_label"]) + " · 工作决策记录", "",
                 text(work["question"]), "", "## 可比较的人工提案（不是已核实事实）", ""]
        lines += ["## 本任务材料与缺口", "", text(work["material_review"]["state"])]
        for check in work["material_review"]["checks"]:
            lines += [text(check["check"]) + "：" + text(check["state"])]
        lines += ["材料角色仅为捕获时标注，仍须核对原文、范围、时效与权利；官网自述不代表消费者意见。", ""]
        lines += ["## 可复查来源", ""]
        for source in work["material_review"]["sources"]:
            source_url, url_state = _source_url(source.get("url"))
            lines += ["来源：" + text(source["source_id"]),
                      "出处：" + text(source_url or ("已隐去（地址含未经批准的参数或凭据）" if url_state == "WITHHELD" else "未知")),
                      "捕获时间：" + text(source.get("captured_at") or "未知"),
                      "发布时间：" + text(source.get("published_at") or "未知（不能以捕获时间替代）"),
                      "材料角色标注：" + text(source["declared_role"]) + "（仍需原文核验）",
                      "商业使用许可：" + text(source.get("commercial_reuse") or "UNKNOWN"),
                      "范围证据：" + text(source["scope_evidence_ref"])]
            metric = source["engagement"]
            lines += ["来源互动字段合计：" + (str(metric["value"]) if metric["value"] is not None else "未知（字段未齐）"),
                      "此数值仅来自来源互动字段，不代表客流、需求、销量或投放回报。", ""]
        for option in work["options"]:
            lines += ["### " + text(option["option_id"]) + " · " + text(option["proposal"]),
                      text(option["rationale"]), "来源：" + text(", ".join(option["source_ids"])),
                      "假设：" + text("；".join(option["assumptions"])),
                      "未知：" + text("；".join(option["unknowns"])), "验证与停止条件：" + text(option["check"]), ""]
        decision = work["decision"]
        lines += ["## 决策与后续工作", ""]
        if decision:
            lines += ["选择：" + text(decision["option_id"]), "理由：" + text(decision["reason"]),
                      "责任人：" + text(decision["owner"]), "复查时间：" + text(decision["review_at"])]
            resources = decision.get("resource_constraints")
            if resources:
                lines += ["预算上限（人工输入）：" + text(resources["budget_amount"] if resources["budget_amount"] is not None else "未知"),
                          "方案成本估计（人工输入）：" + text(resources["estimated_cost_amount"] if resources["estimated_cost_amount"] is not None else "未知"),
                          "币种：" + text(resources["currency"] or "未知"), "估计时点：" + text(resources["as_of"] or "未知"),
                          "预算适配：" + text(resources["budget_fit"]), "资源与停止约束：" + text("；".join(resources["limits"])),
                          "估计不代表已取得报价、已承诺采购或实际支出；超预算方案需调整。"]
        else:
            lines += ["尚未选择方案。"]
        action = work.get("action")
        if action:
            receipt = action["receipt"]
            fresh = work.get("action_read", {}).get("state") == "FRESH_OWNER_VERIFIED"
            lines += ["已记录内部文字制作（" + ("本次已向成果 owner 复查" if fresh else "本次 owner 读取未绑定，历史回执尚未重新核验") + "）。",
                      "人工关联方案：" + text(action["option_id"]), "制作 Task：" + text(receipt["task_id"]),
                      "成果：" + text(receipt["artifact_id"]) + " · 版本 " + str(receipt["version"]),
                      "父成果：" + text(receipt["parent_artifact_id"] or "首版，无父成果"),
                      "内容 hash：" + text(receipt["sha256"]), "Word hash：" + text(receipt["output"]["sha256"]),
                      "内部制作完成不代表活动已执行、内容已获商业许可或消费者效果已验证。"]
        else:
            lines += ["尚未记录已执行行动。"]
        lines += ["此记录不授予联系、发布、投放、资金或采集权限。", "",
                  "## 来源报告与结果", "", "来源报告：" + text(work["source_report"]["job_id"])]
        if work.get("outcome"):
            outcome = work["outcome"]
            lines += ["来源原文：" + text(outcome["quote"]), "限制：" + text(outcome["limits"]),
                      "这是来源报告的说法，不证明本方案的效果或因果关系。"]
        if work.get("outcome_unknown"):
            lines += ["业务效果：UNKNOWN。", "复查限制：" + text(work["outcome_unknown"]["limits"]),
                      "未观察效果不撤销已经完成的内部制作事实。"]
        elif not work.get("outcome"):
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
    offset: int = 0,
) -> Dict[str, Any]:
    """Read signed Canonical rows after fresh CTH scope authorization.

    Optional platform paging selects candidate source IDs from the existing
    Canonical table, then sends those IDs through the Canonical owner's signed
    scope validator. The candidate query grants no access and returns no rows
    directly.
    """
    if not isinstance(connection, sqlite3.Connection):
        raise CTHScopedReadError("CTH_CANONICAL_CONNECTION_INVALID", 503)
    if type(limit) is not int or not 1 <= limit <= 100:
        raise CTHScopedReadError("INVALID_CTH_READ_LIMIT", 400)
    if type(offset) is not int or offset < 0:
        raise CTHScopedReadError("INVALID_CTH_READ_OFFSET", 400)
    if source_ids is not None and (platform is not None or offset != 0):
        raise CTHScopedReadError("CTH_SOURCE_SELECTION_CONFLICT", 400)

    scope = _authorize_cth_read(connection, module=module)
    try:
        import canonical_data
        if platform is None:
            canonical = canonical_data.list_scoped_canonical(
                connection, product_id=PRODUCT_CTH,
                subject_id=scope["subject_id"], limit=limit,
                source_ids=source_ids,
            )
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
    """Read the verified ZBMP canonical slice used by API and UI.

    The function deliberately treats a missing table, no ZBMP rows, and rows
    rejected by the domain adapter as NOT_COLLECTED.  It never falls back to
    the CTH ``notes``/``web_mentions`` tables and never fills missing metrics
    with fabricated zeros.
    """
    from canonical_data import PRODUCT_ZBMP

    snapshot: Dict[str, Any] = {
        "data_state": "NOT_COLLECTED",
        "records": [],
        "canonical_records": [],
        "brands": [],
        "total_records": 0,
        "errors": [],
        "metrics": {
            "total_notes": 0,
            "total_web_mentions": 0,
            "total_canonical_zbmp": 0,
            "total_engagement": {
                "likes": None, "comments": None, "collects": None, "shares": None,
            },
            "sentiment_distribution": {},
            "risk_distribution": {},
            "platform_distribution": {},
            "latest_capture": "",
            "capture_trend": {"labels": [], "total": [], "negative": []},
        },
    }

    conn = None
    try:
        conn = _get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM canonical_data "
                "WHERE product_id = ? AND domain_id = ? "
                "ORDER BY captured_at DESC",
                (PRODUCT_ZBMP, DOMAIN_ZBMP),
            ).fetchall()
        except sqlite3.Error as exc:
            # A missing canonical table means the domain has not collected
            # data; it is not an API failure and must not trigger table writes.
            snapshot["errors"].append(f"canonical_data unavailable: {exc}")
            return snapshot

        adapter = get_adapter(DOMAIN_ZBMP)
        safe_records = []
        rejected = 0
        for row in rows:
            safe = _safe_zbmp_record(row, adapter)
            if safe is None:
                rejected += 1
                continue
            safe_records.append(safe)

        if rejected:
            snapshot["errors"].append(f"rejected_domain_records={rejected}")

        snapshot["records"] = safe_records
        snapshot["canonical_records"] = safe_records[:200]
        snapshot["total_records"] = len(safe_records)
        snapshot["brands"] = _build_zbmp_brands(safe_records)
        if not safe_records:
            return snapshot

        metrics = snapshot["metrics"]
        metrics["total_canonical_zbmp"] = len(safe_records)
        metrics["total_notes"] = sum(
            1 for record in safe_records
            if record.get("source_type") in ("note", "collected_note")
        )
        metrics["total_web_mentions"] = sum(
            1 for record in safe_records if record.get("source_type") == "web_mention"
        )
        for field_name, output_name in (
            ("engagement_likes", "likes"),
            ("engagement_comments", "comments"),
            ("engagement_collects", "collects"),
            ("engagement_shares", "shares"),
        ):
            metrics["total_engagement"][output_name] = _sum_optional(
                [record.get(field_name) for record in safe_records]
            )

        for record in safe_records:
            platform = str(record.get("source_platform") or "unknown")
            metrics["platform_distribution"][platform] = (
                metrics["platform_distribution"].get(platform, 0) + 1
            )
            sentiment = str(record.get("sentiment") or "").strip()
            if sentiment:
                metrics["sentiment_distribution"][sentiment] = (
                    metrics["sentiment_distribution"].get(sentiment, 0) + 1
                )
            risk = str(record.get("risk_level") or "").strip()
            if risk:
                metrics["risk_distribution"][risk] = (
                    metrics["risk_distribution"].get(risk, 0) + 1
                )

        captures = [str(record.get("captured_at") or "") for record in safe_records]
        captures = [value for value in captures if value]
        metrics["latest_capture"] = max(captures) if captures else ""
        metrics["capture_trend"] = _zbmp_capture_trend(safe_records)
        snapshot["data_state"] = "READY"
        return snapshot
    except Exception as exc:
        snapshot["errors"].append(str(exc))
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
            "errors": snapshot["errors"],
        }
        return _api_response(data=data, domain_id=DOMAIN_ZBMP, product_id=PRODUCT_ZBMP)
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
            "total_brands": len(snapshot["brands"]),
            "errors": snapshot["errors"],
        }
        return _api_response(data=data, domain_id=DOMAIN_ZBMP, product_id=PRODUCT_ZBMP)
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
        return _api_response(data=metrics, domain_id=DOMAIN_ZBMP, product_id=PRODUCT_ZBMP)
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

        # AI 状态（检查 ai_analyzer 是否可导入）
        try:
            import ai_analyzer
            status["ai"] = {"status": "available", "module": "ai_analyzer"}
        except Exception as e:
            status["ai"] = {"status": "unavailable", "error": str(e)}

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
