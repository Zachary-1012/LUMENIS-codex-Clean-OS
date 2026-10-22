import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';

const _docxMediaType =
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document';

enum ManuscriptControllerPhase {
  idle,
  preparing,
  running,
  reading,
  cancelling,
  listing,
  reopening,
  exporting,
}

/// A manuscript version that passed the authored-manuscript/v4 checks.
///
/// [artifactId], [version], and [draftDigest] are the real SavedWork parent
/// values used when a later edit is saved as a revision.
final class InternalPitchSavedManuscript {
  const InternalPitchSavedManuscript({
    required this.artifactId,
    required this.artifactSha256,
    required this.artifactSizeBytes,
    required this.workId,
    required this.version,
    required this.previousArtifactId,
    required this.parentSha256,
    required this.draftDigest,
    required this.taskId,
    required this.outputArtifactId,
    required this.outputSha256,
    required this.outputSizeBytes,
    required this.manuscript,
  });

  final String artifactId;
  final String artifactSha256;
  final int artifactSizeBytes;
  final String workId;
  final int version;
  final String? previousArtifactId;
  final String? parentSha256;
  final String draftDigest;
  final String taskId;
  final String outputArtifactId;
  final String outputSha256;
  final int outputSizeBytes;
  final InternalPitchManuscript manuscript;

  /// The version to which the next revision must be bound.
  int get parentVersion => version;
}

/// SH01's in-memory binding to the existing internal-pitch and SavedWork APIs.
/// Draft text remains local until [save] is explicitly invoked.
final class ManuscriptController extends ChangeNotifier {
  factory ManuscriptController({
    required LumenisCoreClient client,
    required InternalPitchManuscript draft,
    LumenisWorkspaceScope? scope,
  }) => ManuscriptController._(client, draft, scope);

  ManuscriptController._(this._client, this._draft, this._scope);

  static final Random _random = Random.secure();

  final LumenisCoreClient _client;
  final Map<String, _ManuscriptAttempt> _attempts =
      <String, _ManuscriptAttempt>{};

  LumenisWorkspaceScope? _scope;
  InternalPitchManuscript _draft;
  InternalPitchSavedManuscript? _savedWork;
  InternalPitchSavedManuscript? _revisionParent;
  _ManuscriptAttempt? _activeAttempt;
  String? _taskId;
  String? _taskState;
  String? _taskError;
  String? _errorCode;
  int _operationCount = 0;
  int _scopeGeneration = 0;
  bool _disposed = false;
  bool _hasMore = false;
  String? _cursor;
  List<InternalPitchSavedManuscript> _items = const [];
  Map<String, dynamic> _pageMetadata = const {};
  final Set<String> _usedCursors = <String>{};
  ManuscriptControllerPhase _phase = ManuscriptControllerPhase.idle;

  LumenisWorkspaceScope? get scope => _scope;
  InternalPitchManuscript get draft => _draft;
  bool get busy => _operationCount > 0;
  ManuscriptControllerPhase get phase => _phase;
  String? get taskId => _taskId;
  String? get taskState => _taskState;
  String? get taskError => _taskError;
  String? get errorCode => _errorCode;
  InternalPitchSavedManuscript? get savedWork => _savedWork;
  List<InternalPitchSavedManuscript> get items =>
      List<InternalPitchSavedManuscript>.unmodifiable(_items);
  bool get hasMore => _hasMore;
  String? get cursor => _cursor;
  String? get nextCursor => _cursor;
  Map<String, dynamic> get pageMetadata =>
      Map<String, dynamic>.unmodifiable(_pageMetadata);

  bool get prepareAcknowledgementLost {
    final attempt = _activeAttempt;
    return attempt != null &&
        attempt.taskId == null &&
        attempt.prepareOutcomeUnknown;
  }

  bool get runRetryAvailable {
    final attempt = _activeAttempt;
    if (attempt == null || attempt.taskId == null) return false;
    return attempt.taskState == 'prepared' &&
        (attempt.runOutcomeUnknown || attempt.runAttempted);
  }

  /// Whether the current scoped save still needs authoritative resolution.
  ///
  /// A successful task remains unresolved until its v4 SavedWork commit has
  /// passed validation. This keeps callers from discarding the recovery path
  /// after a partial or malformed success response.
  bool get hasUnresolvedSave {
    final attempt = _activeAttempt;
    return attempt != null && _attemptNeedsResolution(attempt);
  }

  bool get canSave {
    if (_scope == null || busy || prepareAcknowledgementLost) return false;
    if (runRetryAvailable) return false;
    try {
      final manuscriptJson = _draft.toJson();
      final saved = _savedWork;
      if (saved != null && _revisionParent?.artifactId == saved.artifactId) {
        if (_sameJson(manuscriptJson, saved.manuscript.toJson())) return false;
      }
      final key = _snapshotKey(_scope!, _draft, _revisionParent);
      if (_attempts.values.any(
        (candidate) =>
            candidate.key != key &&
            _sameScope(candidate.scope, _scope) &&
            _attemptNeedsResolution(candidate),
      )) {
        return false;
      }
      final attempt = _attempts[key];
      if (attempt?.taskId != null) {
        if (attempt?.taskState == 'succeeded' && attempt?.savedWork == null) {
          return false;
        }
        if (attempt?.taskState != 'succeeded' && attempt!.runAttempted) {
          return false;
        }
      }
      return true;
    } on FormatException {
      return false;
    }
  }

  /// Updates the actual caller supplied scope. Old-scope replies are ignored.
  void updateScope(LumenisWorkspaceScope? scope) {
    if (_disposed || _sameScope(_scope, scope)) return;
    _scopeGeneration++;
    _scope = scope;
    _savedWork = null;
    _revisionParent = null;
    _activeAttempt = null;
    _taskId = null;
    _taskState = null;
    _taskError = null;
    _errorCode = null;
    _hasMore = false;
    _cursor = null;
    _items = const [];
    _pageMetadata = const {};
    _usedCursors.clear();
    _phase = ManuscriptControllerPhase.idle;
    _notify();
  }

