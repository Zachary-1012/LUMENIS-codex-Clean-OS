# LUMENIS Third-Party / Open-Source Component Register

> Status: CANONICAL REGISTER
> Scope: direct repository dependencies and important optional external components
> Source of truth for presence: current manifests/source, not historical docs.
> License rule: `VERIFY_BEFORE_RELEASE` means the repository has not yet recorded verified license evidence here; do not guess.

## 0. Source license and retained third-party rights — 2026-10-10

Original LUMENIS software and accompanying original technical documentation now
use the unmodified root Apache-2.0 LICENSE. This does not relicense dependencies,
vendored source, fonts, model weights, datasets or customer materials. See
[licensing scope](../LICENSING.md), [attribution](../NOTICE) and the
[third-party notice index](../THIRD_PARTY_NOTICES.md).

Existing VERIFY_BEFORE_RELEASE / NOT VERIFIED entries remain unresolved for the
specific third-party material and actual distribution concerned. They are not
converted to PASS, and they do not invalidate the owner's Apache-2.0 grant for
original LUMENIS software. Source licensing, shipped-package clearance, historical
secret/privacy review and runtime/user-outcome acceptance are separate decisions.

## 1. Policy

Third-party software may accelerate delivery but must remain bounded and replaceable where practical.

Preferred integration shape:

```text
LUMENIS Contract
→ Adapter / Boundary
→ Third-party implementation
```

Third-party components must not silently become the owner of LUMENIS Canonical Data, Evidence, Metric, Permission, Subject Context or business truth.

### 2026-10-26 Collector media and public-parser source adoption

This adopts mature source through the existing SYSTEM Collector/PublicSource and
Shared Media/Artifact owners. The complete Global §10/J1/J7 requirements remain;
supported formats, source access, actual byte coverage and semantic execution are
separate observations. No installation or isolated test closes the product job.

