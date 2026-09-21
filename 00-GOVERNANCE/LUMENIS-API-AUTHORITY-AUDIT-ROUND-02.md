# LUMENIS API / Caller Authority Audit — ROUND 02

> Status: **ROUND 02 EVIDENCE / NOT A SOURCE OR PRODUCT AUTHORITY**
>
> Baseline: `a13ff0cf19de894e917031a2fe7e62c751d58344`; current committed candidate: `542ee83164f3bcee1583d3ad20a64208bc066b06` (external auto-watch commit; ROUND 02 remains REWORK).

This audit records current API/caller truth and the ROUND 02 owner decisions. It does not delete routes, promote future surfaces, prove global data maturity or create a second Product Core, Context, Permission, Evidence or Database owner.

## Current route truth

The generated OpenAPI/route matrix is derived from the executing Flask `app.url_map`, not a hand-maintained route list:

| Measure | Current count |
| --- | ---: |
| URL-map rules | 784 |
| Static rules | 1 |
| API rules | 783 |
| Unique API paths | 744 |
| Operation candidates | 805 |
| Operation groups | 791 |
| Duplicate method/path groups | 14 |
| Candidates in duplicate groups | 28 |

Every duplicate group remains explicit through `x-route-candidates`; generation does not silently choose a winner.

| Method/path group | Candidate owners | Scheduled owner decision |
| --- | --- | --- |
| `GET /api/ai/tasks` | `ai_api.api_ai_tasks_list`; `api_ai_tasks` | ROUND 07 |
| `POST /api/ai/tasks` | `ai_api.api_ai_tasks_create`; `api_ai_tasks` | ROUND 07 |
| `GET /api/browser/sessions` | `ai_browser_runtime.list_sessions`; `api_browser_sessions` | ROUND 06 |
| `GET /api/collector/status` | `collection.api_collector_status`; `collector_status.collector_status` | ROUND 06 |
| KOS professional disable/enable/import/status | `kos.*`; `lumenis_agg.*` | ROUND 12–13 |
| `GET /api/pr/cases/{case_id}` | `api_pr_case_detail`; `pr_case.get_pr_case_detail` | ROUND 11 |
| `GET /api/security/scan` | `api_security_scan`; `system_features.security_scan` | ROUND 04/14 |
| `GET /api/system/runtime` | `api_system_runtime`; `lumenis_agg.system_runtime` | ROUND 05/14 |
| `/api/v4/api-keys` GET/generate/revoke | `account_compat.*`; root account endpoints | ROUND 04 |

Route existence or duplication is not a business-capability result. Each owning round must trace caller, Permission, Evidence, canonical read/write, user result and compatibility before removing or converging anything.

## Legacy Function Map disposition

`function_map.json` is a compatibility catalog, not Product Skill Store, API truth or Production Truth.

- 30 entries total;
- 19 exact registered route matches;
- 11 explicit `BLOCKED`/`DEFERRED` entries: `collect`, `collect_status`, `event_detail`, `web_browser_discovery`, `brand_industry`, `alert_read`, `settings_update`, `developer_run`, `email_test`, `domain_add`, `domain_delete`;
- every non-match names its owning future round or post-launch gate instead of pretending the callable exists.

## OWNER → CALLER → USER CAPABILITY MATRIX

| Canonical owner | Current caller / compatibility surface | User capability in this round | ROUND 02 conclusion |
| --- | --- | --- | --- |
| Product Core/API (`app.py`, registered Flask routes) | OpenAPI generator, Flutter Core client, compatibility callers | One route truth for approved operational surfaces | Classified; 14 duplicate groups remain scheduled, with no silent winner. |
| SYSTEM RuntimeGuardian | `experience_screens._build_sys01()` → `experience_runtime` → Flutter SYS-01 | Read current runtime state, trace and honest failure/recovery | Implemented and tested; live evidence remains governed by the ROUND 02 Charter. |
| Current Subject/Domain context owner (`subject_context.py` plus existing domain callers) | Product Core request context, Experience builders, Evidence/reporting/AI callers | Future default Global→Focus→Return context | Owner/consumer/compatibility contract fixed. Current Guangzhou Taikoo Hui default fallback is legacy protected compatibility, not global product truth; global selector runtime remains later-round work. |
| Subject registry + Shared Database | context and domain consumers | Discover/add stable commercial or brand identities | Not implemented/accepted by ROUND 02; ROUND 03 owns registry/key/data boundary. |
| Permission/account authorization | Product Core and action callers | Decide actor visibility/effects independently of selection | Not implemented by ROUND 02; ROUND 04 owns fail-closed context/Permission separation. |
| SYSTEM Collector/Browser | CTH/BMP requests and scheduled runtime | Continue authorized acquisition independent of UI focus | Contract fixed; live continuity and scope proof belong to ROUND 05–06. |
| One AI Gateway / Shared Agent Skills | CTH/BMP workflows and future Jev typed candidate | Scoped derivative analysis/creation without owning truth | Jev absent and scheduled ROUND 07; no second AI owner created. |
| Flutter operational surfaces | Product Core JSON API | Desktop SYS-01 real job in ROUND 02; future Web/Desktop/Mobile Global selector | SYS-01 slice is current; Global selector interaction belongs to ROUND 08 and later screen rounds. |

## One internal full-universe context conclusion

The repository now routes one internal full-universe edition through `LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md`. `Global Commercial Coverage`, `Global Brand Coverage` and `Guangzhou Taikoo Hui Reference Coverage` are acceptance rows of the same Product/Core/Data/Evidence/Permission/API/Context/Experience stack, not independent products or releases.

ROUND 02 proves only the authority and compatibility decision:

- default product semantics are `GLOBAL / ALL`;
- Subject/BrandFocus selection changes focus only and grants no Permission;
- Guangzhou Taikoo Hui is a controlled depth-reference Subject, not the default, sole choice or global proxy;
- current hard-coded/default fallback behavior is a real compatibility gap assigned to its database/context/surface owner rounds;
- no global discovery, non-reference Subject/brand selection, data-maturity or full reference-loop completion is claimed.

Current conclusion: `LUMENIS_INTERNAL_FULL_UNIVERSE_READY = NO`.

## Evidence boundary

Generated `docs/API-OPENAPI-SPEC.json` and `docs/API-ROUTE-MATRIX.md`, targeted tests, governance validators and the ROUND 02 Windows Desktop evidence bundle are reproducible acceptance inputs. They do not promote `PARTIAL` capabilities to `LIVE_VERIFIED`, do not prove continuous operation, and do not authorize production-data mutation or route deletion.
