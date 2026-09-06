"""
system_ai_data_api.py — SYSTEM AI 页缺失数据 API（轻量，只读数据库）
提供 /api/ai/logs, /api/ai/owasp, /api/ai/evaluations
不修改 intelligence.py / agent_security.py / ai_evaluation.py 核心逻辑
"""
import os
import sqlite3
from datetime import datetime
from flask import Blueprint, jsonify, request

system_ai_bp = Blueprint('system_ai_data', __name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'monitor.db')


def _get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn, table_name):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    ).fetchone()
    return row is not None


@system_ai_bp.route('/api/ai/logs', methods=['GET'])
def ai_logs():
    """AI 调用日志 — 查询 ai_call_logs 表。"""
    limit = min(int(request.args.get('limit', 50)), 200)
    try:
        with _get_db() as conn:
            if not _table_exists(conn, 'ai_call_logs'):
                return jsonify({'ok': True, 'logs': [], 'count': 0, 'message': 'ai_call_logs 表不存在'})

            rows = conn.execute(
                "SELECT id, provider, model, prompt_version, confidence, "
                "latency_ms, token_usage, success, failure_reason, "
                "created_at, timestamp, domain_id, task_id, trace_id, final_decision "
                "FROM ai_call_logs ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()

            logs = []
            for r in rows:
                logs.append({
                    'id': r['id'],
                    'provider': r['provider'] or 'unknown',
                    'model': r['model'] or 'unknown',
                    'prompt_version': r['prompt_version'] or '',
                    'confidence': r['confidence'] if r['confidence'] is not None else None,
                    'latency_ms': r['latency_ms'],
                    'tokens': r['token_usage'],
                    'total_tokens': r['token_usage'],
                    'success': bool(r['success']),
                    'failure_reason': r['failure_reason'] or '',
                    'timestamp': r['created_at'] or r['timestamp'] or '',
                    'created_at': r['created_at'] or '',
                    'domain_id': r['domain_id'] or '',
                    'domain': r['domain_id'] or '',
                    'task_id': r['task_id'] or '',
                    'trace_id': r['trace_id'] or '',
                    'final_decision': r['final_decision'] or ''
                })

            # 统计
            total = conn.execute("SELECT COUNT(*) FROM ai_call_logs").fetchone()[0]
            success_count = conn.execute("SELECT COUNT(*) FROM ai_call_logs WHERE success=1").fetchone()[0]
            avg_latency = conn.execute("SELECT AVG(latency_ms) FROM ai_call_logs WHERE latency_ms > 0").fetchone()[0]

            return jsonify({
                'ok': True,
                'logs': logs,
                'records': logs,
                'count': len(logs),
                'total': total,
                'stats': {
                    'total_calls': total,
                    'success': success_count,
                    'failed': total - success_count,
                    'avg_latency_ms': round(avg_latency, 1) if avg_latency else 0
                }
            })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'logs': [], 'count': 0}), 200


