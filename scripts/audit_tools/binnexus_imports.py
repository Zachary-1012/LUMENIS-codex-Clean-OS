"""Pure extraction from BinNexus. No filesystem or process access.

Upstream: Dvurechensky/BinNexus
Commit: 269444ef4433cc582a57f7fa6854c2448ad5ba6b
Source: app/binnexus/analysis/static/imports.py, lines 16-24.
Copyright (c) 2020-2026 Dvurechensky. MIT; see vendor/lumenis-reuse-notices/Dvurechensky-MIT.txt.
Only the import statement and provenance header are supplied by this package.
The regular expression and parse_imports function below are unchanged.
"""
import re

dll_pattern = re.compile(r"^\s+([A-Za-z0-9_\-\.]+\.dll)", re.IGNORECASE)

def parse_imports(output):
    imports = set()
    for line in output.splitlines():
        match = dll_pattern.match(line)
        if match:
            imports.add(match.group(1).lower())
    return imports
