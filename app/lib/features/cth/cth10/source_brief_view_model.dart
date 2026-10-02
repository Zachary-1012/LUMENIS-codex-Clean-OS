import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';

enum SourceBriefPhase { idle, loading, ready, failed }

enum SourceBriefTaskState {
  unknown,
  pending,
  running,
  succeeded,
  failed,
  interrupted,
}

enum SourceBriefErrorKind {
  contextUnavailable,
  accessDenied,
  notFound,
  unavailable,
  invalidResponse,
  contextChanged,
  analysisUnavailable,
}

enum SourceBriefBusinessAnalysisState {
  unknown,
  notRequested,
  draft,
  unavailable,
  error,
}

final class SourceBriefScope {
  const SourceBriefScope({
    required this.productId,
    required this.domainId,
    required this.globalScope,
    required this.subjectId,
    required this.brandFocusId,
    required this.entityLabel,
    required this.scopeKey,
  });

  final String productId;
  final String domainId;
  final bool globalScope;
  final String? subjectId;
  final String? brandFocusId;
  final String entityLabel;
  final String scopeKey;
}

final class SourceBriefSource {
  const SourceBriefSource({
    required this.sourceId,
    required this.title,
    required this.sourceUrl,
    required this.publishedAt,
    required this.capturedAt,
    required this.evidenceRef,
  });

  final String sourceId;
  final String? title;
  final String? sourceUrl;
  final String? publishedAt;
  final String? capturedAt;
  final String evidenceRef;
}

final class SourceBriefObservation {
  const SourceBriefObservation({required this.sourceId, required this.excerpt});

  final String sourceId;
  final String excerpt;
}

final class SourceBriefInterpretation {
  SourceBriefInterpretation({
    required this.text,
    required List<String> sourceIds,
  }) : sourceIds = List.unmodifiable(sourceIds);

  final String text;
  final List<String> sourceIds;
}

final class SourceBriefPilotProposal {
  const SourceBriefPilotProposal({
    required this.audience,
    required this.procedure,
    required this.measure,
    required this.continueIf,
    required this.stopIf,
  });

  final String audience;
  final String procedure;
  final String measure;
  final String continueIf;
  final String stopIf;
}

final class SourceBriefProposedAction {
  SourceBriefProposedAction({
    required this.action,
    required this.reason,
    required this.check,
    required List<String> sourceIds,
    required this.pilot,
  }) : sourceIds = List.unmodifiable(sourceIds);

  final String action;
  final String reason;
  final String check;
  final List<String> sourceIds;
  final SourceBriefPilotProposal? pilot;
}

final class SourceBriefBusinessAnalysis {
  SourceBriefBusinessAnalysis({
    required List<SourceBriefObservation> sourceObservations,
    required List<SourceBriefInterpretation> interpretations,
    required List<SourceBriefProposedAction> proposedActions,
    required List<String> unknowns,
  }) : sourceObservations = List.unmodifiable(sourceObservations),
       interpretations = List.unmodifiable(interpretations),
       proposedActions = List.unmodifiable(proposedActions),
       unknowns = List.unmodifiable(unknowns);

  final List<SourceBriefObservation> sourceObservations;
  final List<SourceBriefInterpretation> interpretations;
  final List<SourceBriefProposedAction> proposedActions;
  final List<String> unknowns;
}

final class SourceBriefResult {
  SourceBriefResult({
    required this.jobId,
    required this.reportId,
    required this.artifactHash,
    required this.sourceCount,
    required this.scope,
    required List<SourceBriefSource> records,
    required this.businessQuestion,
    required this.businessAnalysisState,
    required this.analysis,
    required this.reviewStatus,
  }) : records = List.unmodifiable(records);

  final String jobId;
  final String reportId;
  final String artifactHash;
  final int? sourceCount;
  final SourceBriefScope scope;
  final List<SourceBriefSource> records;
  final String? businessQuestion;
  final SourceBriefBusinessAnalysisState businessAnalysisState;
  final SourceBriefBusinessAnalysis? analysis;
  final String reviewStatus;
}

class SourceBriefViewModel extends ChangeNotifier {
  SourceBriefViewModel({required this.client});

  static const String _domainId = 'CTH';

  final LumenisCoreClient client;
  bool _disposed = false;
  int _generation = 0;
  SourceBriefPhase _phase = SourceBriefPhase.idle;
  bool _busy = false;
  String? _taskId;
  String? _jobId;
  SourceBriefTaskState _taskState = SourceBriefTaskState.unknown;
  bool _canResume = false;
  SourceBriefResult? _result;
  SourceBriefErrorKind? _errorKind;
  String? _scopeLabel;
  _CthContextSelection? _selection;

