#!/usr/bin/env python3
"""P0 Runtime Audit - Before Snapshot
Scans templates for:
1. P0-A: URL embedded credentials (user:pass@host pattern in templates/JS)
2. P0-B: Inline JS syntax errors (extract <script> blocks, run node --check)
3. P0-C: AuthRecoveryModal duplicate declarations
"""
import os
import re
import subprocess
import tempfile
import json
from pathlib import Path

ROOT = Path(r"D:\Taikoo-monitor-new")
TEMPLATES = ROOT / "templates"
STATIC_JS = ROOT / "static" / "js"

results = {
    "p0a_url_credentials": [],
    "p0b_js_syntax_errors": [],
    "p0c_auth_recovery_modal": {"definitions": [], "includes": [], "dynamic_loads": []},
}

# ============================================================
# P0-A: URL embedded credentials in templates and static JS
# ============================================================
print("=" * 60)
print("P0-A: Scanning for URL embedded credentials")
print("=" * 60)

# Pattern: scheme://user:pass@host  (but exclude data/ captured pages, node_modules, .git)
cred_pattern = re.compile(r'[a-zA-Z][a-zA-Z0-9+.-]*://[^\s/"\'<>]+:[^\s/@"\'<>]+@[^\s/"\'<>]+')
exclude_dirs = {'.git', 'node_modules', 'data', '__pycache__', '.venv', 'venv', '99-ARCHIVE', 'archive', 'backups', 'logs', 'intelligence_library'}

scan_dirs = [TEMPLATES, STATIC_JS]
for scan_dir in scan_dirs:
    for fpath in scan_dir.rglob("*"):
        if not fpath.is_file():
            continue
        if fpath.suffix.lower() not in ('.html', '.js', '.htm'):
            continue
        try:
            content = fpath.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        for m in cred_pattern.finditer(content):
            rel = fpath.relative_to(ROOT)
            line_no = content[:m.start()].count('\n') + 1
            entry = {"file": str(rel), "line": line_no, "match": m.group()[:120]}
            results["p0a_url_credentials"].append(entry)
            print(f"  [CRED] {rel}:{line_no} -> {m.group()[:80]}")

# Also check for auth_header being used in URL construction
print("\n  Checking auth_header / __Z_AUTH usage in URL strings...")
url_auth_pattern = re.compile(r'(auth_header|__Z_AUTH|AUTH_USER|AUTH_PASSWORD).*(\+|concat|template).*(url|href|src|fetch)', re.IGNORECASE)
for scan_dir in scan_dirs:
    for fpath in scan_dir.rglob("*"):
        if not fpath.is_file() or fpath.suffix.lower() not in ('.html', '.js'):
            continue
        try:
            content = fpath.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        for i, line in enumerate(content.split('\n'), 1):
            if url_auth_pattern.search(line):
                rel = fpath.relative_to(ROOT)
                print(f"  [SUSPECT] {rel}:{i}: {line.strip()[:120]}")

print(f"\n  P0-A total credential URL matches: {len(results['p0a_url_credentials'])}")

# ============================================================
# P0-B: Inline JS syntax check in all templates
# ============================================================
print("\n" + "=" * 60)
print("P0-B: Scanning inline <script> blocks for syntax errors")
print("=" * 60)

script_pattern = re.compile(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE)
template_files = list(TEMPLATES.rglob("*.html"))
print(f"  Scanning {len(template_files)} template files...")

node_path = "node"
syntax_errors = []

