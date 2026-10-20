"""XHS Live Data Engine v1

目标：搜索发现 -> 详情定稿 -> 评论采集 -> 数据质量审计 -> 现有主体过滤 -> 入库。
不实现或绕过平台验证码、签名保护或风控；遇到验证直接报告数据源异常。
"""
from __future__ import annotations
import json, subprocess
from datetime import datetime
from pathlib import Path
from typing import Callable

from .models import XHSNote
from ..pipeline.normalize import normalize_note
from ..pipeline.deduplicate import deduplicate
from ..pipeline.subject_filter import filter_subject
import database

# 统一 Node 解析（PATH 优先，项目内置 nodejs/ 兜底），避免常驻进程 PATH 缺 node 抛 WinError 2
try:
    from runtime_bin import resolve_node as _resolve_node
    _NODE_BIN = _resolve_node() or 'node'
except Exception:
    _NODE_BIN = 'node'

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'rednote_collector.cjs'  # rednote CDP 采集引擎（验证通过）
SCRIPT_FALLBACK = ROOT / 'xhs_live_engine.js'  # 备用旧引擎


def run_live(keyword: str, *, max_scroll=5, max_details=20, max_comment_pages=5,
             wait_ms=4000, comments=True, cdp_url=None, account=None) -> dict:
    import xhs_cookie_bridge as _xcb
    resolved_account = account or _xcb.DEFAULT_COLLECTION_ACCOUNT
    policy_gate = _xcb.collection_policy_gate(account=resolved_account, region='intl')
    if not policy_gate.get('ok'):
        return {'ok': False, 'code': policy_gate.get('code'),
                'error': policy_gate.get('reason'), 'notes': [],
                'collection_policy': policy_gate}

    # Registry scope must resolve before CDP/profile/persistence work.
    query_plan = _xcb._resolve_acquisition_plan([keyword])
    query_plan_payload = query_plan.to_dict()
    if not query_plan.is_runnable:
        return {
            'ok': False, 'code': 'ACQUISITION_PLAN_BLOCKED',
            'error': query_plan.reason or query_plan.reason_code,
            'notes': [], 'collection_policy': policy_gate,
            'query_plan': query_plan_payload,
        }
    keyword = query_plan.queries[0].keyword

    import collector as _collector
    cdp_url, endpoint_error = _collector._resolve_server_cdp_url(
        cdp_url, account=resolved_account, region='intl')
    if endpoint_error:
        return {'ok': False, 'code': endpoint_error, 'error': endpoint_error,
                'notes': [], 'collection_policy': policy_gate}
    out = Path(_xcb.PRIVATE_DATA_DIR) / f'xhs_live_{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        env = _collector._collection_env(
            account=resolved_account, region='intl', cdp_url=cdp_url,
            require_local_cookie=True)
    except Exception as exc:  # noqa: BLE001 - any session resolution failure blocks acquisition.
        return {'ok': False, 'code': 'XHS_REGISTERED_SESSION_UNAVAILABLE',
                'error': type(exc).__name__, 'notes': [],
                'collection_policy': policy_gate}
    cmd = [_NODE_BIN, str(SCRIPT), '--keyword', keyword, '--output', str(out),
           '--max-scroll', str(max_scroll), '--max-details', str(max_details),
           '--max-comment-pages', str(max_comment_pages), '--wait-ms', str(wait_ms)]
    if not comments:
        cmd.append('--no-comments')
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=300, env=env)
    stdout = (p.stdout or '').strip()
    # 优先从 ---RESULT_JSON--- 标记后解析；兼容旧版从第一个 { 开始
    marker = '---RESULT_JSON---'
    if marker in stdout:
        json_str = stdout[stdout.index(marker) + len(marker):].strip()
    else:
        idx = stdout.find('{')
        json_str = stdout[idx:] if idx >= 0 else ''
    try:
        data = json.loads(json_str) if json_str else {'ok': False, 'error': (p.stderr or stdout)[-1200:]}
    except json.JSONDecodeError as e:
        data = {'ok': False, 'error': f'JSON解析失败: {e}', 'raw_tail': (p.stderr or stdout)[-1200:]}
    data['_process_returncode'] = p.returncode
    data.setdefault('collection_policy', policy_gate)
    data.setdefault('query_plan', query_plan_payload)
    return data