  SourceBriefPhase get phase => _phase;
  bool get busy => _busy;
  String? get taskId => _taskId;
  String? get jobId => _jobId;
  SourceBriefTaskState get taskState => _taskState;
  bool get canResume => _canResume;
  SourceBriefResult? get result => _result;
  SourceBriefErrorKind? get errorKind => _errorKind;
  String? get scopeLabel => _scopeLabel;
  bool get globalScope => _selection?.globalScope == true;

  Future<void> initialize() async {
    if (_disposed) return;
    final operation = _beginOperation();
    final fresh = await _loadFreshContext(operation);
    if (fresh == null || !_isCurrent(operation)) return;
    _finish(
      operation,
      phase: SourceBriefPhase.ready,
      errorKind: fresh.scopeChanged
          ? SourceBriefErrorKind.contextChanged
          : null,
    );
  }

  Future<void> start({String? businessQuestion}) async {
    if (_disposed) return;
    final operation = _beginOperation();
    final fresh = await _loadFreshContext(operation);
    if (fresh == null || !_isCurrent(operation)) return;

    _clearReportState();
    if (!_contextStillCurrent(fresh, operation)) return;

    if (businessQuestion != null && businessQuestion.trim().isNotEmpty) {
      _finish(
        operation,
        phase: SourceBriefPhase.failed,
        errorKind: SourceBriefErrorKind.analysisUnavailable,
      );
      return;
    }

    try {
      final response = await client.startSourceBriefTask(
        domainId: _domainId,
        limit: 30,
      );
      if (!_isCurrent(operation)) return;
      if (!_contextStillCurrent(fresh, operation)) return;
      await _applyTaskResponse(response, fresh: fresh, operation: operation);
    } catch (error) {
      _fail(operation, _errorFor(error), fresh: fresh);
    }
  }

  Future<void> refreshTask() async {
    if (_disposed) return;
    final operation = _beginOperation();
    final expectedTaskId = _taskId;
    final expectedJobId = _jobId;
    final fresh = await _loadFreshContext(operation);
    if (fresh == null || !_isCurrent(operation)) return;
    if (fresh.scopeChanged) {
      _finish(
        operation,
        phase: SourceBriefPhase.ready,
        errorKind: SourceBriefErrorKind.contextChanged,
      );
      return;
    }
    if (expectedTaskId == null) {
      _finish(
        operation,
        phase: SourceBriefPhase.failed,
        errorKind: SourceBriefErrorKind.notFound,
      );
      return;
    }
    if (!_contextStillCurrent(fresh, operation)) return;

    try {
      final response = await client.sourceBriefTask(
        domainId: _domainId,
        taskId: expectedTaskId,
      );
      if (!_isCurrent(operation)) return;
      if (!_contextStillCurrent(fresh, operation)) return;
      await _applyTaskResponse(
        response,
        fresh: fresh,
        operation: operation,
        expectedTaskId: expectedTaskId,
        expectedJobId: expectedJobId,
      );
    } catch (error) {
      _fail(operation, _errorFor(error), fresh: fresh);
    }
  }

  Future<void> resume() async {
    if (_disposed) return;
    final operation = _beginOperation();
    final expectedTaskId = _taskId;
    final expectedJobId = _jobId;
    final wasResumable = _canResume;
    final fresh = await _loadFreshContext(operation);
    if (fresh == null || !_isCurrent(operation)) return;
    if (fresh.scopeChanged) {
      _finish(
        operation,
        phase: SourceBriefPhase.ready,
        errorKind: SourceBriefErrorKind.contextChanged,
      );
      return;
    }
    if (expectedTaskId == null || !wasResumable) {
      _finish(
        operation,
        phase: SourceBriefPhase.failed,
        errorKind: SourceBriefErrorKind.invalidResponse,
      );
      return;
    }
    if (!_contextStillCurrent(fresh, operation)) return;

    try {
      final response = await client.resumeSourceBriefTask(
        domainId: _domainId,
        taskId: expectedTaskId,
      );
      if (!_isCurrent(operation)) return;
      if (!_contextStillCurrent(fresh, operation)) return;
      await _applyTaskResponse(
        response,
        fresh: fresh,
        operation: operation,
        expectedTaskId: expectedTaskId,
        expectedJobId: expectedJobId,
      );
    } catch (error) {
      _fail(operation, _errorFor(error), fresh: fresh);
    }
  }

