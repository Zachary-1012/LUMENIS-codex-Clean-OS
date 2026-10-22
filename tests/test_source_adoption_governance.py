from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from scripts.audit_tools.verify_source_adoption import validate_local_adoption, RECORD
from scripts.audit_tools.verify_lumenis_ggi_contract import validate_contract

ROOT = Path(__file__).resolve().parents[1]
READ = Path.read_text


def test_current_exchange_and_local_attachment():
    validate_contract(ROOT / '00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json')
    validate_local_adoption(ROOT)


@pytest.mark.parametrize('field,value', [
    ('scope', 'CROSS_PRODUCT_WRITER'), ('source_commit', '0'*40),
    ('record_version', '2.0.0'), ('authority', 'SECOND-ARCHITECTURE.md'),
])
def test_reject_scope_version_or_source_drift(field, value):
    data = json.loads(READ(ROOT / RECORD))
    data[field] = value
    with patch.object(Path, 'read_text', lambda p, *a, **kw: json.dumps(data) if p == ROOT / RECORD else READ(p, *a, **kw)):
        with pytest.raises(AssertionError): validate_local_adoption(ROOT)


@pytest.mark.parametrize('section,key,value', [
    ('boundaries','cross_database_copy',True), ('boundaries','unrestricted_writer',True),
    ('boundaries','automatic_truth_promotion',True), ('boundaries','external_delivery_authorized',True),
    ('exchange_contract','modified',True), ('exchange_contract','external_repositories_modified',True),
    ('exchange_contract','version','1.0.0'), ('exchange_contract','fingerprint','0'*64),
    ('rights','third_party_reuse','APACHE-2.0'), ('rights','original_source_license_file','APACHE-2.0'),
    ('inventory','dimensions',8), ('inventory','capabilities',32),
    ('maps','files','../../outside.json'),
])
def test_reject_false_rights_boundary_parity_or_incomplete_counts(section, key, value):
    data = json.loads(READ(ROOT / RECORD)); data[section][key] = value
    with patch.object(Path, 'read_text', lambda p, *a, **kw: json.dumps(data) if p == ROOT / RECORD else READ(p, *a, **kw)):
        with pytest.raises(AssertionError): validate_local_adoption(ROOT)


@pytest.mark.parametrize('key', ['files', 'endpoints', 'capabilities', 'rights', 'seed_records'])
def test_reject_missing_inventory_row(key):
    data = json.loads(READ(ROOT / RECORD)); target = ROOT / data['maps'][key]
    rows = json.loads(READ(target)); rows.pop()
    with patch.object(Path, 'read_text', lambda p, *a, **kw: json.dumps(rows) if p == target else READ(p, *a, **kw)):
        with pytest.raises(AssertionError): validate_local_adoption(ROOT)


def test_existing_gate_callers_enforce_local_attachment():
    import ast
    for filename in ['verify_lumenis_ggi_contract.py', 'verify_codex_takeover_governance.py']:
        tree = ast.parse((ROOT / 'scripts/audit_tools' / filename).read_text())
        assert any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                   and n.func.id == 'validate_local_adoption' for n in ast.walk(tree))


@pytest.mark.parametrize('key', ['shared_production_database', 'cross_product_runtime_hard_dependency',
                                'copy_product_business_code', 'unrestricted_cross_product_writer',
                                'ai_or_research_may_overwrite_lumenis_production_truth'])
def test_adoption_cannot_flip_exchange_safety_flags(key, tmp_path):
    contract_path = ROOT / '00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json'
    data = json.loads(contract_path.read_text())
    data['truth_and_runtime_boundary'][key] = True
    path = tmp_path / 'contract.json'; path.write_text(json.dumps(data))
    with pytest.raises(AssertionError): validate_contract(path)


@pytest.mark.parametrize('key,field', [('endpoints','target_callable'), ('endpoints','target_http_contract'), ('capabilities','current_target_callable'), ('capabilities','remaining')])
def test_reject_generic_or_unmapped_functional_intent(key, field):
    data = json.loads(READ(ROOT / RECORD)); target = ROOT / data['maps'][key]
    rows = json.loads(READ(target)); rows[0].pop(field)
    with patch.object(Path, 'read_text', lambda p, *a, **kw: json.dumps(rows) if p == target else READ(p, *a, **kw)):
        with pytest.raises(AssertionError): validate_local_adoption(ROOT)


