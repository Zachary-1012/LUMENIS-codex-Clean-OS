# Cross-Repository Contract Boundary — ZBC / OSAI / GGI / LUMENIS Command

> Version: 1.0 · Date: 2026-09-06 · Owner: Shard D / Team 1
> Status: **HISTORICAL / SUPERSEDED — NOT AN EXECUTION AUTHORITY**
>
> 本文保留 2026-09-06 的接口与命名历史。当前跨仓边界以
> [Canonical Registry](../00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md)
> 及其指向的 `lumenis-ggi-cross-product` 机器合同为准；产品语义以
> [Product Architecture](../00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md)
> 为准。下文的 Dual-Core、ZBC/ZBMP 产品层级、CTH 固定主体及
> Zhipu/Local 可调用表述均是历史记录，不授权恢复旧 Provider、默认聚焦、
> 旧部署或跨仓写入。仍被调用的技术标识保留兼容，不能据本文迁移数据。

## 1. Repository Roles

| Repository | Role | Owns | May request | Runtime dependency |
|---|---|---|---|---|
| **ZBC** (序境-Core) | Production Core | production code, data, runtime, policy, reporting, subject authority | research, models, recommendations from OSAI via Contract | **None** — must operate standalone |
| **OSAI** (序境-Intelligence) | Intelligence Core | research, evidence, models, evaluation, contracts, skills | Core implementation through Contract (read-only) | **None** — must operate standalone |
| **GGI** (Global Growth Intelligence) | Independent Product | independent research product, 9-dimension taxonomy | none | **None** — fully independent |
| **LUMENIS Command** | Dev Console | development tooling, CI/CD, release management | none | **None** — dev-only |

**Hard rule**: No repository may become another's runtime hard dependency.
Each must start, collect, filter, analyze, and report without the others running.

## 2. Allowed Communication Patterns

### 2.1 ZBC → OSAI (Production → Intelligence)
- **Allowed**: Read-only contract calls via `contracts/lumenis_adapter.py`
- **Allowed**: AI Gateway calls (Zhipu/Local) — provider-agnostic, not OSAI-specific
- **Allowed**: File-based artifact exchange (JSON/CSV in staging/)
- **Forbidden**: `import osai_engine` or direct OSAI module import
- **Forbidden**: Hardcoded OSAI filesystem paths in production code
- **Forbidden**: OSAI availability as a prerequisite for ZBC startup

### 2.2 OSAI → ZBC (Intelligence → Production)
- **Allowed**: Read-only snapshot via `osai_engine/repository_registry.py` (env var `ZBC_ROOT`)
- **Allowed**: Source code scanning for audit/research (read-only filesystem access)
- **Allowed**: Contract-based data exchange (staging/ artifacts)
- **Forbidden**: Direct `import` of ZBC business modules (app.py, risk_engine, collector)
- **Forbidden**: Write access to ZBC production database
- **Forbidden**: Modifying ZBC subject rules, risk config, or production data

### 2.3 GGI ↔ Any
- **Allowed**: None by default. GGI is fully independent.
- **Allowed**: Manual artifact export/import if explicitly requested.
- **Forbidden**: Any runtime coupling, shared database, or import chain.

### 2.4 LUMENIS Command ↔ Any
- **Allowed**: Git operations, CI/CD, file editing (dev tooling only)
- **Forbidden**: Production runtime access, database writes, auth bypass

## 3. Contract Interface (ZBC ↔ OSAI)

### 3.1 ZBC Production Core Read-Only Adapter
**Location**: `contracts/lumenis_adapter.py`

Exposed functions (all read-only):
- `production_core_snapshot()` — ZBC capabilities, red lines, contract status
- `subject_authority_readonly()` — SUBJECT_WORDS/SUBJECT_EXCLUDE_WORDS counts only (contents never exposed)
- `contract_compatibility()` — adapter version, implemented contracts, write status
- `get_production_facts()` — lightweight runtime facts (python, cwd, version)
- `repository_registry_snapshot()` — ZBC repo metadata (root, branch, sha, remote)
- `permission_gate_snapshot()` — ZBC permission levels and protected entities

**Hard constraints**:
- stdlib only
- No database writes
- No subject word content exposure
- No modification of production core

