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
