#!/usr/bin/env python3
"""CSS 结构平衡检查：花括号、圆括号、注释、引号配对。

背景：Step5j 发现 zbip-panels.css 行73 `var(--x,#HEX` 漏写右括号，
浏览器把后续整段 CSS 当未闭合函数参数吞掉（静态肉眼/只看花括号难以发现）。
本脚本对 static/css 下所有 .css 做严格扫描，任一不平衡即退出码 1。
"""
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CSS_DIR = ROOT / "static" / "css"


def check(text: str):
    """返回 (paren_bal, brace_bal, in_comment, quote_open, first_error)。"""
    i, n = 0, len(text)
    paren = brace = 0
    in_comment = False
    quote = None
    err = None
    line = 1
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1
        if in_comment:
            if text[i:i + 2] == "*/":
                in_comment = False
                i += 2
                continue
            i += 1
            continue
        if quote:
            if c == quote:
                quote = None
            i += 1
            continue
        if text[i:i + 2] == "/*":
            in_comment = True
            i += 2
            continue
        if c in "\"'":
            quote = c
        elif c == "(":
            paren += 1
        elif c == ")":
            paren -= 1
            if paren < 0 and err is None:
                err = f"line {line}: extra ')'"
        elif c == "{":
            brace += 1
        elif c == "}":
            brace -= 1
            if brace < 0 and err is None:
                err = f"line {line}: extra '}}'"
        i += 1
    return paren, brace, in_comment, quote, err


def main():
    failed = 0
    for f in sorted(CSS_DIR.glob("*.css")):
        paren, brace, in_c, q, err = check(f.read_text(encoding="utf-8"))
        ok = (paren == 0 and brace == 0 and not in_c and q is None and err is None)
        if not ok:
            failed += 1
            print(f"[FAIL] {f.name}: paren={paren} brace={brace} in_comment={in_c} quote={q!r} {err or ''}")
        else:
            print(f"[ok]   {f.name}")
    if failed:
        print(f"\n{failed} CSS file(s) unbalanced.")
        return 1
    print("\nAll CSS structurally balanced.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
