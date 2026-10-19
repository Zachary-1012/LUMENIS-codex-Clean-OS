from __future__ import annotations
import copy
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
