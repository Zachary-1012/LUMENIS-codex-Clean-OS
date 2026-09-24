import '../../../core/lumenis_core_client.dart';

enum Cth09ContextMode { globalAll, focused }

class Cth09Context {
  const Cth09Context({required this.mode, this.subjectId, this.displayName});

  final Cth09ContextMode mode;
  final String? subjectId;
  final String? displayName;

  String get contractMode => switch (mode) {
    Cth09ContextMode.globalAll => 'GLOBAL_ALL',
    Cth09ContextMode.focused => 'FOCUS',
  };
}

enum Cth09ContentState { ready, empty, notCollected, partial }

class Cth09EvidenceReference {
  const Cth09EvidenceReference({
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

class Cth09Risk {
  const Cth09Risk({
    required this.id,
    required this.title,
    required this.level,
    required this.score,
    required this.summary,
    required this.evidence,
  });

  final String id;
  final String title;
  final String level;
  final num? score;
  final String summary;
  final List<Cth09EvidenceReference> evidence;
}

class Cth09ActionGate {
  const Cth09ActionGate({
    required this.permission,
    required this.effectFence,
    required this.resultContract,
    required this.callable,
    required this.approval,
  });

  final String permission;
  final String effectFence;
  final String resultContract;
  final bool callable;
  final String approval;

  bool get exactContractBound =>
      permission == 'verified' &&
      effectFence == 'armed' &&
      resultContract == 'bound' &&
      callable &&
      approval != 'required';
}

class Cth09Decision {
  const Cth09Decision({
    required this.id,
    required this.title,
    required this.owner,
    required this.status,
    required this.actionLabel,
    required this.gate,
    required this.evidence,
  });

  final String id;
  final String title;
  final String owner;
  final String status;
  final String actionLabel;
  final Cth09ActionGate gate;
  final List<Cth09EvidenceReference> evidence;
}

class Cth09WorkbenchData {
  const Cth09WorkbenchData({
    required this.context,
    required this.state,
    required this.risks,
    required this.decisions,
  });

  final Cth09Context context;
  final Cth09ContentState state;
  final List<Cth09Risk> risks;
  final List<Cth09Decision> decisions;
}

enum Cth09BlockedReason {
  contextUnavailable,
  pageBindingUnavailable,
  evidenceBindingUnavailable,
}

class Cth09BlockedException implements Exception {
  const Cth09BlockedException(this.reason);

  final Cth09BlockedReason reason;
}

abstract interface class Cth09Repository {
  Future<Cth09WorkbenchData> load();
}

class CoreCth09Repository implements Cth09Repository {
  CoreCth09Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Cth09WorkbenchData> load() async {
    final context = _decodeContext(await _client.settingsContext());
    final response = await _client.screen('CTH-09');
    final binding = _map(response['binding']);
    _requireReadBinding(response, binding, context);
    return _decodeWorkbench(response, context);
  }

  Cth09WorkbenchData _decodeWorkbench(
    Map<String, dynamic> response,
    Cth09Context context,
  ) {
    final sections = _maps(response['sections']);
    final riskSection = _firstSection(sections, 'risks');
    final decisionSection = _firstSection(sections, 'decisions');

    if (riskSection == null && decisionSection == null) {
      return Cth09WorkbenchData(
        context: context,
        state: Cth09ContentState.notCollected,
        risks: const [],
        decisions: const [],
      );
    }

    var droppedRows = false;
    final risks = <Cth09Risk>[];
    for (final raw in _maps(riskSection?['items'])) {
      final decoded = _decodeRisk(raw, context);
      if (decoded == null) {
        droppedRows = true;
      } else {
        risks.add(decoded.value);
        droppedRows |= decoded.dropped;
      }
    }

    final decisions = <Cth09Decision>[];
    for (final raw in _maps(decisionSection?['items'])) {
      final decoded = _decodeDecision(raw, context);
      if (decoded == null) {
        droppedRows = true;
      } else {
        decisions.add(decoded.value);
        droppedRows |= decoded.dropped;
      }
    }

    final hasRows = risks.isNotEmpty || decisions.isNotEmpty;
    final state = droppedRows
        ? Cth09ContentState.partial
        : hasRows
        ? Cth09ContentState.ready
        : Cth09ContentState.empty;

    return Cth09WorkbenchData(
      context: context,
      state: state,
      risks: List.unmodifiable(risks),
      decisions: List.unmodifiable(decisions),
    );
  }

  ({Cth09Risk value, bool dropped})? _decodeRisk(
    Map<String, dynamic> raw,
    Cth09Context context,
  ) {
    final id = _safeText(raw['id']);
    final title = _safeText(raw['title']);
    if (id.isEmpty || title.isEmpty) return null;

    final evidence = _decodeEvidence(raw['evidence'], context);
    if (evidence.items.isEmpty) return null;

    return (
      value: Cth09Risk(
        id: id,
        title: title,
        level: _safeText(raw['level']),
        score: _number(raw['score']),
        summary: _safeText(raw['summary']),
        evidence: evidence.items,
      ),
      dropped: evidence.dropped,
    );
  }

  ({Cth09Decision value, bool dropped})? _decodeDecision(
    Map<String, dynamic> raw,
    Cth09Context context,
  ) {
    final id = _safeText(raw['id']);
    final title = _safeText(raw['title']);
    final actionLabel = _safeText(raw['action_label']);
    if (id.isEmpty || title.isEmpty || actionLabel.isEmpty) return null;

    final evidence = _decodeEvidence(raw['evidence'], context);
    if (evidence.items.isEmpty) return null;
    final gate = _decodeGate(raw['action_contract'] ?? raw['gate']);
    if (gate == null) return null;

    return (
      value: Cth09Decision(
        id: id,
        title: title,
        owner: _safeText(raw['owner']),
        status: _safeText(raw['status']),
        actionLabel: actionLabel,
        gate: gate,
        evidence: evidence.items,
      ),
      dropped: evidence.dropped,
    );
  }

  Cth09ActionGate? _decodeGate(Object? value) {
    final raw = _map(value);
    if (raw == null) return null;
    return Cth09ActionGate(
      permission: _safeText(raw['permission']),
      effectFence: _safeText(raw['effect_fence']),
      resultContract: _safeText(raw['result_contract']),
      callable: raw['callable'] == true,
      approval: _safeText(raw['approval']).toLowerCase(),
    );
  }

  ({List<Cth09EvidenceReference> items, bool dropped}) _decodeEvidence(
    Object? value,
    Cth09Context context,
  ) {
    if (value is! List) return (items: const [], dropped: true);
    final result = <Cth09EvidenceReference>[];
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

  Cth09EvidenceReference? _decodeEvidenceReference(
    Map<String, dynamic> raw,
    Cth09Context context,
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
    if (context.mode == Cth09ContextMode.globalAll) {
      if (rawSubjectId != null) return null;
    } else if (rawSubjectId != context.subjectId) {
      return null;
    }
    return Cth09EvidenceReference(
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

  static Cth09Context _decodeContext(Map<String, dynamic> response) {
    if (response['ok'] != true ||
        response['contract'] != 'lumenis.context.v1' ||
        response['selection_only'] != true) {
      throw const Cth09BlockedException(Cth09BlockedReason.contextUnavailable);
    }

    final context = _map(response['context']);
    final mode = context?['mode'];
    if (mode == 'GLOBAL_ALL' &&
        context?['domain_id'] == null &&
        context?['subject_id'] == null) {
      return const Cth09Context(mode: Cth09ContextMode.globalAll);
    }

    if (mode == 'FOCUS' && context?['domain_id'] == 'CTH') {
      final subjectId = context?['subject_id'];
      if (subjectId is String && subjectId.trim().isNotEmpty) {
        return Cth09Context(
          mode: Cth09ContextMode.focused,
          subjectId: subjectId.trim(),
          displayName: _contextDisplayName(context?['display_name']),
        );
      }
    }

    throw const Cth09BlockedException(Cth09BlockedReason.contextUnavailable);
  }

  static void _requireReadBinding(
    Map<String, dynamic> response,
    Map<String, dynamic>? binding,
    Cth09Context context,
  ) {
    if (response['ok'] != true || response['screen'] != 'CTH-09') {
      throw const FormatException(
        'CTH-09 response does not match its contract.',
      );
    }
    if (binding?['screen'] != 'CTH-09' ||
        binding?['applied'] != true ||
        binding?['domain_id'] != 'CTH' ||
        binding?['product_id'] != 'CTH' ||
        binding?['context_mode'] != context.contractMode ||
        binding?['canonical_scope'] != context.contractMode ||
        binding?['scope_verified'] != true ||
        binding?['read_allowed'] != true ||
        binding?['evidence_lineage'] != 'verified') {
      throw const Cth09BlockedException(
        Cth09BlockedReason.pageBindingUnavailable,
      );
    }
    if (binding?['actor_scope'] != 'verified') {
      throw const Cth09BlockedException(
        Cth09BlockedReason.pageBindingUnavailable,
      );
    }
    if (context.mode == Cth09ContextMode.globalAll &&
        (binding?.containsKey('subject_id') != true ||
            binding?['global_all_granted'] != true ||
            binding?['subject_id'] != null)) {
      throw const Cth09BlockedException(
        Cth09BlockedReason.pageBindingUnavailable,
      );
    }
    if (context.mode == Cth09ContextMode.focused &&
        (binding?['global_all_granted'] != false ||
            binding?['subject_id'] != context.subjectId)) {
      throw const Cth09BlockedException(
        Cth09BlockedReason.pageBindingUnavailable,
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

  static num? _number(Object? value) =>
      value is num && value.isFinite ? value : null;

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
