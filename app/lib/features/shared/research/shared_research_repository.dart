import '../../../core/lumenis_core_client.dart';

Map<String, dynamic> researchMap(Object? value) {
  if (value is! Map) {
    throw const FormatException('Research response is unavailable.');
  }
  return value.map((key, value) => MapEntry('$key', value));
}

bool _shared(Object? value) {
  if (value is! Map) return false;
  return value['scope_kind'] == 'shared_workspace' && value['version'] == 1;
}

class SharedResearchDocument {
  SharedResearchDocument.fromResponse(
    Map<String, dynamic> value, {
    bool reopened = false,
  }) {
    final artifact = researchMap(value['artifact']);
    final document = researchMap(value['document']);
    final reference = researchMap(
      researchMap(document['payload'])['source_brief_reference'],
    );
    final scope = researchMap(value['return_ref'])['scope'];
    id = artifact['artifact_id'] as String;
    sha256 = artifact['sha256'] as String;
    workId = document['work_id'] as String;
    title = document['title'] as String;
    markdown = document['markdown'] as String;
    version = document['version'] as int;
    createdAt = document['created_at'] as String;
    jobId = reference['job_id'] as String;
    parentId = document['parent_artifact_id'] as String?;
    parentSha256 = document['parent_sha256'] as String?;
    if (!RegExp(r'^ART-[0-9a-f]{16}$').hasMatch(id) ||
        !RegExp(r'^[0-9a-f]{64}$').hasMatch(sha256) ||
        !RegExp(r'^brief-[0-9a-f]{32}$').hasMatch(jobId) ||
        workId.isEmpty ||
        version < 1 ||
        title.isEmpty ||
        document['kind'] != 'research' ||
        !_shared(scope) ||
        !_shared(reference['scope'])) {
      throw const FormatException('Research version does not match.');
    }
    if (reopened) {
      final receipt = researchMap(value['receipt']);
      final observations = researchMap(receipt['constraint_observations']);
      if (receipt['ref'] != id ||
          receipt['sha256'] != sha256 ||
          receipt['version'] != version ||
          receipt['work_id'] != workId ||
          !_shared(receipt['scope']) ||
          observations['committed_bytes_match'] != true ||
          observations['parent_chain_verified'] != true ||
          observations['source_authorization'] != 'fresh-per-source') {
        throw const FormatException('Research readback was not verified.');
      }
    }
  }
  late final String id, sha256, workId, title, markdown, createdAt, jobId;
  late final String? parentId, parentSha256;
  late final int version;
}

class SharedResearchTask {
  SharedResearchTask.fromResponse(Map<String, dynamic> value) {
    id = value['task_id'] as String;
    jobId = value['job_id'] as String;
    state = value['state'] as String;
    question = value['business_question'] as String? ?? '';
    canResume = value['can_resume'] == true;
    if (!RegExp(r'^rbrief_[0-9a-f-]{36}$').hasMatch(id) ||
        !RegExp(r'^brief-[0-9a-f]{32}$').hasMatch(jobId) ||
        !const {
          'pending',
          'running',
          'succeeded',
          'failed',
          'interrupted',
          'cancelled',
          'paused',
        }.contains(state)) {
      throw const FormatException('Research task is unavailable.');
    }
    if (state == 'succeeded') {
      final report = researchMap(value['result']);
      final outcome = researchMap(report['artifact_outcome']);
      final brief = researchMap(report['source_brief']);
      if (report['job_id'] != jobId ||
          outcome['report_id'] != jobId ||
          outcome['state'] != 'persisted_and_reopened_verified' ||
          !_shared(brief['scope'])) {
        throw const FormatException('Research result was not verified.');
      }
      markdown = brief['markdown'] as String;
    }
  }
  late final String id, jobId, state, question;
  late final bool canResume;
  String? markdown;
}

class ResearchPage<T> {
  const ResearchPage(this.items, this.cursor, this.incomplete);
  final List<T> items;
  final String? cursor;
  final bool incomplete;
}

abstract interface class SharedResearchRepository {
  Future<ResearchPage<SharedResearchDocument>> history({String? cursor});
  Future<ResearchPage<SharedResearchTask>> tasks({String? cursor});
  Future<SharedResearchTask> start(
    String question,
    List<String> sources,
    String requestId,
  );
  Future<SharedResearchTask> task(String id, {bool resume = false});
  Future<SharedResearchDocument> open(String id);
  Future<SharedResearchDocument> save(
    SharedResearchTask task,
    String requestId,
  );
  Future<SharedResearchDocument> revise(
    SharedResearchDocument parent,
    String title,
    String markdown,
    String requestId,
  );
}