  Future<void> openTask(String taskId) async {
    if (_disposed) return;
    final operation = _beginOperation();
    final requestedTaskId = _safeIdentifier(taskId);
    final fresh = await _loadFreshContext(operation);
    if (fresh == null || !_isCurrent(operation)) return;
    if (fresh.scopeChanged) {
      _finish(
        operation,
        phase: SourceBriefPhase.ready,
        errorKind: SourceBriefErrorKind.contextChanged,
      );
      return;
    }
    if (requestedTaskId == null) {
      _finish(
        operation,
        phase: SourceBriefPhase.failed,
        errorKind: SourceBriefErrorKind.invalidResponse,
      );
      return;
    }
    _clearReportState();
    if (!_contextStillCurrent(fresh, operation)) return;

    try {
      final response = await client.sourceBriefTask(
        domainId: _domainId,
        taskId: requestedTaskId,
      );
      if (!_isCurrent(operation)) return;
      if (!_contextStillCurrent(fresh, operation)) return;
      await _applyTaskResponse(
        response,
        fresh: fresh,
        operation: operation,
        expectedTaskId: requestedTaskId,
      );
    } catch (error) {
      _fail(operation, _errorFor(error), fresh: fresh);
    }
  }

  Future<void> reopenJob(String jobId) async {
    if (_disposed) return;
    final operation = _beginOperation();
    final requestedJobId = _safeIdentifier(jobId);
    final fresh = await _loadFreshContext(operation);
    if (fresh == null || !_isCurrent(operation)) return;
    if (fresh.scopeChanged) {
      _finish(
        operation,
        phase: SourceBriefPhase.ready,
        errorKind: SourceBriefErrorKind.contextChanged,
      );
      return;
    }
    if (requestedJobId == null) {
      _finish(
        operation,
        phase: SourceBriefPhase.failed,
        errorKind: SourceBriefErrorKind.invalidResponse,
      );
      return;
    }
    _clearReportState();
    if (!_contextStillCurrent(fresh, operation)) return;
    await _readBackJob(requestedJobId, fresh: fresh, operation: operation);
  }

  void clear() {
    if (_disposed) return;
    _generation += 1;
    _clearReportState();
    _busy = false;
    _errorKind = null;
    _phase = _selection == null
        ? SourceBriefPhase.idle
        : SourceBriefPhase.ready;
    notifyListeners();
  }

  /// Invalidates transient results immediately after the shell changes scope.
  /// The server still reauthorizes every report request independently.
  void syncContext() {
    if (_disposed || _selection == null) return;
    final selection = _selectionFromEnvelope(client.currentContextEnvelope);
    if (selection != null && _selection!.sameScope(selection)) return;

    _generation += 1;
    _clearReportState();
    if (selection == null) {
      _forgetContext();
      _phase = SourceBriefPhase.failed;
    } else {
      _selection = selection;
      _scopeLabel = selection.scopeLabel;
      _phase = SourceBriefPhase.ready;
    }
    _busy = false;
    _errorKind = SourceBriefErrorKind.contextChanged;
    notifyListeners();
  }

  Future<_FreshCthContext?> _loadFreshContext(int operation) async {
    try {
      final response = await client.settingsContext();
      if (!_isCurrent(operation)) return null;
      final selection = _CthContextSelection.parse(response);
      if (selection == null) {
        _forgetContext();
        _finish(
          operation,
          phase: SourceBriefPhase.failed,
          errorKind: SourceBriefErrorKind.contextUnavailable,
        );
        return null;
      }
      final responseSignature = _contextSignature(response);
      final currentSignature = _contextSignature(client.currentContextEnvelope);
      if (responseSignature == null || responseSignature != currentSignature) {
        _updateSelectionFromCurrentEnvelope();
        _finish(
          operation,
          phase: _selection == null
              ? SourceBriefPhase.failed
              : SourceBriefPhase.ready,
          errorKind: SourceBriefErrorKind.contextChanged,
        );
        return null;
      }

      final changed = _selection != null && !_selection!.sameScope(selection);
      if (changed) _clearReportState();
      _selection = selection;
      _scopeLabel = selection.scopeLabel;
      return _FreshCthContext(
        selection: selection,
        signature: responseSignature,
        scopeChanged: changed,
      );
    } catch (error) {
      if (!_isCurrent(operation)) return null;
      final errorKind = _errorFor(error);
      if (errorKind == SourceBriefErrorKind.unavailable ||
          errorKind == SourceBriefErrorKind.accessDenied) {
        // Keep opaque recovery references, but never show a prior result
        // without a fresh, verified scope selection.
        _result = null;
        _scopeLabel = null;
        if (errorKind == SourceBriefErrorKind.accessDenied) {
          _canResume = false;
        }
      } else {
        _forgetContext();
      }
      _finish(operation, phase: SourceBriefPhase.failed, errorKind: errorKind);
      return null;
    }
  }

  bool _contextStillCurrent(_FreshCthContext fresh, int operation) {
    if (!_isCurrent(operation)) return false;
    if (_contextSignature(client.currentContextEnvelope) == fresh.signature) {
      return true;
    }
    _updateSelectionFromCurrentEnvelope();
    _finish(
      operation,
      phase: _selection == null
          ? SourceBriefPhase.failed
          : SourceBriefPhase.ready,
      errorKind: SourceBriefErrorKind.contextChanged,
    );
    return false;
  }

