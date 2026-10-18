enum Bmp03PresentationState {
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

class Bmp03Snapshot {
  const Bmp03Snapshot({
    required this.contractBound,
    required this.isBmpOwner,
    required this.dataState,
    required this.focus,
    required this.focusBindingApplied,
    required this.readAllowed,
    required this.globalScopeReady,
    required this.signals,
    required this.rejectedCrossFocusCount,
    required this.rejectedUnscopedCount,
    this.sourceObservations = const [],
  });

  final bool contractBound;
  final bool isBmpOwner;
  final String dataState;
  final Bmp03FocusContext focus;
  final bool focusBindingApplied;
  final bool readAllowed;
  final bool globalScopeReady;
  final List<Bmp03Signal> signals;
  // Source observations never acquire signal scores or insight status.
  final List<Bmp03SourceObservation> sourceObservations;
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

  Bmp03PresentationState get presentationState {
    if (!contractBound || !isBmpOwner) {
      return Bmp03PresentationState.unavailable;
    }
    if (!scopeReady) return Bmp03PresentationState.blocked;
    return switch (dataState) {
      'READY' =>
        signals.isEmpty
            ? (rejectedUnscopedCount > 0
                  ? Bmp03PresentationState.blocked
                  : Bmp03PresentationState.empty)
            : Bmp03PresentationState.ready,
      'PARTIAL' => Bmp03PresentationState.partial,
      'STALE' =>
        signals.isEmpty
            ? (rejectedUnscopedCount > 0
                  ? Bmp03PresentationState.blocked
                  : Bmp03PresentationState.empty)
            : Bmp03PresentationState.stale,
      'NOT_COLLECTED' => Bmp03PresentationState.notCollected,
      'EMPTY' => Bmp03PresentationState.empty,
      'BLOCKED' => Bmp03PresentationState.blocked,
      _ => Bmp03PresentationState.unknown,
    };
  }

  factory Bmp03Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'BMP-03') {
      throw const FormatException('BMP-03 runtime response is not valid.');
    }
    if (response['source_observation_contract'] ==
        'lumenis.bmp03-source-observations.v1') {
      return _sourceObservationSnapshot(response);
    }
    final truth = _asMap(response['truth']);
    final binding = _asMap(response['focus_binding']);
    final focus = Bmp03FocusContext.fromJson(response['focus_context']);
    final authorization = _scopeAuthorization(
      binding,
      mode: focus.mode,
      domainId: focus.domainId,
      productId: focus.productId,
      subjectId: focus.subjectId,
      brandFocusId: focus.brandFocusId,
    );
    final rawSignals = _sectionItems(response['sections']);
    final signals = <Bmp03Signal>[];
    var rejectedCrossFocusCount = 0;
    var rejectedUnscopedCount = 0;
    for (final raw in rawSignals) {
      final signal = Bmp03Signal.fromJson(raw);
      if (signal == null) {
        rejectedUnscopedCount++;
      } else if (focus.isGlobal) {
        if (authorization != null &&
            _rowIsAuthorized(raw, focus: focus, authorization: authorization)) {
          signals.add(signal);
        } else {
          rejectedUnscopedCount++;
        }
      } else if (focus.brandFocusId == null ||
          signal.brandFocusId != focus.brandFocusId) {
        rejectedCrossFocusCount++;
      } else if (authorization != null &&
          _rowIsAuthorized(raw, focus: focus, authorization: authorization)) {
        signals.add(signal);
      } else {
        rejectedUnscopedCount++;
      }
    }
    final contractBound =
        response['bound'] == true && response['source'] == 'runtime';
    final isBmpOwner =
        (_asString(truth?['product_id']) ?? '').toUpperCase() == 'ZBMP' &&
        (_asString(truth?['domain_id']) ?? '').toLowerCase() == 'zbmp';
    return Bmp03Snapshot(
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
      signals: List.unmodifiable(signals),
      rejectedCrossFocusCount: rejectedCrossFocusCount,
      rejectedUnscopedCount: rejectedUnscopedCount,
    );
  }
}

