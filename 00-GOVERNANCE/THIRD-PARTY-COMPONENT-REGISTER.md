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
| [DuckDB](https://pypi.org/project/duckdb/1.5.5/) 1.5.5 | PRODUCTION | Local Overture Places Parquet file reader | SYSTEM Collector adapter; in-memory connection only, no business DB ownership | MIT ([v1.5.5 license](https://github.com/duckdb/duckdb/blob/v1.5.5/LICENSE)) | Yes |
| pandas | PRODUCTION | Tabular data processing | Data transformation boundary | VERIFY_BEFORE_RELEASE | Yes, medium-cost |
| openpyxl | PRODUCTION | XLSX read/write | Import/export adapter | VERIFY_BEFORE_RELEASE | Yes |
| xlsxwriter | PRODUCTION | XLSX generation | Export adapter | VERIFY_BEFORE_RELEASE | Yes |
| beautifulsoup4 | PRODUCTION | HTML parsing | Acquisition/parser adapter | VERIFY_BEFORE_RELEASE | Yes |
| lxml | PRODUCTION | XML/HTML parsing | Parser adapter | VERIFY_BEFORE_RELEASE | Yes |
| python-docx | PRODUCTION | DOCX generation | Report/export adapter | VERIFY_BEFORE_RELEASE | Yes |
| reportlab | PRODUCTION | PDF/report generation | Report/export adapter | VERIFY_BEFORE_RELEASE | Yes |
| playwright | PRODUCTION | Browser automation | Browser/Collector adapter boundary | VERIFY_BEFORE_RELEASE | Yes, high-cost |
| cryptography | PRODUCTION SECURITY ADAPTER | Ed25519 training-phase verification; pinned in requirements.txt | Existing SYSTEM Security; evidence and packaging details in the bounded training signature adapter section below | VERIFY_BEFORE_RELEASE | Yes |
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
| [markitdown[pptx]](https://github.com/microsoft/markitdown/tree/v0.1.8) 0.1.8 | PRODUCTION / OPTIONAL IMPORTER ENHANCEMENT | Local HTML/PPTX to Markdown conversion behind `lumenis/importer/parser.py`; no network, Evidence or Canonical ownership | Importer adapter only; existing PDF/Word/Excel parsers remain authoritative; remove or replace by the same ParseResult contract | MIT ([v0.1.8 license](https://github.com/microsoft/markitdown/blob/v0.1.8/LICENSE)); python-pptx and transitive dependencies require separate notice/license reconciliation | Yes |

### Commented / optional entries observed but not required by the current manifest

The current `requirements.txt` mentions, but does not require-install: `openai`, `ollama`, `docx2pdf`, `pypdf`, and Windows-specific `win32-setctime`. Presence at runtime must be checked before treating any of them as active dependencies.

## 2B. Optional Browser Use research adapter (not a production dependency)

| Component | Exact source/version | Current product disposition | License / boundary |
| --- | --- | --- | --- |
| [Browser Use](https://github.com/browser-use/browser-use/tree/0.13.10) | Upstream tag `0.13.10`; optional direct pins are recorded in `requirements-browser-use.txt`; no package is declared by the production `requirements.txt` and no isolated environment was installed in this change. | `DEFER` intelligent execution. `browser_use_adapter.py` is only a fail-closed availability diagnostic; it does not invoke Browser Use or provide an Agent/Action bridge. Current intelligent execution is `UNAVAILABLE`: no server-owned Task/Run or Source/use resolver, no task-domain Gateway executor for Browser, no Action Firewall tool bridge, and no enforced DNS/private-IP/redirect/WebSocket egress boundary. The deterministic SYSTEM Browser remains independent; this batch adds a short-lived human lease and read-only navigation/history/scroll routes only. | MIT ([tagged LICENSE](https://github.com/browser-use/browser-use/blob/0.13.10/LICENSE)). Upstream tag declares `posthog==7.7.0` and several provider SDKs, including Ollama; upstream Agent/session defaults may initialize telemetry or a separate browser session. The LUMENIS adapter must not import/instantiate the package before every gate passes, must not call telemetry or any provider/cloud fallback, and must not claim `allowed_domains` is network egress enforcement. Direct pins are not a transitive hash lock; isolated installation and full notices remain unverified. |

## 2A. Approved owned-AI foundation and retained model inventory (2026-10-01)

| Component | Exact candidate / presence | Decision and owner | License / notices |
| --- | --- | --- | --- |
| [OpenAI gpt-oss-20b](https://huggingface.co/openai/gpt-oss-20b/tree/6cee5e81ee83917806bbde320786a8fb61efebee) | Revision `6cee5e81ee83917806bbde320786a8fb61efebee`; eleven pinned files (13,789,255,832 bytes, three shards totaling13,761,316,904) downloaded outside Git and fully SHA256 verified2026-10-01. No product inference runtime activated. | PO-approved foundation; ADAPT existing SYSTEM AI Gateway, owned LoRA training/deployment; text only, domain quality NOT_VERIFIED. | [Apache-2.0 LICENSE](https://huggingface.co/openai/gpt-oss-20b/blob/6cee5e81ee83917806bbde320786a8fb61efebee/LICENSE), [USAGE_POLICY](https://huggingface.co/openai/gpt-oss-20b/blob/6cee5e81ee83917806bbde320786a8fb61efebee/USAGE_POLICY); retain notices and label modifications. No ownership claim over base weights. |
| [Unsloth NF4 derivative](https://huggingface.co/unsloth/gpt-oss-20b-unsloth-bnb-4bit/tree/093fba6992ef5a7152481afec0bdfca1ac486998) | Revision `093fba6992ef5a7152481afec0bdfca1ac486998`; exact eleven-file training variant in the same canonical manifest. Five large-file hashes verified in actual free Colab. | ADAPT explicit optional T4 recipe; actual three-step public arithmetic training/save only, NOT_EVALUATED. Exact base revision is UPSTREAM_UNSPECIFIED, not asserted equal to the approved OpenAI snapshot. No active provider. | [Model card Apache-2.0](https://huggingface.co/unsloth/gpt-oss-20b-unsloth-bnb-4bit/blob/093fba6992ef5a7152481afec0bdfca1ac486998/README.md); retain upstream OpenAI attribution and policy. |
| Unsloth training stack | Actual Colab: unsloth2026.9.12, zoo2026.9.8, torch2.11.0+cu128, transformers4.56.2, trl0.22.2, bitsandbytes0.50.2, tokenizers0.22.2, triton3.6.0; helper rejects other versions. Not installed into Windows product runtime. | ADAPT optional training only; existing Gateway owns approval, local snapshots/datasets and candidate status. No copied notebook or production dependency. | [Unsloth Apache-2.0](https://github.com/unslothai/unsloth/blob/6c7f0445ff805e54b02fe4369ed77fef1fefa0ad/LICENSE); [Zoo LGPL-3.0](https://github.com/unslothai/unsloth-zoo/blob/37f5c88226d1291ae0d548d60d0e50bb3b5057d4/LICENSE). Reference [notebook LGPL-3.0](https://github.com/unslothai/notebooks/blob/92e38e86308748d18fc4cd4b104c4c6d3db1d67e/LICENSE). Preserve applicable notices/source and relinking obligations when distributing these components; dependency packaging remains a release gate. |

The optional training recipe follows the official
[OpenAI LoRA cookbook](https://developers.openai.com/cookbook/articles/gpt-oss/fine-tune-transfomers),
adapted to explicit local snapshots/data, offline loading and disabled Hub and
telemetry uploads. PyTorch/Transformers/PEFT/TRL/datasets remain optional,
uninstalled in the Windows product runtime; the isolated public Colab validation
has the versions above. Deployment-package licenses must still be reconciled. The cookbook's
H10080GB is a reference configuration, not a guaranteed minimum or promised
LUMENIS performance. Codex CLI licensing covers tool source, not Codex weights.

The observations below are historical inventory, not active routing. Product
Owner subsequently retired Ollama/LM Studio/llama.cpp/Zhipu inference for product
and development work. On 2026-10-06 the current workstation was rechecked: the
Ollama executable/service is absent, the user `.ollama` directory was removed,
and active OpenCode/PATH configuration no longer contains an Ollama provider.
Historical Ollama-managed Qwen/BGE rows therefore record provenance only; their
current physical presence outside that retired store is NOT VERIFIED and they
must not be treated as installed or available. Preserve compatibility interfaces
and provenance; do not restore these models, probes or fallbacks. The approved
foundation direction remains commercially permitted open weights plus
LUMENIS-owned tuning/deployment through the existing SYSTEM AI Gateway. No weight
download, training or deployment is implied by a register entry.

| Component | Observed runtime | Boundary / decision | License and distribution obligations |
| --- | --- | --- | --- |
| [Ollama](https://github.com/ollama/ollama) | HISTORICAL: previously observed 0.34.2; current workstation executable/service and `.ollama` store absent as rechecked 2026-10-06 | ADAPT existing SYSTEM AI Gateway; loopback-only image requests, no proxy/redirect; not a second AI owner | [MIT](https://github.com/ollama/ollama/blob/main/LICENSE), retain copyright/license when distributed; recheck shipped binary notices |
| [Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B) | HISTORICAL Ollama-managed observation: `qwen3.5:4b`, digest `2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd`; current presence NOT VERIFIED after retired Ollama store removal | ADAPT optional replaceable vision provider; image observations are derivative, human review pending | Model card declares Apache-2.0; preserve upstream attribution/license/notices on redistribution; quantization packaging must be reconciled before a distributed release |
| [Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B) | HISTORICAL Ollama-managed observation: `qwen3.5:9b`, digest `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`; current presence NOT VERIFIED after retired Ollama store removal | EVALUATE task-relevance reranking behind SYSTEM AI Gateway, only Reporting-authorized Canonical snippets; no Truth/Permission authority | [Upstream LICENSE](https://huggingface.co/Qwen/Qwen3.5-9B/raw/main/LICENSE) checked 2026-10-01: Apache-2.0; preserve attribution/license/notices; local quantization redistribution still requires package reconciliation; model and useful-result acceptance remain separate |
| [BAAI BGE-M3](https://huggingface.co/BAAI/bge-m3) | HISTORICAL Ollama-managed observation: `bge-m3:latest`, digest `7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab` (2026-10-01); current presence NOT VERIFIED after retired Ollama store removal | ADAPT bounded local embedding interface in existing SYSTEM AI Gateway; Reporting promotion rejected after actual quality/latency failures; no vector DB/new truth owner; replaceable model/adapter | Upstream model card declares MIT; retain copyright/license notices on redistribution, reconcile Ollama model packaging before distributed release |

Sources accessed 2026-10-01. [Ollama vision API](https://docs.ollama.com/capabilities/vision)
was part of the historical local-runtime evaluation. Those historical observations
do not establish current installation or availability after the 2026-10-06 cleanup.
Upstream weights remain third-party work; LUMENIS owns its adapters and business
orchestration, not the underlying foundation model. A historical local inference
receipt is not current product operation or release evidence.

## 3. Python development/test dependencies observed in `requirements-dev.txt`

`requirements-dev.txt` layers on top of `requirements.txt`; entries here are not production-runtime requirements merely because CI installs them.

| Component | Class | Purpose in repository | Integration / replacement boundary | License status | Replaceable |
| --- | --- | --- | --- | --- | --- |
| pytest | TEST ONLY | Automated test collection/execution and CI blocking regression gate | Test runner boundary; production runtime must not depend on it | VERIFY_BEFORE_RELEASE | Yes |
| pdfplumber | TEST ONLY | Pinned 0.11.10; independent extraction of exported PDF text | PDF verification only; no production import; upstream MIT, transitive notices still require reconciliation (https://github.com/jsvine/pdfplumber) | VERIFY_BEFORE_RELEASE | Yes |

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
| [video_player](https://github.com/flutter/packages/tree/main/packages/video_player/video_player) | 2.14.0 | PRODUCTION | Authorized saved MP4/WAV preview on the shared media workbench | `NativeMediaPlayer` adapter; receives a private lease path or authorized Web bytes only, never a source URL, Cookie or Product Core credential | BSD-3-Clause (installed package `LICENSE`; Flutter Authors) | Yes, bounded adapter |
| [video_player_win](https://github.com/jakky1/video_player_win) | 3.3.0 | PRODUCTION / Windows adapter | Native Windows Media Foundation MP4/WAV preview, seeking, volume and resource release | `WindowsMediaPlayer`; Windows-only implementation behind the same `NativeMediaPlayer` boundary | BSD-3-Clause (installed package `LICENSE`; upstream `jakky1`) | Yes, bounded adapter |

For these four rows, exact versions are from `app/pubspec.lock`; repository
URLs and licenses were checked against each installed package's `pubspec.yaml`
and `LICENSE` under the local Pub cache. The Flutter Authors packages use the
three-clause BSD license text; `flutter_acrylic` and `macos_window_utils`
include MIT license text. This records local package evidence only and does not
replace shipped-artifact notice reconciliation at release.

### 2026-10-05 media preview dependency decision

`video_player` 2.14.0 and `video_player_win` 3.3.0 were added because the
existing SH-01 workbench had a saved Artifact retrieval path but no Windows
native player for returned MP4/WAV bytes. The installed lockfile, package
metadata and BSD-3-Clause license files were inspected. `video_player_win`
uses Windows Media Foundation; its upstream documentation records that codec
availability depends on installed Windows codecs. LUMENIS reports an honest
playback failure and never downloads or installs codecs. It does not use the
package's experimental HTTP-header path or pass remote source URLs.

Web uses the browser media element over the same authorized bytes. The MDN
`loadedmetadata` contract applies a queued timeline seek only after duration
metadata exists. Package integration and fixture playback checks do not establish
a released media feature, a customer listening review, or support for all native
platforms. Release packaging must retain BSD notices and reconcile the actual
dependency graph shipped on each target.

## 5A. Engineering tools not shipped as LUMENIS product runtime

| Component | Current workstation state | Product boundary | License / release treatment |
| --- | --- | --- | --- |
| OpenCode CLI/server | 1.18.34 installed locally; current execution route is **SHELVED** by Product Owner | Development tool only; not SYSTEM AI Gateway, not product inference, not a C1-C6 Owner and not a Codex fallback | Not part of the product distribution by current design. If any OpenCode binary/source is ever bundled or redistributed, verify the exact upstream license/notices for that shipped version before release. |
| Codex / Codex CLI | External engineering runtime selected manually by Product Owner | Development/control tooling only; never LUMENIS-owned product AI or Product Truth | Tool/service terms are separate from LUMENIS proprietary materials and third-party product dependencies; do not infer model-weight rights from CLI/tool licensing. |

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

### Existing local FFmpeg/ffprobe media toolchain — verified 2026-10-02

The existing external-process media adapter uses FFmpeg and ffprobe
`9.0.2-essentials_build-www.gyan.dev`. Both binaries were inspected locally with
`-version`; `ffmpeg -L` reports GPLv3 or later, and configure includes
`--enable-gpl --enable-version3`. This exact build is GPL, not the project's
default LGPL configuration. Primary references (accessed 2026-10-02):
[FFmpeg licensing](https://ffmpeg.org/legal.html) and
[Gyan release-build provenance](https://www.gyan.dev/ffmpeg/builds/), which identifies
release9.0.2 and upstream commit946fcce07b. The extracted package includes LICENSE.

Binary SHA256: ffmpeg
`3256173f3f8bffd7df12227c68adf68025edb1832273a9530688a7bb1ed8edec`;
ffprobe `f0d36ecbbdd3bcfac3efa078c96c7271c2e68b3810595552ac3b7f17e9a65c52`.
Classification: existing OPTIONAL ADAPTER / local runtime tool, not committed or
distributed here. Boundary: Shared Artifact/video/podcast subprocess adapters;
existing LUMENIS_FFMPEG_PATH and LUMENIS_FFPROBE_PATH deployment settings. No new
runtime, store, platform library or bundled binary is introduced. Replacement can
use a separately verified compatible executable behind the same adapter.

Before distributing this exact build, reconcile its corresponding source/build
configuration, retained license/notices and compiled-library obligations against
the actual package. Distribution/commercial packaging clearance is NOT VERIFIED;
local execution/version checks do not establish that release gate.

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

### 2026-09-28 Web composite-emoji fallback

ADOPT unmodified Noto Color Emoji 2.057, official `googlefonts/noto-emoji` commit
`e20cbc2bbec1926686be9f9bee7d1d2cfa1fea0e`, path `2D/fonts/NotoColorEmoji.ttf`:
https://github.com/googlefonts/noto-emoji/tree/e20cbc2bbec1926686be9f9bee7d1d2cfa1fea0e/2D/fonts .
Maintained upstream; source and bundled `2D/fonts/LICENSE` inspected 2026-09-28.
SIL OFL 1.1 permits application redistribution with the font's copyright/license
notice. The original font and `NotoColorEmoji-OFL.txt` ship together as Flutter
assets, never as a standalone sold font. No font modification/subsetting occurs.

Class: PRODUCTION ASSET behind the existing Theme's Web-only fallback list,
after SC/KR. Replaceable; no new package, account or paid API. Native fallback
order is unchanged. The original adds 10,730,124 bytes before compression.
Font SHA256 `15671215ab769fdc7162a045d56fd7d7e477c51b04e6b3c761d914d8fdd6cc44`;
notice SHA256 `6a73f9541c2de74158c0e7cf6b0a58ef774f5a780bf191f2d7ec9cc53efe2bf2`.
Sampled composite-glyph rendering and exact local-file return are recorded in
`evidence/round-08/ROUND-08-WEB-EMOJI-FALLBACK-2026-09-28.md`.
This is not a claim of complete Unicode coverage or native-device acceptance.

### 2026-10-02 bounded training phase signature adapter

ADAPT `cryptography` 50.0.2 behind the existing SYSTEM Security owner for
Ed25519 derivative phase receipts. The concrete gap is asymmetric verification
in an approved interactive training notebook without exporting the local
Evidence HMAC key or creating another Permission authority. This adapter does
not grant MODEL_TRAIN permission, host a service, or perform model inference.

Official tagged metadata/license inspected 2026-10-02:
https://raw.githubusercontent.com/pyca/cryptography/50.0.2/pyproject.toml and
https://raw.githubusercontent.com/pyca/cryptography/50.0.2/LICENSE . License:
Apache-2.0 OR BSD-3-Clause; retain the upstream license/copyright notices and
the license material of the statically linked wheel components. Current
PyPI metadata identifies maintained stable 50.0.2 and CPython-compatible
Windows AMD64 wheels. Source API reference:
https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/ .

Class: SYSTEM SECURITY ADAPTER / REQUIRED SIGNATURE-TEST DEPENDENCY.
Historical base ce5b5a632922b4efd3a96942e1d4084c2cb72044 registered the adapter
while its manifest stayed local. On 2026-10-04 the exact pinned dependency is
included with W6's hosted-CI repair: published Ed25519 modules already require
it, and the clean runner otherwise fails during test collection. This changes
installation reproducibility, not Permission, key configuration or training
admission. Upstream tagged metadata/license rechecked on 2026-10-04 supports
Python >=3.9 including the hosted Python3.11 environment.
The local Python 3.13 environment installed cryptography 50.0.2, cffi 2.1.1
and pycparser 3.0 from binary wheels. Installed metadata independently read
2026-10-02 declares `cffi` 2.1.1 as MIT-0 and `pycparser` 3.0 as BSD-3-Clause;
do not substitute older releases' license declarations. Their bundled license material must
remain with any redistributed dependency; packaging/other-target runtime
acceptance is not established by this local installation. Only ephemeral
test signing was verified; no production signing key was provisioned by the
dependency installation. Private key configuration stays inside existing
SYSTEM Security secret management; only public verification keys may leave
the workstation. Replacement remains possible behind the same versioned
receipt contract and requires equivalent signature/expiry/binding tests.

### 2026-10-08 已批准研究范围内的成熟媒体组件准入

本表是条件研究处置，不是安装/采用/再分发许可，具体版本与义务待实际选择时核准。

| 项目 | 本次状态与适配边界 | 接收Owner与必要判断 |
| --- | --- | --- |
| FFmpeg / FFprobe | REUSE_EXISTING_FIRST；读取实际使用构建/路径，不新增媒体Runtime | C4/C6核能力、依赖、编译选项和许可证；LGPL/GPL及libx264等随构建变化，不笼统承诺商用分发许可 |
| OpenTimelineIO | CONDITIONAL_NOT_ADOPTED；仅有实际格式互通需求才适配 | C4转换层；不提供播放器/renderer，不替代现有Timeline |
| RNNoise | CONDITIONAL_NOT_ADOPTED；现有滤镜不满足的真实降噪缺口才评估 | C4/C6核音频质量/延迟/平台/代码与模型许可 |
| whisper.cpp | CONDITIONAL_NOT_ADOPTED；离线转录缺口，经C2原Gateway/模型准入 | C2/C4区分代码、依赖和权重许可，CPU/GPU、zh/en/ko真实效果；不恢复已退役LLM provider、不接付费云转录 |
| Flutter播放/录音/波形组件（含just_audio、record） | CONDITIONAL_NOT_ADOPTED；先复用SH-01播放与FFmpeg解码/Flutter绘制 | F/C4/C6证明现有缺口再选；录音真实许可/文件/中断，四端及目标OS逐一验证 |
| libopenshot / MLT | DEFER_PENDING_PROVEN_GAP；禁止替换已可用内核 | C4证明原renderer无法合理满足已批准任务，M审兼容性和许可后才适配 |
| Audacity；Dify | MECHANISM_REFERENCE_ONLY；未许可引入其完整代码 | 前者GPL兼容与后者附加许可条件按精确版本核查；不得据公开仓库推断可复制 |

每次采用记录固定version/commit、源/依赖/权重/二进制许可与再分发义务、Windows/macOS/Linux/Android/iOS及Web适用性、维护/漏洞/性能/离线/资源、隔离验证、可替换接口与卸载回退。不得为“免费”无理由全局装大型依赖、增加登录/费用或扩大权限。现有模型、Identity、Permission、Evidence、Artifact及媒体Owner保持唯一。本轮规则更新未安装这些可选组件。