  void _updateSelectionFromCurrentEnvelope() {
    _clearReportState();
    final selection = _selectionFromEnvelope(client.currentContextEnvelope);
    if (selection == null) {
      _forgetContext();
      return;
    }
    _selection = selection;
    _scopeLabel = selection.scopeLabel;
  }

  Future<void> _applyTaskResponse(
    Map<String, dynamic> response, {
    required _FreshCthContext fresh,
    required int operation,
    String? expectedTaskId,
    String? expectedJobId,
  }) async {
    if (response['ok'] != true) {
      _fail(operation, _errorForResponse(response), fresh: fresh);
      return;
    }
    final task = _asMap(response['task']);
    if (task == null) {
      _finish(
        operation,
        phase: SourceBriefPhase.failed,
        errorKind: SourceBriefErrorKind.invalidResponse,
      );
      return;
    }

    final returnedTaskId = _safeIdentifier(task['task_id']);
    final returnedJobId = _safeIdentifier(task['job_id']);
    if (returnedTaskId == null ||
        returnedJobId == null ||
        (expectedTaskId != null && returnedTaskId != expectedTaskId) ||
        (expectedJobId != null && returnedJobId != expectedJobId)) {
      _clearReportState();
      _finish(
        operation,
        phase: SourceBriefPhase.failed,
        errorKind: SourceBriefErrorKind.invalidResponse,
      );
      return;
    }

    final parsedState = _parseTaskState(task['state']);
    _taskId = returnedTaskId;
    _jobId = returnedJobId;
    _taskState = parsedState;
    _canResume =
        task['can_resume'] == true &&
        const {
          SourceBriefTaskState.pending,
          SourceBriefTaskState.failed,
          SourceBriefTaskState.interrupted,
        }.contains(parsedState);
    _result = null;

    if (parsedState == SourceBriefTaskState.unknown) {
      _finish(
        operation,
        phase: SourceBriefPhase.failed,
        errorKind: SourceBriefErrorKind.invalidResponse,
      );
      return;
    }

    if (parsedState == SourceBriefTaskState.succeeded) {
      notifyListeners();
      await _readBackJob(returnedJobId, fresh: fresh, operation: operation);
      return;
    }

    _finish(
      operation,
      phase: SourceBriefPhase.ready,
      errorKind: parsedState == SourceBriefTaskState.failed
          ? _errorForTask(task['error'])
          : null,
    );
  }

  Future<void> _readBackJob(
    String jobId, {
    required _FreshCthContext fresh,
    required int operation,
  }) async {
    if (!_contextStillCurrent(fresh, operation)) return;
    try {
      final response = await client.sourceBriefJob(
        domainId: _domainId,
        jobId: jobId,
      );
      if (!_isCurrent(operation)) return;
      if (!_contextStillCurrent(fresh, operation)) return;
      if (response['ok'] != true) {
        _fail(operation, _errorForResponse(response), fresh: fresh);
        return;
      }
      final resultMap = _asMap(response['result']);
      if (resultMap == null) {
        _finish(
          operation,
          phase: SourceBriefPhase.failed,
          errorKind: SourceBriefErrorKind.invalidResponse,
        );
        return;
      }
      final parsed = _parseResult(
        resultMap,
        expectedJobId: jobId,
        expectedContext: fresh.selection,
      );
      _jobId = jobId;
      _taskState = SourceBriefTaskState.succeeded;
      _canResume = false;
      _result = parsed;
      _finish(operation, phase: SourceBriefPhase.ready);
    } catch (error) {
      _fail(operation, _errorFor(error), fresh: fresh);
    }
  }

  int _beginOperation() {
    if (_disposed) return _generation;
    _generation += 1;
    _busy = true;
    _phase = SourceBriefPhase.loading;
    _errorKind = null;
    // Each operation must verify access and the saved artifact again. Keep
    // recovery references, but do not present the previous read as current.
    _result = null;
    notifyListeners();
    return _generation;
  }

  void _finish(
    int operation, {
    required SourceBriefPhase phase,
    SourceBriefErrorKind? errorKind,
  }) {
    if (!_isCurrent(operation)) return;
    _busy = false;
    _phase = phase;
    _errorKind = errorKind;
    notifyListeners();
  }

