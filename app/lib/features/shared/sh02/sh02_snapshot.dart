enum Sh02ScopeMode { globalAll, focus }

enum Sh02ScopeErrorKind { unavailable, denied, malformed }

class Sh02ScopeError implements Exception {
  const Sh02ScopeError(this.kind);

  final Sh02ScopeErrorKind kind;
}

class Sh02Scope {
  const Sh02Scope({
    required this.mode,
    required this.domain,
    required this.focusId,
    required this.displayName,
  });

  final Sh02ScopeMode mode;
  final String? domain;
  final String? focusId;
  final String displayName;

  bool get isGlobal => mode == Sh02ScopeMode.globalAll;

  String get businessDomain => switch (domain) {
    'CTH' => '商业运营',
    'BMP' => '品牌市场',
    _ => '全部范围',
  };

  static Sh02Scope fromResponse(Map<String, dynamic> response) {
    final rawScope = _asMap(response['scope'] ?? response['context']);
    final permission = _asMap(
      response['permission'] ?? response['authorization'],
    );
    if (rawScope == null || permission == null) {
      throw const Sh02ScopeError(Sh02ScopeErrorKind.unavailable);
    }
    if (response['selection_only'] == true ||
        rawScope['selection_only'] == true) {
      throw const Sh02ScopeError(Sh02ScopeErrorKind.unavailable);
    }

    final decision = _string(
      permission['decision'] ?? permission['result'] ?? permission['state'],
    )?.toUpperCase();
    final canRead =
        permission['read'] == true ||
        permission['can_read'] == true ||
        permission['view'] == true;
    if (!canRead ||
        !const {
          'ALLOW',
          'ALLOWED',
          'GRANTED',
          'PERMITTED',
        }.contains(decision)) {
      throw const Sh02ScopeError(Sh02ScopeErrorKind.denied);
    }

    final mode = _string(
      rawScope['mode'] ?? rawScope['scope_mode'],
    )?.toUpperCase();
    if (mode == 'GLOBAL_ALL') {
      if (_present(rawScope['subject_id']) ||
          _present(rawScope['brand_focus_id']) ||
          rawScope['global'] == false) {
        throw const Sh02ScopeError(Sh02ScopeErrorKind.malformed);
      }
      return const Sh02Scope(
        mode: Sh02ScopeMode.globalAll,
        domain: null,
        focusId: null,
        displayName: '全部范围',
      );
    }

    if (mode != 'FOCUS') {
      throw const Sh02ScopeError(Sh02ScopeErrorKind.malformed);
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
      throw const Sh02ScopeError(Sh02ScopeErrorKind.malformed);
    }
    return Sh02Scope(
      mode: Sh02ScopeMode.focus,
      domain: domain == 'ZBMP' ? 'BMP' : domain,
      focusId: focusId,
      displayName: displayName,
    );
  }
}

enum Sh02EvidenceKind { metric, source, finding, risk, caseItem, other }

class Sh02Evidence {
  const Sh02Evidence({
    required this.internalId,
    required this.kind,
    required this.summary,
    required this.source,
    required this.capturedAt,
    required this.freshness,
    required this.lineage,
    required this.origin,
  });

  final String internalId;
  final Sh02EvidenceKind kind;
  final String summary;
  final String source;
  final String capturedAt;
  final String freshness;
  final List<String> lineage;
  final String origin;

  String get kindLabel => switch (kind) {
    Sh02EvidenceKind.metric => '指标',
    Sh02EvidenceKind.source => '来源',
    Sh02EvidenceKind.finding => '发现',
    Sh02EvidenceKind.risk => '风险',
    Sh02EvidenceKind.caseItem => '案例',
    Sh02EvidenceKind.other => '资料',
  };

