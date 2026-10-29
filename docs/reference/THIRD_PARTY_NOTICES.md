# Third-party notices

The root Apache-2.0 license covers original LUMENIS software, not ownership of
third-party materials. Retain the complete original notices with redistributed
components. This index supplements, and does not replace, the canonical
[component register](00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md).

## Notices already present in the source tree

| Material | Original notice to preserve | License evidenced by that notice |
| --- | --- | --- |
| Vendored colorama 0.4.6 | [LICENSE.txt](vendor/colorama-0.4.6.dist-info/licenses/LICENSE.txt) | BSD-3-Clause; copyright Jonathan Hartley |
| Vendored qrcode 8.2 | [LICENSE](vendor/qrcode-8.2.dist-info/LICENSE) | BSD-3-Clause; retain the included pyqrnative / Kazuhiko Arase MIT attribution as well |
| Noto Sans SC | [NotoSansSC-OFL.txt](app/assets/fonts/NotoSansSC-OFL.txt) | SIL Open Font License 1.1 |
| Noto Sans KR | [NotoSansKR-OFL.txt](app/assets/fonts/NotoSansKR-OFL.txt) | SIL Open Font License 1.1 |
| Noto Color Emoji | [NotoColorEmoji-OFL.txt](app/assets/fonts/NotoColorEmoji-OFL.txt) | SIL Open Font License 1.1 |

These entries identify notices inspected in the pinned source tree for the
2026-10-10 licensing change; they are not a complete software bill of materials
or a blanket redistribution clearance. No upstream notice or font file is changed.

## Dependencies and optional external tools

- SYSTEM Collector public media embeds the Unlicense `yt-dlp==2026.10.21`
  Python wheel, not its bundled executable. Preserve its complete
  [original license](vendor/lumenis-reuse-notices/yt-dlp-2026.10.21-Unlicense.txt).
- C1 public platform parsers adapt OpenCLI commit
  `aeaff2b796efabb7fd46654112418ab61fcae917`, copyright 2025 jackwener,
  Apache-2.0. Preserve the complete
  [upstream license](vendor/lumenis-reuse-notices/OpenCLI-aeaff2b7-Apache-2.0.txt)
  and the source/pin/modification notices in adapted files. The selected upstream
  paths carry no separate NOTICE. Auth/publish/session runtime is not adopted.
- C1 Naver/Daum body/iframe parsing adapts `adapters/naver_blog/scrape.py` from
  sipher commit `2c3470f973d47842a13b70c552872a6ceabd7a9b`, copyright 2026
  stepbyjason-lab, MIT. Preserve the complete
  [original notice](vendor/lumenis-reuse-notices/sipher-2c3470f9-MIT.txt).
  Its CLI, setup, model, OCR and session paths are not adopted.

Python, npm, Flutter and native dependencies remain under their own exact-version
licenses. Record the actual shipped dependency graph, copied source and binary
builds before distributing a package, together with required license, attribution,
corresponding-source and other applicable obligations. Do not treat installation,
an import statement, or a historical register entry as redistribution approval.

Model weights, training data and optional media tools such as FFmpeg retain their
separate terms. No such material is added or newly distributed by this change.
VERIFY_BEFORE_RELEASE / NOT VERIFIED entries in the register remain unresolved;
this index neither silently passes them nor relicenses them.


## 2026-10-13 bounded response-shape and static-import reuse

- `lumenis/system/collector/adapters/response_shape.py`: original Python adaptation
  of shape/key/pagination observation ideas in Dvurechensky/Browser.Reverse.Engineering.Toolkit,
  commit `ecbe61af5004f6efa493749a623fbd98ab307a37`, `SiteSnapshotter/injector.js`.
  No injector, browser launcher, storage/session sampler or acquisition code copied.
  This integration adds bounded invocation-local observations and typed validation;
  it does not authorize collection or create Evidence/Canonical facts.
