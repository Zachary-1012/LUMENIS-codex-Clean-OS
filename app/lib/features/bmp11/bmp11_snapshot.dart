class Bmp11Scope {
  const Bmp11Scope({
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

  factory Bmp11Scope.fromJson(Object? value) {
    final map = _asMap(value) ?? const <String, Object?>{};
    final rawNames = _asMap(map['display_name'] ?? map['brand_name']);
    final names = <String, String>{};
    for (final entry
        in rawNames?.entries ?? const <MapEntry<String, Object?>>[]) {
      final text = _safeText(entry.value);
      if (text != null) names[entry.key] = text;
    }
    return Bmp11Scope(
      mode: (_asString(map['mode']) ?? 'UNKNOWN').toUpperCase(),
      brandId: _safeId(map['brand_id']),
      displayNames: names,
    );
  }
}

class Bmp11Competitor {
  const Bmp11Competitor({
    required this.brandId,
    required this.name,
    required this.value,
    required this.comparable,
  });

  final String brandId;
  final String name;
  final num value;
  final bool comparable;
}

class Bmp11BenchmarkRow {
  const Bmp11BenchmarkRow({
    required this.dimension,
    required this.definition,
    required this.selfValue,
    required this.competitors,
    required this.comparable,
  });

  final String dimension;
  final String definition;
  final num selfValue;
  final List<Bmp11Competitor> competitors;
  final bool comparable;

  bool get hasComparableCompetitors =>
      comparable && competitors.any((competitor) => competitor.comparable);
}

class Bmp11Snapshot {
  const Bmp11Snapshot({
    required this.contractBound,
    required this.dataState,
    required this.scope,
    required this.scopeApproved,
    required this.rows,
  });

  final bool contractBound;
  final String dataState;
  final Bmp11Scope scope;
  final bool scopeApproved;
  final List<Bmp11BenchmarkRow> rows;

  bool get hasComparableRows => rows.any((row) => row.hasComparableCompetitors);

  factory Bmp11Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'BMP-11') {
      throw const FormatException('BMP-11 runtime response is not valid.');
    }
    final scope = Bmp11Scope.fromJson(
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
    return Bmp11Snapshot(
      contractBound: contractBound,
      dataState: (_asString(truth['data_state']) ?? 'UNKNOWN').toUpperCase(),
      scope: scope,
      scopeApproved: scopeApproved,
      rows: scopeApproved ? _rows(response['rows'], scope) : const [],
    );
  }
}

List<Bmp11BenchmarkRow> _rows(Object? value, Bmp11Scope scope) {
  final result = <Bmp11BenchmarkRow>[];
  for (final item in _asMapList(value)) {
    final dimension = _safeText(item['dimension'] ?? item['name']);
    final definition = _safeText(
      item['definition'] ?? item['metric_definition'],
    );
    final selfValue = item['self'] ?? item['self_value'];
    final comparable = item['comparable'];
    final evidence = _safeEvidenceRef(item['evidence_ref']);
    final rowBrandId = _safeId(item['brand_id']);
    final competitors = _competitors(item['competitors'], definition);
    final rowIsInScope = scope.isFocus
        ? rowBrandId == scope.brandId
        : rowBrandId == null && item['scope_mode'] == 'GLOBAL_ALL';
    if (dimension == null ||
        definition == null ||
        selfValue is! num ||
        !selfValue.isFinite ||
        comparable is! bool ||
        evidence == null ||
        !rowIsInScope ||
        competitors.isEmpty) {
      continue;
    }
    result.add(
      Bmp11BenchmarkRow(
        dimension: dimension,
        definition: definition,
        selfValue: selfValue,
        competitors: competitors,
        comparable: comparable,
      ),
    );
  }
  return result;
}

List<Bmp11Competitor> _competitors(Object? value, String? definition) {
  final result = <Bmp11Competitor>[];
  for (final item in _asMapList(value)) {
    final brandId = _safeId(item['brand_id'] ?? item['competitor_brand_id']);
    final name = _safeText(item['name'] ?? item['brand_name']);
    final metricDefinition = _safeText(
      item['definition'] ?? item['metric_definition'],
    );
    final number = item['value'];
    final comparable = item['comparable'];
    final evidence = _safeEvidenceRef(item['evidence_ref']);
    if (brandId == null ||
        name == null ||
        metricDefinition != definition ||
        number is! num ||
        !number.isFinite ||
        comparable is! bool ||
        evidence == null) {
      continue;
    }
    result.add(
      Bmp11Competitor(
        brandId: brandId,
        name: name,
        value: number,
        comparable: comparable,
      ),
    );
  }
  return result;
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
      text.length > 160 ||
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

String? _asString(Object? value) =>
    value is String && value.isNotEmpty ? value : null;