@pytest.mark.parametrize('ref,owners', [
    ('original-G:G160', ['C3/Case/Decision + F']),
    ('original-G:G164', ['C3/Case/Decision + F']),
    ('original-G:G143', ['C3', 'F']),
    ('original-G:G163', ['C4', 'F']),
    ('original-G:G181', ['C4', 'C3', 'F']),
    ('adopted-capability:D14', ['C4', 'C3', 'F']),
    ('adopted-capability:C09', ['C4', 'F']),
    ('adopted-capability:R11', ['C5', 'C2', 'F']),
    ('adopted-capability:L07', ['C4', 'F']),
    ('original-RJU:U18', ['C2', 'F']),
])
def test_handoff_rejects_journey_owner_replacing_actual_source(ref, owners):
    from scripts.audit_tools.verify_source_adoption import HANDOFF, validate_owner_handoff_routing
    data = json.loads(READ(ROOT / HANDOFF))
    row = next(row for row in data['coverage'] if row['coverage_ref'] == ref)
    row['source_owners'] = owners
    with patch.object(Path, 'read_text', lambda p, *a, **kw: json.dumps(data) if p == ROOT / HANDOFF else READ(p, *a, **kw)):
        with pytest.raises(AssertionError):
            validate_owner_handoff_routing(ROOT)


@pytest.mark.parametrize('mutation', ['drop_item', 'duplicate_item', 'replace_executors',
                                    'drop_resolution', 'drop_consumers', 'dispatch'])
def test_handoff_keeps_scope_consumers_and_dispatch_boundary(mutation):
    from scripts.audit_tools.verify_source_adoption import HANDOFF, validate_owner_handoff_routing
    data = json.loads(READ(ROOT / HANDOFF))
    row = next(row for row in data['coverage'] if row['coverage_ref'] == 'original-G:G160')
    if mutation == 'drop_item':
        data['coverage'].pop()
    elif mutation == 'duplicate_item':
        data['coverage'][-1] = data['coverage'][0]
    elif mutation == 'replace_executors':
        row['eligible_executors'] = ['Codex']
    elif mutation == 'drop_resolution':
        row['source_owner_resolution']['reason'] = ''
    elif mutation == 'drop_consumers':
        row['outcome_participants'] = []
    elif mutation == 'dispatch':
        row['source_owner_resolution']['assignment'] = 'RUNNING'
    with patch.object(Path, 'read_text', lambda p, *a, **kw: json.dumps(data) if p == ROOT / HANDOFF else READ(p, *a, **kw)):
        with pytest.raises(AssertionError):
            validate_owner_handoff_routing(ROOT)


def test_handoff_preserves_math_source_and_distinct_consumer_contracts():
    from scripts.audit_tools.verify_source_adoption import HANDOFF, validate_owner_handoff_routing
    validate_owner_handoff_routing(ROOT)
    data = json.loads(READ(ROOT / HANDOFF))
    for identifier in ('G160', 'G164'):
        row = next(row for row in data['coverage'] if row['coverage_ref'] == 'original-G:' + identifier)
        assert row['source_owners'] == ['C2', 'C5']
        assert row['outcomes'] == ['J11']
        assert 'C3/Case/Decision + F' in row['outcome_participants']
        assert row['specific_changes']['item_requirement_text']
        assert row['acceptance']['exact_item_criteria']
        assert row['current_status']['complete_product_outcome'] == 'OPEN_UNTIL_ITEM_EVIDENCE'


@pytest.mark.parametrize('ref', ['original-G:G17', 'original-G:G88',
                                  'adopted-capability:D14', 'convenience:CV06'])
def test_handoff_cannot_delete_reconciliation_then_restore_journey_owners(ref):
    from scripts.audit_tools.verify_source_adoption import HANDOFF, validate_owner_handoff_routing
    data = json.loads(READ(ROOT / HANDOFF))
    row = next(row for row in data['coverage'] if row['coverage_ref'] == ref)
    data['source_routing_contract']['changed_coverage_refs'].remove(ref)
    row['source_owners'] = row.pop('outcome_participants')
    row.pop('source_owner_resolution')
    with patch.object(Path, 'read_text', lambda p, *a, **kw: json.dumps(data) if p == ROOT / HANDOFF else READ(p, *a, **kw)):
        with pytest.raises(AssertionError):
            validate_owner_handoff_routing(ROOT)


@pytest.mark.parametrize('ref', ['original-G:G17', 'original-G:G88',
                                  'adopted-capability:D14', 'adopted-capability:L07'])