for fpath in sorted(template_files):
    try:
        content = fpath.read_text(encoding='utf-8', errors='replace')
    except Exception:
        continue
    rel = fpath.relative_to(ROOT)
    # Find all inline script blocks (no src attribute)
    for idx, m in enumerate(script_pattern.finditer(content)):
        js_code = m.group(1).strip()
        if not js_code:
            continue
        # Skip JSON-LD and non-JS types
        start_tag = content[m.start():m.start()+200]
        if 'application/json' in start_tag.lower() or 'ld+json' in start_tag.lower():
            continue
        # Write to temp file and check with node
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8') as tf:
            tf.write(js_code)
            tmp_path = tf.name
        try:
            proc = subprocess.run(
                [node_path, '--check', tmp_path],
                capture_output=True, text=True, timeout=15
            )
            if proc.returncode != 0:
                line_no = content[:m.start()].count('\n') + 1
                err_msg = proc.stderr.strip()[:300]
                entry = {
                    "file": str(rel),
                    "script_block": idx,
                    "line": line_no,
                    "error": err_msg
                }
                syntax_errors.append(entry)
                print(f"  [SYNTAX ERROR] {rel} block#{idx} (line ~{line_no}):")
                print(f"    {err_msg.split(chr(10))[0][:150]}")
        except subprocess.TimeoutExpired:
            print(f"  [TIMEOUT] {rel} block#{idx}")
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

results["p0b_js_syntax_errors"] = syntax_errors
print(f"\n  P0-B total syntax errors: {len(syntax_errors)}")

# ============================================================
# P0-C: AuthRecoveryModal duplicate declaration
# ============================================================
print("\n" + "=" * 60)
print("P0-C: AuthRecoveryModal declaration scan")
print("=" * 60)

# 1. HTML element definitions
modal_id_pattern = re.compile(r'id=["\']auth-recovery-modal["\']')
# 2. JS const/var/let declarations
js_decl_pattern = re.compile(r'(const|var|let|function)\s+AuthRecoveryModal')
# 3. includes
include_pattern = re.compile(r'{%\s*include\s+["\']auth_recovery_modal\.html["\']')
# 4. dynamic loads (fetch / load / import)
dynamic_pattern = re.compile(r'(fetch|load|import|getScript)\s*[\(\s].*auth.recovery', re.IGNORECASE)

all_html = list(TEMPLATES.rglob("*.html"))
all_js = list(STATIC_JS.rglob("*.js"))

for fpath in sorted(all_html + all_js):
    try:
        content = fpath.read_text(encoding='utf-8', errors='replace')
    except Exception:
        continue
    rel = fpath.relative_to(ROOT)
    
    for m in modal_id_pattern.finditer(content):
        line_no = content[:m.start()].count('\n') + 1
        results["p0c_auth_recovery_modal"]["definitions"].append({"file": str(rel), "line": line_no, "type": "html_element"})
        print(f"  [HTML DEF] {rel}:{line_no}")
    
    for m in js_decl_pattern.finditer(content):
        line_no = content[:m.start()].count('\n') + 1
        results["p0c_auth_recovery_modal"]["definitions"].append({"file": str(rel), "line": line_no, "type": "js_declaration"})
        print(f"  [JS DEF]   {rel}:{line_no}: {m.group()[:60]}")
    
    for m in include_pattern.finditer(content):
        line_no = content[:m.start()].count('\n') + 1
        results["p0c_auth_recovery_modal"]["includes"].append({"file": str(rel), "line": line_no})
        print(f"  [INCLUDE]  {rel}:{line_no}")
    
    for m in dynamic_pattern.finditer(content):
        line_no = content[:m.start()].count('\n') + 1
        results["p0c_auth_recovery_modal"]["dynamic_loads"].append({"file": str(rel), "line": line_no})
        print(f"  [DYNAMIC]  {rel}:{line_no}: {m.group()[:80]}")

# Count unique definitions
def_count = len(results["p0c_auth_recovery_modal"]["definitions"])
inc_count = len(results["p0c_auth_recovery_modal"]["includes"])
print(f"\n  P0-C: HTML/JS definitions={def_count}, includes={inc_count}, dynamic_loads={len(results['p0c_auth_recovery_modal']['dynamic_loads'])}")

# ============================================================
# Save results
# ============================================================
out_path = ROOT / "08-AUDIT" / "before_snapshot.json"
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\nResults saved to {out_path}")
