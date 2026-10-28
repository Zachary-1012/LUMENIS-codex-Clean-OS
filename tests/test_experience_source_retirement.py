import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from scripts.audit_tools.experience_gate_mode import frontend_state

RETIREMENT_ROOTS = ('app/lib', 'app/assets/wallpapers', 'website/src')
RETIRED_FILES = {
    'app/lib/retired.dart': b'retired source\n',
    'app/assets/wallpapers/retired.jpg': b'retired wallpaper bytes',
    'website/src/retired.css': b'retired presentation\n',
}
CURRENT_FILE = 'app/lib/current-before-retirement.dart'
UNLISTED_FILE = 'app/lib/unlisted-retirement.dart'
BACKEND_FILE = 'lumenis/shared/retained-before-retirement.py'
ALREADY_ABSENT_FILES = [
    'app/lib/core/lumenis_botanical.dart',
    'app/lib/core/lumenis_context_menu.dart',
    'app/lib/core/lumenis_split_handle.dart',
    'app/lib/core/lumenis_work_object.dart',
    'app/lib/features/ai01/ai01_source_picker.dart',
    'app/lib/features/cth/cth10/business_domain_plan_editor.dart',
    'app/lib/features/cth/cth10/business_work_panel.dart',
    'app/lib/features/shared/sh01/creation_brief_dialog.dart',
    'app/lib/features/shared/sh02/office_property_editor.dart',
    'app/lib/features/system/sys02/collected_comments_panel.dart',
    'app/lib/features/system/sys02/collector_request_panel.dart',
    'app/lib/shell/lumenis_workspace_frame.dart',
    'website/src/components/PixelPlant.astro',
    'website/src/components/PublicContent.astro',
    'website/src/components/PublicNavigation.astro',
    'website/src/pages/[...page].astro',
]
MACHINE_PATH = '00-GOVERNANCE/LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json'
RECEIPT_PATH = '00-GOVERNANCE/evidence/approvals/PO-20261028-SOURCE-RETIREMENT.json'
MANIFEST_PATH = '00-GOVERNANCE/evidence/round-15/workspace-continuity-20261024.json'
MANIFEST_KEY = 'rejected_frontend_retirement_20261028'


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ['git', *arguments], cwd=root, check=True, capture_output=True, text=True,
        timeout=30,
    )
    return result.stdout.strip()


def _write_json(root: Path, relative_path: str, value: dict) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def _git_blobs(root: Path, commit: str) -> dict[str, str]:
    output = subprocess.run(
        ['git', 'ls-tree', '-r', '-z', commit, '--', *RETIREMENT_ROOTS],
        cwd=root, check=True, capture_output=True, timeout=30,
    ).stdout
    blobs = {}
    for entry in output.split(b'\0'):
        if entry:
            metadata, raw_path = entry.split(b'\t', 1)
            _mode, object_type, object_id = metadata.decode('ascii').split()
            if object_type == 'blob':
                blobs[raw_path.decode('utf-8')] = object_id
    return blobs