class Bmp03SourceObservation {
  const Bmp03SourceObservation({required this.id, required this.title,
    required this.platform, required this.evidenceReference});
  final String id;
  final String title;
  final String? platform;
  final String evidenceReference;
}

String? _observationText(Object? value) {
  if (value is! String) return null;
  final text = value.trim();
  if (text.isEmpty || text.length > 180 ||
      RegExp(r'[\x00-\x1F<>]').hasMatch(text)) return null;
  return text;
}

Bmp03Snapshot _sourceObservationSnapshot(Map<String, dynamic> response) {
  final truth = _asMap(response['truth']);
  final binding = _asMap(response['source_read_binding']);
  final focus = Bmp03FocusContext.fromJson(response['source_context']);
  final owner = truth?['product_id'] == 'ZBMP' && truth?['domain_id'] == 'zbmp';
  final bound = response['bound'] == true && response['source'] == 'runtime';
  final raw = response['source_observations'];
  final sourceCount = truth?['source_count'];
  final rejectedCount = truth?['rejected_count'];
  final truncated = truth?['truncated'];
  final state = truth?['data_state'];
  final countersValid = raw is List && sourceCount is int && sourceCount >= 0 &&
      sourceCount == raw.length && rejectedCount is int && rejectedCount >= 0 &&
      truncated is bool;
  final incomplete = countersValid && (truncated == true || rejectedCount > 0);
  final stateValid = countersValid &&
      ((state == 'PARTIAL' && incomplete) ||
       (state == 'EMPTY' && sourceCount == 0 && !incomplete) ||
       (state == 'READY' && sourceCount > 0 && !incomplete));
  final admitted = bound && owner && stateValid &&
      binding?['contract'] == 'lumenis.scope-read-binding.v1' &&
      binding?['module'] == 'brand_market_overview' &&
      binding?['policy'] == 'actor-exact-scope-v1' &&
      binding?['actor_scope'] == 'authenticated' &&
      _positiveInteger(binding?['actor_id']) != null &&
      binding?['applied'] == true && binding?['read_allowed'] == true &&
      binding?['scope_verified'] == true &&
      binding?['domain_id'] == focus.domainId &&
      binding?['product_id'] == focus.productId &&
      binding?['canonical_scope'] == focus.mode &&
      binding?['subject_id'] == focus.subjectId &&
      binding?['brand_focus_id'] == focus.brandFocusId &&
      ((focus.isGlobal && binding?['global_all_granted'] == true) ||
       (focus.isFocused && binding?['global_all_granted'] == false));
  final observations = <Bmp03SourceObservation>[];
  var rejected = 0;
  if (raw is List) {
    for (final value in raw) {
      final row = _asMap(value);
      final proof = _asMap(row?['scope_evidence']);
      final integrity = _asMap(proof?['integrity']);
      final scope = _asMap(proof?['stored_scope']);
      final id = _scopeId(row?['id']);
      final title = _observationText(row?['title']);
      final evidenceId = _positiveInteger(proof?['id']);
      final brand = _scopeId(scope?['brand_focus_id']);
      final digest = integrity?['digest'];
      final valid = admitted && id != null && title != null && evidenceId != null &&
          _scopeId(proof?['source_id']) != null &&
          scope?['product_id'] == 'ZBMP' && scope?['domain_id'] == 'zbmp' &&
          scope?['scope_status'] == 'VERIFIED' &&
          (scope?['subject_id'] == null || scope?['subject_id'] == '') &&
          brand != null && (focus.isGlobal || brand == focus.brandFocusId) &&
          integrity?['integrity_version'] == 2 && integrity?['verified'] == true &&
          integrity?['lineage_verified'] == true &&
          integrity?['assurance'] == 'writer-authenticated' &&
          integrity?['algorithm'] == 'hmac-sha256' &&
          digest is String && RegExp(r'^[0-9a-f]{64}$').hasMatch(digest);
      if (!valid) { rejected++; continue; }
      observations.add(Bmp03SourceObservation(id: id, title: title,
        platform: _safeText(row?['platform']), evidenceReference: 'EV-$evidenceId'));
    }
  } else { rejected++; }
  return Bmp03Snapshot(contractBound: bound, isBmpOwner: owner,
    // The existing insight view stays unknown until insight is actually computed.
    dataState: admitted ? (rejected > 0 || incomplete ? 'PARTIAL' : 'OBSERVATIONS_ONLY') : 'BLOCKED',
    focus: focus, focusBindingApplied: admitted, readAllowed: admitted,
    globalScopeReady: focus.isGlobal && admitted, signals: const [],
    sourceObservations: List.unmodifiable(observations),
    rejectedCrossFocusCount: 0, rejectedUnscopedCount: rejected);
}