  void _fail(
    int operation,
    SourceBriefErrorKind errorKind, {
    _FreshCthContext? fresh,
  }) {
    if (!_isCurrent(operation)) return;
    if (fresh != null &&
        _contextSignature(client.currentContextEnvelope) != fresh.signature) {
      _updateSelectionFromCurrentEnvelope();
      _finish(
        operation,
        phase: _selection == null
            ? SourceBriefPhase.failed
            : SourceBriefPhase.ready,
        errorKind: SourceBriefErrorKind.contextChanged,
      );
      return;
    }
    if (errorKind == SourceBriefErrorKind.accessDenied ||
        errorKind == SourceBriefErrorKind.notFound) {
      _canResume = false;
    }
    _finish(operation, phase: SourceBriefPhase.failed, errorKind: errorKind);
  }

  void _clearReportState() {
    _taskId = null;
    _jobId = null;
    _taskState = SourceBriefTaskState.unknown;
    _canResume = false;
    _result = null;
  }

  void _forgetContext() {
    _clearReportState();
    _selection = null;
    _scopeLabel = null;
  }

  bool _isCurrent(int operation) => !_disposed && operation == _generation;

  SourceBriefErrorKind _errorFor(Object error) {
    if (error is _ContextChanged) {
      return SourceBriefErrorKind.contextChanged;
    }
    if (error is FormatException || error is _InvalidSourceBriefResponse) {
      return SourceBriefErrorKind.invalidResponse;
    }
    if (error is LumenisCoreException) {
      return switch (error.statusCode) {
        401 || 403 => SourceBriefErrorKind.accessDenied,
        404 => SourceBriefErrorKind.notFound,
        _ => SourceBriefErrorKind.unavailable,
      };
    }
    return SourceBriefErrorKind.unavailable;
  }

  SourceBriefErrorKind _errorForResponse(Map<String, dynamic> response) {
    final code = _safeText(response['code'], maxLength: 120)?.toUpperCase();
    if (code == null) return SourceBriefErrorKind.unavailable;
    if (code.contains('DENIED') || code.contains('FORBIDDEN')) {
      return SourceBriefErrorKind.accessDenied;
    }
    if (code.contains('NOT_FOUND')) return SourceBriefErrorKind.notFound;
    return SourceBriefErrorKind.unavailable;
  }

  SourceBriefErrorKind _errorForTask(Object? value) {
    final code = _safeText(value, maxLength: 120)?.toUpperCase();
    if (code != null && code.contains('DENIED')) {
      return SourceBriefErrorKind.accessDenied;
    }
    return SourceBriefErrorKind.unavailable;
  }

  @override
  void dispose() {
    _disposed = true;
    _generation += 1;
    super.dispose();
  }
}

SourceBriefResult _parseResult(
  Map<String, Object?> result, {
  required String expectedJobId,
  required _CthContextSelection expectedContext,
}) {
  if (result['job_id'] != expectedJobId || result['job_state'] != 'completed') {
    throw const _InvalidSourceBriefResponse();
  }
  final artifact = _asMap(result['artifact_outcome']);
  if (artifact == null ||
      artifact['state'] != 'persisted_and_reopened_verified' ||
      artifact['report_id'] != expectedJobId) {
    throw const _InvalidSourceBriefResponse();
  }
  final artifactHash = _safeText(artifact['artifact_hash'], maxLength: 64);
  if (artifactHash == null ||
      !RegExp(r'^[0-9a-f]{64}$').hasMatch(artifactHash)) {
    throw const _InvalidSourceBriefResponse();
  }

  final countValue = artifact['source_count'];
  final sourceCount = countValue == null
      ? null
      : countValue is int && countValue >= 0
      ? countValue
      : throw const _InvalidSourceBriefResponse();

  final sourceBrief = _asMap(result['source_brief']);
  if (sourceBrief == null) throw const _InvalidSourceBriefResponse();
  final rawScope = _asMap(sourceBrief['scope']);
  final scope = _parseScope(rawScope);
  if (scope == null) throw const _InvalidSourceBriefResponse();
  if (!expectedContext.matches(scope)) throw const _ContextChanged();
  final rawRecords = sourceBrief['records'];
  if (rawRecords is! List) throw const _InvalidSourceBriefResponse();
  final records = <SourceBriefSource>[];
  for (final rawRecord in rawRecords) {
    final record = _asMap(rawRecord);
    if (record == null) throw const _InvalidSourceBriefResponse();
    final sourceId = _safeIdentifier(record['source_id']);
    final evidenceRef = _safeIdentifier(record['scope_evidence_ref']);
    if (sourceId == null ||
        evidenceRef == null ||
        record['evidence_id'] != evidenceRef) {
      throw const _InvalidSourceBriefResponse();
    }
    if (!scope.globalScope &&
        (record['subject_id'] != scope.subjectId ||
            record['brand_focus_id'] != null)) {
      throw const _ContextChanged();
    }
    records.add(
      SourceBriefSource(
        sourceId: sourceId,
        title: _safeText(record['title'], maxLength: 240),
        sourceUrl: _safeSourceUrl(record['source_url']),
        publishedAt: _safeText(record['publish_datetime'], maxLength: 100),
        capturedAt: _safeText(record['captured_at'], maxLength: 100),
        evidenceRef: evidenceRef,
      ),
    );
  }
  if (sourceCount != null && sourceCount != records.length) {
    throw const _InvalidSourceBriefResponse();
  }

  final rawBusiness = _asMap(result['business_analysis']);
  final businessState = _businessAnalysisState(rawBusiness?['state']);
  final question = _safeText(result['business_question'], maxLength: 1500);
  SourceBriefBusinessAnalysis? analysis;
  if (businessState == SourceBriefBusinessAnalysisState.draft) {
    final rawAnalysis = _asMap(rawBusiness?['analysis']);
    if (rawAnalysis == null) throw const _InvalidSourceBriefResponse();
    analysis = _parseBusinessAnalysis(
      rawAnalysis,
      knownSourceIds: records.map((record) => record.sourceId).toSet(),
    );
  }

  final reviewStatus = _safeReviewStatus(
    result['review_status'] ?? rawBusiness?['review_status'],
  );
  return SourceBriefResult(
    jobId: expectedJobId,
    reportId: artifact['report_id'] as String,
    artifactHash: artifactHash,
    sourceCount: sourceCount,
    scope: scope,
    records: records,
    businessQuestion: question,
    businessAnalysisState: businessState,
    analysis: analysis,
    reviewStatus: reviewStatus,
  );
}

