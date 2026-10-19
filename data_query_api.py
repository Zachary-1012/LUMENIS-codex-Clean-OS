# -*- coding: utf-8 -*-
"""Domain-scoped data query APIs and legacy projection adapters.

Legacy note fields remain a read projection. Access is selected by the current
domain, freshly authorized, and bound to exact IDs returned by signed Canonical.
"""
from __future__ import annotations

import database as db
import json
from flask import Blueprint, jsonify, request
from lumenis.system.collector.guard.resource_guard import ResourceGuard

_resource_guard = ResourceGuard()  # P0-G 统一资源守卫（只读决策，无共享状态）


class LegacyScopeReadError(RuntimeError):
    """A legacy projection could not bind to the current scoped Canonical owner."""

    def __init__(self, code, status=503):
        super().__init__(code)
        self.code = code
        self.status = status


def _legacy_domain_selection():
    import lumenis_app_api
    try:
        domain = lumenis_app_api._get_domain_context()
    except ValueError as exc:
        raise LegacyScopeReadError(str(exc), 400) from exc
    if domain is None:
        raise LegacyScopeReadError("DOMAIN_SELECTION_REQUIRED", 400)
    if domain != "cth":
        # The old notes table is a CTH compatibility projection. BMP has its
        # own current Canonical/BrandFocus endpoints and must never read CTH rows.
        raise LegacyScopeReadError("LEGACY_CTH_DATA_UNAVAILABLE_FOR_SELECTED_DOMAIN", 409)
    return domain


def _read_cth_canonical_page(*, module, source_type, source_table, limit=100, offset=0,
                             source_ids=None):
    _legacy_domain_selection()
    import api_dual_domain
    connection = None
    try:
        connection = api_dual_domain._get_conn()
        options = {"module": module, "limit": limit, "offset": offset}
        if source_ids is None:
            options.update({"source_type": source_type, "source_table": source_table})
        else:
            options["source_ids"] = source_ids
        return api_dual_domain.read_cth_scoped_canonical(connection, **options)
    except LegacyScopeReadError:
        raise
    except Exception as exc:
        if hasattr(exc, "code") and hasattr(exc, "status"):
            raise LegacyScopeReadError(exc.code, exc.status) from exc
        raise LegacyScopeReadError("CTH_SCOPED_CANONICAL_UNAVAILABLE", 503) from exc
    finally:
        if connection is not None:
            connection.close()


def _read_cth_canonical_snapshot(*, module, limit=100, offset=0):
    _legacy_domain_selection()
    import api_dual_domain
    connection = None
    try:
        connection = api_dual_domain._get_conn()
        return api_dual_domain.read_cth_scoped_canonical(
            connection, module=module, limit=limit, offset=offset,
        )
    except Exception as exc:
        if hasattr(exc, "code") and hasattr(exc, "status"):
            raise LegacyScopeReadError(exc.code, exc.status) from exc
        raise LegacyScopeReadError("CTH_SCOPED_CANONICAL_UNAVAILABLE", 503) from exc
    finally:
        if connection is not None:
            connection.close()


def _validate_canonical_source_row(row, *, source_type, source_table):
    source_id = row.get("source_id")
    if (row.get("product_id") != "CTH" or row.get("domain_id") != "cth"
            or row.get("scope_status") != "VERIFIED"
            or row.get("source_type") != source_type
            or row.get("source_table") != source_table
            or not isinstance(source_id, str) or not source_id or source_id != source_id.strip()
            or row.get("external_id") != source_id):
        raise LegacyScopeReadError("CANONICAL_SOURCE_MAPPING_INVALID", 503)
    try:
        raw_ref = json.loads(row.get("raw_ref") or "")
    except (TypeError, ValueError) as exc:
        raise LegacyScopeReadError("CANONICAL_SOURCE_REFERENCE_INVALID", 503) from exc
    expected_ref_id = "note_id" if source_table == "notes" else "source_id"
    if (not isinstance(raw_ref, dict) or raw_ref.get("table") != source_table
            or raw_ref.get(expected_ref_id) != source_id):
        raise LegacyScopeReadError("CANONICAL_SOURCE_REFERENCE_INVALID", 503)
    return source_id