class CoreSharedResearchRepository implements SharedResearchRepository {
  const CoreSharedResearchRepository(this.client);
  final LumenisCoreClient client;
  Map<String, dynamic> _result(
    Map<String, dynamic> response, [
    String key = 'result',
  ]) {
    if (response['ok'] != true) {
      throw const FormatException('Research request failed.');
    }
    return researchMap(response[key]);
  }

  String? _cursor(Map<String, dynamic> result) {
    if (result['has_more'] is! bool) {
      throw const FormatException('Incomplete page.');
    }
    if (result['has_more'] == false) return null;
    final cursor = result['next_cursor'];
    if (cursor is! String || cursor.isEmpty) {
      throw const FormatException('Missing next page.');
    }
    return cursor;
  }

  @override
  Future<ResearchPage<SharedResearchDocument>> history({String? cursor}) async {
    final result = _result(
      await client.listSharedSavedWork(kind: 'research', cursor: cursor),
    );
    final items = <SharedResearchDocument>[];
    var incomplete = result['verification_complete'] != true;
    for (final raw in result['items'] as List) {
      final item = researchMap(raw);
      final payload = researchMap(researchMap(item['document'])['payload']);
      if (!payload.containsKey('source_brief_reference')) continue;
      try {
        items.add(SharedResearchDocument.fromResponse(item));
      } catch (_) {
        incomplete = true;
      }
    }
    return ResearchPage(items, _cursor(result), incomplete);
  }

  @override
  Future<ResearchPage<SharedResearchTask>> tasks({String? cursor}) async {
    final result = _result(await client.sharedResearchTasks(cursor: cursor));
    return ResearchPage(
      [
        for (final item in result['items'] as List)
          SharedResearchTask.fromResponse(researchMap(item)),
      ],
      _cursor(result),
      false,
    );
  }

  @override
  Future<SharedResearchTask> start(
    String question,
    List<String> sources,
    String requestId,
  ) async => SharedResearchTask.fromResponse(
    _result(
      await client.startSharedResearch(
        question: question,
        sourceIds: sources,
        requestId: requestId,
      ),
      'task',
    ),
  );
  @override
  Future<SharedResearchTask> task(String id, {bool resume = false}) async {
    final task = SharedResearchTask.fromResponse(
      _result(await client.sharedResearchTask(id, resume: resume), 'task'),
    );
    if (task.id != id) throw const FormatException('Research task changed.');
    return task;
  }

  @override
  Future<SharedResearchDocument> open(String id) async {
    final item = SharedResearchDocument.fromResponse(
      _result(await client.reopenSharedSavedWork(id)),
      reopened: true,
    );
    if (item.id != id) throw const FormatException('Research version changed.');
    return item;
  }

  Future<SharedResearchDocument> _readSaved(
    Map<String, dynamic> response,
  ) async {
    final saved = SharedResearchDocument.fromResponse(_result(response));
    final reopened = await open(saved.id);
    if (saved.sha256 != reopened.sha256 ||
        saved.workId != reopened.workId ||
        saved.version != reopened.version ||
        saved.markdown != reopened.markdown ||
        saved.title != reopened.title) {
      throw const FormatException('Saved research readback changed.');
    }
    return reopened;
  }

  @override
  Future<SharedResearchDocument> save(
    SharedResearchTask task,
    String requestId,
  ) async {
    if (task.state != 'succeeded' || task.markdown == null) {
      throw const FormatException('Research is not ready.');
    }
    final item = await _readSaved(
      await client.saveSharedResearch(
        jobId: task.jobId,
        requestId: requestId,
        title: task.question.length <= 300
            ? task.question
            : task.question.substring(0, 300),
      ),
    );
    if (item.jobId != task.jobId) {
      throw const FormatException('Saved research source changed.');
    }
    return item;
  }

  @override
  Future<SharedResearchDocument> revise(
    SharedResearchDocument parent,
    String title,
    String markdown,
    String requestId,
  ) async {
    final item = await _readSaved(
      await client.reviseSharedReport(
        artifactId: parent.id,
        requestId: requestId,
        expectedSha256: parent.sha256,
        reason: 'User revision',
        expectedTitle: parent.title,
        title: title,
        expectedMarkdown: parent.markdown,
        markdown: markdown,
      ),
    );
    if (item.workId != parent.workId ||
        item.version != parent.version + 1 ||
        item.parentId != parent.id ||
        item.parentSha256 != parent.sha256 ||
        item.title != title ||
        item.markdown != markdown) {
      throw const FormatException('Research revision lineage changed.');
    }
    return item;
  }
}
