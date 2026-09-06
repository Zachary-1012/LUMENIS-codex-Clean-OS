# -*- coding: utf-8 -*-
"""
ai_call_logger.py — AI 调用全链路追踪（ZBC Phase 7 + Track3 审计修复 + G2 字段补全）

设计原则：
1. 旁路记录：日志写入失败绝不阻断 AI 调用主链路（try/except 全包）。
2. 持久化：SQLite 表 ai_call_logs，CREATE TABLE IF NOT EXISTS，向后兼容。
3. 可追溯：每次调用记录 provider / model / prompt_version / input_hash / input_text /
   output / confidence / rule_result / final_result / final_decision / task_id / trace_id /
   timestamp / human_correction / latency_ms / token_usage / failure_reason / created_at。
4. 装饰器：@log_ai_call 包装 AI 调用函数，自动记录入参与返回。
5. 凭证安全：input_hash 仅存哈希；input_text 截断存储（默认前 2000 字符），
   且在写入前对 API key / token 做脱敏。

Track3 修复（2026-09-06）：
- 补齐 task_id / trace_id / input_text / final_decision / timestamp 字段。
- 旧表自动迁移（ALTER TABLE ADD COLUMN，幂等）。
- log_call 支持上述新参数；装饰器自动透传 task_id/trace_id。

G2 修复（2026-09-06）：
- 补齐审计字段：target_type / target_id / model_version / system_result / accepted。
- ALTER TABLE 向后兼容加列（DEFAULT ''），不破坏历史数据。
- log_call() 补可选参数，现有调用不传不受影响（None→空）。
- 修复原 INSERT 列数与占位符不匹配 bug（18列名/21占位符）。

数据库路径复用 database.py 的 ZBC_DB_PATH 环境变量约定，未设置时默认 data/monitor.db。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
import time
import traceback
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

# ============================================================
# 1) 数据库路径（与 database.py 保持一致的环境变量约定）
# ============================================================
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.abspath(
    os.environ.get('ZBC_DB_PATH') or os.path.join(_BASE_DIR, 'data', 'monitor.db')
)

_WRITE_LOCK = threading.Lock()  # SQLite 多线程写保护

# ============================================================
# 2) Schema（CREATE TABLE IF NOT EXISTS，幂等）
# ============================================================
_SCHEMA = """
CREATE TABLE IF NOT EXISTS ai_call_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT DEFAULT '',
    model TEXT DEFAULT '',
    prompt_version TEXT DEFAULT '',
    input_hash TEXT DEFAULT '',
    input_text TEXT DEFAULT '',
    output TEXT DEFAULT '',
    confidence REAL DEFAULT 0.0,
    rule_result TEXT DEFAULT '',
    final_result TEXT DEFAULT '',
    final_decision TEXT DEFAULT '',
    task_id TEXT DEFAULT '',
    trace_id TEXT DEFAULT '',
    timestamp TEXT DEFAULT '',
    human_correction TEXT DEFAULT '',
    latency_ms INTEGER DEFAULT 0,
    token_usage INTEGER DEFAULT 0,
    failure_reason TEXT DEFAULT '',
    success INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    target_type TEXT DEFAULT '',
    target_id TEXT DEFAULT '',
    model_version TEXT DEFAULT '',
    system_result TEXT DEFAULT '',
    accepted TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_ai_call_provider ON ai_call_logs(provider);
