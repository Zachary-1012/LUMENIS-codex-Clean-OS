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
    if operation not in {"read", "prepare", "choose", "adopt", "cancel", "interrupt", "resume", "action", "outcome", "outcome_unknown", "evaluate", "review", "restore"}:
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
    DOMAIN_ANALYSIS_VERSION = "cth-bmp-domain-analysis/1"
    QUESTION_ANALYSIS_VERSION = "cth-bmp-domain-analysis/2"
    CURRENT_ANALYSIS_VERSION = "cth-bmp-domain-analysis/3"
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
            if (row["version"] not in {self.VERSION, self.ACTION_VERSION, self.REVISION_VERSION} or row["source"] != "cth_bmp_business"
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
                    origin = (inputs if inputs.get("operation") in {"prepare", "adopt"}
                              else self._active_origin(history)["inputs"])
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
                if row["version"] == self.REVISION_VERSION:
                    adoption = outputs.get("adoption")
                    if not isinstance(adoption, dict):
                        raise RuntimeError("BUSINESS_WORK_ADOPTION_BINDING_INVALID")
                    if inputs.get("operation") == "adopt":
                        if (not history or action is not None
                                or adoption.get("parent_revision") != previous
                                or adoption.get("reason") != inputs["payload"].get("reason")
                                or adoption.get("source_job_id") != inputs["payload"].get("source_job_id")
                                or outputs.get("outcome_state") != "NOT_OBSERVED"):
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
                    version=self.REVISION_VERSION if outputs.get("adoption") else (
                        self.ACTION_VERSION if (outputs.get("action") or "resource_constraints" in (outputs.get("decision") or {})) else self.VERSION),
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
        if (state == "CANCELLED" and operation != "restore") or (state == "OUTCOME_RECORDED" and operation not in {"action", "adopt", "review"}):
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
                return {"state": "DECIDED" if selection else "PREPARED" if options else "NOT_READY",
                        "options": options, "decision": selection, "source_report_hash": report["row"]["artifact_hash"],
                        "source_body_bindings": self._source_bindings(connection, report, scope),
                        "hypothesis_review": report.get("hypothesis_review"),
                        "domain_analysis": analysis,
                        "case_id": history[0]["outputs"].get("case_id"),
                        "case_evidence_ref": history[0]["outputs"].get("case_evidence_ref"),
                        "resume_count": prior["resume_count"], "outcome_state": "NOT_OBSERVED",
                        "business_outcome": "NOT_OBSERVED", "action_state": "NOT_EXECUTED", "adoption": adoption}
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
            return {"state": "DECIDED", "options": options, "decision": selection, "selected_by": actor_ref,
                    "source_report_hash": report["row"]["artifact_hash"],
                    "source_body_bindings": self._source_bindings(connection, report, scope),
                    "hypothesis_review": report.get("hypothesis_review"),
                    "case_id": history[0]["outputs"].get("case_id"),
                    "case_evidence_ref": history[0]["outputs"].get("case_evidence_ref"),
                    "resume_count": prior["resume_count"], "outcome_state": "NOT_OBSERVED",
                    "business_outcome": "NOT_OBSERVED", "action_state": "NOT_EXECUTED", "adoption": adoption}
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
            refs = payload["source_ids"]
            if (not isinstance(refs, list) or not refs or any(type(ref) is not str for ref in refs)
                    or len(refs) != len(set(refs)) or not set(refs) <= available):
                raise PermissionError("BUSINESS_WORK_REVIEW_SOURCE_INVALID")
            result["operator_review"] = {**payload, "reviewer": actor_ref,
                "reviewed_revision": history[-1]["evidence_ref"],
                "outcome_revision": next(e["evidence_ref"] for e in reversed(history)
                                         if e["inputs"]["operation"] in {"outcome", "outcome_unknown"}),
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
                  "action": {"option_id", "task_id"}, "outcome_unknown": {"limits"},
                  "outcome": {"source_job_id", "source_id", "quote", "limits"}}
        if operation not in fields or not isinstance(payload, dict):
            raise ValueError("BUSINESS_WORK_OPERATION_PAYLOAD_INVALID")
        if operation == "choose":
            allowed = (fields[operation], fields[operation] | {"resource_constraints"})
        elif operation == "adopt":
            allowed = (fields[operation], fields[operation] | {"planning_constraints"})
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
        if value is None:
            return {}
        if not isinstance(value, dict) or set(value) - {"time_range", "resource_constraints"}:
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
        return result

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
                   + ("业务材料角色仍缺：" + "、".join(missing) + "。" if missing else "所需角色已有捕获标注，仍需核对原文。"),
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
                                 f"{cohort['subject_id'] or cohort['brand_focus_id'] or '无焦点来源'}："
                                 f"{cohort['source_count']}条发布样本，已知互动组件{q['known_field_count']}/{q['expected_field_count']}，"
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
        if not answers:
            answer("BUSINESS_QUESTION", "UNAVAILABLE", "当前问题缺少可匹配的获准分析输入。", [], limits,
                   "明确需要核对的运营、反馈、品牌或传播问题，提供对象/期间及获准材料，继续同一任务。")
        if manual is None and options:
            result["reason"] = None
            result["state"] = "RESEARCH_ACTIONS_PROPOSED"
        report = {"state": "UNAVAILABLE" if not verified_ids or all(item["state"] == "UNAVAILABLE" for item in answers) else
                  "AVAILABLE" if all(item["state"] == "AVAILABLE" for item in answers) else "PARTIAL",
                  "answers": answers, "canonical_inputs": inputs, "cohorts": cohorts, "period": period,
                  "limitations": limits, "next_actions": [item["next_action"] for item in answers],
                  "business_outcome": "NOT_OBSERVED", "causation": "NOT_ESTABLISHED",
                  "metric_input_claim": "IMMUTABLE_CANONICAL_SNAPSHOT_NOT_NEW_EXTERNAL_FACT"}
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
        outcome = outputs.get("outcome")
        if not outcome:
            return
        body = self._canonical_source(connection, outcome["source_id"], scope)["content"] or ""
        if (hashlib.sha256(body.encode()).hexdigest() != outcome["body_sha256"]
                or outcome["quote"] not in body):
            raise RuntimeError("BUSINESS_WORK_OUTCOME_SOURCE_CHANGED")
        report = self._report(connection, outcome["source_job_id"], actor_ref, scope)
        if report["row"]["artifact_hash"] != outcome["report_hash"]:
            raise RuntimeError("BUSINESS_WORK_OUTCOME_SOURCE_CHANGED")

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
        result = {"version": self.REVISION_VERSION if current["outputs"].get("adoption") else (
                  self.ACTION_VERSION if (current["outputs"].get("action") or
                                         "resource_constraints" in (current["outputs"].get("decision") or {})) else self.VERSION),
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
        result["usable_result"] = self.render_result(result)
        # Shared read/use permissions may change during rendering independently
        # of this domain's report permission. Reconcile all linked versions again.
        if action_read["state"] == "FRESH_OWNER_VERIFIED":
            self._verify_actions(active_history, actor_ref, scope, authorize)
        self._authorize(authorize, actor_ref, scope, "read")
        return result

    def _saved_result_args(self, connection, work, *, actor_ref, scope, request_id,
                           citations, previous_artifact_id, expected_draft_digest):
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
        required_sources = {source for option in work["options"] for source in option["source_ids"]}
        if work.get("outcome"):
            required_sources.add(work["outcome"]["source_id"])
        records = list(work["source_brief"]["records"])
        if work.get("outcome"):
            outcome_report = self._report(connection, work["outcome"]["source_job_id"], actor_ref, scope)
            records += outcome_report["source_brief"]["records"]
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
        for key in ("adoption", "action", "outcome", "outcome_unknown", "case_id", "case_evidence_ref",
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
        return {"title": snapshot_scope["entity_label"][:120] + " · " + work["question"][:160],
                "markdown": markdown, "kind": "report", "payload": payload,
                "citations": citations, "request_id": request_id,
                "work_id": "WORK-" + hashlib.sha256(self._json([actor_ref, identity_scope, work["work_id"]]).encode()).hexdigest()[:24],
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
                                             expected_draft_digest=expected_draft_digest)
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
        from lumenis.shared.reporting.operational_brief import _markdown_text, _source_url
        text = _markdown_text
        lines = ["# " + text(work["scope"]["entity_label"]) + " · 工作决策记录", "",
                 text(work["question"]), "", "## 可比较的人工提案（不是已核实事实）", ""]
        analysis = work.get("domain_analysis")
        question_result = (analysis or {}).get("question_result")
        if analysis is not None:
            lines[0] = "# " + text(work["scope"]["entity_label"]) + " · 业务分析与决策报告"
            if question_result and question_result.get("generation") == "SYSTEM_DERIVED_RECOMMENDATIONS":
                lines[4] = "## 来源支持的研究建议（待用户确认）"
            if question_result:
                lines += ["## 本次问题分析", "", "方法：" + text(question_result["method"]),
                          "分析状态：" + text(question_result["state"]),
                          "完整业务判断：" + text(question_result.get("full_business_answer", "NOT_ESTABLISHED"))]
                business = question_result.get("business_report")
                if isinstance(business, dict):
                    states = {"AVAILABLE": "已得到限定结果", "PARTIAL": "部分可回答", "UNAVAILABLE": "缺少必要输入"}
                    for answer in business.get("answers", []):
                        lines += ["### " + states.get(answer["state"], "未完成"),
                                  text(answer["summary"]), "下一步：" + text(answer["next_action"])]
                        lines += [text(limit) for limit in answer.get("limitations", [])]
                    period = business.get("period", {})
                    bounds = period.get("time_range")
                    if bounds:
                        lines += ["发布样本期间：" + text(bounds["start"]) + " 至 " + text(bounds["end"]),
                                  "按原生发布时间筛选；不代表期间内发生的互动或增长。"]
                    for excluded in period.get("excluded", []):
                        lines += ["期间外或时间未知来源：" + text(excluded["source_id"])
                                  + "（" + text(excluded["reason"]) + "）；采集时间不替代发布时间。"]
                for material in question_result.get("findings", {}).get("source_materials", []):
                    lines += ["可核对来源：" + text(material["source_id"]),
                              "原来源链接：" + text(material.get("url") or "未知"),
                              "原生发布时间：" + text(material.get("published_at") or "未知"),
                              "采集时间：" + text(material.get("captured_at") or "未知"),
                              "材料角色标注：" + text(material.get("declared_role") or "UNKNOWN") + "（仍需核验原文）"]
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
                lines += ["每项建议都是独立的内部研究动作，不是可比商业策略；AI、业务结果和因果均未被伪造。", ""]
            lines += ["## 分析口径与限制", "", text(analysis["judgment"]["conclusion"])]
            for limitation in analysis.get("limitations", []):
                lines.append(text(limitation))
            if question_result is None:
                metrics = analysis["metric_snapshot"]
                total = metrics["total_engagement_complete_sources"]
                lines += ["完整互动字段的来源：" + str(metrics["complete_engagement_source_count"]),
                          "字段合计：" + (str(total) if total is not None else "未知（没有完整输入）"),
                          "互动不是总体需求、销量或投放回报。"]
        lines += ["## 本任务材料与缺口", "", text(work["material_review"]["state"])]
        for check in work["material_review"]["checks"]:
            lines += [text(check["check"]) + "：" + text(check["state"])]
        lines += ["材料角色仅为捕获时标注，仍须核对原文、范围、时效与权利；官网自述不代表消费者意见。", ""]
        lines += ["## 可复查来源", ""]
        for source in work["material_review"]["sources"]:
            source_url, url_state = _source_url(source.get("url"))
            lines += ["来源：" + text(source["source_id"]),
                      "出处：" + text(source_url or ("多个研究出处，详见下列逐字段引用" if source.get("profile_research") else "已隐去（地址含未经批准的参数或凭据）" if url_state == "WITHHELD" else "未知")),
                      "捕获时间：" + text(source.get("captured_at") or "未知"),
                      "发布时间：" + text(source.get("published_at") or "未知（不能以捕获时间替代）"),
                      "材料角色标注：" + text(source["declared_role"]) + "（仍需原文核验）",
                      "商业使用许可：" + text(source.get("commercial_reuse") or "UNKNOWN"),
                      "范围证据：" + text(source["scope_evidence_ref"])]
            research = source.get("profile_research")
            if research:
                lines += ["研究汇编多出处（签名不等于事实验证；捕获方式为工具文本提取）："]
                for reference in research["references"]:
                    lines += [text(reference["source_id"]) + "：" + text(reference["url"] or reference["url_state"]),
                              "来源时点：" + text(reference["source_as_of"] or "UNKNOWN") + "；" + text(reference["temporal_scope_note"] or "当前有效性未核实")]
                for assertion in research["assertions"]:
                    selected = research["review"].get(assertion["field"]) == assertion["id"]
                    lines += [text(assertion["field"]) + "：" + text(str(assertion["value"])) +
                              "；来源 " + text(assertion["source_id"]) +
                              ("；人工选择（仍非独立验真）" if selected else "；未采纳来源断言")]
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
        if work.get("adoption"):
            adoption = work["adoption"]
            lines += ["", "## 已明确采用的修订", "采用理由：" + text(adoption["reason"]),
                      "上一业务版本：" + text(adoption["parent_revision"]),
                      "修改方案：" + text("、".join(adoption["changed_option_ids"]) or "无"),
                      "保持方案：" + text("、".join(adoption["unchanged_option_ids"]) or "无"),
                      "制作成果需要明确采用本版本；未记录引用的其他影响仍未核实。"]
            if adoption["previous_action_ref"]:
                lines += ["上一版本已执行内部制作的回执：" + text(adoption["previous_action_ref"]),
                          "既有制作事实与历史评价保留；本次修改尚未重新执行或产生新的业务效果。"]
        review = work.get("operator_review")
        if review:
            lines += ["", "## 人工效果复核（不是增长事实或执行授权）",
                      "复核版本：" + text(review["reviewed_revision"]),
                      "复核人：" + text(review["reviewer"]),
                      "评价：" + text(review["assessment"]), text(review["observations"]),
                      "限制：" + text("；".join(review["limitations"])),
                      "建议下一步：" + text(review["next_step"]),
                      "反馈来源：" + text("、".join(review["source_ids"])),
                      "评价是人工意见；实际收益和因果仍未验证。"]
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
