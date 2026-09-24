enum Bmp05PresentationState {
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

class Bmp05Snapshot {
  const Bmp05Snapshot({
    required this.contractBound,
    required this.isBmpOwner,
    required this.dataState,
    required this.focus,
    required this.focusBindingApplied,
    required this.readAllowed,
    required this.globalScopeReady,
    required this.creators,
    required this.rejectedCrossFocusCount,
    required this.rejectedUnscopedCount,
  });

  final bool contractBound;
  final bool isBmpOwner;
  final String dataState;
  final Bmp05FocusContext focus;
  final bool focusBindingApplied;
  final bool readAllowed;
  final bool globalScopeReady;
  final List<Bmp05Creator> creators;
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

  Bmp05PresentationState get presentationState {
    if (!contractBound || !isBmpOwner) {
      return Bmp05PresentationState.unavailable;
    }
    if (!scopeReady) return Bmp05PresentationState.blocked;
    return switch (dataState) {
      'READY' =>
        creators.isEmpty
            ? (rejectedUnscopedCount > 0
                  ? Bmp05PresentationState.blocked
                  : Bmp05PresentationState.empty)
            : Bmp05PresentationState.ready,
      'PARTIAL' => Bmp05PresentationState.partial,
      'STALE' =>
        creators.isEmpty
            ? (rejectedUnscopedCount > 0
                  ? Bmp05PresentationState.blocked
                  : Bmp05PresentationState.empty)
            : Bmp05PresentationState.stale,
      'NOT_COLLECTED' => Bmp05PresentationState.notCollected,
      'EMPTY' => Bmp05PresentationState.empty,
      'BLOCKED' => Bmp05PresentationState.blocked,
      _ => Bmp05PresentationState.unknown,
    };
  }

  factory Bmp05Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'BMP-05') {
      throw const FormatException('BMP-05 runtime response is not valid.');
    }
    final truth = _asMap(response['truth']);
    final binding = _asMap(response['focus_binding']);
    final focus = Bmp05FocusContext.fromJson(response['focus_context']);
    final globalBindingAuthorized = _globalBindingIsAuthorized(binding);
    final rawCreators = _sectionItems(response['sections']);
    final creators = <Bmp05Creator>[];
    var rejectedCrossFocusCount = 0;
    var rejectedUnscopedCount = 0;
    for (final raw in rawCreators) {
      final creator = Bmp05Creator.fromJson(raw);
      if (creator == null) {
        rejectedUnscopedCount++;
      } else if (focus.isGlobal) {
        if (globalBindingAuthorized && _globalRowIsAuthorized(raw)) {
          creators.add(creator);
        } else {
          rejectedUnscopedCount++;
        }
      } else if (focus.brandFocusId == null ||
          creator.brandFocusId != focus.brandFocusId) {
        rejectedCrossFocusCount++;
      } else {
        creators.add(creator);
      }
    }
    final contractBound =
        response['bound'] == true && response['source'] == 'runtime';
    final isBmpOwner =
        (_asString(truth?['product_id']) ?? '').toUpperCase() == 'ZBMP' &&
        (_asString(truth?['domain_id']) ?? '').toLowerCase() == 'zbmp';
    return Bmp05Snapshot(
      contractBound: contractBound,
      isBmpOwner: isBmpOwner,
      dataState:
          (_asString(truth?['data_state']) ??
                  _firstSectionState(response['sections']) ??
                  'UNKNOWN')
              .toUpperCase(),
      focus: focus,
      focusBindingApplied: binding?['applied'] == true,
      readAllowed: _readAllowed(binding),
      globalScopeReady:
          contractBound &&
          isBmpOwner &&
          focus.isGlobal &&
          globalBindingAuthorized,
      creators: List.unmodifiable(creators),
      rejectedCrossFocusCount: rejectedCrossFocusCount,
      rejectedUnscopedCount: rejectedUnscopedCount,
    );
  }
}

