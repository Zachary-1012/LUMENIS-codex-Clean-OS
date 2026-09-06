# ZBC Phase 16 — Code Quality & Configuration Audit Report

> **Date**: 2026-09-06
> **Branch**: feat/zbc-full-upgrade-v1
> **HEAD**: 5e0ccd0
> **Auditor**: ZBC Phase 16 Automated Scan + Manual Review
> **Tool**: `code_quality_report.py` (AST-based, repeatable)

---

## 1. Executive Summary

| Category | Count | Severity |
|---|---|---|
| Production Python files scanned | 369 | — |
| Scratch/debug files identified | 68 | INFO |
| Unused imports | 303 (164 files) | LOW |
| Dead code (unreferenced funcs/classes) | 1253 | LOW-MED (high false-positive rate) |
| Duplicate code groups | 4 (8 functions) | MED |
| Hidden side effects | 535 (105 files) | MED |
| Circular dependencies | 1 | MED |
| Secret findings (pre-fix) | 5 (1 prod false-positive, 4 scratch real) | **P0** |
| Hardcoded local paths (production) | 0 | CLEAN |
| Hardcoded non-standard ports | 49 | LOW |
| Merge conflicts (pre-fix) | 6 markers in 5 files | **P0** |
| Config keys in .env not in .env.example (pre-fix) | 21 | MED |
| Config keys in .env not in config.py known_keys (pre-fix) | 44 | MED |

### P0 Issues Fixed
1. **Real Twitter cookies in scratch files** — `_parse_x_cookie.py`, `_parse_x_cookie_v2.py` contained live `auth_token`, `ct0`, `g_state` cookie values. Sanitized with `REDACTED_*` placeholders.
2. **Unresolved git merge conflicts** — 6 conflict markers across 5 files (`auth_recovery_center.py`, `brand_knowledge_base.py`, `case_deep_analysis.py`, `lumenis_skill_adapter.py`, `_split_report_api.py`, `case_ai_evaluate.py`). All resolved keeping HEAD (current branch).
3. **Module-level .env file I/O in `case_ai_evaluate.py`** — Replaced direct `io.open(resolve_path('.env'))` with `os.environ.get('ZHIPU_API_KEY')` (already present in HEAD version of merge conflict).

---

## 2. Secret Leak Check Results

### Pre-Fix Findings
| File | Line | Type | Status |
|---|---|---|---|
| `_parse_x_cookie.py` | 8 | Twitter auth_token (real) | **SANITIZED** |
| `_parse_x_cookie.py` | 9 | Twitter ct0 token (real) | **SANITIZED** |
| `_parse_x_cookie_v2.py` | 7 | Twitter auth_token (real) | **SANITIZED** |
| `_parse_x_cookie_v2.py` | 8 | Twitter ct0 token (real) | **SANITIZED** |
| `security_boundary.py` | 957 | `sk-12345678901234567890` | FALSE POSITIVE (test string for redaction verification) |

### Post-Fix Status
- **Production code: 0 real secrets**
- **Scratch files: 0 real secrets** (all sanitized)
- `.env` file: contains real keys as expected (gitignored, not in source)
- No API keys, tokens, or passwords hardcoded in production Python source

### Secret Scan Patterns Used
- `sk-[A-Za-z0-9]{20,}` (OpenAI-style)
- `ark-[0-9a-f]{8,}-[0-9a-f]{4,}` (Volcano ARK)
- `[0-9a-f]{32}\.[0-9a-zA-Z]{20,}` (Zhipu GLM)
- `auth_token[0-9a-f]{30,}` / `ct0[0-9a-f]{30,}` (Twitter)
- `PC_TOKEN`, `SESSDATA`, `access-token-creator.xiaohongshu.com` (platform cookies)
- `-----BEGIN PRIVATE KEY-----`

---

## 3. Dead Code Inventory

**Total: 1253 unreferenced top-level functions/classes across production code.**

> **Important caveat**: This metric has a high false-positive rate due to:
> - Dynamic imports via `importlib` / string-based module loading
> - Flask route registration via decorators (functions referenced by URL routing, not direct import)
> - Plugin/registry patterns where classes are registered by string name
> - CLI entry points invoked as `python module.py`
> - Functions referenced in templates, config JSON, or database records

**Top files with most dead code candidates** (manual review recommended before any deletion):
- Per AGENTS.md protocol: **no deletion without Dependency Trace → Evidence → Classification → Test → Delete**

---

## 4. Duplicate Code Inventory

All 4 duplicate groups are in `deployment/` directory — duplicate copies with mojibake (garbled Chinese) filenames:

| Hash | Functions | Files |
|---|---|---|
| `0a35b636` | `list_backups` | `deployment/deployment/数据库备份.py` + `deployment/数据库备份.py` |
| `bedb5d6c` | `cleanup_old_backups` | same pair |
| `9a0c98b0` | `main` | same pair |
| `77d5c550` | `main` | `deployment/deployment/健康检查.py` + `deployment/健康检查.py` |

