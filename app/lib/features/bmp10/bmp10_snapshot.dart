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
    this.observedEvents = const [],
    this.observedRisks = const [],
  });

  final bool contractBound;
  final String dataState;
  final Bmp10Scope scope;
  final bool scopeApproved;
  final List<Bmp10Risk> risks;
  final List<Bmp10Event> events;
  final Set<String> grantedPermissions;
  final List<Bmp10Observation> observedEvents;
  final List<Bmp10Observation> observedRisks;

  bool canStage(String permission) =>
      scopeApproved && grantedPermissions.contains(permission);

  factory Bmp10Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'BMP-10') {
      throw const FormatException('BMP-10 runtime response is not valid.');
    }
    if (response['observation_contract'] == 'lumenis.bmp10-observations.v1') {
      return _observationSnapshot(response);
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


class Bmp10Observation {
  const Bmp10Observation({required this.id, required this.title,
    required this.evidenceReference, this.date, this.status, this.level, this.score});
  final String id;
  final String title;
  final String evidenceReference;
  final String? date;
  final String? status;
  final String? level;
  final num? score;
}

String? _observedText(Object? value) {
  if (value is! String || value.trim().isEmpty || value.length > 240 ||
      RegExp(r'[\x00-\x1F<>]').hasMatch(value)) {
    return null;
  }
  return value.trim();
}

String? _observedDate(Object? value) {
  final text=_observedText(value);
  if(text==null) return null;
  final format=RegExp(r'^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.\d{1,6})?)?(?:Z|([+-]\d{2}):?(\d{2}))?)?$').firstMatch(text);
  if(format==null) return null;
  for(final bounds in [[4,23],[5,59],[6,59],[7,23],[8,59]]) {
    final part=format.group(bounds[0]);
    if(part!=null && int.parse(part).abs()>bounds[1]) return null;
  }
  final parsed=DateTime.tryParse(text);
  if(parsed==null) return null;
  // DateTime normalizes impossible calendar days; reject those rather than invent a date.
  final day=DateTime.tryParse(text.substring(0,10));
  if(day==null || day.year!=int.parse(text.substring(0,4)) ||
      day.month!=int.parse(text.substring(5,7)) || day.day!=int.parse(text.substring(8,10))) {
    return null;
  }
  return text;
}

Bmp10Snapshot _observationSnapshot(Map<String,dynamic> response) {
  final binding=_asMap(response['observation_read_binding']) ?? {};
  final context=_asMap(response['observation_context']) ?? {};
  final truth=_asMap(response['truth']) ?? {};
  final events=response['observed_events'];
  final risks=response['observed_risks'];
  final er=_asMap(truth['event_read']) ?? {};
  final coverage=_asMap(truth['coverage']) ?? {};
  final mode=context['canonical_scope'];
  final brand=context['brand_focus_id'];
  final actor=binding['actor_id'];
  final subject=context['subject_id'];
  final focused=mode=='FOCUS' && brand is String && brand.isNotEmpty && brand==brand.trim() &&
      subject is String && subject.isNotEmpty && subject==subject.trim();
  final global=mode=='GLOBAL_ALL' && brand==null && context['subject_id']==null;
  bool count(Object? x)=>x is int && x>=0;
  final eventMeta=events is List && count(er['observed_returned_count']) &&
      er['observed_returned_count']==events.length && count(er['rejected_count']) &&
      er['truncated'] is bool && er['read_complete'] is bool &&
      er['read_complete']==(er['truncated']==false && er['rejected_count']==0);
  final riskMeta=risks is List && count(coverage['risk_returned_count']) &&
      coverage['risk_returned_count']==risks.length && count(coverage['risk_observed_count']) &&
      (coverage['risk_observed_count'] as int)>=risks.length && count(coverage['rejected_sources']) &&
      coverage['source_truncated'] is bool && coverage['risk_truncated'] is bool &&
      coverage['risk_truncated']==((coverage['risk_observed_count'] as int)>risks.length) &&
      coverage['source_read_complete']==(coverage['source_truncated']==false && coverage['rejected_sources']==0) &&
      coverage['risk_read_complete']==(coverage['source_read_complete']==true && coverage['risk_truncated']==false);
  final incomplete=er['read_complete']!=true || coverage['risk_read_complete']!=true;
  final expectedState=incomplete?'PARTIAL':events is List && risks is List && (events.isNotEmpty || risks.isNotEmpty)?'READY':'EMPTY';
  final bound=response['bound']==true && response['source']=='runtime';
  final allowed=bound && eventMeta && riskMeta && truth['data_state']==expectedState &&
      truth['analysis_state']=='NOT_COMPUTED' && truth['domain_id']=='zbmp' && truth['product_id']=='ZBMP' &&
      binding['contract']=='lumenis.scope-read-binding.v1' && binding['module']=='brand_market_overview' &&
      binding['policy']=='actor-exact-scope-v1' && binding['actor_scope']=='authenticated' &&
      actor is int && actor>0 && context['actor_id']==actor &&
      binding['applied']==true && binding['read_allowed']==true && binding['scope_verified']==true &&
      context['domain_id']=='BMP' && context['product_id']=='ZBMP' &&
      binding['domain_id']==context['domain_id'] && binding['product_id']==context['product_id'] &&
      binding['canonical_scope']==mode && binding['subject_id']==context['subject_id'] && binding['brand_focus_id']==brand &&
      ((focused && binding['global_all_granted']==false) || (global && binding['global_all_granted']==true));
  var rejected=0;
  List<Bmp10Observation> parse(Object? raw,bool event) {
    final out=<Bmp10Observation>[];
    if (!allowed || raw is! List) return out;
    for(final value in raw) {
      final row=_asMap(value) ?? {};
      final proof=_asMap(row['scope_evidence']) ?? {};
      final scope=_asMap(proof['stored_scope']) ?? {};
      final integrity=_asMap(proof['integrity']) ?? {};
      final id=row['id'];final evidence=proof['id'];final title=_observedText(row['title']);
      final digest=integrity['digest'];
      final valid=(event ? id is int && id>0 : id is String && id.isNotEmpty) && title!=null &&
          evidence is int && evidence>0 && integrity['verified']==true &&
          integrity['assurance']=='writer-authenticated' && integrity['algorithm']=='hmac-sha256' && digest is String && RegExp(r'^[a-fA-F0-9]{64}$').hasMatch(digest) &&
          scope['domain_id']=='zbmp' && scope['product_id']=='ZBMP' && scope['global']==false &&
          scope['subject_id']==null && scope['brand_focus_id'] is String &&
          (scope['brand_focus_id'] as String).isNotEmpty && (global || scope['brand_focus_id']==brand);
      if(!valid) { rejected++;continue; }
      final score=row['score'];
      out.add(Bmp10Observation(id:id.toString(),title:title,evidenceReference:'EV-$evidence',
        date:_observedDate(row['date']),status:event?_observedText(row['status']):null,
        level:event?null:_observedText(row['level']),score:score is num && score.isFinite && score>=0 && score<=100?score:null));
    }
    return List.unmodifiable(out);
  }
  final observedEvents=parse(events,true),observedRisks=parse(risks,false);
  return Bmp10Snapshot(contractBound:bound,dataState:!allowed?'UNKNOWN':rejected>0?'PARTIAL':expectedState,
    scope:Bmp10Scope(mode:mode is String?mode:'UNKNOWN',brandId:brand is String?brand:null,displayNames:const {}),
    scopeApproved:allowed,risks:const [],events:const [],grantedPermissions:const {},
    observedEvents:observedEvents,observedRisks:observedRisks);
}
