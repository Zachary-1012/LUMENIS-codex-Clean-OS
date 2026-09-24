enum Ai03BindingState { bound, unavailable, blocked, unknown }

enum Ai03ContextMode { globalAll, focus, unknown }

class Ai03Context {
  const Ai03Context({
    required this.mode,
    required this.domainId,
    required this.focusId,
  });

  final Ai03ContextMode mode;
  final String? domainId;
  final String? focusId;

  bool matches(Ai03Context other) =>
      mode == other.mode &&
      domainId == other.domainId &&
      focusId == other.focusId;
}

class Ai03CanonicalEvidence {
  const Ai03CanonicalEvidence({
    required this.id,
    required this.type,
    required this.context,
    required this.readAllowed,
    required this.lineageVerified,
    required this.integrityVerified,
  });

  final String id;
  final String type;
  final Ai03Context context;
  final bool readAllowed;
  final bool lineageVerified;
  final bool integrityVerified;
}

class Ai03Citation {
  const Ai03Citation({
    required this.id,
    required this.evidence,
    this.title,
    this.passage,
  });

  final String id;
  final Ai03CanonicalEvidence evidence;
  final String? title;
  final String? passage;
}

class Ai03ThreadEntry {
  const Ai03ThreadEntry({
    required this.speaker,
    required this.text,
    required this.citations,
  });

  final String speaker;
  final String text;
  final List<Ai03Citation> citations;

  factory Ai03ThreadEntry.fromJson(
    Map<String, dynamic> json, {
    required Ai03Context? context,
  }) {
    final text = _safeText(json['text'] ?? json['message'] ?? json['content']);
    if (text == null) {
      throw const FormatException('AI-03 thread entry has no safe text.');
    }
    final speakerValue = json['who'] ?? json['role'] ?? 'assistant';
    final speaker = switch ('$speakerValue'.toLowerCase()) {
      'user' || 'human' => 'user',
      'system' => 'system',
      _ => 'assistant',
    };
    return Ai03ThreadEntry(
      speaker: speaker,
      text: text,
      citations: _parseCitations(
        json['cites'] ?? json['citations'],
        context: context,
      ),
    );
  }
}

class Ai03Snapshot {
  const Ai03Snapshot({
    required this.bindingState,
    required this.thread,
    required this.unavailableFields,
    this.context,
    this.generatedAt,
  });

  final Ai03BindingState bindingState;
  final List<Ai03ThreadEntry> thread;
  final List<String> unavailableFields;
  final Ai03Context? context;
  final String? generatedAt;

  bool get isBound => bindingState == Ai03BindingState.bound;
  bool get hasEvidence => thread.any((entry) => entry.citations.isNotEmpty);

  factory Ai03Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'AI-03') {
      throw const FormatException('AI-03 response is not valid.');
    }
    final binding = _asMap(response['binding']);
    final context = _parseContext(
      response['context'] ?? response['scope'] ?? binding?['context'],
    );
    final sections = _asMapList(response['sections']);
    final rawThread =
        response['thread'] ??
        sections
            .where(
              (section) =>
                  section['type'] == 'thread' || section['type'] == 'messages',
            )
            .expand(
              (section) => _asList(
                section['items'] ?? section['thread'] ?? section['messages'],
              ),
            )
            .toList(growable: false);
    final entries = <Ai03ThreadEntry>[];
    if (rawThread is List) {
      for (final item in rawThread) {
        if (item is! Map) continue;
        try {
          entries.add(
            Ai03ThreadEntry.fromJson(
              item.map((key, value) => MapEntry('$key', value)),
              context: context,
            ),
          );
        } on FormatException {
          // Do not render an untrusted or malformed claim.
        }
      }
    }
    final isBound =
        response['bound'] == true && response['source'] == 'runtime';
    final state = isBound
        ? Ai03BindingState.bound
        : binding?['blocked'] is List
        ? Ai03BindingState.blocked
        : Ai03BindingState.unavailable;
    return Ai03Snapshot(
      bindingState: state,
      thread: entries,
      unavailableFields: _asStringList(binding?['unavailable']),
      context: context,
      generatedAt: _safeText(response['generated_at']),
    );
  }
}

List<Ai03Citation> _parseCitations(
  Object? value, {
  required Ai03Context? context,
}) {
  if (value is! List) return const [];
  if (context == null) return const [];
  final citations = <Ai03Citation>[];
  for (final item in value) {
    if (item is! Map) continue;
    final map = item.map((key, value) => MapEntry('$key', value));
    final evidence = _parseCanonicalEvidence(
      map['evidence'] ?? map['canonical_evidence'],
      context: context,
    );
    if (evidence == null) continue;
    citations.add(
      Ai03Citation(
        id: evidence.id,
        evidence: evidence,
        title: _safeText(map['title'] ?? map['source_title']),
        passage: _safeText(map['passage'] ?? map['quote']),
      ),
    );
  }
  return citations;
}

