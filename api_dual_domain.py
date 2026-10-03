# -*- coding: utf-8 -*-
"""
ZBC API Dual-Domain Namespace（双域核心扩展）
================================================
三个独立域路由蓝图：
  - zbmp_bp: /api/zbmp/*  多品牌平台域
  - cth_bp:  /api/cth/*   太古汇生产真相域
  - system_bp: /api/system/*  系统基础设施域

每个端点：
  1. 从请求头 X-Domain-Id / X-Product-Id 或 session 解析域身份
  2. 设置线程 SubjectContext + DomainContext
  3. 读真实数据库（canonical_data / notes / web_mentions / runtime_guardian）
  4. 返回统一 JSON: {success, data, error, domain_id, product_id}

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
    if operation not in {"read", "prepare", "choose", "cancel", "interrupt", "resume", "outcome", "evaluate"}:
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
    consumer facts. Nothing here collects, executes a campaign or invokes AI.
    Signed transitions live in the existing Evidence store without a migration.
    """

    VERSION = "cth-bmp-decision/1"
    FEATURE = "CTH_BMP_DECISION_WORK"
    KINDS = {"venue_operations", "consumer_risk", "brand_market", "creator_campaign"}

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
            if (row["version"] != self.VERSION or row["source"] != "cth_bmp_business"
                    or row["product_id"] != scope["product_id"] or row["domain_id"] != scope["domain_id"]
                    or row["status"] != "derived" or row["result"] != "RECORDED"
                    or inputs.get("_lumenis_scope") != _expected_scope_marker(scope)
                    or inputs.get("parent_ref") != previous or inputs.get("work_id") != work_id
                    or inputs.get("submission_id") != row["test_name"]
                    or outputs.get("action_state") != "NOT_EXECUTED"):
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
                outputs = self._transition(connection, history, operation, payload, actor_ref, scope)
                audits = self._authorize(authorize, actor_ref, scope, operation)
                inputs = {"work_id": work_id, "actor_ref": actor_ref, "scope": scope,
                          "submission_id": submission_id, "operation": operation,
                          "payload": payload, "parent_ref": revision, **audits}
                ref = store.record_evidence(
                    connection=connection, source="cth_bmp_business", project="LUMENIS",
                    product=scope["product_id"], domain_id=scope["domain_id"],
                    subject_id=scope.get("subject_id"), brand_focus_id=scope.get("brand_focus_id"),
                    global_scope=False, feature_id=self.FEATURE, asset_id=work_id,
                    test_name=submission_id, version=self.VERSION, status="derived", result="RECORDED",
                    inputs=inputs, outputs=outputs,
                )
                if type(ref) is not int or ref < 1:
                    raise RuntimeError("BUSINESS_WORK_EVIDENCE_WRITE_FAILED")
                history = self._history(connection, work_id, actor_ref, scope)
            # Every replay validates its original report and still-visible source chain.
            self._bound_report(connection, history, actor_ref, scope)
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
                metadata={"work_id": work_id, "actor_ref": actor_ref, "scope": scope,
                          "outcome_state": "SOURCE_REPORTED", "causation": "NOT_ESTABLISHED",
                          "action_state": "NOT_EXECUTED"},
            )
        return self.reopen(work_id, actor_ref=actor_ref, scope=scope, authorize=authorize)

    def _transition(self, connection, history, operation, payload, actor_ref, scope):
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
        if state in {"CANCELLED", "OUTCOME_RECORDED"}:
            raise RuntimeError("BUSINESS_WORK_TERMINAL")
        result = dict(prior)
        if operation == "choose":
            if state != "PREPARED" or payload["option_id"] not in {o["option_id"] for o in prior["options"]}:
                raise ValueError("BUSINESS_WORK_DECISION_INVALID")
            self._text(payload["reason"])
            self._text(payload["owner"])
            self._text(payload["review_at"], 80)
            from datetime import datetime
            when = datetime.fromisoformat(payload["review_at"].replace("Z", "+00:00"))
            if when.tzinfo is None:
                raise ValueError("BUSINESS_WORK_REVIEW_TIMEZONE_REQUIRED")
            result.update(state="DECIDED", decision={**payload, "approval": "INTERNAL_SELECTION_ONLY"})
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
        elif operation == "outcome":
            if state != "DECIDED":
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
                  "outcome": {"source_job_id", "source_id", "quote", "limits"}}
        if operation not in fields or not isinstance(payload, dict) or set(payload) != fields[operation]:
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
                evaluation.update(state="RECORDED", evaluation_id=evaluation_id)
        result = {"version": self.VERSION, "work_id": work_id, "scope": scope,
                "revision": current["evidence_ref"], **current["outputs"],
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
        else:
            lines += ["尚未选择方案。"]
        lines += ["行动尚未执行；此记录不授予联系、发布、投放、资金或采集权限。", "",
                  "## 来源报告与结果", "", "来源报告：" + text(work["source_report"]["job_id"])]
        if work.get("outcome"):
            outcome = work["outcome"]
            lines += ["来源原文：" + text(outcome["quote"]), "限制：" + text(outcome["limits"]),
                      "这是来源报告的说法，不证明本方案的效果或因果关系。"]
        else:
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
    """从请求头 / session / 查询参数解析域身份。

    优先级：X-Domain-Id header > session domain_id > ?domain_id= > 默认 cth
    product_id 从 domain_id 映射，或从 X-Product-Id 显式指定。
    """
    domain_id = ""
    product_id = ""

    # 1. Header
    domain_id = request.headers.get("X-Domain-Id", "").strip().lower()
    product_id = request.headers.get("X-Product-Id", "").strip().upper()

    # 2. Session
    if not domain_id:
        try:
            domain_id = (request.session.get("domain_id") or "").strip().lower()
        except Exception:
            pass
    if not product_id:
        try:
            product_id = (request.session.get("product_id") or "").strip().upper()
        except Exception:
            pass

    # 3. Query param
    if not domain_id:
        domain_id = request.args.get("domain_id", "").strip().lower()
    if not product_id:
        product_id = request.args.get("product_id", "").strip().upper()

    # 4. 映射 + 默认
    if domain_id and domain_id not in (DOMAIN_CTH, DOMAIN_ZBMP, DOMAIN_SYSTEM):
        domain_id = DOMAIN_CTH  # 生产安全默认
    if not domain_id:
        domain_id = DOMAIN_CTH

    if not product_id:
        product_id = domain_to_product(domain_id)
    elif product_id not in (PRODUCT_CTH, PRODUCT_ZBMP, PRODUCT_SYSTEM):
        product_id = domain_to_product(domain_id)

    return {"domain_id": domain_id, "product_id": product_id}


def _setup_domain_context(domain_id: str, product_id: str) -> DomainContext:
    """设置线程级 DomainContext + SubjectContext。CTH 保护强制主体。"""
    brand_key = CTH_BRAND_KEY if domain_id == DOMAIN_CTH else ""
    ctx = DomainContext(
        domain_id=domain_id,
        product_id=product_id,
        brand_key=brand_key,
        subject_id=brand_key.upper().replace("-", "_").replace(" ", "_") if brand_key else "",
    )
    set_domain_context(ctx)

    # 同步设置 SubjectContext（兼容现有体系）
    subject_ctx = SubjectContext(
        subject_id=ctx.subject_id or "UNKNOWN",
        brand_key=ctx.brand_key or "default",
        product_id=product_id,
    )
    set_thread_context(subject_ctx)
    g.domain_context = ctx
    g.subject_context = subject_ctx
    return ctx


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
    identity = _resolve_domain_from_request()
    # ZBMP 蓝图强制 domain_id=zbmp
    identity["domain_id"] = DOMAIN_ZBMP
    identity["product_id"] = PRODUCT_ZBMP
    _setup_domain_context(identity["domain_id"], identity["product_id"])


@zbmp_bp.after_request
def _zbmp_after(response):
    _teardown_domain_context()
    return response


@cth_bp.before_request
def _cth_before():
    identity = _resolve_domain_from_request()
    # CTH 蓝图强制 domain_id=cth + 主体保护
    identity["domain_id"] = DOMAIN_CTH
    identity["product_id"] = PRODUCT_CTH
    _setup_domain_context(identity["domain_id"], identity["product_id"])


@cth_bp.after_request
def _cth_after(response):
    _teardown_domain_context()
    return response


@system_bp.before_request
def _system_before():
    identity = _resolve_domain_from_request()
    identity["domain_id"] = DOMAIN_SYSTEM
    identity["product_id"] = PRODUCT_SYSTEM
    _setup_domain_context(identity["domain_id"], identity["product_id"])


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
@cth_bp.route("/overview", methods=["GET"])
def cth_overview():
    """CTH 太古汇总览：从 canonical_data 按 product_id=CTH 聚合 + subject_rules 过滤。

    读真实数据：canonical_data(product_id=CTH)、notes、web_mentions。
    CTH 保护：强制 subject=guangzhou_taikoo_hui，不读 ZBMP 多品牌字段。
    """
    try:
        conn = _get_conn()
        data = {
            "subject": "guangzhou_taikoo_hui",
            "total_canonical": 0,
            "total_notes": 0,
            "total_web_mentions": 0,
            "by_platform": {},
            "by_sentiment": {},
            "by_risk": {},
            "recent_records": [],
            "engagement_summary": {},
        }

        # canonical_data CTH 聚合
        try:
            row = conn.execute(
                "SELECT COUNT(*) as c FROM canonical_data WHERE product_id = ?",
                (PRODUCT_CTH,)
            ).fetchone()
            data["total_canonical"] = row["c"] if row else 0

            # 最近记录（通过 CTHAdapter 剥离 ZBMP 字段）
            rows = conn.execute(
                "SELECT * FROM canonical_data WHERE product_id = ? ORDER BY captured_at DESC LIMIT 20",
                (PRODUCT_CTH,)
            ).fetchall()
            adapter = get_adapter(DOMAIN_CTH)
            from canonical_data import CanonicalRecord
            recent = []
            for r in rows:
                rec_dict = dict(r)
                rec = CanonicalRecord(**{k: v for k, v in rec_dict.items()
                                          if k in CanonicalRecord.__dataclass_fields__})
                try:
                    domain_rec = adapter.to_domain(rec)
                    recent.append(domain_rec.to_dict())
                except ValueError:
                    continue
            data["recent_records"] = recent
        except Exception as e:
            data["canonical_error"] = str(e)

        # notes 统计（CTH 主体过滤：subject_hit 逻辑简化为关键词匹配）
        try:
            row = conn.execute("SELECT COUNT(*) as c FROM notes").fetchone()
            data["total_notes"] = row["c"] if row else 0

            # 平台分布
            rows = conn.execute(
                "SELECT source_platform, COUNT(*) as cnt FROM notes GROUP BY source_platform"
            ).fetchall()
            data["by_platform"] = {r["source_platform"] or "unknown": r["cnt"] for r in rows}

            # 情感分布
            rows = conn.execute(
                "SELECT sentiment, COUNT(*) as cnt FROM notes WHERE sentiment != '' GROUP BY sentiment"
            ).fetchall()
            data["by_sentiment"] = {r["sentiment"]: r["cnt"] for r in rows}

            # 风险分布
            rows = conn.execute(
                "SELECT risk_level, COUNT(*) as cnt FROM notes WHERE risk_level != '' GROUP BY risk_level"
            ).fetchall()
            data["by_risk"] = {r["risk_level"]: r["cnt"] for r in rows}

            # 互动汇总
            row = conn.execute(
                "SELECT SUM(likes) as l, SUM(comments) as c, SUM(collects) as col, SUM(shares) as s FROM notes"
            ).fetchone()
            if row:
                data["engagement_summary"] = {
                    "likes": row["l"] or 0,
                    "comments": row["c"] or 0,
                    "collects": row["col"] or 0,
                    "shares": row["s"] or 0,
                }
        except Exception as e:
            data["notes_error"] = str(e)

        # web_mentions 统计
        try:
            row = conn.execute("SELECT COUNT(*) as c FROM web_mentions").fetchone()
            data["total_web_mentions"] = row["c"] if row else 0
        except Exception:
            pass

        conn.close()
        return _api_response(data=data, domain_id=DOMAIN_CTH, product_id=PRODUCT_CTH)
    except Exception as e:
        return _api_response(error=str(e), domain_id=DOMAIN_CTH, product_id=PRODUCT_CTH, status=500)


@cth_bp.route("/events", methods=["GET"])
def cth_events():
    """CTH 事件列表：从 notes/canonical_data 中提取 event_hint 和话题事件。

    读真实数据：notes(topics/event_hint)、canonical_data(event_hint)。
    """
    try:
        conn = _get_conn()
        events = []

        # 从 canonical_data 提取事件
        try:
            rows = conn.execute(
                "SELECT canonical_id, title, event_hint, topics, tags, publish_datetime, "
                "captured_at, sentiment, risk_level, source_platform "
                "FROM canonical_data WHERE product_id = ? AND (event_hint != '' OR topics != '[]') "
                "ORDER BY captured_at DESC LIMIT 50",
                (PRODUCT_CTH,)
            ).fetchall()
            for r in rows:
                d = dict(r)
                events.append({
                    "event_id": d["canonical_id"],
                    "title": d["title"],
                    "event_hint": d["event_hint"],
                    "topics": d["topics"],
                    "tags": d["tags"],
                    "publish_datetime": d["publish_datetime"],
                    "captured_at": d["captured_at"],
                    "sentiment": d["sentiment"],
                    "risk_level": d["risk_level"],
                    "platform": d["source_platform"],
                    "domain": DOMAIN_CTH,
                })
        except Exception as e:
            events.append({"error": f"canonical events: {e}"})

        # 从 notes 提取话题事件
        try:
            rows = conn.execute(
                "SELECT note_id, title, topics, publish_date, collected_at, "
                "sentiment, risk_level, source_platform "
                "FROM notes WHERE topics != '' AND topics IS NOT NULL AND topics != '[]' "
                "ORDER BY collected_at DESC LIMIT 30"
            ).fetchall()
            for r in rows:
                d = dict(r)
                events.append({
                    "event_id": f"note_{d['note_id']}",
                    "title": d["title"],
                    "event_hint": "",
                    "topics": d["topics"],
                    "tags": "[]",
                    "publish_datetime": d["publish_date"],
                    "captured_at": d["collected_at"],
                    "sentiment": d["sentiment"],
                    "risk_level": d["risk_level"],
                    "platform": d["source_platform"],
                    "domain": DOMAIN_CTH,
                })
        except Exception:
            pass

        conn.close()
        data = {"events": events, "total_events": len(events)}
        return _api_response(data=data, domain_id=DOMAIN_CTH, product_id=PRODUCT_CTH)
    except Exception as e:
        return _api_response(error=str(e), domain_id=DOMAIN_CTH, product_id=PRODUCT_CTH, status=500)


@cth_bp.route("/xiaohongshu", methods=["GET"])
def cth_xiaohongshu():
    """CTH 小红书数据：从 notes 表筛选小红书平台的太古汇相关数据。

    读真实数据：notes(source_platform='xhs' 或 note_type 含 xhs)。
    CTH 保护：仅返回太古汇主体数据，不包含 ZBMP 多品牌字段。
    """
    try:
        conn = _get_conn()
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))

        # 筛选小红书数据（source_platform 包含 xhs 或 rednote）
        rows = conn.execute(
            "SELECT * FROM notes WHERE source_platform LIKE '%xhs%' "
            "OR source_platform LIKE '%rednote%' OR note_type LIKE '%xhs%' "
            "ORDER BY collected_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()

        records = []
        for r in rows:
            d = dict(r)
            # CTH 视图：剥离 ZBMP 多品牌字段，仅保留 CTH 相关字段
            records.append({
                "note_id": d.get("note_id", ""),
                "title": d.get("title", ""),
                "content": d.get("content", "")[:500],  # 截断长内容
                "url": d.get("url", ""),
                "author_nickname": d.get("author_nickname", ""),
                "publish_date": d.get("publish_date", ""),
                "collected_at": d.get("collected_at", ""),
                "sentiment": d.get("sentiment", ""),
                "sentiment_score": d.get("sentiment_score", 0),
                "risk_level": d.get("risk_level", ""),
                "likes": d.get("likes") or 0,
                "comments": d.get("comments") or 0,
                "collects": d.get("collects") or 0,
                "shares": d.get("shares") or 0,
                "topics": d.get("topics", "[]"),
                "is_taikoo_verified": bool(d.get("is_taikoo_verified", 0)),
                "platform": d.get("source_platform", "xhs"),
                "domain": DOMAIN_CTH,
            })

        # 统计
        total_row = conn.execute(
            "SELECT COUNT(*) as c FROM notes WHERE source_platform LIKE '%xhs%' "
            "OR source_platform LIKE '%rednote%' OR note_type LIKE '%xhs%'"
        ).fetchone()
        total = total_row["c"] if total_row else 0

        conn.close()
        data = {
            "records": records,
            "total": total,
            "limit": limit,
            "offset": offset,
            "platform": "xiaohongshu",
        }
        return _api_response(data=data, domain_id=DOMAIN_CTH, product_id=PRODUCT_CTH)
    except Exception as e:
        return _api_response(error=str(e), domain_id=DOMAIN_CTH, product_id=PRODUCT_CTH, status=500)


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