**Recommendation**: The `deployment/deployment/` subdirectory appears to be an accidental duplicate copy. Mark for deletion after confirming no imports reference it.

---

## 5. Unused Import Inventory

**303 unused imports across 164 files.** Most are `typing` module imports (`Optional`, `List`, `Dict`, `Any`, `Tuple`) that became unused after code changes, plus standard library modules (`os`, `json`, `time`, `hashlib`).

**Top affected files:**
- Various `ad_intelligence/` modules (typing imports)
- `ai_analyzer.py` (`hashlib`)
- `adaptive_engine.py` (`time`)

**Recommendation**: Batch cleanup per module, run tests after each module. Low risk but high volume.

---

## 6. Hidden Side Effects Inventory

**535 module-level executable statements across 105 files.**

### Classification
| Type | Count | Risk |
|---|---|---|
| `print()` at module level | ~300+ | LOW (noise, but indicates script-style modules) |
| `logger.info()` at module level | ~20 | LOW |
| Module-level `if` statements | ~100 | MED (may contain initialization logic) |
| Module-level `try/except` | ~50 | MED (may contain I/O) |
| Module-level `for/while` loops | ~30 | MED |
| Dangerous calls (network/DB at import) | **0** | **CLEAN** |

### Notable Files
- `settings_module.py` — module-level `print("[Settings] 设置模块已加载")` + `sys.path.insert()` (DEPRECATED module)
- `adaptive_engine.py` — module-level `print()` + strategy initialization call
- `system_guardian.py` — 4x module-level `logger.info()`
- `architecture_api.py`, `auto_recovery.py` — module-level `print()`

**Key finding**: No production module performs network requests or database writes at import time. The `case_ai_evaluate.py` module-level .env file reading was fixed.

---

## 7. Circular Dependency Inventory

**1 cycle found:**

```
collector_automation → collector → collector_automation
```

- `collector_automation.py` imports from `collector.py`
- `collector.py` imports from `collector_automation.py`

**Risk**: MED. Python can often resolve this at runtime if imports are function-local, but it's fragile. Recommend refactoring shared code into a third module (e.g., `collector_common.py`).

---

## 8. Scratch / Debug File Inventory

**68 files marked as DELETE-CANDIDATE** (not deleted — per AGENTS.md protocol).

### Root-level scratch files (32):
```
_audit_backups.py, _audit_historical.py, _split_report_api.py,
_db_inspect.py, _db_audit.py, _t7_db_inspect.py, _t7_db_inspect2.py,
_shardC_add_csrf.py, _shardC_add_escape.py, _shardC_db_audit.py,
_shardC_enhance_overview.py, _shardC_enhance_workspace.py,
_shardC_insert_security.py, _shardC_patch_css.py, _shardC_patch_css2.py,
_debug_x.py, _debug_x_v2.py, _debug_x_v3.py, _debug_x_v4.py,
_verify_x.py, _verify_x_adapter.py, _verify_x_final.py, _verify_x_live.py,
_verify_jiguang.py, _parse_x_cookie.py, _parse_x_cookie_v2.py,
_parse_jiguang_cookie.py, _douyin_struct.py, _douyin_ssr_debug.py,
_douyin_render_walk.py, _douyin_detail_debug.py, _open_login_pages.py
```

### Subdirectory scratch files (36):
Located in `tests/`, `00-GOVERNANCE/`, `99-ARCHIVE/`, `audit/`, `archive/` — already in non-production directories.

### .bak files (3):
```
app.py.bak-report-split-20260904212600
ark_llm.py.bak-providerguard
ai_learning_engine.py.bak-providerguard
```

### Verification
- **No scratch file is imported by any production code** (verified via grep for `import _` patterns)
- All `_` prefixed files are standalone scripts

---

## 9. Configuration Governance

### 9.1 Config Key Coverage (Post-Fix)

| Source | Key Count |
|---|---|
| `.env` (actual) | 47 |
| `.env.example` (template) | 85 (was 64, +21 added) |
| `config.py` known_keys | ~110 (was 31, +79 added) |

### 9.2 Keys Added to .env.example (21)
```
ALLOW_CLOUD_AI, ZHIPU_API_KEY, ZHIPU_MODEL, ZHIPU_STRONG_MODEL, ZHIPU_BASE_URL,
ARK_API_KEY, ARK_MODEL, ARK_BASE_URL, ARK_MAX_DAILY_TOKEN,
DASHSCOPE_BASE_URL, OPENAI_PROXY,
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, SMTP_SSL,
TAIKOO_COMPANY_DOMAIN, TAIKOO_COMPANY_NAME,
DAILY_REPORT_HOUR, V4_ACCESS_KEY, XHS_COOKIE
```

