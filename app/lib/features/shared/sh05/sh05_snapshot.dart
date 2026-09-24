enum Sh05ScopeMode { globalAll, focus }

enum Sh05ScopeErrorKind { unavailable, denied, malformed }

class Sh05ScopeError implements Exception {
  const Sh05ScopeError(this.kind);

  final Sh05ScopeErrorKind kind;
}

class Sh05Scope {
  const Sh05Scope({
    required this.mode,
    required this.domain,
    required this.focusId,
    required this.displayName,
  });

  final Sh05ScopeMode mode;
  final String? domain;
  final String? focusId;
  final String displayName;

  bool get isGlobal => mode == Sh05ScopeMode.globalAll;

  String get businessDomain => switch (domain) {
    'CTH' => '商业运营',
    'BMP' => '品牌市场',
    _ => '全部范围',
  };

  static Sh05Scope fromResponse(Map<String, dynamic> response) {
    final rawScope = _asMap(response['scope'] ?? response['context']);
    final permission = _asMap(
      response['permission'] ?? response['authorization'],
    );
    if (rawScope == null || permission == null) {
      throw const Sh05ScopeError(Sh05ScopeErrorKind.unavailable);
    }
    if (response['selection_only'] == true ||
        rawScope['selection_only'] == true) {
      throw const Sh05ScopeError(Sh05ScopeErrorKind.unavailable);
    }
    final decision = _string(
      permission['decision'] ?? permission['result'] ?? permission['state'],
    )?.toUpperCase();
    final canRead =
        permission['read'] == true ||
        permission['can_read'] == true ||
        permission['view'] == true;
    if (!canRead ||
        !const {'ALLOW', 'ALLOWED', 'GRANTED', 'PERMITTED'}.contains(decision)) {
      throw const Sh05ScopeError(Sh05ScopeErrorKind.denied);
    }
    final mode = _string(
      rawScope['mode'] ?? rawScope['scope_mode'],
    )?.toUpperCase();
    if (mode == 'GLOBAL_ALL') {
      if (_present(rawScope['subject_id']) ||
          _present(rawScope['brand_focus_id']) ||
          rawScope['global'] == false) {
        throw const Sh05ScopeError(Sh05ScopeErrorKind.malformed);
      }
      return const Sh05Scope(
        mode: Sh05ScopeMode.globalAll,
        domain: null,
        focusId: null,
        displayName: '全部范围',
      );
    }
    if (mode != 'FOCUS') {
      throw const Sh05ScopeError(Sh05ScopeErrorKind.malformed);
    }
    final domain = _string(
      rawScope['domain_id'] ?? rawScope['domain'],
    )?.toUpperCase();
    final focusId = _string(
      rawScope['subject_id'] ??
          rawScope['brand_focus_id'] ??
          rawScope['focus_id'],
    );
    final displayName = _safeText(rawScope['display_name']);
    if ((domain != 'CTH' && domain != 'BMP' && domain != 'ZBMP') ||
        focusId == null ||
        displayName == null) {
      throw const Sh05ScopeError(Sh05ScopeErrorKind.malformed);
    }
    return Sh05Scope(
      mode: Sh05ScopeMode.focus,
      domain: domain == 'ZBMP' ? 'BMP' : domain,
      focusId: focusId,
      displayName: displayName,
    );
  }
}

enum Sh05AssetKind { sop, retrospective, training, evaluation, pattern, other }

enum Sh05PromotionStatus {
  observed,
  candidate,
  domainVerified,
  transferCandidate,
  coreVerified,
  rejected,
  repaired,
  retired,
  unknown,
}

class Sh05Asset {
  const Sh05Asset({
    required this.internalId,
    required this.title,
    required this.description,
    required this.kind,
    required this.version,
    required this.promotionStatus,
    required this.rollbackAvailable,
    required this.reviewState,
    required this.reviewedAt,
    required this.provenance,
  });

  final String internalId;
  final String title;
  final String description;
  final Sh05AssetKind kind;
  final String version;
  final Sh05PromotionStatus promotionStatus;
  final bool rollbackAvailable;
  final String reviewState;
  final String reviewedAt;
  final String provenance;

  String get kindLabel => switch (kind) {
    Sh05AssetKind.sop => 'SOP',
    Sh05AssetKind.retrospective => '复盘',
    Sh05AssetKind.training => '培训',
    Sh05AssetKind.evaluation => '评估',
    Sh05AssetKind.pattern => '模式',
    Sh05AssetKind.other => '资产',
  };

