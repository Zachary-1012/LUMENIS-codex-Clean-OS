import '../../../core/lumenis_core_client.dart';

enum Cth08ContextMode { globalAll, focused }

class Cth08Context {
  const Cth08Context({required this.mode, this.subjectId, this.displayName});

  final Cth08ContextMode mode;
  final String? subjectId;
  final String? displayName;

  String get contractMode => switch (mode) {
    Cth08ContextMode.globalAll => 'GLOBAL_ALL',
    Cth08ContextMode.focused => 'FOCUS',
  };
}

enum Cth08ContentState { ready, empty, notCollected, partial }

enum Cth08TimelineState { done, current, pending, blocked }

class Cth08EvidenceReference {
  const Cth08EvidenceReference({
    required this.id,
    required this.quote,
    required this.capturedAt,
    required this.integrityStatus,
    required this.integrityVersion,
    required this.scopeMode,
    required this.domainId,
    required this.productId,
    required this.subjectId,
    required this.readAllowed,
  });

  final String id;
  final String quote;
  final String capturedAt;
  final String integrityStatus;
  final String integrityVersion;
  final String scopeMode;
  final String domainId;
  final String productId;
  final String? subjectId;
  final bool readAllowed;
}

class Cth08TimelineStep {
  const Cth08TimelineStep({
    required this.label,
    required this.detail,
    required this.occurredAt,
    required this.state,
  });

  final String label;
  final String detail;
  final String occurredAt;
  final Cth08TimelineState state;
}

class Cth08Case {
  const Cth08Case({
    required this.id,
    required this.title,
    required this.state,
    required this.summary,
    required this.risk,
    required this.timeline,
    required this.evidence,
  });

  final String id;
  final String title;
  final String state;
  final String summary;
  final String risk;
  final List<Cth08TimelineStep> timeline;
  final List<Cth08EvidenceReference> evidence;
}

class Cth08KnowledgeItem {
  const Cth08KnowledgeItem({
    required this.id,
    required this.title,
    required this.summary,
    required this.caseId,
    required this.evidence,
  });

  final String id;
  final String title;
  final String summary;
  final String caseId;
  final List<Cth08EvidenceReference> evidence;
}

class Cth08WorkspaceData {
  const Cth08WorkspaceData({
    required this.context,
    required this.state,
    required this.cases,
    required this.knowledge,
  });

  final Cth08Context context;
  final Cth08ContentState state;
  final List<Cth08Case> cases;
  final List<Cth08KnowledgeItem> knowledge;
}

enum Cth08BlockedReason {
  contextUnavailable,
  pageBindingUnavailable,
  evidenceBindingUnavailable,
}

class Cth08BlockedException implements Exception {
  const Cth08BlockedException(this.reason);

  final Cth08BlockedReason reason;
}

abstract interface class Cth08Repository {
  Future<Cth08WorkspaceData> load();
}

class CoreCth08Repository implements Cth08Repository {
  CoreCth08Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Cth08WorkspaceData> load() async {
    final context = _decodeContext(await _client.settingsContext());
    final response = await _client.screen('CTH-08');
    final binding = _map(response['binding']);
    _requireReadBinding(response, binding, context);
    return _decodeWorkspace(response, context);
  }

  Cth08WorkspaceData _decodeWorkspace(
    Map<String, dynamic> response,
    Cth08Context context,
  ) {
    final sections = _maps(response['sections']);
    final caseSection = _firstSection(sections, 'cases');
    final knowledgeSection = _firstSection(sections, 'knowledge');

    if (caseSection == null && knowledgeSection == null) {
      return Cth08WorkspaceData(
        context: context,
        state: Cth08ContentState.notCollected,
        cases: const [],
        knowledge: const [],
      );
    }

    var droppedRows = false;
    final cases = <Cth08Case>[];
    for (final raw in _maps(caseSection?['items'])) {
      final decoded = _decodeCase(raw, context);
      if (decoded == null) {
        droppedRows = true;
      } else {
        cases.add(decoded.value);
        droppedRows |= decoded.dropped;
      }
    }

    final knowledge = <Cth08KnowledgeItem>[];
    for (final raw in _maps(knowledgeSection?['items'])) {
      final decoded = _decodeKnowledge(raw, context);
      if (decoded == null) {
        droppedRows = true;
      } else {
        knowledge.add(decoded.value);
        droppedRows |= decoded.dropped;
      }
    }

    final hasRows = cases.isNotEmpty || knowledge.isNotEmpty;
    final state = droppedRows
        ? Cth08ContentState.partial
        : hasRows
        ? Cth08ContentState.ready
        : Cth08ContentState.empty;

    return Cth08WorkspaceData(
      context: context,
      state: state,
      cases: List.unmodifiable(cases),
      knowledge: List.unmodifiable(knowledge),
    );
  }

