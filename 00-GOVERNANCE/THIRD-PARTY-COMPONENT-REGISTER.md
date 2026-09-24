# LUMENIS Third-Party / Open-Source Component Register

> Status: CANONICAL REGISTER
> Scope: direct repository dependencies and important optional external components
> Source of truth for presence: current manifests/source, not historical docs.
> License rule: `VERIFY_BEFORE_RELEASE` means the repository has not yet recorded verified license evidence here; do not guess.

## 1. Policy

Third-party software may accelerate delivery but must remain bounded and replaceable where practical.

Preferred integration shape:

```text
LUMENIS Contract
→ Adapter / Boundary
→ Third-party implementation
```

Third-party components must not silently become the owner of LUMENIS Canonical Data, Evidence, Metric, Permission, Subject Context or business truth.

Every release audit should reconcile this register against dependency manifests and vendored assets.

## 2. Python direct dependencies observed in `requirements.txt`

The table records direct manifest entries, not every transitive dependency.

| Component | Class | Purpose in repository | Integration / replacement boundary | License status | Replaceable |
| --- | --- | --- | --- | --- | --- |
| Flask | PRODUCTION | Web application/API framework | HTTP/application boundary | VERIFY_BEFORE_RELEASE | Yes, high-cost |
| Werkzeug | PRODUCTION | Flask/runtime HTTP utilities | Web framework boundary | VERIFY_BEFORE_RELEASE | Yes, coupled to Flask |
| Flask-CORS | PRODUCTION | CORS handling | HTTP middleware | VERIFY_BEFORE_RELEASE | Yes |
| Flask-Limiter | PRODUCTION | Request rate limiting | HTTP middleware/policy boundary | VERIFY_BEFORE_RELEASE | Yes |
| waitress | PRODUCTION | WSGI serving | Process/server boundary | VERIFY_BEFORE_RELEASE | Yes |
| APScheduler | PRODUCTION | Scheduling | Scheduler/runtime boundary | VERIFY_BEFORE_RELEASE | Yes |
| schedule | PRODUCTION | Lightweight scheduling | Scheduler/runtime boundary | VERIFY_BEFORE_RELEASE | Yes |
| pandas | PRODUCTION | Tabular data processing | Data transformation boundary | VERIFY_BEFORE_RELEASE | Yes, medium-cost |
| openpyxl | PRODUCTION | XLSX read/write | Import/export adapter | VERIFY_BEFORE_RELEASE | Yes |
| xlsxwriter | PRODUCTION | XLSX generation | Export adapter | VERIFY_BEFORE_RELEASE | Yes |
| beautifulsoup4 | PRODUCTION | HTML parsing | Acquisition/parser adapter | VERIFY_BEFORE_RELEASE | Yes |
| lxml | PRODUCTION | XML/HTML parsing | Parser adapter | VERIFY_BEFORE_RELEASE | Yes |
| python-docx | PRODUCTION | DOCX generation | Report/export adapter | VERIFY_BEFORE_RELEASE | Yes |
| reportlab | PRODUCTION | PDF/report generation | Report/export adapter | VERIFY_BEFORE_RELEASE | Yes |
| playwright | PRODUCTION | Browser automation | Browser/Collector adapter boundary | VERIFY_BEFORE_RELEASE | Yes, high-cost |
| psutil | PRODUCTION | Process/system monitoring | Runtime observability/process boundary | VERIFY_BEFORE_RELEASE | Yes |
| requests | PRODUCTION | HTTP client | Network adapter | VERIFY_BEFORE_RELEASE | Yes |
| httpx | PRODUCTION | HTTP client | Network adapter | VERIFY_BEFORE_RELEASE | Yes |
| websocket-client | PRODUCTION | WebSocket client | Network/browser adapter | VERIFY_BEFORE_RELEASE | Yes |
| python-dotenv | PRODUCTION | Environment configuration loading | Config boundary | VERIFY_BEFORE_RELEASE | Yes |
| python-dateutil | PRODUCTION | Date/time utilities | Utility boundary | VERIFY_BEFORE_RELEASE | Yes |
| PyYAML | PRODUCTION | YAML parsing | Config/data adapter | VERIFY_BEFORE_RELEASE | Yes |
| colorama | PRODUCTION/CLI | Terminal output compatibility | CLI only | VERIFY_BEFORE_RELEASE | Yes |
| tqdm | PRODUCTION/CLI | Progress display | CLI only | VERIFY_BEFORE_RELEASE | Yes |
| aiohttp | OPTIONAL ENHANCEMENT | Async collector HTTP; manifest notes synchronous fallback | Collector network adapter | VERIFY_BEFORE_RELEASE | Yes |
| yyds-logger | OPTIONAL ENHANCEMENT | Enhanced logging; manifest notes stdlib fallback | Logging adapter | VERIFY_BEFORE_RELEASE | Yes |
| tenacity | OPTIONAL ENHANCEMENT | Retry/backoff | Retry policy boundary | VERIFY_BEFORE_RELEASE | Yes |
| alembic | PRODUCTION TOOLING | DB migration tooling | Migration boundary; migration gate required | VERIFY_BEFORE_RELEASE | Yes |
| feedparser | PRODUCTION | RSS / Atom public-feed parsing, as declared in `requirements.txt` | Public-feed acquisition adapter | VERIFY_BEFORE_RELEASE | Yes |

