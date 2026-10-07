from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "00-GOVERNANCE" / "LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json"


def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def state_path(contract: dict) -> Path:
    return ROOT / contract["dispatch"]["runtime_state_path"]


def current_published_head() -> str:
    for ref in ("origin/main", "HEAD"):
        proc = subprocess.run(
            ["git", "rev-parse", ref],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    return "UNKNOWN"


def blank_role() -> dict:
    return {
        "state": "ELIGIBLE",
        "task_id": None,
        "dispatch_ref": None,
        "admission_ref": None,
        "resume_condition": None,
        "blocked_reason": None,
        "closure_evidence": None,
        "updated_at": None,
    }


def init_state(contract: dict) -> dict:
    data = {
        "schema": "lumenis.live-dispatch/v1",
        "published_head": current_published_head(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "roles": {role: blank_role() for role in contract["roles"]},
    }
    path = state_path(contract)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def load_state(contract: dict) -> dict:
    path = state_path(contract)
    if not path.exists():
        return init_state(contract)
    return json.loads(path.read_text(encoding="utf-8"))


def validate_row(role: str, row: dict, contract: dict) -> None:
    allowed = set(contract["dispatch"]["allowed_states"])
    state = row.get("state")
    if state not in allowed:
        raise SystemExit(f"{role}: invalid state {state}")
    for field in contract["dispatch"]["state_requirements"][state]:
        if not row.get(field):
            raise SystemExit(f"{role}/{state}: missing {field}")


def save_state(data: dict, contract: dict) -> None:
    for role, row in data["roles"].items():
        validate_row(role, row, contract)
    data["published_head"] = current_published_head()
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = state_path(contract)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    contract = load_contract()
    parser = argparse.ArgumentParser(description="Local-only LUMENIS live dispatch ledger")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")
    sub.add_parser("show")
    sub.add_parser("validate")

    setter = sub.add_parser("set")
    setter.add_argument("role", choices=list(contract["roles"]))
    setter.add_argument("state", choices=contract["dispatch"]["allowed_states"])
    setter.add_argument("--task-id")
    setter.add_argument("--dispatch-ref")
    setter.add_argument("--admission-ref")
    setter.add_argument("--resume-condition")
    setter.add_argument("--blocked-reason")
    setter.add_argument("--closure-evidence")

    args = parser.parse_args()
    if args.cmd == "init":
        data = init_state(contract)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    data = load_state(contract)
    if args.cmd == "show":
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    if args.cmd == "validate":
        for role, row in data["roles"].items():
            validate_row(role, row, contract)
        print("LIVE DISPATCH: PASS")
        return

    row = data["roles"][args.role]
    for key in (
        "task_id",
        "dispatch_ref",
        "admission_ref",
        "resume_condition",
        "blocked_reason",
        "closure_evidence",
    ):
        value = getattr(args, key)
        if value is not None:
            row[key] = value
    row["state"] = args.state
    row["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Clear fields that would otherwise make a stale state look current.
    if args.state == "ELIGIBLE":
        data["roles"][args.role] = blank_role()
        data["roles"][args.role]["updated_at"] = datetime.now(timezone.utc).isoformat()
    validate_row(args.role, data["roles"][args.role], contract)
    save_state(data, contract)
    print(json.dumps(data["roles"][args.role], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