def _build_retirement(
    root: Path,
    *,
    unlisted_in_retirement: bool = False,
    later_protected_deletion: bool = False,
) -> dict:
    root.mkdir()
    _git(root, 'init', '--quiet')
    _git(root, 'config', 'user.name', 'Retirement Test')
    _git(root, 'config', 'user.email', 'retirement-test@example.invalid')
    _git(root, 'config', 'core.autocrlf', 'false')

    baseline_files = dict(RETIRED_FILES)
    baseline_files[CURRENT_FILE] = b'valid retained implementation\n'
    baseline_files[BACKEND_FILE] = b'backend retained implementation\n'
    if unlisted_in_retirement:
        baseline_files[UNLISTED_FILE] = b'unapproved removal\n'
    for relative_path, content in baseline_files.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    _git(root, 'add', '-A')
    _git(root, 'commit', '--quiet', '-m', 'baseline')
    base_main = _git(root, 'rev-parse', 'HEAD')
    baseline_blobs = _git_blobs(root, base_main)

    for relative_path in RETIRED_FILES:
        (root / relative_path).unlink()
    if unlisted_in_retirement:
        (root / UNLISTED_FILE).unlink()
    _git(root, 'add', '-A')
    _git(root, 'commit', '--quiet', '-m', 'approved retirement')
    retirement_commit = _git(root, 'rev-parse', 'HEAD')

    # A later change outside the protected source roots remains independent.
    (root / BACKEND_FILE).unlink()
    _git(root, 'add', '-A')
    _git(root, 'commit', '--quiet', '-m', 'later unrelated backend change')
    if later_protected_deletion:
        # Leave this deletion uncommitted to exercise HEAD plus working-tree
        # comparison against the approved base.
        (root / CURRENT_FILE).unlink()

    rows = [
        {
            'path': relative_path,
            'main_blob': baseline_blobs[relative_path],
            'disposition': 'REMOVE_REJECTED_PRESENTATION',
        }
        for relative_path in RETIRED_FILES
    ]
    manifest = {
        MANIFEST_KEY: {
            'base_main': base_main,
            'deleted_from_main_baseline': rows,
            'already_absent_from_main': ALREADY_ABSENT_FILES,
        },
    }
    digest = _manifest_digest(rows)
    absent_digest = _manifest_digest(ALREADY_ABSENT_FILES)
    machine = {
        'verification_policy': {
            'frontend_source_retirement': {
                'state': 'REMOVED_PENDING_REBUILD',
                'approval_receipt': RECEIPT_PATH,
                'manifest': MANIFEST_PATH,
                'manifest_key': MANIFEST_KEY,
                'product_scope_unchanged': True,
                'product_release_allowed': False,
                'active_build_required_before_release': True,
                'removed_manifest_sha256': digest,
                'already_absent_manifest_sha256': absent_digest,
            },
        },
    }
    receipt = {
        'status': 'APPROVED',
        'approved_by': 'Product Owner',
        'approval_source_type': 'direct_product_owner_instruction',
        'scope_manifest': {
            'source_retirement_merge_allowed': True,
            'source_retirement_manifest_sha256': digest,
            'source_retirement_already_absent_manifest_sha256': absent_digest,
            'source_retirement_base_main': base_main,
            'source_retirement_commit': retirement_commit,
            'product_release_without_complete_frontend': False,
        },
    }
    _write_json(root, MACHINE_PATH, machine)
    _write_json(root, RECEIPT_PATH, receipt)
    _write_json(root, MANIFEST_PATH, manifest)
    return {
        'root': root,
        'base_main': base_main,
        'retirement_commit': retirement_commit,
    }


def _manifest_digest(value: list) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(payload).hexdigest()


def _read_json(root: Path, relative_path: str) -> dict:
    return json.loads((root / relative_path).read_text(encoding='utf-8'))


def _sync_bindings(root: Path, *, receipt: bool = True) -> None:
    manifest = _read_json(root, MANIFEST_PATH)
    rows = manifest[MANIFEST_KEY]['deleted_from_main_baseline']
    digest = _manifest_digest(rows)
    machine = _read_json(root, MACHINE_PATH)
    machine['verification_policy']['frontend_source_retirement']['removed_manifest_sha256'] = digest
    _write_json(root, MACHINE_PATH, machine)
    if receipt:
        approval = _read_json(root, RECEIPT_PATH)
        approval['scope_manifest']['source_retirement_manifest_sha256'] = digest
        absent_digest = _manifest_digest(manifest[MANIFEST_KEY]['already_absent_from_main'])
        approval['scope_manifest']['source_retirement_already_absent_manifest_sha256'] = absent_digest
        _write_json(root, RECEIPT_PATH, approval)
    machine = _read_json(root, MACHINE_PATH)
    absent_digest = _manifest_digest(manifest[MANIFEST_KEY]['already_absent_from_main'])
    machine['verification_policy']['frontend_source_retirement'][
        'already_absent_manifest_sha256'
    ] = absent_digest
    _write_json(root, MACHINE_PATH, machine)


def test_approved_retirement_allows_unrelated_backend_deletion(tmp_path):
    fixture = _build_retirement(tmp_path / 'repo')

    assert frontend_state(fixture['root']) == 'REMOVED_PENDING_REBUILD'


def test_new_protected_working_tree_deletion_is_rejected(tmp_path):
    fixture = _build_retirement(tmp_path / 'repo', later_protected_deletion=True)

    with pytest.raises(ValueError, match='Current frontend deletions'):
        frontend_state(fixture['root'])


def test_unlisted_deletion_in_pinned_retirement_commit_is_rejected(tmp_path):
    fixture = _build_retirement(tmp_path / 'repo', unlisted_in_retirement=True)

    with pytest.raises(ValueError, match='Pinned retirement deletions'):
        frontend_state(fixture['root'])


