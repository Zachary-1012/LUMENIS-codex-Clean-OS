enum Sh04ScopeMode { globalAll, focus }

enum Sh04ScopeErrorKind { unavailable, denied, malformed }

class Sh04ScopeError implements Exception {
  const Sh04ScopeError(this.kind);

  final Sh04ScopeErrorKind kind;
}

class Sh04Scope {
  const Sh04Scope({
    required this.mode,
    required this.domain,
    required this.focusId,
    required this.displayName,
  });

  final Sh04ScopeMode mode;
  final String? domain;
  final String? focusId;
  final String displayName;

  bool get isGlobal => mode == Sh04ScopeMode.globalAll;

  String get businessDomain => switch (domain) {
    'CTH' => '商业运营',
    'BMP' => '品牌市场',
    _ => '全部范围',
  };

  static Sh04Scope fromResponse(Map<String, dynamic> response) {
    final rawScope = _asMap(response['scope'] ?? response['context']);
    final permission = _asMap(
      response['permission'] ?? response['authorization'],
    );
    if (rawScope == null || permission == null) {
      throw const Sh04ScopeError(Sh04ScopeErrorKind.unavailable);
    }
    if (response['selection_only'] == true ||
        rawScope['selection_only'] == true) {
      throw const Sh04ScopeError(Sh04ScopeErrorKind.unavailable);
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
      throw const Sh04ScopeError(Sh04ScopeErrorKind.denied);
    }
    final mode = _string(
      rawScope['mode'] ?? rawScope['scope_mode'],
    )?.toUpperCase();
    if (mode == 'GLOBAL_ALL') {
      if (_present(rawScope['subject_id']) ||
          _present(rawScope['brand_focus_id']) ||
          rawScope['global'] == false) {
        throw const Sh04ScopeError(Sh04ScopeErrorKind.malformed);
      }
      return const Sh04Scope(
        mode: Sh04ScopeMode.globalAll,
        domain: null,
        focusId: null,
        displayName: '全部范围',
      );
    }
    if (mode != 'FOCUS') {
      throw const Sh04ScopeError(Sh04ScopeErrorKind.malformed);
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
      throw const Sh04ScopeError(Sh04ScopeErrorKind.malformed);
    }
    return Sh04Scope(
      mode: Sh04ScopeMode.focus,
      domain: domain == 'ZBMP' ? 'BMP' : domain,
      focusId: focusId,
      displayName: displayName,
    );
  }
}

enum Sh04ExportState { draft, generating, ready, failed, unavailable }

enum Sh04Format { markdown, csv, pdf, excel, powerpoint, unknown }

class Sh04Export {
  const Sh04Export({
    required this.internalId,
    required this.title,
    required this.format,
    required this.state,
    required this.scopeVerified,
    required this.reopenable,
    required this.preview,
    required this.evidenceCount,
    required this.generatedAt,
    required this.failureReason,
    this.savedWork,
  });

  final String internalId;
  final String title;
  final Sh04Format format;
  final Sh04ExportState state;
  final bool scopeVerified;
  final bool reopenable;
  final String preview;
  final int? evidenceCount;
  final String generatedAt;
  final String failureReason;
  final Sh04SavedWork? savedWork;

  String get stateLabel => switch (state) {
    Sh04ExportState.draft => '草稿',
    Sh04ExportState.generating => '生成中',
    Sh04ExportState.ready => '已生成',
    Sh04ExportState.failed => '生成失败',
    Sh04ExportState.unavailable => '暂不可用',
  };

  String get formatLabel => switch (format) {
    Sh04Format.markdown => 'Markdown',
    Sh04Format.csv => 'CSV',
    Sh04Format.pdf => 'PDF',
    Sh04Format.excel => 'Excel',
    Sh04Format.powerpoint => 'PPT',
    Sh04Format.unknown => '格式未确认',
  };

  static Sh04Export? tryParse(Object? value, {required Sh04Scope scope}) {
    final record = _asMap(value);
    if (record == null) return null;
    final internalId = _string(
      record['id'] ?? record['report_id'] ?? record['export_id'],
    );
    final title = _safeText(
      record['title'] ?? record['report'] ?? record['name'],
    );
    if (internalId == null || title == null) return null;
    final artifact = _asMap(record['artifact'] ?? record['persistence']);
    final projection = _SharedProjection.tryParse(
      record['projection'],
      scope: scope,
    );
    if (projection == null) return null;
    final state = _state(record['state'] ?? record['status']);
    final reopenable =
        state == Sh04ExportState.ready && artifact?['reopenable'] == true;
    final preview = reopenable
        ? _safeText(
                record['preview'] ?? artifact?['preview'] ?? record['content'],
              ) ??
              ''
        : '';
    return Sh04Export(
      internalId: internalId,
      title: title,
      format: _format(record['format'] ?? record['file_format']),
      state: state == Sh04ExportState.ready && !reopenable
          ? Sh04ExportState.unavailable
          : state,
      scopeVerified: true,
      reopenable: reopenable,
      preview: preview,
      evidenceCount: _nonNegativeInt(
        record['evidence_count'] ?? record['source_trace_count'],
      ),
      generatedAt:
          _safeText(record['generated_at'] ?? record['created_at']) ?? '',
      failureReason:
          _safeText(record['failure_reason'] ?? record['error_message']) ?? '',
    );
  }
}