  String get promotionLabel => switch (promotionStatus) {
    Sh05PromotionStatus.observed => '已观察',
    Sh05PromotionStatus.candidate => '候选',
    Sh05PromotionStatus.domainVerified => '域内验证',
    Sh05PromotionStatus.transferCandidate => '迁移候选',
    Sh05PromotionStatus.coreVerified => '通用验证',
    Sh05PromotionStatus.rejected => '已拒绝',
    Sh05PromotionStatus.repaired => '已修复',
    Sh05PromotionStatus.retired => '已退役',
    Sh05PromotionStatus.unknown => '状态未确认',
  };

  static Sh05Asset? tryParse(Object? value, {required Sh05Scope scope}) {
    final record = _asMap(value);
    if (record == null) return null;
    final id = _string(
      record['id'] ?? record['asset_id'] ?? record['experience_id'],
    );
    final title = _safeText(record['title'] ?? record['name']);
    final version = _string(record['version'] ?? record['asset_version']);
    final status = _promotion(record['promotion_status'] ?? record['status']);
    if (id == null ||
        title == null ||
        version == null ||
        status == Sh05PromotionStatus.unknown) {
      return null;
    }
    if (_SharedProjection.tryParse(record['projection'], scope: scope) == null) {
      return null;
    }
    final rollback = _asMap(record['rollback']);
    return Sh05Asset(
      internalId: id,
      title: title,
      description: _safeText(record['description'] ?? record['summary']) ?? '',
      kind: _kind(record['kind'] ?? record['type']),
      version: version,
      promotionStatus: status,
      rollbackAvailable:
          rollback?['available'] == true ||
          record['rollback_available'] == true,
      reviewState: _reviewState(
        record['review_state'] ?? record['verification_state'],
      ),
      reviewedAt:
          _safeText(record['reviewed_at'] ?? record['updated_at']) ?? '',
      provenance:
          _safeText(record['provenance'] ?? record['source_label']) ?? '',
    );
  }
}

class Sh05Snapshot {
  const Sh05Snapshot({required this.scope, required this.assets});

  final Sh05Scope scope;
  final List<Sh05Asset> assets;

  factory Sh05Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'SH-05') {
      throw const FormatException('SH-05 response identity is invalid.');
    }
    if (response['bound'] != true || response['source'] != 'runtime') {
      throw const FormatException('SH-05 runtime binding is unavailable.');
    }
    final scope = Sh05Scope.fromResponse(response);
    final data = _asMap(response['data']);
    if (data == null) {
      throw const FormatException('SH-05 data envelope is incomplete.');
    }
    final rawAssets = data['assets'];
    if (rawAssets is! List) {
      throw const FormatException('SH-05 asset list is unavailable.');
    }
    return Sh05Snapshot(
      scope: scope,
      assets: rawAssets
          .map((item) => Sh05Asset.tryParse(item, scope: scope))
          .whereType<Sh05Asset>()
          .toList(growable: false),
    );
  }
}

class _SharedProjection {
  const _SharedProjection({
    required this.canonicalEvidenceReference,
    required this.integrityDigest,
    required this.assurance,
    required this.originVerified,
  });

  final String canonicalEvidenceReference;
  final String integrityDigest;
  final String assurance;
  final bool originVerified;

  static _SharedProjection? tryParse(
    Object? value, {
    required Sh05Scope scope,
    bool requireOrigin = false,
  }) {
    final projection = _asMap(value);
    if (projection == null ||
        projection['contract'] !=
            'lumenis.shared.experience-row-projection' ||
        projection['version'] != 2 ||
        projection['read_allowed'] != true) {
      return null;
    }
    final projectionScope = _asMap(projection['scope']);
    if (projectionScope == null ||
        !_projectionScopeMatches(projectionScope, scope)) {
      return null;
    }
    final evidence = _asMap(projection['evidence']);
    final canonicalReference = _safeProjectionReference(
      evidence?['canonical_reference'],
    );
    if (canonicalReference == null) return null;
    final integrity = _asMap(projection['integrity']);
    if (integrity == null ||
        integrity['integrity_version'] != 2 ||
        integrity['verified'] != true ||
        integrity['lineage_verified'] != true) {
      return null;
    }
    final assurance = _string(integrity['assurance']);
    if (assurance == null ||
        !const {'writer-authenticated', 'content-integrity-only'}
            .contains(assurance)) {
      return null;
    }
    final algorithm = _string(integrity['algorithm'])?.toLowerCase();
    final digest = _safeProjectionDigest(integrity['digest']);
    final consistentAssurance =
        (assurance == 'writer-authenticated' && algorithm == 'hmac-sha256') ||
        (assurance == 'content-integrity-only' && algorithm == 'sha256');
    if (digest == null || !consistentAssurance) {
      return null;
    }
    final originVerified = projection['origin_verified'] == true;
    if (requireOrigin && !originVerified) return null;
    return _SharedProjection(
      canonicalEvidenceReference: canonicalReference,
      integrityDigest: digest,
      assurance: assurance,
      originVerified: originVerified,
    );
  }
}

