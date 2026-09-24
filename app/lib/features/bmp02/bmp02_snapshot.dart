enum Bmp02PresentationState {
  global,
  ready,
  empty,
  notCollected,
  stale,
  partial,
  blocked,
  unavailable,
  unknown,
}

class Bmp02Snapshot {
  const Bmp02Snapshot({
    required this.contractBound,
    required this.isBmpOwner,
    required this.dataState,
    required this.focus,
    required this.focusBindingApplied,
    required this.readAllowed,
    required this.globalScopeReady,
    required this.brands,
    required this.rejectedCrossFocusCount,
    required this.rejectedUnscopedCount,
    required this.generatedAt,
  });

  final bool contractBound;
  final bool isBmpOwner;
  final String dataState;
  final Bmp02FocusContext focus;
  final bool focusBindingApplied;
  final bool readAllowed;
  final bool globalScopeReady;
  final List<Bmp02Brand> brands;
  final int rejectedCrossFocusCount;
  final int rejectedUnscopedCount;
  final String? generatedAt;

  bool get hasFocusedBrand =>
      focus.isFocused && focus.brandFocusId != null && focus.brandName != null;

  bool get scopeReady => focus.isGlobal
      ? contractBound && isBmpOwner && globalScopeReady
      : contractBound &&
            isBmpOwner &&
            hasFocusedBrand &&
            focusBindingApplied &&
            readAllowed;

  bool get canDisplayBrands =>
      scopeReady &&
      (dataState == 'READY' ||
          dataState == 'PARTIAL' ||
          dataState == 'STALE') &&
      brands.isNotEmpty;

  Bmp02PresentationState get presentationState {
    if (!contractBound || !isBmpOwner) {
      return Bmp02PresentationState.unavailable;
    }
    if (!scopeReady) return Bmp02PresentationState.blocked;
    return switch (dataState) {
      'READY' =>
        brands.isEmpty
            ? (rejectedUnscopedCount > 0
                  ? Bmp02PresentationState.blocked
                  : Bmp02PresentationState.empty)
            : Bmp02PresentationState.ready,
      'PARTIAL' => Bmp02PresentationState.partial,
      'STALE' =>
        brands.isEmpty
            ? (rejectedUnscopedCount > 0
                  ? Bmp02PresentationState.blocked
                  : Bmp02PresentationState.empty)
            : Bmp02PresentationState.stale,
      'NOT_COLLECTED' => Bmp02PresentationState.notCollected,
      'EMPTY' => Bmp02PresentationState.empty,
      'BLOCKED' => Bmp02PresentationState.blocked,
      _ => Bmp02PresentationState.unknown,
    };
  }

  factory Bmp02Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'BMP-02') {
      throw const FormatException('BMP-02 runtime response is not valid.');
    }

    final truth = _asMap(response['truth']);
    final binding = _asMap(response['focus_binding']);
    final focus = Bmp02FocusContext.fromJson(response['focus_context']);
    final authorization = _scopeAuthorization(
      binding,
      mode: focus.mode,
      domainId: focus.domainId,
      productId: focus.productId,
      subjectId: focus.subjectId,
      brandFocusId: focus.brandFocusId,
    );
    final rawBrands = _sectionItems(response['sections']);
    final accepted = <Bmp02Brand>[];
    var rejectedCrossFocusCount = 0;
    var rejectedUnscopedCount = 0;
    for (final raw in rawBrands) {
      final brand = Bmp02Brand.fromJson(raw);
      if (brand == null) {
        rejectedUnscopedCount++;
        continue;
      }
      if (focus.isGlobal) {
        if (authorization != null &&
            _rowIsAuthorized(raw, focus: focus, authorization: authorization)) {
          accepted.add(brand);
        } else {
          rejectedUnscopedCount++;
        }
        continue;
      }
      if (focus.brandFocusId == null ||
          brand.brandFocusId != focus.brandFocusId) {
        rejectedCrossFocusCount++;
        continue;
      }
      if (authorization != null &&
          _rowIsAuthorized(raw, focus: focus, authorization: authorization)) {
        accepted.add(brand);
      } else {
        rejectedUnscopedCount++;
      }
    }

    final dataState =
        (_asString(truth?['data_state']) ??
                _firstSectionState(response['sections']) ??
                'UNKNOWN')
            .toUpperCase();
    final domainId = (_asString(truth?['domain_id']) ?? '').toLowerCase();
    final productId = (_asString(truth?['product_id']) ?? '').toUpperCase();
    final contractBound =
        response['bound'] == true && response['source'] == 'runtime';
    final isBmpOwner = productId == 'ZBMP' && domainId == 'zbmp';

    return Bmp02Snapshot(
      contractBound: contractBound,
      isBmpOwner: isBmpOwner,
      dataState: dataState,
      focus: focus,
      focusBindingApplied: authorization != null,
      readAllowed: authorization != null,
      globalScopeReady:
          contractBound &&
          isBmpOwner &&
          focus.isGlobal &&
          authorization != null,
      brands: List.unmodifiable(accepted),
      rejectedCrossFocusCount: rejectedCrossFocusCount,
      rejectedUnscopedCount: rejectedUnscopedCount,
      generatedAt: _asString(response['generated_at']),
    );
  }
}