  static Sh02Evidence? tryParse(Object? value, {required Sh02Scope scope}) {
    final record = _asMap(value);
    if (record == null) return null;
    final id = _string(record['id'] ?? record['evidence_id']);
    final summary = _safeText(record['summary'] ?? record['quote']);
    if (id == null || summary == null) return null;
    if (_SharedProjection.tryParse(record['projection'], scope: scope) ==
        null) {
      return null;
    }
    final lineage = _strings(record['lineage'] ?? record['chain']);
    final origin =
        _safeText(
          record['origin'] ?? record['source_context'] ?? record['domain_name'],
        ) ??
        '';
    return Sh02Evidence(
      internalId: id,
      kind: _kind(record['kind'] ?? record['type']),
      summary: summary,
      source: _safeText(record['source'] ?? record['source_name']) ?? '',
      capturedAt: _safeText(record['captured_at'] ?? record['time']) ?? '',
      freshness: _freshness(record['freshness'] ?? record['state']),
      lineage: lineage
          .map(_lineageLabel)
          .where((value) => value.isNotEmpty)
          .toList(growable: false),
      origin: origin,
    );
  }
}

class Sh02Snapshot {
  const Sh02Snapshot({required this.scope, required this.evidence});

  final Sh02Scope scope;
  final List<Sh02Evidence> evidence;

  factory Sh02Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'SH-02') {
      throw const FormatException('SH-02 response identity is invalid.');
    }
    if (response['bound'] != true || response['source'] != 'runtime') {
      throw const FormatException('SH-02 runtime binding is unavailable.');
    }
    final scope = Sh02Scope.fromResponse(response);
    final data = _asMap(response['data']);
    if (data == null) {
      throw const FormatException('SH-02 data envelope is incomplete.');
    }
    final rawItems = data['evidence'] ?? data['items'];
    if (rawItems is! List) {
      throw const FormatException('SH-02 evidence list is unavailable.');
    }
    return Sh02Snapshot(
      scope: scope,
      evidence: rawItems
          .map((item) => Sh02Evidence.tryParse(item, scope: scope))
          .whereType<Sh02Evidence>()
          .toList(growable: false),
    );
  }
}

class Sh02ImportedMaterial {
  const Sh02ImportedMaterial({
    required this.artifactId,
    required this.artifactSha256,
    required this.requestId,
    required this.filename,
    required this.sourceSha256,
    required this.sizeBytes,
    required this.createdAt,
    required this.characterCount,
    required this.tableCount,
    required this.text,
    required this.excerpts,
    required this.limitations,
  });

  final String artifactId;
  final String artifactSha256;
  final String requestId;
  final String filename;
  final String sourceSha256;
  final int sizeBytes;
  final String createdAt;
  final int characterCount;
  final int tableCount;
  final String text;
  final List<String> excerpts;
  final List<String> limitations;