### 9.3 Keys Added to config.py known_keys (~79)
Expanded from 31 to ~110 keys covering: AI providers (Zhipu/ARK/DashScope/OpenAI/DeepSeek), local AI runtimes (Ollama/LMStudio/llama.cpp), collection config, web adapters, XHS config, credentials, SMTP, WeChat notifications, scheduling gate, repository registry paths.

### 9.4 Remaining Config Issues
- **Dual naming**: `EMAIL_SMTP_*` (old) vs `SMTP_*` (new) both exist. Recommend deprecation plan.
- **`APP_HOST`/`APP_PORT` vs `TAIKOO_HOST`/`TAIKOO_PORT`**: config.py uses `APP_*` but .env uses `TAIKOO_*`. Need alias mapping or unification.
- **`settings_module.py`**: DEPRECATED but still active with its own `data/system_config.json` config file. Dual-config track remains.

### 9.5 Hardcoded Ports (49 non-standard)
Most are in scratch/debug files and deployment scripts. Production files with hardcoded ports:
- `xhs_cdp_collector.py:33` — `CDP_URL = 'http://127.0.0.1:9222'` (no env override; standalone subprocess script)
- `system_watchdog.py:41` — `HEALTH_CHECK_URL = 'http://127.0.0.1:8200/...'`
- Various `check_*.py` utility scripts (8200)

---

## 10. Merge Conflict Resolution Log

| File | Markers | Resolution |
|---|---|---|
| `auth_recovery_center.py` | 2 | Keep HEAD (`from database import DB_PATH`) |
| `brand_knowledge_base.py` | 1 | Keep HEAD (`from database import DB_PATH` + env var) |
| `case_deep_analysis.py` | 1 | Keep HEAD (`from database import DB_PATH`) |
| `lumenis_skill_adapter.py` | 1 | Keep HEAD (repo_registry.json + directory scan) |
| `_split_report_api.py` | 1 | Keep HEAD (`get_repo_root()`) |
| `case_ai_evaluate.py` | 1 | Keep HEAD (`os.environ.get()`) |

All conflicts were between HEAD (current branch) and `e9ef5ad` (earlier Phase 1 commit introducing `repository_registry`). HEAD version was preferred as it represents the current production baseline.

---

## 11. Files Modified in This Phase

| File | Change | Reason |
|---|---|---|
| `_parse_x_cookie.py` | Sanitized real cookie values → REDACTED | P0 Secret leak |
| `_parse_x_cookie_v2.py` | Sanitized real cookie values → REDACTED | P0 Secret leak |
| `case_ai_evaluate.py` | Resolved merge conflict; removed module-level .env I/O | P0 Syntax + side effect |
| `auth_recovery_center.py` | Resolved merge conflict (keep HEAD) | P0 Syntax |
| `brand_knowledge_base.py` | Resolved merge conflict (keep HEAD) | P0 Syntax |
| `case_deep_analysis.py` | Resolved merge conflict (keep HEAD) | P0 Syntax |
| `lumenis_skill_adapter.py` | Resolved merge conflict (keep HEAD) | P0 Syntax |
| `_split_report_api.py` | Resolved merge conflict (keep HEAD) | P0 Syntax |
| `config.py` | Expanded `get_known_keys()` from 31 to ~110 keys | Config governance |
| `.env.example` | Added 21 missing config keys | Config governance |
| `code_quality_report.py` | **Created** — AST-based code quality scanner | New tool |
| `audit/code_quality_scan.json` | **Created** — full structured scan results | Scan output |
| `audit/code_quality_audit.md` | **Created** — this report | Audit deliverable |
| `tests/test_code_quality.py` | **Created** — regression tests | Test deliverable |

---

## 12. Recommendations & Next Steps

### P0 (Done)
- [x] Remove real secrets from source code
- [x] Resolve all merge conflicts
- [x] Fix dangerous hidden side effects

### P1 (Recommended)
- [ ] Refactor `collector` ↔ `collector_automation` circular dependency
- [ ] Remove `deployment/deployment/` duplicate directory (after import verification)
- [ ] Unify `APP_*` vs `TAIKOO_*` config naming
- [ ] Add env override to `xhs_cdp_collector.py` CDP_URL
- [ ] Batch cleanup of unused imports (per-module, with tests)

### P2 (Backlog)
- [ ] Deprecate `settings_module.py` → migrate to `config.py`
- [ ] Manual review of dead code candidates (1253) before any deletion
- [ ] Convert module-level `print()` to proper logging
- [ ] Add pre-commit hook for secret scanning
- [ ] Delete scratch files after confirming no references (68 files)

---

## 13. Compliance with AGENTS.md

- **No production database modified** — read-only scan only
- **No SUBJECT_WORDS / subject_hit() modified**
- **No git commit performed** — all changes local
- **No .bak files deleted** — only marked
- **No unknown modules deleted** — scratch files only marked as DELETE-CANDIDATE
- **AI Provider policy preserved** — no API keys written to source
- **Official account read-only protection** — no changes to collector interaction logic

---

*End of report. Generated by ZBC Phase 16 Code Quality Audit.*
