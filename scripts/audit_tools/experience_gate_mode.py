"""Choose Experience coverage from a verified comparison; never swallow diff errors."""
from __future__ import annotations
import argparse
import re
import subprocess
import sys

_RELEVANT = re.compile(r'^(app/lib/|app/pubspec[.]yaml$|website/|00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION[.]md$|00-GOVERNANCE/LUMENIS-MULTI-SURFACE-DECISION-CURRENT[.]md$)')


def select_mode(base: str, head: str = 'HEAD', *, cwd=None):
    # Dispatch and a branch-creation event have no trustworthy comparison.
    # They run strict, never an invented empty diff / baseline.
    if not base or set(base) == {'0'}:
        return '--strict'
    for ref in (base, head):
        subprocess.run(['git', 'rev-parse', '--verify', f'{ref}^{{commit}}'],
                       cwd=cwd, check=True, capture_output=True, timeout=30)
    result = subprocess.run(['git', 'diff', '--name-only', '--no-renames', '-z', base, head, '--'],
                            cwd=cwd, check=True, capture_output=True, timeout=30)
    paths = result.stdout.decode('utf-8', errors='strict').split('\0')
    return '--strict' if any(_RELEVANT.search(p) for p in paths if p) else '--baseline'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='')
    parser.add_argument('--head', default='HEAD')
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    try:
        mode = select_mode(args.base, args.head)
    except (subprocess.SubprocessError, OSError, UnicodeError):
        print('Experience comparison unavailable; blocking, not baseline.', file=sys.stderr)
        return 1
    print(f'Experience gate selected {mode}; unknown base requires strict.')
    if args.run:
        return subprocess.run([sys.executable, 'scripts/audit_tools/verify_experience_anti_template.py', mode], check=False).returncode
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
