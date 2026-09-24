enum Acc02ContextState { globalAll, focused, unavailable }

enum Acc02SubjectState { ready, empty, blocked, unavailable, unknown }

class Acc02Subject {
  const Acc02Subject({
    required this.id,
    required this.name,
    required this.domainId,
    required this.subjectType,
    required this.scope,
  });

  final String id;
  final String name;
  final String domainId;
  final String subjectType;
  final String scope;

  factory Acc02Subject.fromJson(Map<String, dynamic> json) {
    final id = _safeId(json['subject_id'] ?? json['id']);
    final name = _safeText(json['name_zh'] ?? json['name_en'] ?? json['name']);
    final domainId = _safeDomain(json['domain_id'] ?? json['domain']);
    if (id == null || name == null || domainId == null) {
      throw const FormatException('ACC-02 Subject row is not safe.');
    }
    final type =
        _safeText(json['subject_type_name'] ?? json['subject_type']) ?? '经营主体';
    final scope = switch (json['scope']) {
      'global' || 'GLOBAL_ALL' => 'global',
      'focus' || 'FOCUS' => 'focus',
      _ => 'focus',
    };
    return Acc02Subject(
      id: id,
      name: name,
      domainId: domainId,
      subjectType: type,
      scope: scope,
    );
  }
}

class Acc02Snapshot {
  const Acc02Snapshot({
    required this.contextState,
    required this.subjectState,
    required this.subjects,
    required this.selectionOnly,
    this.contextName,
    this.contextDomainId,
    this.selectedSubjectId,
  });

  final Acc02ContextState contextState;
  final Acc02SubjectState subjectState;
  final List<Acc02Subject> subjects;
  final bool selectionOnly;
  final String? contextName;
  final String? contextDomainId;
  final String? selectedSubjectId;

  factory Acc02Snapshot.fromResponses({
    Map<String, dynamic>? contextResponse,
    Map<String, dynamic>? subjectsResponse,
    Object? contextError,
    Object? subjectsError,
  }) {
    final context = _asMap(contextResponse?['context']);
    final validContext =
        contextResponse?['ok'] == true &&
        contextResponse?['contract'] == 'lumenis.context.v1' &&
        contextResponse?['selection_only'] == true &&
        context != null;
    final contextState = validContext
        ? switch (context['mode']) {
            'FOCUS' => Acc02ContextState.focused,
            'GLOBAL_ALL' => Acc02ContextState.globalAll,
            _ => Acc02ContextState.unavailable,
          }
        : Acc02ContextState.unavailable;

    final contextName = validContext
        ? _safeText(_asMap(context['display_name'])?['zh']) ??
              _safeText(_asMap(context['display_name'])?['en'])
        : null;
    final contextDomain = validContext
        ? _safeDomain(context['domain_id'])
        : null;
    final contextSubjectId = validContext
        ? _safeId(context['subject_id'])
        : null;

    final rawSubjects = subjectsResponse?['subjects'];
    final parsedSubjects = <Acc02Subject>[];
    var malformedRow = false;
    if (subjectsResponse?['ok'] == true && rawSubjects is List) {
      for (final item in rawSubjects) {
        if (item is! Map) {
          malformedRow = true;
          continue;
        }
        try {
          parsedSubjects.add(
            Acc02Subject.fromJson(
              item.map((key, value) => MapEntry('$key', value)),
            ),
          );
        } on FormatException {
          malformedRow = true;
        }
      }
    }

    final subjectState = _subjectState(
      response: subjectsResponse,
      rawSubjects: rawSubjects,
      parsedSubjects: parsedSubjects,
      malformedRow: malformedRow,
      error: subjectsError,
    );

    return Acc02Snapshot(
      contextState: contextState,
      subjectState: subjectState,
      subjects: parsedSubjects,
      selectionOnly: subjectsResponse?['selection_only'] == true,
      contextName: contextName,
      contextDomainId: contextDomain,
      selectedSubjectId: contextSubjectId,
    );
  }
}

Acc02SubjectState _subjectState({
  required Map<String, dynamic>? response,
  required Object? rawSubjects,
  required List<Acc02Subject> parsedSubjects,
  required bool malformedRow,
  required Object? error,
}) {
  if (response == null || response['ok'] != true || rawSubjects is! List) {
    return _failureState(error);
  }
  if (parsedSubjects.isEmpty && malformedRow) {
    return Acc02SubjectState.unavailable;
  }
  if (parsedSubjects.isEmpty) {
    return Acc02SubjectState.empty;
  }
  return Acc02SubjectState.ready;
}

Acc02SubjectState _failureState(Object? error) {
  final message = error.toString().toLowerCase();
  if (message.contains('http 401') || message.contains('auth_required')) {
    return Acc02SubjectState.blocked;
  }
  if (message.contains('http 403') || message.contains('permission')) {
    return Acc02SubjectState.blocked;
  }
  if (message.contains('unavailable') || message.contains('timeout')) {
    return Acc02SubjectState.unavailable;
  }
  return Acc02SubjectState.unknown;
}

Map<String, Object?>? _asMap(Object? value) {
  if (value is! Map) return null;
  return value.map((key, value) => MapEntry('$key', value));
}

String? _safeId(Object? value) {
  if (value is! String || value.trim().isEmpty || value.length > 80) {
    return null;
  }
  final text = value.trim();
  if (!RegExp(r'^[A-Za-z0-9._:-]+$').hasMatch(text)) return null;
  return text;
}

String? _safeDomain(Object? value) {
  final text = value is String ? value.trim().toUpperCase() : '';
  return switch (text) {
    'CTH' => 'CTH',
    'BMP' || 'ZBMP' => 'BMP',
    _ => null,
  };
}

String? _safeText(Object? value) {
  if (value is! String || value.trim().isEmpty || value.length > 140) {
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