class Bmp03FocusContext {
  const Bmp03FocusContext({
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

  factory Bmp03FocusContext.fromJson(Object? value) {
    final map = _asMap(value);
    final rawNames = _asMap(map?['display_name']);
    final names = <String, String>{};
    if (rawNames != null) {
      for (final entry in rawNames.entries) {
        final text = _safeText(entry.value);
        if (text != null) names[entry.key] = text;
      }
    }
    return Bmp03FocusContext(
      mode: (_asString(map?['mode']) ?? 'GLOBAL_ALL').toUpperCase(),
      domainId: _asString(map?['domain_id'])?.toUpperCase(),
      productId: _asString(map?['product_id'])?.toUpperCase(),
      subjectId: _asString(map?['subject_id']),
      brandFocusId: _asString(map?['brand_focus_id']),
      displayName: Map.unmodifiable(names),
    );
  }
}

class Bmp03Signal {
  const Bmp03Signal({
    required this.id,
    required this.brandFocusId,
    required this.title,
    required this.kind,
    required this.kindLabel,
    required this.confidence,
    required this.momentum,
    required this.source,
    required this.evidenceReference,
    required this.capturedAt,
    required this.timeWindow,
    required this.summary,
  });

  final String id;
  final String? brandFocusId;
  final String title;
  final String kind;
  final Map<String, String> kindLabel;
  final num? confidence;
  final num? momentum;
  final String source;
  final String evidenceReference;
  final String? capturedAt;
  final String? timeWindow;
  final String? summary;

  static Bmp03Signal? fromJson(Map<String, Object?> json) {
    final id = _safeText(json['id'] ?? json['signal_id']);
    final rawBrandFocusId = json['brand_focus_id'];
    final brandFocusId = _safeText(rawBrandFocusId);
    final title = _safeText(json['title']);
    final kind = _safeText(json['kind']);
    final confidence = _safeNumber(json['confidence'], max: 100);
    final momentum = _safeNumber(
      json.containsKey('momentum') ? json['momentum'] : json['momentum_score'],
      max: 100,
    );
    final source = _safeText(json['source'] ?? json['source_name']);
    final evidenceReference = _canonicalEvidenceReference(json['evidence']);
    if ((json.containsKey('brand_focus_id') &&
            rawBrandFocusId != null &&
            brandFocusId == null) ||
        id == null ||
        title == null ||
        kind == null ||
        source == null ||
        evidenceReference == null) {
      return null;
    }
    return Bmp03Signal(
      id: id,
      brandFocusId: brandFocusId,
      title: title,
      kind: kind,
      kindLabel: _localizedMap(json['kind_label']),
      confidence: confidence,
      momentum: momentum,
      source: source,
      evidenceReference: evidenceReference,
      capturedAt: _safeText(json['captured_at'] ?? json['time']),
      timeWindow: _safeText(json['time_window']),
      summary: _safeText(json['summary'] ?? json['description']),
    );
  }

  String localizedKind(String languageCode) =>
      kindLabel[languageCode] ?? kindLabel['en'] ?? kind;
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
    if (type != 'intel' && type != 'signals' && type != 'opportunities') {
      continue;
    }
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
  required Bmp03FocusContext focus,
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
  return subjectId != null && brandFocusId != null && subjectId != brandFocusId
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

num? _safeNumber(Object? value, {required num max}) {
  if (value is! num || !value.isFinite || value < 0 || value > max) {
    return null;
  }
  return value;
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
