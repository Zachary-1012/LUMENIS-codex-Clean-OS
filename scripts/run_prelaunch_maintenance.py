"""Run signed due acquisition, then retained Source processing in SYSTEM.

The existing scheduler may recover its approved managed platform workers. This
entry does not start Flask or migrate schemas; the signed plan remains authority.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ENV_KEYS = frozenset({
    "ZBC_DB_PATH", "LUMENIS_PRELAUNCH_BASELINE_CONFIG",
    "LUMENIS_PRELAUNCH_BASELINE_HMAC_KEY", "LUMENIS_EVIDENCE_HMAC_KEY_RING",
    "LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "LUMENIS_PUBLIC_SOURCE_DOH_FALLBACK",
    "DOUYIN_CDP_URL", "DOUYIN_LOCAL_WORKER_ENABLED", "DOUYIN_LOCAL_WORKER_ACCOUNT",
    "X_READONLY_CDP_URL", "X_READONLY_LOCAL_WORKER_ENABLED", "X_READONLY_LOCAL_WORKER_ACCOUNT",
    "INSTAGRAM_READONLY_CDP_URL", "INSTAGRAM_READONLY_LOCAL_WORKER_ENABLED",
    "INSTAGRAM_READONLY_LOCAL_WORKER_ACCOUNT",
    "FACEBOOK_READONLY_CDP_URL", "FACEBOOK_READONLY_LOCAL_WORKER_ENABLED",
    "FACEBOOK_READONLY_LOCAL_WORKER_ACCOUNT",
})


def load_settings(path: Path) -> None:
    """Load only this service's private settings; never print their values."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in ENV_KEYS and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


