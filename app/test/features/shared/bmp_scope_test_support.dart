const int bmpTestActorId = 701;

Map<String, dynamic> bmpFocusScope({String brandFocusId = 'BRAND-ONE'}) => {
  'mode': 'FOCUS',
  'domain_id': 'BMP',
  'product_id': 'ZBMP',
  'subject_id': 'SUBJ-ONE',
  'brand_focus_id': brandFocusId,
};

Map<String, dynamic> bmpGlobalScope() => {
  'mode': 'GLOBAL_ALL',
  'domain_id': 'BMP',
  'product_id': 'ZBMP',
  'subject_id': null,
  'brand_focus_id': null,
};

Map<String, dynamic> bmpTestPermission(Map<String, dynamic> scope) => {
  'action': 'read',
  'allowed': true,
  'verification_state': 'verified',
  'actor_id': bmpTestActorId,
  'scope': scope,
};

Map<String, dynamic> bmpTestEvidence(
  Map<String, dynamic> scope, {
  int reference = bmpTestActorId,
  String? digest,
  bool verified = true,
  String assurance = 'content-integrity-only',
}) => {
  'evidence_ref': reference,
  'scope': scope,
  'integrity_version': 2,
  'integrity_algorithm': 'sha256',
  'integrity_key_id': null,
  'integrity_digest': digest ?? _bmpDigest(scope),
  'integrity_verified': verified,
  'integrity_assurance': assurance,
};

Map<String, dynamic> bmpFocusBinding() {
  final scope = bmpFocusScope();
  return {
    'applied': true,
    'read_allowed': true,
    'global_all_granted': false,
    'actor_id': bmpTestActorId,
    'scope': scope,
    'permission': bmpTestPermission(scope),
    'evidence': bmpTestEvidence(scope),
  };
}

Map<String, dynamic> bmpGlobalBinding() {
  final scope = bmpGlobalScope();
  return {
    'applied': true,
    'read_allowed': true,
    'global_all_granted': true,
    'actor_id': bmpTestActorId,
    'scope': scope,
    'permission': bmpTestPermission(scope),
    'evidence': bmpTestEvidence(scope),
  };
}

String _bmpDigest(Map<String, dynamic> scope) {
  if (scope['mode'] == 'GLOBAL_ALL') {
    return 'f081d0baf4e09999c86f9db56168d487867f8b8d14ba3bc9418260cd5d66b024';
  }
  if (scope['brand_focus_id'] == 'BRAND-TWO') {
    return '77c8b5cf877fbf6490f49a327e843545bcdf2ee68e2559501cd3114b869bd76d';
  }
  return '7024f597e2ce082139496fd7a960bd0696eec92440c37e267abb99b15303ef31';
}
