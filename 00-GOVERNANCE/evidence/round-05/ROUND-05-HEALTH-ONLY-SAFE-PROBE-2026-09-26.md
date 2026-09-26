# ROUND 05 — isolated health-only startup probe

Status: **BOUNDED SOURCE AND LOOPBACK PROBE VERIFIED; ROUND 05 REWORK**
Date: 2026-09-26 20:26 Asia/Shanghai
Base: `a1ee3385baf9639602df4518c9da8b76d9c8639f` (`origin/main` fetched before review)

## Task Card and owner

SYSTEM Runtime owns `app.py` startup and `/healthz`. This Batch adds an explicit
`--internal-beta-acceptance --host 127.0.0.1` profile for a health-only safety
probe. It does not open a Workspace, count as Product E2E, start a resident
collector, or promote ROUND 05. Full-Core safe startup and real user-work E2E
remain open.

The profile requires a dedicated absolute `ZBC_DATA_DIR` under the OS temporary
root and an absolute `ZBC_DB_PATH` inside it. Validation happens before app
imports. Logs and XHS Cookie bridge path values remain in the disposable
directory; `.env`, Node profile discovery, scheduler, resident, heartbeat,
preflight, CDP and guardian startup are skipped. The first Flask
`before_request` hook permits only `GET /healthz`; all other requests return
`BLOCKED`/403 before later hooks or route handlers. Duplicate `--host` options
and relative data directories fail closed before imports.

## Verification at the exact candidate

- The agent's guarded import-only probe reported no protected XHS/browser path
  access, automatic effect, network call, subprocess or thread. Sol separately
  reviewed the patch and ran the checks below; this agent report does not
  replace future identity-safe full-Core E2E.
- In a clean archive of the fetched base with only the reviewed source/test
  candidate applied, 18 selected startup and neighboring health tests passed
  (`test_internal_beta_startup_gate.py`,
  `test_runtime_health_endpoint_contract.py`,
  `test_sys01_runtime_health_semantics.py`). Exit 0; no background-thread leak.
  An initial invocation named a file absent from this clean snapshot and
  exited 4; it is not counted as PASS.
- `py_compile` of changed Python files and
  `scripts/audit_tools/verify_ai_native_constitution.py` both passed.
- A real server launched from that archive on `127.0.0.1:8397` with a fresh
  temporary database and explicit inert XHS environment. `GET /healthz`
  returned 200 with database `ok`. `GET /api/xhs/accounts`,
  `POST /api/xhs/switch-account`, and `GET /workspace/CTH-01` each returned
  403 with `INTERNAL_BETA_HEALTH_ONLY`. The server was stopped and port 8397
  had zero listeners afterward. The temporary DB migrated to v17.
- Protected `data/monitor.db` remained 1,458,176 bytes with SHA-256
  `A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45`.

## 真实用户工作闭环验收 / REAL DELIVERY CARD

- **REAL USER JOB:** operator opens the internal Workspace and completes a
  scoped business task. This Batch proves only a safe health probe, so that
  job is **not accepted**.
- **ENTRY / REAL INPUT:** explicit local probe command, fresh disposable DB;
  no real business input.
- **END-TO-END PATH / USER-VISIBLE RESULT:** loopback `/healthz` reports core DB
  availability; business and account routes are intentionally blocked.
- **FAILURE / RECOVERY:** invalid host/storage fails before imports; forbidden
  requests return explicit 403. Full-Core service recovery is unverified.
- **EVIDENCE / ACCEPTANCE ASSERTION:** tests, live HTTP responses, clean stop
  and protected DB fingerprint establish only this narrow safety boundary.
  `REAL USER WORK E2E=NO`, `ROUND 05=REWORK`.
- **GLOBAL UNIVERSE / DATA MATURITY IMPACT:** Global Commercial Coverage,
  Global Brand Coverage and Guangzhou Taikoo Hui Reference Coverage remain
  unverified; no random entity data acceptance was attempted.
- **COMMERCIAL OVERLAY IMPACT:** `COMMERCIAL_READY=NO`; this probe is not a
  production server, internal beta release, or business result.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

Official [Flask 3.1 request-context documentation](https://flask.palletsprojects.com/en/stable/reqcontext/)
and [Flask API documentation](https://flask.palletsprojects.com/en/stable/api/)
were checked 2026-09-26 against installed Flask 3.1.3: a non-None
`before_request` response stops later request handling. The maintained
[Pallets Flask 3.1.3 release](https://github.com/pallets/flask/releases)
uses BSD-3-Clause; its
[deployment guidance](https://flask.palletsprojects.com/en/stable/deploying/)
limits the built-in server to local development. Decision: **ADAPT** the
existing Flask hook and explicit loopback bind inside SYSTEM Runtime; no new
runtime, dependency, data owner or AI capability. Further promotion requires
a separate full-Core safe mode, real user-work E2E, security/recovery review,
and rollout evidence.