| Upstream and fixed version | Actual integration and licensing evidence | Execution boundary |
| --- | --- | --- |
| [yt-dlp 2026.10.21](https://github.com/yt-dlp/yt-dlp/releases/tag/2026.10.21), [PyPI wheel](https://pypi.org/project/yt-dlp/2026.10.21/) | `requirements.txt` pins `yt-dlp==2026.10.21`; official wheel SHA256 `94a3a3e2c423129d0bbd2f1be000c4171fa1226c29e251c84aff868f2851c247` (3,188,012 bytes), Python >=3.10. Read `YoutubeDL`, networking `Request/Response`, Generic/HTML5 embed parsers, HLS/DASH native downloaders and wheel LICENSE. The wheel is Unlicense; retain [complete original license](../vendor/lumenis-reuse-notices/yt-dlp-2026.10.21-Unlicense.txt). PyInstaller distributions have additional/GPL obligations and are not adopted. | `adapters/public_media.py` embeds the fixed library, with `public_source.py` as the sole HTTP/DNS/TLS/redirect/SSRF boundary. No CLI, external config, browser Cookie, netrc login, plugins, JS runtime/remote components, geo bypass, DRM/decryption, external downloader or automatic provider fallback. Explicit public GET metadata/media only; request/byte/time budgets and task cancellation remain. Native HLS/DASH fragments and manifests retain original content hashes/bytes through the existing Artifact owner. Separate native video/audio tracks may be copy-muxed only with the already owned local FFmpeg; keep both tracks and distinguish the assembled representation. No model/semantic understanding is claimed. |
| [OpenCLI](https://github.com/jackwener/OpenCLI/tree/aeaff2b796efabb7fd46654112418ab61fcae917), commit `aeaff2b796efabb7fd46654112418ab61fcae917` | Apache-2.0, copyright 2025 jackwener. Full fixed root [LICENSE](../vendor/lumenis-reuse-notices/OpenCLI-aeaff2b7-Apache-2.0.txt) retained; no root NOTICE or additional notice in the selected parser paths. C1 adapts YouTube utils/video/channel/search/feed/comments; Reddit `web-search.js` search-post-unit/telemetry identity and source partial-cursor parsing; LinkedIn post-root/posts-core/profile-read/company parsers; Tieba read/search/utils public DOM/Vue props. Reddit `read.js` was reviewed, but its COOKIE JSON/morechildren/truncate/zero defaults are rejected; existing media helpers are retained, not counted as new source reuse. Modified files retain pin, source and modification notices. | Existing `youtube.py`, `reddit.py`, `linkedin.py`, `tieba.py` and their SYSTEM public/browser helper consume selected parsing rules. Reject COOKIE JSON/morechildren, zero defaults, automatic expansion/editing, signed `page_pc`, Cookie export, auth and publishing. Channels auth/publish is not collection and is not adopted. No OpenCLI runtime, profile, second browser/Collector, API or data store is installed. HTTP/browser choice is explicit before acquisition, never a response to a refusal. |
| [sipher](https://github.com/stepbyjason-lab/sipher/tree/2c3470f973d47842a13b70c552872a6ceabd7a9b), commit `2c3470f973d47842a13b70c552872a6ceabd7a9b` | MIT, copyright 2026 stepbyjason-lab. Full [LICENSE](../vendor/lumenis-reuse-notices/sipher-2c3470f9-MIT.txt) retained (SHA256 `70a715832e5121e35550059cac4b965e31cfcf4d08201274e8d09ded5da68370`). Exact `adapters/naver_blog/scrape.py` original SHA256 `384d76c1d4dbef97d34ffc1ac68577a779b36e1f27e21c2df6853589321476ec`; C1 adapts only body/iframe parsing in the existing Naver/Daum source owner. | Original fixed research bytes remain in the protected existing delivery work folder; no setup, CLI, AI, OCR, external provider, browser identity or session runtime is run. No unlicensed `naver-post-crawler` source is copied. Production adaptation preserves original source/modified-file attribution and uses the existing Source transport and intake. |

The 2026-10-08 yt-dlp DEFER record remains historical evidence. This bounded
adoption resolves its explicit identity, transport, resource and library-license
conditions; it grants no additional SourceUse, commercial media rights, export,
training, account, deployment or package-distribution acceptance. Rollback removes
the exact dependency/binding while preserving Source originals, component hashes,
Artifacts, failed receipts and their versioned lineage.

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
| python-pptx 1.0.2 | PRODUCTION | Editable PPTX export through existing SavedWork and ReportExporter | Shared Reporting; scope, source-use, immutable readback and DATA_EXPORT remain in the existing owner | MIT; verified against installed 1.0.2 distribution metadata and LICENSE on 2026-10-22 (SHA-256 `7652f271e46d0d533e9dc463f3b5fcbdcacf4d6a9c8d6b554d15efd0f37f6132`); preserve its notice in shipped packages | Yes |
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
| packaging 26.3 | BUILD TOOLING | Parse dependency requirements, markers and canonical names in `app/tool/build_windows.ps1`; pinned in `requirements.txt` | Existing Windows build/dependency inventory; [PyPA source](https://github.com/pypa/packaging), installed distribution declares Apache-2.0 OR BSD-2-Clause; preserve the selected license and notices when redistributed | VERIFY_BEFORE_RELEASE | Yes |
| colorama | PRODUCTION/CLI | Terminal output compatibility | CLI only | VERIFY_BEFORE_RELEASE | Yes |
| tqdm | PRODUCTION/CLI | Progress display | CLI only | VERIFY_BEFORE_RELEASE | Yes |
| aiohttp | OPTIONAL ENHANCEMENT | Async collector HTTP; manifest notes synchronous fallback | Collector network adapter | VERIFY_BEFORE_RELEASE | Yes |
| yyds-logger | OPTIONAL ENHANCEMENT | Enhanced logging; manifest notes stdlib fallback | Logging adapter | VERIFY_BEFORE_RELEASE | Yes |
| tenacity | OPTIONAL ENHANCEMENT | Retry/backoff | Retry policy boundary | VERIFY_BEFORE_RELEASE | Yes |
| alembic | PRODUCTION TOOLING | DB migration tooling | Migration boundary; migration gate required | VERIFY_BEFORE_RELEASE | Yes |
| feedparser | PRODUCTION | RSS / Atom public-feed parsing, as declared in `requirements.txt` | Public-feed acquisition adapter | VERIFY_BEFORE_RELEASE | Yes |
| [markitdown[pptx]](https://github.com/microsoft/markitdown/tree/v0.1.8) 0.1.8 | PRODUCTION / OPTIONAL IMPORTER ENHANCEMENT | Local HTML/PPTX to Markdown conversion behind `lumenis/importer/parser.py`; no network, Evidence or Canonical ownership | Importer adapter only; existing PDF/Word/Excel parsers remain authoritative; remove or replace by the same ParseResult contract | MIT ([v0.1.8 license](https://github.com/microsoft/markitdown/blob/v0.1.8/LICENSE)); python-pptx and transitive dependencies require separate notice/license reconciliation | Yes |

| [xlrd](https://pypi.org/project/xlrd/2.0.2/) | PRODUCTION | Importer legacy XLS parsing | lumenis/importer/parser.py; preserves original bytes and cached-value limitations | VERIFY_BEFORE_RELEASE | Yes |
| [jsonschema](https://pypi.org/project/jsonschema/) | PRODUCTION | Registered MCP tool JSON Schema validation | mcp_skill_runtime.py; validation only, not execution permission | VERIFY_BEFORE_RELEASE | Yes |
| [statsmodels](https://pypi.org/project/statsmodels/0.14.6/) | PRODUCTION | Shared statistical estimation | lumenis/shared/reporting/statistics_methods.py; source/scope and uncertainty retained | VERIFY_BEFORE_RELEASE | Yes |
| [ruptures](https://pypi.org/project/ruptures/1.1.10/) | PRODUCTION | Shared trend change-point detection | Existing Shared Reporting statistics owner; no independent truth store | VERIFY_BEFORE_RELEASE | Yes |
| [networkx](https://pypi.org/project/networkx/3.5/) | PRODUCTION | Shared graph computation | lumenis/shared/reporting/statistics_methods.py; bounded computational adapter | VERIFY_BEFORE_RELEASE | Yes |
| [scipy](https://pypi.org/project/scipy/1.17.1/) | PRODUCTION | Shared bounded scientific computation | requirements.txt selects 1.17.1 on Python <3.12 and 1.18.1 on Python >=3.12; same Reporting owner | VERIFY_BEFORE_RELEASE | Yes |
| [scikit-learn](https://pypi.org/project/scikit-learn/1.7.2/) | PRODUCTION | Shared calibration, clustering and text transforms | Existing Shared Reporting statistics owner; no model-service or weight license grant | VERIFY_BEFORE_RELEASE | Yes |
| [pymc](https://pypi.org/project/pymc/5.25.1/) | PRODUCTION | Existing bounded MMM statistical model | lumenis/shared/reporting/statistics_mmm.py; execution budget and actual diagnostic state required | VERIFY_BEFORE_RELEASE | Yes |
| [arviz](https://pypi.org/project/arviz/0.22.0/) | PRODUCTION | Existing MMM posterior diagnostics | lumenis/shared/reporting/statistics_mmm.py; no false certainty or missing-to-zero conversion | VERIFY_BEFORE_RELEASE | Yes |
| [pdfplumber](https://pypi.org/project/pdfplumber/0.11.10/) | PRODUCTION | Local PDF text/table parsing and test verification | lumenis/importer/parser.py; runtime dependency, not test-only; no cloud parser | VERIFY_BEFORE_RELEASE | Yes |
| [ortools](https://pypi.org/project/ortools/9.15.6755/) | PRODUCTION | Shared bounded scheduling optimization | lumenis/shared/reporting/statistics_methods.py; official CP-SAT adapter, no separate task scheduler | VERIFY_BEFORE_RELEASE | Yes |

MarkItDown's 0.1.8 distribution metadata requires `magika~=0.6.1` unconditionally; the current bundled closure selects Magika 0.6.3. Its local `_get_stream_info_guesses` path calls `Magika.identify_stream` for content inspection even when an extension is supplied, so the explicit `.html`/`.pptx` dispatch does not remove this runtime dependency. The [PyPI 0.6.3 release](https://pypi.org/project/magika/0.6.3/) records verified provenance for the Windows wheel (SHA-256 `e57f75674447b20cab4db928ae58ab264d7d8582b55183a0b876711c2b2787f3`) from `google/magika` commit `a04562a9bb5d52c809a4424911ca8d07c0265767`; the pinned [Python project metadata](https://raw.githubusercontent.com/google/magika/a04562a9bb5d52c809a4424911ca8d07c0265767/python/pyproject.toml) declares Apache-2.0 and the commit's root [LICENSE](https://raw.githubusercontent.com/google/magika/a04562a9bb5d52c809a4424911ca8d07c0265767/LICENSE) is retained in the bundle. That release contains `magika/models/standard_v3_3/model.onnx`; the installed distribution RECORD binds the packaged file to SHA-256 `fe2d2eb49c5f88a9e0a6c048e15d6ffdf86235519c2afc535044de433169ec8c` (3,163,737 bytes). The [pinned model documentation](https://raw.githubusercontent.com/google/magika/a04562a9bb5d52c809a4424911ca8d07c0265767/assets/models/standard_v3_3/README.md) identifies its content-type classification outputs. No model-directory LICENSE/NOTICE or root NOTICE exists at this source commit; the model is covered by the Apache-2.0 project/package release. This is a third-party document file-type classifier only, not LUMENIS-owned/domain model weights, business inference, training, or a bundled training dataset. The root source repository does not provide separate licensing evidence for Magika's training data, which is not shipped here.

2026-10-21 manifest reconciliation: the linked upstream PyPI project/release
pages were read for identity/version provenance. This does not certify the
actual shipped wheel/sdist, transitive licenses or notices; the explicit
VERIFY_BEFORE_RELEASE state remains. [SciPy 1.18.1](https://pypi.org/project/scipy/1.18.1/)
is the separate Python >=3.12 pin. This register has one row per package identity;
conditional manifest entries are not duplicate components. Library source terms
never license model weights, source datasets or customer materials.

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
| [xlwt](https://pypi.org/project/xlwt/1.3.0/) | TEST ONLY | Pinned 1.3.0; synthetic BIFF8 fixture writing | requirements-dev.txt only; production XLS parsing uses xlrd; upstream release identity checked, distribution notices not cleared | VERIFY_BEFORE_RELEASE | Yes |

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
| Codex / Codex CLI | External engineering runtime selected manually by Product Owner | Development/control tooling only; never LUMENIS-owned product AI or Product Truth | Tool/service terms are separate from the Apache-2.0 license for original LUMENIS software and from third-party product dependencies; do not infer model-weight rights from CLI/tool licensing. |

## 6. Built-in / platform dependencies

These are not third-party packages in the manifests but materially affect operation:

| Component | Class | Current role | Portability concern |
| --- | --- | --- | --- |
| SQLite (`sqlite3`) | PYTHON STDLIB / DATA | Local persistence | DB isolation and migration contracts remain release-critical |
| Windows PowerShell 5.1 | PLATFORM | Current canonical production launcher | Current production launch path is Windows-specific |
| Microsoft Edge | EXTERNAL PLATFORM | Headless engine of built-in background collectors 9223–9228 only; never a visible/resident collection browser | Installation path/browser availability must be detected rather than assumed long-term |

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

The 2026-10-23 local media recovery additionally verified Gyan's **9.0.2 full
build** from its official release archive. The essentials build lacks libflite;
the full build exposes that existing local speech adapter. Archive SHA256
`f0e46253c70dfe902bac915dfb4224f0cf1b7c6eeab9da2ccc9a5581f9a71b13`;
ffmpeg `589e50b766d251afdf181dd664d40bd94407e200b019989fd7468c7d118a28d0`;
ffprobe `02264dfa4f56baaa31e443ece8aa16d397f6b008200e7fd184d22b9009e75fd3`.
The archive's LICENSE and README remain beside the isolated local tools.
Only the owned manual-workspace runtime was bound using the existing two path
settings. The essentials binaries, production runtime and global settings were
unchanged and remain the rollback route. This is installed local capability,
not shipped binaries, natural-speech quality acceptance or an AI-model result.
English synthetic output and normal podcast import/save/export/reopen were
observed; missing eSpeak voices are not claimed available. No external speech
service or parallel adapter was introduced. See the current podcast operation
receipt for actual versions and remaining acceptance.

Before distributing either exact build, reconcile its corresponding source/build
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


### 2026-10-09 development-only Ruff CLI

Ruff 0.16.9 (Astral; MIT) is installed as a local static-analysis/format-preview CLI, matching the existing VS Code bundled version. Official [installation documentation](https://docs.astral.sh/ruff/installation/) and [versioned PyPI metadata](https://pypi.org/project/ruff/0.16.9/) identify the distribution. Windows wheel SHA-256: `6bd40fec8cd4c8a3d4dd589bd8ad4e6320c13c29234159bfd959a40d529d597b`; downloaded bytes were checked before installation. Runtime executable and rollback receipts remain workstation-local. This does not add a shipped LUMENIS dependency, AI provider, account, paid obligation, automatic fixer or product acceptance proof.

### 2026-10-10 OpenAI Math v2 — optional local proof tooling

The mathematical Python ports are independently authored v2 source with fixed paper/specification attribution; no complete upstream prover/LLM/provider is shipped. OpenAI Math [fixed license](https://github.com/openai/math/blob/fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb/LICENSE) is Apache-2.0. Upstream paper attribution/version and numerical limits remain attached; copying proof material for redistribution would also require its original license/notices.

| Component | Exact pin / scope | License and replacement |
| --- | --- | --- |
| Lean | 4.34.1 Linux; official portable archive SHA `47bf4bbd78f70c2e9670598ab7124d92b6efb7330ff33e5fbb4030f6fd72e4e4` | Apache-2.0; isolated user-level proof compiler, not product Runtime. |
| Mathlib | `d13f23b723b8a846827a245b89c10fc7d3f11612` plus declared locked dependencies | [Apache-2.0](https://github.com/leanprover-community/mathlib4/blob/d13f23b723b8a846827a245b89c10fc7d3f11612/LICENSE); fixed trusted compile cache, no runtime product dependency. |
| Comparator | `d03acab154d269c06e60e4de7e4cc85deebff94b` | [Apache-2.0](https://github.com/leanprover/comparator/blob/d03acab154d269c06e60e4de7e4cc85deebff94b/LICENSE); theorem statement/kernel/axiom comparison, never fake sandbox. |
| lean4export | `076e8e57707e813375e8f9da8bf989799ace9680` | [Apache-2.0](https://github.com/leanprover/lean4export/blob/076e8e57707e813375e8f9da8bf989799ace9680/LICENSE); compatible fixed dependency only. |
| Landrun | 0.1.17 Linux official binary SHA `6ada66a06669e8994e174a7271af2db636308e55a0d6ec896cc7d326b46727f6` | [MIT](https://github.com/Zouuup/landrun/blob/v0.1.17/LICENSE); kernel ABI compatibility explicit, systemd AF_UNIX guard retained. |

Tools are installed only under the existing development tool root and WSL user-local `lumenis-math-v2`; no global PATH, account, proxy, production dependency, service/provider, paid resource or elevated installation changed. Rollback is removal of this specifically inventoried portable tool directory after its own proof job ends; caches and original failure/source receipts remain recoverable. Mathematical execution in LUMENIS uses existing Python standard-library dependencies. Model data/weights/training/promotion keep separate Permission approval.


### 2026-10-13 bounded JSON-shape / Windows static-import adoption

Direct PO approved `LUMENIS_Reuse_20261013(1).zip`, SHA-256
`79ea56ad35ae1acb2e2953c2229a6d428a2503d7c7a41f3f6ddbc6867b946329`.
Existing Collector owner receives value-free response-shape observations through
AdapterResult and the current Douyin adapter; C6 build tooling receives optional
single-file static DUMPBIN diagnostics. C5 Evidence persistence is not asserted.
No platform/browser/model/OS executor or dependency is added, and no live source
or protected identity is accessed. Same-run live diagnostic recovery remains unverified.

| Component | Fixed original / adoption | License / boundary |
| --- | --- | --- |
| Browser.Reverse.Engineering.Toolkit | `ecbe61af5004f6efa493749a623fbd98ab307a37`, SiteSnapshotter/injector.js shapeOf/collectJsonKeys/detectPagination ideas; independently authored Python adaptation | MIT, copyright 2020-2026 Dvurechensky; bounded type-only metadata, not source truth or a fetch hook |
| BinNexus | `269444ef4433cc582a57f7fa6854c2448ad5ba6b`, app/binnexus/analysis/static/imports.py:16-24; verbatim regex/function extraction | MIT, copyright 2020-2026 Dvurechensky; only static direct-import observation, no DLL or target execution |
| Delivery helpers | response_shape.py and dll_imports.py from the reviewed archive plus bounded existing-owner binding | MIT delivery notice retained; standard library only; Windows tool installation and runtime acceptance excluded |

Full notices are retained in `vendor/lumenis-reuse-notices/` and indexed by
`THIRD_PARTY_NOTICES.md`. Rollback removes only this exact hash-matched delta;
retain older native-field/failure-state/build safeguards and unrelated dirty work.

## 2026-10-13 Selected component: rich-text editor

`flutter_quill` (pub.dev) is the selected rich-text editor, used only behind a LUMENIS adapter; its stored format must align with the SavedWork contract (backend owner). Not yet added to `app/pubspec.yaml`. License: VERIFY_BEFORE_RELEASE.

### 2026-10-14 transitions-ui-generation — generated-result motion

Source: [Jakubantalik/transitions.dev@9398105c07dafe877e43197b71c15a10a3b0e3f6](https://github.com/Jakubantalik/transitions.dev/tree/9398105c07dafe877e43197b71c15a10a3b0e3f6/skills/transitions-ui-generation); reviewed SKILL.md, both mode references, ui-generation.js/css and LICENSE.txt. Source runtime hashes: JS `b6f63c95cf1a20048f350d3200e907511f464c85216ffe58f4691cd8f53f4bfe`; CSS `1a55fce94aad06dcea99a67089175ac67c7666c8ebecf5b54a67a9a08fc8117d`. Verified 2026-10-14.

License: custom Transitions.dev, free personal/commercial use, modification and distribution inside a product; no repackaged competing transition library/motion pack. Tooling elsewhere is MIT, but this skill/runtime is not under that blanket license. No paid plan, external inference, network runtime or account is needed for these files. Preserve upstream attribution/license when distributing adapted source; product branding is excluded. No whole skill collection is installed or redistributed.

Decision: ADAPT in existing Flutter/Core visual primitives and permitted result consumers under Experience §19. The upstream measures DOM and cannot directly measure Flutter canvas; use actual Flutter render geometry with explicit font/layout readiness. Existing Astro Website remains its own DOM surface. No global auto() scan, route/list-row reveal, fake generation texts, or replacement of approved product motion. This documentation decision alone is not an implemented/runtime-verified claim; code/actual target results remain separately recorded in CURRENT. The effect remains removable without changing data, permission or result identity.

### 2026-10-14 六项开源采用 / Six bounded OSS adaptations

PO supplied these repositories for useful adaptation and secondary development. Reviewed fixed source, implementation/skill entry points and license files on 2026-10-14; popularity figures were not used as admission evidence. Decisions below map into existing plan G109/G130/G159/G163, media E1/E8 and Experience result-visualization clauses. They record methods adopted and optional component candidates, not installed dependencies, copied assets, runtime acceptance or a new roadmap.

| Repository / fixed commit | Verified license and inspected source | Existing-owner decision and useful outcome |
| --- | --- | --- |
| [storytold/artcraft](https://github.com/storytold/artcraft/tree/d4e4ac69bbd93d237eaf5d0260bc6a5ff3a5e373) | MIT OR Apache-2.0 for source; `LICENSE-MIT`, `NOTICE`, `frontend/libs/components/video-editor/src/lib/core/managers/save-manager.ts`, `frontend/libs/components/pagescene/src/lib/engine/save_manager.ts`, `frontend/apps/artcraft/app/src/pages/PageScene/sceneOutputAdapter.ts` | ADAPT methods in C4 editable Timeline/Artifact and F editing: immutable edit snapshots, stale-load ticket rejection, explicit pending save and independent asset readback/preview. Keep independent manual creation. Do not import its provider/account stack or create a second scene/Timeline owner. |
| [wheresryan22/anatomy](https://github.com/wheresryan22/anatomy/tree/e6600ffc4e8e6620eeb45bf49bcdbd5e4b84163f) | MIT, copyright Ryan; `LICENSE`, `SKILL.md`, `kit/iso-kit.mjs`, `kit/audit.mjs` | ADAPT same-data geometry/labels/readout, projection fitting and geometry validation in F/C5 task-specific explanatory results. A technical figure must accurately represent the actual relationship. Isometric diagrams are an optional representation, never a product-wide style or proof of mechanism/causality. |
| [cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design/tree/11b08eade8049c441ed3df1895e3b527c26c0fbe) | Skill MIT, copyright Cathryn Lavery; `LICENSE`, `THIRD_PARTY_LICENSES.md`, `skills/diagram-design/SKILL.md`, semantic-pattern/data-flow references, `scripts/verify-geometry.py`, `scripts/lint-render.py` | ADAPT semantic choice of diagram, coherent reading order, static completeness, label/connector checks and constrained render diagnostics in existing F visualization/C5 Reporting/Artifact. The inspected catalog has 45 types; neither a catalog count nor a generic HTML+SVG template defines LUMENIS scope. |
| [mattpocock/skills](https://github.com/mattpocock/skills/tree/49dd158d1076134a641b33efb035946536778336) | MIT, copyright Matt Pocock; `LICENSE`, `skills/engineering/codebase-design/SKILL.md`, `DEEPENING.md`, `skills/productivity/writing-for-agents/SKILL.md` | ADAPT interface invariants, ordering/errors/configuration/performance review and progressive context in current engineering owners. Apply to actual Timeline/Artifact and Reporting/SavedWork seams, preserving callers and recovery. Existing context routing is reused; the upstream multi-agent design procedure does not dispatch extra windows or justify speculative adapters. |
| [lyogavin/airllm](https://github.com/lyogavin/airllm/tree/cb807515f640f9489f267adc0c66afb249e90a17) | Apache-2.0, root and `air_llm/LICENSE`; `air_llm/setup.py` v4.0.0, `airllm/auto_model.py`, `airllm/airllm_base.py`, `airllm/airllm_lora.py` under `air_llm/` | CONDITIONAL C2 resource candidate: layer streaming/prefetch and LoRA with recomputation can be evaluated against an exact approved model/recipe. Current source includes Qwen-specific LoRA training, not only inference; that training class is not a gpt-oss implementation. No exact gpt-oss/MXFP4 compatibility or workstation throughput was demonstrated; existing Gateway, owned base model and free-resource/Permission boundaries remain. |
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes/tree/3de4763d53de194b4ddc4d5d8f724fe0e3b3ca74) | Apache-2.0, copyright 2026 HeyGen; `LICENSE`, core/CLI package manifests v0.8.155 (CLI Node >=22), render documentation, `renderFrameSibling.ts`, `renderCancellation.ts`, CLI render `execute.ts` | ADAPT render-readiness/cancellation ideas; CONDITIONAL optional C4 HTML-video renderer behind the existing media boundary. Use for editable titles, explanatory graphics or permitted composition clips, then probe/hash/import into existing MediaAsset/Timeline/Artifact. Existing FFmpeg rendering stays available. Do not adopt cloud hosting, AI provider defaults, Studio as another product or a parallel task runtime. |

**Code and asset rights.** Artcraft's NOTICE excludes its marks, third-party provider logos, named game audio/characters, skyboxes and referenced animation assets; permissive source licensing does not clear them. Diagram Design lists Tabler MIT, Simple Icons CC0, Devicon MIT, Instrument Serif OFL and separately attributed icons; retain the actual component notices and trademark boundaries for anything shipped. AirLLM's software license does not license model weights or data. For adapted/copied source, retain the chosen upstream license/copyright, NOTICE where applicable and changed-file attribution in the existing notice index; no upstream code or assets are redistributed in this research update. LUMENIS original logo/icons, approved visual language and existing motion remain.

**Concrete adaptation checks.** Artcraft's sampled save manager clears its dirty marker before awaiting save; do not copy a failure path that loses pending edits. Existing LUMENIS saves must retain failed/retryable changes, reject stale parent versions, preserve old artifacts and distinguish committed output from failed preview/readback. A cancelled/stale load cannot replace the current project. Anatomy/Diagram Design geometry, values, labels, accessible description and export must derive from one source/result version; verify clipping, overlap, connector ownership, long zh/en/ko labels, keyboard/touch, narrow layouts and still output. External SVG/HTML is untrusted: use the existing import/render owner to reject scripts, event handlers, unsafe external URLs and unsupported content before display/export. Do not insert raw generated HTML/SVG into privileged product pages or create a second sanitizer/renderer. Real result data and accessible text remain usable with motion skipped; animation choices do not reduce existing effects.

**Resource and renderer limits.** AirLLM uses disk/RAM traffic and architecture-specific loading; advertising 70B on 4GB is not a latency, model-quality or local-compatibility guarantee. Fixed source contains `trust_remote_code` paths: review/pin that model code before any execution. Verify the approved model layout/quantization, PyTorch/Transformers/accelerator compatibility, disk budget, peak RAM/VRAM, cold/warm throughput and output equivalence before binding. Preserve original weights/checkpoints, bounded cancellation and reload. Its LoRA path separately requires exact MODEL_TRAIN/data rights, checkpoint reload and independent held-out improvement; nothing here starts training or replaces gpt-oss. Hyperframes may download/use a browser: resolve exact approved executable/version and isolated render profile, not personal or Collector sessions. Experimental HTML-in-canvas APIs require capability detection and a verified supported fallback; do not change user browser flags. Pin fonts/media, dimensions, frame/time base and render input; wait for real layout/assets, use task-scoped cancellation, decode/probe the completed video and retain editable input plus source rights. A successful preview/container/CLI exit does not prove final frames, audio, alpha or saved project recovery.

**Acceptance and rollback.** Before a component is bound, the existing owner demonstrates its concrete gap, compares the present implementation, records exact dependency/notice changes and verifies real edit → render/compute → useful output → save → revise → reopen/recover. Graphic methods must improve comprehension without inventing facts; media outputs must actually play; model resource savings need a same-model measured baseline. Optional adapters can be disabled/reverted without changing stored source facts, Permission, Timeline or Artifact identities. This update installs nothing and starts no service, model, paid resource or other window. Research/method adoption is OBSERVED; new source bindings, runtime and user outcomes remain NOT_VERIFIED.

## 2026-10-18 source-origin adoption

Origin: `Zachary-1012/global-growth-intelligence`, commit `e6cde984480cff3176eb39b038c7c0a66e1e2124` (72 files). No LICENSE or NOTICE was present in that source snapshot. The owner explicitly authorized sanitized owned-source/document publication into LUMENIS. Adapted original owned/authorized work falls within the existing LICENSING.md grant; this is not a fabricated upstream third-party license.

The 7 market, 12 platform, 14 policy and 3 scenario references retain original source URLs/dates and historical claims. Third-party reuse rights are UNKNOWN / NOT_DECLARED_IN_SOURCE, not Apache-2.0 by inference. Acquisition, publication and training permission are separate. Preserve effective/observation/capture dates, jurisdiction, uncertainty and provenance; no current legal/market fact or legal clearance is established. Full source file/rights mappings: `00-GOVERNANCE/LUMENIS-SOURCE-ADOPTION-V1.json`. Original example configuration, old provider defaults and passwords are not production configuration. No source runtime DB, credentials or standalone dependency stack is imported by this adoption record.


## 2026-10-26 Flutter work-surface adaptations

The existing Flutter owner consumes pinned packages through `app/pubspec.yaml` and `app/pubspec.lock`. `lumenis_workspace_frame.dart` uses flutter_animate state-driven reversible feedback with reduced-motion equivalence; `lumenis_botanical.dart` uses pixel_snap physical-pixel quantization for original botanical geometry at fractional display scales. No upstream example layout, artwork, provider, analytics or product data is imported. flutter_shaders is flutter_animate's transitive BSD dependency; no remote shader or new GPU requirement is introduced. Full product capability and user acceptance remain separate from this implementation. Rollback removes these package bindings while retaining route, focus, draft and permission contracts.

| Component | Pinned release archive SHA256 | Notice |
|---|---|---|
| flutter_animate 4.5.2 | `7befe2d3252728afb77aecaaea1dec88a89d35b9b1d2eea6d04479e8af9117b5` | [flutter_animate original notice](../vendor/lumenis-reuse-notices/flutter_animate-4.5.2-LICENSE.txt) |
| pixel_snap 0.1.5 | `677410ea37b07cd37ecb6d5e6c0d8d7615a7cf3bd92ba406fd1ac57e937d1fb0` | [pixel_snap original notice](../vendor/lumenis-reuse-notices/pixel_snap-0.1.5-LICENSE.txt) |
| flutter_shaders 0.1.5 | `16cd456daf2fd6ed7ac0c5168716c5e2fe18f91d82631b775f1af9100fb3f586` | [flutter_shaders original notice](../vendor/lumenis-reuse-notices/flutter_shaders-0.1.5-LICENSE.txt) |

## 2026-10-26 Memory lexical retrieval code adaptation


| Component / fixed source | Existing owner / changes | License / boundary |
|---|---|---|
| [rank_bm25](https://github.com/dorianbrown/rank_bm25/tree/47aa3ddf8dc1ebeb7ef4e65f2b4536af44594099) `rank_bm25.py` | C2 Memory `agent_memory/retrieval.py`: term frequencies and document-length normalization adapted into sparse postings, positive IDF and bounded passage selection, preserving authorization/revalidation | Apache-2.0; original license SHA256 `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4` retained under `vendor/lumenis-reuse-notices/`. No new service, weight download, model permission or neural-search completion claim. Rollback changes ranking implementation without changing original documents or scopes. |