SourceBriefScope? _parseScope(Map<String, Object?>? value) {
  if (value == null ||
      value['product_id'] != 'CTH' ||
      value['domain_id'] != 'cth' ||
      value['global'] is! bool) {
    return null;
  }
  final globalScope = value['global'] as bool;
  final rawSubjectId = value['subject_id'];
  final rawBrandFocusId = value['brand_focus_id'];
  final subjectId = _optionalIdentifier(rawSubjectId);
  final brandFocusId = _optionalIdentifier(rawBrandFocusId);
  final entityLabel = _safeText(value['entity_label'], maxLength: 240);
  final scopeKey = _safeText(value['scope_key'], maxLength: 64);
  if (entityLabel == null ||
      scopeKey == null ||
      !RegExp(r'^[0-9a-f]{64}$').hasMatch(scopeKey) ||
      (rawSubjectId != null && subjectId == null) ||
      (rawBrandFocusId != null && brandFocusId == null) ||
      (globalScope && (subjectId != null || brandFocusId != null)) ||
      (!globalScope && (subjectId == null || brandFocusId != null))) {
    return null;
  }
  return SourceBriefScope(
    productId: 'CTH',
    domainId: 'cth',
    globalScope: globalScope,
    subjectId: subjectId,
    brandFocusId: brandFocusId,
    entityLabel: entityLabel,
    scopeKey: scopeKey,
  );
}