bool _projectionScopeMatches(Map<String, dynamic> raw, Sh05Scope scope) {
  final mode = _string(raw['mode'] ?? raw['scope_mode'])?.toUpperCase();
  if (scope.isGlobal) {
    return mode == 'GLOBAL_ALL' &&
        raw['global_all_granted'] == true &&
        !_present(raw['subject_id']) &&
        !_present(raw['brand_focus_id']) &&
        !_present(raw['focus_id']);
  }
  if (mode != 'FOCUS' || raw['global_all_granted'] == true) return false;
  final domain = _string(raw['domain_id'] ?? raw['domain'])?.toUpperCase();
  final ids = <String?>[
    _string(raw['subject_id']),
    _string(raw['brand_focus_id']),
    _string(raw['focus_id']),
  ].whereType<String>().toList(growable: false);
  if (ids.length != 1) return false;
  return (domain == scope.domain || (domain == 'ZBMP' && scope.domain == 'BMP')) &&
      ids.single == scope.focusId;
}

String? _safeProjectionReference(Object? value) {
  final reference = _string(value);
  if (reference == null || reference.length > 200) return null;
  return RegExp(r'^evidence:canonical:[A-Za-z0-9._:-]+$').hasMatch(reference)
      ? reference
      : null;
}

String? _safeProjectionDigest(Object? value) {
  final digest = _string(value);
  if (digest == null || digest.length > 200) return null;
  return RegExp(r'^[a-f0-9]{64}$').hasMatch(digest)
      ? digest
      : null;
}

Sh05AssetKind _kind(Object? value) => switch (_string(value)?.toUpperCase()) {
  'SOP' => Sh05AssetKind.sop,
  'RETROSPECTIVE' || 'REVIEW' => Sh05AssetKind.retrospective,
  'TRAINING' => Sh05AssetKind.training,
  'EVALUATION' || 'BENCHMARK' => Sh05AssetKind.evaluation,
  'PATTERN' => Sh05AssetKind.pattern,
  _ => Sh05AssetKind.other,
};

Sh05PromotionStatus _promotion(Object? value) => switch (_string(
  value,
)?.toUpperCase()) {
  'OBSERVED' => Sh05PromotionStatus.observed,
  'CANDIDATE' => Sh05PromotionStatus.candidate,
  'DOMAIN-VERIFIED' || 'DOMAIN_VERIFIED' => Sh05PromotionStatus.domainVerified,
  'TRANSFER-CANDIDATE' ||
  'TRANSFER_CANDIDATE' => Sh05PromotionStatus.transferCandidate,
  'CORE-VERIFIED' || 'CORE_VERIFIED' => Sh05PromotionStatus.coreVerified,
  'REJECTED' => Sh05PromotionStatus.rejected,
  'REPAIRED' => Sh05PromotionStatus.repaired,
  'RETIRED' => Sh05PromotionStatus.retired,
  _ => Sh05PromotionStatus.unknown,
};

String _reviewState(Object? value) => switch (_string(value)?.toUpperCase()) {
  'VERIFIED' || 'APPROVED' => '已复核',
  'PENDING' || 'REVIEW' => '待复核',
  'REJECTED' => '复核未通过',
  _ => '复核状态未确认',
};

Map<String, dynamic>? _asMap(Object? value) {
  if (value is! Map) return null;
  return value.map((key, value) => MapEntry('$key', value));
}

String? _string(Object? value) =>
    value is String && value.trim().isNotEmpty ? value.trim() : null;

bool _present(Object? value) => _string(value) != null;

String? _safeText(Object? value) {
  final text = _string(value);
  if (text == null || text.length > 220 || RegExp(r'[<>]').hasMatch(text)) {
    return null;
  }
  if (RegExp(
    r'(api|database|sqlite|\bdb\b|provider|permission|owner|runtime|contract|viewmodel|canonical|subject|brandfocus|\bcth\b|\bbmp\b|\bzbmp\b|token|cookie|secret|internal|private|path|https?)',
    caseSensitive: false,
  ).hasMatch(text)) {
    return null;
  }
  return text;
}
