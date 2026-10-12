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

The direct Flutter dependency `crypto` 3.0.7 retains the Dart project authors'
BSD-3-Clause [original versioned notice](https://github.com/dart-lang/core/blob/crypto-v3.0.7/pkgs/crypto/LICENSE).
Its installed notice was read on 2026-10-11 for the SavedWork download-byte
integrity repair. Preserve that complete copyright, conditions and disclaimer
with redistributed source and binary packages. Verification of the generated
application's actual license bundle remains part of packaging acceptance.

Model weights, training data and optional media tools such as FFmpeg retain their
separate terms. No such material is added or newly distributed by this change.
VERIFY_BEFORE_RELEASE / NOT VERIFIED entries in the register remain unresolved;
this index neither silently passes them nor relicenses them.

## python-pptx 1.0.2

The existing Shared ReportExporter uses this exact package for editable PPTX
output. Its wheel SHA-256 is `160838e0b8565a8b1f67947675886e9fea18aa5e795db7ae531606d68e785cba`.
The full original wheel notice follows. Preserve it with redistributed copies.
Existing Pillow, lxml, XlsxWriter and typing-extensions retain their own notices;
the final packaged graph and license bundle remain release checks.

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
