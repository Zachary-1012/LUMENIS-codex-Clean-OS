class Bmp10Scope {
  const Bmp10Scope({
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

  factory Bmp10Scope.fromJson(Object? value) {
    final map = _asMap(value) ?? const <String, Object?>{};
    final rawNames = _asMap(map['display_name'] ?? map['brand_name']);
    final names = <String, String>{};
    for (final entry
        in rawNames?.entries ?? const <MapEntry<String, Object?>>[]) {
      final text = _safeText(entry.value);
      if (text != null) names[entry.key] = text;
    }
    return Bmp10Scope(
      mode: (_asString(map['mode']) ?? 'UNKNOWN').toUpperCase(),
      brandId: _safeId(map['brand_id']),
      displayNames: names,
    );
  }
}

class Bmp10Risk {
  const Bmp10Risk({
    required this.title,
    required this.severity,
    required this.recency,
  });

  final String title;
  final String severity;
  final String recency;
}

class Bmp10Event {
  const Bmp10Event({
    required this.title,
    required this.date,
    required this.state,
  });

  final String title;
  final String date;
  final String state;
}

class Bmp10Snapshot {
  const Bmp10Snapshot({
    required this.contractBound,
    required this.dataState,
    required this.scope,
    required this.scopeApproved,
    required this.risks,
    required this.events,
    required this.grantedPermissions,
  });

  final bool contractBound;
  final String dataState;
  final Bmp10Scope scope;
  final bool scopeApproved;
  final List<Bmp10Risk> risks;
  final List<Bmp10Event> events;
  final Set<String> grantedPermissions;

  bool canStage(String permission) =>
      scopeApproved && grantedPermissions.contains(permission);

  factory Bmp10Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'BMP-10') {
      throw const FormatException('BMP-10 runtime response is not valid.');
    }
    final scope = Bmp10Scope.fromJson(
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
    return Bmp10Snapshot(
      contractBound: contractBound,
      dataState: (_asString(truth['data_state']) ?? 'UNKNOWN').toUpperCase(),
      scope: scope,
      scopeApproved: scopeApproved,
      risks: scopeApproved ? _risks(response['risks'], scope) : const [],
      events: scopeApproved ? _events(response['events'], scope) : const [],
      grantedPermissions: _asStringList(binding['granted_permissions']).toSet(),
    );
  }
}

List<Bmp10Risk> _risks(Object? value, Bmp10Scope scope) {
  final result = <Bmp10Risk>[];
  for (final item in _asMapList(value)) {
    final title = _safeText(item['title']);
    final severity = _allowed(item['severity'], const {
      'CRITICAL',
      'HIGH',
      'MEDIUM',
      'LOW',
    });
    final recency = _safeText(item['recency'] ?? item['date']);
    final brandId = _safeId(item['brand_id']);
    final evidence = _safeEvidenceRef(item['evidence_ref']);
    final matchesScope = scope.isFocus
        ? brandId == scope.brandId
        : scope.isGlobal && brandId == null && item['scope'] == 'GLOBAL_ALL';
    if (title != null &&
        severity != null &&
        recency != null &&
        matchesScope &&
        evidence != null) {
      result.add(Bmp10Risk(title: title, severity: severity, recency: recency));
    }
  }
  return result;
}

List<Bmp10Event> _events(Object? value, Bmp10Scope scope) {
  final result = <Bmp10Event>[];
  for (final item in _asMapList(value)) {
    final title = _safeText(item['title']);
    final date = _safeText(item['date']);
    final state = _allowed(item['state'], const {
      'OPEN',
      'MONITORING',
      'RESOLVED',
    });
    final brandId = _safeId(item['brand_id']);
    final evidence = _safeEvidenceRef(item['evidence_ref']);
    final matchesScope = scope.isFocus
        ? brandId == scope.brandId
        : scope.isGlobal && brandId == null && item['scope'] == 'GLOBAL_ALL';
    if (title != null &&
        date != null &&
        state != null &&
        matchesScope &&
        evidence != null) {
      result.add(Bmp10Event(title: title, date: date, state: state));
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