  /// Updates local writing without changing the saved parent or retry snapshot.
  void updateDraft(InternalPitchManuscript draft) {
    if (_disposed) return;
    _draft = draft;
    _notify();
  }

  /// Starts an unlinked local document and clears the current save identity.
  /// Returns false while an operation or unresolved save is in flight.
  bool startNewDraft(InternalPitchManuscript draft) {
    if (_disposed || busy || hasUnresolvedSave) return false;
    _draft = draft;
    _savedWork = null;
    _revisionParent = null;
    _activeAttempt = null;
    _attempts.clear();
    _taskId = null;
    _taskState = null;
    _taskError = null;
    _errorCode = null;
    _phase = ManuscriptControllerPhase.idle;
    _notify();
    return true;
  }

  /// Prepares, runs once, then reads the authoritative task and SavedWork row.
  Future<void> save() async {
    final scope = _scope;
    if (scope == null) {
      _errorCode = 'CONTENT_CONTEXT_UNAVAILABLE';
      _notify();
      return;
    }
    if (busy || !canSave) return;

    late final _ManuscriptAttempt attempt;
    try {
      _draft.toJson();
      final key = _snapshotKey(scope, _draft, _revisionParent);
      attempt = _attempts.putIfAbsent(
        key,
        () => _ManuscriptAttempt(
          key: key,
          scope: scope,
          manuscript: _draft,
          parent: _revisionParent,
          requestId: _newRequestId(),
        ),
      );
    } on FormatException {
      _errorCode = 'INTERNAL_PITCH_INPUT_INVALID';
      _notify();
      return;
    }

    _activeAttempt = attempt;
    _taskId = attempt.taskId;
    _taskState = attempt.taskState;
    _taskError = attempt.taskError;
    if (!_begin(ManuscriptControllerPhase.preparing)) return;
    final generation = _scopeGeneration;
    try {
      if (attempt.taskId == null) {
        final prepared = await _prepare(attempt, generation);
        if (prepared && _isCurrent(generation, scope)) {
          await _continueAfterPrepare(attempt, generation);
        }
      } else if (attempt.runAttempted) {
        // A second Save after a possibly lost run response is read-only.
        await _readAttempt(attempt, generation);
      } else if (_isCurrent(generation, scope)) {
        await _continueAfterPrepare(attempt, generation);
      }
    } finally {
      _end(generation);
    }
  }

  /// Retries an unacknowledged prepare with the exact same request ID and body.
  /// Acknowledging that original save continues through one run and a read.
  Future<void> retryPrepare() async {
    final scope = _scope;
    final attempt = _activeAttempt;
    if (scope == null || attempt == null || attempt.taskId != null || busy) {
      return;
    }
    if (!_sameScope(scope, attempt.scope) || !attempt.prepareOutcomeUnknown) {
      return;
    }
    if (!_begin(ManuscriptControllerPhase.preparing)) return;
    final generation = _scopeGeneration;
    try {
      final prepared = await _prepare(attempt, generation);
      if (prepared && _isCurrent(generation, scope)) {
        await _continueAfterPrepare(attempt, generation);
      }
    } finally {
      _end(generation);
    }
  }

  /// Reads the current task. It never repeats prepare, run, or cancel.
  Future<void> read() async {
    final scope = _scope;
    if (scope == null || busy) return;
    final attempt = _activeAttempt;
    final taskId = attempt?.taskId ?? _taskId ?? _savedWork?.taskId;
    if (taskId == null) {
      _errorCode = 'INTERNAL_PITCH_TASK_ID_UNAVAILABLE';
      _notify();
      return;
    }
    if (!_begin(ManuscriptControllerPhase.reading)) return;
    final generation = _scopeGeneration;
    try {
      await _readTask(
        scope: scope,
        taskId: taskId,
        attempt: attempt,
        expectedSaved: attempt == null ? _savedWork : null,
        generation: generation,
      );
    } finally {
      _end(generation);
    }
  }

  /// Explicitly retries one run after readback left it pending or uncertain.
  Future<void> retryRun() async {
    final scope = _scope;
    final attempt = _activeAttempt;
    if (scope == null || attempt == null || attempt.taskId == null || busy) {
      return;
    }
    if (!_sameScope(scope, attempt.scope) || !runRetryAvailable) return;
    if (!_begin(ManuscriptControllerPhase.running)) return;
    final generation = _scopeGeneration;
    try {
      await _runAndRead(attempt, generation);
    } finally {
      _end(generation);
    }
  }

  /// Requests cancellation once and then reads the task's authoritative state.
  Future<void> cancel() async {
    final scope = _scope;
    final attempt = _activeAttempt;
    final taskId = attempt?.taskId ?? _taskId;
    if (scope == null || taskId == null || busy) return;
    if (attempt != null && !_sameScope(scope, attempt.scope)) return;
    if (!_begin(ManuscriptControllerPhase.cancelling)) return;
    final generation = _scopeGeneration;
    Object? cancelFailure;
    try {
      try {
        final result = await _client.cancelInternalPitch(
          taskId: taskId,
          scope: scope,
        );
        _validateTaskReply(result, expectedTaskId: taskId, scope: scope);
        if (_isCurrent(generation, scope)) {
          final cancellation = result['cancellation'];
          if (cancellation is String) _taskError = null;
        }
      } catch (error) {
        cancelFailure = error;
      }
      if (_isCurrent(generation, scope)) {
        await _readTask(
          scope: scope,
          taskId: taskId,
          attempt: attempt,
          expectedSaved: attempt == null ? _savedWork : null,
          generation: generation,
        );
        if (cancelFailure != null && _isCurrent(generation, scope)) {
          _errorCode = _errorCodeFor(cancelFailure);
        }
      }
    } finally {
      _end(generation);
    }
  }

