"""Persist Reporting delivery preferences in the existing Artifact owner.

Notifications are a read-only projection of saved work through agent_focus.
This module sends no messages, creates no notification DB and claims no App
push/mobile delivery. W6/F bind the projection to their existing surfaces.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from agent_focus.notification import FocusProtector, NotificationEvent, NotificationLevel, NotificationRouter
from agent_focus.policy import FocusPolicy, QuietHours
from . import saved_work as works

_DEFAULT = {"language": "zh-CN", "export_format": "json", "notifications_enabled": True,
            "quiet_hours": {"enabled": False, "start_hour": 22, "end_hour": 8, "timezone": "Asia/Shanghai"},
            "acknowledged_artifact_ids": [],
            "subject_directory": {"mode": "EVIDENCED_CN", "subject_ids": [],
                                  "removed_subject_ids": []}}


def _identity(actor, scope):
    context = works.authorize(actor, scope, action="read")
    return context, "WORK-" + works._digest({"owner": "reporting-delivery-preferences", "context": context})[:24]


def _validate(value):
    legacy_keys = set(_DEFAULT) - {"subject_directory"}
    if isinstance(value, dict) and set(value) == legacy_keys:
        # Existing immutable preference artifacts predate the directory
        # working-set field. Keep their notification/export values intact and
        # project the new preference with its default semantics on read.
        value = {**deepcopy(_DEFAULT), **value}
    if (not isinstance(value, dict) or set(value) != set(_DEFAULT)
            or value["language"] not in {"zh-CN", "en", "ko"}
            or value["export_format"] not in {"json", "md", "txt", "docx", "pdf", "xlsx"}
            or type(value["notifications_enabled"]) is not bool):
        raise works.SavedWorkError("DELIVERY_PREFERENCES_INVALID")
    quiet = value["quiet_hours"]
    if (not isinstance(quiet, dict) or set(quiet) != set(_DEFAULT["quiet_hours"])
            or type(quiet["enabled"]) is not bool
            or any(type(quiet[k]) is not int or not 0 <= quiet[k] <= 23 for k in ("start_hour", "end_hour"))
            or not isinstance(quiet["timezone"], str)):
        raise works.SavedWorkError("DELIVERY_QUIET_HOURS_INVALID")
    try:
        ZoneInfo(quiet["timezone"])
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise works.SavedWorkError("DELIVERY_TIMEZONE_INVALID") from exc
    acknowledged = value["acknowledged_artifact_ids"]
    if (not isinstance(acknowledged, list) or len(acknowledged) > 100
            or any(not isinstance(x, str) or not works._ID.fullmatch(x) for x in acknowledged)
            or len(set(acknowledged)) != len(acknowledged)):
        raise works.SavedWorkError("DELIVERY_ACKNOWLEDGEMENT_INVALID")
    directory = value["subject_directory"]
    if (isinstance(directory, dict) and directory.get("mode") in {"DEFAULT_ALL", "CUSTOM"}
            and set(directory) == {"mode", "subject_ids", "removed_subject_ids"}):
        # Older pre-release working-set drafts could include every registered
        # subject. Preserve explicit removals, but never promote that old
        # global default or unverified selections into the current CN directory.
        directory = {"mode": "EVIDENCED_CN", "subject_ids": [],
                     "removed_subject_ids": directory["removed_subject_ids"]}
        value = {**value, "subject_directory": directory}
    if (not isinstance(directory, dict)
            or set(directory) != {"mode", "subject_ids", "removed_subject_ids"}
            or directory["mode"] != "EVIDENCED_CN"):
        raise works.SavedWorkError("SUBJECT_DIRECTORY_PREFERENCE_INVALID")

    def valid_subject_ids(values):
        return (
            isinstance(values, list) and len(values) <= 10000
            and all(type(item) is str and item and item == item.strip()
                    and len(item) <= 256 and not any(ord(char) < 32 for char in item)
                    for item in values)
            and len(set(values)) == len(values)
        )

    selected = directory["subject_ids"]
    removed = directory["removed_subject_ids"]
    if (not valid_subject_ids(selected) or not valid_subject_ids(removed)
            or set(selected).intersection(removed)
            or selected):
        raise works.SavedWorkError("SUBJECT_DIRECTORY_PREFERENCE_INVALID")
    return deepcopy(value)


def read_preferences(*, actor: Any, scope: Mapping) -> dict:
    context, work_id = _identity(actor, scope)
    with works.get_repository().connection(read_only=True, wal=False) as con:
        versions = works._versions(con, work_id, context, actor)
    works.authorize(actor, scope, action="read")
    if not versions:
        return {"preferences": deepcopy(_DEFAULT), "persisted": False, "artifact_ref": None,
                "version": 0, "draft_digest": None, "work_id": work_id}
    item = versions[-1]
    if item["document"]["kind"] != "delivery_preferences":
        raise works.SavedWorkError("DELIVERY_PREFERENCES_CONTEXT_MISMATCH")
    return {"preferences": _validate(item["document"]["payload"]), "persisted": True,
            "artifact_ref": item["artifact"]["artifact_id"], "version": item["document"]["version"],
            "draft_digest": item["document"]["draft_digest"], "work_id": work_id}


def save_preferences(preferences: dict, *, actor: Any, scope: Mapping, request_id: str,
                     previous_artifact_id: str | None = None,
                     expected_draft_digest: str | None = None) -> dict:
    _, work_id = _identity(actor, scope)
    value = _validate(preferences)
    for ref in value["acknowledged_artifact_ids"]:
        item = works.reopen_work(ref, actor=actor, scope=scope)
        if item["document"]["kind"] == "delivery_preferences":
            raise works.SavedWorkError("DELIVERY_ACKNOWLEDGEMENT_INVALID")
    return works.save_work(title="Reporting delivery preferences", markdown="Saved delivery preferences.",
                           kind="delivery_preferences", payload=value, citations=[], request_id=request_id,
                           actor=actor, scope=scope, work_id=work_id,
                           previous_artifact_id=previous_artifact_id,
                           expected_draft_digest=expected_draft_digest)


def notification_feed(*, actor: Any, scope: Mapping, limit: int = 30,
                      cursor: str | None = None) -> dict:
    preferences = read_preferences(actor=actor, scope=scope)
    values = preferences["preferences"]
    quiet = values["quiet_hours"]
    hour = datetime.now(ZoneInfo(quiet["timezone"])).hour
    quiet_now = QuietHours(**quiet).is_quiet_now(hour=hour)
    # Compute the configured zone in this adapter; the legacy router uses the
    # host hour. Classification/routing remains in the existing owner.
    protector = FocusProtector(FocusPolicy(quiet_hours=QuietHours(enabled=False)))
    routed = []
    router = NotificationRouter(protector, log_sink=routed.append,
                                toast_sink=routed.append, modal_sink=routed.append)
    result = works.search_work(actor=actor, scope=scope, limit=limit, cursor=cursor)
    notifications = []
    for item in result["items"]:
        artifact, doc = item["artifact"], item["document"]
        if doc["kind"] == "delivery_preferences":
            continue
        acknowledged = artifact["artifact_id"] in values["acknowledged_artifact_ids"]
        requires_action = artifact["approval_required"] == 1 and artifact["approval_status"] != "approved"
        level = (NotificationLevel.HUMAN_DECISION if requires_action else NotificationLevel.IMPORTANT_SIGNAL)
        if not requires_action and (quiet_now or not values["notifications_enabled"]):
            level = NotificationLevel.SILENT_PROGRESS
        event = NotificationEvent(event_id="saved-work:" + artifact["artifact_id"], level=level.value,
                                  title=doc["title"], message=f"Saved version {doc['version']}",
                                  source="reporting", event_type="approval_required" if requires_action else "report_ready",
                                  requires_action=requires_action,
                                  evidence_refs=[str(c["evidence_id"]) for c in doc["citations"]])
        shown = False if acknowledged else router.route(event)
        notifications.append({"event": event.to_dict(), "visible": shown, "acknowledged": acknowledged,
                              "return_ref": item["return_ref"]})
    works.authorize(actor, scope, action="read")
    return {"notifications": notifications, "preferences_ref": preferences["artifact_ref"],
            "quiet_now": quiet_now, "has_more": result["has_more"], "next_cursor": result["next_cursor"],
            "verification_complete": result["verification_complete"], "delivery": "in-product-projection"}
