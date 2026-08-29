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

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'rednote_collector.cjs'  # rednote CDP 采集引擎（验证通过）
SCRIPT_FALLBACK = ROOT / 'xhs_live_engine.js'  # 备用旧引擎


def run_live(keyword: str, *, max_scroll=5, max_details=20, max_comment_pages=5,
             wait_ms=4000, comments=True, cdp_url=None) -> dict:
    out = ROOT / 'data' / f'xhs_live_{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}.json'
    env = os.environ.copy()
    if cdp_url:
        env['XHS_CDP_URL'] = cdp_url
    cmd = ['node', str(SCRIPT), '--keyword', keyword, '--output', str(out),
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
    return data


def persist_live(data: dict, subject_hit: Callable[[str], bool]) -> dict:
    if data.get('verification_required'):
        return {'ok': False, 'status': 'verification_required', 'accepted': 0, 'reason': '平台要求人工验证，本次不把0条当作无舆情'}
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
        n['comments_collected'] = int(n.get('comments_collected',0) or 0)
        database.insert_note(n)
        database.save_collector_quality(n.get('note_id'), {
            **q, 'detail_status': n.get('detail_status',''),
            'comments_collected': n.get('comments_collected',0), 'collector_version':'xhs-live-v2'
        })
        database.upsert_note_comments(n.get('note_id'), n.get('comments_data') or [])
        stats['persisted'] += 1
        stats['comments'] += len(n.get('comments_data') or [])
    return {'ok': True, 'status': 'success', **stats}