SourceBriefBusinessAnalysis _parseBusinessAnalysis(
  Map<String, Object?> value, {
  required Set<String> knownSourceIds,
}) {
  const keys = {
    'source_observations',
    'interpretations',
    'proposed_actions',
    'unknowns',
  };
  if (value.keys.toSet().difference(keys).isNotEmpty ||
      value.keys.toSet().length != keys.length) {
    throw const _InvalidSourceBriefResponse();
  }

  final observationsValue = value['source_observations'];
  final interpretationsValue = value['interpretations'];
  final actionsValue = value['proposed_actions'];
  final unknownsValue = value['unknowns'];
  if (observationsValue is! List ||
      interpretationsValue is! List ||
      actionsValue is! List ||
      unknownsValue is! List ||
      observationsValue.isEmpty ||
      interpretationsValue.isEmpty ||
      actionsValue.isEmpty ||
      unknownsValue.isEmpty ||
      observationsValue.length > 3 ||
      interpretationsValue.length > 3 ||
      actionsValue.length > 3 ||
      unknownsValue.length > 5) {
    throw const _InvalidSourceBriefResponse();
  }

  final observations = <SourceBriefObservation>[];
  for (final raw in observationsValue) {
    final row = _asMap(raw);
    final sourceId = _safeIdentifier(row?['source_id']);
    final excerpt = _safeText(row?['excerpt'], maxLength: 500);
    if (row == null ||
        row.keys.toSet().difference({'source_id', 'excerpt'}).isNotEmpty ||
        sourceId == null ||
        !knownSourceIds.contains(sourceId) ||
        excerpt == null) {
      throw const _InvalidSourceBriefResponse();
    }
    observations.add(
      SourceBriefObservation(sourceId: sourceId, excerpt: excerpt),
    );
  }

  final interpretations = <SourceBriefInterpretation>[];
  for (final raw in interpretationsValue) {
    final row = _asMap(raw);
    final text = _safeText(row?['text'], maxLength: 180);
    final sourceIds = _sourceReferences(
      row?['source_ids'],
      knownSourceIds: knownSourceIds,
    );
    if (row == null ||
        row.keys.toSet().difference({'text', 'source_ids'}).isNotEmpty ||
        text == null ||
        sourceIds == null) {
      throw const _InvalidSourceBriefResponse();
    }
    interpretations.add(
      SourceBriefInterpretation(text: text, sourceIds: sourceIds),
    );
  }

  final actions = <SourceBriefProposedAction>[];
  for (final raw in actionsValue) {
    final row = _asMap(raw);
    final action = _safeText(row?['action'], maxLength: 180);
    final reason = _safeText(row?['reason'], maxLength: 180);
    final check = _safeText(row?['check'], maxLength: 180);
    final sourceIds = _sourceReferences(
      row?['source_ids'],
      knownSourceIds: knownSourceIds,
    );
    final pilot = row?['pilot'] == null ? null : _parsePilot(row?['pilot']);
    const allowed = {'action', 'reason', 'check', 'source_ids', 'pilot'};
    if (row == null ||
        row.keys.toSet().difference(allowed).isNotEmpty ||
        action == null ||
        reason == null ||
        check == null ||
        sourceIds == null ||
        (row.containsKey('pilot') && row['pilot'] != null && pilot == null)) {
      throw const _InvalidSourceBriefResponse();
    }
    actions.add(
      SourceBriefProposedAction(
        action: action,
        reason: reason,
        check: check,
        sourceIds: sourceIds,
        pilot: pilot,
      ),
    );
  }

  final unknowns = <String>[];
  for (final raw in unknownsValue) {
    final item = _safeText(raw, maxLength: 180);
    if (item == null) throw const _InvalidSourceBriefResponse();
    unknowns.add(item);
  }
  return SourceBriefBusinessAnalysis(
    sourceObservations: observations,
    interpretations: interpretations,
    proposedActions: actions,
    unknowns: unknowns,
  );
}

SourceBriefPilotProposal? _parsePilot(Object? value) {
  final map = _asMap(value);
  if (map == null ||
      map.keys.toSet().difference({
        'audience',
        'procedure',
        'measure',
        'continue_if',
        'stop_if',
      }).isNotEmpty ||
      map.keys.toSet().length != 5) {
    return null;
  }
  final audience = _safeText(map['audience'], maxLength: 180);
  final procedure = _safeText(map['procedure'], maxLength: 180);
  final measure = _safeText(map['measure'], maxLength: 180);
  final continueIf = _safeText(map['continue_if'], maxLength: 180);
  final stopIf = _safeText(map['stop_if'], maxLength: 180);
  if (audience == null ||
      procedure == null ||
      measure == null ||
      continueIf == null ||
      stopIf == null) {
    return null;
  }
  return SourceBriefPilotProposal(
    audience: audience,
    procedure: procedure,
    measure: measure,
    continueIf: continueIf,
    stopIf: stopIf,
  );
}

List<String>? _sourceReferences(
  Object? value, {
  required Set<String> knownSourceIds,
}) {
  if (value is! List || value.isEmpty || value.length > 8) return null;
  final result = <String>[];
  for (final raw in value) {
    final sourceId = _safeIdentifier(raw);
    if (sourceId == null || !knownSourceIds.contains(sourceId)) return null;
    result.add(sourceId);
  }
  return result;
}

SourceBriefBusinessAnalysisState _businessAnalysisState(Object? value) =>
    switch (value) {
      'not_requested' => SourceBriefBusinessAnalysisState.notRequested,
      'draft' => SourceBriefBusinessAnalysisState.draft,
      'unavailable' => SourceBriefBusinessAnalysisState.unavailable,
      'error' => SourceBriefBusinessAnalysisState.error,
      _ => SourceBriefBusinessAnalysisState.unknown,
    };

SourceBriefTaskState _parseTaskState(Object? value) => switch (value) {
  'pending' => SourceBriefTaskState.pending,
  'running' => SourceBriefTaskState.running,
  'succeeded' => SourceBriefTaskState.succeeded,
  'failed' => SourceBriefTaskState.failed,
  'interrupted' => SourceBriefTaskState.interrupted,
  _ => SourceBriefTaskState.unknown,
};

String _safeReviewStatus(Object? value) => switch (value) {
  'HUMAN_PENDING' => 'HUMAN_PENDING',
  'APPROVED' => 'APPROVED',
  'REJECTED' => 'REJECTED',
  _ => 'UNKNOWN',
};

