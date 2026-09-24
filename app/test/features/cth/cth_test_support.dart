const Map<String, dynamic> cthGlobalProjection = {
  'contract': 'lumenis.shared.experience-row-projection',
  'version': 2,
  'read_allowed': true,
  'scope': {
    'mode': 'GLOBAL_ALL',
    'domain_id': 'CTH',
    'product_id': 'CTH',
    'global_all_granted': true,
  },
  'evidence': {'canonical_reference': 'evidence:canonical:cth-test'},
  'integrity': {
    'integrity_version': 2,
    'verified': true,
    'lineage_verified': true,
    'assurance': 'content-integrity-only',
    'algorithm': 'sha256',
    'digest':
        '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
  },
};

const Map<String, dynamic> cthGuangzhouFocusProjection = {
  'contract': 'lumenis.shared.experience-row-projection',
  'version': 2,
  'read_allowed': true,
  'scope': {
    'mode': 'FOCUS',
    'domain_id': 'CTH',
    'product_id': 'CTH',
    'subject_id': 'GUANGZHOU_TAIKOO_HUI',
  },
  'evidence': {'canonical_reference': 'evidence:canonical:cth-test-focus'},
  'integrity': {
    'integrity_version': 2,
    'verified': true,
    'lineage_verified': true,
    'assurance': 'content-integrity-only',
    'algorithm': 'sha256',
    'digest':
        'fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210',
  },
};