class Bmp05FocusContext {
  const Bmp05FocusContext({
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

  factory Bmp05FocusContext.fromJson(Object? value) {
    final map = _asMap(value);
    final rawNames = _asMap(map?['display_name']);
    final names = <String, String>{};
    if (rawNames != null) {
      for (final entry in rawNames.entries) {
        final text = _safeText(entry.value);
        if (text != null) names[entry.key] = text;
      }
    }
    return Bmp05FocusContext(
      mode: (_asString(map?['mode']) ?? 'GLOBAL_ALL').toUpperCase(),
      domainId: _asString(map?['domain_id'])?.toUpperCase(),
      productId: _asString(map?['product_id'])?.toUpperCase(),
      subjectId: _asString(map?['subject_id']),
      brandFocusId: _asString(map?['brand_focus_id']),
      displayName: Map.unmodifiable(names),
    );
  }
}

class Bmp05Creator {
  const Bmp05Creator({
    required this.id,
    required this.brandFocusId,
    required this.name,
    required this.tier,
    required this.platform,
    required this.posts,
    required this.engagement,
    required this.conversion,
    required this.risk,
    required this.evidenceReference,
    required this.source,
  });

  final String id;
  final String? brandFocusId;
  final String name;
  final String tier;
  final String platform;
  final Bmp05Metric? posts;
  final Bmp05Metric? engagement;
  final Bmp05Metric? conversion;
  final Bmp05Risk? risk;
  final String evidenceReference;
  final String source;

  static Bmp05Creator? fromJson(Map<String, Object?> json) {
    final id = _safeText(json['id'] ?? json['creator_id']);
    final rawBrandFocusId = json['brand_focus_id'];
    final brandFocusId = _safeText(rawBrandFocusId);
    final name = _safeText(json['name'] ?? json['display_name']);
    final tier = _normalizeTier(json['tier'] ?? json['type']);
    final platform = _safeText(json['platform']);
    final evidenceReference = _safeTraceReference(
      json['evidence_ref'] ?? json['evidence'],
    );
    final source = _safeText(json['source'] ?? json['source_name']);
    if ((json.containsKey('brand_focus_id') &&
            rawBrandFocusId != null &&
            brandFocusId == null) ||
        id == null ||
        name == null ||
        tier == null ||
        platform == null ||
        evidenceReference == null ||
        source == null) {
      return null;
    }
    return Bmp05Creator(
      id: id,
      brandFocusId: brandFocusId,
      name: name,
      tier: tier,
      platform: platform,
      posts: Bmp05Metric.fromJson(json['posts'] ?? json['content']),
      engagement: Bmp05Metric.fromJson(json['engagement']),
      conversion: Bmp05Metric.fromJson(json['conversion']),
      risk: Bmp05Risk.fromJson(json['risk']),
      evidenceReference: evidenceReference,
      source: source,
    );
  }
}

class Bmp05Metric {
  const Bmp05Metric({
    required this.value,
    required this.unit,
    required this.definition,
    required this.window,
  });

  final num value;
  final String? unit;
  final String definition;
  final String window;

  static Bmp05Metric? fromJson(Object? value) {
    final map = _asMap(value);
    if (map == null) return null;
    final rawValue = map['value'];
    final number = rawValue is num && rawValue.isFinite && rawValue >= 0
        ? rawValue
        : null;
    final definition = _safeText(map['definition']);
    final window = _safeText(map['window']);
    if (number == null ||
        number.abs() > 1000000000000 ||
        definition == null ||
        window == null) {
      return null;
    }
    return Bmp05Metric(
      value: number,
      unit: _safeText(map['unit']),
      definition: definition,
      window: window,
    );
  }
}

class Bmp05Risk {
  const Bmp05Risk({required this.level, required this.label, this.score});

  final String level;
  final String label;
  final num? score;

  static Bmp05Risk? fromJson(Object? value) {
    final map = _asMap(value);
    final level = _safeText(map?['level'] ?? value);
    final label = _safeText(map?['label'] ?? value);
    if (level == null || label == null) return null;
    final rawScore = map?['score'];
    final score = rawScore is num && rawScore.isFinite && rawScore >= 0
        ? rawScore
        : null;
    return Bmp05Risk(level: level, label: label, score: score);
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
    final type = _asString(section?['type'])?.toLowerCase();
    if (type != 'creators' && type != 'creator_roster') continue;
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

bool _readAllowed(Map<String, Object?>? binding) {
  if (binding?['read_allowed'] == true) return true;
  final permission = _asString(binding?['permission'])?.toUpperCase();
  return permission == 'ALLOW' || permission == 'ALLOWED';
}

bool _globalBindingIsAuthorized(Map<String, Object?>? binding) {
  final evidence = binding?['evidence_lineage'];
  final evidenceLineage =
      evidence == true || _asString(evidence)?.toLowerCase() == 'verified';
  final canonicalScope = _scopeMode(binding?['canonical_scope']);
  final bindingScope = _scopeMode(
    binding?['scope_mode'] ?? binding?['scope'] ?? binding?['context_mode'],
  );
  final explicitGlobal =
      binding?['global_all_granted'] == true ||
      binding?['global_scope'] == true ||
      canonicalScope == 'GLOBAL_ALL' ||
      bindingScope == 'GLOBAL_ALL';
  final scopeVerified = binding?['scope_verified'] == true || explicitGlobal;
  return binding?['applied'] == true &&
      binding?['read_allowed'] == true &&
      scopeVerified &&
      explicitGlobal &&
      evidenceLineage;
}

bool _globalRowIsAuthorized(Map<String, Object?> json) {
  final scope = _scopeMode(json['scope_mode'] ?? json['scope']);
  final canonicalScope = _scopeMode(json['canonical_scope']);
  final lineage = _asMap(json['lineage']);
  final lineageScope = _scopeMode(lineage?['scope_mode'] ?? lineage?['scope']);
  final lineageStatus = _asString(
    lineage?['status'] ?? lineage?['state'] ?? json['evidence_lineage'],
  )?.toUpperCase();
  final lineageVerified =
      json['lineage'] == true ||
      json['lineage'] == 'verified' ||
      json['evidence_lineage'] == 'verified' ||
      (lineageStatus == 'VERIFIED' &&
          (lineage?['canonical'] == true || lineageScope == 'GLOBAL_ALL'));
  return scope == 'GLOBAL_ALL' &&
      (canonicalScope == null || canonicalScope == 'GLOBAL_ALL') &&
      json['read_allowed'] == true &&
      lineageVerified &&
      (lineageScope == null || lineageScope == 'GLOBAL_ALL');
}

String? _scopeMode(Object? value) => _asString(value)?.trim().toUpperCase();

String? _normalizeTier(Object? value) {
  final tier = _asString(value)?.trim().toUpperCase();
  return switch (tier) {
    'KOS' || 'KOL' || 'KOC' || 'UGC' => tier,
    _ => null,
  };
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
