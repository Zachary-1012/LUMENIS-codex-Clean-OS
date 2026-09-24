enum Ai02TaskState {
  pending,
  running,
  completed,
  blocked,
  unavailable,
  unknown,
}

enum Ai02BindingState { bound, unavailable, blocked, unknown }

enum Ai02ScopeMode { globalAll, focus, unknown }

class Ai02ExecutionProof {
  const Ai02ExecutionProof({
    required this.actorBound,
    required this.scopeMode,
    required this.scopeAuthorized,
    required this.scopeDomainId,
    required this.scopeSubjectId,
    required this.readAllowed,
    required this.executeAllowed,
    required this.evidenceRefsPresent,
    required this.evidenceLineageVerified,
    required this.evidenceIntegrityVerified,
    required this.callableContract,
  });

  const Ai02ExecutionProof.unverified()
    : actorBound = false,
      scopeMode = Ai02ScopeMode.unknown,
      scopeAuthorized = false,
      scopeDomainId = null,
      scopeSubjectId = null,
      readAllowed = false,
      executeAllowed = false,
      evidenceRefsPresent = false,
      evidenceLineageVerified = false,
      evidenceIntegrityVerified = false,
      callableContract = false;

  final bool actorBound;
  final Ai02ScopeMode scopeMode;
  final bool scopeAuthorized;
  final String? scopeDomainId;
  final String? scopeSubjectId;
  final bool readAllowed;
  final bool executeAllowed;
  final bool evidenceRefsPresent;
  final bool evidenceLineageVerified;
  final bool evidenceIntegrityVerified;
  final bool callableContract;

  bool get exactScope {
    if (!scopeAuthorized || scopeDomainId == null) return false;
    return switch (scopeMode) {
      Ai02ScopeMode.globalAll => scopeSubjectId == null,
      Ai02ScopeMode.focus => scopeSubjectId != null,
      Ai02ScopeMode.unknown => false,
    };
  }

  bool get ready =>
      actorBound &&
      exactScope &&
      readAllowed &&
      executeAllowed &&
      evidenceRefsPresent &&
      evidenceLineageVerified &&
      evidenceIntegrityVerified &&
      callableContract;
}

class Ai02TaskStep {
  const Ai02TaskStep({
    required this.key,
    required this.label,
    required this.state,
  });

  final String key;
  final String label;
  final Ai02TaskState state;

  factory Ai02TaskStep.fromJson(Map<String, dynamic> json, int index) {
    final key = _safeId(json['key'] ?? json['id']) ?? 'stage-${index + 1}';
    final label = _safeText(json['label'] ?? json['label_key']);
    if (label == null) {
      throw const FormatException('AI-02 task step has no safe label.');
    }
    return Ai02TaskStep(
      key: key,
      label: label,
      state: _parseState(json['state']),
    );
  }
}

class Ai02Snapshot {
  const Ai02Snapshot({
    required this.bindingState,
    required this.steps,
    required this.evidenceRefs,
    required this.executionProof,
    required this.unavailableFields,
    this.generatedAt,
  });

  final Ai02BindingState bindingState;
  final List<Ai02TaskStep> steps;
  final List<String> evidenceRefs;
  final Ai02ExecutionProof executionProof;
  final List<String> unavailableFields;
  final String? generatedAt;

  bool get isBound => bindingState == Ai02BindingState.bound;
  bool get hasExecutableRoute => isBound && executionProof.ready;