def test_handoff_cannot_satisfy_source_ownership_by_adding_every_owner(ref):
    from scripts.audit_tools.verify_source_adoption import HANDOFF, validate_owner_handoff_routing
    data = json.loads(READ(ROOT / HANDOFF))
    row = next(row for row in data['coverage'] if row['coverage_ref'] == ref)
    row['source_owners'] = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'F', 'M']
    with patch.object(Path, 'read_text', lambda p, *a, **kw: json.dumps(data) if p == ROOT / HANDOFF else READ(p, *a, **kw)):
        with pytest.raises(AssertionError):
            validate_owner_handoff_routing(ROOT)


def test_all_reconciled_owner_routes_have_independent_exact_expectations():
    from scripts.audit_tools.verify_source_adoption import HANDOFF, RECONCILED_SOURCE_OWNERS
    data = json.loads(READ(ROOT / HANDOFF))
    rows = {row['coverage_ref']: row for row in data['coverage']}
    assert len(RECONCILED_SOURCE_OWNERS) == 181
    assert set(data['source_routing_contract']['changed_coverage_refs']) == RECONCILED_SOURCE_OWNERS.keys()
    for ref, expected in RECONCILED_SOURCE_OWNERS.items():
        assert set(rows[ref]['source_owners']) == expected


@pytest.fixture
def document_handoff(tmp_path):
    content = '# Plan\n\n## Work\nSave and reopen the result.\n\n## Next\nOther work.\n'
    (tmp_path / 'plan.md').write_text(content, encoding='utf-8', newline='\n')
    binding = {'path': 'plan.md', 'sha256': hashlib.sha256(content.encode()).hexdigest(),
               'heading': '## Work', 'start_line': 3, 'end_line': 5,
               'expected_start_line_text': '## Work',
               'historical_bindings': [{'path': 'old-missing.md', 'sha256': '0' * 64}]}
    data = {'scope_sources': [], 'requirements': [], 'coverage': [{
        'coverage_ref': 'original-G:G1', 'source_requirement': binding,
        'specific_changes': {'item_requirement_text': '## Work\nSave and reopen the result.\n'},
    }]}
    return tmp_path, data


def test_current_binding_accepts_git_lf_and_preserves_historical_identity(document_handoff):
    from scripts.audit_tools.verify_source_adoption import (
        validate_handoff_document_bindings,
    )
    root, data = document_handoff
    original = copy.deepcopy(data)
    validate_handoff_document_bindings(root, data)
    path = root / 'plan.md'
    path.write_bytes(path.read_bytes().replace(b'\n', b'\r\n'))
    validate_handoff_document_bindings(root, data)
    assert data == original


@pytest.mark.parametrize('mutation,reason', [
    ('content', 'Stale current document hash'),
    ('digest', 'Stale current document hash'),
    ('missing', 'Missing current document'),
    ('anchor', 'Missing or ambiguous current anchor'),
    ('duplicate_anchor', 'Missing or ambiguous current anchor'),
    ('start', 'Stale current anchor line'),
    ('end', 'Stale or truncated current range'),
    ('copied_text', 'Stale copied requirement'),
    ('outside', 'Document escapes repository'),
])
def test_current_document_drift_blocks_handoff(document_handoff, mutation, reason):
    from scripts.audit_tools.verify_source_adoption import (
        validate_handoff_document_bindings,
    )
    root, data = document_handoff
    binding = data['coverage'][0]['source_requirement']
    path = root / 'plan.md'
    if mutation == 'content':
        path.write_bytes(path.read_bytes() + b'Changed requirement.\n')
    elif mutation == 'digest':
        binding['sha256'] = '0' * 64
    elif mutation == 'missing':
        binding['path'] = 'missing.md'
    elif mutation == 'anchor':
        binding['heading'] = '## Missing'
    elif mutation == 'duplicate_anchor':
        content = path.read_bytes() + b'## Work\nAnother result.\n'
        path.write_bytes(content)
        binding['sha256'] = hashlib.sha256(content).hexdigest()
    elif mutation == 'start':
        binding['start_line'] = 4
    elif mutation == 'end':
        binding['end_line'] = 3
    elif mutation == 'copied_text':
        data['coverage'][0]['specific_changes']['item_requirement_text'] = 'Old product requirement'
    elif mutation == 'outside':
        binding['path'] = '../other-project.md'
    with pytest.raises(AssertionError, match=reason):
        validate_handoff_document_bindings(root, data)
