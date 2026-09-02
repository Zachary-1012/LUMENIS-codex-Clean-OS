# -*- coding: utf-8 -*-
"""Dead-Letter Queue + 恢复重放（研究自 baldurhq/baldur 的 DLQ-replay 范式，落地 ZBC 采集）。

来源范式（baldur README/concepts/foundations/dlq-replay.md，Apache-2.0）：
  "A call that fails for good is captured with its context and replayed once the
   dependency recovers. Replay is for work that failed on the way out, never for
   a business rejection."
  + 墙钟总预算（wall-clock budget）约束所有重试：SDK 自身最坏 = timeout×(retries+1)。

ZBC 落地（服务「数据零丢失」红线）：
  - 采集关键词任务失败（风控/网络/登录失效等**基础设施类失败**）-> 捕获上下文入 JSONL DLQ
  - 恢复期（schedule ramp_up / 手动补采）-> replay：逐条重放成功即 ack，失败保留不丢
  - 业务拒绝（如用户主动暂停、非法参数）不应当入队（由调用方判断 is_business_rejection）

数据零丢失：DLQ 是追加式 JSONL，失败任务永不丢失，直到显式 ack/archive。
"""
import datetime
import io
import json
import os
import threading
import uuid

DEFAULT_DLQ_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "data", "collector_dlq.jsonl")


class DeadLetterQueue:
    """追加式 JSONL 死信队列（线程安全）。每条含唯一 task_id + 上下文 + 错误 + 重试计数。"""

    def __init__(self, path=None, max_attempts=5):
        self.path = path or DEFAULT_DLQ_PATH
        self.max_attempts = max_attempts
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def _append(self, rec):
        with self._lock, io.open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def enqueue(self, keyword, *, error, context=None, run_type="manual", is_business_rejection=False):
        """入队一个失败任务。业务拒绝返回 None（不写 DLQ）。"""
        if is_business_rejection:
            return None
        rec = {
            "task_id": uuid.uuid4().hex[:16],
            "keyword": keyword,
            "error": error or "unknown",
            "context": context or {},
            "run_type": run_type,
            "attempts": 1,
            "created_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "status": "pending",
        }
        self._append(rec)
        return rec["task_id"]

    def list_pending(self):
        """读取全部 pending 任务（只读，重放决策用）。"""
        if not os.path.exists(self.path):
            return []
        out = []
        with io.open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("status") == "pending":
                    out.append(rec)
        return out

    def _rewrite(self, recs):
        with self._lock, io.open(self.path, "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    def ack(self, task_id):
        """重放成功：标记 done（保留审计轨迹）。"""
        recs = self._all()
        changed = False
        for r in recs:
            if r.get("task_id") == task_id and r.get("status") == "pending":
                r["status"] = "done"
                r["acked_at"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                changed = True
        if changed:
            self._rewrite(recs)
        return changed

    def fail_retry(self, task_id, error):
        """重放失败：attempts+1，超阈值标记 dead（不再自动重放，但保留记录）。"""
        recs = self._all()
        for r in recs:
            if r.get("task_id") == task_id and r.get("status") == "pending":
                r["attempts"] = r.get("attempts", 0) + 1
                r["last_error"] = error or ""
                r["last_try_at"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                if r["attempts"] >= self.max_attempts:
                    r["status"] = "dead"
                    r["dead_at"] = r["last_try_at"]
        self._rewrite(recs)

    def _all(self):
        if not os.path.exists(self.path):
            return []
        out = []
        with io.open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
        return out

    def stats(self):
        """DLQ 统计：pending / done / dead / 总条数（真实计数）。"""
        recs = self._all()
        from collections import Counter
        c = Counter(r.get("status", "unknown") for r in recs)
        return {"total": len(recs), "pending": c.get("pending", 0),
                "done": c.get("done", 0), "dead": c.get("dead", 0)}

    def replay(self, handler, *, max_items=50):
        """恢复期重放：对 pending 任务逐个 handler(keyword, context) -> 成功 ack / 失败 fail_retry。
        返回 (ok_count, fail_count)。handler 抛异常视为失败。"""
        pending = self.list_pending()[:max_items]
        ok = fail = 0
        for rec in pending:
            tid = rec["task_id"]
            try:
                handler(rec.get("keyword", ""), rec.get("context") or {})
                if self.ack(tid):
                    ok += 1
            except Exception as e:
                self.fail_retry(tid, str(e))
                fail += 1
        return ok, fail
