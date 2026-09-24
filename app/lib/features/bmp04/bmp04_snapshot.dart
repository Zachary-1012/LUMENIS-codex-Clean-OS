enum Bmp04PresentationState {
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

class Bmp04Snapshot {
  const Bmp04Snapshot({
    required this.contractBound,
    required this.isBmpOwner,
    required this.dataState,
    required this.focus,
    required this.focusBindingApplied,
    required this.readAllowed,
    required this.globalScopeReady,
    required this.channels,
    required this.rejectedCrossFocusCount,
    required this.rejectedUnscopedCount,
  });

  final bool contractBound;
  final bool isBmpOwner;
  final String dataState;
  final Bmp04FocusContext focus;
  final bool focusBindingApplied;
  final bool readAllowed;
  final bool globalScopeReady;
  final List<Bmp04Channel> channels;
  final int rejectedCrossFocusCount;
  final int rejectedUnscopedCount;

  bool get scopeReady => focus.isGlobal
      ? contractBound && isBmpOwner && globalScopeReady
      : contractBound &&
            isBmpOwner &&
            focus.isFocused &&
            focus.brandFocusId != null &&
            focusBindingApplied &&
            readAllowed;

  Bmp04PresentationState get presentationState {
    if (!contractBound || !isBmpOwner) {
      return Bmp04PresentationState.unavailable;
    }
    if (!scopeReady) return Bmp04PresentationState.blocked;
    return switch (dataState) {
      'READY' =>
        channels.isEmpty
            ? (rejectedUnscopedCount > 0
                  ? Bmp04PresentationState.blocked
                  : Bmp04PresentationState.empty)
            : Bmp04PresentationState.ready,
      'PARTIAL' => Bmp04PresentationState.partial,
      'STALE' =>
        channels.isEmpty
            ? (rejectedUnscopedCount > 0
                  ? Bmp04PresentationState.blocked
                  : Bmp04PresentationState.empty)
            : Bmp04PresentationState.stale,
      'NOT_COLLECTED' => Bmp04PresentationState.notCollected,
      'EMPTY' => Bmp04PresentationState.empty,
      'BLOCKED' => Bmp04PresentationState.blocked,
      _ => Bmp04PresentationState.unknown,
    };
  }

  factory Bmp04Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'BMP-04') {
      throw const FormatException('BMP-04 runtime response is not valid.');
    }
    final truth = _asMap(response['truth']);
    final binding = _asMap(response['focus_binding']);
    final focus = Bmp04FocusContext.fromJson(response['focus_context']);
    final authorization = _scopeAuthorization(
      binding,
      mode: focus.mode,
      domainId: focus.domainId,
      productId: focus.productId,
      subjectId: focus.subjectId,
      brandFocusId: focus.brandFocusId,
    );
    final rawChannels = _sectionItems(response['sections']);
    final channels = <Bmp04Channel>[];
    var rejectedCrossFocusCount = 0;
    var rejectedUnscopedCount = 0;
    for (final raw in rawChannels) {
      final channel = Bmp04Channel.fromJson(raw);
      if (channel == null) {
        rejectedUnscopedCount++;
      } else if (focus.isGlobal) {
        if (authorization != null &&
            _rowIsAuthorized(raw, focus: focus, authorization: authorization)) {
          channels.add(channel);
        } else {
          rejectedUnscopedCount++;
        }
      } else if (focus.brandFocusId == null ||
          channel.brandFocusId != focus.brandFocusId) {
        rejectedCrossFocusCount++;
      } else if (authorization != null &&
          _rowIsAuthorized(raw, focus: focus, authorization: authorization)) {
        channels.add(channel);
      } else {
        rejectedUnscopedCount++;
      }
    }
    final contractBound =
        response['bound'] == true && response['source'] == 'runtime';
    final isBmpOwner =
        (_asString(truth?['product_id']) ?? '').toUpperCase() == 'ZBMP' &&
        (_asString(truth?['domain_id']) ?? '').toLowerCase() == 'zbmp';
    return Bmp04Snapshot(
      contractBound: contractBound,
      isBmpOwner: isBmpOwner,
      dataState:
          (_asString(truth?['data_state']) ??
                  _firstSectionState(response['sections']) ??
                  'UNKNOWN')
              .toUpperCase(),
      focus: focus,
      focusBindingApplied: authorization != null,
      readAllowed: authorization != null,
      globalScopeReady:
          contractBound &&
          isBmpOwner &&
          focus.isGlobal &&
          authorization != null,
      channels: List.unmodifiable(channels),
      rejectedCrossFocusCount: rejectedCrossFocusCount,
      rejectedUnscopedCount: rejectedUnscopedCount,
    );
  }
}

