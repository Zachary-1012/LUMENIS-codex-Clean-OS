"""XHS Live Data Engine v1

目标：搜索发现 -> 详情定稿 -> 评论采集 -> 数据质量审计 -> 现有主体过滤 -> 入库。
不实现或绕过平台验证码、签名保护或风控；遇到验证直接报告数据源异常。
"""
from __future__ import annotations
import json, os, subprocess
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
    if cdp_url and not cdp_url.rstrip('/').endswith(':9223'):
        gate = dict(policy_gate)
        gate.update({'ok': False, 'code': 'cdp_port_not_allowed',
                     'reason': '当前生产采集仅允许香港/国际驻场端口9223'})
        return {'ok': False, 'code': gate['code'], 'error': gate['reason'],
                'notes': [], 'collection_policy': gate}
    cdp_url = cdp_url or _xcb.cdp_url_for(resolved_account)
    out = Path(_xcb.PRIVATE_DATA_DIR) / f'xhs_live_{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['XHS_CDP_URL'] = cdp_url
    env['XHS_COLLECTION_REGION'] = 'intl'
    env['XHS_COLLECTION_HOST'] = 'www.rednote.com'
    profile = _xcb.ACCOUNT_PROFILES.get(resolved_account)
    if profile and profile[0]:
        env['XHS_COOKIE_FILE'] = str(profile[0])
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
    return data


def _bypass_evidence_canonical_live(note_data, provider='xhs-live-v2', *,
                                    subject_scope='CTH', domain_id='cth', product_id='CTH'):
    """P0-3/P0-4: Evidence Chain + Canonical Data 旁路写入（side-write）。

    硬红线：所有写入必须 try/except 吞掉并 log warning，绝不影响 notes 主入库。
    """
    try:
        from lumenis.shared.evidence import EvidenceChain
        from lumenis.shared.database import main_db_path
        db_path = main_db_path()
        _raw = (str(note_data.get('title','')) + ' ' + str(note_data.get('content',''))).strip()
        _chain = EvidenceChain(db_path)
        _chain.capture_and_canonicalize(
            source_type='xhs_note',
            source_url=str(note_data.get('url','')),
            raw_content=_raw,
            source_id=str(note_data.get('note_id','')),
            normalized_content=_raw[:500],
            subject_hit=True,
            subject_keywords=['taikoo_hui'],
            sentiment='neutral',
            risk_level='low',
            engagement_metrics={
                'likes': note_data.get('likes',0),
                'comments': note_data.get('comments',0),
                'collects': note_data.get('collects',0),
                'shares': note_data.get('shares',0),
            },
            publish_datetime=note_data.get('publish_datetime') or note_data.get('publish_date') or None,
            subject_scope=subject_scope,
            provider=provider,
            dedupe_by_source=True,
            domain_id=domain_id,
            product_id=product_id,
        )
    except Exception as _e:
        print(f"[bypass][shared_evidence][live] side-write skipped (non-fatal): {_e}")
    try:
        import canonical_data as _cd
        from lumenis.shared.database import main_db_path
        db_path = main_db_path()
        _cd.ensure_canonical_table(db_path)
        _rec = _cd.note_to_canonical(note_data, product_id=product_id)
        _con = _cd.get_connection(db_path)
        try:
            _cd.persist_canonical(_con, _rec)
            _con.commit()
        finally:
            _con.close()
    except Exception as _e:
        print(f"[bypass][canonical_data][live] side-write skipped (non-fatal): {_e}")


def persist_live(data: dict, subject_hit: Callable[[str], bool], *,
                 subject_scope='CTH', domain_id='cth', product_id='CTH') -> dict:
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
    notes = deduplicate([normalize_note(n) for n in raw])
    # 红线：这里唯一调用现有 subject_hit；不在采集器内重写主体口径。
    accepted = filter_subject(notes, subject_hit)
    stats = {'fetched': len(notes), 'accepted': len(accepted), 'rejected_subject': len(notes)-len(accepted), 'persisted': 0, 'comments': 0}
    for n in accepted:
        q = n.get('data_quality') or {}
        n['data_quality_status'] = q.get('status','unknown')
        n['data_quality_score'] = q.get('score',0)
        n['collector_version'] = 'xhs-live-v2'
        n['captured_at'] = n.get('fetched_at') or datetime.now().isoformat()
        n['comments_collected'] = n.get('comments_collected')
        database.insert_note(n)
        # P0-3/P0-4: Evidence Chain + Canonical Data 旁路写入（side-write，失败不影响主入库）
        _bypass_evidence_canonical_live(
            n, provider='xhs-live-v2', subject_scope=subject_scope,
            domain_id=domain_id, product_id=product_id,
        )
        database.save_collector_quality(n.get('note_id'), {
            **q, 'detail_status': n.get('detail_status',''),
            'comments_collected': n.get('comments_collected',0), 'collector_version':'xhs-live-v2'
        })
        database.upsert_note_comments(n.get('note_id'), n.get('comments_data') or [])
        stats['persisted'] += 1
        stats['comments'] += len(n.get('comments_data') or [])
    return {'ok': True, 'status': 'success', **stats}
