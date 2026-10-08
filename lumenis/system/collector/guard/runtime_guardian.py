"""Lease-based runtime recovery composed from the existing collector queue.

Workers receive leases through ``TaskQueue``; this guardian supplies the
operational boundary missing from the queue: heartbeat/checkpoint forwarding,
stale-worker reaping, bounded retry, terminal DLQ capture, and an append-only
recovery audit.  It does not replace the scheduler or collector.
"""
import json
import os
import time

from lumenis.shared.database.registry import get_data_dir
from .dlq_replay import DeadLetterQueue
from .queue_worker import QueueWorker


class RuntimeGuardian:
    """Make queue-worker failure observable and recoverable without fake success."""

    def __init__(self, queue, processor, *, worker_id=None, heartbeat_timeout=120,
                 dlq=None, audit_path=None):
        self.queue = queue
        self.worker = QueueWorker(queue, processor, worker_id=worker_id)
        self.heartbeat_timeout = float(heartbeat_timeout)
        self.dlq = dlq or DeadLetterQueue()
        self.audit_path = audit_path or os.path.join(
            get_data_dir(), "collector_guard", "recovery_audit.jsonl")

    def process_once(self):
        return self.worker.process_once()

    def _owns_attempt_receipt(self, worker_id, lease_owner):
        """Reject receipts from workers other than this guardian's worker."""
        return (worker_id == self.worker.worker_id
                and lease_owner == self.worker.lease_owner)

    def heartbeat(self, task_id, *, run_id=None, worker_id=None, lease_owner=None):
        """Renew a lease only with the complete receipt returned by dequeue."""
        if not self._owns_attempt_receipt(worker_id, lease_owner):
            return False
        return self.queue.heartbeat(
            task_id, worker_id, run_id=run_id, lease_owner=lease_owner)

    def checkpoint(self, task_id, checkpoint_id, *, run_id=None, worker_id=None,
                   lease_owner=None):
        """Persist progress only for this guardian's active queue attempt."""
        if not self._owns_attempt_receipt(worker_id, lease_owner):
            return False
        return self.queue.checkpoint(
            task_id, worker_id, checkpoint_id,
            run_id=run_id, lease_owner=lease_owner)

    def reap(self):
        """Recover stale leases; terminal failures are retained in the DLQ."""
        ids = self.queue.reap_stale(self.heartbeat_timeout)
        failed = {row["id"]: row for row in self.queue.list_by_status("failed", limit=1000)}
        events = []
        for task_id in ids:
            row = failed.get(task_id)
            event = {"task_id": task_id, "event": "STALE_WORKER_RECOVERED",
                     "recovered_at": time.time(),
                     "status": "DEAD_LETTER" if row else "RETRYING"}
            if row:
                self.dlq.enqueue(row["task_type"], error=row.get("last_error") or "heartbeat timeout",
                                 context={"queue_task_id": task_id,
                                          "recovery_reason": "heartbeat timeout"},
                                 run_type="runtime_guardian")
            self._audit(event)
            events.append(event)
        return events

    def status(self):
        stats = self.queue.stats()
        return {"worker_id": self.worker.worker_id,
                "heartbeat_timeout": self.heartbeat_timeout,
                "queue": stats, "dlq": self.dlq.stats(),
                "status": "DEGRADED" if stats.get("running", 0) else "HEALTHY"}

    def _audit(self, event):
        directory = os.path.dirname(self.audit_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.audit_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