### Commented / optional entries observed but not required by the current manifest

The current `requirements.txt` mentions, but does not require-install: `openai`, `ollama`, `docx2pdf`, `pypdf`, and Windows-specific `win32-setctime`. Presence at runtime must be checked before treating any of them as active dependencies.

## 3. Python development/test dependencies observed in `requirements-dev.txt`

`requirements-dev.txt` layers on top of `requirements.txt`; entries here are not production-runtime requirements merely because CI installs them.

| Component | Class | Purpose in repository | Integration / replacement boundary | License status | Replaceable |
| --- | --- | --- | --- | --- | --- |
| pytest | TEST ONLY | Automated test collection/execution and CI blocking regression gate | Test runner boundary; production runtime must not depend on it | VERIFY_BEFORE_RELEASE | Yes |

## 4. Node direct dependencies observed in root `package.json`

| Component | Class | Purpose | Integration / replacement boundary | License status | Replaceable |
| --- | --- | --- | --- | --- | --- |
| playwright | PRODUCTION TOOLING | Root Node scripts for browser/login/search flows | Browser/Collector adapter boundary | VERIFY_BEFORE_RELEASE | Yes, high-cost |

Current root package metadata still carries historical naming. Metadata cleanup is allowed, but script/behavior changes require runtime verification.

## 5. Flutter direct dependencies observed in `app/pubspec.yaml`

Versions below come from the current `app/pubspec.lock`. Flutter SDK packages
use the SDK-managed `0.0.0` lockfile marker rather than an independently
released package version.

