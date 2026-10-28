class Ai02TaskStep {
  const Ai02TaskStep(this.label, this.status);
  final String label;
  final String status;
}

class Ai02WorkRef {
  const Ai02WorkRef(this.kind, this.artifactId, this.title);
  final String kind, artifactId, title;
}

class Ai02Task {
  const Ai02Task({
    required this.id,
    required this.title,
    required this.input,
    required this.status,
    required this.canCancel,
    required this.canResume,
    required this.steps,
    required this.works,
    this.createdAt,
    this.updatedAt,
    this.output,
    this.errorCode,
    this.requestId,
    this.resultRestricted = false,
  });
  final String id, title, input, status;
  final bool canCancel, canResume;
  final DateTime? createdAt, updatedAt;
  final String? output, errorCode;
  final String? requestId;
  final bool resultRestricted;
  final List<Ai02TaskStep> steps;
  final List<Ai02WorkRef> works;
  bool get active => const {
    'pending',
    'queued',
    'created',
    'running',
    'executing',
    'parsing',
    'dispatching',
    'cancel_requested',
  }.contains(status);

  factory Ai02Task.fromJson(Map<String, dynamic> row) {
    final id = row['task_id'] ?? row['execution_id'];
    final view = row['workspace_view'];
    if (id is! String ||
        !RegExp(r'^(?:task_|skilljob_)[A-Za-z0-9_-]{8,128}$').hasMatch(id) ||
        view is! Map ||
        view['status'] is! String ||
        view['can_cancel'] is! bool ||
        view['can_resume'] is! bool) {
      throw const FormatException('Invalid task workspace response.');
    }
    String text(Object? value, {int max = 16000}) =>
        value is String && value.length <= max ? value : '';
    final input = text(view['input']);
    final title = text(view['title'], max: 240);
    final output = text(view['output_text'], max: 200000);
    final steps = <Ai02TaskStep>[];
    for (final row
        in view['steps'] is List ? view['steps'] as List : const []) {
      if (row is Map && row['label'] is String && row['status'] is String) {
        steps.add(Ai02TaskStep(text(row['label'], max: 240), row['status']));
      }
    }
    final works = <Ai02WorkRef>[];
    for (final row
        in view['work_refs'] is List ? view['work_refs'] as List : const []) {
      if (row is! Map) continue;
      final artifact = row['artifact_id'];
      if (artifact is String &&
          RegExp(r'^ART-[a-f0-9]{16}$').hasMatch(artifact) &&
          const {
            'report',
            'manuscript',
            'media',
            'video',
            'podcast',
          }.contains(row['kind'])) {
        works.add(
          Ai02WorkRef(row['kind'], artifact, text(row['title'], max: 240)),
        );
      }
    }
    final error = view['error_code'];
    final requestId = row['request_id'] ?? view['request_id'];
    if (requestId != null &&
        (requestId is! String ||
            !RegExp(r'^[0-9a-f]{32}$').hasMatch(requestId))) {
      throw const FormatException('Invalid task request identity.');
    }
    return Ai02Task(
      id: id,
      title: title,
      input: input,
      status: view['status'],
      canCancel: view['can_cancel'] == true,
      canResume: view['can_resume'] == true,
      createdAt: DateTime.tryParse('${view['created_at']}'),
      updatedAt: DateTime.tryParse('${view['updated_at']}'),
      output: output.isEmpty ? null : output,
      requestId: requestId as String?,
      resultRestricted: view['result_access_state'] == 'RESTRICTED',
      errorCode:
          error is String && RegExp(r'^[A-Z][A-Z0-9_]{1,95}$').hasMatch(error)
          ? error
          : null,
      steps: List.unmodifiable(steps),
      works: List.unmodifiable(works),
    );
  }
}

class Ai02Snapshot {
  const Ai02Snapshot({required this.tasks, this.nextOffset});
  final List<Ai02Task> tasks;
  final int? nextOffset;
  factory Ai02Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true ||
        response['tasks'] is! List ||
        response['has_more'] is! bool ||
        (response['has_more'] == true && response['next_offset'] is! int)) {
      throw const FormatException('Invalid task list response.');
    }
    final tasks = (response['tasks'] as List)
        .map((row) {
          if (row is! Map) throw const FormatException('Invalid task row.');
          return Ai02Task.fromJson(Map<String, dynamic>.from(row));
        })
        .toList(growable: false);
    return Ai02Snapshot(
      tasks: tasks,
      nextOffset: response['has_more'] == true
          ? response['next_offset'] as int
          : null,
    );
  }
}
