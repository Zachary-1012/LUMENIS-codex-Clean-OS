import '../../../core/lumenis_core_client.dart';

enum Cth10ContextMode { globalAll, focused }

class Cth10Context {
  const Cth10Context({required this.mode, this.subjectId, this.displayName});

  final Cth10ContextMode mode;
  final String? subjectId;
  final String? displayName;

  String get contractMode => switch (mode) {
    Cth10ContextMode.globalAll => 'GLOBAL_ALL',
    Cth10ContextMode.focused => 'FOCUS',
  };
}

enum Cth10ContentState { ready, empty, notCollected, partial }

class Cth10EvidenceReference {
  const Cth10EvidenceReference({
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

class Cth10ReportBlock {
  const Cth10ReportBlock({
    required this.id,
    required this.title,
    required this.kind,
    required this.body,
    required this.status,
  });

  final String id;
  final String title;
  final String kind;
  final String body;
  final String status;
}

class Cth10Report {
  const Cth10Report({
    required this.id,
    required this.title,
    required this.period,
    required this.state,
    required this.scopeLabel,
    required this.blocks,
    required this.evidence,
    this.sourceBrief,
  });

  final String id;
  final String title;
  final String period;
  final String state;
  final String scopeLabel;
  final List<Cth10ReportBlock> blocks;
  final List<Cth10EvidenceReference> evidence;
  final Cth10SourceBrief? sourceBrief;
}

/// Presentation projection of the existing owner response, after read binding.
/// These counts describe returned sources, never market or business metrics.
class Cth10SourceBrief {
  const Cth10SourceBrief({
    required this.contentHash,
    required this.status,
    required this.coverage,
    required this.freshness,
    required this.collectionState,
    required this.sample,
    required this.records,
  });

  final String contentHash, status, coverage, freshness, collectionState;
  final Map<String, dynamic> sample;
  final List<Map<String, dynamic>> records;
}

class Cth10WorkspaceData {
  const Cth10WorkspaceData({
    required this.context,
    required this.state,
    required this.reports,
  });

  final Cth10Context context;
  final Cth10ContentState state;
  final List<Cth10Report> reports;
}

enum Cth10BlockedReason {
  contextUnavailable,
  pageBindingUnavailable,
  evidenceBindingUnavailable,
  reportScopeUnavailable,
}

class Cth10BlockedException implements Exception {
  const Cth10BlockedException(this.reason);

  final Cth10BlockedReason reason;
}

abstract interface class Cth10Repository {
  Future<Cth10WorkspaceData> load();
}

class CoreCth10Repository implements Cth10Repository {
  CoreCth10Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Cth10WorkspaceData> load() async {
    final context = _decodeContext(await _client.settingsContext());
    final response = await _client.screen('CTH-10');
    final binding = _map(response['binding']);
    _requireReadBinding(response, binding, context);
    return _decodeWorkspace(response, context);
  }

  Cth10WorkspaceData _decodeWorkspace(
    Map<String, dynamic> response,
    Cth10Context context,
  ) {
    final sections = _maps(response['sections']);
    final reportSection = _firstSection(sections, 'reports');
    if (reportSection == null) {
      return Cth10WorkspaceData(
        context: context,
        state: Cth10ContentState.notCollected,
        reports: const [],
      );
    }

    var droppedRows = false;
    final reports = <Cth10Report>[];
    for (final raw in _maps(reportSection['items'])) {
      final decoded = _decodeReport(
        raw,
        context,
        _map(response['source_brief']),
      );
      if (decoded == null) {
        droppedRows = true;
      } else {
        reports.add(decoded.value);
        droppedRows |= decoded.dropped;
      }
    }

    final state = droppedRows
        ? Cth10ContentState.partial
        : reports.isEmpty
        ? Cth10ContentState.empty
        : Cth10ContentState.ready;
    return Cth10WorkspaceData(
      context: context,
      state: state,
      reports: List.unmodifiable(reports),
    );
  }

  ({Cth10Report value, bool dropped})? _decodeReport(
    Map<String, dynamic> raw,
    Cth10Context context,
    Map<String, dynamic>? sourceBrief,
  ) {
    final id = _safeText(raw['id']);
    final title = _safeText(raw['title']);
    final period = _safeText(raw['period']);
    final scopeLabel = _safeText(raw['scope']);
    if (id.isEmpty || title.isEmpty || period.isEmpty || scopeLabel.isEmpty) {
      return null;
    }

    final evidence = _decodeEvidence(raw['evidence'], context);
    if (evidence.items.isEmpty) return null;

    final rawBlocks = raw['blocks'];
    if (rawBlocks is! List) return null;
    final blocks = _maps(
      rawBlocks,
    ).map(_decodeBlock).whereType<Cth10ReportBlock>().toList(growable: false);
    if (blocks.isEmpty) return null;

    final brief = id.startsWith('source-brief:')
        ? _decodeSourceBrief(
            sourceBrief,
            id,
            scopeLabel,
            blocks,
            evidence.items,
            context,
          )
        : null;
    // Never fall back to diagnostic Markdown when the structured projection
    // does not belong to this exact report/source snapshot.
    if (id.startsWith('source-brief:') && brief == null) return null;

    return (
      value: Cth10Report(
        id: id,
        title: title,
        period: period,
        state: _safeText(raw['state']),
        scopeLabel: scopeLabel,
        blocks: blocks,
        evidence: evidence.items,
        sourceBrief: brief,
      ),
      dropped: evidence.dropped || blocks.length != rawBlocks.length,
    );
  }

  Cth10SourceBrief? _decodeSourceBrief(
    Map<String, dynamic>? brief,
    String reportId,
    String scopeLabel,
    List<Cth10ReportBlock> blocks,
    List<Cth10EvidenceReference> evidence,
    Cth10Context context,
  ) {
    if (brief == null) return null;
    final hash = brief['content_hash'];
    final scope = _map(brief['scope']);
    final sample = _map(brief['sample']);
    final records = _maps(brief['records']);
    final focused = context.mode == Cth10ContextMode.focused;
    if (hash is! String ||
        !RegExp(r'^[0-9a-f]{64}$').hasMatch(hash) ||
        reportId != 'source-brief:$hash' ||
        !blocks.any(
          (block) =>
              block.kind == 'source_brief' && block.body == brief['markdown'],
        ) ||
        scope?['product_id'] != 'CTH' ||
        scope?['domain_id'] != 'cth' ||
        scope?['global'] != !focused ||
        scope?['subject_id'] != (focused ? context.subjectId : null) ||
        scope?['brand_focus_id'] != null ||
        scope?['entity_label'] != scopeLabel ||
        brief['records'] is! List ||
        records.length != (brief['records'] as List).length ||
        records.length != evidence.length ||
        sample?['returned_verified_count'] != records.length ||
        !{'AVAILABLE', 'PARTIAL', 'EMPTY'}.contains(brief['status'])) {
      return null;
    }
    for (final key in [
      'candidate_count',
      'scanned_count',
      'rejected_count',
      'withheld_count',
    ]) {
      final count = sample?[key];
      if (count is! int || count < 0) return null;
    }
    if (sample?['truncated'] is! bool || sample?['withheld'] is! bool) {
      return null;
    }
    for (final key in ['source_type_counts_sample', 'platform_counts_sample']) {
      final counts = _map(sample?[key]);
      if (counts == null ||
          counts.entries.any(
            (entry) =>
                _safeText(entry.key).isEmpty ||
                entry.value is! int ||
                (entry.value as int) < 0,
          )) {
        return null;
      }
    }
    final identities = <String>{};
    for (final record in records) {
      final id = record['evidence_id'];
      if (id is! String ||
          !RegExp(r'^[1-9][0-9]*$').hasMatch(id) ||
          record['scope_evidence_ref'] != id ||
          !evidence.any((item) => item.id == 'evidence:canonical:$id') ||
          !identities.add(id) ||
          _safeText(record['source_id']).isEmpty ||
          (focused && record['subject_id'] != context.subjectId)) {
        return null;
      }
    }
    return Cth10SourceBrief(
      contentHash: hash,
      status: brief['status'] as String,
      coverage: _safeText(brief['coverage']),
      freshness: _safeText(brief['freshness']),
      collectionState: _safeText(brief['collection_state']),
      sample: Map.unmodifiable(sample!),
      records: List.unmodifiable(
        records.map((record) => Map<String, dynamic>.unmodifiable(record)),
      ),
    );
  }

  Cth10ReportBlock? _decodeBlock(Map<String, dynamic> raw) {
    final id = _safeText(raw['id']);
    final title = _safeText(raw['title']);
    final body = _safeText(raw['body'], maxLength: null);
    if (id.isEmpty || title.isEmpty || body.isEmpty) return null;
    return Cth10ReportBlock(
      id: id,
      title: title,
      kind: _safeText(raw['kind']),
      body: body,
      status: _safeText(raw['status']),
    );
  }

  ({List<Cth10EvidenceReference> items, bool dropped}) _decodeEvidence(
    Object? value,
    Cth10Context context,
  ) {
    if (value is! List) return (items: const [], dropped: true);
    final result = <Cth10EvidenceReference>[];
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

  Cth10EvidenceReference? _decodeEvidenceReference(
    Map<String, dynamic> raw,
    Cth10Context context,
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
    if (context.mode == Cth10ContextMode.globalAll) {
      if (rawSubjectId != null) return null;
    } else if (rawSubjectId != context.subjectId) {
      return null;
    }
    return Cth10EvidenceReference(
      id: id,
      quote: _safeText(raw['quote'], maxLength: null),
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

  static Cth10Context _decodeContext(Map<String, dynamic> response) {
    if (response['ok'] != true ||
        response['contract'] != 'lumenis.context.v1' ||
        response['selection_only'] != true) {
      throw const Cth10BlockedException(Cth10BlockedReason.contextUnavailable);
    }

    final context = _map(response['context']);
    final mode = context?['mode'];
    if (mode == 'GLOBAL_ALL' &&
        context?['domain_id'] == null &&
        context?['subject_id'] == null) {
      return const Cth10Context(mode: Cth10ContextMode.globalAll);
    }

    if (mode == 'FOCUS' && context?['domain_id'] == 'CTH') {
      final subjectId = context?['subject_id'];
      if (subjectId is String && subjectId.trim().isNotEmpty) {
        return Cth10Context(
          mode: Cth10ContextMode.focused,
          subjectId: subjectId.trim(),
          displayName: _contextDisplayName(context?['display_name']),
        );
      }
    }

    throw const Cth10BlockedException(Cth10BlockedReason.contextUnavailable);
  }

  static void _requireReadBinding(
    Map<String, dynamic> response,
    Map<String, dynamic>? binding,
    Cth10Context context,
  ) {
    if (response['ok'] != true || response['screen'] != 'CTH-10') {
      throw const FormatException(
        'CTH-10 response does not match its contract.',
      );
    }
    if (binding?['screen'] != 'CTH-10' ||
        binding?['contract'] != 'lumenis.scope-read-binding.v1' ||
        binding?['module'] != 'commercial_realtime_stream' ||
        binding?['applied'] != true ||
        binding?['domain_id'] != 'CTH' ||
        binding?['product_id'] != 'CTH' ||
        binding?['context_mode'] != context.contractMode ||
        binding?['canonical_scope'] != context.contractMode ||
        binding?['scope_verified'] != true ||
        binding?['read_allowed'] != true ||
        binding?['evidence_lineage'] != 'verified') {
      throw const Cth10BlockedException(
        Cth10BlockedReason.pageBindingUnavailable,
      );
    }
    final policy = binding?['policy'];
    final actorScope = binding?['actor_scope'];
    final localRead =
        policy == 'local-workspace-read-v1' && actorScope == 'anonymous_read';
    final actorRead =
        policy == 'actor-exact-scope-v1' && actorScope == 'authenticated';
    if (!localRead && !actorRead) {
      throw const Cth10BlockedException(
        Cth10BlockedReason.pageBindingUnavailable,
      );
    }
    if (context.mode == Cth10ContextMode.globalAll &&
        (binding?.containsKey('subject_id') != true ||
            binding?['global_all_granted'] != actorRead ||
            binding?['subject_id'] != null)) {
      throw const Cth10BlockedException(
        Cth10BlockedReason.pageBindingUnavailable,
      );
    }
    if (context.mode == Cth10ContextMode.focused &&
        (binding?['global_all_granted'] != false ||
            binding?['subject_id'] != context.subjectId)) {
      throw const Cth10BlockedException(
        Cth10BlockedReason.pageBindingUnavailable,
      );
    }
    if (binding?['evidence_lineage'] != 'verified') {
      throw const Cth10BlockedException(
        Cth10BlockedReason.evidenceBindingUnavailable,
      );
    }
    if (binding?['scope_verified'] != true) {
      throw const Cth10BlockedException(
        Cth10BlockedReason.reportScopeUnavailable,
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

  static String _safeText(Object? value, {int? maxLength = 240}) {
    if (value is! String) return '';
    final text = value.trim();
    // Labels are bounded; report prose and quotations must retain the full
    // authorized text rather than disappear under a label-length limit.
    if (text.isEmpty || (maxLength != null && text.length > maxLength)) {
      return '';
    }
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
