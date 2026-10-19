enum Bmp04PresentationState {
  global,
  ready,
  observationsOnly,
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
    this.sourceObservations = const [],
    this.dashboards = const [],
    this.curatedEvents = const [],
    this.unclassifiedEventCount,
    this.classificationState = 'UNAVAILABLE',
    this.analysisState = 'UNKNOWN',

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
  final List<Bmp04SourceObservation> sourceObservations;
  final List<Bmp04Dashboard> dashboards;
  final List<Bmp04CuratedEvent> curatedEvents;
  final int? unclassifiedEventCount;
  final String classificationState;
  final String analysisState;


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
      'OBSERVATIONS_ONLY' => Bmp04PresentationState.observationsOnly,
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
    if (response['observation_contract'] == 'lumenis.bmp04-source-observations.v1') {
      return _sourceObservationSnapshot(response);
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


class Bmp04SourceObservation {
  const Bmp04SourceObservation({required this.id, required this.evidenceReference,
    this.title, this.platform});
  final String id;
  final String evidenceReference;
  final String? title;
  final String? platform;
}

String? _observationText(Object? value) {
  if(value is! String || value.isEmpty || value!=value.trim() || value.length>240 ||
      RegExp(r'[\x00-\x1F<>]').hasMatch(value)) {
    return null;
  }
  return value;
}

Bmp04Snapshot _sourceObservationSnapshot(Map<String,dynamic> response) {
  final truth=_asMap(response['truth']) ?? {};
  final binding=_asMap(response['observation_read_binding']) ?? {};
  final context=_asMap(response['observation_context']) ?? {};
  final raw=response['source_observations'];
  final subject=_observationText(context['subject_id']);
  final brand=_observationText(context['brand_focus_id']);
  final mode=context['canonical_scope'];
  final focus=Bmp04FocusContext(mode:mode is String?mode:'UNKNOWN',domainId:context['domain_id'] is String?context['domain_id'] as String:null,
    productId:context['product_id'] is String?context['product_id'] as String:null,subjectId:subject,brandFocusId:brand,displayName:const {});
  final sourceComplete=truth['source_read_complete'];final eventComplete=truth['event_read_complete'];
  final rejected=truth['rejected_source_count'];final truncated=truth['source_truncated'];
  bool count(Object? v)=>v is int && v>=0;
  final metaValid=raw is List && count(truth['observed_source_count']) && truth['observed_source_count']==raw.length &&
      count(rejected) && truncated is bool && sourceComplete is bool && eventComplete is bool &&
      sourceComplete==(truncated==false && rejected==0) &&
      (sourceComplete==true?truth['source_count']==raw.length:truth['source_count']==null) &&
      (eventComplete!=true || count(truth['event_returned_count']));
  final incomplete=sourceComplete!=true || eventComplete!=true;
  final expected=incomplete?'PARTIAL':raw is List && (raw.isNotEmpty || (truth['event_returned_count'] is int && (truth['event_returned_count'] as int)>0))?'READY':'EMPTY';
  final owner=truth['domain_id']=='zbmp' && truth['product_id']=='ZBMP';
  final bound=response['bound']==true && response['source']=='runtime';
  final actor=binding['actor_id'];
  final allowed=bound && owner && metaValid && truth['data_state']==expected && truth['analysis_state']=='NOT_COMPUTED' &&
      binding['contract']=='lumenis.scope-read-binding.v1' && binding['module']=='brand_market_overview' &&
      binding['policy']=='actor-exact-scope-v1' && binding['actor_scope']=='authenticated' &&
      actor is int && actor>0 && actor==context['actor_id'] && binding['applied']==true && binding['read_allowed']==true && binding['scope_verified']==true &&
      binding['domain_id']==context['domain_id'] && binding['product_id']==context['product_id'] &&
      binding['canonical_scope']==mode && binding['subject_id']==context['subject_id'] && binding['brand_focus_id']==context['brand_focus_id'] &&
      ((focus.isFocused && binding['global_all_granted']==false) ||
       (focus.isGlobal && context['subject_id']==null && context['brand_focus_id']==null && binding['global_all_granted']==true));
  final observations=<Bmp04SourceObservation>[];var rejectedRows=0;
  if(allowed) {
    for(final value in raw) {
      final row=_asMap(value) ?? {};final proof=_asMap(row['scope_evidence']) ?? {};
      final integrity=_asMap(proof['integrity']) ?? {};final scope=_asMap(proof['stored_scope']) ?? {};
      final id=_observationText(row['id']);final eid=proof['id'];final digest=integrity['digest'];
      final valid=id!=null && eid is int && eid>0 && integrity['verified']==true && integrity['lineage_verified']==true &&
          integrity['assurance']=='writer-authenticated' && integrity['algorithm']=='hmac-sha256' &&
          digest is String && RegExp(r'^[a-fA-F0-9]{64}$').hasMatch(digest) &&
          scope['domain_id']=='zbmp' && scope['product_id']=='ZBMP' && scope['scope_status']=='VERIFIED' &&
          (scope['subject_id']==null || scope['subject_id']=='') && _observationText(scope['brand_focus_id'])!=null &&
          (focus.isGlobal || scope['brand_focus_id']==brand);
      if(!valid){rejectedRows++;continue;}
      observations.add(Bmp04SourceObservation(id:id,evidenceReference:'EV-$eid',title:_observationText(row['title']),platform:_observationText(row['platform'])));
    }
  }
  return Bmp04Snapshot(contractBound:bound,isBmpOwner:owner,dataState:!allowed?'UNKNOWN':incomplete || rejectedRows>0?'PARTIAL':expected=='READY'?'OBSERVATIONS_ONLY':'EMPTY',
      focus:focus,focusBindingApplied:allowed,readAllowed:allowed,globalScopeReady:allowed && focus.isGlobal,
      channels:const [],rejectedCrossFocusCount:0,rejectedUnscopedCount:rejectedRows,sourceObservations:List.unmodifiable(observations),
      analysisState: allowed ? 'NOT_COMPUTED' : 'UNKNOWN',
      dashboards: allowed ? _dashboards(truth, focus) : const [],
      curatedEvents: allowed ? _curatedEvents(response['sections']) : const [],
      classificationState: allowed && truth['classification_state'] is String
          ? truth['classification_state'] as String : 'UNAVAILABLE',
      unclassifiedEventCount: allowed && count(truth['unclassified_event_count'])
          ? truth['unclassified_event_count'] as int : null);

}

const bmp04Categories = ['brand_event', 'product_event', 'industry_event'];

class Bmp04CuratedEvent {
  const Bmp04CuratedEvent(this.id, this.title, this.evidenceReference);
  final int id;
  final String title;
  final String evidenceReference;
}

class Bmp04Dashboard {
  const Bmp04Dashboard({required this.category, required this.observed,
    required this.total, required this.events});
  final String category;
  final int observed;
  final int? total;
  final List<Bmp04CuratedEvent> events;
}

List<Bmp04CuratedEvent> _eventRows(Object? raw) {
  if (raw is! List) return const [];
  final events = <Bmp04CuratedEvent>[];
  final seen = <int>{};
  for (final item in raw) {
    final row = _asMap(item) ?? {};
    final id = row['event_id'];
    final title = _observationText(row['title']);
    final evidence = row['evidence_ref'];
    if (id is! int || id <= 0 || title == null || evidence is! String ||
        !RegExp(r'^EV-[1-9][0-9]*$').hasMatch(evidence) ||
        row['evidence_state'] != 'REFERENCED' || !seen.add(id)) {
      continue;
    }
    events.add(Bmp04CuratedEvent(id, title, evidence));
  }
  return List.unmodifiable(events);
}

List<Bmp04CuratedEvent> _curatedEvents(Object? sections) {
  if (sections is! List) return const [];
  for (final section in sections) {
    final row = _asMap(section);
    if (row?['type'] == 'events') return _eventRows(row?['items']);
  }
  return const [];
}

List<Bmp04Dashboard> _dashboards(Map<String, dynamic> truth, Bmp04FocusContext focus) {
  final raw = truth['dashboards'];
  if (raw is! List || raw.length != 3 ||
      !const ['READY', 'EMPTY', 'PARTIAL'].contains(truth['classification_state']) ||
      truth['total_events_semantics'] != 'current_verified_curated_sample_not_population') {
    return const [];
  }
  final result = <Bmp04Dashboard>[];
  final seen = <String>{};
  final classifiedIds = <int>{};
  for (final item in raw) {
    final row = _asMap(item) ?? {};
    final category = row['category'];
    final observed = row['observed_events'];
    final total = row['total_events'];
    if (category is! String || !bmp04Categories.contains(category) ||
        !seen.add(category) || observed is! int || observed < 0 ||
        row['claim_type'] != 'human_business_classification' ||
        (total != null && (total is! int || total != observed ||
          truth['event_read_complete'] != true || truth['unclassified_event_count'] != 0 ||
          truth['classification_rejected'] != 0 ||
          !const ['READY', 'EMPTY'].contains(truth['classification_state'])))) {
      return const [];
    }
    final refs = row['source_refs'];
    if (refs is! List || refs.length != observed) return const [];
    final references = <int, String>{};
    for (final value in refs) {
      final ref = _asMap(value) ?? {};
      final id = ref['event_id'];
      final proof = _asMap(ref['scope_evidence']) ?? {};
      final integrity = _asMap(proof['integrity']) ?? {};
      final scope = _asMap(proof['stored_scope']) ?? {};
      final evidenceId = proof['id'];
      final digest = integrity['digest'];
      if (id is! int || id <= 0 || !classifiedIds.add(id) ||
          evidenceId is! int || evidenceId <= 0 ||
          integrity['verified'] != true || integrity['assurance'] != 'writer-authenticated' ||
          integrity['algorithm'] != 'hmac-sha256' || digest is! String ||
          !RegExp(r'^[a-fA-F0-9]{64}$').hasMatch(digest) ||
          scope['domain_id'] != 'zbmp' || scope['product_id'] != 'ZBMP' ||
          scope['global'] != false || _observationText(scope['brand_focus_id']) == null ||
          (!focus.isGlobal && scope['brand_focus_id'] != focus.brandFocusId)) {
        return const [];
      }
      references[id] = 'EV-$evidenceId';
    }
    final events = _eventRows(row['events']);
    if (events.any((event) => references[event.id] != event.evidenceReference)) return const [];
    result.add(Bmp04Dashboard(category: category, observed: observed,
      total: total as int?, events: events));
  }
  return List.unmodifiable(result);
}