class Bmp04FocusContext {
  const Bmp04FocusContext({
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

  String? localizedName(String languageCode) =>
      displayName[languageCode] ?? displayName['en'] ?? displayName['zh-CN'];

  factory Bmp04FocusContext.fromJson(Object? value) {
    final map = _asMap(value);
    final rawNames = _asMap(map?['display_name']);
    final names = <String, String>{};
    if (rawNames != null) {
      for (final entry in rawNames.entries) {
        final text = _safeText(entry.value);
        if (text != null) names[entry.key] = text;
      }
    }
    return Bmp04FocusContext(
      mode: (_asString(map?['mode']) ?? 'GLOBAL_ALL').toUpperCase(),
      domainId: _asString(map?['domain_id'])?.toUpperCase(),
      productId: _asString(map?['product_id'])?.toUpperCase(),
      subjectId: _asString(map?['subject_id']),
      brandFocusId: _asString(map?['brand_focus_id']),
      displayName: Map.unmodifiable(names),
    );
  }
}

class Bmp04Channel {
  const Bmp04Channel({
    required this.id,
    required this.brandFocusId,
    required this.name,
    required this.content,
    required this.exposure,
    required this.response,
    required this.conversion,
  });

  final String id;
  final String? brandFocusId;
  final String name;
  final Bmp04Metric? content;
  final Bmp04Metric? exposure;
  final Bmp04Metric? response;
  final Bmp04Metric? conversion;

  static Bmp04Channel? fromJson(Map<String, Object?> json) {
    final id = _safeText(json['id'] ?? json['channel_id']);
    final rawBrandFocusId = json['brand_focus_id'];
    final brandFocusId = _safeText(rawBrandFocusId);
    final name = _safeText(json['name'] ?? json['channel']);
    if ((json.containsKey('brand_focus_id') &&
            rawBrandFocusId != null &&
            brandFocusId == null) ||
        id == null ||
        name == null) {
      return null;
    }
    final content = Bmp04Metric.fromJson(json['content']);
    final exposure = Bmp04Metric.fromJson(json['exposure'] ?? json['reach']);
    final response = Bmp04Metric.fromJson(
      json['response'] ?? json['engagement'],
    );
    final conversion = Bmp04Metric.fromJson(json['conversion']);
    if (content == null &&
        exposure == null &&
        response == null &&
        conversion == null) {
      return null;
    }
    return Bmp04Channel(
      id: id,
      brandFocusId: brandFocusId,
      name: name,
      content: content,
      exposure: exposure,
      response: response,
      conversion: conversion,
    );
  }
}

class Bmp04Metric {
  const Bmp04Metric({
    required this.value,
    required this.unit,
    required this.definition,
    required this.window,
    required this.source,
    required this.evidenceReference,
    required this.freshness,
    required this.label,
  });

  final num value;
  final String? unit;
  final String definition;
  final String window;
  final String source;
  final String evidenceReference;
  final String? freshness;
  final Map<String, String> label;

  static Bmp04Metric? fromJson(Object? value) {
    final map = _asMap(value);
    if (map == null) return null;
    final rawValue = map['value'];
    final number = rawValue is num && rawValue.isFinite && rawValue >= 0
        ? rawValue
        : null;
    final definition = _safeText(map['definition']);
    final window = _safeText(map['window']);
    final source = _safeText(map['source'] ?? map['source_name']);
    final evidenceReference = _safeTraceReference(
      map['evidence_ref'] ?? map['evidence'],
    );
    if (number == null ||
        number.abs() > 1000000000000 ||
        definition == null ||
        window == null ||
        source == null ||
        evidenceReference == null) {
      return null;
    }
    return Bmp04Metric(
      value: number,
      unit: _safeText(map['unit']),
      definition: definition,
      window: window,
      source: source,
      evidenceReference: evidenceReference,
      freshness: _safeText(map['freshness']),
      label: _localizedMap(map['label']),
    );
  }

  String localizedLabel(String languageCode, String fallback) =>
      label[languageCode] ?? label['en'] ?? fallback;
}

Map<String, Object?>? _asMap(Object? value) {
  if (value is! Map) return null;
  return value.map((key, value) => MapEntry('$key', value));
}

List<Map<String, Object?>> _sectionItems(Object? sections) {
  if (sections is! List) return const [];
  for (final value in sections) {
    final section = _asMap(value);
    final type = _asString(section?['type'])?.toLowerCase();
    if (type != 'channels' && type != 'propagation') continue;
    final items = section?['items'] ?? section?['rows'];
    if (items is! List) return const [];
    return items.map(_asMap).whereType<Map<String, Object?>>().toList();
  }
  return const [];
}

String? _firstSectionState(Object? sections) {
  if (sections is! List) return null;
  for (final value in sections) {
    final state = _asString(_asMap(value)?['state']);
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
  required Bmp04FocusContext focus,
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
  if (scope == null ||
      scope.length != keys.length ||
      !scope.keys.every(keys.contains)) {
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
  final evidenceScope = _canonicalScope(evidence?['scope']);
  if (evidence == null ||
      evidence.length != keys.length ||
      !evidence.keys.every(keys.contains) ||
      _positiveInteger(evidence['evidence_ref']) == null ||
      evidence['integrity_version'] != 2 ||
      evidence['integrity_verified'] != true ||
      evidenceScope == null ||
      !_sameScope(evidenceScope, expectedScope)) {
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

String? _safeTraceReference(Object? value) {
  final reference = _asString(value)?.trim();
  if (reference == null || reference.length > 64) return null;
  return RegExp(r'^(EV|TRACE|SRC)-[A-Za-z0-9._:-]{1,60}$').hasMatch(reference)
      ? reference
      : null;
}

String? _safeText(Object? value) {
  if (value is! String) return null;
  final text = value.trim();
  if (text.isEmpty || text.length > 180) return null;
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