def test_receipt_binds_manifest_digest_and_baseline(tmp_path):
    fixture = _build_retirement(tmp_path / 'repo')
    root = fixture['root']
    receipt = _read_json(root, RECEIPT_PATH)
    receipt['scope_manifest']['source_retirement_base_main'] = '0' * 40
    _write_json(root, RECEIPT_PATH, receipt)

    with pytest.raises(ValueError, match='not bound to the approval receipt'):
        frontend_state(root)


def test_manifest_edit_cannot_be_rebound_without_receipt_authority(tmp_path):
    fixture = _build_retirement(tmp_path / 'repo')
    root = fixture['root']
    manifest = _read_json(root, MANIFEST_PATH)
    manifest[MANIFEST_KEY]['deleted_from_main_baseline'][0]['disposition'] = 'OTHER'
    _write_json(root, MANIFEST_PATH, manifest)
    _sync_bindings(root, receipt=False)

    with pytest.raises(ValueError, match='not bound to the approval receipt'):
        frontend_state(root)


def test_previously_absent_paths_are_bound_and_must_remain_absent(tmp_path):
    fixture = _build_retirement(tmp_path / 'repo')
    root = fixture['root']
    assert frontend_state(root) == 'REMOVED_PENDING_REBUILD'

    restored = root / ALREADY_ABSENT_FILES[0]
    restored.parent.mkdir(parents=True, exist_ok=True)
    restored.write_bytes(b'restored rejected presentation\n')
    with pytest.raises(ValueError, match='Previously absent frontend presentation restored'):
        frontend_state(root)


def test_previously_absent_manifest_digest_requires_receipt_binding(tmp_path):
    fixture = _build_retirement(tmp_path / 'repo')
    root = fixture['root']
    manifest = _read_json(root, MANIFEST_PATH)
    manifest[MANIFEST_KEY]['already_absent_from_main'].pop()
    _write_json(root, MANIFEST_PATH, manifest)
    _sync_bindings(root, receipt=False)

    with pytest.raises(ValueError, match='Previously absent frontend manifest is not bound'):
        frontend_state(root)


def test_previously_absent_paths_must_be_absent_from_base_main(tmp_path):
    fixture = _build_retirement(tmp_path / 'repo')
    root = fixture['root']
    manifest = _read_json(root, MANIFEST_PATH)
    manifest[MANIFEST_KEY]['already_absent_from_main'].append(CURRENT_FILE)
    _write_json(root, MANIFEST_PATH, manifest)
    _sync_bindings(root)

    with pytest.raises(ValueError, match='exists in base_main'):
        frontend_state(root)


def test_rebound_manifest_must_match_baseline_blob(tmp_path):
    fixture = _build_retirement(tmp_path / 'repo')
    root = fixture['root']
    manifest = _read_json(root, MANIFEST_PATH)
    manifest[MANIFEST_KEY]['deleted_from_main_baseline'][0]['main_blob'] = '0' * 40
    _write_json(root, MANIFEST_PATH, manifest)
    _sync_bindings(root)

    with pytest.raises(ValueError, match='does not match its base_main blobs'):
        frontend_state(root)


def test_malformed_manifest_path_fails_closed(tmp_path):
    fixture = _build_retirement(tmp_path / 'repo')
    root = fixture['root']
    manifest = _read_json(root, MANIFEST_PATH)
    manifest[MANIFEST_KEY]['deleted_from_main_baseline'][0]['path'] = {'bad': 'path'}
    _write_json(root, MANIFEST_PATH, manifest)
    _sync_bindings(root)

    with pytest.raises(ValueError, match='invalid path'):
        frontend_state(root)


def test_rejected_presentation_cannot_be_restored_or_copied(tmp_path):
    fixture = _build_retirement(tmp_path / 'restored')
    root = fixture['root']
    restored = next(iter(RETIRED_FILES))
    (root / restored).write_bytes(RETIRED_FILES[restored])
    with pytest.raises(ValueError, match='restored'):
        frontend_state(root)

    fixture = _build_retirement(tmp_path / 'copied')
    root = fixture['root']
    copied = root / 'app/lib/copied-retirement.dart'
    copied.parent.mkdir(parents=True, exist_ok=True)
    copied.write_bytes(RETIRED_FILES['app/lib/retired.dart'])
    with pytest.raises(ValueError, match='copied to'):
        frontend_state(root)