def run_once(*, post_intake_only=False) -> dict:
    # Imports, DB checks, and the existing scheduler can transitively emit
    # diagnostics to stdout. Keep the task's stdout reserved for the JSON line.
    with redirect_stdout(io.StringIO()):
        from lumenis.shared.database import connect_sqlite, main_db_path
        from lumenis.system.collector.adapters.scheduling.prelaunch_baseline import (
            load_prelaunch_baseline_config, run_due_prelaunch_baseline,
        )

        # No database is opened, or created, when the signed plan is disabled.
        if load_prelaunch_baseline_config(expand_registry=False)["status"] == "DISABLED":
            return {"status": "DISABLED"}
        db = Path(main_db_path())
        if not db.is_file():
            return {"status": "FAILED", "reason": "PRODUCT_DB_UNAVAILABLE"}
        connection = connect_sqlite(str(db), read_only=True)
        try:
            row = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()
            if not row or int(row[0] or 0) < 18:
                return {"status": "FAILED", "reason": "PRODUCT_SCHEMA_REQUIRES_V18"}
        finally:
            connection.close()
        phase_elapsed_ms = {}
        # New permitted acquisition must not wait behind historical Source and
        # keyword scans. Each acquisition still commits its originals before
        # derivative processing; scheduler claims/cursors remain its sole owner.
        result = None
        if not post_intake_only:
            started = time.monotonic()
            try:
                result = run_due_prelaunch_baseline()
            except Exception as error:
                # Preserve the failure while still recovering committed Source.
                # Exception text can contain private inputs and is never logged.
                reason = getattr(error, "code", None)
                if not isinstance(reason, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,100}", reason):
                    reason = type(error).__name__
                result = {"status": "FAILED", "reason": reason}
            finally:
                phase_elapsed_ms["due_acquisition"] = round((time.monotonic() - started) * 1000)
        # Processing dependencies stop only their use, never erase committed
        # originals or prevent the next signed scheduler cycle from running.
        started = time.monotonic()
        try:
            from lumenis.system.collector.adapters.secondary_collection import (
                process_prelaunch_keyword_backlog, recover_prelaunch_pending_sources,
            )
            pending_sources = recover_prelaunch_pending_sources()
        except Exception:
            pending_sources = {"status": "FAILED", "reason": "PENDING_SOURCE_RECOVERY_UNAVAILABLE"}
        finally:
            phase_elapsed_ms["pending_source_recovery"] = round((time.monotonic() - started) * 1000)
        started = time.monotonic()
        try:
            from lumenis.system.collector.adapters.secondary_collection import process_prelaunch_keyword_backlog
            post_intake = process_prelaunch_keyword_backlog()
        except Exception:
            post_intake = {"status": "FAILED", "reason": "POST_INTAKE_PROCESSING_UNAVAILABLE"}
        finally:
            phase_elapsed_ms["keyword_processing"] = round((time.monotonic() - started) * 1000)
        safe_post_intake = {key: post_intake[key] for key in (
            "status", "reason", "processed", "saved", "pending", "owned_inference") if key in post_intake}
        reasons = {}
        for item in post_intake.get("results", []):
            code = item.get("reason")
            if isinstance(code, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{0,100}", code):
                reasons[code] = reasons.get(code, 0) + 1
        safe_post_intake["pending_reasons"] = reasons
        safe_post_intake["source_recovery"] = {
            key: pending_sources[key] for key in (
                "status", "reason", "processed", "saved", "native_detail_unavailable",
                "canonical_rows_created", "network_collection", "scope_status") if key in pending_sources}
        if post_intake_only:
            return {"status": "COMPLETED" if all(item.get("status") in {
                    "COMPLETED", "DISABLED"} for item in (pending_sources, post_intake))
                    else "PARTIAL", "post_intake": safe_post_intake,
                    "summary": {"maintenance_phase_elapsed_ms": phase_elapsed_ms}}
        # Raw run records, source bodies, private settings, and exception text
        # stay out of the task log; only bounded categorical statuses survive.
        safe_result = {key: result[key] for key in ("status", "reason", "plan_version", "summary")
                       if key in result}
        summary = safe_result.get("summary")
        safe_result["summary"] = {
            **(summary if isinstance(summary, dict) else {}),
            "maintenance_phase_elapsed_ms": phase_elapsed_ms,
        }
        if safe_result.get("status") == "COMPLETED" and any(
                item.get("status") not in {"COMPLETED", "DISABLED"}
                for item in (pending_sources, post_intake)):
            safe_result["status"] = "PARTIAL"
        safe_result["post_intake"] = safe_post_intake
        runs = result.get("runs")
        if isinstance(runs, list):
            run_status_counts = {}
            observed_counts = {}
            outcome_fields = {
                "returned_count": "observed_items_sum",
                "imported": "imported_rows_sum",
                "updated": "updated_rows_sum",
                "canonical_synced": "canonical_refresh_rows_sum",
                "review_pending_count": "review_pending_sum",
            }
            intake_fields = {
                "originals_saved": "source_originals_saved_sum",
                "originals_pending": "source_originals_pending_sum",
                "covers_saved": "covers_saved_sum",
                "keyword_analyses_saved": "keyword_analyses_saved_sum",
                "keyword_analyses_pending": "keyword_analyses_pending_sum",
            }
            for item in runs:
                status = item.get("status") if isinstance(item, dict) else None
                if not isinstance(status, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", status):
                    status = "UNKNOWN"
                run_status_counts[status] = run_status_counts.get(status, 0) + 1
                result = item.get("result") if isinstance(item, dict) else None
                if isinstance(result, dict):
                    for source_field, sum_field in outcome_fields.items():
                        value = result.get(source_field)
                        if type(value) is int and value >= 0:
                            observed_counts[sum_field] = observed_counts.get(sum_field, 0) + value
                        else:
                            missing_field = source_field + "_unknown_attempts"
                            observed_counts[missing_field] = observed_counts.get(missing_field, 0) + 1
                    intake = result.get("source_intake")
                    if isinstance(intake, dict):
                        for source_field, sum_field in intake_fields.items():
                            value = intake.get(source_field)
                            if type(value) is int and value >= 0:
                                observed_counts[sum_field] = observed_counts.get(sum_field, 0) + value
                            else:
                                missing_field = source_field + "_unknown_attempts"
                                observed_counts[missing_field] = observed_counts.get(missing_field, 0) + 1
                    else:
                        observed_counts["source_intake_unknown_attempts"] = (
                            observed_counts.get("source_intake_unknown_attempts", 0) + 1)
            summary = safe_result.get("summary")
            if isinstance(summary, dict):
                safe_result["summary"] = {
                    **summary,
                    "run_status_counts": dict(sorted(run_status_counts.items())),
                    "observed_outcomes": observed_counts,
                }
        return safe_result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--post-intake-only", action="store_true",
                        help="Resume permitted processing of existing Source originals; no network collection.")
    args = parser.parse_args(argv)
    try:
        load_settings(args.env_file)
        result = run_once(post_intake_only=args.post_intake_only)
    except Exception as error:
        with redirect_stdout(io.StringIO()):
            from lumenis.system.collector.adapters.scheduling.prelaunch_baseline import BaselineConfigError
            reason = error.code if isinstance(error, BaselineConfigError) else type(error).__name__
        result = {"status": "FAILED", "reason": reason}
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0 if result["status"] in {"COMPLETED", "DISABLED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