  /// Loads one report/v4 SavedWork page, preserving its opaque cursor metadata.
  Future<void> list({int limit = 100}) async {
    final scope = _scope;
    if (scope == null || busy) {
      if (scope == null && !_disposed) {
        _errorCode = 'CONTENT_CONTEXT_UNAVAILABLE';
        _notify();
      }
      return;
    }
    _items = const [];
    _cursor = null;
    _hasMore = false;
    _pageMetadata = const {};
    _usedCursors.clear();
    _errorCode = null;
    await _loadPage(scope: scope, cursor: null, limit: limit, append: false);
  }

  /// Reads the next opaque SavedWork cursor, including when this page filtered
  /// to zero v4 manuscripts but the server reports that more pages remain.
  Future<void> loadMore() async {
    final scope = _scope;
    final cursor = _cursor;
    if (scope == null || busy || !_hasMore || cursor == null) return;
    if (_usedCursors.contains(cursor)) {
      _errorCode = 'SAVED_WORK_CURSOR_REPEATED';
      _notify();
      return;
    }
    await _loadPage(scope: scope, cursor: cursor, limit: 100, append: true);
  }

  /// Reopens one SavedWork item and binds it only if its v4 context matches.
  Future<void> reopen(String artifactId) async {
    final scope = _scope;
    if (scope == null || busy) return;
    if (!_isArtifactIdValue(artifactId)) {
      _errorCode = 'SAVED_WORK_ARTIFACT_INVALID';
      _notify();
      return;
    }
    if (!_begin(ManuscriptControllerPhase.reopening)) return;
    final generation = _scopeGeneration;
    try {
      final response = scope is SharedWorkspaceScope
          ? await _client.reopenSharedSavedManuscript(
              scope: scope,
              artifactId: artifactId,
            )
          : await _client.reopenSavedManuscript(
              domainId: (scope as InternalPitchScope).domainId,
              artifactId: artifactId,
            );
      if (!_isCurrent(generation, scope)) return;
      final saved = _parseSavedManuscript(
        response,
        expectedScope: scope,
        requireReceipt: true,
      );
      if (saved.artifactId != artifactId) {
        throw const FormatException('SavedWork artifact identity mismatch.');
      }
      _savedWork = saved;
      _revisionParent = saved;
      _taskId = saved.taskId;
      _taskState = 'succeeded';
      _taskError = null;
      _errorCode = null;
      _activeAttempt = null;
    } catch (error) {
      if (_isCurrent(generation, scope)) _errorCode = _errorCodeFor(error);
    } finally {
      _end(generation);
    }
  }

  /// Returns only bytes validated by LumenisCoreClient's DOCX response guard.
  Future<InternalPitchFile?> export() async {
    final scope = _scope;
    final saved = _savedWork;
    if (scope == null || saved == null || busy) return null;
    if (!_begin(ManuscriptControllerPhase.exporting)) return null;
    final generation = _scopeGeneration;
    try {
      final file = await _client.exportInternalPitch(
        taskId: saved.taskId,
        scope: scope,
      );
      if (!_isCurrent(generation, scope)) return null;
      _errorCode = null;
      return file;
    } catch (error) {
      if (_isCurrent(generation, scope)) _errorCode = _errorCodeFor(error);
      return null;
    } finally {
      _end(generation);
    }
  }

  Future<bool> _prepare(_ManuscriptAttempt attempt, int generation) async {
    try {
      final response = await _client.prepareInternalPitch(
        scope: attempt.scope,
        manuscript: attempt.manuscript,
        requestId: attempt.requestId,
        revision: attempt.revision,
      );
      final reply = _validateTaskReply(response, scope: attempt.scope);
      attempt
        ..taskId = reply.taskId
        ..taskState = reply.state
        ..taskError = reply.errorCode
        ..prepareOutcomeUnknown = false;
      if (_isCurrent(generation, attempt.scope)) {
        _taskId = reply.taskId;
        _taskState = reply.state;
        _taskError = reply.errorCode;
        _errorCode = reply.errorCode;
      }
      return true;
    } catch (error) {
      attempt.prepareOutcomeUnknown = _writeOutcomeUnknown(error);
      if (_isCurrent(generation, attempt.scope)) {
        _errorCode = _errorCodeFor(error);
      }
      return false;
    }
  }

  Future<void> _continueAfterPrepare(
    _ManuscriptAttempt attempt,
    int generation,
  ) async {
    if (!_isCurrent(generation, attempt.scope)) return;
    if (attempt.taskState == 'prepared' && !attempt.runAttempted) {
      await _runAndRead(attempt, generation);
      return;
    }
    // A duplicate prepare acknowledgement may report a later or unknown raw
    // state. Read it before considering any further write.
    await _readAttempt(attempt, generation);
  }

  Future<void> _runAndRead(_ManuscriptAttempt attempt, int generation) async {
    final taskId = attempt.taskId;
    if (taskId == null || !_isCurrent(generation, attempt.scope)) return;
    attempt.runAttempted = true;
    Object? runFailure;
    try {
      final response = await _client.runInternalPitch(
        taskId: taskId,
        scope: attempt.scope,
      );
      final reply = _validateTaskReply(
        response,
        expectedTaskId: taskId,
        scope: attempt.scope,
      );
      attempt
        ..taskState = reply.state
        ..taskError = reply.errorCode
        ..runOutcomeUnknown = false;
      if (_isCurrent(generation, attempt.scope)) {
        _taskState = reply.state;
        _taskError = reply.errorCode;
      }
    } catch (error) {
      runFailure = error;
      attempt.runOutcomeUnknown = _writeOutcomeUnknown(error);
      if (_isCurrent(generation, attempt.scope)) {
        _errorCode = _errorCodeFor(error);
      }
    }

    // A read is safe after either response. A second run is never automatic.
    if (_isCurrent(generation, attempt.scope)) {
      await _readAttempt(attempt, generation);
      if (runFailure != null &&
          attempt.taskState == 'succeeded' &&
          _isCurrent(generation, attempt.scope)) {
        _errorCode = null;
      }
    }
  }

  Future<void> _readAttempt(_ManuscriptAttempt attempt, int generation) async {
    final taskId = attempt.taskId;
    if (taskId == null) return;
    await _readTask(
      scope: attempt.scope,
      taskId: taskId,
      attempt: attempt,
      generation: generation,
    );
  }