  ({Cth08Case value, bool dropped})? _decodeCase(
    Map<String, dynamic> raw,
    Cth08Context context,
  ) {
    final id = _safeText(raw['id']);
    final title = _safeText(raw['title']);
    if (id.isEmpty || title.isEmpty) return null;

    final evidence = _decodeEvidence(raw['evidence'], context);
    if (evidence.items.isEmpty) return null;

    final timeline = _maps(raw['timeline'])
        .map(_decodeTimeline)
        .whereType<Cth08TimelineStep>()
        .toList(growable: false);

    return (
      value: Cth08Case(
        id: id,
        title: title,
        state: _safeText(raw['state']),
        summary: _safeText(raw['summary']),
        risk: _safeText(raw['risk']),
        timeline: timeline,
        evidence: evidence.items,
      ),
      dropped: evidence.dropped,
    );
  }

  ({Cth08KnowledgeItem value, bool dropped})? _decodeKnowledge(
    Map<String, dynamic> raw,
    Cth08Context context,
  ) {
    final id = _safeText(raw['id']);
    final title = _safeText(raw['title']);
    final reviewState = _safeText(raw['review_state']).toLowerCase();
    final caseId = _safeText(raw['case_id']);
    if (id.isEmpty ||
        title.isEmpty ||
        caseId.isEmpty ||
        !{'reviewed', 'approved'}.contains(reviewState)) {
      return null;
    }

    final evidence = _decodeEvidence(raw['evidence'], context);
    if (evidence.items.isEmpty) return null;

    return (
      value: Cth08KnowledgeItem(
        id: id,
        title: title,
        summary: _safeText(raw['summary']),
        caseId: caseId,
        evidence: evidence.items,
      ),
      dropped: evidence.dropped,
    );
  }

  Cth08TimelineStep? _decodeTimeline(Map<String, dynamic> raw) {
    final label = _safeText(raw['label']);
    if (label.isEmpty) return null;
    final state = switch (_safeText(raw['state']).toLowerCase()) {
      'done' => Cth08TimelineState.done,
      'current' => Cth08TimelineState.current,
      'blocked' => Cth08TimelineState.blocked,
      _ => Cth08TimelineState.pending,
    };
    return Cth08TimelineStep(
      label: label,
      detail: _safeText(raw['detail']),
      occurredAt: _safeText(raw['occurred_at']),
      state: state,
    );
  }

  ({List<Cth08EvidenceReference> items, bool dropped}) _decodeEvidence(
    Object? value,
    Cth08Context context,
  ) {
    if (value is! List) return (items: const [], dropped: true);
    final result = <Cth08EvidenceReference>[];
    var dropped = false;
    for (final raw in value) {
      final map = _map(raw);
      if (map == null) {
        dropped = true;
        continue;
      }
      final evidence = _decodeEvidenceReference(map, context);
      if (evidence == null) {
        dropped = true;
      } else {
        result.add(evidence);
      }
    }
    return (items: List.unmodifiable(result), dropped: dropped);
  }

  Cth08EvidenceReference? _decodeEvidenceReference(
    Map<String, dynamic> raw,
    Cth08Context context,
  ) {
    final id = _safeText(raw['canonical_ref']);
    final integrity = _map(raw['integrity']);
    final scope = _map(raw['scope']);
    if (id.isEmpty ||
        raw['canonical'] != true ||
        raw['read_allowed'] != true ||
        integrity?['status'] != 'verified' ||
        _safeText(integrity?['version']).isEmpty ||
        scope == null ||
        !scope.containsKey('subject_id') ||
        scope['mode'] != context.contractMode ||
        scope['domain_id'] != 'CTH' ||
        scope['product_id'] != 'CTH' ||
        scope['scope_verified'] != true) {
      return null;
    }
    final rawSubjectId = scope['subject_id'];
    final subjectId = _safeOptionalText(rawSubjectId);
    if (context.mode == Cth08ContextMode.globalAll) {
      if (rawSubjectId != null) return null;
    } else if (rawSubjectId != context.subjectId) {
      return null;
    }
    return Cth08EvidenceReference(
      id: id,
      quote: _safeText(raw['quote']),
      capturedAt: _safeText(raw['captured_at']),
      integrityStatus: 'verified',
      integrityVersion: _safeText(integrity?['version']),
      scopeMode: context.contractMode,
      domainId: 'CTH',
      productId: 'CTH',
      subjectId: subjectId,
      readAllowed: true,
    );
  }

