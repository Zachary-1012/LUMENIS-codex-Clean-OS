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