/// A validated immutable SavedWork record. List rows have [committed] false
/// until a fresh reopen response carries a matching committed-work receipt.
class Sh04SavedWork {
  Sh04SavedWork({
    required this.artifactId,
    required this.domainId,
    required this.hash,
    required this.sizeBytes,
    required this.workId,
    required this.version,
    required this.title,
    required this.markdown,
    required this.kind,
    required this.createdAt,
    required this.parentArtifactId,
    required this.parentSha256,
    required this.draftDigest,
    required this.taskId,
    required this.contractId,
    required this.contractVersion,
    required List<Map<String, dynamic>> citations,
    required List<Map<String, dynamic>> sources,
    required Map<String, dynamic> document,
    required Map<String, dynamic> returnScope,
    required this.committed,
  }) : citations = List<Map<String, dynamic>>.unmodifiable(
         citations.map(_freezeMap),
       ),
       sources = List<Map<String, dynamic>>.unmodifiable(
         sources.map(_freezeMap),
       ),
       document = _freezeMap(document),
       returnScope = _freezeMap(returnScope);

  final String artifactId;

  /// Public API domain (`CTH` or `BMP`), retained for Core export calls.
  final String domainId;
  final String hash;
  final int sizeBytes;
  final String workId;
  final int version;
  final String title;
  final String markdown;
  final String kind;
  final String createdAt;
  final String? parentArtifactId;
  final String? parentSha256;
  final String draftDigest;
  final String? taskId;
  final String contractId;
  final String contractVersion;
  final List<Map<String, dynamic>> citations;

  /// Receipt sources are shown only after a successful fresh reopen.
  final List<Map<String, dynamic>> sources;
  final Map<String, dynamic> document;
  final Map<String, dynamic> returnScope;
  final bool committed;
}

class Sh04Snapshot {
  Sh04Snapshot({
    required this.scope,
    required List<Sh04Export> exports,
    List<String> failedDomains = const <String>[],
    this.incomplete = false,
    this.hasMore = false,
    Map<String, String?> cursors = const <String, String?>{},
    Map<String, bool> hasMoreByDomain = const <String, bool>{},
    this.query = '',
    this.contextSignature,
  }) : exports = List<Sh04Export>.unmodifiable(exports),
       failedDomains = List<String>.unmodifiable(failedDomains),
       cursors = Map<String, String?>.unmodifiable(cursors),
       hasMoreByDomain = Map<String, bool>.unmodifiable(hasMoreByDomain);

  final Sh04Scope scope;
  final List<Sh04Export> exports;
  final List<String> failedDomains;
  final bool incomplete;
  final bool hasMore;
  final Map<String, String?> cursors;
  final Map<String, bool> hasMoreByDomain;
  final String query;
  final String? contextSignature;

  factory Sh04Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'SH-04') {
      throw const FormatException('SH-04 response identity is invalid.');
    }
    if (response['bound'] != true || response['source'] != 'runtime') {
      throw const FormatException('SH-04 runtime binding is unavailable.');
    }
    final scope = Sh04Scope.fromResponse(response);
    final data = _asMap(response['data']);
    if (data == null) {
      throw const FormatException('SH-04 data envelope is incomplete.');
    }
    final rawExports = data['exports'] ?? data['artifacts'];
    if (rawExports is! List) {
      throw const FormatException('SH-04 export list is unavailable.');
    }
    return Sh04Snapshot(
      scope: scope,
      exports: rawExports
          .map((item) => Sh04Export.tryParse(item, scope: scope))
          .whereType<Sh04Export>()
          .toList(growable: false),
    );
  }
}

Sh04ExportState _state(Object? value) =>
    switch (_string(value)?.toUpperCase()) {
      'DRAFT' || 'PENDING' => Sh04ExportState.draft,
      'GENERATING' || 'RUNNING' => Sh04ExportState.generating,
      'READY' || 'AVAILABLE' || 'COMPLETED' => Sh04ExportState.ready,
      'FAILED' || 'ERROR' => Sh04ExportState.failed,
      _ => Sh04ExportState.unavailable,
    };

Sh04Format _format(Object? value) => switch (_string(value)?.toLowerCase()) {
  'markdown' || 'md' => Sh04Format.markdown,
  'csv' => Sh04Format.csv,
  'pdf' => Sh04Format.pdf,
  'excel' || 'xlsx' || 'xls' => Sh04Format.excel,
  'ppt' || 'pptx' || 'powerpoint' => Sh04Format.powerpoint,
  _ => Sh04Format.unknown,
};

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
    required Sh04Scope scope,
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

bool _projectionScopeMatches(Map<String, dynamic> raw, Sh04Scope scope) {
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

Map<String, dynamic>? _asMap(Object? value) {
  if (value is! Map) return null;
  return value.map((key, value) => MapEntry('$key', value));
}

Map<String, dynamic> _freezeMap(Map<String, dynamic> value) =>
    Map<String, dynamic>.unmodifiable(
      value.map((key, value) => MapEntry(key, _freezeJson(value))),
    );

Object? _freezeJson(Object? value) {
  if (value is Map) {
    final result = <String, dynamic>{};
    for (final entry in value.entries) {
      if (entry.key is! String) {
        throw const FormatException('SavedWork JSON has a non-string key.');
      }
      result[entry.key as String] = _freezeJson(entry.value);
    }
    return Map<String, dynamic>.unmodifiable(result);
  }
  if (value is List) {
    return List<Object?>.unmodifiable(value.map(_freezeJson));
  }
  if (value is num && !value.isFinite) {
    throw const FormatException('SavedWork JSON has a non-finite number.');
  }
  if (value == null || value is String || value is bool || value is num) {
    return value;
  }
  throw const FormatException('SavedWork JSON has an unsupported value.');
}

String? _string(Object? value) =>
    value is String && value.trim().isNotEmpty ? value.trim() : null;

bool _present(Object? value) => _string(value) != null;

int? _nonNegativeInt(Object? value) =>
    value is int && value >= 0 ? value : null;

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
