class Bmp07Scope {
  const Bmp07Scope({
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

  factory Bmp07Scope.fromJson(Object? value) {
    final map = _asMap(value) ?? const <String, Object?>{};
    final rawNames = _asMap(map['display_name'] ?? map['brand_name']);
    final names = <String, String>{};
    for (final entry
        in rawNames?.entries ?? const <MapEntry<String, Object?>>[]) {
      final text = _safeText(entry.value);
      if (text != null) names[entry.key] = text;
    }
    return Bmp07Scope(
      mode: (_asString(map['mode']) ?? 'UNKNOWN').toUpperCase(),
      brandId: _safeId(map['brand_id']),
      displayNames: names,
    );
  }
}

class Bmp07Milestone {
  const Bmp07Milestone({
    required this.label,
    required this.date,
    required this.stage,
  });

  final String label;
  final String date;
  final String stage;
}

class Bmp07Channel {
  const Bmp07Channel({
    required this.name,
    required this.planned,
    required this.budgeted,
  });

  final String name;
  final bool planned;
  final bool budgeted;
}

class Bmp07Campaign {
  const Bmp07Campaign({
    required this.goal,
    required this.stage,
    required this.milestones,
    required this.channels,
    required this.plannedRoi,
    required this.actualRoi,
  });

  final String? goal;
  final String stage;
  final List<Bmp07Milestone> milestones;
  final List<Bmp07Channel> channels;
  final num? plannedRoi;
  final num? actualRoi;

  bool get hasActualResult => actualRoi != null;
}

class Bmp07Snapshot {
  const Bmp07Snapshot({
    required this.contractBound,
    required this.dataState,
    required this.scope,
    required this.scopeApproved,
    required this.grantedPermissions,
    required this.campaign,
  });

  final bool contractBound;
  final String dataState;
  final Bmp07Scope scope;
  final bool scopeApproved;
  final Set<String> grantedPermissions;
  final Bmp07Campaign? campaign;

  bool canStage(String permission) =>
      scopeApproved && grantedPermissions.contains(permission);

  factory Bmp07Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'BMP-07') {
      throw const FormatException('BMP-07 runtime response is not valid.');
    }
    final scope = Bmp07Scope.fromJson(
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
    return Bmp07Snapshot(
      contractBound: contractBound,
      dataState: (_asString(truth['data_state']) ?? 'UNKNOWN').toUpperCase(),
      scope: scope,
      scopeApproved: scopeApproved,
      grantedPermissions: _asStringList(binding['granted_permissions']).toSet(),
      campaign: scopeApproved ? _campaign(response['campaign'], scope) : null,
    );
  }
}

Bmp07Campaign? _campaign(Object? value, Bmp07Scope scope) {
  final map = _asMap(value);
  if (map == null) return null;
  final campaignBrandId = _safeId(map['brand_id']);
  final matchesScope = scope.isFocus
      ? campaignBrandId == scope.brandId
      : scope.isGlobal &&
            campaignBrandId == null &&
            map['scope'] == 'GLOBAL_ALL';
  if (!matchesScope) return null;
  final goal = _safeText(map['goal']);
  final stage = _allowed(map['stage'], const {
    'PLANNED',
    'BUDGETED',
    'LAUNCHED',
    'OBSERVED',
    'MEASURED',
  });
  if (stage == null) return null;
  final milestones = <Bmp07Milestone>[];
  for (final item in _asMapList(map['timeline'])) {
    final label = _safeText(item['label']);
    final date = _safeText(item['date']);
    final itemStage = _allowed(item['stage'], const {
      'PLANNED',
      'BUDGETED',
      'LAUNCHED',
      'OBSERVED',
      'MEASURED',
    });
    final brandId = _safeId(item['brand_id']);
    final evidence = _safeEvidenceRef(item['evidence_ref']);
    final matchesItemScope = scope.isFocus
        ? brandId == scope.brandId
        : scope.isGlobal && brandId == null && item['scope'] == 'GLOBAL_ALL';
    if (label != null &&
        date != null &&
        itemStage != null &&
        matchesItemScope &&
        evidence != null) {
      milestones.add(
        Bmp07Milestone(label: label, date: date, stage: itemStage),
      );
    }
  }
  final channels = <Bmp07Channel>[];
  for (final item in _asMapList(map['channels'])) {
    final name = _safeText(item['name']);
    final brandId = _safeId(item['brand_id']);
    final matchesItemScope = scope.isFocus
        ? brandId == scope.brandId
        : scope.isGlobal && brandId == null && item['scope'] == 'GLOBAL_ALL';
    if (name != null && matchesItemScope) {
      channels.add(
        Bmp07Channel(
          name: name,
          planned: item['planned'] == true,
          budgeted: item['budgeted'] == true,
        ),
      );
    }
  }
  final actualResult = map['actual_result'] == true;
  final actualEvidence = _safeEvidenceRef(map['actual_evidence_ref']);
  final rawActualRoi = map['roi'];
  final actualRoi =
      actualResult && actualEvidence != null && rawActualRoi is num
      ? rawActualRoi
      : null;
  final rawPlannedRoi = map['planned_roi'];
  return Bmp07Campaign(
    goal: goal,
    stage: stage,
    milestones: milestones,
    channels: channels,
    plannedRoi: rawPlannedRoi is num ? rawPlannedRoi : null,
    actualRoi: actualRoi,
  );
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
