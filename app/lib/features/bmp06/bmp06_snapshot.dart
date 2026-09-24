class Bmp06Scope {
  const Bmp06Scope({
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

  factory Bmp06Scope.fromJson(Object? value) {
    final map = _asMap(value) ?? const <String, Object?>{};
    final rawNames = _asMap(map['display_name'] ?? map['brand_name']);
    final names = <String, String>{};
    for (final entry
        in rawNames?.entries ?? const <MapEntry<String, Object?>>[]) {
      final text = _safeText(entry.value);
      if (text != null) names[entry.key] = text;
    }
    return Bmp06Scope(
      mode: (_asString(map['mode']) ?? 'UNKNOWN').toUpperCase(),
      brandId: _safeId(map['brand_id'] ?? map['subject_id']),
      displayNames: names,
    );
  }
}

class Bmp06Asset {
  const Bmp06Asset({
    required this.id,
    required this.title,
    required this.kind,
    required this.state,
    required this.approval,
    required this.brandId,
  });

  final String id;
  final String title;
  final String kind;
  final String state;
  final String approval;
  final String? brandId;
}

class Bmp06Snapshot {
  const Bmp06Snapshot({
    required this.contractBound,
    required this.dataState,
    required this.scope,
    required this.scopeVerified,
    required this.permissionGranted,
    required this.evidenceLineageVerified,
    required this.globalAllGranted,
    required this.grantedPermissions,
    required this.assets,
  });

  final bool contractBound;
  final String dataState;
  final Bmp06Scope scope;
  final bool scopeVerified;
  final bool permissionGranted;
  final bool evidenceLineageVerified;
  final bool globalAllGranted;
  final Set<String> grantedPermissions;
  final List<Bmp06Asset> assets;

  bool get isScopeApproved =>
      contractBound &&
      scopeVerified &&
      permissionGranted &&
      evidenceLineageVerified &&
      ((scope.isFocus && scope.brandId != null) ||
          (scope.isGlobal && globalAllGranted));

  bool canStage(String permission) =>
      isScopeApproved && grantedPermissions.contains(permission);

  factory Bmp06Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'BMP-06') {
      throw const FormatException('BMP-06 runtime response is not valid.');
    }

    final scope = Bmp06Scope.fromJson(
      response['focus_context'] ?? response['scope'],
    );
    final binding = _asMap(response['binding']) ?? const <String, Object?>{};
    final truth = _asMap(response['truth']) ?? const <String, Object?>{};
    final readContractV2 =
        binding['scope_read_evidence_version'] == 'v2' &&
        binding['evidence_lineage_version'] == 'v2';
    final scopeMatches =
        (_asString(binding['scope_mode'])?.toUpperCase() == scope.mode) &&
        ((scope.isFocus && binding['brand_id'] == scope.brandId) ||
            (scope.isGlobal &&
                binding['brand_id'] == null &&
                binding['global_read'] == 'ALL_GRANTED'));
    final scopeVerified = readContractV2 && scopeMatches;
    final permissionGranted = binding['read_access'] == 'ALLOWED';
    final evidenceLineageVerified = readContractV2;
    final globalAllGranted = binding['global_read'] == 'ALL_GRANTED';
    final permissions = _asStringList(binding['granted_permissions']);
    final contractBound =
        response['bound'] == true && response['source'] == 'runtime';
    final approved =
        contractBound &&
        scopeVerified &&
        permissionGranted &&
        evidenceLineageVerified &&
        ((scope.isFocus && scope.brandId != null) ||
            (scope.isGlobal && globalAllGranted));

    return Bmp06Snapshot(
      contractBound: contractBound,
      dataState: (_asString(truth['data_state']) ?? 'UNKNOWN').toUpperCase(),
      scope: scope,
      scopeVerified: scopeVerified,
      permissionGranted: permissionGranted,
      evidenceLineageVerified: evidenceLineageVerified,
      globalAllGranted: globalAllGranted,
      grantedPermissions: permissions.toSet(),
      assets: approved ? _assets(response['assets'], scope) : const [],
    );
  }
}

List<Bmp06Asset> _assets(Object? value, Bmp06Scope scope) {
  final result = <Bmp06Asset>[];
  for (final item in _asMapList(value)) {
    final id = _safeId(item['id']);
    final title = _safeText(item['title']);
    final kind = _allowed(item['kind'], const {
      'BRIEF',
      'DRAFT',
      'VIDEO',
      'IMAGE',
      'COPY',
    });
    final state = _allowed(item['state'], const {
      'BRIEF',
      'DRAFT',
      'REVIEW',
      'APPROVED',
      'SCHEDULED',
      'DELIVERED',
    });
    final approval = _allowed(item['approval'], const {
      'NOT_REQUESTED',
      'PENDING',
      'APPROVED',
      'REJECTED',
    });
    final evidenceRef = _safeEvidenceRef(item['evidence_ref']);
    final brandId = _safeId(item['brand_id']);
    final matchesScope = scope.isFocus
        ? brandId == scope.brandId
        : scope.isGlobal && brandId == null && item['scope'] == 'GLOBAL_ALL';
    if (id == null ||
        title == null ||
        kind == null ||
        state == null ||
        approval == null ||
        evidenceRef == null ||
        !matchesScope) {
      continue;
    }
    result.add(
      Bmp06Asset(
        id: id,
        title: title,
        kind: kind,
        state: state,
        approval: approval,
        brandId: brandId,
      ),
    );
  }
  return result;
}

String? _allowed(Object? value, Set<String> allowed) {
  final text = _asString(value)?.trim().toUpperCase();
  return text != null && allowed.contains(text) ? text : null;
}

String? _safeEvidenceRef(Object? value) {
  final text = _asString(value)?.trim();
  if (text == null || text.length > 120 || _containsInternalWord(text)) {
    return null;
  }
  return text;
}

String? _safeId(Object? value) {
  final text = _asString(value)?.trim();
  if (text == null || text.length > 120 || _containsInternalWord(text)) {
    return null;
  }
  return text;
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
