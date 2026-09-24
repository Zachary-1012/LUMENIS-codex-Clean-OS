class Bmp09Scope {
  const Bmp09Scope({
    required this.mode,
    required this.brandId,
    required this.displayNames,
  });

  final String mode;
  final String? brandId;
  final Map<String, String> displayNames;

  bool get isFocus => mode == 'FOCUS' && brandId != null;
  bool get isGlobal => mode == 'GLOBAL_ALL' && brandId == null;

  String? localizedName(String languageCode) =>
      displayNames[languageCode] ??
      displayNames['en'] ??
      displayNames['zh-CN'] ??
      displayNames['ko'];

  factory Bmp09Scope.fromJson(Object? value) {
    final map = _asMap(value) ?? const <String, Object?>{};
    final rawNames = _asMap(map['display_name'] ?? map['brand_name']);
    final names = <String, String>{};
    for (final entry
        in rawNames?.entries ?? const <MapEntry<String, Object?>>[]) {
      final text = _safeText(entry.value);
      if (text != null) names[entry.key] = text;
    }
    return Bmp09Scope(
      mode: (_asString(map['mode']) ?? 'UNKNOWN').toUpperCase(),
      brandId: _safeId(map['brand_id']),
      displayNames: names,
    );
  }
}

class Bmp09Dimension {
  const Bmp09Dimension({
    required this.name,
    required this.score,
    required this.movement,
    required this.confidence,
    required this.evidenceCoverage,
  });

  final String name;
  final num score;
  final String movement;
  final String confidence;
  final String evidenceCoverage;
}

class Bmp09Report {
  const Bmp09Report({required this.title, required this.period});

  final String title;
  final String period;
}

class Bmp09Snapshot {
  const Bmp09Snapshot({
    required this.contractBound,
    required this.dataState,
    required this.scope,
    required this.scopeApproved,
    required this.dimensions,
    required this.reports,
    required this.grantedPermissions,
  });

  final bool contractBound;
  final String dataState;
  final Bmp09Scope scope;
  final bool scopeApproved;
  final List<Bmp09Dimension> dimensions;
  final List<Bmp09Report> reports;
  final Set<String> grantedPermissions;

  bool get hasMeasuredResults => dimensions.isNotEmpty;

  bool canStage(String permission) =>
      scopeApproved && grantedPermissions.contains(permission);

  factory Bmp09Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'BMP-09') {
      throw const FormatException('BMP-09 runtime response is not valid.');
    }
    final scope = Bmp09Scope.fromJson(
      response['focus_context'] ?? response['scope'],
    );
    final binding = _asMap(response['binding']) ?? const <String, Object?>{};
    final truth = _asMap(response['truth']) ?? const <String, Object?>{};
    final contractBound =
        response['bound'] == true && response['source'] == 'runtime';
    final readContractV2 =
        binding['scope_read_evidence_version'] == 'v2' &&
        binding['evidence_lineage_version'] == 'v2';
    final scopeMatches =
        (_asString(binding['scope_mode'])?.toUpperCase() == scope.mode) &&
        ((scope.isFocus && binding['brand_id'] == scope.brandId) ||
            (scope.isGlobal &&
                binding['brand_id'] == null &&
                binding['global_read'] == 'ALL_GRANTED'));
    final scopeApproved =
        contractBound &&
        readContractV2 &&
        binding['read_access'] == 'ALLOWED' &&
        scopeMatches;
    return Bmp09Snapshot(
      contractBound: contractBound,
      dataState: (_asString(truth['data_state']) ?? 'UNKNOWN').toUpperCase(),
      scope: scope,
      scopeApproved: scopeApproved,
      dimensions: scopeApproved
          ? _dimensions(response['dimensions'], scope)
          : const [],
      reports: scopeApproved ? _reports(response['reports'], scope) : const [],
      grantedPermissions: _asStringList(binding['granted_permissions']).toSet(),
    );
  }
}