CREATE INDEX IF NOT EXISTS idx_ai_call_created ON ai_call_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_call_success ON ai_call_logs(success);
-- Track3: new-column indexes created after migration in _migrate_schema
"""

# Track3：旧表迁移——为已存在的 ai_call_logs 表补齐缺失列（幂等）
_MIGRATION_COLUMNS = [
    ("input_text", "TEXT DEFAULT ''"),
    ("final_decision", "TEXT DEFAULT ''"),
    ("task_id", "TEXT DEFAULT ''"),
    ("trace_id", "TEXT DEFAULT ''"),
    ("timestamp", "TEXT DEFAULT ''"),
    # ZBC V2.0 双域隔离：域身份字段
    ("domain_id", "TEXT DEFAULT ''"),
    ("product_id", "TEXT DEFAULT ''"),
    ("output_hash", "TEXT DEFAULT ''"),
    # G2 (2026-09-06): 审计字段补全
    ("target_type", "TEXT DEFAULT ''"),
    ("target_id", "TEXT DEFAULT ''"),
    ("model_version", "TEXT DEFAULT ''"),
    ("system_result", "TEXT DEFAULT ''"),
    ("accepted", "TEXT DEFAULT ''"),
]


def _migrate_schema(conn):
    """对已存在的表执行 ALTER TABLE 补列（忽略已存在的列）。"""
    try:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(ai_call_logs)").fetchall()}
    except Exception:
        existing = set()
    for col, col_def in _MIGRATION_COLUMNS:
        if col not in existing:
            try:
                conn.execute(f"ALTER TABLE ai_call_logs ADD COLUMN {col} {col_def}")
            except Exception:
                pass
    # Track3: 在列存在后再创建索引（幂等）
    for idx_name, col in (("idx_ai_call_task", "task_id"), ("idx_ai_call_trace", "trace_id")):
        try:
            conn.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON ai_call_logs({col})")
        except Exception:
            pass


def _ensure_dir():
    d = os.path.dirname(DB_PATH)
    if d and not os.path.exists(d):
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass


# 脱敏：写入 input_text 前清除可能的 API key / token / cookie
_SENSITIVE_RE = re.compile(
    r'(?i)(api[_-]?key|access[_-]?token|secret|password|cookie|authorization|bearer|session[_-]?id)\s*[:=]\s*\S+',
)


def _sanitize_input(text: str) -> str:
    """对输入文本做敏感信息脱敏后再入库。"""
    if not text:
        return ''
    return _SENSITIVE_RE.sub(r'\1=[REDACTED]', str(text))


@contextmanager
def _get_conn():
    """获取 SQLite 连接（自动建表+迁移）。调用方应在短事务内使用。"""
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(_SCHEMA)
        _migrate_schema(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """显式初始化表结构（幂等，可在启动时调用）。"""
    try:
        with _get_conn() as conn:
            conn.execute("SELECT 1 FROM ai_call_logs LIMIT 1")
        return True
    except Exception as e:
        print(f'[AICallLogger] init_db failed: {e}')
        return False


# ============================================================
# 3) 输入哈希（不存原始 prompt，保护敏感内容）
# ============================================================
def compute_input_hash(*parts: Any) -> str:
    """对输入内容计算 SHA-256 哈希（前 32 位），用于去重和追溯，不存原文。"""
    h = hashlib.sha256()
    for p in parts:
        h.update(repr(p).encode('utf-8', errors='replace'))
        h.update(b'\x00')
    return h.hexdigest()[:32]


# ============================================================
# 4) 核心写入：log_call
# ============================================================
def log_call(
    provider: str = '',
    model: str = '',
    prompt_version: str = '',
    input_hash: str = '',
    input_text: str = '',
    output: str = '',
    confidence: float = 0.0,
    rule_result: str = '',
    final_result: str = '',
    final_decision: str = '',
    task_id: str = '',
    trace_id: str = '',
    timestamp: str = '',
    human_correction: str = '',
    latency_ms: int = 0,
    token_usage: int = 0,
    failure_reason: str = '',
    success: bool = True,
    domain_id: str = '',
    product_id: str = '',
    output_hash: str = '',
    # G2: 审计字段补全（可选，None→空，不破坏现有调用）
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    model_version: Optional[str] = None,
    system_result: Optional[str] = None,
    accepted: Optional[str] = None,
) -> Optional[int]:
    """
    记录一次 AI 调用。旁路写入：任何异常仅打印日志，不抛出。

    Track3：新增 input_text / final_decision / task_id / trace_id / timestamp。
    G2：新增 target_type / target_id / model_version / system_result / accepted。

    Returns:
        插入行的 id；失败返回 None。
    """
    try:
        out_str = str(output)[:4000] if output is not None else ''
        rule_str = str(rule_result)[:1000] if rule_result is not None else ''
        final_str = str(final_result)[:1000] if final_result is not None else ''
        decision_str = str(final_decision)[:1000] if final_decision is not None else ''
        corr_str = str(human_correction)[:1000] if human_correction is not None else ''
        fail_str = str(failure_reason)[:500] if failure_reason is not None else ''
        in_str = _sanitize_input(input_text)[:2000] if input_text else ''
        ts = timestamp or datetime.now().isoformat(timespec='seconds')
        # G2: 新字段 None→空串
        tt = str(target_type)[:100] if target_type is not None else ''
        tid = str(target_id)[:200] if target_id is not None else ''
        mv = str(model_version)[:100] if model_version is not None else ''
        sr = str(system_result)[:2000] if system_result is not None else ''
        acc = str(accepted)[:50] if accepted is not None else ''

        with _WRITE_LOCK:
            with _get_conn() as conn:
                cur = conn.execute(
                    """INSERT INTO ai_call_logs
                       (provider, model, prompt_version, input_hash, input_text, output,
                        confidence, rule_result, final_result, final_decision,
                        task_id, trace_id, timestamp, human_correction,
                        latency_ms, token_usage, failure_reason, success,
                        domain_id, product_id, output_hash,
                        target_type, target_id, model_version, system_result, accepted)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        provider or '', model or '', prompt_version or '',
                        input_hash or '', in_str, out_str,
                        float(confidence or 0.0),
                        rule_str, final_str, decision_str,
                        task_id or '', trace_id or '', ts, corr_str,
                        int(latency_ms or 0), int(token_usage or 0),
                        fail_str, 1 if success else 0,
                        domain_id or '', product_id or '', output_hash or '',
                        tt, tid, mv, sr, acc,
                    ),
                )
                return cur.lastrowid
    except Exception as e:
        # 旁路：日志写入失败绝不影响主链路
        print(f'[AICallLogger] log_call failed (bypass): {e}')
        return None


