enum Sh03ScopeMode { globalAll, focus }

enum Sh03ScopeErrorKind { unavailable, denied, malformed }

class Sh03ScopeError implements Exception {
  const Sh03ScopeError(this.kind);

  final Sh03ScopeErrorKind kind;
}

class Sh03Scope {
  const Sh03Scope({
    required this.mode,
    required this.domain,
    required this.focusId,
    required this.displayName,
  });

  final Sh03ScopeMode mode;
  final String? domain;
  final String? focusId;
  final String displayName;

  bool get isGlobal => mode == Sh03ScopeMode.globalAll;

  String get businessDomain => switch (domain) {
    'CTH' => '商业运营',
    'BMP' => '品牌市场',
    _ => '全部范围',
  };

  static Sh03Scope fromResponse(Map<String, dynamic> response) {
    final rawScope = _asMap(response['scope'] ?? response['context']);
    final permission = _asMap(
      response['permission'] ?? response['authorization'],
    );
    if (rawScope == null || permission == null) {
      throw const Sh03ScopeError(Sh03ScopeErrorKind.unavailable);
    }
    if (response['selection_only'] == true ||
        rawScope['selection_only'] == true) {
      throw const Sh03ScopeError(Sh03ScopeErrorKind.unavailable);
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
      throw const Sh03ScopeError(Sh03ScopeErrorKind.denied);
    }
    final mode = _string(
      rawScope['mode'] ?? rawScope['scope_mode'],
    )?.toUpperCase();
    if (mode == 'GLOBAL_ALL') {
      if (_present(rawScope['subject_id']) ||
          _present(rawScope['brand_focus_id']) ||
          rawScope['global'] == false) {
        throw const Sh03ScopeError(Sh03ScopeErrorKind.malformed);
      }
      return const Sh03Scope(
        mode: Sh03ScopeMode.globalAll,
        domain: null,
        focusId: null,
        displayName: '全部范围',
      );
    }
    if (mode != 'FOCUS') {
      throw const Sh03ScopeError(Sh03ScopeErrorKind.malformed);
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
      throw const Sh03ScopeError(Sh03ScopeErrorKind.malformed);
    }
    return Sh03Scope(
      mode: Sh03ScopeMode.focus,
      domain: domain == 'ZBMP' ? 'BMP' : domain,
      focusId: focusId,
      displayName: displayName,
    );
  }
}

enum Sh03MetricState { ready, partial, stale, notCollected, unavailable }

class Sh03Sample {
  const Sh03Sample({
    required this.label,
    required this.value,
    required this.time,
  });

  final String label;
  final String value;
  final String time;

  static Sh03Sample? tryParse(Object? value) {
    final record = _asMap(value);
    if (record == null) return null;
    final label = _safeText(record['label'] ?? record['name']);
    final sampleValue = _safeText(record['value'] ?? record['display_value']);
    if (label == null || sampleValue == null) return null;
    return Sh03Sample(
      label: label,
      value: sampleValue,
      time: _safeText(record['time'] ?? record['captured_at']) ?? '',
    );
  }
}

class Sh03Metric {
  const Sh03Metric({
    required this.internalName,
    required this.name,
    required this.definition,
    required this.cadence,
    required this.state,
    required this.derived,
    required this.lineage,
    required this.samples,
  });

  final String internalName;
  final String name;
  final String definition;
  final String cadence;
  final Sh03MetricState state;
  final bool derived;
  final List<String> lineage;
  final List<Sh03Sample> samples;

  String get stateLabel => switch (state) {
    Sh03MetricState.ready => '已确认',
    Sh03MetricState.partial => '部分确认',
    Sh03MetricState.stale => '已标记为过期',
    Sh03MetricState.notCollected => '尚未采集',
    Sh03MetricState.unavailable => '暂不可用',
  };

  static Sh03Metric? tryParse(Object? value, {required Sh03Scope scope}) {
    final record = _asMap(value);
    if (record == null) return null;
    final internalName = _string(
      record['name'] ?? record['metric_id'] ?? record['id'],
    );
    final name = _safeText(
      record['display_name'] ?? record['label'] ?? record['title'],
    );
    final definition = _safeText(record['definition'] ?? record['description']);
    if (internalName == null || name == null || definition == null) return null;
    if (_SharedProjection.tryParse(record['projection'], scope: scope) == null) {
      return null;
    }
    final rawSamples = record['samples'] ?? record['sample_records'];
    return Sh03Metric(
      internalName: internalName,
      name: name,
      definition: definition,
      cadence: _safeText(record['cadence'] ?? record['updated']) ?? '更新频率未确认',
      state: _state(record['state'] ?? record['status']),
      derived:
          record['derived'] == true ||
          _string(record['kind'])?.toUpperCase() == 'DERIVED',
      lineage: _lineage(record['lineage']),
      samples: rawSamples is List
          ? rawSamples
                .map(Sh03Sample.tryParse)
                .whereType<Sh03Sample>()
                .toList(growable: false)
          : const [],
    );
  }
}

class Sh03Snapshot {
  const Sh03Snapshot({required this.scope, required this.metrics});

  final Sh03Scope scope;
  final List<Sh03Metric> metrics;

  factory Sh03Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'SH-03') {
      throw const FormatException('SH-03 response identity is invalid.');
    }
    if (response['bound'] != true || response['source'] != 'runtime') {
      throw const FormatException('SH-03 runtime binding is unavailable.');
    }
    final scope = Sh03Scope.fromResponse(response);
    final data = _asMap(response['data']);
    if (data == null) {
      throw const FormatException('SH-03 data envelope is incomplete.');
    }
    final rawMetrics = data['metrics'];
    if (rawMetrics is! List) {
      throw const FormatException('SH-03 metric list is unavailable.');
    }
    return Sh03Snapshot(
      scope: scope,
      metrics: rawMetrics
          .map((item) => Sh03Metric.tryParse(item, scope: scope))
          .whereType<Sh03Metric>()
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
    required Sh03Scope scope,
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

bool _projectionScopeMatches(Map<String, dynamic> raw, Sh03Scope scope) {
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

Sh03MetricState _state(Object? value) =>
    switch (_string(value)?.toUpperCase()) {
      'READY' || 'OK' || 'CONFIRMED' => Sh03MetricState.ready,
      'PARTIAL' => Sh03MetricState.partial,
      'STALE' => Sh03MetricState.stale,
      'NOT_COLLECTED' => Sh03MetricState.notCollected,
      _ => Sh03MetricState.unavailable,
    };

List<String> _lineage(Object? value) => value is List
    ? value
          .map(_string)
          .whereType<String>()
          .map(_lineageLabel)
          .where((item) => item.isNotEmpty)
          .toList(growable: false)
    : const [];

String _lineageLabel(String value) => switch (value.toUpperCase()) {
  'SOURCE' => '来源',
  'EVIDENCE' => '资料依据',
  'CANONICAL' => '正式记录',
  'METRIC' => '指标',
  'VIEW' || 'VIEWMODEL' => '查看结果',
  _ => '',
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