String? _safeSourceUrl(Object? value) {
  final text = _safeText(value, maxLength: 2048);
  if (text == null) return null;
  final uri = Uri.tryParse(text);
  if (uri == null ||
      (uri.scheme != 'http' && uri.scheme != 'https') ||
      uri.host.isEmpty ||
      uri.userInfo.isNotEmpty) {
    return null;
  }
  return text;
}

String? _safeIdentifier(Object? value) {
  final text = _safeText(value, maxLength: 160);
  if (text == null ||
      !RegExp(r'^[A-Za-z0-9][A-Za-z0-9:._/@-]{0,159}$').hasMatch(text)) {
    return null;
  }
  return text;
}

String? _optionalIdentifier(Object? value) {
  if (value == null) return null;
  return _safeIdentifier(value);
}

String? _safeText(Object? value, {required int maxLength}) {
  if (value is! String) return null;
  final text = value.trim();
  if (text.isEmpty ||
      text.length > maxLength ||
      RegExp(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]').hasMatch(text)) {
    return null;
  }
  return text;
}

Map<String, Object?>? _asMap(Object? value) {
  if (value is! Map) return null;
  final result = <String, Object?>{};
  for (final entry in value.entries) {
    if (entry.key is! String) return null;
    result[entry.key as String] = entry.value;
  }
  return result;
}

String? _contextSignature(Object? value) {
  if (value is! Map) return null;
  try {
    return jsonEncode(_canonicalValue(value));
  } on Object {
    return null;
  }
}

Object? _canonicalValue(Object? value) {
  if (value is Map) {
    final entries = value.entries.where((entry) => entry.key is String).toList()
      ..sort(
        (left, right) => (left.key as String).compareTo(right.key as String),
      );
    return {
      for (final entry in entries)
        entry.key as String: _canonicalValue(entry.value),
    };
  }
  if (value is Iterable) {
    return value.map(_canonicalValue).toList(growable: false);
  }
  return value;
}

final class _CthContextSelection {
  const _CthContextSelection({
    required this.globalScope,
    required this.subjectId,
    required this.displayNames,
  });

  final bool globalScope;
  final String? subjectId;
  final Map<String, String> displayNames;

  String? get scopeLabel =>
      displayNames['zh-CN'] ??
      displayNames['en'] ??
      displayNames['ko'] ??
      (globalScope ? '全球商业' : subjectId);

  bool sameScope(_CthContextSelection other) =>
      globalScope == other.globalScope &&
      (globalScope || subjectId == other.subjectId);

  bool matches(SourceBriefScope scope) =>
      scope.productId == 'CTH' &&
      scope.domainId == 'cth' &&
      scope.globalScope == globalScope &&
      scope.brandFocusId == null &&
      (globalScope
          ? scope.subjectId == null
          : scope.subjectId == subjectId && subjectId != null);

  static _CthContextSelection? parse(Map<String, dynamic> response) {
    if (response['ok'] != true ||
        response['contract'] != 'lumenis.context.v1' ||
        response['selection_only'] != true) {
      return null;
    }
    final context = _asMap(response['context']);
    if (context == null) return null;
    final mode = context['mode'];
    if (mode == 'GLOBAL_ALL' &&
        context['domain_id'] == null &&
        context['subject_id'] == null &&
        context['brand_focus_id'] == null) {
      return _CthContextSelection(
        globalScope: true,
        subjectId: null,
        displayNames: _displayNames(context['display_name']),
      );
    }
    if (mode != 'FOCUS' ||
        context['domain_id'] != 'CTH' ||
        context['brand_focus_id'] != null) {
      return null;
    }
    final subjectId = _safeIdentifier(context['subject_id']);
    if (subjectId == null) return null;
    return _CthContextSelection(
      globalScope: false,
      subjectId: subjectId,
      displayNames: _displayNames(context['display_name']),
    );
  }
}

_CthContextSelection? _selectionFromEnvelope(Object? envelope) {
  final response = _asMap(envelope);
  if (response == null) return null;
  return _CthContextSelection.parse(response);
}

Map<String, String> _displayNames(Object? value) {
  final map = _asMap(value);
  if (map == null) return const {};
  final result = <String, String>{};
  for (final entry in map.entries) {
    final text = _safeText(entry.value, maxLength: 240);
    if (text != null) result[entry.key] = text;
  }
  return Map.unmodifiable(result);
}

final class _FreshCthContext {
  const _FreshCthContext({
    required this.selection,
    required this.signature,
    required this.scopeChanged,
  });

  final _CthContextSelection selection;
  final String signature;
  final bool scopeChanged;
}

final class _ContextChanged implements Exception {
  const _ContextChanged();
}

final class _InvalidSourceBriefResponse implements Exception {
  const _InvalidSourceBriefResponse();
}