def read_scoped_legacy_note_rows(*, module="content", filters=None, limit=100,
                                 offset=0, require_complete=False, max_sources=None,
                                 scan_all=False, include_all_projection=False):
    """Read legacy note fields only after fresh CTH scope + signed Canonical IDs.

    Normal pages walk only far enough through the legacy date-ordered candidate
    IDs to serve the requested page. Full aggregates opt into `scan_all`; no
    1,000-source ceiling can make later pages or exact IDs unreachable.
    """
    if module not in {"content", "reports"}:
        raise LegacyScopeReadError("INVALID_CTH_READ_MODULE", 400)
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise LegacyScopeReadError("INVALID_CTH_READ_LIMIT", 400)
    if type(offset) is not int or offset < 0:
        raise LegacyScopeReadError("INVALID_CTH_READ_OFFSET", 400)
    if max_sources is not None and (type(max_sources) is not int or max_sources < 1):
        raise LegacyScopeReadError("INVALID_CTH_SOURCE_SCAN_LIMIT", 400)
    normalized_filters = dict(filters or {})
    if "note_id" in normalized_filters:
        requested_note_id = normalized_filters["note_id"]
        if (type(requested_note_id) is not str or not requested_note_id
                or requested_note_id != requested_note_id.strip()
                or len(requested_note_id) > 512):
            raise LegacyScopeReadError("INVALID_NOTE_ID_FILTER", 400)
    projection_filters = dict(normalized_filters)
    # This venue-specific legacy flag is not the same fact as signed Canonical
    # scope verification. Keep the historical verified=false response empty.
    legacy_verified_false = projection_filters.get("verified") is False
    projection_filters.pop("verified", None)

    source_ids = []
    canonical_by_source_id = {}
    page_notes = []
    all_notes = []
    rejected = 0
    requested_note_id = normalized_filters.get("note_id")
    if requested_note_id is not None:
        # Exact detail lookup is sent straight to Canonical source_ids; no
        # prefix scan can hide an item that appears after the first 1,000.
        first = _read_cth_canonical_page(
            module=module, source_type="note", source_table="notes",
            limit=1, source_ids=[requested_note_id],
        )
        scope = first["scope"]
        canonical = first.get("canonical") or {}
        rows = canonical.get("records")
        if not isinstance(rows, list):
            raise LegacyScopeReadError("CTH_CANONICAL_RECORDS_UNAVAILABLE", 503)
        rejected += int(canonical.get("rejected_count", 0) or 0)
        for row in rows:
            source_id = _validate_canonical_source_row(
                row, source_type="note", source_table="notes",
            )
            if source_id != requested_note_id:
                raise LegacyScopeReadError("CANONICAL_SOURCE_ID_COLLISION", 503)
            if scope.get("subject_id") is not None and row.get("subject_id") != scope["subject_id"]:
                raise LegacyScopeReadError("CANONICAL_SUBJECT_SCOPE_MISMATCH", 503)
            source_ids.append(source_id)
            canonical_by_source_id[source_id] = row
        candidate_total = 1 if rows or rejected else 0
        projection_candidate_count = db.get_canonical_note_projection_count(scope)
        filtered_candidate_count = db.get_note_count_for_canonical_source_ids(
            source_ids, projection_filters,
        )
        source_rows_complete = (
            db.get_note_count_for_canonical_source_ids(source_ids) == len(source_ids)
        )
        if not source_rows_complete:
            rejected += 1
        truncated = bool(rejected)
        if require_complete and truncated:
            raise LegacyScopeReadError("LEGACY_NOTE_SOURCE_ROW_UNAVAILABLE", 503)
        note_rows = [] if legacy_verified_false else db.get_notes_for_canonical_source_ids(
            source_ids, projection_filters, limit=limit, offset=offset,
        )
        if include_all_projection and not legacy_verified_false:
            all_notes = db.get_notes_for_canonical_source_ids(
                source_ids, projection_filters, limit=max(1, filtered_candidate_count), offset=0,
            )
            note_rows = all_notes
        total = filtered_candidate_count if not truncated else None
    else:
        # Obtain current authorized scope and the Canonical source count before
        # consulting the legacy projection. The DB query returns IDs only.
        first = _read_cth_canonical_page(
            module=module, source_type="note", source_table="notes", limit=1, offset=0,
        )
        scope = first["scope"]
        canonical_page = (first.get("canonical") or {}).get("page", {})
        candidate_total = canonical_page.get("candidate_source_count")
        if type(candidate_total) is not int or candidate_total < 0:
            raise LegacyScopeReadError("CTH_CANONICAL_PAGE_UNAVAILABLE", 503)
        try:
            projection_candidate_count = db.get_canonical_note_projection_count(scope)
            filtered_candidate_count = db.get_canonical_note_projection_count(
                scope, projection_filters,
            )
        except Exception as exc:
            raise LegacyScopeReadError("LEGACY_NOTE_CANDIDATE_UNAVAILABLE", 503) from exc

        # Small scopes are inexpensive to verify completely, retaining exact
        # totals for common cases. Large scopes return a valid page promptly;
        # total stays UNKNOWN until the signed scan reaches the end.
        target_count = offset + limit
        must_scan_all = (
            scan_all or require_complete
            or filtered_candidate_count <= max(100, target_count)
        )
        matching_count = 0
        candidate_offset = 0
        seen_candidates = set()
        truncated_by_change = False
        while candidate_offset < filtered_candidate_count and (
                must_scan_all or matching_count < target_count):
            batch_limit = min(100, filtered_candidate_count - candidate_offset)
            try:
                batch_ids = db.get_canonical_note_projection_candidate_page(
                    scope, projection_filters, limit=batch_limit, offset=candidate_offset,
                )
            except Exception as exc:
                raise LegacyScopeReadError("LEGACY_NOTE_CANDIDATE_UNAVAILABLE", 503) from exc
            if not batch_ids:
                rejected += max(1, filtered_candidate_count - candidate_offset)
                truncated_by_change = True
                break
            duplicate_ids = [source_id for source_id in batch_ids if source_id in seen_candidates]
            if duplicate_ids:
                rejected += len(duplicate_ids)
                truncated_by_change = True
            seen_candidates.update(batch_ids)

            signed_page = _read_cth_canonical_page(
                module=module, source_type="note", source_table="notes",
                limit=len(batch_ids), source_ids=batch_ids,
            )
            if signed_page.get("scope") != scope:
                raise LegacyScopeReadError("CTH_SCOPE_CHANGED_DURING_READ", 409)
            signed = signed_page.get("canonical") or {}
            signed_rows = signed.get("records")
            if not isinstance(signed_rows, list):
                raise LegacyScopeReadError("CTH_CANONICAL_RECORDS_UNAVAILABLE", 503)
            rejected += int(signed.get("rejected_count", 0) or 0)
            signed_by_id = {}
            for row in signed_rows:
                source_id = _validate_canonical_source_row(
                    row, source_type="note", source_table="notes",
                )
                if source_id not in batch_ids:
                    raise LegacyScopeReadError("CANONICAL_SOURCE_ID_COLLISION", 503)
                if scope.get("subject_id") is not None and row.get("subject_id") != scope["subject_id"]:
                    raise LegacyScopeReadError("CANONICAL_SUBJECT_SCOPE_MISMATCH", 503)
                signed_by_id[source_id] = row
            rejected += sum(1 for source_id in batch_ids if source_id not in signed_by_id)

            valid_ids = [source_id for source_id in batch_ids if source_id in signed_by_id]
            projected_rows = db.get_notes_for_canonical_source_ids(
                valid_ids, projection_filters, limit=max(1, len(valid_ids)), offset=0,
            )
            projected_by_id = {row.get("note_id"): row for row in projected_rows}
            for source_id in batch_ids:
                if source_id not in signed_by_id:
                    continue
                note = projected_by_id.get(source_id)
                if note is None:
                    # A filter or projection changed while the request was in
                    # flight, or the source row disappeared; never claim total.
                    rejected += 1
                    truncated_by_change = True
                    continue
                note["canonical_source"] = {
                    "canonical_id": signed_by_id[source_id].get("canonical_id"),
                    "source_id": source_id,
                    "source_type": signed_by_id[source_id].get("source_type"),
                    "source_table": signed_by_id[source_id].get("source_table"),
                    "scope_status": signed_by_id[source_id].get("scope_status"),
                    "scope_evidence_ref": signed_by_id[source_id].get("scope_evidence_ref"),
                    "captured_at": signed_by_id[source_id].get("captured_at"),
                    "field_origin": "legacy_note_projection; Canonical supplies source and scope binding",
                }
                source_ids.append(source_id)
                canonical_by_source_id[source_id] = signed_by_id[source_id]
                if offset <= matching_count < offset + limit:
                    page_notes.append(note)
                if include_all_projection:
                    all_notes.append(note)
                matching_count += 1
            candidate_offset += len(batch_ids)

        full_scan = candidate_offset >= filtered_candidate_count
        unfiltered_projection_complete = projection_candidate_count == candidate_total
        rejected = max(rejected, 0)
        truncated = bool(
            not full_scan or rejected or truncated_by_change
            or (must_scan_all and not unfiltered_projection_complete)
        )
        if require_complete and truncated:
            raise LegacyScopeReadError("CTH_CANONICAL_SCAN_INCOMPLETE", 503)
        note_rows = all_notes if include_all_projection else page_notes
        if legacy_verified_false:
            note_rows = []
            total = 0 if not truncated else None
        else:
            total = matching_count if full_scan and not truncated else None

    for note in note_rows:
        canonical = canonical_by_source_id.get(note.get("note_id"))
        if canonical is None:
            raise LegacyScopeReadError("CANONICAL_NOTE_BINDING_UNAVAILABLE", 503)
        # The row has already been annotated from the signed Canonical result.
        if not note.get("canonical_source"):
            note["canonical_source"] = {
                "canonical_id": canonical.get("canonical_id"),
                "source_id": canonical.get("source_id"),
                "source_type": canonical.get("source_type"),
                "source_table": canonical.get("source_table"),
                "scope_status": canonical.get("scope_status"),
                "scope_evidence_ref": canonical.get("scope_evidence_ref"),
                "captured_at": canonical.get("captured_at"),
                "field_origin": "legacy_note_projection; Canonical supplies source and scope binding",
            }

    data_state = (
        "PARTIAL" if truncated else
        "READY" if candidate_total > 0 else "NOT_COLLECTED"
    )
    return {
        "scope": scope,
        "notes": note_rows,
        "total": total,
        "candidate_count": candidate_total,
        "projection_candidate_count": projection_candidate_count,
        "filtered_candidate_count": filtered_candidate_count,
        "verified_source_count": len(source_ids),
        "verified_source_count_complete": not truncated,
        "rejected_source_count": rejected,
        "truncated": truncated,
        "data_state": data_state,
        "permission_audit_id": first.get("permission_audit_id"),
        # Internal callers such as scoped aggregates use this only after asking
        # for scan_all=True; API routes never serialize it.
        "_verified_source_ids": source_ids,
    }


