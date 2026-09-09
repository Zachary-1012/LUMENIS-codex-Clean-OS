from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PYTHON = Path(os.environ.get("LUMENIS_VERIFY_PYTHON", os.sys.executable))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class PeakSampler:
    def __init__(self) -> None:
        self.stop = threading.Event()
        self.peak_system_used_mb = 0
        self.peak_ollama_rss_mb = 0
        self.peak_cpu_percent = 0.0
        self.thread = threading.Thread(target=self._run, name="local-ai-resource-sampler", daemon=True)

    def _run(self) -> None:
        import psutil
        while not self.stop.wait(0.1):
            memory = psutil.virtual_memory()
            self.peak_system_used_mb = max(self.peak_system_used_mb, int(memory.used / 1048576))
            self.peak_cpu_percent = max(self.peak_cpu_percent, float(psutil.cpu_percent(interval=None)))
            rss = 0
            for process in psutil.process_iter(["name", "memory_info"]):
                try:
                    if "ollama" in (process.info["name"] or "").lower():
                        rss += int(process.info["memory_info"].rss / 1048576)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            self.peak_ollama_rss_mb = max(self.peak_ollama_rss_mb, rss)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.stop.set()
        self.thread.join(timeout=2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    os.environ.update({
        "LUMENIS_AI_RUNTIME_MODE": "LOCAL_ONLY",
        "CLOUD_AI_DISABLED": "1",
        "ZHIPU_DISABLED": "1",
        "ZBC_TEST_OFFLINE": "1",
        "LUMENIS_AI_EVIDENCE_DIR": str(args.output / "runtime-evidence"),
        "TAIKOO_AUTH_USER": "local-ai-verifier",
        "TAIKOO_AUTH_PASSWORD": "local-ai-verifier-session-only",
    })
    source_db = ROOT / "data" / "monitor.db"
    source_db_mtime = source_db.stat().st_mtime_ns
    source_db_hash = sha256(source_db)
    isolated_db = args.output / "isolated-monitor.db"
    shutil.copy2(source_db, isolated_db)
    os.environ["ZBC_DB_PATH"] = str(isolated_db)

    public_attempts: list[str] = []
    original_create_connection = socket.create_connection

    def guarded_create_connection(address, *a, **kw):
        host = str(address[0] if isinstance(address, tuple) else address).strip("[]").lower()
        if host not in {"127.0.0.1", "localhost", "::1"}:
            public_attempts.append(host)
            raise ConnectionRefusedError("ZERO_CLOUD outbound guard blocked public endpoint")
        return original_create_connection(address, *a, **kw)

    socket.create_connection = guarded_create_connection
    from local_ai_runtime import LocalFirstAIService
    from local_ai_runtime.benchmark import run_acceptance
    from local_ai_runtime.ollama import OllamaAdapter
    from local_ai_runtime.registry import AIRuntimeRegistry
    from local_ai_runtime.research import ResearchBudget, ResearchOptimizer

    registry = AIRuntimeRegistry()
    model = registry.model(registry.runtime["default_model"])
    weight = Path(model["weight_source"])
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
        "runtime_mode": "LOCAL_ONLY",
        "cloud_flags": {"CLOUD_AI_DISABLED": "1", "ZHIPU_DISABLED": "1"},
        "model_registry": model,
        "weight_checksum_pass": weight.is_file() and sha256(weight) == model["checksum"].split(":", 1)[1],
    }

    with PeakSampler() as sampler:
        service = LocalFirstAIService(evidence_dir=args.output / "runtime-evidence")
        report["health"] = service.health(real_call=True)
        report["health_stability"] = [service.health(real_call=True) for _ in range(2)]
        stream = "".join(service.adapter.chat_stream("简洁回答。", "只回答：流式通过", max_tokens=16))
        report["streaming"] = {"pass": bool(stream.strip()), "content_hash": hashlib.sha256(stream.encode()).hexdigest()}
        business = service.analyze(
            "用户投诉停车等待时间过长，尚未获得官方核实。",
            task_type="sentiment",
            mode="LOCAL_ONLY",
            evidence_ids=["verification-business-input-1"],
        )
        report["business_analysis"] = business
        report["acceptance"] = run_acceptance(service, args.output / "model-acceptance.json")

        race_text = "活动现场秩序正常，用户反馈整体满意，但样本仅有三条。"
        before = service.analyze(race_text, task_type="performance_baseline", mode="LOCAL_ONLY")
        after = service.analyze(race_text, task_type="performance_candidate", mode="LOCAL_ONLY")
        equivalent = all(before[key] == after[key] for key in ("sentiment", "fact_basis"))
        race_keep = equivalent and after["latency_ms"] <= before["latency_ms"]
        report["performance_race"] = {
            "before_latency_ms": before["latency_ms"], "after_latency_ms": after["latency_ms"],
            "quality_equivalence": equivalent, "latency_delta_ms": after["latency_ms"] - before["latency_ms"],
            "result": "KEEP" if race_keep else "REJECT",
        }

        optimizer = ResearchOptimizer(ResearchBudget(max_iterations=1, max_runtime_seconds=5, max_model_calls=0, max_resource_mb=128))
        sample = {"evidence": list(range(200)), "status": "SHADOW"}
        research = optimizer.run(
            "compact-evidence-json",
            lambda: json.dumps(sample, ensure_ascii=False, indent=2),
            lambda: json.dumps(sample, ensure_ascii=False, separators=(",", ":")),
            lambda a, b: json.loads(a) == json.loads(b),
        )
        report["auto_research"] = research

        unavailable = LocalFirstAIService(
            evidence_dir=args.output / "failure-evidence",
            adapter=OllamaAdapter("http://127.0.0.1:11999", registry.runtime["default_model"], timeout=1),
        )
        down_health = unavailable.health(real_call=True)
        down_result = unavailable.analyze("核心服务仍需返回确定性结果。", mode="LOCAL_ONLY")
        report["local_failure"] = {"health": down_health, "result": down_result, "core_alive": True}

        hybrid = service.analyze("品牌活动现场反馈正常。", mode="HYBRID")
        report["hybrid"] = {"provider": hybrid["provider"], "fallback": hybrid["fallback"], "pass": hybrid["provider"] == "OLLAMA_LOCAL"}

        from app import app
        app.config["TESTING"] = True
        client = app.test_client()
        token = base64.b64encode(b"local-ai-verifier:local-ai-verifier-session-only").decode()
        headers = {"Authorization": "Basic " + token}
        api_started = time.perf_counter()
        core_response = client.get("/api/health", headers=headers)
        api_response = client.post(
            "/api/ai/analyze",
            headers=headers,
            json={"text": "用户表示活动体验满意，当前仅依据该条文本。", "type": "sentiment", "runtime_mode": "LOCAL_ONLY"},
        )
        api_payload = api_response.get_json(silent=True) or {}
        test_response = client.post(
            "/api/ai/test",
            headers=headers,
            json={"text": "本地连接测试。", "runtime_mode": "LOCAL_ONLY"},
        )
        test_payload = test_response.get_json(silent=True) or {}
        report["business_api_e2e"] = {
            "core_status": core_response.status_code,
            "api_status": api_response.status_code,
            "provider": (api_payload.get("analysis") or {}).get("provider"),
            "structured": all(key in (api_payload.get("analysis") or {}) for key in ("summary", "sentiment", "confidence", "trace_id", "evidence_id")),
            "wall_time_ms": int((time.perf_counter() - api_started) * 1000),
            "test_api_status": test_response.status_code,
            "test_api_provider": (test_payload.get("analysis") or {}).get("provider"),
        }

        db_started = time.perf_counter()
        with sqlite3.connect(isolated_db) as connection:
            table_count = int(connection.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0])
        report["execution_efficiency"] = {
            "python_runtime": os.sys.version.split()[0],
            "sqlite_table_count": table_count,
            "sqlite_catalog_latency_ms": round((time.perf_counter() - db_started) * 1000, 3),
            "database_bytes": isolated_db.stat().st_size,
            "gpu_kernel": "NOT_REQUIRED_FOR_CURRENT_NODE",
            "worker_browser_agent_deep_profile": "NOT_REQUIRED_FOR_THIS_LOCAL_AI_GATE",
        }

    report["resource"] = {
        "peak_system_used_mb": sampler.peak_system_used_mb,
        "peak_ollama_process_rss_mb": sampler.peak_ollama_rss_mb,
        "peak_cpu_percent": sampler.peak_cpu_percent,
    }
    report["zero_cloud"] = {"public_connection_attempts": public_attempts, "pass": not public_attempts}
    report["evidence_chain_pass"] = service.evidence.verify()
    source_after_hash = sha256(source_db)
    report["isolated_database"] = {
        "path": str(isolated_db),
        "source_before_sha256": source_db_hash,
        "source_after_sha256": source_after_hash,
        "source_untouched": source_db.stat().st_mtime_ns == source_db_mtime and source_after_hash == source_db_hash,
    }
    report["critical_e2e_pass"] = all([
        report["health"].get("real_call_verified"),
        all(item.get("real_call_verified") for item in report["health_stability"]),
        report["business_analysis"].get("provider") == "OLLAMA_LOCAL",
        report["business_api_e2e"]["core_status"] == 200,
        report["business_api_e2e"]["api_status"] == 200,
        report["business_api_e2e"]["provider"] == "OLLAMA_LOCAL",
        report["business_api_e2e"]["test_api_status"] == 200,
        report["business_api_e2e"]["test_api_provider"] == "OLLAMA_LOCAL",
        report["business_api_e2e"]["structured"],
        report["zero_cloud"]["pass"],
        report["evidence_chain_pass"],
        report["local_failure"]["result"].get("provider") == "DETERMINISTIC_RULE",
        report["acceptance"].get("quality_score", 0) >= 0.8,
        report["acceptance"].get("local_provider_pass"),
        report["weight_checksum_pass"],
        report["isolated_database"]["source_untouched"],
    ])
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "critical_e2e_pass": report["critical_e2e_pass"],
        "health": report["health"],
        "business_provider": report["business_analysis"].get("provider"),
        "api_e2e": report["business_api_e2e"],
        "zero_cloud": report["zero_cloud"],
        "resource": report["resource"],
        "acceptance": report["acceptance"],
        "performance_race": report["performance_race"],
        "auto_research": report["auto_research"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["critical_e2e_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