class Bmp02FocusContext {
  const Bmp02FocusContext({
    required this.mode,
    required this.domainId,
    required this.productId,
    required this.subjectId,
    required this.brandFocusId,
    required this.displayName,
  });

  final String mode;
  final String? domainId;
  final String? productId;
  final String? subjectId;
  final String? brandFocusId;
  final Map<String, String> displayName;

  bool get isGlobal =>
      mode == 'GLOBAL_ALL' &&
      domainId == 'BMP' &&
      productId == 'ZBMP' &&
      subjectId == null &&
      brandFocusId == null;

  bool get isFocused =>
      mode == 'FOCUS' &&
      domainId == 'BMP' &&
      productId == 'ZBMP' &&
      subjectId != null &&
      brandFocusId != null &&
      subjectId != brandFocusId;

  String? get brandName => displayName['zh-CN'] ?? displayName['en'];

  String? localizedName(String languageCode) =>
      displayName[languageCode] ?? displayName['en'] ?? displayName['zh-CN'];

  factory Bmp02FocusContext.fromJson(Object? value) {
    final map = _asMap(value);
    final rawDisplayName = _asMap(map?['display_name']);
    final displayName = <String, String>{};
    if (rawDisplayName != null) {
      for (final entry in rawDisplayName.entries) {
        final value = _safeText(entry.value);
        if (value != null) displayName[entry.key] = value;
      }
    }
    return Bmp02FocusContext(
      mode: (_asString(map?['mode']) ?? 'GLOBAL_ALL').toUpperCase(),
      domainId: _asString(map?['domain_id'])?.toUpperCase(),
      productId: _asString(map?['product_id'])?.toUpperCase(),
      subjectId: _asString(map?['subject_id']),
      brandFocusId: _asString(map?['brand_focus_id']),
      displayName: Map.unmodifiable(displayName),
    );
  }
}

class Bmp02Brand {
  const Bmp02Brand({
    required this.id,
    required this.brandFocusId,
    required this.name,
    required this.role,
    required this.roleLabel,
    required this.category,
    required this.health,
    required this.voice,
    required this.positive,
    required this.engagement,
    required this.evidenceReference,
    required this.source,
    required this.timeWindow,
  });

  final String id;
  final String? brandFocusId;
  final String name;
  final String role;
  final Map<String, String> roleLabel;
  final String? category;
  final Bmp02Metric? health;
  final Bmp02Metric? voice;
  final Bmp02Metric? positive;
  final Bmp02Metric? engagement;
  final String evidenceReference;
  final String source;
  final String? timeWindow;

  String localizedRole(String languageCode) =>
      roleLabel[languageCode] ?? roleLabel['en'] ?? role;

  static Bmp02Brand? fromJson(Map<String, Object?> json) {
    final id = _safeText(json['id'] ?? json['brand_id']);
    final rawBrandFocusId = json['brand_focus_id'];
    final brandFocusId = _safeText(rawBrandFocusId);
    final name = _safeText(json['name'] ?? json['title']);
    final role = _normalizeRole(json['role']);
    final evidenceReference = _canonicalEvidenceReference(json['evidence']);
    final source = _safeText(json['source'] ?? json['source_name']);
    if ((json.containsKey('brand_focus_id') &&
            rawBrandFocusId != null &&
            brandFocusId == null) ||
        id == null ||
        name == null ||
        role == null ||
        evidenceReference == null ||
        source == null) {
      return null;
    }
    return Bmp02Brand(
      id: id,
      brandFocusId: brandFocusId,
      name: name,
      role: role,
      roleLabel: _localizedMap(json['role_label']),
      category: _safeText(json['category']),
      health: Bmp02Metric.fromJson(json['health']),
      voice: Bmp02Metric.fromJson(json['voice']),
      positive: Bmp02Metric.fromJson(json['positive']),
      engagement: Bmp02Metric.fromJson(json['engagement']),
      evidenceReference: evidenceReference,
      source: source,
      timeWindow: _safeText(json['time_window']),
    );
  }
}