Ai03CanonicalEvidence? _parseCanonicalEvidence(
  Object? value, {
  required Ai03Context context,
}) {
  final record = _asMap(value);
  if (record == null || record['evidence_version'] != 2) return null;
  if (record['canonical'] != true || record['scope_verified'] != true) {
    return null;
  }
  final id = _safeEvidenceId(record['evidence_id'] ?? record['canonical_ref']);
  final type = _knownEvidenceType(record['type']);
  final evidenceContext = _parseContext(
    record['context'] ?? record['scope'],
    requireGlobalMarker: true,
  );
  final permission = _asMap(record['permission']);
  final lineage = _asSafeLineage(record['lineage']);
  final integrity = _asMap(record['integrity']);
  final integrityVersion =
      integrity?['version'] ?? record['integrity_version'];
  final integrityStatus = integrity?['status'] ?? record['integrity_status'];
  final integrityAlgorithm =
      integrity?['algorithm'] ?? record['integrity_algorithm'];
  final integrityDigest = integrity?['digest'] ?? record['integrity_digest'];
  final integrityVerified =
      integrityVersion == 2 &&
      (integrity?['verified'] == true || integrityStatus == 'verified') &&
      (integrityAlgorithm == 'sha256' || integrityAlgorithm == 'hmac-sha256') &&
      _isDigest(integrityDigest);
  if (id == null || type == null || evidenceContext == null) return null;
  if (!evidenceContext.matches(context)) return null;
  if (permission?['read'] != true || permission?['decision'] != 'ALLOW') {
    return null;
  }
  if (record['read_allowed'] != true ||
      record['lineage_verified'] != true ||
      lineage.isEmpty ||
      !integrityVerified) {
    return null;
  }
  return Ai03CanonicalEvidence(
    id: id,
    type: type,
    context: evidenceContext,
    readAllowed: true,
    lineageVerified: true,
    integrityVerified: true,
  );
}

Ai03Context? _parseContext(
  Object? value, {
  bool requireGlobalMarker = false,
}) {
  final raw = _asMap(value);
  if (raw == null) return null;
  final modeText = raw['mode'] is String
      ? (raw['mode'] as String).trim().toUpperCase()
      : '';
  final mode = switch (modeText) {
    'GLOBAL_ALL' => Ai03ContextMode.globalAll,
    'FOCUS' => Ai03ContextMode.focus,
    _ => Ai03ContextMode.unknown,
  };
  final domain = _safeDomain(raw['domain_id'] ?? raw['domain']);
  if (mode == Ai03ContextMode.globalAll) {
    if (requireGlobalMarker && raw['global'] != true) return null;
    if (_present(raw['subject_id']) || _present(raw['brand_focus_id'])) {
      return null;
    }
    return Ai03Context(
      mode: mode,
      domainId: domain,
      focusId: null,
    );
  }
  if (mode != Ai03ContextMode.focus || domain == null) return null;
  final subjectId = _safeId(raw['subject_id']);
  final brandFocusId = _safeId(raw['brand_focus_id']);
  if (domain == 'CTH' && (subjectId == null || brandFocusId != null)) {
    return null;
  }
  if (domain == 'BMP' && (brandFocusId == null || subjectId != null)) {
    return null;
  }
  return Ai03Context(
    mode: mode,
    domainId: domain,
    focusId: subjectId ?? brandFocusId,
  );
}

Map<String, Object?>? _asMap(Object? value) {
  if (value is! Map) return null;
  return value.map((key, value) => MapEntry('$key', value));
}

List<Map<String, Object?>> _asMapList(Object? value) {
  if (value is! List) return const [];
  return value
      .map(_asMap)
      .whereType<Map<String, Object?>>()
      .toList(growable: false);
}

List<Object?> _asList(Object? value) => value is List ? value : const [];

List<String> _asStringList(Object? value) => value is List
    ? value
          .whereType<String>()
          .where((item) => item.length <= 100)
          .toList(growable: false)
    : const [];

String? _safeEvidenceId(Object? value) {
  if (value is! String || value.trim().isEmpty || value.length > 100) {
    return null;
  }
  final text = value.trim();
  if (text.contains('/') || text.contains('\\')) return null;
  return RegExp(
        r'^(EV[-:][A-Za-z0-9_.:-]+|PEV_[A-Za-z0-9]+|[A-Z]{2,8}-\d+|\d+)$',
      ).hasMatch(text)
      ? text
      : null;
}

String? _safeId(Object? value) {
  if (value is! String || value.trim().isEmpty || value.length > 100) {
    return null;
  }
  final text = value.trim();
  return RegExp(r'^[A-Za-z0-9_.:-]+$').hasMatch(text) ? text : null;
}

String? _safeDomain(Object? value) {
  final text = value is String ? value.trim().toUpperCase() : '';
  return switch (text) {
    'CTH' => 'CTH',
    'BMP' || 'ZBMP' => 'BMP',
    _ => null,
  };
}

String? _knownEvidenceType(Object? value) => switch (value) {
  'COMMENT' ||
  'CLUSTER' ||
  'FINDING' ||
  'METRIC' ||
  'RISK' ||
  'SOURCE' => '$value',
  _ => null,
};

List<String> _asSafeLineage(Object? value) => value is List
    ? value
          .whereType<String>()
          .map((item) => item.trim())
          .where(
            (item) =>
                item.isNotEmpty &&
                item.length <= 60 &&
                RegExp(r'^[A-Za-z][A-Za-z0-9 _-]*$').hasMatch(item),
          )
          .toList(growable: false)
    : const [];

bool _isDigest(Object? value) =>
    value is String && RegExp(r'^[0-9a-f]{64}$').hasMatch(value);

bool _present(Object? value) => value is String && value.trim().isNotEmpty;

String? _safeText(Object? value) {
  if (value is! String || value.trim().isEmpty || value.length > 280) {
    return null;
  }
  final text = value.trim();
  final lower = text.toLowerCase();
  if (text.contains(RegExp(r'[\r\n\x00]')) ||
      text.contains('/') ||
      text.contains('\\') ||
      lower.contains('token') ||
      lower.contains('secret') ||
      lower.contains('password') ||
      lower.contains('provider=') ||
      lower.contains('model=')) {
    return null;
  }
  return text;
}