  static Cth08Context _decodeContext(Map<String, dynamic> response) {
    if (response['ok'] != true ||
        response['contract'] != 'lumenis.context.v1' ||
        response['selection_only'] != true) {
      throw const Cth08BlockedException(Cth08BlockedReason.contextUnavailable);
    }

    final context = _map(response['context']);
    final mode = context?['mode'];
    if (mode == 'GLOBAL_ALL' &&
        context?['domain_id'] == null &&
        context?['subject_id'] == null) {
      return const Cth08Context(mode: Cth08ContextMode.globalAll);
    }

    if (mode == 'FOCUS' && context?['domain_id'] == 'CTH') {
      final subjectId = context?['subject_id'];
      if (subjectId is String && subjectId.trim().isNotEmpty) {
        final displayName = _contextDisplayName(context?['display_name']);
        return Cth08Context(
          mode: Cth08ContextMode.focused,
          subjectId: subjectId.trim(),
          displayName: displayName,
        );
      }
    }

    throw const Cth08BlockedException(Cth08BlockedReason.contextUnavailable);
  }

  static void _requireReadBinding(
    Map<String, dynamic> response,
    Map<String, dynamic>? binding,
    Cth08Context context,
  ) {
    if (response['ok'] != true || response['screen'] != 'CTH-08') {
      throw const FormatException(
        'CTH-08 response does not match its contract.',
      );
    }
    if (binding?['screen'] != 'CTH-08' ||
        binding?['applied'] != true ||
        binding?['domain_id'] != 'CTH' ||
        binding?['product_id'] != 'CTH' ||
        binding?['context_mode'] != context.contractMode ||
        binding?['canonical_scope'] != context.contractMode ||
        binding?['scope_verified'] != true ||
        binding?['read_allowed'] != true ||
        binding?['evidence_lineage'] != 'verified') {
      throw const Cth08BlockedException(
        Cth08BlockedReason.pageBindingUnavailable,
      );
    }
    if (binding?['actor_scope'] != 'verified') {
      throw const Cth08BlockedException(
        Cth08BlockedReason.pageBindingUnavailable,
      );
    }
    if (context.mode == Cth08ContextMode.globalAll &&
        (binding?.containsKey('subject_id') != true ||
            binding?['global_all_granted'] != true ||
            binding?['subject_id'] != null)) {
      throw const Cth08BlockedException(
        Cth08BlockedReason.pageBindingUnavailable,
      );
    }
    if (context.mode == Cth08ContextMode.focused &&
        (binding?['global_all_granted'] != false ||
            binding?['subject_id'] != context.subjectId)) {
      throw const Cth08BlockedException(
        Cth08BlockedReason.pageBindingUnavailable,
      );
    }
  }

  static String? _contextDisplayName(Object? value) {
    final map = _map(value);
    for (final key in const ['zh-CN', 'en', 'ko']) {
      final candidate = _safeText(map?[key]);
      if (candidate.isNotEmpty) return candidate;
    }
    return null;
  }

  static Map<String, dynamic>? _firstSection(
    List<Map<String, dynamic>> sections,
    String type,
  ) {
    for (final section in sections) {
      if (section['type'] == type) return section;
    }
    return null;
  }

  static List<Map<String, dynamic>> _maps(Object? value) {
    if (value is! List) return const [];
    return value.map(_map).whereType<Map<String, dynamic>>().toList();
  }

  static Map<String, dynamic>? _map(Object? value) {
    if (value is Map<String, dynamic>) return value;
    if (value is! Map) return null;
    return value.map((key, value) => MapEntry('$key', value));
  }

  static String _safeText(Object? value) {
    if (value is! String) return '';
    final text = value.trim();
    if (text.isEmpty || text.length > 240) return '';
    if (RegExp(
      r'(api[_ -]?key|token|cookie|password|secret|authorization|/api/|http 4\d\d|permission|lumenis core)',
      caseSensitive: false,
    ).hasMatch(text)) {
      return '';
    }
    return text;
  }

  static String? _safeOptionalText(Object? value) {
    if (value == null) return null;
    final text = _safeText(value);
    return text.isEmpty ? null : text;
  }
}