  Future<void> _readTask({
    required LumenisWorkspaceScope scope,
    required String taskId,
    required _ManuscriptAttempt? attempt,
    required int generation,
    InternalPitchSavedManuscript? expectedSaved,
  }) async {
    try {
      final response = await _client.readInternalPitch(
        taskId: taskId,
        scope: scope,
      );
      final reply = _validateTaskReply(
        response,
        expectedTaskId: taskId,
        scope: scope,
      );
      if (attempt != null) {
        attempt
          ..taskState = reply.state
          ..taskError = reply.errorCode;
      }
      if (_isCurrent(generation, scope)) {
        _taskId = taskId;
        _taskState = reply.state;
        _taskError = reply.errorCode;
        _errorCode = reply.errorCode;
      }
      InternalPitchSavedManuscript? committed;
      if (reply.state == 'succeeded') {
        committed = _parseTaskCommit(
          response,
          scope: scope,
          taskId: taskId,
          expectedManuscript: attempt?.manuscript,
          expectedParent: attempt?.parent,
          expectedRequestId: attempt?.requestId,
          expectedSaved: expectedSaved,
        );
      }
      if (attempt != null) {
        attempt.runOutcomeUnknown =
            reply.state != 'succeeded' && attempt.runOutcomeUnknown;
        if (committed != null) {
          attempt
            ..savedWork = committed
            ..runOutcomeUnknown = false;
        }
      }
      if (!_isCurrent(generation, scope)) return;
      if (committed != null) {
        _savedWork = committed;
        _revisionParent = committed;
        _taskError = null;
        _errorCode = null;
      } else {
        _errorCode = reply.errorCode;
      }
    } catch (error) {
      if (attempt != null &&
          _writeOutcomeUnknown(error) &&
          attempt.runAttempted &&
          attempt.taskState != 'succeeded') {
        attempt.runOutcomeUnknown = true;
      }
      if (_isCurrent(generation, scope)) _errorCode = _errorCodeFor(error);
    }
  }

  Future<void> _loadPage({
    required LumenisWorkspaceScope scope,
    required String? cursor,
    required int limit,
    required bool append,
  }) async {
    if (!_begin(ManuscriptControllerPhase.listing)) return;
    final generation = _scopeGeneration;
    if (cursor != null) _usedCursors.add(cursor);
    try {
      final response = scope is SharedWorkspaceScope
          ? await _client.listSharedAuthoredManuscripts(
              scope: scope,
              limit: limit,
              cursor: cursor,
            )
          : await _client.listAuthoredManuscripts(
              domainId: (scope as InternalPitchScope).domainId,
              limit: limit,
              cursor: cursor,
            );
      if (!_isCurrent(generation, scope)) return;
      final page = _parsePage(response, expectedScope: scope);
      if (page.nextCursor == cursor && page.nextCursor != null ||
          page.nextCursor != null && _usedCursors.contains(page.nextCursor)) {
        throw const FormatException('SavedWork cursor repeated.');
      }
      final merged = append ? _mergeItems(_items, page.items) : page.items;
      if (!_isCurrent(generation, scope)) return;
      _items = List<InternalPitchSavedManuscript>.unmodifiable(merged);
      _hasMore = page.hasMore;
      _cursor = page.nextCursor;
      _pageMetadata = Map<String, dynamic>.unmodifiable(page.metadata);
      _errorCode = null;
    } catch (error) {
      if (_isCurrent(generation, scope)) _errorCode = _errorCodeFor(error);
    } finally {
      _end(generation);
    }
  }

  _SavedManuscriptPage _parsePage(
    Map<String, dynamic> response, {
    required LumenisWorkspaceScope expectedScope,
  }) {
    final rawItems = response['items'];
    final hasMore = response['has_more'];
    final nextCursor = response['next_cursor'];
    if (rawItems is! List || hasMore is! bool) {
      throw const FormatException('SavedWork page is malformed.');
    }
    if (nextCursor != null &&
        (nextCursor is! String ||
            nextCursor.isEmpty ||
            nextCursor.length > 4096 ||
            RegExp(r'[\x00-\x1f\x7f]').hasMatch(nextCursor))) {
      throw const FormatException('SavedWork cursor is malformed.');
    }

    final pageItems = <InternalPitchSavedManuscript>[];
    for (final rawItem in rawItems) {
      final row = _stringMap(rawItem);
      if (row == null) {
        throw const FormatException('SavedWork item is malformed.');
      }
      final document = _stringMap(row['document']);
      if (document == null) {
        throw const FormatException('SavedWork document is malformed.');
      }
      if (!_isAuthoredManuscriptV4(document['contract'])) continue;
      final context = _stringMap(document['context']);
      if (context == null) {
        throw const FormatException('SavedWork context is malformed.');
      }
      // The report/v4 endpoint can include other focus records for a domain.
      // They stay out of this exact caller scope without affecting pagination.
      if (!_savedDocumentContextMatches(context, expectedScope)) continue;
      pageItems.add(_parseSavedManuscript(row, expectedScope: expectedScope));
    }

    final metadata = Map<String, dynamic>.of(response)..remove('items');
    return _SavedManuscriptPage(
      items: List<InternalPitchSavedManuscript>.unmodifiable(pageItems),
      hasMore: hasMore,
      nextCursor: nextCursor as String?,
      metadata: metadata,
    );
  }

  List<InternalPitchSavedManuscript> _mergeItems(
    List<InternalPitchSavedManuscript> current,
    List<InternalPitchSavedManuscript> incoming,
  ) {
    final merged = List<InternalPitchSavedManuscript>.of(current);
    for (final item in incoming) {
      final existing = merged.where(
        (value) => value.artifactId == item.artifactId,
      );
      if (existing.isEmpty) {
        merged.add(item);
      } else if (!_sameSaved(existing.first, item)) {
        throw const FormatException('Conflicting SavedWork manuscript row.');
      }
    }
    return merged;
  }