### 3.2 OSAI Repository Registry
**Location**: `osai_engine/repository_registry.py` (OSAI repo)

Exposed functions:
- `resolve_path(key)` — env var → existence check → platform default
- `resolve_python(key)` — venv → system python resolution
- `get_repo_info(key)` — name, role, root, python, branch, sha
- `registry_snapshot()` — dual-core full snapshot

**Env vars**: `ZBC_ROOT`, `OSAI_ROOT` (override defaults)

## 4. Subject / Brand Boundary

### 4.1 CTH (Guangzhou Taikoo Hui) — Protected Production Domain
- `subject_hit()` is locked to Guangzhou Taikoo Hui by default
- `SUBJECT_WORDS` / `SUBJECT_EXCLUDE_WORDS` are not bypassable by Skill/Agent
- Chengdu/Beijing/Shanghai/Hong Kong Taikoo properties are strictly excluded
- `ZBC_PRODUCT_ID=CTH` env var enforces CTH-only mode (blocks brand switching)

### 4.2 ZBMP (Multi-Subject Brand Management Platform)
- Multi-brand KOS scenarios use `brand_scope("hainan_cdf")` context manager
- `subject_hit_for_brand(brand_key=...)` for explicit brand queries
- `subject_sql_and_values_for(brand_key=...)` for brand-scoped SQL
- Each brand has independent `BRAND_PROFILES` entry with own subject/exclude words

### 4.3 Request-Level Isolation (Flask)
- `subject_context.init_app(app)` registers before_request/after_request hooks
- Brand resolved per-request from: `X-Brand-Key` header → session → query param → env var → CTH default
- Thread-local context prevents cross-request brand leakage
- `brand_scope()` context manager for explicit local brand switching in code

## 5. Path Resolution Contract

### 5.1 ZBC Repository Registry
**Location**: `core/repository_registry.py`

All production code MUST obtain paths via:
- `get_repo_root()` — repository root (env `ZBC_ROOT` → dynamic `__file__` → fallback probe)
- `get_data_dir()` / `get_db_path()` — data directory and SQLite path
- `get_log_dir()` / `get_config_dir()` / `get_staging_dir()` — standard subdirs
- `get_osai_root()` / `get_ggi_root()` — optional cross-repo refs (None if absent)
- `get_python_executable()` — venv python resolution
- `registry_snapshot()` — full registry state for health checks

**Forbidden**: Hardcoded `D:\Taikoo-monitor-new`, `D:\Zachary OS AI`, `C:\Users\private-user-efa8e21551f0 in production .py files.

### 5.2 Test Files
Test files may use `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` for path resolution, or set `ZBC_ROOT` env var in conftest.py.

## 6. Dependency Matrix

| From \ To | ZBC | OSAI | GGI | LUMENIS Cmd |
|---|---|---|---|---|
| **ZBC** | — | read-only contract (optional) | none | none |
| **OSAI** | read-only scan (optional) | — | none | none |
| **GGI** | none | none | — | none |
| **LUMENIS Cmd** | git/CI only | git/CI only | git/CI only | — |

**All dependencies are optional**. If the target is unavailable, the source must degrade gracefully and continue operating.

## 7. Verification

### 7.1 Cross-Repo Import Scan
```bash
# ZBC must NOT import OSAI modules
grep -rn "import osai" --include="*.py" .
grep -rn "from osai" --include="*.py" .

# OSAI must NOT import ZBC business modules
grep -rn "import app\|import risk_engine\|import collector" --include="*.py" osai_engine/
```

### 7.2 Hardcoded Path Scan
```bash
grep -rn "D:\\\\Taikoo-monitor-new\|D:\\\\Zachary OS AI\|C:\\\\Users\\\\private-user-121dcc385158" --include="*.py" .
```
Expected: 0 in production code (excluding tests/, scripts/, docs/, and documented fallbacks).

### 7.3 Standalone Startup Test
```bash
# ZBC must start without OSAI
ZBC_PRODUCT_ID=CTH python app.py
# OSAI must start without ZBC
python -m osai_engine
```

## 8. Change Control

Any change to this contract requires:
1. Dependency scan of both repositories
2. Standalone startup verification of both
3. Cross-repo import scan (zero forbidden imports)
4. Update to Feature Registry status
5. Git commit with `feat(shard-D): contract <change>` message