def resolve_live_scope(*, domain_id=None, product_id=None, subject_id=None,
                       brand_focus_id=None):
    """Validate the exact business scope required before an XHS write."""
    from domain_isolation import resolve_domain_identity
    domain_id, product_id = resolve_domain_identity(domain_id, product_id)
    if not domain_id or not product_id:
        raise ValueError("COLLECTION_DOMAIN_REQUIRED")
    for value in (subject_id, brand_focus_id):
        if value is not None and (not isinstance(value, str) or not value or value != value.strip()):
            raise ValueError("COLLECTION_FOCUS_INVALID")
    if domain_id == "cth":
        if not subject_id or brand_focus_id is not None:
            raise ValueError("CTH_COLLECTION_SUBJECT_REQUIRED")
        subject_scope = subject_id
    elif domain_id == "zbmp":
        if not brand_focus_id or subject_id is not None:
            raise ValueError("BMP_COLLECTION_BRAND_FOCUS_REQUIRED")
        subject_scope = brand_focus_id
    else:
        raise ValueError("BUSINESS_COLLECTION_DOMAIN_REQUIRED")
    return domain_id, product_id, subject_id, brand_focus_id, subject_scope


def _bypass_evidence_canonical_live(note_data, provider='xhs-live-v2', *,
                                    domain_id, product_id, subject_id=None,
                                    brand_focus_id=None):
    """Write the sole business canonical row, then attach Evidence lineage.

    The legacy ``zbc_canonical_data`` overlay is intentionally not written here.
    Source ``notes`` is already stored by the caller; canonical_data.py remains
    the one business Canonical writer and EvidenceChain records only provenance
    plus a lifecycle link to that row.
    """
    domain_id, product_id, subject_id, brand_focus_id, subject_scope = resolve_live_scope(
        domain_id=domain_id, product_id=product_id,
        subject_id=subject_id, brand_focus_id=brand_focus_id,
    )

    from lumenis.shared.database import main_db_path
    db_path = main_db_path()
    source_id = str(note_data.get('note_id') or '')
    raw_content = (str(note_data.get('title', '')) + ' ' + str(note_data.get('content', ''))).strip()
    result = {
        'ok': False, 'source_id': source_id, 'canonical_id': '',
        'canonical_action': '', 'evidence_id': '', 'errors': [],
    }
    try:
        import canonical_data as _cd
        _cd.ensure_canonical_table(db_path)
        note_data["domain_id"] = domain_id
        note_data["product_id"] = product_id
        note_data["subject_id"] = subject_id or ""
        note_data["brand_focus_id"] = brand_focus_id or ""
        record = _cd.note_to_canonical(note_data, product_id=product_id)
        _con = _cd.get_connection(db_path)
        try:
            result['canonical_action'] = _cd.persist_canonical(_con, record)
            _con.commit()
        finally:
            _con.close()
        result['canonical_id'] = record.canonical_id
    except Exception as exc:
        result['errors'].append({'stage': 'canonical_data', 'error_type': type(exc).__name__})

    try:
        from lumenis.shared.evidence import EvidenceChain

        evidence_result = EvidenceChain(db_path).capture_evidence_for_canonical(
            canonical_id=result['canonical_id'],
            source_type='xhs_note',
            source_url=str(note_data.get('url', '')),
            raw_content=raw_content,
            source_id=source_id,
            captured_at=str(note_data.get('captured_at') or note_data.get('fetched_at') or ''),
            publish_datetime=note_data.get('publish_datetime') or note_data.get('publish_date') or None,
            subject_scope=subject_scope,
            task_id=str(note_data.get('task_id') or ''),
            trace_id=str(note_data.get('trace_id') or ''),
            collection_metadata={
                'source_platform': str(note_data.get('source_platform') or 'xhs'),
                'collector_version': str(note_data.get('collector_version') or 'xhs-live-v2'),
                'source_keyword': str(note_data.get('source_keyword') or ''),
            },
            provider=provider,
            dedupe_by_source=True,
            domain_id=domain_id,
            product_id=product_id,
        )
        result['evidence_id'] = evidence_result['evidence'].evidence_id
    except Exception as exc:
        result['errors'].append({'stage': 'evidence_lineage', 'error_type': type(exc).__name__})

    result['ok'] = bool(result['canonical_id'] and result['evidence_id'] and not result['errors'])
    return result


