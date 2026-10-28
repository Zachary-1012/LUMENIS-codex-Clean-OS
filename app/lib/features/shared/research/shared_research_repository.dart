import 'dart:async';
import 'dart:math';

import 'package:flutter/foundation.dart';

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

enum _ResearchPendingKind { start, save, revise }

/// Owner-level task and saved-work state for Shared Research.
///
/// This keeps task identity, idempotency keys, readback, recovery, and version
/// lineage outside any particular presentation. A surface can bind to this
/// controller without becoming another research owner.
final class SharedResearchController extends ChangeNotifier {
  SharedResearchController({
    required this.repository,
    Map<String, String> sources = const {},
  }) : sources = Map.unmodifiable(sources) {
    _selectedSourceIds.addAll(sources.keys.take(100));
  }

  final SharedResearchRepository repository;
  final Map<String, String> sources;
  final Set<String> _selectedSourceIds = {};
  final List<SharedResearchDocument> historyItems = [];
  final List<SharedResearchTask> taskItems = [];
  String question = '';
  String title = '';
  String markdown = '';

  SharedResearchDocument? opened;
  SharedResearchTask? task;
  String? historyCursor;
  String? taskCursor;
  String? notice;
  bool loading = false;
  bool busy = false;
  bool historyIncomplete = false;
  bool editing = false;
  int _generation = 0;
  int _loadGeneration = 0;
  bool _disposed = false;
  Timer? _poll;
  _PendingResearchOperation? _pending;

  bool get hasPendingOperation => _pending != null;
  Set<String> get selectedSourceIds => Set.unmodifiable(_selectedSourceIds);
  bool get hasUnsavedEdits =>
      opened != null &&
      (title != opened!.title || markdown != opened!.markdown);

  Future<void> loadInitial({String? artifactId}) async {
    await load();
    if (!_disposed && artifactId != null) await openDocument(artifactId);
  }

  Future<void> load({bool moreHistory = false, bool moreTasks = false}) async {
    if (_disposed || busy || loading) return;
    final generation = ++_loadGeneration;
    loading = true;
    notice = null;
    _notify();
    try {
      final history = moreTasks
          ? null
          : await repository.history(
              cursor: moreHistory ? historyCursor : null,
            );
      final tasks = moreHistory
          ? null
          : await repository.tasks(cursor: moreTasks ? taskCursor : null);
      if (_isLoadStale(generation)) return;
      if (history != null) {
        if (moreHistory) {
          historyItems.addAll(history.items);
        } else {
          historyItems
            ..clear()
            ..addAll(history.items);
        }
        historyCursor = history.cursor;
        historyIncomplete = moreHistory
            ? historyIncomplete || history.incomplete
            : history.incomplete;
      }
      if (tasks != null) {
        if (moreTasks) {
          final known = taskItems.map((item) => item.id).toSet();
          taskItems.addAll(tasks.items.where((item) => !known.contains(item.id)));
        } else {
          taskItems
            ..clear()
            ..addAll(tasks.items);
        }
        taskCursor = tasks.cursor;
      }
    } catch (error) {
      if (!_isLoadStale(generation)) _handleError(error);
    } finally {
      if (!_isLoadStale(generation)) {
        loading = false;
        _notify();
      }
    }
  }

  void selectSource(String sourceId, bool selected) {
    if (_disposed || busy || !sources.containsKey(sourceId)) return;
    if (selected) {
      if (_selectedSourceIds.length < 100) _selectedSourceIds.add(sourceId);
    } else {
      _selectedSourceIds.remove(sourceId);
    }
    _notify();
  }

  void updateQuestion(String value) {
    if (_disposed || busy || _pending != null || value == question) return;
    question = value;
    _notify();
  }

  void editTitle(String value) {
    if (_disposed || _pending != null || value == title) return;
    title = value;
    _notify();
  }

  void editMarkdown(String value) {
    if (_disposed || _pending != null || value == markdown) return;
    markdown = value;
    _notify();
  }

  void setEditing(bool value) {
    if (_disposed || busy || _pending != null || opened == null) return;
    editing = value;
    _notify();
  }

  Future<bool> start() async {
    final prompt = question.trim();
    if (_disposed ||
        busy ||
        _pending != null ||
        prompt.length < 4 ||
        _selectedSourceIds.isEmpty ||
        hasUnsavedEdits) {
      return false;
    }
    _poll?.cancel();
    _generation++;
    _pending = _PendingResearchOperation.start(
      question: prompt,
      sources: List.unmodifiable(_selectedSourceIds),
      requestId: _requestId(),
    );
    await checkPendingOperation();
    return _pending == null;
  }

  Future<bool> openDocument(
    String artifactId, {
    bool discardLocalEdits = false,
  }) async {
    if (_disposed || busy || _pending != null || artifactId.isEmpty) {
      return false;
    }
    if (hasUnsavedEdits && !discardLocalEdits) return false;
    final generation = ++_generation;
    _poll?.cancel();
    busy = true;
    opened = null;
    task = null;
    title = '';
    markdown = '';
    editing = false;
    notice = null;
    _notify();
    try {
      final current = await repository.open(artifactId);
      if (_isStale(generation) || current.id != artifactId) {
        throw const FormatException('Wrong research version.');
      }
      _showDocument(current);
      return true;
    } catch (error) {
      if (!_isStale(generation)) _handleError(error);
      return false;
    } finally {
      if (!_isStale(generation)) {
        busy = false;
        _notify();
      }
    }
  }

