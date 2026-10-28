"""Choose Experience coverage from a verified comparison; never swallow diff errors."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

_RELEVANT = re.compile(r'^(app/lib/|app/pubspec[.]yaml$|website/|00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION[.]md$|00-GOVERNANCE/LUMENIS-MULTI-SURFACE-DECISION-CURRENT[.]md$)')
_RETIREMENT_ROOTS = ('app/lib', 'app/assets/wallpapers', 'website/src')
_GIT_OBJECT_ID = re.compile(r'^[0-9a-f]{40}$')


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



def _git_output(root: Path, arguments: list[str]) -> bytes:
    try:
        return subprocess.run(
            ['git', *arguments], cwd=root, check=True, capture_output=True, timeout=30,
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError('Could not verify approved frontend retirement in Git') from exc


def _retirement_git_snapshot(root: Path, base_main: str, retirement_commit: str):
    tree = _git_output(root, [
        'ls-tree', '-r', '-z', base_main, '--', *_RETIREMENT_ROOTS,
    ])
    baseline_blobs = {}
    for entry in tree.split(b'\0'):
        if not entry:
            continue
        try:
            metadata, raw_path = entry.split(b'\t', 1)
            _mode, object_type, object_id = metadata.decode('ascii').split()
        except (ValueError, UnicodeError) as exc:
            raise ValueError('Could not parse approved frontend baseline tree') from exc
        if object_type == 'blob':
            baseline_blobs[os.fsdecode(raw_path)] = object_id

    deleted = _git_output(root, [
        'diff', '--name-only', '--no-renames', '--diff-filter=D', '-z',
        base_main, retirement_commit, '--', *_RETIREMENT_ROOTS,
    ])
    deleted_paths = {os.fsdecode(path) for path in deleted.split(b'\0') if path}
    return baseline_blobs, deleted_paths


def _manifest_sha256(value) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(canonical).hexdigest()


def frontend_state(root: Path) -> str:
    machine = json.loads((root / '00-GOVERNANCE/LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json').read_text('utf-8'))
    policy = machine['verification_policy'].get('frontend_source_retirement')
    if policy is None or policy.get('state') == 'ACTIVE':
        return 'ACTIVE'
    if policy.get('state') != 'REMOVED_PENDING_REBUILD':
        raise ValueError('Unknown frontend implementation state')
    if (policy.get('product_scope_unchanged') is not True
            or policy.get('product_release_allowed') is not False
            or policy.get('active_build_required_before_release') is not True):
        raise ValueError('Retirement cannot reduce product scope or permit release')
    receipt_path = policy['approval_receipt']
    if not receipt_path.startswith('00-GOVERNANCE/evidence/approvals/') or '..' in Path(receipt_path).parts:
        raise ValueError('Invalid retirement approval path')
    receipt = json.loads((root / receipt_path).read_text('utf-8'))
    receipt_scope = receipt.get('scope_manifest')
    if not isinstance(receipt_scope, dict):
        raise TypeError('Retirement approval has no scope manifest')
    if (receipt.get('status') != 'APPROVED' or receipt.get('approved_by') != 'Product Owner'
            or receipt.get('approval_source_type') != 'direct_product_owner_instruction'
            or receipt_scope.get('source_retirement_merge_allowed') is not True
            or receipt_scope.get('product_release_without_complete_frontend') is not False):
        raise ValueError('Retirement requires explicit PO source-only merge approval')
    manifest_path = policy['manifest']
    if not manifest_path.startswith('00-GOVERNANCE/evidence/') or '..' in Path(manifest_path).parts:
        raise ValueError('Invalid retirement manifest path')
    manifest = json.loads((root / manifest_path).read_text('utf-8'))
    record = manifest.get(policy.get('manifest_key'))
    if not isinstance(record, dict):
        raise TypeError('Approved retirement manifest record is missing')
    rows = record.get('deleted_from_main_baseline')
    if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError('Retirement manifest is empty or invalid')
    digest = _manifest_sha256(rows)
    if (digest != policy.get('removed_manifest_sha256')
            or digest != receipt_scope.get('source_retirement_manifest_sha256')):
        raise ValueError('Retirement manifest is not bound to the approval receipt')
    absent_paths = record.get('already_absent_from_main')
    if (not isinstance(absent_paths, list) or not absent_paths
            or not all(isinstance(path, str) for path in absent_paths)):
        raise ValueError('Previously absent frontend manifest is empty or invalid')
    absent_digest = _manifest_sha256(absent_paths)
    if (absent_digest != policy.get('already_absent_manifest_sha256')
            or absent_digest != receipt_scope.get('source_retirement_already_absent_manifest_sha256')):
        raise ValueError('Previously absent frontend manifest is not bound to the approval receipt')
    if len(set(absent_paths)) != len(absent_paths):
        raise ValueError('Previously absent frontend manifest is duplicated')
    for name in absent_paths:
        if (not name.startswith(('app/lib/', 'app/assets/wallpapers/', 'website/src/'))
                or '..' in Path(name).parts):
            raise ValueError('Previously absent frontend path extends outside approved presentation')
    base_main = record.get('base_main')
    retirement_commit = receipt_scope.get('source_retirement_commit')
    if (not isinstance(base_main, str) or not _GIT_OBJECT_ID.fullmatch(base_main)
            or receipt_scope.get('source_retirement_base_main') != base_main
            or not isinstance(retirement_commit, str)
            or not _GIT_OBJECT_ID.fullmatch(retirement_commit)):
        raise ValueError('Retirement baseline or source commit is not bound to the approval receipt')
    if not all(isinstance(row.get('path'), str) for row in rows):
        raise ValueError('Retirement manifest contains an invalid path')
    if len({row['path'] for row in rows}) != len(rows):
        raise ValueError('Retirement manifest is empty or duplicated')
    expected_paths = set()
    old_blobs = set()
    for row in rows:
        name = row.get('path')
        main_blob = row.get('main_blob')
        if (not isinstance(name, str)
                or not name.startswith(('app/lib/', 'app/assets/wallpapers/', 'website/src/'))
                or '..' in Path(name).parts or not isinstance(main_blob, str)
                or not _GIT_OBJECT_ID.fullmatch(main_blob)):
            raise ValueError('Retirement extends outside approved presentation')
        if (root / name).exists():
            raise ValueError('Rejected presentation restored: ' + name)
        expected_paths.add(name)
        old_blobs.add(main_blob)

    baseline_blobs, deleted_paths = _retirement_git_snapshot(root, base_main, retirement_commit)
    if deleted_paths != expected_paths:
        raise ValueError('Pinned retirement deletions do not match the approved manifest')
    if any(baseline_blobs.get(row['path']) != row['main_blob'] for row in rows):
        raise ValueError('Retirement manifest does not match its base_main blobs')
    if any(name in baseline_blobs for name in absent_paths):
        raise ValueError('Previously absent frontend manifest path exists in base_main')

    current_deletions = _git_output(root, [
        'diff', '--name-only', '--no-renames', '--diff-filter=D', '-z', base_main,
        '--', *_RETIREMENT_ROOTS,
    ])
    current_deleted_paths = {os.fsdecode(path) for path in current_deletions.split(b'\0') if path}
    if current_deleted_paths != expected_paths:
        raise ValueError('Current frontend deletions do not match the approved manifest')
    restored_absent_paths = [
        name for name in absent_paths if (root / name).exists() or (root / name).is_symlink()
    ]
    if restored_absent_paths:
        raise ValueError('Previously absent frontend presentation restored: ' + restored_absent_paths[0])
    for folder in ('app/lib', 'website/src', 'app/assets/wallpapers'):
        for path in (root / folder).rglob('*'):
            if not path.is_file() or path.suffix not in {'.dart', '.astro', '.css', '.js', '.jpg'}:
                continue
            content = path.read_bytes()
            if path.suffix != '.jpg':
                content = content.replace(b'\r\n', b'\n')
            blob = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
            if blob in old_blobs:
                raise ValueError('Rejected presentation copied to: ' + str(path.relative_to(root)))
    for folder in ('app/build/web', 'app/build/windows', 'website/dist'):
        if (root / folder).exists():
            raise ValueError('Retired frontend has active build output: ' + folder)
    return 'REMOVED_PENDING_REBUILD'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='')
    parser.add_argument('--head', default='HEAD')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--source-state', action='store_true')
    parser.add_argument('--require-product', action='store_true')
    parser.add_argument('--github-output')
    args = parser.parse_args()
    if args.source_state or args.require_product:
        try:
            state = frontend_state(Path(__file__).resolve().parents[2])
            if args.require_product and state != 'ACTIVE':
                raise ValueError('Product release blocked: frontend replacement is incomplete')
            print(json.dumps({'source_state': state, 'frontend_build': 'REQUIRED' if state == 'ACTIVE' else 'NOT_AVAILABLE', 'product_accepted': False}))
            if args.github_output:
                with open(args.github_output, 'a', encoding='utf-8') as output:
                    output.write('state=' + state + '\n')
            return 0
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
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