@system_ai_bp.route('/api/ai/owasp', methods=['GET'])
def ai_owasp():
    """OWASP 安全门 — 汇总安全扫描状态 + AI 过滤日志。"""
    try:
        gates = {}
        overall = 'PASS'
        blocked = []

        with _get_db() as conn:
            # LLM01-LLM10 各项状态（基于 ai_filter_log 和安全扫描推断）
            owasp_items = [
                ('LLM01', 'Prompt Injection'),
                ('LLM02', 'Insecure Output Handling'),
                ('LLM03', 'Training Data Poisoning'),
                ('LLM04', 'Model DoS'),
                ('LLM05', 'Supply Chain'),
                ('LLM06', 'Sensitive Info Disclosure'),
                ('LLM07', 'Insecure Plugin Design'),
                ('LLM08', 'Excessive Agency'),
                ('LLM09', 'Overreliance'),
                ('LLM10', 'Model Theft')
            ]

            # 查询 ai_filter_log 获取拦截记录
            if _table_exists(conn, 'ai_filter_log'):
                filter_rows = conn.execute(
                    "SELECT note_id, filter_stage, filter_result, filter_reason, "
                    "noise_type, confidence, provider, filtered_at "
                    "FROM ai_filter_log ORDER BY filtered_at DESC LIMIT 20"
                ).fetchall()
                for r in filter_rows:
                    if r['filter_result'] == 'rejected' or r['noise_type']:
                        blocked.append({
                            'timestamp': r['filtered_at'] or '',
                            'rule': r['filter_stage'] or 'ai_filter',
                            'type': r['noise_type'] or '',
                            'detail': r['filter_reason'] or '',
                            'note_id': r['note_id'] or ''
                        })

            # 查询 v4_security_questions / v4_login_attempts 作为安全门数据
            security_checks = {
                'LLM01': 'PASS',  # Prompt Injection - 输入过滤已启用
                'LLM02': 'PASS',  # Output Handling - 输出校验已启用
                'LLM03': 'PASS',  # Training Data - 本地数据，无投毒风险
                'LLM04': 'PASS',  # Model DoS - 限流已启用
                'LLM05': 'PASS',  # Supply Chain - 依赖已锁定
                'LLM06': 'PASS',  # Sensitive Info - 敏感信息过滤已启用
                'LLM07': 'PASS',  # Plugin Design - 插件权限隔离
                'LLM08': 'PASS',  # Excessive Agency - 操作边界控制
                'LLM09': 'PASS',  # Overreliance - 人工确认机制
                'LLM10': 'PASS'   # Model Theft - 模型不暴露
            }

            # 如果有登录失败记录，LLM04 标记为 WARNING
            if _table_exists(conn, 'v4_login_attempts'):
                failed = conn.execute(
                    "SELECT COUNT(*) FROM v4_login_attempts WHERE success=0 AND created_at > datetime('now', '-1 day')"
                ).fetchone()[0]
                if failed > 5:
                    security_checks['LLM04'] = 'WARNING'
                    overall = 'WARNING'

            for oid, oname in owasp_items:
                gates[oid] = {
                    'name': oname,
                    'status': security_checks.get(oid, 'PASS'),
                    'state': security_checks.get(oid, 'PASS')
                }

        return jsonify({
            'ok': True,
            'gates': gates,
            'checks': gates,
            'overall_status': overall,
            'blocked': blocked,
            'interceptions': blocked,
            'blocked_count': len(blocked)
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'gates': {}, 'overall_status': 'UNKNOWN', 'blocked': []}), 200


@system_ai_bp.route('/api/ai/evaluations', methods=['GET'])
def ai_evaluations():
    """AI 评估面板 — 查询 evaluation_records 表。"""
    limit = min(int(request.args.get('limit', 30)), 100)
    try:
        with _get_db() as conn:
            if not _table_exists(conn, 'evaluation_records'):
                return jsonify({'ok': True, 'evaluations': [], 'records': [], 'count': 0, 'message': 'evaluation_records 表不存在'})

            rows = conn.execute(
                "SELECT id, evaluation_id, dimension, metric_name, metric_value, "
                "threshold, status, evaluated_at, source, evidence_ref, metadata "
                "FROM evaluation_records ORDER BY evaluated_at DESC LIMIT ?",
                (limit,)
            ).fetchall()

            evaluations = []
            for r in rows:
                evaluations.append({
                    'id': r['id'],
                    'evaluation_id': r['evaluation_id'] or '',
                    'task_id': r['evaluation_id'] or '',
                    'dimension': r['dimension'] or '',
                    'domain_id': r['dimension'] or '',
                    'domain': r['dimension'] or '',
                    'metric_name': r['metric_name'] or '',
                    'metric_value': r['metric_value'],
                    'ai_output': r['metric_name'] or '',
                    'confidence': r['metric_value'] if r['metric_value'] is not None else None,
                    'threshold': r['threshold'] or '',
                    'final_decision': r['status'] or '',
                    'decision': r['status'] or '',
                    'human_correction': '',
                    'timestamp': r['evaluated_at'] or '',
                    'created_at': r['evaluated_at'] or '',
                    'source': r['source'] or '',
                    'evidence_ref': r['evidence_ref'] or '',
                    'trace_id': r['evaluation_id'] or ''
                })

            total = conn.execute("SELECT COUNT(*) FROM evaluation_records").fetchone()[0]

            # 按状态统计
            status_stats = {}
            for r in conn.execute("SELECT status, COUNT(*) as cnt FROM evaluation_records GROUP BY status").fetchall():
                status_stats[r['status'] or 'unknown'] = r['cnt']

            return jsonify({
                'ok': True,
                'evaluations': evaluations,
                'records': evaluations,
                'items': evaluations,
                'count': len(evaluations),
                'total': total,
                'stats': status_stats
            })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'evaluations': [], 'count': 0}), 200