# ============================================================
# 5) 装饰器：@log_ai_call
# ============================================================
def log_ai_call(
    provider: str = '',
    model: str = '',
    prompt_version: str = '',
    task_id: str = '',
    trace_id: str = '',
    extract_output: Optional[Callable[[Any], str]] = None,
    extract_confidence: Optional[Callable[[Any], float]] = None,
    extract_tokens: Optional[Callable[[Any], int]] = None,
):
    """
    装饰器：包装 AI 调用函数，自动记录调用追踪。

    被装饰函数应返回 AI 结果（任意类型）。装饰器会：
    - 计算输入哈希（*args, **kwargs）
    - 计时
    - 调用原函数
    - 记录成功/失败、输出、延迟、task_id、trace_id
    - 失败时记录 failure_reason 并重新抛出原异常（不吞异常）

    Track3：新增 task_id / trace_id / input_text / final_decision 透传。
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            t0 = time.time()
            input_hash = compute_input_hash(func.__name__, args, kwargs)
            # 从 kwargs 提取 task_id / trace_id（如果调用方传入）
            _task_id = kwargs.pop('task_id', task_id) if 'task_id' in kwargs else task_id
            _trace_id = kwargs.pop('trace_id', trace_id) if 'trace_id' in kwargs else trace_id
            input_text = ''
            if args:
                input_text = ' '.join(str(a)[:500] for a in args[:3])
            try:
                result = func(*args, **kwargs)
                latency_ms = int((time.time() - t0) * 1000)

                # 提取输出/置信度/token
                out_text = ''
                if extract_output:
                    try:
                        out_text = extract_output(result) or ''
                    except Exception:
                        out_text = str(result)[:4000]
                elif isinstance(result, str):
                    out_text = result
                elif isinstance(result, dict):
                    out_text = json.dumps(result, ensure_ascii=False, default=str)[:4000]
                else:
                    out_text = str(result)[:4000]

                conf = 0.0
                if extract_confidence:
                    try:
                        conf = float(extract_confidence(result) or 0.0)
                    except Exception:
                        pass
                elif isinstance(result, dict):
                    conf = float(result.get('confidence', 0.0) or 0.0)

                tokens = 0
                if extract_tokens:
                    try:
                        tokens = int(extract_tokens(result) or 0)
                    except Exception:
                        pass

                # 从返回值提取 provider/model/final_decision（如果是 dict）
                prov = provider
                mod = model
                final_decision = ''
                if isinstance(result, dict):
                    prov = prov or str(result.get('provider', ''))
                    mod = mod or str(result.get('model', ''))
                    final_decision = str(result.get('final_decision', result.get('decision', '')))

                log_call(
                    provider=prov, model=mod, prompt_version=prompt_version,
                    input_hash=input_hash, input_text=input_text,
                    output=out_text, confidence=conf,
                    final_decision=final_decision,
                    task_id=_task_id, trace_id=_trace_id,
                    latency_ms=latency_ms, token_usage=tokens, success=True,
                    domain_id=kwargs.get('domain_id', ''),
                    product_id=kwargs.get('product_id', ''),
                )
                return result
            except Exception as exc:
                latency_ms = int((time.time() - t0) * 1000)
                log_call(
                    provider=provider, model=model, prompt_version=prompt_version,
                    input_hash=input_hash, input_text=input_text, output='', confidence=0.0,
                    task_id=_task_id, trace_id=_trace_id,
                    latency_ms=latency_ms, token_usage=0,
                    failure_reason=f'{type(exc).__name__}: {str(exc)[:300]}',
                    success=False,
                )
                raise  # 不吞异常，让上层降级逻辑处理
        return wrapper
    return decorator


# ============================================================
# 6) 查询接口（供 Evaluation 和审计使用）
# ============================================================
def query_calls(
    provider: str = '',
    success: Optional[bool] = None,
    task_id: str = '',
    trace_id: str = '',
    domain_id: str = '',
    product_id: str = '',
    target_type: str = '',
    target_id: str = '',
    limit: int = 100,
    offset: int = 0,
    since: str = '',
) -> List[Dict[str, Any]]:
    """查询 AI 调用日志。Track3：支持 task_id / trace_id 过滤。G2：支持 target_type / target_id。"""
    try:
        sql = "SELECT * FROM ai_call_logs WHERE 1=1"
        params: List[Any] = []
        if provider:
            sql += " AND provider = ?"
            params.append(provider)
        if success is not None:
            sql += " AND success = ?"
            params.append(1 if success else 0)
        if task_id:
            sql += " AND task_id = ?"
            params.append(task_id)
        if trace_id:
            sql += " AND trace_id = ?"
            params.append(trace_id)
        if domain_id:
            sql += " AND domain_id = ?"
            params.append(domain_id)
        if product_id:
            sql += " AND product_id = ?"
            params.append(product_id)
        if target_type:
            sql += " AND target_type = ?"
            params.append(target_type)
        if target_id:
            sql += " AND target_id = ?"
            params.append(target_id)
        if since:
            sql += " AND created_at >= ?"
            params.append(since)
        sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with _get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f'[AICallLogger] query_calls failed: {e}')
        return []


def get_stats(provider: str = '', since: str = '') -> Dict[str, Any]:
    """获取调用统计（供 Evaluation 使用）。"""
    try:
        sql = """SELECT
            COUNT(*) as total,
            SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as success_count,
            SUM(CASE WHEN success=0 THEN 1 ELSE 0 END) as failure_count,
            AVG(latency_ms) as avg_latency,
            SUM(token_usage) as total_tokens,
            AVG(confidence) as avg_confidence
            FROM ai_call_logs WHERE 1=1"""
        params: List[Any] = []
        if provider:
            sql += " AND provider = ?"
            params.append(provider)
        if since:
            sql += " AND created_at >= ?"
            params.append(since)
        with _get_conn() as conn:
            row = conn.execute(sql, params).fetchone()
            if not row:
                return {}
            d = dict(row)
            total = d.get('total', 0) or 0
            d['failure_rate'] = (d.get('failure_count', 0) or 0) / total if total else 0.0
            return d
    except Exception as e:
        print(f'[AICallLogger] get_stats failed: {e}')
        return {}


def record_human_correction(call_id: int, correction: str) -> bool:
    """
    人工修正反馈闭环：更新指定调用记录的 human_correction 字段。
    这是 AI Evaluation 的核心反馈入口。
    """
    try:
        with _WRITE_LOCK:
            with _get_conn() as conn:
                conn.execute(
                    "UPDATE ai_call_logs SET human_correction = ? WHERE id = ?",
                    (str(correction)[:1000], call_id),
                )
        return True
    except Exception as e:
        print(f'[AICallLogger] record_human_correction failed: {e}')
        return False


def get_correction_stats(since: str = '') -> Dict[str, Any]:
    """获取人工修正统计。"""
    try:
        sql = """SELECT
            COUNT(*) as total_with_correction,
            COUNT(DISTINCT provider) as providers
            FROM ai_call_logs WHERE human_correction != '' AND human_correction IS NOT NULL"""
        params: List[Any] = []
        if since:
            sql += " AND created_at >= ?"
            params.append(since)
        with _get_conn() as conn:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else {}
    except Exception as e:
        print(f'[AICallLogger] get_correction_stats failed: {e}')
        return {}


# ============================================================
# 7) 模块自描述：Provider 状态注册表（供审计报告引用）
# ============================================================
PROVIDER_STATUS = {
    'zhipu': 'ACTIVE',
    'glm': 'ACTIVE',          # zhipu 别名
    'ark': 'ACTIVE_FALLBACK',
    'doubao': 'ACTIVE_FALLBACK',
    'ollama': 'ACTIVE_FALLBACK',    # Track3：本地兜底模型，运行时探测后 ACTIVE
    'lmstudio': 'AVAILABLE',
    'llama_cpp': 'AVAILABLE',
    'qwen': 'NOT_CONFIGURED',
    'openai': 'DISABLED',
    'deepseek': 'NOT_CONFIGURED',
    'rule': 'RULE_FALLBACK',
    'local_rule': 'RULE_FALLBACK',
    'deterministic_rule': 'RULE_FALLBACK',
}


def get_provider_status(provider: str) -> str:
    return PROVIDER_STATUS.get(provider.lower(), 'UNKNOWN')


# 启动时自动建表（旁路，失败不影响）
init_db()
