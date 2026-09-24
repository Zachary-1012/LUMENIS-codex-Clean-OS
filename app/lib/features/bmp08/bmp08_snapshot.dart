class Bmp08Scope {
  const Bmp08Scope({
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

  factory Bmp08Scope.fromJson(Object? value) {
    final map = _asMap(value) ?? const <String, Object?>{};
    final rawNames = _asMap(map['display_name'] ?? map['brand_name']);
    final names = <String, String>{};
    for (final entry
        in rawNames?.entries ?? const <MapEntry<String, Object?>>[]) {
      final text = _safeText(entry.value);
      if (text != null) names[entry.key] = text;
    }
    return Bmp08Scope(
      mode: (_asString(map['mode']) ?? 'UNKNOWN').toUpperCase(),
      brandId: _safeId(map['brand_id']),
      displayNames: names,
    );
  }
}

class Bmp08Material {
  const Bmp08Material({
    required this.name,
    required this.kind,
    required this.brandId,
  });

  final String name;
  final String kind;
  final String? brandId;
}

class Bmp08OutlineSection {
  const Bmp08OutlineSection({
    required this.title,
    required this.timecode,
    required this.hasSource,
  });

  final String title;
  final String timecode;
  final bool hasSource;
}

class Bmp08Snapshot {
  const Bmp08Snapshot({
    required this.contractBound,
    required this.dataState,
    required this.scope,
    required this.scopeApproved,
    required this.audioAvailable,
    required this.versioned,
    required this.rightsReady,
    required this.materials,
    required this.outline,
    required this.grantedPermissions,
  });

  final bool contractBound;
  final String dataState;
  final Bmp08Scope scope;
  final bool scopeApproved;
  final bool audioAvailable;
  final bool versioned;
  final bool rightsReady;
  final List<Bmp08Material> materials;
  final List<Bmp08OutlineSection> outline;
  final Set<String> grantedPermissions;

  bool canStage(String permission) =>
      scopeApproved && grantedPermissions.contains(permission);

  factory Bmp08Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'BMP-08') {
      throw const FormatException('BMP-08 runtime response is not valid.');
    }
    final scope = Bmp08Scope.fromJson(
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
    return Bmp08Snapshot(
      contractBound: contractBound,
      dataState: (_asString(truth['data_state']) ?? 'UNKNOWN').toUpperCase(),
      scope: scope,
      scopeApproved: scopeApproved,
      audioAvailable: scopeApproved && _audio(response['audio'], scope),
      versioned: scopeApproved && response['versioned'] == true,
      rightsReady: scopeApproved && response['rights_ready'] == true,
      materials: scopeApproved
          ? _materials(response['materials'], scope)
          : const [],
      outline: scopeApproved ? _outline(response['outline'], scope) : const [],
      grantedPermissions: _asStringList(binding['granted_permissions']).toSet(),
    );
  }
}

bool _audio(Object? value, Bmp08Scope scope) {
  final map = _asMap(value);
  final brandId = _safeId(map?['brand_id']);
  final matchesScope = scope.isFocus
      ? brandId == scope.brandId
      : scope.isGlobal && brandId == null && map?['scope'] == 'GLOBAL_ALL';
  return map?['available'] == true &&
      matchesScope &&
      _safeEvidenceRef(map?['evidence_ref']) != null;
}

List<Bmp08Material> _materials(Object? value, Bmp08Scope scope) {
  final result = <Bmp08Material>[];
  for (final item in _asMapList(value)) {
    final name = _safeText(item['name'] ?? item['title']);
    final kind = _allowed(item['kind'], const {
      'FILE',
      'BRIEF',
      'AUDIO',
      'TRANSCRIPT',
    });
    final brandId = _safeId(item['brand_id']);
    final evidence = _safeEvidenceRef(item['evidence_ref']);
    final matchesScope = scope.isFocus
        ? brandId == scope.brandId
        : scope.isGlobal && brandId == null && item['scope'] == 'GLOBAL_ALL';
    if (name != null && kind != null && evidence != null && matchesScope) {
      result.add(Bmp08Material(name: name, kind: kind, brandId: brandId));
    }
  }
  return result;
}

List<Bmp08OutlineSection> _outline(Object? value, Bmp08Scope scope) {
  final result = <Bmp08OutlineSection>[];
  for (final item in _asMapList(value)) {
    final title = _safeText(item['title'] ?? item['section']);
    final timecode = _safeText(item['timecode']);
    final brandId = _safeId(item['brand_id']);
    final evidence = _safeEvidenceRef(item['evidence_ref']);
    final matchesScope = scope.isFocus
        ? brandId == scope.brandId
        : scope.isGlobal && brandId == null && item['scope'] == 'GLOBAL_ALL';
    if (title != null && timecode != null && matchesScope && evidence != null) {
      result.add(
        Bmp08OutlineSection(
          title: title,
          timecode: timecode,
          hasSource: _safeEvidenceRef(item['source_evidence_ref']) != null,
        ),
      );
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