  _TaskReply _validateTaskReply(
    Map<String, dynamic> response, {
    String? expectedTaskId,
    required LumenisWorkspaceScope scope,
  }) {
    final taskId = response['task_id'];
    final state = response['state'];
    final error = response['error'];
    if (taskId is! String ||
        !_isTaskId(taskId) ||
        (expectedTaskId != null && taskId != expectedTaskId) ||
        state is! String ||
        state.isEmpty ||
        !response.containsKey('error') ||
        (error != null && _safeErrorCode(error) == null) ||
        !_scopeMatches(_stringMap(response['scope']), scope)) {
      throw const FormatException('Internal pitch task reply is malformed.');
    }
    return _TaskReply(taskId, state, error as String?);
  }

  InternalPitchSavedManuscript _parseTaskCommit(
    Map<String, dynamic> response, {
    required LumenisWorkspaceScope scope,
    required String taskId,
    required InternalPitchManuscript? expectedManuscript,
    required InternalPitchSavedManuscript? expectedParent,
    required String? expectedRequestId,
    required InternalPitchSavedManuscript? expectedSaved,
  }) {
    final work = _stringMap(response['work']);
    final receipt = _stringMap(response['action_receipt']);
    if (work == null || receipt == null) {
      throw const FormatException(
        'Internal pitch commit is missing its receipt.',
      );
    }
    final saved = _parseSavedManuscript(
      work,
      expectedScope: scope,
      requireReceipt: true,
    );
    final document = _stringMap(work['document'])!;
    final shouldCheckParent =
        expectedManuscript != null ||
        expectedRequestId != null ||
        expectedParent != null;
    if (saved.taskId != taskId ||
        document['request_id'] != expectedRequestId &&
            expectedRequestId != null ||
        expectedManuscript != null &&
            !_sameJson(
              saved.manuscript.toJson(),
              expectedManuscript.toJson(),
            ) ||
        (shouldCheckParent && !_parentMatches(saved, expectedParent)) ||
        expectedSaved != null && !_sameSaved(saved, expectedSaved) ||
        !_actionReceiptMatches(receipt, saved, scope, taskId)) {
      throw const FormatException(
        'Internal pitch commit does not match its input.',
      );
    }
    return saved;
  }

  InternalPitchSavedManuscript _parseSavedManuscript(
    Map<String, dynamic> row, {
    required LumenisWorkspaceScope expectedScope,
    bool requireReceipt = false,
  }) {
    final artifact = _stringMap(row['artifact']);
    final document = _stringMap(row['document']);
    if (artifact == null || document == null) {
      throw const FormatException('SavedWork record is malformed.');
    }
    final context = _stringMap(document['context']);
    final contract = _stringMap(document['contract']);
    final payload = _stringMap(document['payload']);
    if (document['schema'] != 'lumenis.saved-work/v1' ||
        context == null ||
        !_savedDocumentContextMatches(context, expectedScope) ||
        !_isAuthoredManuscriptV4(contract) ||
        document['kind'] != 'report' ||
        payload == null ||
        payload.length != 2 ||
        !_stringMap(payload['truth_state']).isTruthyMap) {
      throw const FormatException('SavedWork manuscript contract is invalid.');
    }
    final rawManuscript = _stringMap(payload['manuscript']);
    if (rawManuscript == null) {
      throw const FormatException('SavedWork manuscript payload is invalid.');
    }
    final manuscript = _parseManuscript(rawManuscript);
    final truthState = _stringMap(payload['truth_state'])!;
    const truthFields = {
      'source_admission',
      'citation_admission',
      'external_fact_verification',
      'owned_model_execution',
      'external_effect',
      'business_outcome',
    };
    if (truthFields.any((field) => truthState[field] is! String) ||
        truthState.length != truthFields.length ||
        truthState['source_admission'] !=
            (manuscript.authorship == 'user_supplied'
                ? 'USER_AUTHORED_CONTENT'
                : 'ASSISTED_DERIVED_CONTENT') ||
        truthState['citation_admission'] != 'NO_SIGNED_QUOTE' ||
        truthState['external_fact_verification'] !=
            'NOT_INFERRED_FROM_AUTHORSHIP' ||
        truthState['owned_model_execution'] != 'NOT_RUN' ||
        truthState['external_effect'] != 'NOT_PERFORMED' ||
        truthState['business_outcome'] != 'NOT_OBSERVED' ||
        payload.containsKey('shot_plan') ||
        payload.containsKey('upstream_binding') ||
        payload.containsKey('input_manifest')) {
      throw const FormatException(
        'SavedWork manuscript truth state is invalid.',
      );
    }

    final artifactId = artifact['artifact_id'];
    final artifactSha256 = artifact['sha256'];
    final artifactSize = artifact['size_bytes'];
    final workId = document['work_id'];
    final version = document['version'];
    final previousArtifactId = document['parent_artifact_id'];
    final parentSha256 = document['parent_sha256'];
    final draftDigest = document['draft_digest'];
    final taskId = document['task_id'];
    final requestId = document['request_id'];
    final inputHash = document['input_hash'];
    if (artifactId is! String ||
        !_isArtifactIdValue(artifactId) ||
        artifactSha256 is! String ||
        !_isDigest(artifactSha256) ||
        artifactSize is! int ||
        artifactSize <= 0 ||
        artifactSize > 8 * 1024 * 1024 ||
        artifact['kind'] != 'saved_document' ||
        workId is! String ||
        !_isWorkId(workId) ||
        artifact['source_execution_id'] != workId ||
        version is! int ||
        version < 1 ||
        previousArtifactId != null &&
            (previousArtifactId is! String ||
                !_isArtifactIdValue(previousArtifactId)) ||
        parentSha256 != null &&
            (parentSha256 is! String || !_isDigest(parentSha256)) ||
        (version == 1 &&
            (previousArtifactId != null || parentSha256 != null)) ||
        (version > 1 && (previousArtifactId == null || parentSha256 == null)) ||
        draftDigest is! String ||
        !_isDigest(draftDigest) ||
        taskId is! String ||
        !_isTaskId(taskId) ||
        requestId is! String ||
        !RegExp(r'^[A-Za-z0-9_-]{8,128}$').hasMatch(requestId) ||
        inputHash is! String ||
        !_isDigest(inputHash) ||
        document['title'] != manuscript.title ||
        document['markdown'] != _markdownFor(manuscript) ||
        document['assertion_id'] != null ||
        document['citations'] is! List ||
        (document['citations'] as List).isNotEmpty) {
      throw const FormatException('SavedWork manuscript identity is invalid.');
    }

    final rawAttachments = document['attachments'];
    if (rawAttachments is! List || rawAttachments.length != 1) {
      throw const FormatException(
        'SavedWork manuscript attachment is invalid.',
      );
    }
    final attachment = _stringMap(rawAttachments.single);
    if (attachment == null ||
        attachment['name'] != 'document.docx' ||
        !_isArtifactIdValue(attachment['artifact_id']) ||
        attachment['artifact_id'] == artifactId ||
        !_isDigest(attachment['sha256']) ||
        attachment['size_bytes'] is! int ||
        (attachment['size_bytes'] as int) <= 0 ||
        (attachment['size_bytes'] as int) > 8 * 1024 * 1024 ||
        attachment['media_type'] != _docxMediaType) {
      throw const FormatException(
        'SavedWork manuscript attachment is invalid.',
      );
    }

    if (version > 1 &&
        (previousArtifactId == artifactId ||
            previousArtifactId == null ||
            parentSha256 == artifactSha256)) {
      throw const FormatException('SavedWork manuscript parent is invalid.');
    }

    final returnRef = _stringMap(row['return_ref']);
    if (returnRef != null &&
        (returnRef.length != 4 ||
            returnRef['artifact_id'] != artifactId ||
            returnRef['work_id'] != workId ||
            returnRef['version'] != version ||
            !_scopeMatches(_stringMap(returnRef['scope']), expectedScope))) {
      throw const FormatException('SavedWork return reference is invalid.');
    }

    final receipt = _stringMap(row['receipt']);
    if (requireReceipt && (receipt == null || returnRef == null)) {
      throw const FormatException('SavedWork commit receipt is missing.');
    }
    if (receipt != null &&
        !_savedWorkReceiptMatches(receipt, artifact, document, expectedScope)) {
      throw const FormatException('SavedWork commit receipt is invalid.');
    }

    return InternalPitchSavedManuscript(
      artifactId: artifactId,
      artifactSha256: artifactSha256,
      artifactSizeBytes: artifactSize,
      workId: workId,
      version: version,
      previousArtifactId: previousArtifactId as String?,
      parentSha256: parentSha256 as String?,
      draftDigest: draftDigest,
      taskId: taskId,
      outputArtifactId: attachment['artifact_id'] as String,
      outputSha256: attachment['sha256'] as String,
      outputSizeBytes: attachment['size_bytes'] as int,
      manuscript: manuscript,
    );
  }

