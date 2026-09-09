from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1048576), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source = ROOT / "data" / "monitor.db"
    before = digest(source)
    isolated = args.output / "ollama-stopped-monitor.db"
    shutil.copy2(source, isolated)
    os.environ.update({
        "ZBC_DB_PATH": str(isolated),
        "LUMENIS_AI_RUNTIME_MODE": "LOCAL_ONLY",
        "CLOUD_AI_DISABLED": "1",
        "ZHIPU_DISABLED": "1",
        "LUMENIS_AI_EVIDENCE_DIR": str(args.output / "evidence"),
        "TAIKOO_AUTH_USER": "ollama-stopped-verifier",
        "TAIKOO_AUTH_PASSWORD": "ollama-stopped-verifier-session-only",
        "ZBC_GUARDIAN_ENABLED": "0",
    })
    from local_ai_runtime import LocalFirstAIService
    service = LocalFirstAIService()
    health = service.health(real_call=True)
    direct = service.analyze("Ollama 停止时核心仍需返回可解释结果。", mode="LOCAL_ONLY")
    from app import app
    app.config["TESTING"] = True
    client = app.test_client()
    token = base64.b64encode(b"ollama-stopped-verifier:ollama-stopped-verifier-session-only").decode()
    headers = {"Authorization": "Basic " + token}
    core = client.get("/api/health", headers=headers)
    analysis = client.post("/api/ai/analyze", headers=headers, json={"text": "服务不可用必须显式降级。", "runtime_mode": "LOCAL_ONLY"})
    payload = analysis.get_json(silent=True) or {}
    after = digest(source)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ollama_health": health,
        "direct_result": direct,
        "core_http_status": core.status_code,
        "analysis_http_status": analysis.status_code,
        "api_provider": (payload.get("analysis") or {}).get("provider"),
        "cloud_disabled": True,
        "source_db_untouched": before == after,
    }
    report["pass"] = all([
        health.get("status") == "DOWN",
        direct.get("provider") == "DETERMINISTIC_RULE",
        core.status_code == 200,
        analysis.status_code == 200,
        report["api_provider"] == "DETERMINISTIC_RULE",
        report["source_db_untouched"],
    ])
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