def register_data_query_api(app):
    """在 Flask app 上注册数据只读查询蓝图。"""
    bp = Blueprint("data_query", __name__)

    @bp.route('/api/stats', endpoint='api_stats')
    def api_stats():
        try:
            result = read_scoped_legacy_note_rows(
                module="reports", limit=1, scan_all=True,
            )
            source_note_ids = result["_verified_source_ids"]
            complete_aggregate = not result["truncated"] and result["data_state"] == "READY"
            stats = db.get_stats_for_canonical_source_ids(source_note_ids) if complete_aggregate else None
            top_topics = ([{'topic': topic, 'count': count} for topic, count in
                           db.get_top_topics_for_canonical_source_ids(source_note_ids, 12)]
                          if complete_aggregate else None)
            categories = (db.get_category_distribution_for_canonical_source_ids(source_note_ids)
                          if complete_aggregate else None)
            return jsonify({
                'ok': True, 'stats': stats,
                'top_topics': top_topics,
                'categories': categories,
                'aggregate_state': 'READY' if complete_aggregate else result["data_state"],
                'scope': result["scope"], 'data_state': result["data_state"],
                'candidate_count': result["candidate_count"],
                'verified_source_count': result["verified_source_count"],
                'rejected_source_count': result["rejected_source_count"],
                'truncated': result["truncated"],
            })
        except LegacyScopeReadError as exc:
            return jsonify({'ok': False, 'code': exc.code, 'error': exc.code}), exc.status

    @bp.route('/api/notes', endpoint='api_notes')
    def api_notes():
        try:
            page = max(1, int(request.args.get('page', 1)))
            per_page = max(1, min(100, int(request.args.get('per_page', 20))))
        except ValueError:
            return jsonify({'ok': False, 'error': 'page/per_page 必须为整数'}), 400
        filters = {}
        for key in ('note_id', 'sentiment', 'risk_level', 'category', 'keyword', 'date_start', 'date_end'):
            v = request.args.get(key, '')
            if v:
                filters[key] = v
        if request.args.get('is_official') in ('0', '1'):
            filters['is_official'] = request.args.get('is_official') == '1'
        if request.args.get('verified') in ('0', '1'):
            filters['verified'] = request.args.get('verified') == '1'
        # GAP-06 双维度筛选透传（非法枚举在 _apply_filters 白名单内被忽略）
        for _dim in ('subject_type', 'content_type'):
            _dv = request.args.get(_dim, '')
            if _dv:
                filters[_dim] = _dv
        offset = (page - 1) * per_page
        try:
            result = read_scoped_legacy_note_rows(
                module="content", filters=filters, limit=per_page, offset=offset,
            )
            total = result["total"]
            return jsonify({
                'ok': True, 'notes': result["notes"], 'total': total, 'page': page,
                'per_page': per_page,
                'total_pages': None if total is None else (total + per_page - 1) // per_page,
                'scope': result["scope"], 'data_state': result["data_state"],
                'candidate_count': result["candidate_count"],
                'verified_source_count': result["verified_source_count"],
                'truncated': result["truncated"],
            })
        except LegacyScopeReadError as exc:
            return jsonify({'ok': False, 'code': exc.code, 'error': exc.code}), exc.status

    @bp.route('/api/risk-alerts', endpoint='api_risk_alerts')
    def api_risk_alerts():
        try:
            result = read_scoped_legacy_note_rows(
                module="reports", limit=1000, scan_all=True,
                include_all_projection=True,
            )
            rows = [note for note in result["notes"]
                    if note.get("risk_level") in {"critical", "high", "medium"}
                    and note.get("negative_confirmed") != 2]
            def risk_sort_value(note):
                value = note.get("risk_score")
                valid = type(value) is int
                return (not valid, -value if valid else 0)
            rows.sort(key=lambda note: (
                note.get("risk_level") != "critical",
                note.get("risk_level") != "high",
                risk_sort_value(note),
                str(note.get("collected_at") or ""),
            ), reverse=False)
            has_complete_data = (
                not result["truncated"] and result["data_state"] == "READY"
                and result["total"] is not None and result["total"] == len(result["notes"])
            )
            return jsonify({'ok': True, 'notes': rows[:30], 'scope': result["scope"],
                            'data_state': result["data_state"],
                            'total': len(rows) if has_complete_data else None,
                            'truncated': result["truncated"]})
        except LegacyScopeReadError as exc:
            return jsonify({'ok': False, 'code': exc.code, 'error': exc.code}), exc.status

    # P0 断链兼容路由：保留两个旧 URL，但风险读取必须有显式业务域，
    # 并复用当前 Permission + Canonical owner；不能把跨域 GLOBAL 映射成旧 notes 查询。
    @bp.route('/api/risks/active', endpoint='api_risks_active')
    @bp.route('/api/risk/active', endpoint='api_risk_active')
    def api_risks_active():
        """读取所选业务域中已授权 Canonical 投影的活跃风险记录。"""
        limit = max(1, min(200, request.args.get('limit', 50, type=int)))
        try:
            # This legacy URL is neutral across CTH/BMP. Requiring an explicit
            # domain keeps GLOBAL / ALL from silently selecting a CTH policy or
            # reading the unscoped legacy notes table.
            import lumenis_app_api
            domain = lumenis_app_api._get_domain_context()
            if domain is None:
                return jsonify({
                    'ok': False,
                    'code': 'DOMAIN_SELECTION_REQUIRED',
                    'error': 'Select CTH or BMP before reading active risks.',
                    'risks': None,
                    'total': None,
                    'selection_required': True,
                }), 400

            # Resolve the existing domain risk policy as an explicit support
            # check; records themselves remain sourced from scoped Canonical.
            from risk_engine import get_risk_policy
            policy = get_risk_policy(domain)
            scope, canonical = lumenis_app_api._domain_api_canonical(domain, 'reports')
            records = canonical.get('records', [])
            active_levels = {'critical', 'high', 'medium', '严重', '高', '中'}
            risk_candidates = [
                row for row in records
                if isinstance(row.get('risk_level'), str)
                and row['risk_level'].strip().lower() in active_levels
            ]

            # Preserve the established human-dismissal behavior, but only for
            # note IDs already selected by the signed Canonical scope read.
            # Non-note rows or an inconsistent source reference cannot safely
            # inherit a note review state, so fail closed rather than surface a
            # possibly dismissed record as active.
            review_ids = []
            for row in risk_candidates:
                source_id = row.get('source_id')
                raw_ref = row.get('raw_ref')
                try:
                    source_ref = json.loads(raw_ref) if isinstance(raw_ref, str) else None
                except (TypeError, ValueError):
                    source_ref = None
                if (
                    row.get('source_type') != 'note'
                    or row.get('source_table') != 'notes'
                    or not isinstance(source_id, str) or not source_id.strip()
                    or row.get('external_id') != source_id
                    or not isinstance(source_ref, dict)
                    or source_ref.get('table') != 'notes'
                    or source_ref.get('note_id') != source_id
                ):
                    return jsonify({
                        'ok': False,
                        'code': 'RISK_DISMISSAL_SOURCE_MAPPING_UNAVAILABLE',
                        'error': 'Canonical risk source cannot be matched safely to its review state.',
                        'risks': None,
                        'total': None,
                        'data_state': 'UNAVAILABLE',
                    }), 503
                review_ids.append(source_id)

            if risk_candidates:
                try:
                    review_states = db.get_high_risk_note_dismissal_states(review_ids)
                except Exception:
                    return jsonify({
                        'ok': False,
                        'code': 'RISK_DISMISSAL_STATE_UNAVAILABLE',
                        'error': 'The existing note review state could not be read.',
                        'risks': None,
                        'total': None,
                        'data_state': 'UNAVAILABLE',
                    }), 503
                if set(review_states) != set(review_ids) or any(
                    isinstance(state, bool) or state not in (0, 1, 2)
                    for state in review_states.values()
                ):
                    return jsonify({
                        'ok': False,
                        'code': 'RISK_DISMISSAL_STATE_UNAVAILABLE',
                        'error': 'A Canonical risk source has no reliable note review state.',
                        'risks': None,
                        'total': None,
                        'data_state': 'UNAVAILABLE',
                    }), 503
                risk_candidates = [
                    row for row in risk_candidates
                    if review_states[row['source_id']] != 2
                ]

            risks = risk_candidates[:limit]

            by_level = {}
            for row in risks:
                level = row['risk_level'].strip().lower()
                by_level[level] = by_level.get(level, 0) + 1

            return jsonify({
                'ok': True,
                'domain': domain,
                'domain_id': scope.get('domain_id'),
                'product_id': scope.get('product_id'),
                'scope': scope,
                'risks': risks,
                'total': len(risks),
                'by_level': by_level,
                'limit': limit,
                # Persisted Canonical scores have no applied-policy field.
                # Do not relabel historical values with today's policy.
                'risk_policy_version': None,
                'risk_policy_version_state': 'NOT_RECORDED',
                'current_risk_policy_version': policy.policy_version,
                'canonical_returned': canonical.get('returned_count', len(records)),
                'canonical_candidate_count': canonical.get('candidate_count'),
                'truncated': canonical.get('truncated'),
                'data_state': 'READY' if records else 'NOT_COLLECTED',
                'source': 'permission-checked canonical_data.list_scoped_canonical',
                'dismissal_state': 'APPLIED_FOR_CANONICAL_NOTE_SOURCE_IDS',
            })
        except ValueError as exc:
            return jsonify({'ok': False, 'code': str(exc)}), 400
        except Exception as exc:
            if hasattr(exc, 'code') and hasattr(exc, 'status'):
                return jsonify({'ok': False, 'code': exc.code}), exc.status
            return jsonify({
                'ok': False,
                'code': 'RISK_CANONICAL_UNAVAILABLE',
                'error': 'Authorized Canonical risk data is unavailable.',
            }), 503

    @bp.route('/api/hot-notes', endpoint='api_hot_notes')
    def api_hot_notes():
        try:
            result = read_scoped_legacy_note_rows(
                module="reports", limit=1000, scan_all=True,
                include_all_projection=True,
            )
            rows = list(result["notes"])
            def engagement_sort_value(note):
                fields = ("likes", "comments", "collects", "shares")
                values = [note.get(field) for field in fields]
                complete = all(type(value) is int for value in values)
                return (not complete, -sum(values) if complete else 0)
            rows.sort(key=engagement_sort_value)
            has_complete_data = (
                not result["truncated"] and result["data_state"] == "READY"
                and result["total"] is not None and result["total"] == len(result["notes"])
            )
            return jsonify({'ok': True, 'notes': rows[:10], 'scope': result["scope"],
                            'data_state': result["data_state"],
                            'total': len(rows) if has_complete_data else None,
                            'truncated': result["truncated"]})
        except LegacyScopeReadError as exc:
            return jsonify({'ok': False, 'code': exc.code, 'error': exc.code}), exc.status

    @bp.route('/api/comments', endpoint='api_comments')
    def api_comments():
        try:
            # Bind the request to an actual CTH authorization first; the legacy
            # comments table has no canonical negative-classification contract.
            read_scoped_legacy_note_rows(module="reports", limit=1)
        except LegacyScopeReadError as exc:
            return jsonify({'ok': False, 'code': exc.code, 'error': exc.code}), exc.status
        return jsonify({'ok': False, 'code': 'COMMENT_SENTIMENT_NOT_BOUND_TO_CANONICAL',
                        'error': 'Comment sentiment has no current scoped Canonical source.'}), 503

    @bp.route('/api/events', endpoint='api_events')
    def api_events():
        try:
            snapshot = _read_cth_canonical_snapshot(module="reports", limit=100)
        except LegacyScopeReadError as exc:
            return jsonify({'ok': False, 'code': exc.code, 'error': exc.code}), exc.status
        canonical = snapshot["canonical"]
        events = []
        for record in canonical.get("records", []):
            event_hint = record.get("event_hint")
            topics = record.get("topics")
            try:
                has_topics = bool(json.loads(topics)) if isinstance(topics, str) else bool(topics)
            except (TypeError, ValueError):
                has_topics = False
            if not (isinstance(event_hint, str) and event_hint.strip()) and not has_topics:
                continue
            events.append({
                "event_id": record.get("canonical_id"), "title": record.get("title"),
                "event_hint": event_hint, "topics": topics, "tags": record.get("tags"),
                "publish_datetime": record.get("publish_datetime"),
                "captured_at": record.get("captured_at"),
                "sentiment": record.get("sentiment"), "risk_level": record.get("risk_level"),
                "platform": record.get("source_platform"), "domain": "cth",
                "subject_id": record.get("subject_id"), "source_id": record.get("source_id"),
                "scope_evidence_ref": record.get("scope_evidence_ref"),
            })
        truncated = bool(canonical.get("truncated"))
        data_state = ("PARTIAL" if truncated else
                      "READY" if canonical.get("candidate_count", 0) else "NOT_COLLECTED")
        return jsonify({'ok': True, 'events': events,
                        'total': len(events) if data_state == "READY" else None,
                        'generic_count': None, 'noise_count': None,
                        'scope': snapshot["scope"], 'data_state': data_state,
                        'truncated': truncated, 'mode': 'verified_canonical'})

    @bp.route('/api/web-mentions', endpoint='api_web_mentions')
    def api_web_mentions():
        limit = max(1, min(100, request.args.get('limit', 50, type=int)))
        offset = max(0, request.args.get('offset', 0, type=int))
        try:
            snapshot = _read_cth_canonical_page(
                module="content", source_type="web_mention", source_table="web_mentions",
                limit=limit, offset=offset,
            )
        except LegacyScopeReadError as exc:
            return jsonify({'ok': False, 'code': exc.code, 'error': exc.code}), exc.status
        canonical = snapshot["canonical"]
        mentions = []
        try:
            for record in canonical.get("records", []):
                _validate_canonical_source_row(record, source_type="web_mention", source_table="web_mentions")
                if record.get("relevance_status") == "relevant":
                    mentions.append({
                        "source_id": record.get("source_id"), "source_platform": record.get("source_platform"),
                        "source_type": record.get("source_type"), "title": record.get("title"),
                        "content": record.get("content"), "url": record.get("url"),
                        "published_at": record.get("publish_datetime"), "fetched_at": record.get("captured_at"),
                        "relevance": record.get("relevance_status"), "verification": record.get("verification_status"),
                        "topics": record.get("topics"), "scope_evidence_ref": record.get("scope_evidence_ref"),
                    })
        except LegacyScopeReadError as exc:
            return jsonify({'ok': False, 'code': exc.code, 'error': exc.code}), exc.status
        page = canonical.get("page", {})
        truncated = bool(page.get("truncated") or canonical.get("truncated"))
        data_state = ("PARTIAL" if truncated else
                      "READY" if page.get("candidate_source_count", 0) else "NOT_COLLECTED")
        return jsonify({'ok': True, 'mentions': mentions,
                        'total': len(mentions) if data_state == "READY" else None,
                        'scope': snapshot["scope"], 'data_state': data_state,
                        'candidate_count': page.get('candidate_source_count'),
                        'offset': offset, 'limit': limit, 'truncated': truncated})

    @bp.route('/api/feedback-keywords', endpoint='api_feedback_keywords')
    def api_feedback_keywords():
        try:
            read_scoped_legacy_note_rows(module="reports", limit=1)
        except LegacyScopeReadError as exc:
            return jsonify({'ok': False, 'code': exc.code, 'error': exc.code}), exc.status
        return jsonify({'ok': False, 'code': 'FEEDBACK_KEYWORD_SCOPE_NOT_BOUND',
                        'error': 'Feedback keyword rows have no current domain and Canonical binding.'}), 503

    @bp.route('/api/hot-topics', endpoint='api_hot_topics')
    def api_hot_topics():
        limit = max(1, min(30, request.args.get('limit', 12, type=int)))
        try:
            result = read_scoped_legacy_note_rows(
                module="reports", limit=1, scan_all=True,
            )
            complete = not result["truncated"] and result["data_state"] == "READY"
            topics = [{'topic': topic, 'count': count} for topic, count in
                      db.get_top_topics_for_canonical_source_ids(
                          result["_verified_source_ids"], limit)]
            return jsonify({'ok': True, 'topics': topics, 'scope': result["scope"],
                            'data_state': result["data_state"],
                            'total': len(topics) if complete else None,
                            'truncated': result["truncated"]})
        except LegacyScopeReadError as exc:
            return jsonify({'ok': False, 'code': exc.code, 'error': exc.code}), exc.status

    @bp.route('/api/metric-trend', endpoint='api_metric_trend')
    def api_metric_trend():
        # 指标快照时间序列（BASELINE §9/§11/§12）：只读，供报告/前端动态可视化绑定真实数据
        entity_type = request.args.get('entity_type', 'note')
        entity_key = request.args.get('entity_key', '').strip()
        if entity_type not in ('note', 'topic') or not entity_key:
            return jsonify({'ok': False, 'error': 'entity_type must be note|topic and entity_key required'}), 400
        limit = max(1, min(1000, request.args.get('limit', 200, type=int)))
        rows = db.get_metric_trend(entity_type, entity_key, limit)
        return jsonify({'ok': True, 'entity_type': entity_type, 'entity_key': entity_key,
                        'points': len(rows), 'trend': rows})

    @bp.route('/api/resource-guard', endpoint='api_resource_guard')
    def api_resource_guard():
        """P0-G 最大效率统一资源守卫：消费 lifecycle_action + 资源指标，输出四态调度建议（只读）。"""
        action = request.args.get('action', 'schedule_normal')
        if action not in ('schedule_normal', 'backoff_interval', 'pause_until_cooldown',
                          'freeze_and_recover', 'probe_only', 'ramp_up'):
            return jsonify({'ok': False, 'error': 'invalid action'}), 400
        cpu = request.args.get('cpu', type=float)
        ram = request.args.get('ram', type=float)
        lag = request.args.get('queue_lag', type=int)
        snap = _resource_guard.snapshot(action, cpu_pct=cpu, ram_pct=ram, queue_lag=lag)
        return jsonify({'ok': True, **snap})

    app.register_blueprint(bp)
    return bp