def _source_counters_observed(note) -> bool:
    """True only when the source explicitly returned all four counters."""
    for key in ("likes", "comments", "collects", "shares"):
        value = note.get(key)
        if value is None or isinstance(value, bool):
            return False
        if isinstance(value, str) and not value.strip():
            return False
    return True


def persist_live(data: dict, subject_hit: Callable[[str], bool], *, domain_id=None,
                 product_id=None, subject_id=None, brand_focus_id=None) -> dict:
    try:
        domain_id, product_id, subject_id, brand_focus_id, _ = resolve_live_scope(
            domain_id=domain_id, product_id=product_id,
            subject_id=subject_id, brand_focus_id=brand_focus_id,
        )
    except ValueError as exc:
        return {"ok": False, "status": "scope_unavailable", "accepted": 0,
                "persisted": 0, "reason": str(exc)}

    if data.get('code') in ('account_paused', 'region_paused', 'policy_unavailable',
                            'policy_error', 'cdp_port_not_allowed'):
        return {'ok': False, 'status': 'policy_blocked', 'accepted': 0,
                'reason': data.get('error') or '采集策略阻断'}
    if data.get('verification_required'):
        return {'ok': False, 'status': 'verification_required', 'accepted': 0, 'reason': '平台要求人工验证，本次不把0条当作无舆情'}
    if not data.get('ok', True) and not data.get('notes'):
        return {'ok': False, 'status': 'source_unavailable', 'accepted': 0,
                'reason': data.get('error') or '采集源不可用，本次不把0条当作正常空结果'}
    raw = data.get('notes') or []
    # Completeness is judged on the source fields before normalization, which
    # materializes missing counters as 0.
    notes = deduplicate([
        normalize_note({**n, '_lumenis_metric_observation_complete': _source_counters_observed(n)})
        if isinstance(n, dict) else normalize_note(n)
        for n in raw
    ])
    # 红线：这里唯一调用现有 subject_hit；不在采集器内重写主体口径。
    accepted = filter_subject(notes, subject_hit)
    stats = {
        'fetched': len(notes), 'accepted': len(accepted),
        'rejected_subject': len(notes) - len(accepted), 'persisted': 0, 'comments': 0,
        'canonical_synced': 0, 'evidence_recorded': 0, 'lineage_failures': 0,
    }
    for n in accepted:
        q = n.get('data_quality') or {}
        n['data_quality_status'] = q.get('status','unknown')
        n['data_quality_score'] = q.get('score')
        n['collector_version'] = 'xhs-live-v2'
        n['domain_id'] = domain_id
        n['product_id'] = product_id
        n['subject_id'] = subject_id or ""
        n['brand_focus_id'] = brand_focus_id or ""
        n['captured_at'] = n.get('fetched_at') or datetime.now().isoformat()
        n['comments_collected'] = n.get('comments_collected')
        if not isinstance(n.get('sentiment'), str) or not n['sentiment'].strip():
            n['sentiment'] = 'unknown'
        if not isinstance(n.get('risk_level'), str) or not n['risk_level'].strip():
            n['risk_level'] = 'unknown'
        database.insert_note(n)
        lineage = _bypass_evidence_canonical_live(
            n, provider='xhs-live-v2', domain_id=domain_id, product_id=product_id,
            subject_id=subject_id, brand_focus_id=brand_focus_id,
        )
        stats['canonical_synced'] += int(bool(lineage.get('canonical_id')))
        stats['evidence_recorded'] += int(bool(lineage.get('evidence_id')))
        stats['lineage_failures'] += int(not lineage.get('ok'))
        database.save_collector_quality(n.get('note_id'), {
            **q, 'detail_status': n.get('detail_status',''),
            'comments_collected': n.get('comments_collected',0), 'collector_version':'xhs-live-v2'
        })
        database.upsert_note_comments(n.get('note_id'), n.get('comments_data') or [])
        stats['persisted'] += 1
        stats['comments'] += len(n.get('comments_data') or [])
    lineage_complete = (
        stats['canonical_synced'] == stats['persisted']
        and stats['evidence_recorded'] == stats['persisted']
        and stats['lineage_failures'] == 0
    )
    return {
        'ok': lineage_complete,
        'status': ('success' if lineage_complete and stats['persisted'] else
                   'no_new_data' if lineage_complete else 'partial_lineage_failure'),
        **stats,
    }