class Bmp02Metric {
  const Bmp02Metric({
    required this.value,
    required this.unit,
    required this.definition,
    required this.window,
  });

  final num value;
  final String? unit;
  final String? definition;
  final String? window;

  static Bmp02Metric? fromJson(Object? value) {
    final map = _asMap(value);
    final rawValue = map == null ? value : map['value'];
    if (rawValue is! num || !rawValue.isFinite) return null;
    if (rawValue < 0 || rawValue.abs() > 1000000000000) return null;
    return Bmp02Metric(
      value: rawValue,
      unit: _safeText(map?['unit']),
      definition: _safeText(map?['definition']),
      window: _safeText(map?['window']),
    );
  }
}

Map<String, Object?>? _asMap(Object? value) {
  if (value is! Map) return null;
  return value.map((key, value) => MapEntry('$key', value));
}

List<Map<String, Object?>> _sectionItems(Object? sections) {
  if (sections is! List) return const [];
  for (final value in sections) {
    final section = _asMap(value);
    if (section == null) continue;
    final type = _asString(section['type'])?.toLowerCase();
    if (type != 'brands' && type != 'portfolio' && type != 'table') {
      continue;
    }
    final items = section['items'] ?? section['rows'];
    if (items is! List) return const [];
    return items.map(_asMap).whereType<Map<String, Object?>>().toList();
  }
  return const [];
}

String? _firstSectionState(Object? sections) {
  if (sections is! List) return null;
  for (final value in sections) {
    final section = _asMap(value);
    final state = _asString(section?['state']);
    if (state != null) return state;
  }
  return null;
}

class _ScopeAuthorization {
  const _ScopeAuthorization({required this.actorId, required this.scope});

  final int actorId;
  final Map<String, Object?> scope;
}

_ScopeAuthorization? _scopeAuthorization(
  Map<String, Object?>? binding, {
  required String mode,
  required String? domainId,
  required String? productId,
  required String? subjectId,
  required String? brandFocusId,
}) {
  if (binding == null ||
      binding['applied'] != true ||
      binding['read_allowed'] != true ||
      binding['global_all_granted'] is! bool) {
    return null;
  }
  final scope = _canonicalScope(binding['scope']);
  final actorId = _positiveInteger(binding['actor_id']);
  if (scope == null ||
      actorId == null ||
      !_scopeMatchesContext(
        scope,
        mode: mode,
        domainId: domainId,
        productId: productId,
        subjectId: subjectId,
        brandFocusId: brandFocusId,
      ) ||
      !_readPermission(binding['permission'], actorId, scope) ||
      _canonicalEvidence(binding['evidence'], scope) == null) {
    return null;
  }
  final globalGrant = binding['global_all_granted'];
  if (mode == 'GLOBAL_ALL' && globalGrant != true) return null;
  if (mode == 'FOCUS' && globalGrant != false) return null;
  return _ScopeAuthorization(actorId: actorId, scope: scope);
}

bool _rowIsAuthorized(
  Map<String, Object?> row, {
  required Bmp02FocusContext focus,
  required _ScopeAuthorization authorization,
}) {
  final scope = _canonicalScope(row['scope']);
  return scope != null &&
      _sameScope(scope, authorization.scope) &&
      _scopeMatchesContext(
        scope,
        mode: focus.mode,
        domainId: focus.domainId,
        productId: focus.productId,
        subjectId: focus.subjectId,
        brandFocusId: focus.brandFocusId,
      ) &&
      row['read_allowed'] == true &&
      _readPermission(row['permission'], authorization.actorId, scope) &&
      _canonicalEvidence(row['evidence'], scope) != null;
}

Map<String, Object?>? _canonicalScope(Object? value) {
  final scope = _asMap(value);
  const keys = {
    'mode',
    'domain_id',
    'product_id',
    'subject_id',
    'brand_focus_id',
  };
  if (scope == null || scope.length != keys.length || !scope.keys.every(keys.contains)) {
    return null;
  }
  final mode = scope['mode'];
  if (mode != 'GLOBAL_ALL' && mode != 'FOCUS') return null;
  if (scope['domain_id'] != 'BMP' || scope['product_id'] != 'ZBMP') {
    return null;
  }
  if (mode == 'GLOBAL_ALL') {
    return scope['subject_id'] == null && scope['brand_focus_id'] == null
        ? scope
        : null;
  }
  final subjectId = _scopeId(scope['subject_id']);
  final brandFocusId = _scopeId(scope['brand_focus_id']);
  return subjectId != null &&
          brandFocusId != null &&
          subjectId != brandFocusId
      ? scope
      : null;
}