  static Sh02ImportedMaterial? tryParse(Object? value) {
    final item = _asMap(value);
    final artifact = _asMap(item?['artifact']);
    final document = _asMap(item?['document']);
    final payload = _asMap(document?['payload']);
    final source = _asMap(payload?['source_material']);
    final parsed = _asMap(payload?['parsed_source']);
    final analysis = _asMap(payload?['basic_analysis']);
    final artifactId = _string(artifact?['artifact_id']);
    final artifactSha = _string(artifact?['sha256']);
    final requestId = _string(document?['request_id']);
    final filename = _string(source?['original_filename']);
    final sourceSha = _string(source?['sha256']);
    final size = source?['size_bytes'];
    final characterCount = analysis?['character_count'];
    final tableCount = analysis?['table_count'];
    final text = parsed?['text'];
    final createdAt = _string(artifact?['created_at']);
    if (document?['kind'] != 'research' ||
        source?['origin'] != 'user-upload' ||
        artifactId == null ||
        !RegExp(r'^ART-[0-9a-f]{16}$').hasMatch(artifactId) ||
        artifactSha == null ||
        !RegExp(r'^[0-9a-f]{64}$').hasMatch(artifactSha) ||
        requestId == null ||
        !RegExp(r'^[A-Za-z0-9_-]{8,128}$').hasMatch(requestId) ||
        filename == null ||
        filename.runes.length > 185 ||
        sourceSha == null ||
        !RegExp(r'^[0-9a-f]{64}$').hasMatch(sourceSha) ||
        size is! int ||
        size <= 0 ||
        size > 8 * 1024 * 1024 ||
        characterCount is! int ||
        characterCount < 0 ||
        tableCount is! int ||
        tableCount < 0 ||
        text is! String ||
        text.runes.length != characterCount ||
        createdAt == null ||
        createdAt.isEmpty) {
      return null;
    }
    final rawExcerpts = analysis?['source_excerpts'];
    final excerpts = rawExcerpts is List
        ? rawExcerpts
              .map(_asMap)
              .whereType<Map<String, dynamic>>()
              .map((excerpt) => excerpt['text'])
              .whereType<String>()
              .toList(growable: false)
        : const <String>[];
    final rawLimitations = analysis?['limitations'];
    final limitations = rawLimitations is List
        ? rawLimitations.whereType<String>().toList(growable: false)
        : const <String>[];
    return Sh02ImportedMaterial(
      artifactId: artifactId,
      artifactSha256: artifactSha,
      requestId: requestId,
      filename: filename,
      sourceSha256: sourceSha,
      sizeBytes: size,
      createdAt: createdAt,
      characterCount: characterCount,
      tableCount: tableCount,
      text: text,
      excerpts: excerpts,
      limitations: limitations,
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
    required Sh02Scope scope,
    bool requireOrigin = false,
  }) {
    final projection = _asMap(value);
    if (projection == null ||
        projection['contract'] != 'lumenis.shared.experience-row-projection' ||
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
        !const {
          'writer-authenticated',
          'content-integrity-only',
        }.contains(assurance)) {
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

bool _projectionScopeMatches(Map<String, dynamic> raw, Sh02Scope scope) {
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
  return (domain == scope.domain ||
          (domain == 'ZBMP' && scope.domain == 'BMP')) &&
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
  return RegExp(r'^[a-f0-9]{64}$').hasMatch(digest) ? digest : null;
}

Sh02EvidenceKind _kind(Object? value) =>
    switch (_string(value)?.toUpperCase()) {
      'METRIC' => Sh02EvidenceKind.metric,
      'SOURCE' => Sh02EvidenceKind.source,
      'FINDING' => Sh02EvidenceKind.finding,
      'RISK' => Sh02EvidenceKind.risk,
      'CASE' => Sh02EvidenceKind.caseItem,
      _ => Sh02EvidenceKind.other,
    };

String _freshness(Object? value) => switch (_string(value)?.toUpperCase()) {
  'FRESH' || 'READY' || 'CURRENT' => '已确认新鲜',
  'STALE' => '已标记为过期',
  'NOT_COLLECTED' => '尚未采集',
  'OFFLINE' => '暂时离线',
  _ => '新鲜度未确认',
};

String _lineageLabel(String value) => switch (value.toUpperCase()) {
  'SOURCE' => '来源',
  'EVIDENCE' => '资料依据',
  'CANONICAL' => '正式记录',
  'METRIC' => '指标',
  'EVENT' => '事件',
  _ => '',
};

Map<String, dynamic>? _asMap(Object? value) {
  if (value is! Map) return null;
  return value.map((key, value) => MapEntry('$key', value));
}

String? _string(Object? value) =>
    value is String && value.trim().isNotEmpty ? value.trim() : null;

bool _present(Object? value) => _string(value) != null;

List<String> _strings(Object? value) => value is List
    ? value.map(_string).whereType<String>().toList(growable: false)
    : const [];

String? _safeText(Object? value) {
  final text = _string(value);
  if (text == null || text.length > 180 || RegExp(r'[<>]').hasMatch(text)) {
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
