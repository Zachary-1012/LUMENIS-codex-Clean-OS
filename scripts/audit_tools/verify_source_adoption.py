"""Validate the local source provenance attachment, not a second runtime contract."""
from __future__ import annotations
import json
import re
from pathlib import Path

RECORD = '00-GOVERNANCE/LUMENIS-SOURCE-ADOPTION-V1.json'
FINGERPRINT = '68caa37c3f4a8d50f0c0b77befac0e8ae0c954b63b1a7583a8f822a28eaa690f'
SOURCE_COMMIT = 'e6cde984480cff3176eb39b038c7c0a66e1e2124'


HANDOFF = '00-GOVERNANCE/evidence/round-15/source-adoption-20261018/EXISTING-OWNER-WORK-HANDOFF.json'
OWNER_INDEX = '00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md'


# Reviewed source-responsibility invariants, frozen independently of the handoff.
# These are regression expectations, not a second task queue or dispatch table.
# Basis: Owner Index current R/J/U tables and C1-C6 source responsibilities;
# Math adoption's algorithm/training/consumer separation and existing capability
# callers. A source-authority change must update and review these expectations,
# not silently regenerate ownership from a user journey or this JSON's metadata.
_RECONCILED_SOURCE_GROUPS = (
    (('C5', 'C2'),
     'original-G:G7 original-G:G91'
    ),
    (('C2', 'C5', 'C3', 'C4'),
     'original-G:G10 original-G:G78 original-G:G81 original-G:G110 '
     'original-G:G125 adopted-capability:L01 adopted-capability:L02 adopted-capability:L03 '
     'adopted-capability:L04 adopted-capability:L05 adopted-capability:L06 adopted-capability:L07 '
     'adopted-capability:L08 adopted-capability:L09 adopted-capability:L10 adopted-capability:L11 '
     'adopted-capability:L12'
    ),
    (('C5', 'C4', 'C3', 'C2'),
     'original-G:G11 original-G:G170'
    ),
    (('C4', 'C5', 'C6', 'F'),
     'original-G:G13'
    ),
    (('C2', 'C5', 'C3'),
     'original-G:G17 original-G:G163'
    ),
    (('C1', 'C5', 'C6'),
     'original-G:G69 original-G:G85 original-G:G86 adopted-capability:D06'
    ),
    (('C2', 'C3', 'C4', 'C5', 'C6'),
     'original-G:G71 original-G:G92 original-G:G175 original-RJU:U18'
    ),
    (('C4', 'C5', 'C2', 'C6', 'F'),
     'original-G:G79 original-G:G28 original-G:G128 original-G:G184'
    ),
    (('C1', 'C6'),
     'original-G:G88 original-RJU:R03 original-RJU:J1 original-RJU:U04 '
     'original-RJU:U05'
    ),
    (('C2', 'C5', 'C4', 'C6'),
     'original-G:G23 original-G:G124'
    ),
    (('C1', 'C3', 'C5'),
     'original-G:G49.4 original-G:G49.5 original-G:G154 original-G:G166 '
     'original-G:G167 adopted-capability:D05 adopted-capability:D09 adopted-capability:D10 '
     'adopted-capability:D20'
    ),
    (('C2', 'C3', 'C5', 'C6'),
     'original-G:G49.6 original-G:G162'
    ),
    (('C6', 'M'),
     'original-G:G96 original-RJU:R15 original-RJU:U25'
    ),
    (('C5', 'C6', 'C2', 'F'),
     'original-G:G111'
    ),
    (('C5', 'C3', 'C4'),
     'original-G:G114'
    ),
    (('C3', 'C2', 'C5'),
     'original-G:G117 original-G:G118 original-G:G153 original-RJU:U09'
    ),
    (('C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'F', 'M'),
     'original-G:G131 original-G:G132'
    ),
    (('C5', 'C3', 'C2'),
     'original-G:G135'
    ),
    (('C1', 'C3', 'C6'),
     'original-G:G139 original-G:G176 original-G:G177'
    ),
    (('C5', 'C3', 'C2', 'C6'),
     'original-G:G143'
    ),
    (('C3', 'C5'),
     'original-G:G144 original-G:G145 original-G:G146 original-G:G147 '
     'original-G:G148 original-G:G149 original-G:G150 original-G:G151 '
     'original-G:G152 original-G:G155 original-G:G156 original-G:G157 '
     'original-G:G158 adopted-capability:D01 adopted-capability:D02 adopted-capability:D03 '
     'adopted-capability:D04 adopted-capability:D07 adopted-capability:D08 adopted-capability:D11 '
     'adopted-capability:D12 adopted-capability:D13 adopted-capability:D14 adopted-capability:D15 '
     'adopted-capability:D16 adopted-capability:D17 adopted-capability:D18 adopted-capability:D19 '
     'adopted-capability:D21 adopted-capability:D22 adopted-capability:D23 adopted-capability:D24 '
     'adopted-capability:D25 adopted-capability:D26 adopted-capability:D27 adopted-capability:D28 '
     'adopted-capability:D29 adopted-capability:D32 adopted-capability:D40 adopted-capability:D41 '
     'adopted-capability:D42 adopted-capability:D43 adopted-capability:D44'
    ),
    (('C3', 'C5', 'C2', 'F'),
     'original-G:G159'
    ),
    (('C2', 'C5'),
     'original-G:G160 original-G:G164 original-RJU:J7 convenience:CV06'
    ),
    (('C1', 'C2', 'C3', 'C5', 'C6'),
     'original-G:G161'
    ),
    (('C5', 'C2', 'C3', 'F'),
     'original-G:G165'
    ),
    (('C3', 'C5', 'C1'),
     'original-G:G168 original-G:G169'
    ),
    (('C1', 'C2', 'C3', 'C5', 'F'),
     'original-G:G181'
    ),
    (('M', 'C6'),
     'original-RJU:R01 original-RJU:R02'
    ),
    (('C1', 'C2', 'C5', 'C6'),
     'original-RJU:R04'
    ),
    (('C1', 'C2', 'C6'),
     'original-RJU:R05'
    ),
    (('C1', 'C6', 'F'),
     'original-RJU:R06 original-RJU:U01 original-RJU:U21'
    ),
    (('C2', 'C4', 'C5'),
     'original-RJU:R07'
    ),
    (('C6', 'F'),
     'original-RJU:R08 original-RJU:J8 original-RJU:U23'
    ),
    (('C1', 'C2', 'C3', 'C5', 'C6', 'F'),
     'original-RJU:R09'
    ),
    (('C1', 'C3'),
     'original-RJU:R10 original-RJU:U02'
    ),
    (('C2', 'C3', 'C4', 'C5'),
     'original-RJU:R11 original-RJU:R13 original-RJU:U20'
    ),
    (('C1', 'C2', 'C3'),
     'original-RJU:R12'
    ),
    (('C1', 'C2', 'C5', 'C6', 'F'),
     'original-RJU:R14'
    ),
    (('C3', 'C1', 'C2', 'C5'),
     'original-RJU:J2 original-RJU:J3 original-RJU:U07 original-RJU:U08 '
     'original-RJU:U10 original-RJU:U11'
    ),
    (('C4', 'C2', 'C5', 'F'),
     'original-RJU:J4 original-RJU:J5 original-RJU:J6 original-RJU:U13 '
     'original-RJU:U14 original-RJU:U15'
    ),
    (('C1', 'C3', 'F'),
     'original-RJU:U03'
    ),
    (('C3', 'C1', 'C5', 'F'),
     'original-RJU:U06'
    ),
    (('C3', 'C2', 'C4', 'C5', 'F'),
     'original-RJU:U12'
    ),
    (('C5', 'C2', 'C1'),
     'original-RJU:U16'
    ),
    (('C5', 'C2', 'C3', 'C4'),
     'original-RJU:U17'
    ),
    (('C2', 'C6'),
     'original-RJU:U19'
    ),
    (('C6', 'C1', 'C2', 'C5', 'F'),
     'original-RJU:U22'
    ),
    (('C5', 'C6', 'F'),
     'original-RJU:U24'
    ),
    (('C6', 'C4', 'C2'),
     'adopted-capability:B07'
    ),
    (('C4', 'C2', 'C5', 'C6'),
     'adopted-capability:C09'
    ),
    (('C4', 'C2', 'C6'),
     'adopted-capability:C22 adopted-capability:C23'
    ),
    (('C5', 'C2', 'C3'),
     'adopted-capability:D30 adopted-capability:D31'
    ),
    (('C5', 'C6', 'C2'),
     'adopted-capability:R01 adopted-capability:R02 adopted-capability:R03 adopted-capability:R04 '
     'adopted-capability:R05 adopted-capability:R06 adopted-capability:R07 adopted-capability:R08 '
     'adopted-capability:R10 adopted-capability:R12 adopted-capability:R13'
    ),
    (('C2', 'C5', 'C6'),
     'adopted-capability:R09'
    ),
    (('C5', 'C3', 'C6'),
     'adopted-capability:R11'
    ),
 )
RECONCILED_SOURCE_OWNERS = {
    ref: set(owners)
    for owners, references in _RECONCILED_SOURCE_GROUPS
    for ref in references.split()
}


def _owner_roles(values) -> set[str]:
    return set(re.findall(r'\b(?:C[1-6]|F|M)\b', ' '.join(values)))


def validate_owner_handoff_routing(root: Path) -> None:
    """Guard source ownership separately from journey participation and dispatch.

    This validates the existing handoff, not a second requirement register or an
    implementation/acceptance gate. Exact document hashes are bound by the
    publication workflow after canonical content is frozen.
    """
    data = json.loads((root / HANDOFF).read_text(encoding='utf-8'))
    rows = {row['coverage_ref']: row for row in data['coverage']}
    assert len(rows) == len(data['coverage']) == 396
    assert len({row['id'] for row in data['requirements']}) == 30
    assert data['delivery_schema_version'] == 1
    for row in [*data['coverage'], *data['requirements']]:
        assert set(row['eligible_executors']) == {'Codex', 'Zack', '阿康'}
    routing = data['source_routing_contract']
    corrected = set(routing['changed_coverage_refs'])
    assert corrected == RECONCILED_SOURCE_OWNERS.keys(), "Reconciled source routes cannot be dropped or invented"
    assert corrected <= rows.keys()
    for ref in corrected:
        row = rows[ref]
        resolution = row['source_owner_resolution']
        assert resolution['basis'] == OWNER_INDEX
        assert resolution['reason'] and resolution['requirement_basis']
        assert resolution['assignment'] == 'UNCHANGED_NOT_ASSIGNED_BY_THIS_INDEX'
        assert row['outcome_participants'] and row['source_owners']
        assert all(role in {'C1','C2','C3','C4','C5','C6','F','M'} for role in row['source_owners'])
        assert row['source_owners'] != row['outcome_participants'], ref
        assert len(row['source_owners']) == len(set(row['source_owners'])), ref
        assert set(row['source_owners']) == RECONCILED_SOURCE_OWNERS[ref], ref
    # Read the actual source authority, not a second hardcoded R/J/U owner table.
    authority = {}
    for line in (root / OWNER_INDEX).read_text(encoding='utf-8').splitlines():
        cells = [cell.strip() for cell in line.split('|')]
        if len(cells) > 3 and re.fullmatch(r'[RJU]\d+', cells[1]):
            value = cells[2] if len(cells) == 4 else cells[3]
            roles = re.findall(r'\b(?:C[1-6]|F|M|W6)\b', value)
            if roles:
                authority[cells[1]] = {'C6' if role == 'W6' else role for role in roles}
    for identifier, expected in authority.items():
        ref = 'original-RJU:' + identifier
        assert ref in corrected
        assert _owner_roles(rows[ref]['source_owners']) == expected, ref


def validate_local_adoption(root: Path) -> None:
    root = root.resolve()
    validate_owner_handoff_routing(root)
    data = json.loads((root / RECORD).read_text(encoding='utf-8'))
    assert data['schema'] == 'lumenis.source-adoption-record/v1'
    assert data['record_version'] == '1.0.0'
    assert data['scope'] == 'LOCAL_SOURCE_ADOPTION_ONLY'
    assert data['authority'] == 'LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md'
    assert data['plan'] == 'LOOP-PLAN-20261014/product-plan-full.md'
    assert data['source_repository'] == 'Zachary-1012/global-growth-intelligence'
    assert data['source_commit'] == SOURCE_COMMIT
    assert data['status'] in {'IN_PROGRESS_OWNER_VALIDATION_REQUIRED', 'VERIFIED_BOUNDED_SOURCE_ADOPTION'}
    exchange = data['exchange_contract']
    assert exchange['version'] == '1.1.0' and exchange['fingerprint'] == FINGERPRINT
    for field in ('modified', 'external_repositories_modified', 'local_attachment_is_exchange_version'):
        assert exchange[field] is False, field
    contract = json.loads((root / '00-GOVERNANCE' / exchange['path']).read_text(encoding='utf-8'))
    assert contract['contract_version'] == exchange['version']
    assert contract['protocol_fingerprint_sha256'] == exchange['fingerprint']
    expected_boundaries = {'new_product_domain', 'parallel_runtime_account_database', 'cross_database_copy',
                           'unrestricted_writer', 'automatic_truth_promotion', 'external_delivery_authorized'}
    assert set(data['boundaries']) == expected_boundaries
    assert all(value is False for value in data['boundaries'].values())
    assert data['inventory'] == {'files': 72, 'route_intentions': 51, 'capabilities': 33, 'dimensions': 9,
                                'reference_records': {'market': 7, 'platform': 12, 'policy': 14, 'scenario': 3}}
    assert data['rights']['original_source_license_file'] == 'ABSENT'
    assert data['rights']['third_party_reuse'] == 'UNKNOWN'
    assert data['rights']['seed_fact_status'] == 'HISTORICAL_REFERENCE_REVERIFY'
    maps = {}
    for key, relative in data['maps'].items():
        path = (root / relative).resolve()
        assert path.is_relative_to(root / '00-GOVERNANCE/evidence/round-15/source-adoption-20261018'), key
        maps[key] = json.loads(path.read_text(encoding='utf-8'))
    assert set(maps) == {'files', 'endpoints', 'capabilities', 'rights', 'seed_records'}
    assert len(maps['files']) == 72 and len({r['path'] for r in maps['files']}) == 72
    for row in maps['files']:
        assert row['verified'] is True
        assert row['git_blob_sha1'] == row['expected_blob_sha1']
        assert len(row['sha256']) == 64 and row['adoption_target'] and row['proposed_owner']
    assert len(maps['endpoints']) == 51
    assert len({(r['method'], r['source_path']) for r in maps['endpoints']}) == 51
    assert all(r['owner'] and r['target'] and r['acceptance'] and r.get('target_callable')
               and r.get('target_http_contract') and r.get('semantic_adaptation') for r in maps['endpoints'])
    expected_ids = {f'{prefix}{i:02}' for prefix, count in [('R', 9), ('E', 8), ('B', 8), ('I', 8)] for i in range(1, count + 1)}
    assert {r['id'] for r in maps['capabilities']} == expected_ids
    assert len(maps['capabilities']) == 33
    assert all(r['existing_owner'] and r['positive_acceptance'] and r['negative_acceptance']
               and r.get('current_target_callable') and r.get('remaining') for r in maps['capabilities'])
    assert len(maps['seed_records']) == 36
    for kind, count in data['inventory']['reference_records'].items():
        assert sum(r['source_kind'] == kind for r in maps['seed_records']) == count
    for row in maps['seed_records']:
        assert row['rights'] == 'UNKNOWN' and row['freshness'] == 'NOT_REVERIFIED'
        assert row['source_claim_is_current_fact'] is False
        assert row['scenario_is_observed_outcome'] is False
        assert row['source_commit'] == SOURCE_COMMIT
    assert len(maps['rights']) == 4
    assert all(r['reuse_license'] == 'NOT_DECLARED_IN_SOURCE' and isinstance(r['source_urls'], list) for r in maps['rights'])
    for relative in ('AGENTS.md', 'README.md', '00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md',
                     '00-GOVERNANCE/CANONICAL_REGISTRY.md', '00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md',
                     '00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md', '00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md'):
        assert 'LUMENIS-SOURCE-ADOPTION-V1.json' in (root / relative).read_text(encoding='utf-8'), relative
    assert len((root / 'AGENTS.md').read_bytes()) + 16384 <= 131072


if __name__ == '__main__':
    validate_local_adoption(Path(__file__).resolve().parents[2])
    print('LOCAL SOURCE ADOPTION provenance/mapping/boundary OK; not product acceptance')