  Future<bool> readTask(
    String taskId, {
    bool resume = false,
    bool select = false,
    bool discardLocalEdits = false,
  }) async {
    if (_disposed || busy || _pending != null || taskId.isEmpty) return false;
    if (select && hasUnsavedEdits && !discardLocalEdits) return false;
    final generation = ++_generation;
    busy = true;
    notice = null;
    if (select) _poll?.cancel();
    _notify();
    try {
      final current = await repository.task(taskId, resume: resume);
      if (_isStale(generation) || current.id != taskId) {
        throw const FormatException('Wrong research task.');
      }
      _showTask(current);
      return true;
    } catch (error) {
      if (!_isStale(generation)) _handleError(error);
      return false;
    } finally {
      if (!_isStale(generation)) {
        busy = false;
        _notify();
      }
    }
  }

  Future<bool> saveResult() async {
    final currentTask = task;
    if (_disposed ||
        busy ||
        _pending != null ||
        currentTask == null ||
        currentTask.state != 'succeeded' ||
        currentTask.markdown == null) {
      return false;
    }
    _pending = _PendingResearchOperation.save(
      task: currentTask,
      requestId: _requestId(),
    );
    await checkPendingOperation();
    return _pending == null;
  }

  Future<bool> reviseSaved() async {
    final parent = opened;
    final nextTitle = title.trim();
    final nextMarkdown = markdown;
    if (_disposed ||
        busy ||
        _pending != null ||
        parent == null ||
        !hasUnsavedEdits ||
        nextTitle.isEmpty ||
        nextMarkdown.trim().isEmpty) {
      return false;
    }
    _pending = _PendingResearchOperation.revise(
      parent: parent,
      title: nextTitle,
      markdown: nextMarkdown,
      requestId: _requestId(),
    );
    await checkPendingOperation();
    return _pending == null;
  }

  /// Replays the exact pending request with the same idempotency key after an
  /// uncertain response. It never invents a new task or version identity.
  Future<void> checkPendingOperation() async {
    final operation = _pending;
    if (_disposed || busy || operation == null) return;
    busy = true;
    notice = null;
    _notify();
    try {
      switch (operation.kind) {
        case _ResearchPendingKind.start:
          final result = await repository.start(
            operation.question!,
            operation.sources!,
            operation.requestId,
          );
          _showTask(result);
        case _ResearchPendingKind.save:
          final result = await repository.save(
            operation.task!,
            operation.requestId,
          );
          _showDocument(result);
        case _ResearchPendingKind.revise:
          final result = await repository.revise(
            operation.parent!,
            operation.title!,
            operation.markdown!,
            operation.requestId,
          );
          _showDocument(result);
      }
      if (!_disposed) _pending = null;
    } catch (error) {
      if (!_disposed) _handleError(error);
    } finally {
      if (!_disposed) {
        busy = false;
        _notify();
      }
    }
    if (!_disposed && _pending == null) await load();
  }

  void _showDocument(SharedResearchDocument item) {
    opened = item;
    editing = false;
    task = null;
    title = item.title;
    markdown = item.markdown;
    notice = null;
    _poll?.cancel();
    _notify();
  }

  void _showTask(SharedResearchTask value) {
    task = value;
    editing = false;
    final index = taskItems.indexWhere((item) => item.id == value.id);
    if (index < 0) {
      taskItems.insert(0, value);
    } else {
      taskItems[index] = value;
    }
    opened = null;
    title = value.question;
    markdown = value.markdown ?? '';
    notice = null;
    _poll?.cancel();
    if (value.state == 'pending' || value.state == 'running') {
      _poll = Timer(const Duration(seconds: 2), () {
        unawaited(readTask(value.id));
      });
    }
    _notify();
  }

  void _handleError(Object error) {
    _poll?.cancel();
    final restricted =
        error is LumenisCoreException &&
        const {401, 403, 404, 409, 410}.contains(error.statusCode);
    if (restricted) {
      _generation++;
      opened = null;
      task = null;
      title = '';
      markdown = '';
      _pending = null;
      historyItems.clear();
      taskItems.clear();
      notice = 'source_or_version_changed';
    } else {
      notice = 'result_unconfirmed';
    }
    _notify();
  }

  String _requestId() =>
      'research_${DateTime.now().microsecondsSinceEpoch}_${Random.secure().nextInt(1 << 30)}';

  bool _isStale(int generation) => _disposed || generation != _generation;

  bool _isLoadStale(int generation) =>
      _disposed || generation != _loadGeneration;

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _generation++;
    _poll?.cancel();
    super.dispose();
  }
}

final class _PendingResearchOperation {
  const _PendingResearchOperation._({
    required this.kind,
    required this.requestId,
    this.question,
    this.sources,
    this.task,
    this.parent,
    this.title,
    this.markdown,
  });

  factory _PendingResearchOperation.start({
    required String question,
    required List<String> sources,
    required String requestId,
  }) => _PendingResearchOperation._(
    kind: _ResearchPendingKind.start,
    question: question,
    sources: sources,
    requestId: requestId,
  );

  factory _PendingResearchOperation.save({
    required SharedResearchTask task,
    required String requestId,
  }) => _PendingResearchOperation._(
    kind: _ResearchPendingKind.save,
    task: task,
    requestId: requestId,
  );

  factory _PendingResearchOperation.revise({
    required SharedResearchDocument parent,
    required String title,
    required String markdown,
    required String requestId,
  }) => _PendingResearchOperation._(
    kind: _ResearchPendingKind.revise,
    parent: parent,
    title: title,
    markdown: markdown,
    requestId: requestId,
  );

  final _ResearchPendingKind kind;
  final String requestId;
  final String? question;
  final List<String>? sources;
  final SharedResearchTask? task;
  final SharedResearchDocument? parent;
  final String? title;
  final String? markdown;
}