  InternalPitchManuscript _parseManuscript(Map<String, dynamic> raw) {
    const expectedKeys = {
      'title',
      'summary',
      'sections',
      'language',
      'authorship',
    };
    final sections = raw['sections'];
    if (raw.keys.toSet().difference(expectedKeys).isNotEmpty ||
        expectedKeys.difference(raw.keys.toSet()).isNotEmpty ||
        raw['title'] is! String ||
        raw['summary'] is! String ||
        sections is! List ||
        raw['language'] is! String ||
        raw['authorship'] is! String) {
      throw const FormatException('SavedWork manuscript payload is invalid.');
    }
    final parsedSections = <InternalPitchSection>[];
    for (final rawSection in sections) {
      final section = _stringMap(rawSection);
      if (section == null ||
          section.length != 2 ||
          section['heading'] is! String ||
          section['body'] is! String) {
        throw const FormatException('SavedWork manuscript section is invalid.');
      }
      parsedSections.add(
        InternalPitchSection(
          heading: section['heading'] as String,
          body: section['body'] as String,
        ),
      );
    }
    final manuscript = InternalPitchManuscript(
      title: raw['title'] as String,
      summary: raw['summary'] as String,
      sections: parsedSections,
      language: raw['language'] as String,
      authorship: raw['authorship'] as String,
    );
    try {
      manuscript.toJson();
    } on FormatException {
      throw const FormatException('SavedWork manuscript payload is invalid.');
    }
    return manuscript;
  }

  bool _savedWorkReceiptMatches(
    Map<String, dynamic> receipt,
    Map<String, dynamic> artifact,
    Map<String, dynamic> document,
    LumenisWorkspaceScope scope,
  ) {
    final parent = _stringMap(receipt['parent']);
    final observations = _stringMap(receipt['constraint_observations']);
    return receipt['schema'] == 'lumenis.committed-saved-work/v1' &&
        receipt['task_id'] == document['task_id'] &&
        receipt['assertion_id'] == document['assertion_id'] &&
        document['assertion_id'] == null &&
        _sameJson(receipt['contract'], document['contract']) &&
        _scopeMatches(_stringMap(receipt['scope']), scope) &&
        receipt['ref'] == artifact['artifact_id'] &&
        receipt['work_id'] == document['work_id'] &&
        receipt['version'] == document['version'] &&
        parent != null &&
        parent['ref'] == document['parent_artifact_id'] &&
        parent['sha256'] == document['parent_sha256'] &&
        receipt['sha256'] == artifact['sha256'] &&
        receipt['size_bytes'] == artifact['size_bytes'] &&
        receipt['draft_digest'] == document['draft_digest'] &&
        receipt['sources'] is List &&
        (receipt['sources'] as List).isEmpty &&
        observations != null &&
        observations['committed_bytes_match'] == true &&
        observations['parent_chain_verified'] == true &&
        _sameJson(observations['required_payload_paths_present'], [
          'manuscript',
          'truth_state',
        ]);
  }

