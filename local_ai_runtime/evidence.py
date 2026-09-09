from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .security import sanitize_trace


class EvidenceWriter:
    def __init__(self, directory: Path | None = None):
        configured = os.getenv("LUMENIS_AI_EVIDENCE_DIR", "").strip()
        self.directory = directory or (Path(configured) if configured else Path("data/ai_runtime_evidence"))
        self.directory = self.directory.resolve()
        self.path = self.directory / "ai-runtime-evidence.jsonl"
        self._lock = threading.Lock()

    def append(self, event_type: str, payload: dict[str, Any], trace_id: str) -> str:
        clean = sanitize_trace(payload)
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self.directory.mkdir(parents=True, exist_ok=True)
            previous = self._last_hash()
            body = {"event_type": event_type, "timestamp": timestamp, "trace_id": trace_id, "previous_hash": previous, "payload": clean}
            canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            evidence_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            record = {**body, "evidence_id": evidence_id}
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        return evidence_id

    def _last_hash(self) -> str:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return "GENESIS"
        try:
            last = self.path.read_text(encoding="utf-8").splitlines()[-1]
            return str(json.loads(last)["evidence_id"])
        except Exception:
            return "CORRUPT"

    def verify(self) -> bool:
        previous = "GENESIS"
        if not self.path.exists():
            return True
        for line in self.path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            evidence_id = record.pop("evidence_id")
            if record["previous_hash"] != previous:
                return False
            canonical = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != evidence_id:
                return False
            previous = evidence_id
        return True