| Component | Locked version | Class | Purpose | Integration / replacement boundary | License status | Replaceable |
| --- | --- | --- | --- | --- | --- | --- |
| Flutter SDK | SDK-managed | PRODUCTION | Shared Web/Desktop/Mobile Experience runtime | Experience surface only; never Product Core or business truth | VERIFY_BEFORE_RELEASE | High-cost |
| flutter_localizations | SDK (`0.0.0` marker) | PRODUCTION | zh-CN/en/ko framework localization support | Canonical copy/localization adapter | VERIFY_BEFORE_RELEASE | Coupled to Flutter |
| flutter_web_plugins | SDK (`0.0.0` marker) | PRODUCTION | Web URL-strategy integration | Web platform adapter | VERIFY_BEFORE_RELEASE | Coupled to Flutter Web |
| cupertino_icons | 1.0.9 | PRODUCTION ASSET | Cupertino icon font required by Flutter mobile/Web builds | Experience icon asset only | MIT (pub.dev publisher metadata; notice reconciliation still required) | Yes |
| go_router | 18.0.1 | PRODUCTION | Declarative workspace URL and browser-history synchronization | Presentation routing only | VERIFY_BEFORE_RELEASE | Yes, medium-cost |
| http | 1.6.0 | PRODUCTION | Browser-safe Product Core HTTP transport | `app/lib/core/transport` adapter | VERIFY_BEFORE_RELEASE | Yes |
| [file_selector](https://github.com/flutter/packages/tree/main/packages/file_selector/file_selector) | 1.1.0 | PRODUCTION | Local wallpaper image picker in SYS-05 | `sys05_appearance_editor.dart`; user-selected bytes only | BSD-3-Clause (installed package `LICENSE`) | Yes |
| [shared_preferences](https://github.com/flutter/packages/tree/main/packages/shared_preferences/shared_preferences) | 2.5.5 | PRODUCTION | Device-local SYS-05 appearance and wallpaper preference persistence | `Sys05AppearanceController` via `SharedPreferencesAsync`; no server or business-data ownership | BSD-3-Clause (installed package `LICENSE`) | Yes |
| [flutter_acrylic](https://github.com/alexmercerind/flutter_acrylic) | 1.1.4 | PRODUCTION | Windows acrylic host-window material adapter | `lumenis_window_material_io.dart`; Windows native appearance only | MIT (installed package `LICENSE`) | Yes |
| [macos_window_utils](https://github.com/Adrian-Samoticha/macos_window_utils.dart) | 1.9.1 | PRODUCTION | macOS window material and brightness adapter | `lumenis_window_material_io.dart`; macOS native appearance only | MIT (installed package `LICENSE`) | Yes |

For these four rows, exact versions are from `app/pubspec.lock`; repository
URLs and licenses were checked against each installed package's `pubspec.yaml`
and `LICENSE` under the local Pub cache. The Flutter Authors packages use the
three-clause BSD license text; `flutter_acrylic` and `macos_window_utils`
include MIT license text. This records local package evidence only and does not
replace shipped-artifact notice reconciliation at release.

## 6. Built-in / platform dependencies

These are not third-party packages in the manifests but materially affect operation:

| Component | Class | Current role | Portability concern |
| --- | --- | --- | --- |
| SQLite (`sqlite3`) | PYTHON STDLIB / DATA | Local persistence | DB isolation and migration contracts remain release-critical |
| Windows PowerShell 5.1 | PLATFORM | Current canonical production launcher | Current production launch path is Windows-specific |
| Microsoft Edge | EXTERNAL PLATFORM | Resident browser/CDP path in current launcher | Installation path/browser availability must be detected rather than assumed long-term |

## 7. Evaluated future OSS adapters — not installed by this register

These names are architectural candidates only. Their inclusion here does **not** authorize installation or imply current usage.

| Component | Intended gap | Rule before adoption |
| --- | --- | --- |
| OpenTelemetry | Standardized traces/metrics/observability | Adopt only behind observability boundary after current instrumentation gap is proven |
| Langfuse OSS | AI trace/evaluation/prompt observation | AI observability only; never Evidence/Metric/Permission/Business Truth owner |
| Temporal | Durable long-running workflow/recovery | Adopt only if current scheduler/runtime/recovery is proven insufficient; use a workflow adapter |

## 8. Required pre-release reconciliation

Before a production release:

1. Re-scan `requirements*.txt`, `pyproject.toml` if present, `package*.json`, vendored source, binary tools, fonts, icons and copied third-party assets.
2. Record exact versions actually shipped where lockfiles/build artifacts define them.
3. Verify licenses from authoritative package/project sources and replace every `VERIFY_BEFORE_RELEASE` entry that ships.
4. Record attribution or notice obligations.
5. Mark each dependency `PRODUCTION`, `DEVELOPMENT`, `TEST`, or `OPTIONAL ADAPTER` from real import/runtime evidence.
6. Confirm critical third-party code is behind a bounded interface where practical.
7. Record any component that cannot yet be reasonably replaced and why.

Unknown licensing or unregistered shipped third-party code is a release blocker, not a documentation footnote.

### 2026-09-24 bundled CJK text rendering

Decision: ADOPT unmodified Noto Sans SC and KR variable fonts from the official Google Fonts repository. The real browser preview exposed missing Chinese glyphs when dynamic remote fallback was unavailable. These fonts cover product copy and user-provided Chinese/Korean text through the existing Flutter Theme owner, without a remote font-service dependency.

| Font | Official source | License | SHA-256 of bundled original |
| --- | --- | --- | --- |
| Noto Sans SC | https://github.com/google/fonts/tree/main/ofl/notosanssc | SIL OFL 1.1; bundled NotoSansSC-OFL.txt | a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da |
| Noto Sans KR | https://github.com/google/fonts/tree/main/ofl/notosanskr | SIL OFL 1.1; bundled NotoSansKR-OFL.txt | 194018e6b2b293a7964f037b25c0249ce1418bc9ab3c971060a03aa57861e252 |

Source and LICENSE inspected 2026-09-24 through the public GitHub content API and original files. Unmodified binaries are retained under app/assets/fonts; their license text is registered with Flutter LicenseRegistry. They are bundled with the application, never sold separately. Assets add approximately 28.2 MB before transport compression; browser/network and current-build rendering verification remain required. No reference screenshot, private video frame, or proprietary system font is bundled.
