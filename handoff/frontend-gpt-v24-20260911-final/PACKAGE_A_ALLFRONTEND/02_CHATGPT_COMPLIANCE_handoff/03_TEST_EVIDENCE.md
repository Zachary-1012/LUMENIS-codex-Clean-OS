# 03 — Test Evidence (real commands, deterministic gates only)

No "passed" claim without command + result. Raw outputs in `evidence/`. Higher-cost
ladders (MCP contract/integration/inspector/E2E) were NOT run because no public server exists;
they are queued for Codex in `05_NEXT_CODEX_PROMPT.md`.

| # | Command (run from repo / D:\LUMENIS_REBUILD) | Exit | Result |
|---|---|---|---|
| T1 | `python _syntax_audit.py` (222 JSON parse + dup-key + BOM; 13 JS `node --check`; 22 Python `py_compile`; 6 CSS / 89 HTML balance; YAML) | 0 | TOTAL FINDINGS **0** post-fix |
| T2 | `node --check` per JS (inside T1) | 0 | 13/13 clean |
| T3 | `py_compile` per Python (inside T1) | 0 | 22/22 clean |
| T4 | `python experience_v2/18_validation/validate_handoff.py` (from `experience_v2/build`) | 0 | `VALIDATE 34/34` |
| T5 | `python _secret_scan.py` (high-confidence secret patterns over experience_v2) | 0 | 367 text files, **0** secret hits |

## JSON hard-acceptance (supplement mandate)
- JSON_PARSE_ERRORS = 0 (after the single 18-escape fix; rescan confirms)
- SYNTAX_ERRORS = 0
- NEW_CONFIG_PARSE_FAILURES = 0

## Validation commands a human can re-run
```powershell
$env:PYTHONPATH="D:\lum-toolchain\pylibs"
cd D:\LUMENIS_REBUILD
python _syntax_audit.py
python _secret_scan.py
cd LUMENIS-codex-Clean-OS\experience_v2\build
python ..\18_validation\validate_handoff.py
```