  bool _actionReceiptMatches(
    Map<String, dynamic> receipt,
    InternalPitchSavedManuscript saved,
    LumenisWorkspaceScope scope,
    String taskId,
  ) {
    final output = _stringMap(receipt['output']);
    // The task receipt is checked against the committed work and its output.
    return receipt['owner'] == 'Shared ContentCreation/TaskEngine/SavedWork' &&
        receipt['task_id'] == taskId &&
        receipt['artifact_id'] == saved.artifactId &&
        receipt['sha256'] == saved.artifactSha256 &&
        receipt['size_bytes'] == saved.artifactSizeBytes &&
        receipt['work_id'] == saved.workId &&
        receipt['version'] == saved.version &&
        receipt['parent_artifact_id'] == saved.previousArtifactId &&
        receipt['parent_sha256'] == saved.parentSha256 &&
        receipt['execution_state'] == 'ARTIFACT_COMMITTED' &&
        receipt['business_outcome'] == 'NOT_OBSERVED' &&
        receipt['external_effect'] == 'NOT_PERFORMED' &&
        _scopeMatches(_stringMap(receipt['scope']), scope) &&
        output != null &&
        output['name'] == 'document.docx' &&
        output['artifact_id'] == saved.outputArtifactId &&
        output['sha256'] == saved.outputSha256 &&
        output['media_type'] == _docxMediaType &&
        output['size_bytes'] == saved.outputSizeBytes &&
        receipt['action_kind'] ==
            (saved.version == 1
                ? 'INTERNAL_TEXT_CREATION'
                : 'INTERNAL_TEXT_REVISION');
  }

  bool _parentMatches(
    InternalPitchSavedManuscript saved,
    InternalPitchSavedManuscript? expectedParent,
  ) {
    if (expectedParent == null) {
      return saved.version == 1 &&
          saved.previousArtifactId == null &&
          saved.parentSha256 == null;
    }
    return saved.version == expectedParent.version + 1 &&
        saved.workId == expectedParent.workId &&
        saved.previousArtifactId == expectedParent.artifactId &&
        saved.parentSha256 == expectedParent.artifactSha256;
  }

  bool _attemptNeedsResolution(_ManuscriptAttempt attempt) {
    if (attempt.taskId == null) return attempt.prepareOutcomeUnknown;
    if (attempt.taskState == 'succeeded') return attempt.savedWork == null;
    if (const {'failed', 'cancelled', 'canceled'}.contains(attempt.taskState)) {
      return false;
    }
    return true;
  }

  bool _sameSaved(
    InternalPitchSavedManuscript left,
    InternalPitchSavedManuscript right,
  ) =>
      left.artifactId == right.artifactId &&
      left.artifactSha256 == right.artifactSha256 &&
      left.artifactSizeBytes == right.artifactSizeBytes &&
      left.workId == right.workId &&
      left.version == right.version &&
      left.previousArtifactId == right.previousArtifactId &&
      left.parentSha256 == right.parentSha256 &&
      left.draftDigest == right.draftDigest &&
      left.taskId == right.taskId &&
      left.outputArtifactId == right.outputArtifactId &&
      left.outputSha256 == right.outputSha256 &&
      left.outputSizeBytes == right.outputSizeBytes &&
      _sameJson(left.manuscript.toJson(), right.manuscript.toJson());

  bool _begin(ManuscriptControllerPhase phase) {
    if (_disposed || busy) return false;
    _operationCount++;
    _phase = phase;
    _errorCode = null;
    _notify();
    return true;
  }

  void _end(int generation) {
    if (_operationCount > 0) _operationCount--;
    if (_isCurrentGeneration(generation)) {
      _phase = ManuscriptControllerPhase.idle;
    }
    _notify();
  }

  bool _isCurrent(int generation, LumenisWorkspaceScope scope) =>
      _isCurrentGeneration(generation) && _sameScope(_scope, scope);

  bool _isCurrentGeneration(int generation) =>
      !_disposed && generation == _scopeGeneration;

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  String _snapshotKey(
    LumenisWorkspaceScope scope,
    InternalPitchManuscript manuscript,
    InternalPitchSavedManuscript? parent,
  ) => _canonicalJson({
    'scope': scope.toJson(),
    'manuscript': manuscript.toJson(),
    'parent': parent == null
        ? null
        : {
            'artifact_id': parent.artifactId,
            'artifact_sha256': parent.artifactSha256,
            'draft_digest': parent.draftDigest,
            'version': parent.version,
            'work_id': parent.workId,
          },
  });

  static String _newRequestId() =>
      'pitch-${List.generate(24, (_) => _random.nextInt(16).toRadixString(16)).join()}';

  static String _canonicalJson(Object? value) =>
      jsonEncode(_canonicalValue(value));

  static Object? _canonicalValue(Object? value) {
    if (value is Map) {
      final keys = value.keys.map((key) => key.toString()).toList()..sort();
      return <String, Object?>{
        for (final key in keys) key: _canonicalValue(value[key]),
      };
    }
    if (value is List) return value.map(_canonicalValue).toList();
    return value;
  }

  static bool _sameJson(Object? left, Object? right) =>
      _canonicalJson(left) == _canonicalJson(right);

  static Map<String, dynamic>? _stringMap(Object? value) {
    if (value is! Map) return null;
    final result = <String, dynamic>{};
    for (final entry in value.entries) {
      if (entry.key is! String) return null;
      result[entry.key as String] = entry.value;
    }
    return result;
  }

  static bool _scopeMatches(
    Map<String, dynamic>? value,
    LumenisWorkspaceScope expected,
  ) {
    if (value == null) return false;
    if (expected is SharedWorkspaceScope) {
      return value.length == 2 &&
          value['scope_kind'] == 'shared_workspace' &&
          value['version'] == 1;
    }
    if (expected is! InternalPitchScope || value.length != 4) return false;
    final actualDomain = _canonicalSavedWorkDomain(value['domain_id']);
    final expectedDomain = _canonicalSavedWorkDomain(expected.domainId);
    return actualDomain != null &&
        expectedDomain != null &&
        actualDomain == expectedDomain &&
        value.containsKey('subject_id') &&
        value.containsKey('brand_focus_id') &&
        value.containsKey('global_scope') &&
        value['subject_id'] == expected.subjectId &&
        value['brand_focus_id'] == expected.brandFocusId &&
        value['global_scope'] == expected.globalScope;
  }

