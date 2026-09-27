"""Run one due-only public-baseline tick through the existing SYSTEM scheduler.

An OS task may invoke this without starting Flask, account flows, browsers, or
schema migrations. The signed source plan remains the collection authority.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ENV_KEYS = frozenset({
    "ZBC_DB_PATH", "LUMENIS_PRELAUNCH_BASELINE_CONFIG",
    "LUMENIS_PRELAUNCH_BASELINE_HMAC_KEY", "LUMENIS_EVIDENCE_HMAC_KEY_RING",
    "LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "LUMENIS_PUBLIC_SOURCE_DOH_FALLBACK",
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


def run_once() -> dict:
    from lumenis.shared.database import connect_sqlite, main_db_path
    from lumenis.system.collector.adapters.scheduling.prelaunch_baseline import (
        load_prelaunch_baseline_config, run_due_prelaunch_baseline,
    )

    # No database is opened, or created, when the signed plan is disabled.
    if load_prelaunch_baseline_config()["status"] == "DISABLED":
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
    result = run_due_prelaunch_baseline()
    # Raw source bodies, private settings and exception messages stay out of logs.
    return {key: result[key] for key in ("status", "reason", "plan_version", "summary")
            if key in result}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    args = parser.parse_args(argv)
    try:
        load_settings(args.env_file)
        result = run_once()
    except Exception as error:
        from lumenis.system.collector.adapters.scheduling.prelaunch_baseline import BaselineConfigError
        reason = error.code if isinstance(error, BaselineConfigError) else type(error).__name__
        result = {"status": "FAILED", "reason": reason}
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0 if result["status"] in {"COMPLETED", "DISABLED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