- `scripts/audit_tools/binnexus_imports.py`: verbatim `dll_pattern` and `parse_imports`
  from Dvurechensky/BinNexus commit `269444ef4433cc582a57f7fa6854c2448ad5ba6b`,
  `app/binnexus/analysis/static/imports.py`, lines 16-24; provenance/header added.
  `dll_imports.py` is the separately authored single-file, timeout-bounded wrapper.
  No DLL loading, target execution, recursive scan or new runtime dependency.

Retain the complete [upstream MIT notice](vendor/lumenis-reuse-notices/Dvurechensky-MIT.txt)
and [delivery MIT notice](vendor/lumenis-reuse-notices/Delivery-MIT.txt) with copies.
The root Apache-2.0 license is unchanged. Build/static observations do not prove
runtime dependency resolution, current-main build identity or product acceptance.

## 2026-10-18 source-origin adoption

Origin: `Zachary-1012/global-growth-intelligence`, commit `e6cde984480cff3176eb39b038c7c0a66e1e2124` (72 files). No LICENSE or NOTICE was present in that source snapshot. The owner explicitly authorized sanitized owned-source/document publication into LUMENIS. Adapted original owned/authorized work falls within the existing LICENSING.md grant; this is not a fabricated upstream third-party license.

The 7 market, 12 platform, 14 policy and 3 scenario references retain original source URLs/dates and historical claims. Third-party reuse rights are UNKNOWN / NOT_DECLARED_IN_SOURCE, not Apache-2.0 by inference. Acquisition, publication and training permission are separate. Preserve effective/observation/capture dates, jurisdiction, uncertainty and provenance; no current legal/market fact or legal clearance is established. Full source file/rights mappings: `00-GOVERNANCE/LUMENIS-SOURCE-ADOPTION-V1.json`. Original example configuration, old provider defaults and passwords are not production configuration. No source runtime DB, credentials or standalone dependency stack is imported by this adoption record.

## python-pptx 1.0.2

Editable PPTX export uses the existing Shared ReportExporter. The installed
1.0.2 distribution retains the following original MIT notice. Preserve it with
redistributed copies; Pillow, lxml, XlsxWriter and typing-extensions retain
their own notices. Packaged dependency and license bundles remain release checks.

```text
The MIT License (MIT)
Copyright (c) 2013 Steve Canny, https://github.com/scanny

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```


## Flutter work-surface packages

- flutter_animate 4.5.2: [complete upstream license](vendor/lumenis-reuse-notices/flutter_animate-4.5.2-LICENSE.txt); package archive SHA256 `7befe2d3252728afb77aecaaea1dec88a89d35b9b1d2eea6d04479e8af9117b5`.
- pixel_snap 0.1.5: [complete upstream license](vendor/lumenis-reuse-notices/pixel_snap-0.1.5-LICENSE.txt); package archive SHA256 `677410ea37b07cd37ecb6d5e6c0d8d7615a7cf3bd92ba406fd1ac57e937d1fb0`.
- flutter_shaders 0.1.5: [complete upstream license](vendor/lumenis-reuse-notices/flutter_shaders-0.1.5-LICENSE.txt); package archive SHA256 `16cd456daf2fd6ed7ac0c5168716c5e2fe18f91d82631b775f1af9100fb3f586`.

## 2026-10-26 authorized lexical retrieval adaptation


`agent_memory/retrieval.py` adapts the BM25Okapi term-frequency/length normalization from `dorianbrown/rank_bm25`, pinned commit `47aa3ddf8dc1ebeb7ef4e65f2b4536af44594099`, `rank_bm25.py`. Original copyright Dorian Brown; Apache-2.0. The adapted implementation retains workspace/actor filtering and revalidation, adds sparse postings and bounded long-document passage selection, and uses non-negative IDF instead of upstream negative-IDF flooring. This lexical component is not a neural embedding or cross-encoder reranker. Retain the [complete upstream license](vendor/lumenis-reuse-notices/rank_bm25-47aa3ddf-Apache-2.0.txt).