bool _scopeMatchesContext(
  Map<String, Object?> scope, {
  required String mode,
  required String? domainId,
  required String? productId,
  required String? subjectId,
  required String? brandFocusId,
}) =>
    scope['mode'] == mode &&
    scope['domain_id'] == domainId &&
    scope['product_id'] == productId &&
    scope['subject_id'] == subjectId &&
    scope['brand_focus_id'] == brandFocusId;

bool _sameScope(Map<String, Object?> left, Map<String, Object?> right) =>
    const [
      'mode',
      'domain_id',
      'product_id',
      'subject_id',
      'brand_focus_id',
    ].every((key) => left[key] == right[key]);

bool _readPermission(Object? value, int actorId, Map<String, Object?> scope) {
  final permission = _asMap(value);
  final permissionScope = _canonicalScope(permission?['scope']);
  return permission != null &&
      permission['action'] == 'read' &&
      permission['allowed'] == true &&
      permission['verification_state'] == 'verified' &&
      permission['actor_id'] == actorId &&
      permissionScope != null &&
      _sameScope(permissionScope, scope);
}

Map<String, Object?>? _canonicalEvidence(
  Object? value,
  Map<String, Object?> expectedScope,
) {
  final evidence = _asMap(value);
  const keys = {
    'evidence_ref',
    'scope',
    'integrity_version',
    'integrity_algorithm',
    'integrity_key_id',
    'integrity_digest',
    'integrity_verified',
    'integrity_assurance',
  };
  if (evidence == null ||
      evidence.length != keys.length ||
      !evidence.keys.every(keys.contains) ||
      _positiveInteger(evidence['evidence_ref']) == null ||
      evidence['integrity_version'] != 2 ||
      evidence['integrity_verified'] != true ||
      !_sameScope(_canonicalScope(evidence['scope']) ?? const {}, expectedScope)) {
    return null;
  }
  final digest = evidence['integrity_digest'];
  final algorithm = evidence['integrity_algorithm'];
  final assurance = evidence['integrity_assurance'];
  final keyId = evidence['integrity_key_id'];
  if (digest is! String ||
      !RegExp(r'^[0-9a-f]{64}$').hasMatch(digest) ||
      (assurance == 'content-integrity-only' &&
          (algorithm != 'sha256' || keyId != null)) ||
      (assurance == 'writer-authenticated' &&
          (algorithm != 'hmac-sha256' || _scopeId(keyId) == null)) ||
      !const {
        'content-integrity-only',
        'writer-authenticated',
      }.contains(assurance)) {
    return null;
  }
  return evidence;
}

String? _canonicalEvidenceReference(Object? value) {
  final evidence = _asMap(value);
  final reference = _positiveInteger(evidence?['evidence_ref']);
  return reference == null ? null : 'EV-$reference';
}

int? _positiveInteger(Object? value) =>
    value is int && value > 0 ? value : null;

String? _scopeId(Object? value) {
  if (value is! String) return null;
  final text = value.trim();
  return text.isNotEmpty &&
          text == value &&
          text.length <= 120 &&
          RegExp(r'^[A-Za-z0-9][A-Za-z0-9._:-]*$').hasMatch(text)
      ? text
      : null;
}

String? _normalizeRole(Object? value) {
  final role = _asString(value)?.trim().toLowerCase();
  return switch (role) {
    'owned' || 'own' || '自有品牌' => 'owned',
    'sub_brand' || 'sub-brand' || '子品牌' => 'sub_brand',
    'competitor' || '竞品' => 'competitor',
    _ => null,
  };
}

Map<String, String> _localizedMap(Object? value) {
  final map = _asMap(value);
  if (map == null) return const {};
  final result = <String, String>{};
  for (final entry in map.entries) {
    final text = _safeText(entry.value);
    if (text != null) result[entry.key] = text;
  }
  return Map.unmodifiable(result);
}

String? _safeText(Object? value) {
  if (value is! String) return null;
  final text = value.trim();
  if (text.isEmpty || text.length > 160) return null;
  if (RegExp(r'[\x00-\x1F<>]').hasMatch(text)) return null;
  if (RegExp(
    r'\b(core|viewmodel|evidence|owner|scope|contract|provider|runtime|subject|brandfocus|canonical|permission|database|sqlite|api|path|http)\b',
    caseSensitive: false,
  ).hasMatch(text)) {
    return null;
  }
  return text;
}

String? _asString(Object? value) =>
    value is String && value.isNotEmpty ? value : null;