  factory Ai02Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'AI-02') {
      throw const FormatException('AI-02 response is not valid.');
    }
    final binding = _asMap(response['binding']);
    final sections = _asMapList(response['sections']);
    final rawSteps =
        response['task_steps'] ??
        sections
            .expand(
              (section) => _asList(
                section['task_steps'] ?? section['steps'] ?? section['items'],
              ),
            )
            .toList(growable: false);
    final steps = <Ai02TaskStep>[];
    if (rawSteps is List) {
      for (var index = 0; index < rawSteps.length; index++) {
        final item = rawSteps[index];
        if (item is! Map) continue;
        try {
          steps.add(
            Ai02TaskStep.fromJson(
              item.map((key, value) => MapEntry('$key', value)),
              index,
            ),
          );
        } on FormatException {
          // A malformed stage is not shown as a fabricated stage.
        }
      }
    }
    final refs = <String>[];
    final rawRefs =
        response['evidence_refs'] ??
        sections
            .expand((section) => _asList(section['evidence_refs']))
            .toList();
    if (rawRefs is List) {
      for (final ref in rawRefs) {
        final safe = _safeEvidenceId(ref);
        if (safe != null && !refs.contains(safe)) refs.add(safe);
      }
    }
    final actor = _asMap(response['actor'] ?? binding?['actor']);
    final scope = _asMap(response['scope'] ?? binding?['scope']);
    final permission = _asMap(response['permission']);
    final evidence = _asMap(response['evidence']);
    final scopeMode = _parseScopeMode(scope?['mode']);
    final scopeDomainId = _safeDomain(scope?['domain_id'] ?? scope?['domain']);
    final scopeSubjectId = _safeId(scope?['subject_id']);
    final executionProof = Ai02ExecutionProof(
      actorBound:
          actor?['bound'] == true &&
          actor?['source'] == 'server' &&
          _safeId(actor?['id']) != null,
      scopeMode: scopeMode,
      scopeAuthorized: scope?['authorized'] == true,
      scopeDomainId: scopeDomainId,
      scopeSubjectId: scopeSubjectId,
      readAllowed:
          permission?['read'] == true && permission?['decision'] == 'ALLOW',
      executeAllowed:
          permission?['execute'] == true && permission?['decision'] == 'ALLOW',
      evidenceRefsPresent: refs.isNotEmpty,
      evidenceLineageVerified: evidence?['lineage_verified'] == true,
      evidenceIntegrityVerified: evidence?['integrity_verified'] == true,
      callableContract: _hasCallableContract(response['actions']),
    );
    final isBound =
        response['bound'] == true && response['source'] == 'runtime';
    final state = isBound
        ? Ai02BindingState.bound
        : binding?['blocked'] is List
        ? Ai02BindingState.blocked
        : Ai02BindingState.unavailable;
    return Ai02Snapshot(
      bindingState: state,
      steps: steps,
      evidenceRefs: refs,
      executionProof: executionProof,
      unavailableFields: _asStringList(binding?['unavailable']),
      generatedAt: _safeText(response['generated_at']),
    );
  }
}

Ai02TaskState _parseState(Object? value) => switch ('$value'.toLowerCase()) {
  'pending' || 'scheduled' => Ai02TaskState.pending,
  'running' || 'in_progress' => Ai02TaskState.running,
  'completed' || 'done' => Ai02TaskState.completed,
  'blocked' || 'denied' => Ai02TaskState.blocked,
  'unavailable' || 'offline' => Ai02TaskState.unavailable,
  _ => Ai02TaskState.unknown,
};

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

Ai02ScopeMode _parseScopeMode(Object? value) => switch (value) {
  'GLOBAL_ALL' => Ai02ScopeMode.globalAll,
  'FOCUS' => Ai02ScopeMode.focus,
  _ => Ai02ScopeMode.unknown,
};

String? _safeDomain(Object? value) {
  final text = value is String ? value.trim().toUpperCase() : '';
  return switch (text) {
    'CTH' => 'CTH',
    'BMP' || 'ZBMP' => 'BMP',
    _ => null,
  };
}

bool _hasCallableContract(Object? value) {
  if (value is! List) return false;
  for (final item in value) {
    if (item is! Map || item['capability_status'] != 'VERIFIED_AVAILABLE') {
      continue;
    }
    if (_safeId(item['action_id'] ?? item['id']) == null) continue;
    final callable = _asMap(item['callable']);
    final requestFields = _asStringList(callable?['request_fields']);
    final responseFields = _asStringList(callable?['response_fields']);
    final requestIsSupported =
        requestFields.contains('task') || requestFields.contains('intent');
    final responseIsSupported =
        responseFields.contains('execution_id') &&
        responseFields.contains('status');
    if (callable?['available'] == true &&
        callable?['method'] == 'POST' &&
        callable?['route'] == '/api/experience/ai/intent' &&
        requestIsSupported &&
        responseIsSupported) {
      return true;
    }
  }
  return false;
}

String? _safeId(Object? value) {
  if (value is! String || value.trim().isEmpty || value.length > 80) {
    return null;
  }
  final text = value.trim();
  return RegExp(r'^[A-Za-z0-9._:-]+$').hasMatch(text) ? text : null;
}

String? _safeEvidenceId(Object? value) {
  if (value is! String || value.length > 100) return null;
  final text = value.trim();
  if (text.isEmpty || text.contains('/') || text.contains('\\')) return null;
  return RegExp(r'^(EV[-:][A-Za-z0-9_.:-]+|[A-Z]{2,8}-\d+)$').hasMatch(text)
      ? text
      : null;
}

String? _safeText(Object? value) {
  if (value is! String || value.trim().isEmpty || value.length > 180) {
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