  static bool _savedDocumentContextMatches(
    Map<String, dynamic> value,
    LumenisWorkspaceScope expected,
  ) {
    final scopeKeys = expected.toJson().keys.toSet();
    final keys = value.keys.toSet();
    final identityFields = keys.difference(scopeKeys).toSet();
    final actorId = value['actor_id'];
    final principalKind = value['principal_kind'];
    final principalRef = value['principal_ref'];
    final identityIsValid =
        identityFields.isEmpty ||
        (keys.difference(scopeKeys).toSet().length == 1 &&
            keys.contains('actor_id') &&
            (actorId is String && actorId.isNotEmpty ||
                actorId is int && actorId >= 0)) ||
        (keys.difference(scopeKeys).toSet().length == 2 &&
            keys.containsAll({'principal_kind', 'principal_ref'}) &&
            principalKind is String &&
            principalKind.isNotEmpty &&
            principalRef is String &&
            principalRef.isNotEmpty);
    final scope = <String, dynamic>{
      for (final key in scopeKeys)
        if (value.containsKey(key)) key: value[key],
    };
    return identityIsValid &&
        scope.length == scopeKeys.length &&
        _scopeMatches(scope, expected);
  }

  static String? _canonicalSavedWorkDomain(Object? value) {
    if (value == 'cth') return 'cth';
    if (value == 'bmp' || value == 'zbmp') return 'zbmp';
    return null;
  }

  static bool _sameScope(
    LumenisWorkspaceScope? left,
    LumenisWorkspaceScope? right,
  ) => left == null
      ? right == null
      : right != null && _sameJson(left.toJson(), right.toJson());

  static bool _isAuthoredManuscriptV4(Object? value) {
    final contract = _stringMap(value);
    final paths = contract?['required_payload_paths'];
    return contract != null &&
        contract.length == 3 &&
        contract.keys.toSet().containsAll({
          'id',
          'version',
          'required_payload_paths',
        }) &&
        contract['id'] == 'lumenis.internal-pitch' &&
        contract['version'] == '4' &&
        paths is List &&
        paths.length == 2 &&
        paths[0] == 'manuscript' &&
        paths[1] == 'truth_state';
  }

  static bool _isArtifactIdValue(Object? value) =>
      value is String && RegExp(r'^ART-[0-9a-f]{16}$').hasMatch(value);

  static bool _isWorkId(Object? value) =>
      value is String && RegExp(r'^WORK-[0-9a-f]{24}$').hasMatch(value);

  static bool _isTaskId(Object? value) =>
      value is String && RegExp(r'^task-pitch-[0-9a-f]{24}$').hasMatch(value);

  static bool _isDigest(Object? value) =>
      value is String && RegExp(r'^[0-9a-f]{64}$').hasMatch(value);

  static String _markdownFor(InternalPitchManuscript manuscript) =>
      '${manuscript.title}\n\n${manuscript.summary}\n\n${manuscript.sections.map((section) => '## ${section.heading}\n\n${section.body}').join('\n\n')}';

  static String? _safeErrorCode(Object? value) =>
      value is String && RegExp(r'^[A-Z][A-Z_0-9]{0,99}$').hasMatch(value)
      ? value
      : null;

  static bool _writeOutcomeUnknown(Object error) {
    if (error is LumenisCoreException) {
      final status = error.statusCode;
      return status == null || status >= 500;
    }
    return true;
  }

  static String _errorCodeFor(Object error) {
    if (error is LumenisCoreException) {
      return _safeErrorCode(error.errorCode) ??
          (error.statusCode == 401
              ? 'CONTENT_AUTH_REQUIRED'
              : error.statusCode == 403
              ? 'CONTENT_SCOPE_DENIED'
              : 'INTERNAL_PITCH_REQUEST_FAILED');
    }
    if (error is FormatException) return 'INTERNAL_PITCH_RESPONSE_INVALID';
    if (error is TimeoutException) return 'INTERNAL_PITCH_REQUEST_TIMEOUT';
    if (error is ArgumentError) return 'INTERNAL_PITCH_INPUT_INVALID';
    return 'INTERNAL_PITCH_REQUEST_FAILED';
  }

  @override
  void dispose() {
    _disposed = true;
    _scopeGeneration++;
    _attempts.clear();
    super.dispose();
  }
}

final class _ManuscriptAttempt {
  _ManuscriptAttempt({
    required this.key,
    required this.scope,
    required this.manuscript,
    required this.parent,
    required this.requestId,
  });

  final String key;
  final LumenisWorkspaceScope scope;
  final InternalPitchManuscript manuscript;
  final InternalPitchSavedManuscript? parent;
  final String requestId;
  String? taskId;
  String? taskState;
  String? taskError;
  bool prepareOutcomeUnknown = false;
  bool runAttempted = false;
  bool runOutcomeUnknown = false;
  InternalPitchSavedManuscript? savedWork;

  InternalPitchRevision? get revision {
    final value = parent;
    if (value == null) return null;
    return InternalPitchRevision(
      workId: value.workId,
      previousArtifactId: value.artifactId,
      expectedDraftDigest: value.draftDigest,
    );
  }
}

final class _TaskReply {
  const _TaskReply(this.taskId, this.state, this.errorCode);

  final String taskId;
  final String state;
  final String? errorCode;
}

final class _SavedManuscriptPage {
  const _SavedManuscriptPage({
    required this.items,
    required this.hasMore,
    required this.nextCursor,
    required this.metadata,
  });

  final List<InternalPitchSavedManuscript> items;
  final bool hasMore;
  final String? nextCursor;
  final Map<String, dynamic> metadata;
}

extension on Map<String, dynamic>? {
  bool get isTruthyMap => this != null && this!.isNotEmpty;
}