List<Bmp09Dimension> _dimensions(Object? value, Bmp09Scope scope) {
  final result = <Bmp09Dimension>[];
  for (final item in _asMapList(value)) {
    final name = _safeText(item['name']);
    final brandId = _safeId(item['brand_id']);
    final score = item['score'];
    final source = _asString(item['source'])?.toLowerCase();
    final evidence = _safeEvidenceRef(item['evidence_ref']);
    final movement = _allowed(item['movement'], const {'UP', 'DOWN', 'FLAT'});
    final confidence = _allowed(item['confidence'], const {
      'HIGH',
      'MEDIUM',
      'LOW',
    });
    final coverage = _allowed(item['evidence_coverage'], const {
      'FULL',
      'PARTIAL',
    });
    final matchesScope = scope.isFocus
        ? brandId == scope.brandId
        : scope.isGlobal && brandId == null && item['scope'] == 'GLOBAL_ALL';
    if (name == null ||
        !matchesScope ||
        score is! num ||
        !score.isFinite ||
        score < 0 ||
        score > 100 ||
        (source != 'actual_result' && source != 'verified_result') ||
        evidence == null ||
        movement == null ||
        confidence == null ||
        coverage == null) {
      continue;
    }
    result.add(
      Bmp09Dimension(
        name: name,
        score: score,
        movement: movement,
        confidence: confidence,
        evidenceCoverage: coverage,
      ),
    );
  }
  return result;
}

List<Bmp09Report> _reports(Object? value, Bmp09Scope scope) {
  final result = <Bmp09Report>[];
  for (final item in _asMapList(value)) {
    final title = _safeText(item['title']);
    final period = _safeText(item['period']);
    final brandId = _safeId(item['brand_id']);
    final evidence = _safeEvidenceRef(item['evidence_ref']);
    final matchesScope = scope.isFocus
        ? brandId == scope.brandId
        : scope.isGlobal && brandId == null && item['scope'] == 'GLOBAL_ALL';
    if (title != null && period != null && matchesScope && evidence != null) {
      result.add(Bmp09Report(title: title, period: period));
    }
  }
  return result;
}

String? _allowed(Object? value, Set<String> allowed) {
  final text = _asString(value)?.trim().toUpperCase();
  return text != null && allowed.contains(text) ? text : null;
}

String? _safeEvidenceRef(Object? value) {
  final text = _asString(value)?.trim();
  return text != null && text.length <= 120 && !_containsInternalWord(text)
      ? text
      : null;
}

String? _safeId(Object? value) {
  final text = _asString(value)?.trim();
  return text != null && text.length <= 120 && !_containsInternalWord(text)
      ? text
      : null;
}

String? _safeText(Object? value) {
  final text = _asString(value)?.trim();
  if (text == null ||
      text.length > 120 ||
      text.contains(RegExp(r'[\r\n]')) ||
      _containsInternalWord(text)) {
    return null;
  }
  return text;
}

bool _containsInternalWord(String value) {
  final normalized = value.toLowerCase();
  return <String>[
    'api',
    'canonical',
    'database',
    'evidence',
    'permission',
    'provider',
    'binding',
    'actor',
    'scope',
    'http',
    'sql',
    'token',
  ].any(normalized.contains);
}

Map<String, Object?>? _asMap(Object? value) {
  if (value is! Map) return null;
  return value.map((key, value) => MapEntry('$key', value));
}

List<Map<String, Object?>> _asMapList(Object? value) {
  if (value is! List) return const [];
  return value.map(_asMap).whereType<Map<String, Object?>>().toList();
}

List<String> _asStringList(Object? value) {
  if (value is! List) return const [];
  return value
      .whereType<String>()
      .map((item) => item.trim())
      .where((item) {
        return item.isNotEmpty &&
            item.length <= 80 &&
            !_containsInternalWord(item);
      })
      .toList(growable: false);
}

String? _asString(Object? value) =>
    value is String && value.isNotEmpty ? value : null;
